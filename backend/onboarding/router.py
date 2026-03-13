"""
API routes for onboarding endpoints (database-backed).
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional

from backend.app.core.db import get_async_session
from onboarding.schemas import (
    SignupRequest,
    SignupResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    OnboardingStatusResponse,
)
from onboarding.service import (
    create_org_and_user,
    test_connection,
    get_onboarding_status,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/signup", response_model=SignupResponse)
async def signup(
    data: SignupRequest,
    db=Depends(get_async_session),
) -> SignupResponse:
    """
    Create a new organization and user account (database-backed).
    Returns JWT token and API key for onboarding.
    """
    try:
        response = await create_org_and_user(db, data)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection_endpoint(
    data: TestConnectionRequest,
    db=Depends(get_async_session),
) -> TestConnectionResponse:
    """
    Test a connection to Staxx (database-backed).
    Validates that the API key is valid and simulates data ingestion.
    """
    response, org_id = await test_connection(db, data)
    if not org_id:
        raise HTTPException(status_code=401, detail=response.message)
    return response


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(
    x_api_key: Optional[str] = Header(None),
    db=Depends(get_async_session),
) -> OnboardingStatusResponse:
    """
    Get the current onboarding status (database-backed).
    Checks if org has received first telemetry event.
    Requires X-API-Key header.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    response, is_valid = await get_onboarding_status(db, x_api_key)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return response
