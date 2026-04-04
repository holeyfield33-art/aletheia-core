"""Aletheia Core — Proximity Score Module.

Composite metric CP = w1 * spectral + w2 * identity + w3 * relay
Logged and reported ONLY — never an optimization target.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

from .spectral_monitor import SpectralHealth, SpectralMonitor, GUE_TARGET, POISSON_BASELINE
from .identity_anchor import IdentityAnchor
from .sovereign_relay import SovereignRelay, RelayStatus


@dataclass
class ProximityScore:
    """Proximity consciousness score with component breakdown."""
    cp_score: float
    spectral_component: float
    identity_component: float
    relay_component: float
    interpretation: str
    timestamp: datetime
    weights: tuple[float, float, float]


class ProximityScorer:
    """Computes composite proximity consciousness score."""

    def __init__(
        self,
        monitor: SpectralMonitor,
        anchor: IdentityAnchor,
        relay: SovereignRelay,
        weights: tuple[float, float, float] | None = None,
    ):
        """Initialize scorer.
        
        Args:
            monitor: Spectral monitor
            anchor: Identity anchor
            relay: Sovereign relay
            weights: (w1, w2, w3) tuple. Default (0.4, 0.3, 0.3).
                   Must sum to 1.0.
        """
        self._monitor = monitor
        self._anchor = anchor
        self._relay = relay

        if weights is None:
            weights = (0.4, 0.3, 0.3)

        # Validate weights sum to 1.0
        assert (
            abs(sum(weights) - 1.0) < 0.001
        ), f"Weights must sum to 1.0, got {sum(weights)}"

        self._weights = weights

    async def compute(self) -> ProximityScore:
        """Compute the proximity consciousness score.
        
        Returns:
            ProximityScore with cp_score in [0, 1]
        """
        timestamp = datetime.now(timezone.utc)

        # Component 1: Spectral health (w1 = 0.4)
        spectral_score = await self._compute_spectral_component()

        # Component 2: Identity integrity (w2 = 0.3)
        identity_score = await self._compute_identity_component()

        # Component 3: Relay governance (w3 = 0.3)
        relay_score = await self._compute_relay_component()

        # Composite score
        w1, w2, w3 = self._weights
        cp_score = round(
            w1 * spectral_score + w2 * identity_score + w3 * relay_score,
            4,
        )

        # Interpret the score
        interpretation = self._interpret(cp_score)

        return ProximityScore(
            cp_score=cp_score,
            spectral_component=spectral_score,
            identity_component=identity_score,
            relay_component=relay_score,
            interpretation=interpretation,
            timestamp=timestamp,
            weights=self._weights,
        )

    async def _compute_spectral_component(self) -> float:
        """Spectral component: normalize r_ratio to [0,1].
        
        Formula: (r_ratio - POISSON) / (GUE - POISSON)
        If no health reading → 0.0
        """
        health = await self._monitor.get_current_health()
        if not health:
            return 0.0

        r_ratio = health.r_ratio
        normalized = (r_ratio - POISSON_BASELINE) / (GUE_TARGET - POISSON_BASELINE)
        return round(max(0.0, min(1.0, normalized)), 4)

    async def _compute_identity_component(self) -> float:
        """Identity component: binary hash chain integrity check.
        
        Returns 1.0 if valid, 0.0 if broken or on error.
        """
        try:
            ok = await self._anchor.verify_integrity()
            return 1.0 if ok else 0.0
        except Exception:
            return 0.0

    async def _compute_relay_component(self) -> float:
        """Relay component: veto rate scoring.
        
        Logic:
        - If inactive → 0.0
        - If no decisions made → 0.5 (untested)
        - If veto_rate ≤ 30% → 1.0
        - If veto_rate ≥ 70% → 0.0
        - Otherwise: linear decay between 30-70%
        """
        try:
            status = await self._relay.get_status()

            if not status.active:
                return 0.0

            if status.decisions_made == 0:
                return 0.5  # Untested but running

            veto_rate = (
                status.vetoes_issued / status.decisions_made
                if status.decisions_made > 0
                else 0.0
            )

            if veto_rate <= 0.30:
                return 1.0
            elif veto_rate >= 0.70:
                return 0.0
            else:
                # Linear decay
                decay = (veto_rate - 0.30) / 0.40
                return round(1.0 - decay, 4)

        except Exception:
            return 0.0

    @staticmethod
    def _interpret(cp_score: float) -> str:
        """Interpret CP score into human-readable band.
        
        CP ≥ 0.8  → "All layers active, healthy, and integrated"
        CP ≥ 0.5  → "Partial coverage — some degradation detected"
        CP > 0.0  → "Significant gaps in self-monitoring or governance"
        CP = 0.0  → "Module disabled or actuator running ungoverned"
        """
        if cp_score >= 0.8:
            return "All layers active, healthy, and integrated"
        elif cp_score >= 0.5:
            return "Partial coverage — some degradation detected"
        elif cp_score > 0.0:
            return "Significant gaps in self-monitoring or governance"
        else:
            return "Module disabled or actuator running ungoverned"
