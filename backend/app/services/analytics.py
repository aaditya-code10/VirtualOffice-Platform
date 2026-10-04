"""Analytics computed from stored metric rows - nothing hardcoded."""
from __future__ import annotations

from collections import defaultdict
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Metric, WorkOrder, WorkOrderStatus
from app.schemas import AnalyticsOut, KpiOut, SeriesOut
from app.services.heuristics import MetricTrend, format_value

# KPIs surfaced on the dashboard, in display order.
HEADLINE_KEYS = ["revenue", "gross_margin", "csat", "capacity_utilisation"]


class Goal(str, Enum):
    """How a metric's value maps onto 'healthy'."""

    HIGHER = "higher"   # more is better, up to the target
    LOWER = "lower"     # less is better, target is the acceptable ceiling
    BAND = "band"       # a target band; both under- and over-shoot are unhealthy


# key -> (weight, target, goal). Weights are renormalised over whichever
# metrics a company actually reports, so partial coverage still scores fairly.
HEALTH_SPEC: dict[str, tuple[float, float, Goal]] = {
    "gross_margin":         (0.25, 70.0, Goal.HIGHER),
    "csat":                 (0.20, 90.0, Goal.HIGHER),
    "capacity_utilisation": (0.15, 80.0, Goal.BAND),
    "win_rate":             (0.15, 35.0, Goal.HIGHER),
    "churn_rate":           (0.15, 3.0,  Goal.LOWER),
    "cash_runway_months":   (0.10, 18.0, Goal.HIGHER),
    "on_time_delivery":     (0.10, 95.0, Goal.HIGHER),
    "attrition_rate":       (0.10, 12.0, Goal.LOWER),
}

# How far either side of a BAND target still counts as fully healthy, as a
# fraction of the target (0.08 -> an 80% target means 73.6%-86.4% scores 1.0).
_BAND_TOLERANCE = 0.08
# How quickly health falls off outside the band, also as a fraction of target.
# Reaching this far past the band edge scores 0.
_BAND_DECAY_SPAN = 0.35


def score_metric(value: float, target: float, goal: Goal) -> float:
    """Map a raw metric value onto 0.0-1.0 health."""
    if target <= 0:
        return 0.0

    if goal is Goal.HIGHER:
        return max(0.0, min(value / target, 1.0))

    if goal is Goal.LOWER:
        if value <= target:
            return 1.0
        # Decay from 1.0 downward as the value overshoots its ceiling.
        return max(0.0, min(target / value, 1.0))

    # BAND: full marks inside the tolerance window, linear decay outside it.
    tolerance = target * _BAND_TOLERANCE
    distance = abs(value - target)
    if distance <= tolerance:
        return 1.0
    return max(0.0, 1.0 - (distance - tolerance) / (target * _BAND_DECAY_SPAN))


def load_trends(db: Session, company_id: str) -> dict[str, MetricTrend]:
    """Build a per-metric trend view from the stored time series."""
    rows = db.execute(
        select(Metric)
        .where(Metric.company_id == company_id)
        .order_by(Metric.key, Metric.period)
    ).scalars().all()

    grouped: dict[str, list[Metric]] = defaultdict(list)
    for row in rows:
        grouped[row.key].append(row)

    trends: dict[str, MetricTrend] = {}
    for key, series in grouped.items():
        series.sort(key=lambda m: m.period)
        latest = series[-1]
        previous = series[-2] if len(series) > 1 else None
        change = None
        if previous and previous.value:
            change = (latest.value - previous.value) / abs(previous.value) * 100

        trends[key] = MetricTrend(
            key=key,
            label=latest.label,
            unit=latest.unit,
            latest=latest.value,
            previous=previous.value if previous else None,
            change_pct=round(change, 2) if change is not None else None,
            periods=len(series),
        )
    return trends


