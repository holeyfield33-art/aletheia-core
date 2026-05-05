# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Environment-variable secret backend (default).

This is the zero-dependency backend that preserves full backward
compatibility with existing deployments.  Secrets are read from
``os.environ`` exactly as before; ``set_secret`` writes back to the
process environment (useful for hot rotation via ``/v1/rotate``).
"""

from __future__ import annotations

import os
from typing import Optional

from core.secrets.base import SecretManager


class EnvSecretManager(SecretManager):
    """Read secrets from process environment variables.

    This is the default backend (``ALETHEIA_SECRET_BACKEND=env``).
    Existing deployments that use env vars or mounted secret files
    continue to work without any configuration change.
    """

    # Prefix applied when looking up keys.  Allows callers to use
    # short names (``receipt_secret``) while the real env var is
    # ``ALETHEIA_RECEIPT_SECRET``.
    _PREFIX = "ALETHEIA_"

    def _env_key(self, key: str) -> str:
        """Normalise *key* to the expected env-var name."""
        upper = key.upper()
        if upper.startswith(self._PREFIX):
            return upper
        return f"{self._PREFIX}{upper}"

    async def get_secret(self, key: str) -> Optional[str]:
        val = os.environ.get(self._env_key(key), "").strip()
        return val if val else None

    async def set_secret(self, key: str, value: str) -> None:
        os.environ[self._env_key(key)] = value

    async def delete_secret(self, key: str) -> None:
        os.environ.pop(self._env_key(key), None)

    async def list_secrets(self, prefix: str = "") -> list[str]:
        full_prefix = self._env_key(prefix) if prefix else self._PREFIX
        return sorted(k for k in os.environ if k.startswith(full_prefix))

    async def health_check(self) -> bool:
        # Environment is always available.
        return True
