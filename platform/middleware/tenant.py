"""
Tenant isolation middleware for Staxx.

This Starlette middleware runs on every request and extracts the tenant's
org_id from either:
  1. A JWT bearer token  (Authorization: Bearer <token>)
  2. An API key header   (X-API-Key: stx_<...>)

The resolved org_id (and the auth method used) are attached to
request.state so that any downstream code can reference them
without re-parsing the token.

  request.state.org_id   → UUID | None
  request.state.auth_via → "jwt" | "api_key" | None

IMPORTANT: This middleware does NOT reject unauthenticated requests —
it only extracts tenant context when credentials are present. Actual
enforcement of authentication is done by the FastAPI dependency
functions in platform/auth/dependencies.py. This keeps the middleware
fast and free of DB calls on public routes (e.g. /health, /webhooks).
"""

import logging
from uuid import UUID

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from platform.auth.api_key_auth import hash_api_key
from platform.auth.jwt_handler import decode_token

logger = logging.getLogger(__name__)

# Routes where we intentionally skip tenant extraction to avoid overhead
_SKIP_PATHS = frozenset(
    [
        "/health",
        "/api/v1/platform/webhooks/stripe",
        "/api/v1/platform/auth/signup",
        "/api/v1/platform/auth/login",
        "/api/v1/platform/auth/refresh",
        "/api/v1/platform/org/invite/accept",
        "/docs",
        "/openapi.json",
    ]
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts org_id from JWT or API key and attaches it to request.state.

    This runs before any route handler, allowing you to use
    request.state.org_id in logging, rate-limiting, or analytics
    middleware that runs further down the stack.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Attach defaults so downstream always finds these attributes
        request.state.org_id = None
        request.state.auth_via = None

        # Skip extraction on public / webhook routes
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # --- Try JWT ---
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token, expected_type="access")
                org_raw = payload.get("org")
                if org_raw:
                    request.state.org_id = UUID(org_raw)
                    request.state.auth_via = "jwt"
            except (JWTError, ValueError):
                # Invalid token — let the route-level dependency reject it
                pass

        # --- Try API key (only if JWT didn't match) ---
        if request.state.org_id is None:
            api_key = request.headers.get("X-API-Key", "")
            if api_key:
                # We can't do a DB lookup here without an async session,
                # so we just record the hash. The dependency will validate it.
                # We signal that an API key is present so logging/rate limiting
                # middleware can treat this as a programmatic request.
                request.state.api_key_hash = hash_api_key(api_key)
                request.state.auth_via = "api_key"

        response = await call_next(request)
        return response
