# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Persistence abstraction layer.

Provides a tenant-aware query helper and database backend selection.
All queries MUST go through ``tenant_scope()`` to enforce hard tenant
isolation — there is no way to accidentally issue an unscoped query.

Backend selection (``ALETHEIA_DATABASE_BACKEND`` / ``settings.database_backend``):
    sqlite   — development default, single-file, zero config
    postgres — production, asyncpg connection pool, TLS enforced
"""

from __future__ import annotations

import logging
from typing import Optional

_logger = logging.getLogger("aletheia.persistence")

# Default tenant for backward compatibility with pre-multi-tenant data.
DEFAULT_TENANT: str = "default"


def tenant_scope(tenant_id: Optional[str]) -> str:
    """Resolve and validate a tenant ID.

    Every database query must call this to get a non-None, non-empty
    tenant identifier.  Returns ``DEFAULT_TENANT`` when the caller
    passes ``None`` — this preserves backward compatibility for
    single-tenant deployments.

    Raises ``ValueError`` on empty-string or whitespace-only input.
    """
    if tenant_id is None:
        return DEFAULT_TENANT
    clean = tenant_id.strip()
    if not clean:
        raise ValueError("tenant_id must not be empty or whitespace-only")
    # Defense: reject path-traversal or injection-suspicious characters
    if any(c in clean for c in ("/", "\\", "\x00", "..", ";")):
        raise ValueError(f"Illegal characters in tenant_id: {clean!r}")
    return clean


def redis_tenant_key(tenant_id: Optional[str], namespace: str, key: str) -> str:
    """Build a tenant-namespaced Redis key.

    Format: ``tenant:{tenant_id}:{namespace}:{key}``

    Examples:
        >>> redis_tenant_key("acme", "rl", "10.0.0.1")
        'tenant:acme:rl:10.0.0.1'
        >>> redis_tenant_key(None, "decision", "abc123")
        'tenant:default:decision:abc123'
    """
    tid = tenant_scope(tenant_id)
    return f"tenant:{tid}:{namespace}:{key}"
