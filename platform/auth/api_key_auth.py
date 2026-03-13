"""
API key generation and validation.

Key format: stx_<32 hex chars>
  - Full key is shown once at creation time
  - Only the SHA-256 hash is stored in the database
  - key_prefix = first 8 chars of the hex portion (for display/identification)
"""

import hashlib
import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from platform.db.models import APIKey
from platform.db.queries import get_api_key_by_hash

_KEY_PREFIX = "stx_"
_HEX_LENGTH = 32  # 32 hex chars = 16 bytes of entropy


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        (full_key, key_hash, key_prefix)
        - full_key:   the raw key shown to the user exactly once
        - key_hash:   SHA-256 hex digest stored in the DB
        - key_prefix: first 8 hex chars (for display on key list pages)
    """
    hex_part = secrets.token_hex(_HEX_LENGTH // 2)  # token_hex(n) → 2n hex chars
    full_key = f"{_KEY_PREFIX}{hex_part}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = hex_part[:8]
    return full_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """Return SHA-256 hex digest of a raw API key string."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def validate_api_key(
    raw_key: str, db: AsyncSession
) -> APIKey | None:
    """
    Look up an API key by its hash.

    Returns the APIKey ORM object (with org_id attached) if valid and active,
    or None if not found / revoked.
    """
    key_hash = hash_api_key(raw_key)
    return await get_api_key_by_hash(db, key_hash)
