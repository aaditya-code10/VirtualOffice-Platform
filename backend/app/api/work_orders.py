"""Work orders: the unit of work the digital workforce executes."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.registry import AGENTS_BY_KEY, needs_approval, route_command
from app.core.deps import CurrentCompany, CurrentUser, DbSession, RequireMember
from app.models import AgentTask, WorkOrder
from app.schemas import AgentTaskOut, WorkOrderCreate, WorkOrderOut, WorkOrderSummary
from app.services import orchestrator

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


@router.get("", response_model=list[WorkOrderSummary])
def list_work_orders(
    company: CurrentCompany,
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    agent_key: str | None = None,
) -> list[WorkOrderSummary]:
    query = select(WorkOrder).where(WorkOrder.company_id == company.id)
    if agent_key:
        query = query.join(AgentTask).where(AgentTask.agent_key == agent_key)

    orders = db.execute(
        query.order_by(WorkOrder.created_at.desc()).limit(limit)
    ).scalars().unique().all()

    return [WorkOrderSummary.model_validate(_summary(o)) for o in orders]


@router.post("", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    company: CurrentCompany,
    user: RequireMember,
    db: DbSession,
) -> WorkOrderOut:
    """Execute a command against the workforce and return the completed result.

    Execution is synchronous: specialists run concurrently and the whole order
    typically completes in well under a second on the deterministic engine, and
    in a few seconds on the LLM engine.
    """
    if payload.agent_key and payload.agent_key not in AGENTS_BY_KEY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown agent '{payload.agent_key}'")

    order = orchestrator.execute_work_order(
        db,
        company=company,
        user=user,
        command=payload.command,
        agent_key=payload.agent_key,
        document_id=payload.document_id,
        category=payload.category,
    )
    db.flush()
    return WorkOrderOut.model_validate(_detail(db, order))


@router.get("/preview")
def preview_routing(
    command: str,
    company: CurrentCompany,
    user: CurrentUser,
) -> dict:
    """Which agents would handle this command, without running it."""
    keys = route_command(command)[: orchestrator.MAX_PARALLEL_AGENTS]
    return {
        "command": command,
        "agents": [
            {
                "key": k,
                "name": AGENTS_BY_KEY[k].name,
                "department": AGENTS_BY_KEY[k].department,
            }
            for k in keys
        ],
        "requires_approval": needs_approval(command),
    }


@router.get("/{work_order_id}", response_model=WorkOrderOut)
def get_work_order(
    work_order_id: str, company: CurrentCompany, user: CurrentUser, db: DbSession
) -> WorkOrderOut:
    order = db.execute(
        select(WorkOrder)
        .options(selectinload(WorkOrder.tasks))
        .where(WorkOrder.company_id == company.id, WorkOrder.id == work_order_id)
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work order not found")
    return WorkOrderOut.model_validate(_detail(db, order))


# --------------------------------------------------------------------------- #
def _summary(order: WorkOrder) -> dict:
    return {
        "id": order.id, "command": order.command, "status": order.status.value,
        "progress": order.progress, "engine": order.engine, "confidence": order.confidence,
        "document_id": getattr(order, "document_id", None),
        "category": getattr(order, "category", None),
        "headline": order.headline, "recommendation": order.recommendation,
        "consulted_agent_keys": order.consulted_agent_keys or [],
        "requires_approval": order.requires_approval, "created_at": order.created_at,
    }


def _detail(db, order: WorkOrder) -> dict:
    tasks = db.execute(
        select(AgentTask).where(AgentTask.work_order_id == order.id).order_by(AgentTask.created_at)
    ).scalars().all()

    return {
        "id": order.id,
        "command": order.command,
        "status": order.status.value,
        "progress": order.progress,
        "mode": order.mode,
        "engine": order.engine,
        "target_agent_key": order.target_agent_key,
        "document_id": getattr(order, "document_id", None),
        "category": getattr(order, "category", None),
        "headline": order.headline,
        "summary": order.summary,
        "recommendation": order.recommendation,
        "artifact_title": order.artifact_title,
        "artifact_body": order.artifact_body,
        "confidence": order.confidence,
        "risks": order.risks or [],
        "opportunities": order.opportunities or [],
        "next_actions": order.next_actions or [],
        "citations": order.citations or [],
        "consulted_agent_keys": order.consulted_agent_keys or [],
        "requires_approval": order.requires_approval,
        "error": order.error,
        "duration_ms": order.duration_ms,
        "tokens_used": order.tokens_used,
        "created_at": order.created_at,
        "completed_at": order.completed_at,
        "tasks": [
            AgentTaskOut.model_validate(
                {
                    "id": t.id, "agent_key": t.agent_key, "status": t.status.value,
                    "finding": t.finding, "evidence": t.evidence or [], "risks": t.risks or [],
                    "opportunities": t.opportunities or [], "recommended_action": t.recommended_action,
                    "confidence": t.confidence, "duration_ms": t.duration_ms, "error": t.error,
                }
            )
            for t in tasks
        ],
    }
