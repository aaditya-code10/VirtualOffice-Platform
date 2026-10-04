"""Audit trail."""
from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentCompany, DbSession, RequireAdmin
from app.models import AuditEvent
from app.schemas import AuditEventOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_events(
    company: CurrentCompany,
    user: RequireAdmin,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = None,
) -> list[AuditEventOut]:
    query = select(AuditEvent).where(AuditEvent.company_id == company.id)
    if action:
        query = query.where(AuditEvent.action == action)

    events = db.execute(query.order_by(AuditEvent.at.desc()).limit(limit)).scalars().all()
    return [AuditEventOut.model_validate(e) for e in events]
