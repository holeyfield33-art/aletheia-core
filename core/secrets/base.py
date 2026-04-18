"""Aletheia Core — Abstract secret manager interface.

All secret backends implement this ABC.  The runtime selects the
concrete implementation via ``ALETHEIA_SECRET_BACKEND`` (default: ``env``).

Design notes
------------
* Every method is ``async`` so cloud backends (Vault, AWS, Azure, GCP)
  can use non-blocking I/O without callers caring.
* ``get_secret`` returns ``None`` for missing keys — never raises.
* ``health_check`` is used by ``/ready`` to surface backend connectivity
  problems before they become silent auth failures.
"""

from __future__ import annotations

import abc
from typing import Optional


class SecretManager(abc.ABC):
    """Abstract base for pluggable secret-manager backends."""

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret value by key.  Returns ``None`` if not found."""

    @abc.abstractmethod
    async def set_secret(self, key: str, value: str) -> None:
        """Store or overwrite a secret value."""

    @abc.abstractmethod
    async def delete_secret(self, key: str) -> None:
        """Delete a secret.  No-op if the key does not exist."""

    @abc.abstractmethod
    async def list_secrets(self, prefix: str = "") -> list[str]:
        """Return secret *names* (not values) matching an optional prefix."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` if the backend is reachable and authenticated."""

    async def close(self) -> None:
        """Release any resources held by the backend (connections, sessions)."""

    # ------------------------------------------------------------------
    # Optional convenience
    # ------------------------------------------------------------------

    async def get_secret_or_default(self, key: str, default: str = "") -> str:
        """Like ``get_secret`` but returns *default* instead of ``None``."""
        val = await self.get_secret(key)
        return val if val is not None else default
