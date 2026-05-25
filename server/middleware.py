# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""HTTP middleware for the Aletheia API server.

Register these with the FastAPI app in server/app.py — order matters.
FastAPI applies middleware in LIFO order, so the last registered runs first.
"""
from __future__ import annotations

import logging
import os
import secrets
import uuid as _uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from core.auth import get_auth_provider
from core.auth.models import AuthContext

_logger = logging.getLogger("aletheia.api.middleware")

# ---------------------------------------------------------------------------
# Internal-secret guard constants
# ---------------------------------------------------------------------------

_INTERNAL_SECRET: str = os.getenv("ALETHEIA_INTERNAL_SECRET", "").strip()

# Paths exempt from the Vercel-proxy guard.
#
# The guard is only meaningful when traffic is expected to arrive exclusively
# through the Vercel edge (which injects the x-aletheia-internal header).
# Some paths must remain reachable without the proxy:
#
#  - Infra probes (/health, /ready) — called by Render, Kubernetes, etc.
#  - Public-key endpoints — downloaded by receipt verifiers and clients.
#  - OpenAPI docs — developer tooling.
#  - /v1/audit — API-SDK clients authenticate with API keys and call Render
#    directly.  Forcing them through the Vercel proxy would break the SDK.
#    Auth on /v1/audit is enforced by the _check_api_key dependency, so
#    the proxy guard provides no additional protection here.
_INTERNAL_SECRET_EXEMPT = frozenset(
    [
        "/health",
        "/ready",
        "/docs",
        "/openapi.json",
        "/metrics",
        "/.well-known/aletheia-receipt-key.pem",
        "/.well-known/aletheia-manifest-key.pem",
        "/v1/public-key",
        "/v1/audit",
    ]
)


# ---------------------------------------------------------------------------
# Security + rate limit headers
# ---------------------------------------------------------------------------


async def add_security_and_rate_limit_headers(request: Request, call_next):
    # Propagate or generate a request ID so callers can correlate log entries.
    request_id = request.headers.get("x-request-id") or str(_uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Request-ID"] = request_id
    # HSTS: two-year max-age, covers subdomains, eligible for preload.
    # Only meaningful over TLS, but safe to send on HTTP (browsers ignore it).
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    if "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'"
    )
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=()"
    )
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(
            request.state.rate_limit_remaining
        )
    if hasattr(request.state, "retry_after"):
        response.headers["Retry-After"] = str(request.state.retry_after)
    return response


# ---------------------------------------------------------------------------
# Unified auth middleware (enterprise auth layer)
# ---------------------------------------------------------------------------


async def enterprise_auth_middleware(request: Request, call_next):
    """Populate ``request.state.auth_context`` from the active auth provider.

    This middleware runs on every request. Endpoints that need auth use
    ``require_permission()`` or ``require_role()`` dependencies which read
    ``request.state.auth_context``. Unauthenticated requests get
    ``auth_context = None`` — the dependencies decide whether to reject.
    """
    unauthenticated_paths = {"/health", "/ready", "/docs", "/redoc", "/openapi.json"}
    if request.url.path in unauthenticated_paths:
        return await call_next(request)

    credential = request.headers.get("authorization", "") or request.headers.get(
        "x-api-key", ""
    )
    if credential:
        try:
            provider = get_auth_provider()
            user = await provider.authenticate(credential)
            if user:
                request.state.auth_context = AuthContext(user=user, token=credential)
        except Exception as exc:
            _logger.debug("Auth middleware error: %s", exc)

    return await call_next(request)


# ---------------------------------------------------------------------------
# Internal-secret guard — runs first (registered last in app.py)
# ---------------------------------------------------------------------------


async def internal_secret_guard(request: Request, call_next):
    """Reject /v1/* requests that did not arrive via the Vercel proxy.

    When ALETHEIA_INTERNAL_SECRET is set, every request to a guarded path
    must carry the matching ``x-aletheia-internal`` header. The Vercel
    /api/v1/* proxy injects this header automatically. Direct callers
    hitting the Render URL receive 403.

    If the env var is unset the guard is a no-op so existing deployments
    continue to work until the operator explicitly enables it.
    """
    if not _INTERNAL_SECRET:
        return await call_next(request)

    path = request.url.path
    guarded = path.startswith("/v1/") or path == "/v1"
    if not guarded or path in _INTERNAL_SECRET_EXEMPT:
        return await call_next(request)

    provided = request.headers.get("x-aletheia-internal", "")
    if not provided or not secrets.compare_digest(provided, _INTERNAL_SECRET):
        _logger.warning(  # nosemgrep
            "internal_secret_guard: rejected request path=%s xff=%s",
            path,
            request.headers.get("x-forwarded-for", "unknown"),
        )
        return JSONResponse(status_code=403, content={"error": "forbidden"})

    return await call_next(request)
