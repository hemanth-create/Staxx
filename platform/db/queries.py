"""
Async database query functions for the platform layer.

All queries that touch org-scoped data accept an explicit `org_id` parameter
to enforce row-level security at the application layer. Never query
organizations/users/api_keys without passing the caller's org_id.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from platform.db.models import APIKey, OrgInvitation, Organization, User


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


async def get_org_by_id(db: AsyncSession, org_id: UUID) -> Optional[Organization]:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    return result.scalar_one_or_none()


async def get_org_by_slug(db: AsyncSession, slug: str) -> Optional[Organization]:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    return result.scalar_one_or_none()


async def get_org_by_stripe_customer(
    db: AsyncSession, stripe_customer_id: str
) -> Optional[Organization]:
    result = await db.execute(
        select(Organization).where(
            Organization.stripe_customer_id == stripe_customer_id
        )
    )
    return result.scalar_one_or_none()


async def create_org(
    db: AsyncSession,
    name: str,
    slug: str,
    plan: str = "free",
) -> Organization:
    org = Organization(id=uuid.uuid4(), name=name, slug=slug, plan=plan)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def update_org_stripe(
    db: AsyncSession,
    org_id: UUID,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    stripe_usage_item_id: Optional[str] = None,
    plan: Optional[str] = None,
) -> None:
    values: dict = {}
    if stripe_customer_id is not None:
        values["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id is not None:
        values["stripe_subscription_id"] = stripe_subscription_id
    if stripe_usage_item_id is not None:
        values["stripe_usage_item_id"] = stripe_usage_item_id
    if plan is not None:
        values["plan"] = plan
    if not values:
        return
    await db.execute(
        update(Organization).where(Organization.id == org_id).values(**values)
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_users_by_org(db: AsyncSession, org_id: UUID) -> list[User]:
    result = await db.execute(select(User).where(User.org_id == org_id))
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    email: str,
    password_hash: str,
    org_id: Optional[UUID] = None,
    role: str = "viewer",
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=password_hash,
        org_id=org_id,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_org(
    db: AsyncSession, user_id: UUID, org_id: UUID, role: str
) -> None:
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(org_id=org_id, role=role)
    )
    await db.commit()


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


async def create_api_key(
    db: AsyncSession,
    org_id: UUID,
    key_hash: str,
    key_prefix: str,
    label: Optional[str] = None,
) -> APIKey:
    key = APIKey(
        id=uuid.uuid4(),
        org_id=org_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=label,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


async def get_api_keys_by_org(db: AsyncSession, org_id: UUID) -> list[APIKey]:
    """Returns all active (non-revoked) API keys for the org."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.org_id == org_id, APIKey.revoked_at.is_(None))
        )
    )
    return list(result.scalars().all())


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> Optional[APIKey]:
    """Looks up an active API key by its SHA-256 hash."""
    result = await db.execute(
        select(APIKey).where(
            and_(APIKey.key_hash == key_hash, APIKey.revoked_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def revoke_api_key(
    db: AsyncSession, key_id: UUID, org_id: UUID
) -> bool:
    """
    Revokes a key. Returns True if a row was updated.
    The org_id check prevents cross-tenant revocation.
    """
    result = await db.execute(
        update(APIKey)
        .where(and_(APIKey.id == key_id, APIKey.org_id == org_id, APIKey.revoked_at.is_(None)))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Org Invitations
# ---------------------------------------------------------------------------


async def create_invitation(
    db: AsyncSession,
    org_id: UUID,
    invited_email: str,
    role: str,
    token: str,
    expires_at: datetime,
) -> OrgInvitation:
    inv = OrgInvitation(
        id=uuid.uuid4(),
        org_id=org_id,
        invited_email=invited_email,
        role=role,
        token=token,
        accepted=False,
        expires_at=expires_at,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


async def get_invitation_by_token(
    db: AsyncSession, token: str
) -> Optional[OrgInvitation]:
    result = await db.execute(
        select(OrgInvitation).where(
            and_(OrgInvitation.token == token, OrgInvitation.accepted.is_(False))
        )
    )
    return result.scalar_one_or_none()


async def accept_invitation(db: AsyncSession, invitation_id: UUID) -> None:
    await db.execute(
        update(OrgInvitation)
        .where(OrgInvitation.id == invitation_id)
        .values(accepted=True)
    )
    await db.commit()
