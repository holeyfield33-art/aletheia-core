# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Authentication data models.

These dataclasses are the canonical types exchanged between auth
providers, RBAC middleware, and API endpoints.  They are decoupled
from any specific auth mechanism (API key, OIDC, SAML).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Valid roles in ascending privilege order.
VALID_ROLES = ("viewer", "auditor", "operator", "admin")


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity extracted from a successful authentication event.

    Attributes:
        user_id:      Unique identifier (sub claim, key ID, etc.)
        email:        User email (may be empty for service accounts)
        roles:        Set of granted roles (see ``VALID_ROLES``)
        tenant_id:    Tenant UUID (None = default / single-tenant)
        display_name: Human-readable name (optional)
        auth_method:  How the user authenticated (``api_key``, ``oidc``, ``saml``)
        raw_claims:   Full JWT / SAML claims for audit logging (never expose to clients)
    """

    user_id: str
    email: str = ""
    roles: frozenset[str] = field(default_factory=lambda: frozenset({"operator"}))
    tenant_id: Optional[str] = None
    display_name: str = ""
    auth_method: str = "api_key"
    raw_claims: dict = field(default_factory=dict, repr=False)

    @property
    def primary_role(self) -> str:
        """Return the highest-privilege role the user holds."""
        for role in reversed(VALID_ROLES):
            if role in self.roles:
                return role
        return "viewer"

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


@dataclass(frozen=True)
class AuthContext:
    """Per-request authentication context injected by the FastAPI dependency.

    Wraps ``AuthenticatedUser`` plus request-scoped metadata.
    """

    user: AuthenticatedUser
    token: str = ""  # raw Bearer token / API key (for audit, never log)
    scopes: frozenset[str] = field(default_factory=frozenset)
