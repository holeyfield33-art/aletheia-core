"""Aletheia Core — API-key authentication provider.

Wraps the existing X-API-Key auth logic (env-based keys + SQLite key
store) behind the ``AuthProvider`` interface so it participates in the
pluggable auth framework without any behavioural change.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from core.auth.base import AuthProvider
from core.auth.models import AuthenticatedUser

_logger = logging.getLogger("aletheia.auth.api_key")


class APIKeyAuthProvider(AuthProvider):
    """Authenticate via X-API-Key header.

    Two sources checked in priority order:

    1. **Environment keys** (``ALETHEIA_API_KEYS`` CSV) — admin / demo,
       no quota.  Role is ``operator`` by default; env keys that match
       ``ALETHEIA_ADMIN_KEY`` are promoted to ``admin``.
    2. **Key store** (SQLite) — trial / pro with monthly quota.
       Role stored in the ``role`` column (default ``operator``).
    """

    def __init__(self) -> None:
        self._env_keys: set[str] = set()
        self._reload_env_keys()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reload_env_keys(self) -> None:
        raw = os.getenv("ALETHEIA_API_KEYS", "")
        self._env_keys = {k.strip() for k in raw.split(",") if k.strip()}

    async def authenticate(self, credential: str) -> Optional[AuthenticatedUser]:
        if not credential:
            return None

        # 1. Check env-based keys (constant-time over ALL keys).
        env_matches = [
            secrets.compare_digest(credential, allowed)
            for allowed in self._env_keys
        ]
        if any(env_matches):
            # Check if this is the admin key
            admin_key = os.getenv("ALETHEIA_ADMIN_KEY", "").strip()
            is_admin = bool(admin_key and secrets.compare_digest(credential, admin_key))
            roles = frozenset({"admin", "operator"}) if is_admin else frozenset({"operator"})
            return AuthenticatedUser(
                user_id="env_key",
                roles=roles,
                auth_method="api_key",
            )

        # 2. Check SQLite key store.
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
