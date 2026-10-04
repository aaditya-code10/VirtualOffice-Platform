"""Registration, login, and current-user endpoints."""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.core import audit
from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Company, User, UserRole, utcnow
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.seed import ensure_agents, unique_slug

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    """Create a company plus its owner account and full agent roster."""
    email = payload.email.lower().strip()
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists")

    company = Company(
        name=payload.company_name.strip(),
        slug=unique_slug(db, payload.company_name),
        industry=payload.industry,
    )
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=UserRole.OWNER,
        last_login_at=utcnow(),
    )
    db.add(user)
    ensure_agents(db, company)

    audit.record(
        db, action="auth.register", company_id=company.id, actor=user,
        entity_type="company", entity_id=company.id, detail={"company": company.name},
    )
    db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, {"company_id": company.id, "role": user.role.value}),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(_as_out(user)),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        # Same message either way - do not reveal which accounts exist.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")

    user.last_login_at = utcnow()
    audit.record(db, action="auth.login", company_id=user.company_id, actor=user)
    db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, {"company_id": user.company_id, "role": user.role.value}),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(_as_out(user)),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(_as_out(user))


def _as_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "company_id": user.company_id,
        "last_login_at": user.last_login_at,
    }
