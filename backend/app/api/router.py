from fastapi import APIRouter

from app.api.capture import router as capture_router

api_router = APIRouter()
api_router.include_router(capture_router, tags=["capture"])
