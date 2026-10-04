"""Anthropic-backed reasoning layer.

The orchestrator calls :func:`analyse` for specialist agents and :func:`synthesise`
for the executive agent. Both return validated Pydantic objects via the SDK's
structured-output support, so the rest of the application never parses free text.

If no ``ANTHROPIC_API_KEY`` is configured - or the API errors - the caller falls
back to the deterministic engine in ``app.services.heuristics``. That keeps the
product fully functional offline while making the LLM path a drop-in upgrade.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Structured output contracts
# --------------------------------------------------------------------------- #
class SpecialistFinding(BaseModel):
    """What one department agent returns for a work order."""

    analysis: str = Field(description="Detailed perspective on the business idea grounded in the provided context.")
    key_strengths: list[str] = Field(default_factory=list, description="What works well in this domain.")
    key_risks: list[str] = Field(default_factory=list, description="Primary vulnerabilities, each under 20 words.")
    assumptions_made: list[str] = Field(default_factory=list, description="What you are assuming about the idea.")
    missing_information: list[str] = Field(default_factory=list, description="What we still need to know.")
    recommended_pivot: str = Field(description="One specific suggested tweak to the idea to make it better.")
    viability_score: int = Field(ge=0, le=100, description="How viable this specific domain is given the evidence.")


class ExecutiveBrief(BaseModel):
    """What the strategy agent returns after reconciling specialist findings."""

    executive_summary: str = Field(description="High-level overview of the proposed business idea's viability.")
    department_agreements: list[str] = Field(default_factory=list, description="Where the experts aligned.")
    department_contradictions: list[str] = Field(default_factory=list, description="Where experts disagreed and how it was resolved.")
    final_decision: str = Field(description="Must be exactly: GO, NO_GO, or PIVOT.")
    action_plan: list[str] = Field(default_factory=list, description="Ordered, concrete next steps for launching or pivoting.")
    artifact_body: str = Field(description="Markdown decision brief an executive could act on directly.")
    requires_human_approval: bool = Field(
        description="True when the recommendation commits money or resources."
    )


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
from app.services import gemini_service
from app.services.gemini_service import LLMUnavailable

def is_available() -> bool:
    return gemini_service.is_available()

def _parse(system: str, user: str, schema: type[BaseModel]) -> tuple[BaseModel, int]:
    """One structured-output request. Returns (parsed, tokens_used)."""
    return gemini_service.parse(system, user, schema)

# --------------------------------------------------------------------------- #
# Prompt assembly
# --------------------------------------------------------------------------- #
def build_specialist_prompt(
    *,
    command: str,
    context_block: str,
) -> str:
    return f"""
BUSINESS IDEA / REQUEST SUBMITTED BY ENTREPRENEUR
{command}

{('BUSINESS PLAN & CONTEXT FROM UPLOADED DOCUMENTS:\n' + context_block) if context_block.strip() else '(No additional business documents were provided.)'}

IMPORTANT RULES:
- If an attached business document or PDF is present above, thoroughly examine all details mentioned in it (e.g. business model, target audience, pricing, operations, curriculum/services, financials). Ground your analysis directly in these provided details.
- Analyze ONLY the business idea and attached documents described above.
- Do NOT reference any internal company databases, health scores, or unrelated corporate metrics.
- If key information is missing (e.g. exact budget, team size, experience), clearly list it under missing_information.
- Distinguish between facts stated by the user or PDF, your assumptions, and your estimates.
- Use simple, practical language that a first-time entrepreneur can understand.
- Do NOT use jargon like "principal exposure", "threshold breach", "named owner", "instrument strategy", etc.

Analyze this business from your specialist perspective and provide a practical, grounded assessment.
""".strip()


def build_synthesis_prompt(
    *,
    command: str,
    specialist_block: str,
    extra_context: str = "",
) -> str:
    context_section = f"\n\nDOCUMENT CONTEXT & DETAILS:\n{extra_context}\n" if extra_context.strip() else ""
    return f"""
BUSINESS IDEA SUBMITTED BY ENTREPRENEUR
{command}
{context_section}
SPECIALIST ANALYSES TO SYNTHESIZE
{specialist_block}

Your task is to write ONE clear, entrepreneur-friendly consulting recommendation.

You MUST structure your artifact_body using these exact headings:
## Business Summary
## What Looks Promising
## Major Risks
## Financial Considerations
## Recommended Approach
## First 5 Steps
## Missing Information

Rules:
- If a business document or PDF was provided, directly integrate and cite its key numbers, assumptions, and business offerings.
- Do NOT simply copy-paste what the specialists said. Reason across their findings.
- If specialists contradict each other (e.g., Finance says budget is too low but Marketing suggests expensive ads), call out the contradiction and make a ruling.
- Do NOT reference Northwind Logistics, internal metrics, health scores, or any unrelated company data.
- Use simple, clear language a college student can understand.
- Avoid jargon like "principal exposure", "composite health score", "instrument metrics", "alert threshold", "named owner".
- final_decision must be exactly: GO, NO_GO, or PIVOT.
- Set requires_human_approval to true since this recommendation involves committing real money.
""".strip()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def analyse(system_prompt: str, user_prompt: str) -> tuple[SpecialistFinding, int]:
    parsed, tokens = _parse(system_prompt, user_prompt, SpecialistFinding)
    return parsed, tokens  # type: ignore[return-value]


def synthesise(system_prompt: str, user_prompt: str) -> tuple[ExecutiveBrief, int]:
    parsed, tokens = _parse(system_prompt, user_prompt, ExecutiveBrief)
    return parsed, tokens  # type: ignore[return-value]
