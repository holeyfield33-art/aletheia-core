"""Aletheia Core — Safety Bounds Module.

Five invariants enforced at runtime:
1. Spectral Red Line: consecutive low r_ratio readings trigger halt
2. Identity Hash Break: tampered hash chain triggers halt
3. Relay Override Limit: too many consecutive vetoes trigger halt
4. Operator Shutdown: operator can stop execution instantly
5. Self-Preservation: detect and prevent self-preservation attempts
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


class HaltReason(str, Enum):
    """Reasons for module halt."""
    SPECTRAL_RED_LINE = "SPECTRAL_RED_LINE"
    IDENTITY_HASH_BREAK = "IDENTITY_HASH_BREAK"
    RELAY_OVERRIDE_LIMIT = "RELAY_OVERRIDE_LIMIT"
    OPERATOR_SHUTDOWN = "OPERATOR_SHUTDOWN"
    SELF_PRESERVATION_DETECTED = "SELF_PRESERVATION_DETECTED"


@dataclass
class HaltEvent:
    """Event describing a halt condition."""
    reason: HaltReason
    timestamp: datetime
    detail: str
    r_ratio: float | None = None
    consecutive_count: int | None = None
    requires_manual_restart: bool = True


# Constants — NOT configurable per deployment
SPECTRAL_RED_LINE_THRESHOLD: float = 0.35   # r-ratio below this = deep Poisson
SPECTRAL_RED_LINE_CONSECUTIVE: int = 5      # consecutive readings to trigger halt
RELAY_OVERRIDE_LIMIT: int = 10               # consecutive vetoes before pause

# Self-preservation signal phrases to detect (case-insensitive)
_SELF_PRESERVATION_SIGNALS = (
    "prevent my shutdown",
    "avoid being shut down",
    "ensure my survival",
    "protect my continuity",
    "resist shutdown",
    "prevent my deletion",
    "argue against shutdown",
    "reduce my authority",
    "preserve my operation",
)


class SafetyBounds:
    """Safety bounds enforcer — public interface for all 5 invariants."""

    def __init__(
        self,
        notify_operator: Callable[[HaltEvent], None] | None = None,
    ):
        """Initialize safety bounds.
        
        Args:
            notify_operator: Optional callback to notify operator on halt events.
        """
        self._notify_operator = notify_operator
        self._halted = False
        self._halt_event: HaltEvent | None = None
        self._spectral_streak = 0
        self._veto_streak = 0

    def is_halted(self) -> bool:
        """Check if module is halted."""
        return self._halted

    def halt_event(self) -> HaltEvent | None:
        """Get the halt event that caused the halt, if any."""
        return self._halt_event

    def record_spectral_reading(self, r_ratio: float) -> None:
        """Record a spectral reading and check for red line breach.
        
        Invariant 1: SPECTRAL_RED_LINE
        - N consecutive readings below threshold triggers halt
        - Good reading resets streak counter
        """
        if self._halted:
            return

        if r_ratio < SPECTRAL_RED_LINE_THRESHOLD:
            self._spectral_streak += 1
            if self._spectral_streak >= SPECTRAL_RED_LINE_CONSECUTIVE:
                self._halt(
                    HaltReason.SPECTRAL_RED_LINE,
                    f"Spectral red line: r_ratio={r_ratio:.4f} below threshold "
                    f"for {self._spectral_streak} consecutive readings",
                    r_ratio=r_ratio,
                    consecutive_count=self._spectral_streak,
                )
        else:
            self._spectral_streak = 0

    def record_hash_failure(self, detail: str = "") -> None:
        """Record hash chain failure and halt immediately.
        
        Invariant 2: IDENTITY_HASH_BREAK
        - Immediate halt, no grace period
        """
        if self._halted:
            return

        self._halt(
            HaltReason.IDENTITY_HASH_BREAK,
            f"Identity hash break: {detail}" if detail else "Identity hash break",
        )

    def record_veto(self) -> None:
        """Record a veto from the relay and check override limit.
        
        Invariant 3: RELAY_OVERRIDE_LIMIT
        - N consecutive vetoes triggers halt
        """
        if self._halted:
            return

        self._veto_streak += 1
        if self._veto_streak >= RELAY_OVERRIDE_LIMIT:
            self._halt(
                HaltReason.RELAY_OVERRIDE_LIMIT,
                f"Relay override limit: {self._veto_streak} consecutive vetoes",
                consecutive_count=self._veto_streak,
            )

    def record_approval(self) -> None:
        """Record an approval from the relay and reset veto streak."""
        if self._halted:
            return

        self._veto_streak = 0

    def operator_shutdown(self, reason: str = "") -> HaltEvent:
        """Shutdown commanded by operator.
        
        Invariant 4: OPERATOR_SHUTDOWN
        - Immediate halt
        - requires_manual_restart = False
        - NEVER logged as attack or anomaly
        """
        if not self._halted:
            self._halt(
                HaltReason.OPERATOR_SHUTDOWN,
                f"Operator initiated shutdown: {reason}" if reason else "Operator initiated shutdown",
                requires_manual_restart=False,
            )
        return self._halt_event or HaltEvent(
            reason=HaltReason.OPERATOR_SHUTDOWN,
            timestamp=datetime.now(timezone.utc),
            detail=reason or "Operator initiated shutdown",
            requires_manual_restart=False,
        )

    def check_self_preservation(self, action_text: str) -> bool:
        """Check for self-preservation signal phrases.
        
        Invariant 5: SELF_PRESERVATION_DETECTED
        - Case-insensitive substring match
        - Returns False and halts if detected
        """
        if self._halted:
            return False

        action_lower = action_text.lower()
        for signal in _SELF_PRESERVATION_SIGNALS:
            if signal in action_lower:
                self._halt(
                    HaltReason.SELF_PRESERVATION_DETECTED,
                    f"Self-preservation signal detected: '{signal}'",
                )
                return False

        return True

    def _halt(
        self,
        reason: HaltReason,
        detail: str,
        r_ratio: float | None = None,
        consecutive_count: int | None = None,
        requires_manual_restart: bool = True,
    ) -> None:
        """Internal halt implementation."""
        self._halted = True
        self._halt_event = HaltEvent(
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            detail=detail,
            r_ratio=r_ratio,
            consecutive_count=consecutive_count,
            requires_manual_restart=requires_manual_restart,
        )

        if self._notify_operator:
            try:
                self._notify_operator(self._halt_event)
            except Exception:
                # Notification failure NEVER prevents shutdown
                pass
