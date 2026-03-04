from fastapi import APIRouter

from app.api.capture import router as capture_router
from cost_engine.api.router import router as cost_router

api_router = APIRouter()
api_router.include_router(capture_router, tags=["capture"])
api_router.include_router(cost_router)
