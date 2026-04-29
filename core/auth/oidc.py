"""Aletheia Core — OIDC (OpenID Connect) authentication provider.

Validates Bearer JWT tokens against an OIDC discovery endpoint.
Supports Okta, Auth0, Azure AD, Keycloak, and any spec-compliant IdP.

Requires ``authlib`` (``pip install aletheia-core[oidc]``).

Configuration (via ``AletheiaSettings`` / env vars):
    ALETHEIA_OIDC_ISSUER       — OIDC issuer URL (required)
    ALETHEIA_OIDC_CLIENT_ID    — Client ID registered with IdP
    ALETHEIA_OIDC_AUDIENCE     — Expected ``aud`` claim (defaults to client ID)
    ALETHEIA_OIDC_ROLE_CLAIM   — JWT claim carrying the Aletheia role
                                 (default ``aletheia_role``)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from core.auth.base import AuthProvider
from core.auth.models import VALID_ROLES, AuthenticatedUser

_logger = logging.getLogger("aletheia.auth.oidc")

# JWKS cache TTL — 1 hour.  Keeps things fast while still rotating.
_JWKS_CACHE_TTL = 3600


class OIDCAuthProvider(AuthProvider):
    """Validate OIDC Bearer JWTs against the IdP JWKS endpoint."""

    def __init__(
        self,
        issuer: str,
        client_id: str = "",
        audience: str = "",
        role_claim: str = "aletheia_role",
    ) -> None:
        try:
            from authlib.jose import JsonWebToken, JsonWebKey  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "OIDC auth provider requires 'authlib'. "
                "Install with: pip install aletheia-core[oidc]"
            ) from exc

        if not issuer:
            raise ValueError("OIDC issuer URL is required (ALETHEIA_OIDC_ISSUER).")

        self._issuer = issuer.rstrip("/")
        self._client_id = client_id
        self._audience = audience or client_id
        self._role_claim = role_claim

        self._jwt = JsonWebToken(["RS256", "ES256", "PS256"])
        self._jwk_cls = JsonWebKey

        # JWKS cache
        self._jwks: Any = None
        self._jwks_fetched_at: float = 0.0

        # Discovery endpoint
        self._discovery_url = f"{self._issuer}/.well-known/openid-configuration"
        self._jwks_uri: str = ""

    async def _fetch_jwks(self) -> Any:
        """Fetch (or return cached) JWKS from the IdP."""
        now = time.time()
        if self._jwks and (now - self._jwks_fetched_at) < _JWKS_CACHE_TTL:
            return self._jwks

        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            if not self._jwks_uri:
                disc = await client.get(self._discovery_url)
                disc.raise_for_status()
                self._jwks_uri = disc.json()["jwks_uri"]

            resp = await client.get(self._jwks_uri)
            resp.raise_for_status()
            self._jwks = self._jwk_cls.import_key_set(resp.json())
            self._jwks_fetched_at = now
            _logger.debug("JWKS refreshed from %s", self._jwks_uri)
            return self._jwks

    async def authenticate(self, credential: str) -> Optional[AuthenticatedUser]:
        """Validate a Bearer JWT and return an ``AuthenticatedUser``."""
        if not credential:
            return None

        # Strip "Bearer " prefix if present.
        token = credential.removeprefix("Bearer ").strip()
        if not token:
            return None

        try:
            jwks = await self._fetch_jwks()
            claims = self._jwt.decode(token, jwks)

            # Standard validations.
            claims.validate()

            # Issuer check.
            if claims.get("iss") != self._issuer:
                _logger.warning("OIDC: issuer mismatch: got %s", claims.get("iss"))
                return None

            # Audience check.
            aud = claims.get("aud", "")
            if isinstance(aud, list):
                if self._audience and self._audience not in aud:
                    _logger.warning("OIDC: audience mismatch: got %s", aud)
                    return None
            elif self._audience and aud != self._audience:
                _logger.warning("OIDC: audience mismatch: got %s", aud)
                return None

            # Extract role.
            role = claims.get(self._role_claim, "operator")
            if role not in VALID_ROLES:
                _logger.warning(
                    "OIDC: unknown role claim '%s', defaulting to operator", role
                )
                role = "operator"

            tenant_id = claims.get("tenant_id") or claims.get("aletheia_tenant")

            return AuthenticatedUser(
                user_id=claims["sub"],
                email=claims.get("email", ""),
                roles=frozenset({role}),
                tenant_id=tenant_id,
                display_name=claims.get("name", ""),
                auth_method="oidc",
                raw_claims=dict(claims),
            )
        except Exception as exc:
            _logger.debug("OIDC authentication failed: %s", exc)
            return None

    async def health_check(self) -> bool:
        """Verify IdP discovery endpoint is reachable."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(self._discovery_url)
                return resp.status_code == 200
        except Exception:
            return False
