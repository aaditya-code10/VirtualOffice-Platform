"""The product must stay fully functional when the LLM is unavailable."""
from unittest.mock import patch

from app.agents.registry import AGENTS_BY_KEY
from app.services import llm, orchestrator
from app.services.llm import LLMUnavailable


def test_llm_reports_unavailable_without_a_key():
    from app.config import settings
    with patch.object(settings, "gemini_api_key", None):
        assert llm.is_available() is False


def test_specialist_fails_gracefully_when_the_api_errors(client, demo):
    """When the LLM API call fails, the work order must be marked failed with an informative error message."""
    with (
        patch.object(llm, "is_available", return_value=True),
        patch.object(llm, "analyse", side_effect=LLMUnavailable("simulated outage")),
    ):
        response = client.post(
            "/api/work-orders",
            headers=demo["headers"],
            json={"command": "Assess our margin position"},
        )

    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "failed"
    assert "simulated outage" in order["error"]


def test_llm_success_creates_completed_work_order(client, demo):
    from app.services.llm import ExecutiveBrief, SpecialistFinding

    good = SpecialistFinding(
        analysis="Margins compressed 5.9 points over the period.",
        key_strengths=["Reprice legacy accounts"],
        key_risks=["Margin below plan"],
        assumptions_made=["Customers will accept 5% price increase"],
        missing_information=["Competitor renewal rates"],
        recommended_pivot="Model an 8% increase at renewal.",
        viability_score=78,
    )
    brief = ExecutiveBrief(
        executive_summary="Margin is the binding constraint.",
        department_agreements=["Need to improve margins"],
        department_contradictions=["Finance and Operations disagree on sequencing"],
        final_decision="PIVOT",
        action_plan=["Model the increase", "Pilot at renewal"],
        artifact_body="# Margin Brief\n\nDetail.",
        requires_human_approval=True,
    )

    with (
        patch.object(llm, "is_available", return_value=True),
        patch.object(llm, "analyse", return_value=(good, 1200)),
        patch.object(llm, "synthesise", return_value=(brief, 900)),
    ):
        order = client.post(
            "/api/work-orders",
            headers=demo["headers"],
            json={"command": "Assess margin and capacity"},
        ).json()

    assert order["status"] == "completed"
    assert order["engine"] == "llm"
    assert "PIVOT" in order["headline"]
    assert order["requires_approval"] is True


def test_every_agent_has_a_usable_system_prompt():
    for key, spec in AGENTS_BY_KEY.items():
        assert spec.system_prompt.strip(), f"{key} has no system prompt"
        assert "CONTEXT" in spec.system_prompt or "context" in spec.system_prompt
        assert "YOUR ROLE" in spec.system_prompt


def test_orchestrator_caps_parallel_agents(client, demo):
    """A command touching every department must not fan out unbounded."""
    order = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={
            "command": (
                "Review sales pipeline, hiring and staff attrition, gross margin and costs, "
                "marketing campaigns and CAC, operations capacity, and customer churn sentiment"
            )
        },
    ).json()

    specialists = [k for k in order["consulted_agent_keys"] if k != "strategy"]
    assert len(specialists) <= orchestrator.MAX_PARALLEL_AGENTS
