"""Routing, multi-agent execution, approvals and reports."""
from app.agents.registry import needs_approval, route_command


def test_routing_picks_relevant_departments():
    routes = route_command("Why did our gross margin fall?")
    assert "finance" in routes
    assert "business_strategy" in routes
    assert "market_research" in routes


def test_routing_includes_all_consulting_specialists():
    ranked = route_command("Our churn rate and customer sentiment are both falling")
    assert "market_research" in ranked
    assert "marketing" in ranked


def test_routing_falls_back_for_vague_commands():
    assert len(route_command("What should we do next?")) == 4


def test_approval_triggers():
    assert needs_approval("Launch a discount campaign next month")
    assert needs_approval("Should we hire more staff?")
    assert not needs_approval("Summarise last quarter's customer sentiment")


def test_orchestrated_work_order_consults_multiple_agents(client, demo):
    response = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Churn is rising while our delivery capacity is maxed out. What should we do?"},
    )
    assert response.status_code == 201, response.text
    order = response.json()

    assert order["status"] == "completed"
    assert order["progress"] == 100
    assert order["mode"] == "orchestrated"
    assert order["engine"] in {"heuristic", "hybrid", "llm"}

    # Specialists plus the strategy synthesiser.
    assert len(order["consulted_agent_keys"]) >= 2
    assert "strategy" in order["consulted_agent_keys"]
    assert len(order["tasks"]) == len(order["consulted_agent_keys"])

    assert order["summary"]
    assert order["recommendation"]
    assert order["artifact_body"].startswith("#")
    assert 0 < order["confidence"] <= 100


def test_findings_are_grounded_in_actual_metrics(client, demo):
    """The engine must cite findings from the specialist agents."""
    order = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Assess our financial position"},
    ).json()

    task = next((t for t in order["tasks"] if t["agent_key"] in {"finance", "business_strategy"}), None)
    assert task is not None
    assert task["finding"]


def test_direct_work_order_targets_one_agent(client, demo):
    order = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Give me a finance read on this quarter", "agent_key": "finance"},
    ).json()

    assert order["mode"] == "direct"
    assert order["target_agent_key"] == "finance"
    assert len(order["tasks"]) == 1
    assert order["tasks"][0]["agent_key"] == "finance"


def test_unknown_agent_is_rejected(client, demo):
    response = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Do something", "agent_key": "janitor"},
    )
    assert response.status_code == 400


def test_work_order_cites_knowledge_base(client, demo):
    order = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "What does our QBR say about implementation capacity and churn?"},
    ).json()
    assert order["citations"], "expected citations from the indexed QBR document"
    assert all("filename" in c and "excerpt" in c for c in order["citations"])


def test_resource_committing_command_raises_an_approval(client, demo):
    order = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Should we hire three implementation engineers and launch a pricing change?"},
    ).json()
    assert order["requires_approval"] is True

    approvals = client.get("/api/approvals", headers=demo["headers"]).json()
    linked = [a for a in approvals if a["work_order_id"] == order["id"]]
    assert linked, "an approval should have been created for this work order"
    assert linked[0]["status"] == "PENDING"


def test_read_only_command_does_not_raise_an_approval():
    assert needs_approval("Summarise our customer sentiment trend") is False
    assert needs_approval("Analyze the competitive landscape") is False


def test_approval_decision_flow(client, demo):
    order = client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Approve budget to hire two engineers"},
    ).json()

    approval = next(
        a for a in client.get("/api/approvals", headers=demo["headers"]).json()
        if a["work_order_id"] == order["id"]
    )

    decided = client.post(
        f"/api/approvals/{approval['id']}/decision",
        headers=demo["headers"],
        json={"decision": "approve", "comment": "Agreed - proceed with two hires."},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "APPROVED"
    assert decided.json()["comment"].startswith("Agreed")

    # A second decision on the same approval is a conflict, not a silent overwrite.
    again = client.post(
        f"/api/approvals/{approval['id']}/decision",
        headers=demo["headers"],
        json={"decision": "reject"},
    )
    assert again.status_code == 409


def test_reports_derive_from_completed_work_orders(client, demo):
    client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Give me an executive read on margin and churn"},
    )
    reports = client.get("/api/reports", headers=demo["headers"]).json()
    assert reports

    report = reports[0]
    assert report["findings"]
    assert report["summary"]
    assert report["code"].startswith("BRIEF /")

    export = client.get(f"/api/reports/{report['id']}/export", headers=demo["headers"])
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    assert export.text.startswith("#")


def test_routing_preview_does_not_execute(client, demo):
    before = len(client.get("/api/work-orders", headers=demo["headers"]).json())

    preview = client.get(
        "/api/work-orders/preview",
        params={"command": "Should we cut prices to reduce churn?"},
        headers=demo["headers"],
    ).json()

    assert preview["requires_approval"] is True
    assert [a["key"] for a in preview["agents"]]

    after = len(client.get("/api/work-orders", headers=demo["headers"]).json())
    assert before == after


def test_audit_trail_records_execution(client, demo):
    client.post(
        "/api/work-orders",
        headers=demo["headers"],
        json={"command": "Audit trail check on operations"},
    )
    events = client.get("/api/audit", headers=demo["headers"]).json()
    assert any(e["action"] == "work_order.executed" for e in events)
