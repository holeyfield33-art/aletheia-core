# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""FastAPI Depends() functions for auth and rate limiting."""
from __future__ import annotations

import logging
import os

from fastapi import Header, HTTPException, Request

from core.auth.api_key_flow import authenticate_api_key
from core.auth.api_key_validation import raise_for_quota_failure, resolve_api_key
from core.auth.models import AuthContext
from core.auth.rbac import Permission, has_permission
from core.config import env_bool
from core.key_store import key_store
from core.rate_limit import eval_rate_limiter
from server._bridge import _check_hosted_prisma_api_key, _lookup_hosted_api_key_user_id
from server._helpers import _get_client_ip

_logger = logging.getLogger("aletheia.api")

# ALETHEIA_AUTH_DISABLED only takes effect when the runtime explicitly
# identifies itself as a dev/test environment. An unset or misspelled
# ENVIRONMENT now fails closed (auth required) instead of silently
# bypassing on the assumption "not production = safe".
_DEV_ENVIRONMENTS = {"development", "dev", "test", "testing", "local"}


def _auth_bypass_allowed() -> bool:
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    if env in _DEV_ENVIRONMENTS:
        return True
    # Pytest-driven runs are always dev — covers conftest setups that
    # rely on ALETHEIA_AUTH_DISABLED without setting ENVIRONMENT.
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


async def _check_api_key(
    request: Request, x_api_key: str | None = Header(default=None)
) -> None:
    """Dependency: validate X-API-Key header and enforce quota.

    Also accepts enterprise auth (OIDC/SAML) when the auth middleware
    has already populated ``request.state.auth_context`` with a user
    holding the ``audit:submit`` permission.

    Auth is REQUIRED by default. To explicitly disable (dev only),
    set ALETHEIA_AUTH_DISABLED=true. This never works in production.

    Keys are authenticated exclusively via the KeyStore (SQLite/Postgres).
    Environment-variable keys (ALETHEIA_API_KEYS) are no longer accepted.
    """
    ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    if ctx is not None and has_permission(ctx.user.roles, Permission.AUDIT_SUBMIT):
        return

    if env_bool("ALETHEIA_AUTH_DISABLED") and _auth_bypass_allowed():
        return

    headers = getattr(request, "headers", {})
    auth_header = headers.get("authorization", "") if headers is not None else ""
    api_key = resolve_api_key(x_api_key, auth_header)

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Valid X-API-Key required."},
        )

    auth_result = await authenticate_api_key(
        api_key,
        key_store=key_store,
        hosted_quota_checker=_check_hosted_prisma_api_key,
        hosted_user_lookup=_lookup_hosted_api_key_user_id,
        logger=_logger,
    )
    if auth_result.user_id:
        request.state.api_user_id = auth_result.user_id
    quota = auth_result.quota
    if quota.allowed:
        return
    raise_for_quota_failure(quota)


async def _check_eval_rate_limit(request: Request) -> None:
    """FastAPI dependency: enforce per-IP rate limit on /v1/evaluate.

    Limits are read from environment at startup:
      EVAL_RATE_LIMIT_PER_MINUTE  (default 20)
      EVAL_RATE_BURST             (default 5)
    """
    client_ip = _get_client_ip(request)
    allowed, retry_after = await eval_rate_limiter.allow(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds",
            headers={"Retry-After": str(retry_after)},
        )
