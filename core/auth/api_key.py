# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — API-key authentication provider.

Authenticates via the KeyStore (SQLite/Postgres).  Environment-variable
keys (ALETHEIA_API_KEYS) are **no longer accepted** — they bypassed
hashing, quotas, and audit trails.  KeyStore is the only auth source.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.auth.base import AuthProvider
from core.auth.models import AuthenticatedUser

_logger = logging.getLogger("aletheia.auth.api_key")


class APIKeyAuthProvider(AuthProvider):
    """Authenticate via X-API-Key header using KeyStore only.

    KeyStore (SQLite/Postgres) is the sole authentication source.
    Environment-variable keys (ALETHEIA_API_KEYS) are rejected — they
    bypassed hashing, quotas, and the audit trail.
    """

    def __init__(self) -> None:
        # Fail-fast: refuse to start if env keys are configured in production
        raw_env_keys = os.getenv("ALETHEIA_API_KEYS", "").strip()
        if raw_env_keys and os.getenv("ENVIRONMENT", "").lower() == "production":
            raise RuntimeError(
                "FATAL: ALETHEIA_API_KEYS environment variable is set in production. "
                "Environment-based API keys are no longer supported — they bypass "
                "hashing, quotas, and audit trails. Use the KeyStore (POST /v1/keys) "
                "to provision API keys. Remove ALETHEIA_API_KEYS to proceed."
            )
        if raw_env_keys:
            _logger.warning(
                "ALETHEIA_API_KEYS is set but will be IGNORED. "
                "Environment-based API keys are deprecated. "
                "Use the KeyStore (POST /v1/keys) to provision keys."
            )

    async def authenticate(self, credential: str) -> Optional[AuthenticatedUser]:
        if not credential:
            return None

        # Authenticate via KeyStore only.
        from core.key_store import key_store

        quota = key_store.check_and_increment(credential)
        if quota.allowed:
            record = key_store.lookup_by_hash(credential)
            role = getattr(record, "role", "operator") if record else "operator"
            user_id = record.id if record else "unknown"
            return AuthenticatedUser(
                user_id=user_id,
                roles=frozenset({role}),
                auth_method="api_key",
            )

        # Authentication failed.
        return None

    async def health_check(self) -> bool:
        return True
