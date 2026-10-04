"""Deterministic analysis engine.

This is the fallback used when no Anthropic key is configured. Unlike a canned
demo, it reads the company's actual metric history and retrieved document
excerpts and derives its findings from them - trend direction, magnitude of
change, threshold breaches - so the output changes when the data changes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.agents.registry import AgentSpec, needs_approval
from app.services.llm import ExecutiveBrief, SpecialistFinding
from app.services.rag import Retrieved


@dataclass
class MetricTrend:
    key: str
    label: str
    unit: str
    latest: float
    previous: float | None
    change_pct: float | None
    periods: int

    @property
    def direction(self) -> str:
        if self.change_pct is None or abs(self.change_pct) < 0.5:
            return "flat"
        return "up" if self.change_pct > 0 else "down"

    def render(self) -> str:
        value = format_value(self.latest, self.unit)
        if self.change_pct is None:
            return f"{self.label} is {value}"
        arrow = {"up": "up", "down": "down", "flat": "flat at"}[self.direction]
        if self.direction == "flat":
            return f"{self.label} is {arrow} {value}"
        return f"{self.label} is {arrow} {abs(self.change_pct):.1f}% to {value}"


def format_value(value: float, unit: str, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}
    if unit == "currency":
        symbol = symbols.get(currency, "")
        if abs(value) >= 1_000_000:
            return f"{symbol}{value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"{symbol}{value / 1_000:.1f}K"
        return f"{symbol}{value:,.0f}"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "score":
        return f"{value:.0f}/100"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:g}"


# Metrics where a rising value is bad news.
INVERSE_METRICS = {"cac", "churn_rate", "attrition_rate", "opex", "support_tickets", "cycle_time_days", "deal_cycle_days"}

# Threshold rules: (metric_key, comparison, limit, risk phrasing)
THRESHOLDS: list[tuple[str, str, float, str]] = [
    ("gross_margin", "<", 55.0, "Gross margin below 55% leaves little room for acquisition spend"),
    ("cash_runway_months", "<", 9.0, "Cash runway under 9 months constrains hiring and investment"),
    ("capacity_utilisation", ">", 85.0, "Capacity above 85% means delivery risk on any new demand"),
    ("churn_rate", ">", 5.0, "Churn above 5% is eroding the revenue base faster than acquisition replaces it"),
    ("attrition_rate", ">", 15.0, "Attrition above 15% signals retention risk in delivery teams"),
    ("csat", "<", 75.0, "CSAT below 75 correlates with renewal risk"),
    ("win_rate", "<", 20.0, "Win rate under 20% suggests qualification or positioning problems"),
]


def evaluate_thresholds(trends: dict[str, MetricTrend]) -> list[str]:
    breaches: list[str] = []
    for key, comparison, limit, phrasing in THRESHOLDS:
        trend = trends.get(key)
        if trend is None:
            continue
        if (comparison == "<" and trend.latest < limit) or (comparison == ">" and trend.latest > limit):
            breaches.append(phrasing)
    return breaches


# --------------------------------------------------------------------------- #
# Question analysis
#
# Without these the engine would recite the same departmental dashboard whatever
# it was asked. The command has to steer which metrics are foregrounded, which
# document passages are quoted, and how the answer is framed.
# --------------------------------------------------------------------------- #
QUESTION_SHAPES: list[tuple[str, tuple[str, ...]]] = [
    # Order matters: the first match wins.
    ("decision", ("should we", "should i", "can we", "can i", "do we", "is it worth",
                  "would it", "or slow", "vs ", " versus ", "either", "better to")),
    ("cause",    ("why", "what caused", "what is driving", "what's driving", "reason for",
                  "explain", "root cause", "how come")),
    ("quantity", ("how much", "how many", "what is our", "what's our", "how long",
                  "what are our", "current level", "how fast")),
    ("forecast", ("will we", "forecast", "project", "expect", "if we do nothing",
                  "next quarter", "next month", "runway", "trend toward")),
    ("risk",     ("risk", "danger", "exposed", "worst case", "what could go wrong",
                  "threat", "vulnerab")),
]


def question_shape(command: str) -> str:
    """Classify what kind of answer the question is asking for."""
    text = " " + " ".join(command.lower().split()) + " "
    for shape, markers in QUESTION_SHAPES:
        if any(marker in text for marker in markers):
            return shape
    return "assessment"


def rank_metrics_for_question(
    spec: AgentSpec,
    command: str,
    trends: dict[str, MetricTrend],
) -> tuple[list[MetricTrend], list[MetricTrend]]:
    """Split the agent's metrics into (those the question asks about, the rest).

    Matching is on the metric key and its human label, so "what is our runway"
    foregrounds cash_runway_months rather than whatever moved most.
    """
    from app.services.rag import tokenize

    asked = set(tokenize(command))
    owned = [trends[key] for key in spec.metric_keys if key in trends]

    targeted: list[MetricTrend] = []
    rest: list[MetricTrend] = []
    for trend in owned:
        vocabulary = set(tokenize(trend.key.replace("_", " ") + " " + trend.label))
        (targeted if vocabulary & asked else rest).append(trend)

    return targeted, rest


def _is_meaningful_match(score: int, asked: set[str]) -> bool:
    """Is this overlap strong enough to quote?

    A flat "at least two terms" rule silently discards short, specific questions
    ("should we raise prices?" overlaps a pricing fact on one term). Scoring
    relative to the question's length keeps precision on long questions without
    going blind on short ones.
    """
    if not asked:
        return False
    return score >= 2 or (score >= 1 and score / len(asked) >= 0.2)


def matching_fact(facts: list, command: str) -> tuple[str, str] | None:
    """Find the curated fact that best answers the question.

    Facts are hand-entered ground truth and are often the only thing that speaks
    to a subject the department has no metric for (pricing policy, concentration,
    contract terms). Ignoring them was leaving the best evidence on the table.
    """
    from app.services.rag import tokenize

    asked = set(tokenize(command))
    if not asked or not facts:
        return None

    best = None
    best_score = 0
    for fact in facts:
        text = f"{getattr(fact, 'title', '')} {getattr(fact, 'statement', '')}"
        score = len(asked & set(tokenize(text)))
        if score > best_score:
            best_score, best = score, fact

    if best is None or not _is_meaningful_match(best_score, asked):
        return None

    classification = getattr(best.classification, "value", best.classification)
    return str(best.statement), str(classification)


def quote_supporting_passage(hits: list[Retrieved], command: str, limit: int = 220) -> str | None:
    """Pull the sentence from the retrieved chunks that best matches the question.

    Quoting the passage is what makes a document-grounded answer change when the
    question changes - the retrieval already varies, so the answer should too.
    """
    from app.services.rag import tokenize

    asked = set(tokenize(command))
    if not asked:
        return None

    best_sentence = None
    best_score = 0
    for hit in hits[:3]:
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(hit.content.split())):
            if len(sentence) < 40:
                continue
            score = len(asked & set(tokenize(sentence)))
            if score > best_score:
                best_score, best_sentence = score, sentence

    if best_sentence is None or not _is_meaningful_match(best_score, asked):
        return None
    return best_sentence[:limit] + ("…" if len(best_sentence) > limit else "")


def frame_verdict(
    shape: str,
    spec: AgentSpec,
    focus: MetricTrend | None,
    deteriorating: list[MetricTrend],
) -> str:
    """Word the conclusion according to what was actually asked."""
    worst = (
        max(deteriorating, key=lambda t: abs(t.change_pct or 0))
        if deteriorating
        else None
    )

    if shape == "decision":
        if worst is not None:
            return (
                f"On {spec.department}'s numbers the answer is constrained by "
                f"{worst.label.lower()} at {format_value(worst.latest, worst.unit)} "
                f"({abs(worst.change_pct or 0):.1f}% adverse) - that is the figure this "
                f"decision has to clear."
            )
        return (
            f"No {spec.department.lower()} metric argues against proceeding; this "
            f"department is not the blocker on this decision."
        )

    if shape == "cause":
        if focus is not None and focus.change_pct is not None:
            return (
                f"The movement in {focus.label.lower()} is {focus.change_pct:+.1f}% "
                f"period-over-period. {_driver_sentence(focus, deteriorating)}"
            )
        return (
            f"{spec.department} has no metric that isolates the cause; the driver is "
            f"not visible in the data this department holds."
        )

    if shape == "quantity":
        if focus is not None:
            prior = (
                f" (was {format_value(focus.previous, focus.unit)} the prior period)"
                if focus.previous is not None
                else ""
            )
            return f"{focus.label} currently stands at {format_value(focus.latest, focus.unit)}{prior}."
        return f"{spec.department} does not track a figure that answers this directly."

    if shape == "forecast":
        if focus is not None and focus.change_pct is not None:
            projected = focus.latest * (1 + (focus.change_pct / 100))
            return (
                f"Extending the current rate one more period puts {focus.label.lower()} at "
                f"roughly {format_value(projected, focus.unit)}. This is a straight-line "
                f"extrapolation, not a model."
            )
        return f"{spec.department} lacks the history to project this."

    if shape == "risk":
        if deteriorating:
            names = ", ".join(t.label.lower() for t in deteriorating[:3])
            return f"The exposure in {spec.department.lower()} sits in {names}."
        return f"No {spec.department.lower()} metric is currently trending into risk."

    # assessment
    if worst is not None:
        return (
            f"The pressure point is {worst.label.lower()}, which moved "
            f"{abs(worst.change_pct or 0):.1f}% in the wrong direction and is the constraint "
            f"to address before anything else in {spec.department}."
        )
    return (
        f"No {spec.department.lower()} metric is deteriorating, so this department is not "
        f"currently the binding constraint on the request."
    )


def _driver_sentence(focus: MetricTrend, deteriorating: list[MetricTrend]) -> str:
    """Name a plausible co-moving metric rather than asserting causation."""
    others = [t for t in deteriorating if t.key != focus.key]
    if not others:
        return "No other tracked metric in this department moved with it."
    partner = max(others, key=lambda t: abs(t.change_pct or 0))
    return (
        f"{partner.label} moved {partner.change_pct:+.1f}% over the same period and is the "
        f"strongest co-movement in this department - correlation only, not a proven cause."
    )


def frame_action(shape: str, spec: AgentSpec, focus: MetricTrend | None) -> str:
    """The recommended next step depends on what was asked, not only on the data."""
    if focus is None:
        return f"Add {spec.department} metrics to the workspace so this question can be answered with data."

    value = format_value(focus.latest, focus.unit)
    if shape == "decision":
        return (
            f"Model this decision against {focus.label.lower()} at {value} and set the "
            f"threshold that would make it a no."
        )
    if shape == "cause":
        return (
            f"Break {focus.label.lower()} ({value}) down by its components to isolate the "
            f"driver, and report back within one week."
        )
    if shape == "quantity":
        return f"Confirm {focus.label.lower()} at {value} against source records before it is quoted onward."
    if shape == "forecast":
        return f"Build a two-period projection for {focus.label.lower()} from {value} with stated assumptions."
    if shape == "risk":
        return f"Set an alert threshold on {focus.label.lower()} and name the owner accountable for it."
    return (
        f"{spec.department} to review {focus.label.lower()} (currently {value}) and report "
        f"the driver within one week."
    )


# --------------------------------------------------------------------------- #
# Consultant templates: used when no LLM key is available
# --------------------------------------------------------------------------- #
def specialist_finding(
    *,
    spec: AgentSpec,
    command: str,
    trends: dict[str, MetricTrend],
    hits: list[Retrieved],
    currency: str = "USD",
    facts: list | None = None,
) -> SpecialistFinding:
    """Fallback analysis scoped to the business idea, not company metrics."""
    # Echo back the prompt to demonstrate dynamic-like behavior in the offline fallback
    idea_summary = trim(command, 100)
    
    analysis = (
        f"As the {spec.name} ({spec.role}), I have reviewed your idea: '{idea_summary}'. "
        "Please note: This is a deterministic fallback response because no Anthropic API key is configured. "
        "A true AI analysis of your budget, market, and operations requires enabling the LLM engine."
    )

    # Enrich analysis with any RAG passage
    passage = quote_supporting_passage(hits, command)
    if passage and hits:
        analysis += f' A relevant insight from your uploaded documents: "{passage}"'

    strengths = [
        f"{spec.department} principles can be applied to this idea.",
        "Early planning reduces downstream risks."
    ]
    risks = [
        f"Execution risks related to {spec.department.lower()}.",
        "Insufficient data to validate product-market fit."
    ]
    missing = [
        "Actual market validation and surveys.",
        "Detailed cost breakdowns.",
        "Competitor analysis."
    ]

    return SpecialistFinding(
        analysis=analysis,
        key_strengths=strengths,
        key_risks=risks,
        assumptions_made=[
            "Operating without LLM analysis (deterministic fallback).",
        ],
        missing_information=missing,
        recommended_pivot=f"Enable the LLM engine in backend/.env for genuine AI {spec.department.lower()} analysis.",
        viability_score=50,
    )


def executive_brief(
    *,
    command: str,
    company_name: str,
    findings: list[tuple[AgentSpec, SpecialistFinding]],
    trends: dict[str, MetricTrend],
    health_score: int,
) -> ExecutiveBrief:
    """Fallback synthesis: reconcile specialist findings into an entrepreneur-friendly brief."""
    all_agreements: list[str] = []
    all_risks: list[str] = []
    all_actions: list[str] = []
    avg_score = 0

    for spec, finding in findings:
        all_agreements.extend(finding.key_strengths)
        all_risks.extend(finding.key_risks)
        if finding.recommended_pivot:
            all_actions.append(f"{spec.department}: {finding.recommended_pivot}")
        avg_score += finding.viability_score

    avg_score = avg_score // max(len(findings), 1)
    final_decision = "GO" if avg_score >= 60 else ("PIVOT" if avg_score >= 40 else "NO_GO")

    summary = (
        f"Your business idea has been reviewed by {len(findings)} specialist advisors: "
        + ", ".join(spec.department for spec, _ in findings)
        + ". "
        + ("Overall, the idea shows promise for a small-scale launch but requires careful planning. "
           if final_decision == "GO" else
           "The idea needs significant changes before it is ready to launch. " if final_decision == "PIVOT" else
           "Based on current information, the idea faces too many unresolved challenges to proceed. ")
        + "Key next steps and risks are outlined below."
    )

    # Build entrepreneur-friendly artifact
    strengths_block = "\n".join(f"- {s}" for s in dedupe(all_agreements)[:6]) or "- None identified yet."
    risks_block = "\n".join(f"- {r}" for r in dedupe(all_risks)[:6]) or "- None identified yet."
    actions_block = "\n".join(f"{i}. {a}" for i, a in enumerate(dedupe(all_actions)[:5], start=1)) or "1. Gather more information before proceeding."

    missing_all: list[str] = []
    for _, finding in findings:
        missing_all.extend(finding.missing_information)
    missing_block = "\n".join(f"- {m}" for m in dedupe(missing_all)[:8]) or "- No critical missing information identified."

    artifact_body = f"""## Business Summary
{summary}

