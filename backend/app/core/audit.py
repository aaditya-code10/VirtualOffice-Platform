"""Audit trail helper."""
from sqlalchemy.orm import Session

from app.models import AuditEvent, User


def record(
    db: Session,
    *,
    action: str,
    company_id: str | None = None,
    actor: User | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    detail: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        company_id=company_id or (actor.company_id if actor else None),
        actor_id=actor.id if actor else None,
        actor_label=actor.email if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
    )
    db.add(event)
    return event
