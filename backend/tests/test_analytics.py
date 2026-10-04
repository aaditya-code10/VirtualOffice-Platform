"""Metric-derived analytics and the composite health score."""
from app.services.analytics import Goal, health_score, score_metric
from app.services.heuristics import MetricTrend


def _trend(key, value, label="X", unit="percent", change=None):
    return MetricTrend(
        key=key, label=label, unit=unit, latest=value,
        previous=None, change_pct=change, periods=2,
    )


def test_score_metric_higher_is_better():
    assert score_metric(70, 70, Goal.HIGHER) == 1.0
    assert score_metric(35, 70, Goal.HIGHER) == 0.5
    assert score_metric(140, 70, Goal.HIGHER) == 1.0  # capped, never rewards overshoot


def test_score_metric_lower_is_better():
    assert score_metric(3, 3, Goal.LOWER) == 1.0
    assert score_metric(1, 3, Goal.LOWER) == 1.0
    assert score_metric(6, 3, Goal.LOWER) == 0.5


def test_score_metric_band_penalises_both_directions():
    assert score_metric(80, 80, Goal.BAND) == 1.0
    over = score_metric(95, 80, Goal.BAND)
    under = score_metric(60, 80, Goal.BAND)
    assert 0 < over < 1
    assert 0 <= under < 1


def test_health_score_renormalises_over_available_metrics():
    """A company reporting only one perfect metric scores 100, not 25."""
    assert health_score({"gross_margin": _trend("gross_margin", 70)}) == 100
    assert health_score({}) == 0


def test_health_score_reflects_deterioration():
    healthy = {
        "gross_margin": _trend("gross_margin", 70),
        "churn_rate": _trend("churn_rate", 2.0),
        "csat": _trend("csat", 90, unit="score"),
    }
    struggling = {
        "gross_margin": _trend("gross_margin", 45),
        "churn_rate": _trend("churn_rate", 9.0),
        "csat": _trend("csat", 55, unit="score"),
    }
    assert health_score(healthy) > health_score(struggling)
    assert health_score(healthy) == 100
    assert health_score(struggling) < 65


def test_analytics_endpoint_computes_from_metric_rows(client, demo):
    body = client.get("/api/analytics", headers=demo["headers"]).json()

    assert 0 < body["health_score"] <= 100
    assert body["kpis"], "seeded metrics should produce KPIs"

    revenue = next(k for k in body["kpis"] if k["key"] == "revenue")
    assert revenue["change_pct"] is not None
    assert revenue["direction"] == "up"
    assert revenue["display"].startswith("$")

    margin = next(k for k in body["kpis"] if k["key"] == "gross_margin")
    assert margin["direction"] == "down"


def test_metric_upsert_changes_analytics(client, registered):
    headers = registered["headers"]
    assert client.get("/api/analytics", headers=headers).json()["health_score"] == 0

    for period, value in (("2026-01", 40.0), ("2026-02", 70.0)):
        response = client.post(
            "/api/metrics",
            headers=headers,
            json={
                "key": "gross_margin", "label": "Gross Margin",
                "period": period, "value": value, "unit": "percent",
            },
        )
        assert response.status_code == 201

    body = client.get("/api/analytics", headers=headers).json()
    assert body["health_score"] == 100

    kpi = next(k for k in body["kpis"] if k["key"] == "gross_margin")
    assert kpi["change_pct"] == 75.0  # 40 -> 70
    assert kpi["direction"] == "up"

    # Upserting the same key/period overwrites rather than duplicating.
    client.post(
        "/api/metrics",
        headers=headers,
        json={"key": "gross_margin", "label": "Gross Margin",
              "period": "2026-02", "value": 35.0, "unit": "percent"},
    )
    metrics = client.get("/api/metrics", headers=headers).json()
    assert len([m for m in metrics if m["key"] == "gross_margin"]) == 2
