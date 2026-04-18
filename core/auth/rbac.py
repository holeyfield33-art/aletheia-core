"""Aletheia Core — Role-Based Access Control (RBAC).

Defines a static permission matrix mapping roles to allowed operations.
The ``require_role()`` function returns a FastAPI dependency that rejects
requests from users lacking the required role.

Roles (ascending privilege):
    viewer    — read-only dashboard access
    auditor   — read logs, keys, metrics
    operator  — submit audit requests, view keys
    admin     — full access: key management, rotation, tenant ops
"""

from __future__ import annotations

import enum
import logging
from typing import Callable

from fastapi import Depends, HTTPException, Request

from core.auth.models import AuthContext, VALID_ROLES

_logger = logging.getLogger("aletheia.auth.rbac")


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class Permission(str, enum.Enum):
    """Named operations that can be guarded by RBAC."""
    AUDIT_SUBMIT = "audit:submit"
    AUDIT_READ = "audit:read"
    KEYS_CREATE = "keys:create"
    KEYS_LIST = "keys:list"
    KEYS_REVOKE = "keys:revoke"
    KEYS_USAGE = "keys:usage"
    SECRETS_ROTATE = "secrets:rotate"
    METRICS_READ = "metrics:read"
    HEALTH_FULL = "health:full"
    TENANT_MANAGE = "tenant:manage"


# Static permission matrix — intentionally not DB-driven to avoid
# privilege escalation via data-plane tampering.
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer": frozenset({
        Permission.KEYS_LIST,
    }),
    "auditor": frozenset({
        Permission.AUDIT_READ,
        Permission.KEYS_LIST,
        Permission.KEYS_USAGE,
        Permission.METRICS_READ,
        Permission.HEALTH_FULL,
    }),
    "operator": frozenset({
        Permission.AUDIT_SUBMIT,
        Permission.AUDIT_READ,
        Permission.KEYS_LIST,
        Permission.KEYS_USAGE,
        Permission.METRICS_READ,
        Permission.HEALTH_FULL,
    }),
    "admin": frozenset(Permission),  # all permissions
}


def has_permission(roles: frozenset[str], permission: Permission) -> bool:
    """Check if any of the user's roles grant *permission*."""
    for role in roles:
        if permission in ROLE_PERMISSIONS.get(role, frozenset()):
            return True
    return False


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------

def require_permission(permission: Permission) -> Callable:
    """Return a FastAPI dependency that enforces *permission*.

    Usage::

        @app.post("/v1/keys", dependencies=[Depends(require_permission(Permission.KEYS_CREATE))])
        async def create_key(...): ...

    The dependency reads ``request.state.auth_context`` which is set by
    the unified auth middleware in ``bridge/fastapi_wrapper.py``.
    """
    async def _check(request: Request) -> None:
        ctx: AuthContext | None = getattr(request.state, "auth_context", None)
        if ctx is None:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Authentication required."},
            )
        if not has_permission(ctx.user.roles, permission):
            _logger.warning(
                "RBAC denied: user=%s roles=%s needs=%s",
                ctx.user.user_id, ctx.user.roles, permission.value,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "message": f"Insufficient permissions. Required: {permission.value}",
                },
            )
    return _check


def require_role(*roles: str) -> Callable:
    """Return a FastAPI dependency that requires the user to hold at
    least one of the specified *roles*.

    Usage::

        @app.delete("/v1/keys/{id}", dependencies=[Depends(require_role("admin"))])
    """
    allowed = frozenset(roles)

    async def _check(request: Request) -> None:
        ctx: AuthContext | None = getattr(request.state, "auth_context", None)
        if ctx is None:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Authentication required."},
            )
        if not ctx.user.roles & allowed:
            _logger.warning(
                "RBAC denied: user=%s roles=%s required_any=%s",
                ctx.user.user_id, ctx.user.roles, allowed,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "message": f"Required role: {' or '.join(sorted(allowed))}",
                },
            )
    return _check
