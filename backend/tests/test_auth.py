"""Authentication, tenancy isolation and role gating."""


def test_register_creates_company_and_agent_roster(client, registered):
    agents = client.get("/api/agents", headers=registered["headers"]).json()
    assert len(agents) == 5
    assert {a["key"] for a in agents} == {
        "business_strategy", "market_research", "finance", "marketing", "strategy"
    }
    assert sum(1 for a in agents if a["is_synthesizer"]) == 1


def test_duplicate_email_rejected(client, registered):
    response = client.post(
        "/api/auth/register",
        json={
            "email": registered["email"],
            "password": "anotherpassword",
            "full_name": "Impostor",
            "company_name": "Other Co",
        },
    )
    assert response.status_code == 409


def test_login_roundtrip_and_me(client, registered):
    response = client.post(
        "/api/auth/login",
        json={"email": registered["email"], "password": registered["password"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == registered["email"]


def test_wrong_password_is_rejected_without_leaking_existence(client, registered):
    known = client.post(
        "/api/auth/login", json={"email": registered["email"], "password": "wrongwrong"}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrongwrong"}
    )
    assert known.status_code == unknown.status_code == 401
    assert known.json()["detail"] == unknown.json()["detail"]


def test_endpoints_require_authentication(client):
    for path in ("/api/company", "/api/agents", "/api/analytics", "/api/work-orders"):
        assert client.get(path).status_code == 401


def test_tenant_isolation(client, registered):
    """A second company must not see the first company's work orders."""
    client.post(
        "/api/work-orders",
        headers=registered["headers"],
        json={"command": "Review our margin structure"},
    )

    other = client.post(
        "/api/auth/register",
        json={
            "email": "rival@example.com",
            "password": "supersecret1",
            "full_name": "Rival",
            "company_name": "Rival Inc",
        },
    ).json()
    rival_headers = {"Authorization": f"Bearer {other['access_token']}"}

    mine = client.get("/api/work-orders", headers=registered["headers"]).json()
    theirs = client.get("/api/work-orders", headers=rival_headers).json()

    assert len(mine) >= 1
    assert theirs == []
