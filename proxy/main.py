"""
Staxx Proxy Gateway — Application entry point.

This is the FastAPI application that serves as a transparent reverse
proxy for LLM API calls.  Customers swap their provider base URL to
this proxy, and we forward everything while logging telemetry.

Start with::

    uvicorn proxy.main:app --host 0.0.0.0 --port 8080 --reload

Or via the ``__main__`` block at the bottom.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
import structlog
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from proxy.config import settings
from proxy.middleware.telemetry import close_telemetry, init_telemetry
from proxy.routes.anthropic_proxy import router as anthropic_router
from proxy.routes.openai_proxy import router as openai_router
from proxy.services.forwarder import close_http_client, init_http_client

# ── Structured logging setup ───────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_level_from_name(settings.log_level),
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# ── Custom exception classes ───────────────────────────────────────────

class ProxyError(Exception):
    """Base exception for proxy-specific errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UpstreamUnavailableError(ProxyError):
    """Raised when the upstream provider cannot be reached."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Upstream provider '{provider}' is unreachable.",
            status_code=502,
        )
        self.provider = provider


# ── Application lifespan ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup / shutdown of shared resources.

    Resources initialised:
      - asyncpg connection pool (Postgres — API key lookups)
      - httpx.AsyncClient (provider forwarding)
      - Redis connection (telemetry publishing)
    """
    logger.info(
        "proxy.starting",
        host=settings.host,
        port=settings.port,
        openai_base=settings.openai_base_url,
        anthropic_base=settings.anthropic_base_url,
    )

    # 1. Postgres pool for API key validation
    try:
        db_pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
        )
        app.state.db_pool = db_pool
        logger.info("proxy.postgres_pool_ready")
    except Exception:
        logger.error("proxy.postgres_pool_failed", exc_info=True)
        # If Postgres is down the proxy cannot validate keys — fail fast.
        raise

    # 2. Shared HTTP client for forwarding
    await init_http_client()

    # 3. Redis for telemetry
    await init_telemetry()

    logger.info("proxy.ready")

    yield  # ── Application runs here ──

    # Shutdown
    logger.info("proxy.shutting_down")
    await close_http_client()
    await close_telemetry()
    if db_pool:
        await db_pool.close()
    logger.info("proxy.stopped")


# ── FastAPI application ────────────────────────────────────────────────

app = FastAPI(
    title="Staxx Proxy Gateway",
    description=(
        "Transparent reverse proxy for LLM API calls.  "
        "Swap your provider base URL and Staxx captures telemetry "
        "for cost analysis and shadow evaluation."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

# CORS — permissive by default; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount provider routers
app.include_router(openai_router)
app.include_router(anthropic_router)


# ── Global exception handlers ──────────────────────────────────────────

@app.exception_handler(ProxyError)
async def proxy_error_handler(request: Request, exc: ProxyError) -> JSONResponse:
    """Return a structured JSON error for proxy-specific exceptions."""
    logger.error("proxy.error", message=exc.message, status=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.message, "type": "proxy_error"}},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — ensure the proxy never returns an HTML error page."""
    logger.error("proxy.unhandled_exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal proxy error. The request was not forwarded.",
                "type": "proxy_internal_error",
            }
        },
    )


# ── Health check ────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Basic liveness probe."""
    return {"status": "ok", "service": "staxx-proxy-gateway"}


@app.get("/ready", tags=["Health"])
async def readiness_check(request: Request) -> Response:
    """Readiness probe — verifies Postgres & Redis connectivity."""
    errors: list[str] = []

    # Postgres
    try:
        pool: asyncpg.Pool = request.app.state.db_pool
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        errors.append("postgres")

    # Redis (best effort — telemetry is optional for readiness)
    from proxy.middleware.telemetry import _redis
    if _redis is not None:
        try:
            await _redis.ping()
        except Exception:
            errors.append("redis")
    else:
        errors.append("redis")

    if errors:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "unhealthy": errors},
        )
    return JSONResponse(content={"status": "ready"})


# ── CLI entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "proxy.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
