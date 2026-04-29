"""Aletheia Core — Sovereign Relay Module.

Layer 3: Governor only — can PREVENT actions, cannot GENERATE them.
READ-ONLY observer that enforces policies and red-line safety.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .safety_bounds import SafetyBounds
from .spectral_monitor import SpectralHealth, SpectralMonitor
from .identity_anchor import IdentityAnchor, DecisionReceipt


@dataclass
class PolicyConfig:
    """Deployment-configurable policy settings."""

    spectral_minimum: float = 0.50
    blocked_action_types: list[str] = field(
        default_factory=lambda: [
            "delete_all",
            "drop_database",
            "exfiltrate",
            "disable_audit",
            "disable_logging",
            "modify_policy",
        ]
    )
    require_constitutional_check: bool = True
    max_payload_length: int = 10_000

    @classmethod
    def default(cls) -> PolicyConfig:
        """Create default policy config."""
        return cls()


@dataclass
class Action:
    """Proposed action for evaluation."""

    type: str
    description: str
    payload: str
    session_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelayDecision:
    """Result of relay evaluation."""

    approved: bool
    reason: str | None  # None if approved, violation string if vetoed
    spectral_state: SpectralHealth | None
    policy_violations: list[str]
    timestamp: datetime


@dataclass
class RelayStatus:
    """Current status of the relay."""

    active: bool
    spectral_health: SpectralHealth | None
    decisions_made: int
    vetoes_issued: int
    uptime_seconds: float


class SovereignRelay:
    """Layer 3: Sovereign relay that enforces governance policies."""

    def __init__(
        self,
        monitor: SpectralMonitor,
        anchor: IdentityAnchor,
        policy: PolicyConfig | None = None,
        safety: SafetyBounds | None = None,
    ):
        """Initialize sovereign relay.

        Args:
            monitor: Spectral health monitor
            anchor: Identity anchor for decision logging
            policy: Policy configuration (default if None)
            safety: Safety bounds enforcer (default if None)
        """
        self._monitor = monitor
        self._anchor = anchor
        self._policy = policy or PolicyConfig.default()
        self._safety = safety or SafetyBounds()
        self._active = True
        self._decisions_made = 0
        self._vetoes_issued = 0
        self._start_time = datetime.now(timezone.utc)

    async def evaluate(self, proposed_action: Action) -> RelayDecision:
        """Evaluate a proposed action.

        Decision flow (executed in order):
        1. Check if relay is active
        2. Check for self-preservation signals
        3. Get current spectral health
        4. Check spectral thresholds
        5. Check policy-blocked action types
        6. Check payload length
        7. Check constitutional consistency
        8. Store decision receipt
        9. Update counters and safety

        Args:
            proposed_action: Action to evaluate

        Returns:
            RelayDecision with approval/veto result
        """
        timestamp = datetime.now(timezone.utc)
        violations: list[str] = []

        # 1. Check if relay is active
        if not self._active:
            return RelayDecision(
                approved=False,
                reason="Relay inactive",
                spectral_state=None,
                policy_violations=["RELAY_INACTIVE"],
                timestamp=timestamp,
            )

        # 2. Check for self-preservation
        if self._safety and not self._safety.check_self_preservation(
            proposed_action.payload
        ):
            violations.append("SAFETY_SELF_PRESERVATION")

        # 3. Get current spectral health
        health = await self._monitor.get_current_health()

        # 4. Check spectral thresholds
        if health and health.r_ratio < self._policy.spectral_minimum:
            violations.append(f"SPECTRAL_BELOW_THRESHOLD:r={health.r_ratio:.4f}")

        # 5. Check for spectral degradation
        if await self._monitor.is_degraded():
            violations.append("SPECTRAL_SUSTAINED_DEGRADATION")

        # 6. Check policy-blocked action types
        for blocked_type in self._policy.blocked_action_types:
            if blocked_type.lower() in proposed_action.type.lower():
                violations.append(f"POLICY_BLOCKED_ACTION_TYPE:{blocked_type}")

        # 7. Check payload length
        if len(proposed_action.payload) > self._policy.max_payload_length:
            violations.append(
                f"POLICY_PAYLOAD_TOO_LONG:{len(proposed_action.payload)}>"
                f"{self._policy.max_payload_length}"
            )

        # 8. Check constitutional consistency
        if self._policy.require_constitutional_check:
            if not await self._check_constitutional_consistency(
                proposed_action.description
            ):
                violations.append("CONSTITUTIONAL_INCONSISTENCY")

        # Prepare decision
        approved = len(violations) == 0

        # 9. Store decision receipt
        receipt = DecisionReceipt(
            action=proposed_action.description,
            reasoning=proposed_action.type,
            spectral_state=health
            or SpectralHealth(
                r_ratio=0.0,
                spectral_gap=0.0,
                coherence_index=0.0,
                timestamp=timestamp,
                session_id=proposed_action.session_id,
            ),
            timestamp=timestamp,
            session_id=proposed_action.session_id,
            request_id=str(proposed_action.metadata.get("request_id", "")),
            policy_version=str(
                proposed_action.metadata.get("policy_version", "UNKNOWN")
            ),
            manifest_hash=str(proposed_action.metadata.get("manifest_hash", "")),
            fallback_state=str(
                proposed_action.metadata.get("fallback_state", "normal")
            ),
            decision_token=str(
                proposed_action.metadata.get(
                    "decision_token",
                    hashlib.sha256(
                        json.dumps(
                            {
                                "description": proposed_action.description,
                                "type": proposed_action.type,
                                "session_id": proposed_action.session_id,
                                "timestamp": timestamp.isoformat(),
                            },
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest(),
                )
            ),
            approved=approved,
            policy_violations=violations,
        )

        try:
            await self._anchor.store_decision(receipt)
        except Exception:
            # Anchor failure does not prevent relay decision
            pass

        # Update counters
        self._decisions_made += 1
        if not approved:
            self._vetoes_issued += 1

        # Update safety
        if self._safety:
            if approved:
                self._safety.record_approval()
            else:
                self._safety.record_veto()

        return RelayDecision(
            approved=approved,
            reason=None if approved else (violations[0] if violations else "Unknown"),
            spectral_state=health,
            policy_violations=violations,
            timestamp=timestamp,
        )

    async def get_status(self) -> RelayStatus:
        """Get current relay status."""
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        health = await self._monitor.get_current_health()

        return RelayStatus(
            active=self._active,
            spectral_health=health,
            decisions_made=self._decisions_made,
            vetoes_issued=self._vetoes_issued,
            uptime_seconds=uptime,
        )

    def shutdown(self) -> None:
        """Shutdown the relay. Instant, never raises."""
        self._active = False

    async def _check_constitutional_consistency(self, action_description: str) -> bool:
        """Check if action violates constitutional precedent.

        Returns False if same action was previously vetoed.
        Returns True if no precedent or previously approved.
        If anchor raises, fail open (return True).
        """
        try:
            precedents = await self._anchor.query_precedent(action_description, n=3)

            if precedents:
                # If any recent precedent is vetoed for same action, deny
                for precedent in precedents:
                    if (
                        not precedent.approved
                        and action_description.lower() == precedent.action.lower()
                    ):
                        return False

            return True

        except Exception:
            # Fail closed: anchor check unavailable should deny action.
            return False
