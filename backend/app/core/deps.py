"""Shared FastAPI dependencies: current user, company scope, role gates."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import Company, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_access_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_company(db: DbSession, user: CurrentUser) -> Company:
    company = db.get(Company, user.company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


CurrentCompany = Annotated[Company, Depends(get_current_company)]

_RANK = {UserRole.VIEWER: 0, UserRole.MEMBER: 1, UserRole.ADMIN: 2, UserRole.OWNER: 3}


def require_role(minimum: UserRole):
    """Dependency factory gating an endpoint behind a minimum role."""

    def _guard(user: CurrentUser) -> User:
        if _RANK[user.role] < _RANK[minimum]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires {minimum.value} role or higher",
            )
        return user

    return _guard


RequireMember = Annotated[User, Depends(require_role(UserRole.MEMBER))]
RequireAdmin = Annotated[User, Depends(require_role(UserRole.ADMIN))]