## What Looks Promising
{strengths_block}

## Major Risks
{risks_block}

## Financial Considerations
- Review your budget against the breakdown your Finance advisor outlined.
- Aim to break even within the first 3–6 months.
- Keep at least 20% of your budget as a reserve for unexpected costs.

## Recommended Approach
Start small — test with one location, build your first 20–30 loyal customers, then scale. Do not spend your full budget before validating that customers will pay consistently.

## First 5 Steps
{actions_block}

## Missing Information
{missing_block}"""

    return ExecutiveBrief(
        executive_summary=summary,
        department_agreements=dedupe(all_agreements)[:6],
        department_contradictions=dedupe(all_risks)[:6],
        final_decision=final_decision,
        action_plan=dedupe(all_actions)[:5],
        artifact_body=artifact_body,
        requires_human_approval=True,
    )


def question_targeted_trend(command: str, trends: dict[str, MetricTrend]) -> MetricTrend | None:
    """The metric the question explicitly names, if any."""
    from app.services.rag import tokenize

    asked = set(tokenize(command))
    if not asked:
        return None

    best, best_score = None, 0
    for trend in trends.values():
        vocabulary = set(tokenize(trend.key.replace("_", " ") + " " + trend.label))
        score = len(vocabulary & asked)
        if score > best_score:
            best, best_score = trend, score
    return best


def frame_executive_recommendation(
    shape: str,
    weakest: MetricTrend | None,
    contradictions: list[str],
) -> str:
    """The executive's answer, worded for the question that was asked."""
    if weakest is None:
        return (
            "No corrective action is indicated by current metrics. Direct effort at the largest "
            "opportunity identified below rather than at remediation."
        )

    label = weakest.label.lower()
    value = format_value(weakest.latest, weakest.unit)
    blocked = " Resolve the departmental contradiction above before committing either way." if contradictions else ""

    if shape == "decision":
        return (
            f"Do not commit until {label} ({value}) is accounted for in the plan. State the "
            f"threshold on {label} that would turn this into a no, and decide against that "
            f"number rather than against sentiment.{blocked}"
        )
    if shape == "cause":
        return (
            f"Treat {label} at {value} as the lead indicator and decompose it by component to "
            f"isolate the driver. The correlations named above are not proof of cause.{blocked}"
        )
    if shape == "quantity":
        return (
            f"{weakest.label} is {value}. Verify it against source records before it is quoted "
            f"externally, then set the target for next period.{blocked}"
        )
    if shape == "forecast":
        return (
            f"Project {label} forward from {value} with assumptions written down, and review the "
            f"projection against actuals next period.{blocked}"
        )
    if shape == "risk":
        return (
            f"Put a named owner and an alert threshold on {label} ({value}) this week. An "
            f"unowned risk is not a managed risk.{blocked}"
        )
    return (
        f"Prioritise {label} ({value}) before adding new commitments. Assign a named owner, set "
        f"a target for next period, and re-run this analysis against the result.{blocked}"
    )


