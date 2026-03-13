"""
Platform API router.

Mounts under /api/v1/platform (or wherever the FastAPI app includes it).

Endpoints:
  POST   /auth/signup                     Create org + owner account
  POST   /auth/login                      Get JWT tokens
  POST   /auth/refresh                    Refresh access token
  GET    /auth/me                         Current user info

  GET    /org                             Get current org
  PATCH  /org                             Update org settings (owner/admin)

  GET    /org/members                     List org members
  POST   /org/invite                      Invite user (owner only)
  POST   /org/invite/accept               Accept invitation (no auth required)

  GET    /org/keys                        List API keys
  POST   /org/keys                        Create API key
  DELETE /org/keys/{key_id}               Revoke API key

  GET    /billing/usage                   Usage summary
  POST   /billing/upgrade                 Upgrade plan (creates/updates Stripe sub)
  GET    /billing/portal                  Stripe billing portal URL
  POST   /webhooks/stripe                 Stripe webhook receiver
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from platform.api.schemas import (
    AcceptInviteRequest,
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyOut,
    APIKeyRevokeResponse,
    BillingPortalResponse,
    InviteRequest,
    InviteResponse,
    LoginRequest,
    MessageResponse,
    OrgOut,
    OrgUpdateRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UpgradeRequest,
    UsageSummaryResponse,
    UserOut,
)
from platform.auth.api_key_auth import generate_api_key
from platform.auth.dependencies import (
    AnyMember,
    CurrentOrg,
    CurrentUser,
    OwnerOnly,
    OwnerOrAdmin,
)
from platform.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from platform.auth.password import hash_password, verify_password
from platform.billing.stripe_client import (
    PLAN_LIMITS,
    create_billing_portal_session,
    create_stripe_customer,
    create_subscription,
    update_subscription_plan,
)
from platform.billing.usage_tracker import get_usage_summary
from platform.billing.webhooks import handle_stripe_webhook
from platform.config import settings
from platform.db.models import Organization, User
from platform.db.queries import (
    accept_invitation,
    create_api_key,
    create_invitation,
    create_org,
    create_user,
    get_api_keys_by_org,
    get_invitation_by_token,
    get_org_by_id,
    get_org_by_slug,
    get_user_by_email,
    get_users_by_org,
    revoke_api_key,
    update_org_stripe,
    update_user_org,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["platform"])
DBDep = Depends(get_db)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = DBDep):
    """
    Create a new organization and owner account in one shot.
    Returns JWT tokens so the user is immediately logged in.
    """
    # Uniqueness checks
    if await get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if await get_org_by_slug(db, body.org_slug):
        raise HTTPException(status.HTTP_409_CONFLICT, "Org slug already taken")

    # Create org first
    org = await create_org(db, name=body.org_name, slug=body.org_slug, plan="free")

    # Create owner user
    user = await create_user(
        db,
        email=body.email,
        password_hash=hash_password(body.password),
        org_id=org.id,
        role="owner",
    )

    # Issue tokens
    access = create_access_token(user.id, org.id, user.role)
    refresh = create_refresh_token(user.id, org.id, user.role)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = DBDep):
    user = await get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if user.org_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no associated organization")

    access = create_access_token(user.id, user.org_id, user.role)
    refresh = create_refresh_token(user.id, user.org_id, user.role)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_tokens(body: RefreshRequest, db: AsyncSession = DBDep):
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc

    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org"])
    role = payload["role"]

    # Validate user still exists
    from platform.db.queries import get_user_by_id
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    access = create_access_token(user_id, org_id, role)
    refresh = create_refresh_token(user_id, org_id, role)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/auth/me", response_model=UserOut)
async def get_me(user: CurrentUser):
    return user


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


@router.get("/org", response_model=OrgOut)
async def get_org(org: CurrentOrg):
    return org


@router.patch("/org", response_model=OrgOut)
async def update_org(
    body: OrgUpdateRequest,
    org: CurrentOrg,
    _: OwnerOrAdmin,
    db: AsyncSession = DBDep,
):
    if body.name is not None:
        org.name = body.name
    if body.risk_tolerance is not None:
        org.risk_tolerance = body.risk_tolerance
    await db.commit()
    await db.refresh(org)
    return org


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/org/members", response_model=list[UserOut])
async def list_members(org: CurrentOrg, _: AnyMember, db: AsyncSession = DBDep):
    return await get_users_by_org(db, org.id)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post("/org/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    body: InviteRequest,
    org: CurrentOrg,
    _: OwnerOnly,
    db: AsyncSession = DBDep,
):
    # Prevent double-inviting an existing member
    existing = await get_user_by_email(db, body.email)
    if existing and existing.org_id == org.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this org")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.INVITATION_EXPIRE_HOURS
    )
    inv = await create_invitation(
        db,
        org_id=org.id,
        invited_email=body.email,
        role=body.role,
        token=token,
        expires_at=expires_at,
    )
    invite_url = f"{settings.APP_BASE_URL}/accept-invite?token={token}"

    # NOTE: Plug in your email provider here (SendGrid, SES, Resend, etc.)
    # await send_invite_email(to=body.email, invite_url=invite_url, org_name=org.name)

    return InviteResponse(
        invitation_id=inv.id,
        invited_email=body.email,
        role=body.role,
        expires_at=expires_at,
        invite_url=invite_url,
    )


@router.post("/org/invite/accept", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def accept_invite(body: AcceptInviteRequest, db: AsyncSession = DBDep):
    inv = await get_invitation_by_token(db, body.token)
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or already used invitation token")
    if inv.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "Invitation has expired")

    # Create user account (or assign to existing account)
    existing_user = await get_user_by_email(db, inv.invited_email)
    if existing_user:
        # User already has an account — update their org membership
        await update_user_org(db, existing_user.id, inv.org_id, inv.role)
        user = existing_user
    else:
        user = await create_user(
            db,
            email=inv.invited_email,
            password_hash=hash_password(body.password),
            org_id=inv.org_id,
            role=inv.role,
        )

    await accept_invitation(db, inv.id)

    access = create_access_token(user.id, inv.org_id, inv.role)
    refresh = create_refresh_token(user.id, inv.org_id, inv.role)
    return TokenResponse(access_token=access, refresh_token=refresh)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@router.get("/org/keys", response_model=list[APIKeyOut])
async def list_api_keys(org: CurrentOrg, _: OwnerOrAdmin, db: AsyncSession = DBDep):
    return await get_api_keys_by_org(db, org.id)


@router.post(
    "/org/keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_key(
    body: APIKeyCreateRequest,
    org: CurrentOrg,
    _: OwnerOrAdmin,
    db: AsyncSession = DBDep,
):
    full_key, key_hash, key_prefix = generate_api_key()
    key_record = await create_api_key(
        db,
        org_id=org.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=body.label,
    )
    return APIKeyCreateResponse(
        id=key_record.id,
        key=full_key,  # shown exactly once
        key_prefix=key_prefix,
        label=key_record.label,
        created_at=key_record.created_at,
    )


@router.delete("/org/keys/{key_id}", response_model=APIKeyRevokeResponse)
async def revoke_key(
    key_id: UUID,
    org: CurrentOrg,
    _: OwnerOrAdmin,
    db: AsyncSession = DBDep,
):
    revoked = await revoke_api_key(db, key_id=key_id, org_id=org.id)
    if not revoked:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "API key not found or already revoked",
        )
    return APIKeyRevokeResponse(id=key_id, revoked=True)


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


@router.get("/billing/usage", response_model=UsageSummaryResponse)
async def usage_summary(org: CurrentOrg, _: AnyMember):
    summary = await get_usage_summary(org.id)
    limit = PLAN_LIMITS.get(org.plan, 10_000)
    return UsageSummaryResponse(
        **summary,
        plan=org.plan,
        plan_limit=limit,
    )


@router.post("/billing/upgrade", response_model=OrgOut)
async def upgrade_plan(
    body: UpgradeRequest,
    org: CurrentOrg,
    user: CurrentUser,
    _: OwnerOnly,
    db: AsyncSession = DBDep,
):
    if org.plan == body.plan:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Already on the '{body.plan}' plan")

    # Create Stripe customer if this is the first paid plan
    customer_id = org.stripe_customer_id
    if not customer_id:
        customer_id = await create_stripe_customer(org.id, org.name, user.email)
        await update_org_stripe(db, org.id, stripe_customer_id=customer_id)

    if org.stripe_subscription_id:
        # Modify existing subscription
        sub_id, usage_item_id = await update_subscription_plan(
            org.stripe_subscription_id, body.plan
        )
    else:
        # Create new subscription
        sub_id, usage_item_id = await create_subscription(customer_id, body.plan)

    await update_org_stripe(
        db,
        org.id,
        stripe_subscription_id=sub_id,
        stripe_usage_item_id=usage_item_id,
        plan=body.plan,
    )

    updated_org = await get_org_by_id(db, org.id)
    return updated_org


@router.get("/billing/portal", response_model=BillingPortalResponse)
async def billing_portal(org: CurrentOrg, _: OwnerOnly):
    if not org.stripe_customer_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No Stripe customer associated with this org. Upgrade to a paid plan first.",
        )
    return_url = f"{settings.APP_BASE_URL}/settings/billing"
    portal_url = await create_billing_portal_session(org.stripe_customer_id, return_url)
    return BillingPortalResponse(portal_url=portal_url)


# ---------------------------------------------------------------------------
# Stripe Webhook
# ---------------------------------------------------------------------------


@router.post("/webhooks/stripe", response_model=MessageResponse)
async def stripe_webhook(request: Request, db: AsyncSession = DBDep):
    result = await handle_stripe_webhook(request, db)
    return MessageResponse(message=result["status"])
