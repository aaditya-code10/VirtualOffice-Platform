"""API surface: one router mounted under the configured prefix."""
from fastapi import APIRouter

from app.api import agents, analytics, approvals, audit, auth, company, knowledge, reports, work_orders

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(agents.router)
api_router.include_router(knowledge.router)
api_router.include_router(work_orders.router)
api_router.include_router(approvals.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
