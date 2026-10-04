"""The digital workforce roster."""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core import audit
from app.core.deps import CurrentCompany, CurrentUser, DbSession, RequireAdmin
from app.models import Agent, AgentStatus, AgentTask, WorkOrder
from app.schemas import AgentOut, AgentUpdate

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
def list_agents(company: CurrentCompany, user: CurrentUser, db: DbSession) -> list[AgentOut]:
    agents = db.execute(
        select(Agent).where(Agent.company_id == company.id).order_by(Agent.is_synthesizer, Agent.key)
    ).scalars().all()
    return [AgentOut.model_validate(_as_out(a)) for a in agents]


@router.get("/{agent_key}", response_model=AgentOut)
def get_agent(agent_key: str, company: CurrentCompany, user: CurrentUser, db: DbSession) -> AgentOut:
    agent = _lookup(db, company.id, agent_key)
    return AgentOut.model_validate(_as_out(agent))


@router.get("/{agent_key}/tasks")
def agent_tasks(agent_key: str, company: CurrentCompany, user: CurrentUser, db: DbSession, limit: int = 20):
    """Recent work this agent contributed to, newest first."""
    agent = _lookup(db, company.id, agent_key)
    rows = db.execute(
        select(AgentTask, WorkOrder)
        .join(WorkOrder, WorkOrder.id == AgentTask.work_order_id)
        .where(AgentTask.agent_id == agent.id)
        .order_by(AgentTask.created_at.desc())
        .limit(min(limit, 100))
    ).all()

    return [
        {
            "id": task.id,
            "work_order_id": order.id,
            "command": order.command,
            "status": task.status.value,
            "finding": task.finding,
            "recommended_action": task.recommended_action,
            "confidence": task.confidence,
            "evidence": task.evidence,
            "duration_ms": task.duration_ms,
            "created_at": task.created_at,
        }
        for task, order in rows
    ]


@router.patch("/{agent_key}", response_model=AgentOut)
def update_agent(
    agent_key: str,
    payload: AgentUpdate,
    company: CurrentCompany,
    user: RequireAdmin,
    db: DbSession,
) -> AgentOut:
    agent = _lookup(db, company.id, agent_key)
    changes = payload.model_dump(exclude_unset=True)

    if "status" in changes and changes["status"] is not None:
        changes["status"] = AgentStatus(changes["status"])

    for field, value in changes.items():
        setattr(agent, field, value)

    audit.record(
        db, action="agent.updated", company_id=company.id, actor=user,
        entity_type="agent", entity_id=agent.id, detail={"fields": list(changes)},
    )
    db.flush()
    return AgentOut.model_validate(_as_out(agent))


def _lookup(db, company_id: str, agent_key: str) -> Agent:
    agent = db.execute(
        select(Agent).where(Agent.company_id == company_id, Agent.key == agent_key)
    ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No agent '{agent_key}' in this workspace")
    return agent


def _as_out(agent: Agent) -> dict:
    return {
        "id": agent.id,
        "key": agent.key,
        "name": agent.name,
        "role": agent.role,
        "department": agent.department,
        "focus": agent.focus,
        "responsibilities": agent.responsibilities or [],
        "status": agent.status.value,
        "health": agent.health,
        "is_synthesizer": agent.is_synthesizer,
        "enabled": agent.enabled,
    }
