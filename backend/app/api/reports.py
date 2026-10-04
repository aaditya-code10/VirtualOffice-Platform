"""Executive reports derived from completed work orders."""
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.agents.registry import AGENTS_BY_KEY
from app.core.deps import CurrentCompany, CurrentUser, DbSession
from app.models import AgentTask, Approval, ApprovalStatus, WorkOrder, WorkOrderStatus
from app.schemas import ReportFinding, ReportOut
from app.services import analytics as analytics_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(
    company: CurrentCompany,
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> list[ReportOut]:
    """One report per completed orchestrated work order, newest first."""
    orders = db.execute(
        select(WorkOrder)
        .where(
            WorkOrder.company_id == company.id,
            WorkOrder.status == WorkOrderStatus.COMPLETED,
        )
        .order_by(WorkOrder.created_at.desc())
        .limit(limit)
    ).scalars().all()

    health = analytics_service.health_score(analytics_service.load_trends(db, company.id))
    return [_to_report(db, order, health) for order in orders]


@router.get("/{work_order_id}", response_model=ReportOut)
def get_report(
    work_order_id: str, company: CurrentCompany, user: CurrentUser, db: DbSession
) -> ReportOut:
    order = _lookup(db, company.id, work_order_id)
    health = analytics_service.health_score(analytics_service.load_trends(db, company.id))
    return _to_report(db, order, health)


@router.get("/{work_order_id}/export", response_class=PlainTextResponse)
def export_report(
    work_order_id: str, company: CurrentCompany, user: CurrentUser, db: DbSession
) -> PlainTextResponse:
    """Download the decision brief as Markdown."""
    order = _lookup(db, company.id, work_order_id)
    body = order.artifact_body or order.summary or "(No artifact was produced for this work order.)"
    filename = f"{order.id}.md"
    return PlainTextResponse(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _lookup(db, company_id: str, work_order_id: str) -> WorkOrder:
    order = db.execute(
        select(WorkOrder).where(WorkOrder.company_id == company_id, WorkOrder.id == work_order_id)
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return order


def _to_report(db, order: WorkOrder, health: int) -> ReportOut:
    tasks = db.execute(
        select(AgentTask).where(AgentTask.work_order_id == order.id).order_by(AgentTask.created_at)
    ).scalars().all()

    approval = db.execute(
        select(Approval).where(Approval.work_order_id == order.id).order_by(Approval.created_at.desc())
    ).scalars().first()

    if approval:
        report_status = (
            "HUMAN REVIEW REQUIRED"
            if approval.status == ApprovalStatus.PENDING
            else approval.status.value
        )
    else:
        report_status = "NO APPROVAL REQUIRED"

    findings = []
    for task in tasks:
        spec = AGENTS_BY_KEY.get(task.agent_key)
        findings.append(
            ReportFinding(
                department=spec.department if spec else task.agent_key.upper(),
                agent=spec.name if spec else task.agent_key,
                text=task.finding or "",
                confidence=task.confidence,
            )
        )

    return ReportOut(
        id=order.id,
        code=f"BRIEF / {order.id.split('_')[-1].upper()}",
        title=order.artifact_title or f"Brief: {order.command[:60]}",
        date=order.completed_at or order.created_at,
        summary=order.summary or "",
        recommendation=order.recommendation,
        health_score=order.confidence or health,
        status=report_status,
        engine=order.engine,
        findings=findings,
        risks=order.risks or [],
        opportunities=order.opportunities or [],
        next_actions=order.next_actions or [],
        citations=order.citations or [],
    )
