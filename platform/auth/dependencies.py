"""
FastAPI dependency functions for authentication and authorization.

Usage in route handlers:

    @router.get("/me")
    async def get_me(user: CurrentUser):
        ...

    @router.post("/keys")
    async def create_key(org: CurrentOrg, _: OwnerOrAdmin):
        ...

    # API key auth (for proxy / SDK endpoints):
    @router.post("/track")
    async def track(org: OrgFromAPIKey):
        ...
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from platform.auth.api_key_auth import validate_api_key
from platform.auth.jwt_handler import decode_token
from platform.db.models import Organization, User
from platform.db.queries import get_org_by_id, get_user_by_id

# Reuse the backend's DB session dependency
from app.core.db import get_db

_bearer = HTTPBearer(auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# JWT-based auth
# ---------------------------------------------------------------------------


async def get_current_user(
    db: DBSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(_bearer)
    ] = None,
) -> User:
    """
    Extract and validate the JWT bearer token.
    Returns the authenticated User ORM object.
    Raises HTTP 401 on any failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await get_user_by_id(db, UUID(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_org(user: CurrentUser, db: DBSession) -> Organization:
    """
    Return the Organization the current user belongs to.
    Raises HTTP 403 if the user has no org yet (e.g. fresh signup without an org).
    """
    if user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization",
        )
    org = await get_org_by_id(db, user.org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization not found")
    return org


CurrentOrg = Annotated[Organization, Depends(get_current_org)]


# ---------------------------------------------------------------------------
# Role guards — compose on top of CurrentUser
# ---------------------------------------------------------------------------


def _require_roles(*allowed_roles: str):
    """Factory that returns a dependency enforcing role membership."""

    async def _check(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {allowed_roles}. You have: {user.role}",
            )
        return user

    return Depends(_check)


# Pre-built role guards
OwnerOnly = _require_roles("owner")
OwnerOrAdmin = _require_roles("owner", "admin")
AnyMember = _require_roles("owner", "admin", "viewer")


# ---------------------------------------------------------------------------
# API key auth (for proxy / SDK / programmatic access)
# ---------------------------------------------------------------------------


async def get_org_from_api_key(
    db: DBSession,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Organization:
    """
    Validate the X-API-Key header and return the associated Organization.
    Raises HTTP 401 if the key is missing, invalid, or revoked.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
        )
    api_key_record = await validate_api_key(x_api_key, db)
    if api_key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )
    org = await get_org_by_id(db, api_key_record.org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization associated with this API key no longer exists",
        )
    return org


OrgFromAPIKey = Annotated[Organization, Depends(get_org_from_api_key)]


# ---------------------------------------------------------------------------
# Flexible auth: accepts EITHER a JWT bearer token OR an API key
# ---------------------------------------------------------------------------


async def get_org_from_jwt_or_api_key(
    db: DBSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(_bearer)
    ] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Organization:
    """
    Dual-mode auth dependency.
    Tries JWT first; falls back to API key.
    Used on endpoints accessible by both dashboard users and SDK/proxy clients.
    """
    # Try JWT
    if credentials is not None:
        try:
            payload = decode_token(credentials.credentials, expected_type="access")
            org_id = payload.get("org")
            if org_id:
                org = await get_org_by_id(db, UUID(org_id))
                if org:
                    return org
        except (JWTError, ValueError):
            pass  # fall through to API key check

    # Try API key
    if x_api_key:
        api_key_record = await validate_api_key(x_api_key, db)
        if api_key_record:
            org = await get_org_by_id(db, api_key_record.org_id)
            if org:
                return org

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid JWT bearer token or X-API-Key header required",
        headers={"WWW-Authenticate": "Bearer"},
    )


OrgFromJWTOrAPIKey = Annotated[Organization, Depends(get_org_from_jwt_or_api_key)]