def render_artifact(
    *,
    command: str,
    company_name: str,
    summary: str,
    recommendation: str,
    findings: list[tuple[AgentSpec, SpecialistFinding]],
    risks: list[str],
    opportunities: list[str],
    next_actions: list[str],
    health_score: int,
) -> str:
    lines = [
        f"# Executive Decision Brief — {company_name}",
        "",
        f"**Request:** {command}",
        f"**Business health score:** {health_score}/100",
        "",
        "## Summary",
        summary,
        "",
        "## Recommendation",
        recommendation,
        "",
        "## Departmental findings",
    ]
    for spec, finding in findings:
        lines += [
            "",
            f"### {spec.department} — {spec.name} ({finding.viability_score}% viability score)",
            finding.analysis,
            "",
            f"*Strengths:* {', '.join(finding.key_strengths) or 'none'}",
            f"*Recommended pivot:* {finding.recommended_pivot}",
        ]
    if risks:
        lines += ["", "## Risks"] + [f"- {r}" for r in risks[:6]]
    if opportunities:
        lines += ["", "## Opportunities"] + [f"- {o}" for o in opportunities[:6]]
    if next_actions:
        lines += ["", "## Next actions"] + [f"{i}. {a}" for i, a in enumerate(next_actions, start=1)]
    return "\n".join(lines)


def metric_owner(metric_key: str) -> str | None:
    """Which department is accountable for a metric, if any."""
    from app.agents.registry import AGENT_SPECS

    for spec in AGENT_SPECS:
        if metric_key in spec.metric_keys:
            return spec.department
    return None


def weakest_trend(trends: dict[str, MetricTrend]) -> MetricTrend | None:
    """The metric moving most adversely, accounting for inverted metrics."""
    scored = []
    for trend in trends.values():
        if trend.change_pct is None:
            continue
        adverse = -trend.change_pct if trend.key not in INVERSE_METRICS else trend.change_pct
        scored.append((adverse, trend))
    if not scored:
        return next(iter(trends.values()), None)
    scored.sort(key=lambda pair: pair[0], reverse=True)
    worst_score, worst = scored[0]
    return worst if worst_score > 0 else None


def dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(i for i in items if i))


def trim(text: str, limit: int = 80) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"
