"""API key authentication middleware.

Checks X-API-Key header on all /api/* routes.
Health-check endpoints are exempt so Docker can probe them without credentials.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from api.settings import settings

# Paths that skip auth — needed for Docker health checks and internal probes
EXEMPT_PATHS: frozenset[str] = frozenset(
    {"/api/health/live", "/api/health/ready", "/"}
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests that don't supply the correct X-API-Key header."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Skip auth entirely when a placeholder / empty key is configured
        # so devs can start the API without setting up a key first.
        if not settings.api_key or settings.api_key == "dev-key-123":
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if provided != settings.api_key:
            return JSONResponse(
                {"error": "Unauthorized — missing or invalid X-API-Key header"},
                status_code=401,
            )
        return await call_next(request)
