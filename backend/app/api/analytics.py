"""Analytics and metric management."""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core import audit
from app.core.deps import CurrentCompany, CurrentUser, DbSession, RequireMember
from app.models import Metric
from app.schemas import AnalyticsOut, MetricCreate, MetricOut
from app.services import analytics as analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(company: CurrentCompany, user: CurrentUser, db: DbSession) -> AnalyticsOut:
    """KPIs, trend series and the composite health score, computed from metric rows."""
    return analytics_service.build_analytics(db, company.id, company.currency)


@router.get("/metrics", response_model=list[MetricOut])
def list_metrics(company: CurrentCompany, user: CurrentUser, db: DbSession) -> list[MetricOut]:
    rows = db.execute(
        select(Metric).where(Metric.company_id == company.id).order_by(Metric.key, Metric.period)
    ).scalars().all()
    return [MetricOut.model_validate(m) for m in rows]


@router.post("/metrics", response_model=MetricOut, status_code=status.HTTP_201_CREATED)
def upsert_metric(
    payload: MetricCreate, company: CurrentCompany, user: RequireMember, db: DbSession
) -> MetricOut:
    """Record (or overwrite) one metric datapoint for a period."""
    existing = db.execute(
        select(Metric).where(
            Metric.company_id == company.id,
            Metric.key == payload.key,
            Metric.period == payload.period,
        )
    ).scalar_one_or_none()

    if existing:
        existing.value = payload.value
        existing.label = payload.label
        existing.unit = payload.unit
        existing.department = payload.department
        metric = existing
        action = "metric.updated"
    else:
        metric = Metric(company_id=company.id, **payload.model_dump())
        db.add(metric)
        action = "metric.created"

    audit.record(
        db, action=action, company_id=company.id, actor=user,
        entity_type="metric", entity_id=metric.id,
        detail={"key": payload.key, "period": payload.period, "value": payload.value},
    )
    db.flush()
    return MetricOut.model_validate(metric)


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metric(metric_id: str, company: CurrentCompany, user: RequireMember, db: DbSession) -> None:
    metric = db.execute(
        select(Metric).where(Metric.company_id == company.id, Metric.id == metric_id)
    ).scalar_one_or_none()
    if metric is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Metric not found")
    db.delete(metric)
    db.flush()
