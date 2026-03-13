from fastapi import APIRouter

from app.api.capture import router as capture_router
from cost_engine.api.router import router as cost_router
from platform.api.router import router as platform_router
from recommendations.api.router import (
    roi_router,
    router as recommendations_router,
)
from alerts.api.router import router as alerts_router
from onboarding.router import router as onboarding_router

api_router = APIRouter()
api_router.include_router(capture_router, tags=["capture"])
api_router.include_router(cost_router)
api_router.include_router(recommendations_router)
api_router.include_router(roi_router)
api_router.include_router(alerts_router)
api_router.include_router(platform_router)
api_router.include_router(onboarding_router)
