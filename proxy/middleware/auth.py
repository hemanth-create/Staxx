"""
Staxx Proxy Gateway — X-Staxx-Key authentication middleware.

Validates the ``X-Staxx-Key`` header against hashed API keys in Postgres
and injects ``org_id`` into the request state for downstream handlers.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import structlog
from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)


def _hash_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest used to look up an API key in the DB."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def validate_staxx_key(request: Request) -> str:
    """FastAPI dependency that authenticates via ``X-Staxx-Key``.

    Looks up the SHA-256 hash of the provided key in the ``api_keys`` table.
    On success, stores ``org_id`` in ``request.state`` and returns it.

    Raises:
        HTTPException 401: If the header is missing, empty, or not found / revoked.
    """
    raw_key: str | None = request.headers.get("x-staxx-key")

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Staxx-Key header. Provide your Staxx API key.",
        )

    key_hash = _hash_key(raw_key)

    pool: asyncpg.Pool = request.app.state.db_pool  # set during lifespan

    row = await pool.fetchrow(
        """
        SELECT ak.org_id, o.plan
        FROM api_keys ak
        JOIN organizations o ON o.id = ak.org_id
        WHERE ak.key_hash = $1
          AND ak.revoked_at IS NULL
        """,
        key_hash,
    )

    if row is None:
        logger.warning("auth.invalid_key", key_prefix=raw_key[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked X-Staxx-Key.",
        )

    org_id = str(row["org_id"])
    request.state.org_id = org_id
    request.state.org_plan = row["plan"]

    logger.debug("auth.success", org_id=org_id)
    return org_id
