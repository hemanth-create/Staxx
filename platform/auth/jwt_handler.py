"""
JWT creation and validation using python-jose.

Tokens contain:
  sub   - user UUID (str)
  org   - org UUID (str)
  role  - user role string
  exp   - expiration timestamp
  type  - "access" or "refresh"
"""

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID

from jose import JWTError, jwt

from platform.config import settings

_ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: UUID,
    org_id: UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived access token (default 30 minutes)."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "role": role,
        "type": "access",
        "exp": _now() + delta,
        "iat": _now(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    org_id: UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a long-lived refresh token (default 7 days)."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "org": str(org_id),
        "role": role,
        "type": "refresh",
        "exp": _now() + delta,
        "iat": _now(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def decode_token(token: str, expected_type: Literal["access", "refresh"] = "access") -> dict:
    """
    Decode and validate a JWT token.

    Returns the payload dict on success.
    Raises jose.JWTError on invalid/expired tokens.
    Raises ValueError if the token type doesn't match.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
    if payload.get("type") != expected_type:
        raise ValueError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'"
        )
    return payload
