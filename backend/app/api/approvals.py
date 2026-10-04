"""Human-in-the-loop approval queue."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core import audit
from app.core.deps import CurrentCompany, CurrentUser, DbSession, RequireAdmin
from app.models import Approval, ApprovalStatus, utcnow
from app.schemas import ApprovalDecision, ApprovalOut

router = APIRouter(prefix="/approvals", tags=["approvals"])

_DECISION_MAP = {
    "approve": ApprovalStatus.APPROVED,
    "reject": ApprovalStatus.REJECTED,
    "changes": ApprovalStatus.CHANGES_REQUESTED,
}


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    company: CurrentCompany,
    user: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[ApprovalOut]:
    query = select(Approval).where(Approval.company_id == company.id)
    if status_filter:
        try:
            query = query.where(Approval.status == ApprovalStatus(status_filter.upper()))
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown status '{status_filter}'") from exc

    approvals = db.execute(query.order_by(Approval.created_at.desc())).scalars().all()
    return [ApprovalOut.model_validate(_out(a)) for a in approvals]


@router.post("/{approval_id}/decision", response_model=ApprovalOut)
def decide(
    approval_id: str,
    payload: ApprovalDecision,
    company: CurrentCompany,
    user: RequireAdmin,
    db: DbSession,
) -> ApprovalOut:
    approval = db.execute(
        select(Approval).where(Approval.company_id == company.id, Approval.id == approval_id)
    ).scalar_one_or_none()
    if approval is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This approval was already {approval.status.value.lower()}",
        )

    approval.status = _DECISION_MAP[payload.decision]
    approval.comment = payload.comment
    approval.decided_by_id = user.id
    approval.decided_at = utcnow()

    audit.record(
        db, action=f"approval.{payload.decision}", company_id=company.id, actor=user,
        entity_type="approval", entity_id=approval.id,
        detail={"work_order_id": approval.work_order_id, "comment": payload.comment},
    )
    db.flush()
    return ApprovalOut.model_validate(_out(approval))


def _out(a: Approval) -> dict:
    return {
        "id": a.id, "work_order_id": a.work_order_id, "title": a.title,
        "description": a.description, "risk": a.risk.value, "owner": a.owner,
        "expected_impact": a.expected_impact, "status": a.status.value, "comment": a.comment,
        "created_at": a.created_at, "decided_at": a.decided_at,
    }
