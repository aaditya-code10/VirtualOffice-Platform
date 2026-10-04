"""Company profile (the 'digital twin' the agents reason about)."""
from fastapi import APIRouter

from app.core import audit
from app.core.deps import CurrentCompany, DbSession, RequireAdmin
from app.schemas import CompanyOut, CompanyUpdate

router = APIRouter(prefix="/company", tags=["company"])


@router.get("", response_model=CompanyOut)
def get_company(company: CurrentCompany) -> CompanyOut:
    return CompanyOut.model_validate(company)


@router.patch("", response_model=CompanyOut)
def update_company(
    payload: CompanyUpdate,
    company: CurrentCompany,
    user: RequireAdmin,
    db: DbSession,
) -> CompanyOut:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(company, field, value)

    # Filling in the profile completes onboarding.
    if company.industry and company.target_market and company.primary_goal:
        company.onboarding_complete = True

    audit.record(
        db, action="company.updated", company_id=company.id, actor=user,
        entity_type="company", entity_id=company.id, detail={"fields": list(changes)},
    )
    db.flush()
    return CompanyOut.model_validate(company)
