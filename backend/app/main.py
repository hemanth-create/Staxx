import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: connect to DB, Redis, etc.
    logger.info("Starting up `%s` API...", settings.PROJECT_NAME)
    yield
    # Shutdown logic
    logger.info("Shutting down `%s` API...", settings.PROJECT_NAME)


from app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check() -> dict:
    """
    Basic health check endpoint.
    """
    return {"status": "healthy"}
