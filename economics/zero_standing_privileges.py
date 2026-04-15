"""Gate E1 — Zero Standing Privileges.

Every request must explicitly declare the resources it requires.
No session carries implicit authority — each call is evaluated
from a zero-trust baseline.

Integrates with the existing policy manifest for resource allowlists.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

_logger = logging.getLogger("aletheia.economics.zsp")


@dataclass(frozen=True)
class RequestPrivileges:
    """Resources a request declares it needs."""
    required_resources: tuple[str, ...] = ()

    @classmethod
    def from_list(cls, resources: list[str] | None) -> "RequestPrivileges":
        if not resources:
            return cls()
        return cls(required_resources=tuple(resources))


@dataclass
class ZSPDecision:
    """Result of a ZSP enforcement check."""
    allowed: bool
    reason: str = ""


class ZSPEnforcer:
    """Zero Standing Privileges enforcer.

    Principles:
    - No implicit inheritance between requests.
    - Every request must declare what it needs.
    - Undeclared requests are rejected.
    - Resource allowlists are checked against the policy manifest.
    """

    def __init__(self, allowed_resources: set[str] | None = None) -> None:
        self._allowed_resources: set[str] = allowed_resources or set()
        self._violations: int = 0

    def enforce(
        self,
        session_id: str,
        privileges: RequestPrivileges,
    ) -> ZSPDecision:
        """Check whether the declared privileges are permitted.

        Returns ``ZSPDecision(allowed=True)`` if the request is
        acceptable, or ``ZSPDecision(allowed=False, reason=...)``
        if it violates ZSP policy.
        """
        if not privileges.required_resources:
            self._violations += 1
            _logger.warning(
                "ZSP violation: session=%s declared no resources", session_id
            )
            return ZSPDecision(
                allowed=False,
                reason="ZSP: Request must declare at least one required resource.",
            )

        if self._allowed_resources:
            denied = [
                r for r in privileges.required_resources
                if r not in self._allowed_resources
            ]
            if denied:
                self._violations += 1
                _logger.warning(
                    "ZSP violation: session=%s requested disallowed resources: %s",
                    session_id,
                    denied,
                )
                return ZSPDecision(
                    allowed=False,
                    reason=f"ZSP: Disallowed resources: {denied}",
                )

        return ZSPDecision(allowed=True)

    @property
    def violation_count(self) -> int:
        return self._violations
