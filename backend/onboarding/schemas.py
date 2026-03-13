"""
Pydantic schemas for onboarding endpoints.
"""

from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Request to create an account and organization."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    company_name: str = Field(..., min_length=1, max_length=255)


class SignupResponse(BaseModel):
    """Response after successful signup."""
    token: str  # JWT token for auth
    api_key: str  # sk-staxx-{uuid}
    org_id: str  # UUID
    proxy_url: str  # https://proxy.staxx.ai/v1


class TestConnectionRequest(BaseModel):
    """Request to test a connection to Staxx."""
    integration_type: Literal["proxy", "sdk", "log_connector"]
    api_key: str


class TestConnectionResponse(BaseModel):
    """Response after testing connection."""
    status: Literal["connected", "pending", "failed"]
    message: str
    latency_ms: Optional[float] = None


class FirstEventDetail(BaseModel):
    """Details of the first captured LLM call."""
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    task_type: str


class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status check."""
    has_first_event: bool
    event: Optional[FirstEventDetail] = None
