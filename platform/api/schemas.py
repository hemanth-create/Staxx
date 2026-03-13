"""
Pydantic v2 request/response schemas for the platform API.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    org_name: str = Field(min_length=1, max_length=200)
    org_slug: str = Field(min_length=2, max_length=63, pattern=r"^[a-z0-9-]+$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    org_id: Optional[UUID]
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


class OrgOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    risk_tolerance: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgUpdateRequest(BaseModel):
    name: Optional[str] = None
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = None


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


class APIKeyCreateRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=255)


class APIKeyCreateResponse(BaseModel):
    """
    Returned once at creation time.
    The full key is shown ONLY here — it is never stored or retrievable again.
    """

    id: UUID
    key: str  # full key: stx_<32 hex chars>
    key_prefix: str
    label: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyOut(BaseModel):
    """Safe representation for listing — no secret material."""

    id: UUID
    key_prefix: str
    label: Optional[str]
    created_at: datetime
    revoked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class APIKeyRevokeResponse(BaseModel):
    id: UUID
    revoked: bool


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "viewer"] = "viewer"


class InviteResponse(BaseModel):
    invitation_id: UUID
    invited_email: str
    role: str
    expires_at: datetime
    invite_url: str  # returned so the backend can pass to email sender


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


class UpgradeRequest(BaseModel):
    plan: Literal["starter", "growth", "enterprise"]


class BillingPortalResponse(BaseModel):
    portal_url: str


class UsageSummaryResponse(BaseModel):
    current_period: str
    current_usage: int
    previous_period: str
    previous_usage: int
    plan: str
    plan_limit: int  # -1 = unlimited


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    message: str
