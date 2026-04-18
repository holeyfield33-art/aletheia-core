"""Aletheia Core — Pluggable authentication layer.

Usage::

    from core.auth import get_auth_provider

    provider = get_auth_provider()       # singleton, from settings
    user = await provider.authenticate(credential)

Provider selection (``ALETHEIA_AUTH_PROVIDER`` / ``settings.auth_provider``):

    api_key  — X-API-Key header (default, full backward compat)
    oidc     — OIDC Bearer JWT validation
    saml     — SAML 2.0 Response validation
    multi    — OIDC first, then fall back to API key (migration path)
"""

from __future__ import annotations

import logging
from typing import Optional

from core.auth.base import AuthProvider
from core.auth.models import AuthContext, AuthenticatedUser, VALID_ROLES

_logger = logging.getLogger("aletheia.auth")

_instance: Optional[AuthProvider] = None


def get_auth_provider() -> AuthProvider:
    """Return the singleton auth provider based on settings."""
    global _instance
    if _instance is not None:
        return _instance

    from core.config import settings

    name = settings.auth_provider

    if name == "api_key":
        from core.auth.api_key import APIKeyAuthProvider
        _instance = APIKeyAuthProvider()
    elif name == "oidc":
        from core.auth.oidc import OIDCAuthProvider
        _instance = OIDCAuthProvider(
            issuer=settings.oidc_issuer,
            client_id=settings.oidc_client_id,
            audience=settings.oidc_audience,
            role_claim=settings.oidc_role_claim,
        )
    elif name == "saml":
        from core.auth.saml import SAMLAuthProvider
        _instance = SAMLAuthProvider(
            metadata_url=settings.saml_metadata_url,
            entity_id=settings.saml_entity_id,
            acs_url=settings.saml_acs_url,
        )
    elif name == "multi":
        _instance = _MultiAuthProvider(settings)
    else:
        raise ValueError(
            f"Unknown auth provider '{name}'. "
            f"Valid options: api_key, oidc, saml, multi."
        )

    _logger.info("Auth provider initialised: %s", name)
    return _instance


def reset_auth_provider() -> None:
    """Reset the singleton (for testing only)."""
    global _instance
    _instance = None


class _MultiAuthProvider(AuthProvider):
    """Try OIDC first, then fall back to API key.

    This is the recommended migration path for organisations adopting
    OIDC while still supporting API-key clients.
    """

    def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
        from core.auth.oidc import OIDCAuthProvider
        from core.auth.api_key import APIKeyAuthProvider

        self._oidc = OIDCAuthProvider(
            issuer=settings.oidc_issuer,
            client_id=settings.oidc_client_id,
            audience=settings.oidc_audience,
            role_claim=settings.oidc_role_claim,
        )
        self._api_key = APIKeyAuthProvider()

    async def authenticate(self, credential: str) -> Optional[AuthenticatedUser]:
        # If it looks like a JWT, try OIDC first.
        if credential and ("." in credential or credential.startswith("Bearer ")):
            user = await self._oidc.authenticate(credential)
            if user:
                return user

        # Fall back to API key.
        return await self._api_key.authenticate(credential)

    async def health_check(self) -> bool:
        # Healthy if EITHER provider works (graceful degradation).
        oidc_ok = await self._oidc.health_check()
        apikey_ok = await self._api_key.health_check()
        return oidc_ok or apikey_ok

    async def close(self) -> None:
        await self._oidc.close()
        await self._api_key.close()


__all__ = [
    "AuthProvider",
    "AuthContext",
    "AuthenticatedUser",
    "VALID_ROLES",
    "get_auth_provider",
    "reset_auth_provider",
]
