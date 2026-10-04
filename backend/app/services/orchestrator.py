"""Multi-agent orchestration.

Flow for an orchestrated work order:

    command
      -> route to relevant specialists (keyword scoring)
      -> for each specialist, retrieve company context (RAG + metrics + facts)
      -> run specialists CONCURRENTLY (thread pool; the Anthropic client is sync)
      -> persist each contribution as an AgentTask row
      -> executive agent reconciles the findings into one decision brief
      -> raise an Approval when the recommendation commits real resources

Every stage degrades gracefully: if the LLM is unavailable or a single agent
fails, the deterministic engine fills that slot and the work order still
completes with an honest ``engine`` label.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.registry import (
    AGENTS_BY_KEY,
    SYNTHESIZER_KEY,
    AgentSpec,
    needs_approval,
    route_command,
)
from app.config import settings
from app.core import audit
from app.models import (
    Agent,
    AgentTask,
    Approval,
    ApprovalStatus,
    Company,
    Document,
    DocumentChunk,
    Fact,
    RiskLevel,
    TaskStatus,
    User,
    WorkOrder,
    WorkOrderStatus,
    utcnow,
)
from app.services import analytics as analytics_service
from app.services import heuristics, llm, rag
from app.services.heuristics import MetricTrend, format_value
from app.services.llm import ExecutiveBrief, LLMUnavailable, SpecialistFinding
from app.services.rag import Retrieved

logger = logging.getLogger(__name__)

MAX_PARALLEL_AGENTS = 4


# --- Context generation for business analysis ---
# In the previous corporate workflow, this loaded company-specific metrics
# and database facts. The new AI Business Consultant workflow only relies on 
# the user's direct inputs and uploaded documents.


# --------------------------------------------------------------------------- #
# Single specialist execution
# --------------------------------------------------------------------------- #
def run_specialist(
    spec: AgentSpec,
    command: str,
    hits: list[Retrieved],
    extra_context: str = "",
) -> tuple[SpecialistFinding, str, int]:
    """Return (finding, engine_used, tokens)."""
    if not llm.is_available():
        raise RuntimeError("AI analysis is currently unavailable. Please check the Gemini API configuration.")
        
    context_block = rag.build_context_block(hits)
    if extra_context:
        context_block = f"{extra_context}\n\n{context_block}".strip() if context_block else extra_context

    prompt = llm.build_specialist_prompt(
        command=command,
        context_block=context_block,
    )
    finding, tokens = llm.analyse(spec.system_prompt, prompt)
    return finding, "llm", tokens


def run_synthesis(
    command: str,
    findings: list[tuple[AgentSpec, SpecialistFinding]],
    extra_context: str = "",
) -> tuple[ExecutiveBrief, str, int]:
    if not llm.is_available():
        raise RuntimeError("AI analysis is currently unavailable. Please check the Gemini API configuration.")
        
    specialist_block = "\n\n".join(
        f"### {spec.department} — {spec.name}\n"
        f"Analysis: {f.analysis}\n"
        f"Strengths: {', '.join(f.key_strengths) or 'none'}\n"
        f"Risks: {'; '.join(f.key_risks) or 'none'}\n"
        f"Assumptions: {'; '.join(f.assumptions_made) or 'none'}\n"
        f"Missing Info: {'; '.join(f.missing_information) or 'none'}\n"
        f"Recommended pivot: {f.recommended_pivot}"
        for spec, f in findings
    )
    prompt = llm.build_synthesis_prompt(
        command=command,
        specialist_block=specialist_block,
        extra_context=extra_context,
    )
    brief, tokens = llm.synthesise(AGENTS_BY_KEY[SYNTHESIZER_KEY].system_prompt, prompt)
    return brief, "llm", tokens


# --------------------------------------------------------------------------- #
# Work order execution
# --------------------------------------------------------------------------- #
def execute_work_order(
    db: Session,
    *,
    company: Company,
    user: User | None,
    command: str,
    agent_key: str | None = None,
    document_id: str | None = None,
    category: str | None = None,
) -> WorkOrder:
    """Create, run, and persist a work order end to end."""
    started = time.perf_counter()
    command = command.strip()
    direct = bool(agent_key)

    order = WorkOrder(
        company_id=company.id,
        requested_by_id=user.id if user else None,
        command=command,
        status=WorkOrderStatus.RUNNING,
        mode="direct" if direct else "orchestrated",
        target_agent_key=agent_key,
        document_id=document_id,
        category=category,
        progress=5,
    )
    db.add(order)
    db.flush()

    try:
        _run(db, order, company, command, agent_key, direct, document_id, category)
        order.status = WorkOrderStatus.COMPLETED
        order.progress = 100
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Work order %s failed", order.id)
        order.status = WorkOrderStatus.FAILED
        order.error = str(exc)
        order.progress = 100

    order.completed_at = utcnow()
    order.duration_ms = int((time.perf_counter() - started) * 1000)

    audit.record(
        db,
        action="work_order.executed",
        company_id=company.id,
        actor=user,
        entity_type="work_order",
        entity_id=order.id,
        detail={
            "status": order.status.value,
            "engine": order.engine,
            "agents": order.consulted_agent_keys,
            "duration_ms": order.duration_ms,
        },
    )
    db.flush()
    return order


def _run(
    db: Session,
    order: WorkOrder,
    company: Company,
    command: str,
    agent_key: str | None,
    direct: bool,
    document_id: str | None = None,
    category: str | None = None,
) -> None:

    # --- Load attached business document if provided ----------------------
    attached_doc = None
    doc_text_block = ""
    if document_id:
        attached_doc = db.execute(
            select(Document).where(Document.id == document_id, Document.company_id == company.id)
        ).scalar_one_or_none()
        if attached_doc:
            chunks = db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == attached_doc.id)
                .order_by(DocumentChunk.position)
            ).scalars().all()
            if chunks:
                joined = "\n\n".join(c.content for c in chunks)
                doc_text_block = (
                    f"=== ATTACHED BUSINESS PLAN DOCUMENT: {attached_doc.filename} ===\n"
                    f"{joined[:35000]}\n"
                    f"=== END OF ATTACHED BUSINESS PLAN ==="
                )

    extra_parts = []
    if category:
        extra_parts.append(f"BUSINESS CATEGORY / INDUSTRY SECTOR: {category}")
    if doc_text_block:
        extra_parts.append(doc_text_block)
    extra_context = "\n\n".join(extra_parts)

    # --- Choose the panel --------------------------------------------------
    if direct:
        if agent_key not in AGENTS_BY_KEY:
            raise ValueError(f"Unknown agent '{agent_key}'")
        specialist_keys = [agent_key]
    else:
        specialist_keys = route_command(command)[:MAX_PARALLEL_AGENTS]

    db_agents = {
        a.key: a
        for a in db.execute(select(Agent).where(Agent.company_id == company.id)).scalars().all()
    }
    specialist_keys = [k for k in specialist_keys if db_agents.get(k) and db_agents[k].enabled]
    if not specialist_keys:
        specialist_keys = [k for k in ("finance", "operations", "sales") if k in db_agents]
    if not specialist_keys:
        raise ValueError("No enabled agents available for this company")

    order.consulted_agent_keys = list(specialist_keys)
    order.progress = 20
    db.flush()

    # --- Retrieve context per agent ---------------------------------------
    retrieval: dict[str, list[Retrieved]] = {}
    for key in specialist_keys:
        spec = AGENTS_BY_KEY[key]
        query = f"{command} {category or ''} {spec.focus}"
        retrieval[key] = rag.search(db, company.id, query, top_k=settings.retrieval_top_k)

    # --- Fan out (concurrently) -------------------------------------------
    specs = [AGENTS_BY_KEY[k] for k in specialist_keys]
    engines: set[str] = set()
    total_tokens = 0

    def _work(spec: AgentSpec):
        agent_started = time.perf_counter()
        finding, engine, tokens = run_specialist(
            spec, command, retrieval[spec.key], extra_context=extra_context
        )
        return spec, finding, engine, tokens, int((time.perf_counter() - agent_started) * 1000)

    # Run specialists sequentially with a small delay to avoid burst rate limits.
    results = []
    for i, spec in enumerate(specs):
        results.append(_work(spec))
        if i < len(specs) - 1 and settings.rate_limit_delay_seconds > 0:
            time.sleep(settings.rate_limit_delay_seconds)

    findings: list[tuple[AgentSpec, SpecialistFinding]] = []
    for spec, finding, engine, tokens, elapsed in results:
        engines.add(engine)
        total_tokens += tokens
        findings.append((spec, finding))

        db.add(
            AgentTask(
                work_order_id=order.id,
                agent_id=db_agents[spec.key].id,
                agent_key=spec.key,
                status=TaskStatus.COMPLETED,
                finding=finding.analysis,
                evidence=finding.key_strengths + finding.assumptions_made + finding.missing_information,
                risks=finding.key_risks,
                opportunities=finding.key_strengths,
                recommended_action=finding.recommended_pivot,
                confidence=finding.viability_score,
                duration_ms=elapsed,
            )
        )

    order.progress = 70
    db.flush()

    # --- Synthesise --------------------------------------------------------
    if direct:
        spec, finding = findings[0]
        order.headline = heuristics.trim(f"{spec.department}: {finding.analysis}", 118)
        order.summary = finding.analysis
        order.recommendation = finding.recommended_pivot
        order.artifact_title = f"{spec.department} Analysis — {heuristics.trim(command, 60)}"
        order.artifact_body = _direct_artifact(spec, finding, command, company.name)
        order.confidence = finding.viability_score
        order.risks = finding.key_risks
        order.opportunities = finding.key_strengths
        order.next_actions = [finding.recommended_pivot]
        order.requires_approval = needs_approval(command)
    else:
        brief, engine, tokens = run_synthesis(command, findings, extra_context=extra_context)
        engines.add(engine)
        total_tokens += tokens

        synth = AGENTS_BY_KEY[SYNTHESIZER_KEY]
        if synth.key in db_agents:
            db.add(
                AgentTask(
                    work_order_id=order.id,
                    agent_id=db_agents[synth.key].id,
                    agent_key=synth.key,
                    status=TaskStatus.COMPLETED,
                    finding=brief.executive_summary,
                    evidence=[f"{spec.department} finding" for spec, _ in findings],
                    risks=brief.department_contradictions,
                    opportunities=brief.department_agreements,
                    recommended_action=brief.final_decision,
                    confidence=50,
                )
            )
            order.consulted_agent_keys = list(order.consulted_agent_keys) + [synth.key]

        order.headline = f"Master AI Decision: {brief.final_decision}"
        order.summary = brief.executive_summary
        order.recommendation = brief.final_decision
        if attached_doc:
            order.artifact_title = f"AI Business Analysis — {attached_doc.filename}"
        elif category:
            order.artifact_title = f"{category} Analysis — {heuristics.trim(command, 60)}"
        else:
            order.artifact_title = "Consulting Brief"
        order.artifact_body = brief.artifact_body
        order.confidence = 50
        order.risks = brief.department_contradictions
        order.opportunities = brief.department_agreements
        order.next_actions = brief.action_plan
        order.requires_approval = brief.requires_human_approval or needs_approval(command)

    # --- Citations ---------------------------------------------------------
    citations: list[dict] = []
    if attached_doc:
        citations.append(
            {
                "document_id": attached_doc.id,
                "filename": attached_doc.filename,
                "chunk": 0,
                "score": 100.0,
                "excerpt": f"Attached Business Plan: '{attached_doc.filename}' ({attached_doc.word_count:,} words). Analyzed in detail by workforce.",
            }
        )
    seen: set[str] = set()
    for hits in retrieval.values():
        for hit in hits[:3]:
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            citations.append(
                {
                    "document_id": hit.document_id,
                    "filename": hit.filename,
                    "chunk": hit.position,
                    "score": hit.score,
                    "excerpt": hit.excerpt,
                }
            )
    order.citations = citations[:10]
    order.engine = "llm" if engines == {"llm"} else ("hybrid" if "llm" in engines else "heuristic")
    order.tokens_used = total_tokens

    # --- Approval gate -----------------------------------------------------
    if order.requires_approval:
        db.add(
            Approval(
                company_id=company.id,
                work_order_id=order.id,
                title=heuristics.trim(order.headline or command, 200),
                description=order.recommendation,
                risk=_risk_from(order),
                owner=AGENTS_BY_KEY[SYNTHESIZER_KEY].department,
                expected_impact=f"Confidence {order.confidence}%",
                status=ApprovalStatus.PENDING,
            )
        )


def _risk_from(order: WorkOrder) -> RiskLevel:
    risk_count = len(order.risks or [])
    if order.confidence < 50 or risk_count >= 4:
        return RiskLevel.HIGH
    if risk_count >= 2:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _direct_artifact(spec: AgentSpec, finding: SpecialistFinding, command: str, company_name: str) -> str:
    lines = [
        f"# {spec.department} Analysis — {company_name}",
        "",
        f"**Analyst:** {spec.name} ({spec.role})",
        f"**Request:** {command}",
        f"**Viability Score:** {finding.viability_score}%",
        "",
        "## Analysis",
        finding.analysis,
        "",
        "## Recommended Pivot",
        finding.recommended_pivot,
    ]
    if finding.key_strengths:
        lines += ["", "## Key Strengths"] + [f"- {e}" for e in finding.key_strengths]
    if finding.key_risks:
        lines += ["", "## Risks"] + [f"- {r}" for r in finding.key_risks]
    if finding.assumptions_made:
        lines += ["", "## Assumptions"] + [f"- {o}" for o in finding.assumptions_made]
    if finding.missing_information:
        lines += ["", "## Missing Information"] + [f"- {o}" for o in finding.missing_information]
    return "\n".join(lines)
