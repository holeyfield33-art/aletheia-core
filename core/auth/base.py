# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Abstract auth provider interface.

Every authentication backend implements this ABC.  The runtime selects
the concrete provider via ``settings.auth_provider``.
"""

from __future__ import annotations

import abc
from typing import Optional

from core.auth.models import AuthenticatedUser


class AuthProvider(abc.ABC):
    """Abstract base class for authentication providers."""

    @abc.abstractmethod
    async def authenticate(self, credential: str) -> Optional[AuthenticatedUser]:
        """Validate *credential* (API key, Bearer JWT, SAML assertion).

        Returns ``AuthenticatedUser`` on success, ``None`` on failure.
        Implementations MUST use constant-time comparison where applicable
        and NEVER log raw credentials.
        """

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` if the provider is operational."""

    async def close(self) -> None:
        """Release resources (HTTP sessions, caches)."""