def health_score(trends: dict[str, MetricTrend]) -> int:
    """Weighted composite health, renormalised over the metrics we actually have."""
    total_weight = 0.0
    accumulated = 0.0

    for key, (weight, target, goal) in HEALTH_SPEC.items():
        trend = trends.get(key)
        if trend is None:
            continue
        accumulated += weight * score_metric(trend.latest, target, goal)
        total_weight += weight

    if not total_weight:
        return 0
    return int(round(accumulated / total_weight * 100))


def metric_sentiment(key: str, direction: str) -> str:
    """Is this movement good news? Depends on whether lower is better."""
    if direction == "flat":
        return "neutral"

    spec = HEALTH_SPEC.get(key)
    goal = spec[2] if spec else _INFERRED_GOALS.get(key)
    if goal is None:
        return "neutral"

    if goal is Goal.BAND:
        # Movement toward the target band is good; away from it is bad.
        return "neutral"

    improving = (goal is Goal.HIGHER and direction == "up") or (
        goal is Goal.LOWER and direction == "down"
    )
    return "good" if improving else "bad"


# Metrics that are not part of the health score still need a sentiment so the
# dashboard colours them honestly.
_INFERRED_GOALS: dict[str, Goal] = {
    "revenue": Goal.HIGHER,
    "pipeline": Goal.HIGHER,
    "mql": Goal.HIGHER,
    "conversion_rate": Goal.HIGHER,
    "nps": Goal.HIGHER,
    "headcount": Goal.HIGHER,
    "cac": Goal.LOWER,
    "opex": Goal.LOWER,
    "support_tickets": Goal.LOWER,
    "cycle_time_days": Goal.LOWER,
    "deal_cycle_days": Goal.LOWER,
    "utilisation": Goal.BAND,
}


def build_series(db: Session, company_id: str, keys: list[str] | None = None) -> list[SeriesOut]:
    query = select(Metric).where(Metric.company_id == company_id)
    if keys:
        query = query.where(Metric.key.in_(keys))
    rows = db.execute(query.order_by(Metric.key, Metric.period)).scalars().all()

    grouped: dict[str, list[Metric]] = defaultdict(list)
    for row in rows:
        grouped[row.key].append(row)

    out: list[SeriesOut] = []
    for key, series in grouped.items():
        series.sort(key=lambda m: m.period)
        out.append(
            SeriesOut(
                key=key,
                label=series[-1].label,
                unit=series[-1].unit,
                periods=[m.period for m in series],
                values=[m.value for m in series],
            )
        )
    out.sort(key=lambda s: HEADLINE_KEYS.index(s.key) if s.key in HEADLINE_KEYS else 99)
    return out


def work_order_stats(db: Session, company_id: str) -> dict[str, int]:
    rows = db.execute(
        select(WorkOrder.status, func.count(WorkOrder.id))
        .where(WorkOrder.company_id == company_id)
        .group_by(WorkOrder.status)
    ).all()
    stats = {status.value: 0 for status in WorkOrderStatus}
    for status, count in rows:
        key = status.value if hasattr(status, "value") else str(status)
        stats[key] = count
    stats["total"] = sum(v for k, v in stats.items() if k != "total")
    return stats


def build_analytics(db: Session, company_id: str, currency: str = "USD") -> AnalyticsOut:
    trends = load_trends(db, company_id)

    kpis: list[KpiOut] = []
    ordered_keys = [k for k in HEADLINE_KEYS if k in trends]
    ordered_keys += [k for k in trends if k not in HEADLINE_KEYS]

    for key in ordered_keys[:8]:
        trend = trends[key]
        kpis.append(
            KpiOut(
                key=key,
                label=trend.label,
                value=trend.latest,
                display=format_value(trend.latest, trend.unit, currency),
                unit=trend.unit,
                change_pct=trend.change_pct,
                direction=trend.direction,
                sentiment=metric_sentiment(key, trend.direction),
            )
        )

    return AnalyticsOut(
        currency=currency,
        kpis=kpis,
        series=build_series(db, company_id),
        health_score=health_score(trends),
        work_order_stats=work_order_stats(db, company_id),
    )
