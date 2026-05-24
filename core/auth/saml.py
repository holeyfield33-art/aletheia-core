# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — SAML 2.0 authentication provider.

Validates SAML responses and maps attributes to ``AuthenticatedUser``.
Requires ``python3-saml`` (``pip install aletheia-core[saml]``).

Configuration (via env or ``AletheiaSettings``):
    ALETHEIA_SAML_METADATA_URL  — IdP metadata endpoint
    ALETHEIA_SAML_ENTITY_ID     — SP entity ID
    ALETHEIA_SAML_ACS_URL       — Assertion Consumer Service URL

The ``authenticate()`` method expects a **Base64-encoded SAML Response**
(the POST binding value) as the *credential* parameter.

Security considerations:
    - ``strict=True`` enforces timestamp and destination checks.
    - ``wantAssertionsSigned`` and ``wantMessagesSigned`` are both required.
    - Responses exceeding ``_MAX_SAML_RESPONSE_BYTES`` are rejected before parsing
      to prevent XML expansion attacks.
    - ``http_host`` is derived from ``acs_url`` so the library can validate
      that the response destination matches the registered ACS endpoint.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Optional

from core.auth.base import AuthProvider
from core.auth.models import VALID_ROLES, AuthenticatedUser

_logger = logging.getLogger("aletheia.auth.saml")

# Reject SAML responses larger than this to guard against XML expansion attacks.
_MAX_SAML_RESPONSE_BYTES = 50_000


class SAMLAuthProvider(AuthProvider):
    """Validate SAML 2.0 responses from an enterprise IdP."""

    def __init__(
        self,
        metadata_url: str = "",
        entity_id: str = "",
        acs_url: str = "",
    ) -> None:
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "SAML auth provider requires 'python3-saml'. "
                "Install with: pip install aletheia-core[saml]"
            ) from exc

        if not metadata_url:
            raise ValueError(
                "SAML IdP metadata URL is required (ALETHEIA_SAML_METADATA_URL)."
            )
        if not entity_id:
            raise ValueError("SAML SP entity ID is required (ALETHEIA_SAML_ENTITY_ID).")
        if not acs_url:
            raise ValueError("SAML ACS URL is required (ALETHEIA_SAML_ACS_URL).")

        self._metadata_url = metadata_url
        self._entity_id = entity_id
        self._acs_url = acs_url
        self._saml_settings = self._build_settings()

    def _build_settings(self) -> dict[str, Any]:
        """Build python3-saml settings dict."""
        return {
            "strict": True,
            "sp": {
                "entityId": self._entity_id,
                "assertionConsumerService": {
                    "url": self._acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
            },
            "idp": {
                "entityId": "",  # populated from metadata
                "singleSignOnService": {"url": "", "binding": ""},
                "x509cert": "",
            },
            "security": {
                "authnRequestsSigned": False,
                # Both the outer message AND the inner assertion must be signed.
                # Requiring only assertion signatures leaves the envelope unsigned,
                # allowing wrapping attacks against IdPs that sign assertions alone.
                "wantMessagesSigned": True,
                "wantAssertionsSigned": True,
                "wantNameIdEncrypted": False,
            },
        }

    async def authenticate(self, credential: str) -> Optional[AuthenticatedUser]:
        """Validate a Base64-encoded SAML Response.

        Args:
            credential: The SAMLResponse POST parameter value.

        Returns:
            ``AuthenticatedUser`` on success, ``None`` on validation failure.
        """
        if not credential:
            return None

        # Reject oversized responses before any XML parsing.
        if len(credential.encode()) > _MAX_SAML_RESPONSE_BYTES:
            _logger.warning(
                "SAML: response exceeds size limit (%d bytes), rejecting",
                len(credential.encode()),
            )
            return None

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-untyped]

            # Derive http_host from the registered ACS URL so the library can
            # confirm the response Destination attribute matches this SP.
            # An empty http_host skips that check entirely.
            _parsed = urllib.parse.urlparse(self._acs_url)
            http_host = _parsed.netloc or _parsed.hostname or ""

            # Build the request dict expected by python3-saml.
            request_data = {
                "https": "on",
                "http_host": http_host,
                "script_name": self._acs_url,
                "post_data": {"SAMLResponse": credential},
            }

            auth = OneLogin_Saml2_Auth(request_data, old_settings=self._saml_settings)
            auth.process_response()
            errors = auth.get_errors()
            if errors:
                _logger.warning("SAML validation errors: %s", errors)
                return None

            if not auth.is_authenticated():
                return None

            attrs = auth.get_attributes()
            name_id = auth.get_nameid()

            # Map SAML attributes to AuthenticatedUser fields.
            role = (attrs.get("aletheia_role") or ["operator"])[0]
            if role not in VALID_ROLES:
                role = "operator"

            email = (attrs.get("email") or attrs.get("mail") or [name_id])[0]
            tenant_id = (
                attrs.get("tenant_id") or attrs.get("aletheia_tenant") or [None]
            )[0]
            display_name = (attrs.get("displayName") or attrs.get("cn") or [""])[0]

            return AuthenticatedUser(
                user_id=name_id,
                email=email,
                roles=frozenset({role}),
                tenant_id=tenant_id,
                display_name=display_name,
                auth_method="saml",
                raw_claims=dict(attrs),
            )
        except ImportError:
            raise
        except Exception as exc:
            _logger.debug("SAML authentication failed: %s", exc)
            return None

    async def health_check(self) -> bool:
        """Verify IdP metadata is reachable."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(self._metadata_url)
                return resp.status_code == 200
        except Exception:
            return False
