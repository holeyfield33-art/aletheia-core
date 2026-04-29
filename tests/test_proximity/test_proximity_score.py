"""Tests for Proximity Score module."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from proximity.proximity_score import ProximityScorer
from proximity.spectral_monitor import (
    SpectralMonitor,
    SpectralHealth,
    GUE_TARGET,
    POISSON_BASELINE,
)
from proximity.identity_anchor import IdentityAnchor
from proximity.sovereign_relay import SovereignRelay, RelayStatus


class TestInterpretation:
    """Test score interpretation bands."""

    def test_interpret_high_score(self):
        """High score should interpret as healthy."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = AsyncMock(spec=SovereignRelay)

        scorer = ProximityScorer(monitor, anchor, relay)
        interp = scorer._interpret(0.85)
        assert "healthy" in interp.lower()

    def test_interpret_medium_score(self):
        """Medium score should interpret as partial coverage."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = AsyncMock(spec=SovereignRelay)

        scorer = ProximityScorer(monitor, anchor, relay)
        interp = scorer._interpret(0.65)
        assert "partial" in interp.lower() or "degradation" in interp.lower()

    def test_interpret_low_score(self):
        """Low score should interpret as gaps."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = AsyncMock(spec=SovereignRelay)

        scorer = ProximityScorer(monitor, anchor, relay)
        interp = scorer._interpret(0.2)
        assert "gaps" in interp.lower()

    def test_interpret_zero_score(self):
        """Zero score should interpret as disabled."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = AsyncMock(spec=SovereignRelay)

        scorer = ProximityScorer(monitor, anchor, relay)
        interp = scorer._interpret(0.0)
        assert "disabled" in interp.lower() or "ungoverned" in interp.lower()


class TestCompute:
    """Test score computation."""

    @pytest.mark.asyncio
    async def test_returns_proximity_score(self):
        """Compute should return ProximityScore."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=10,
            vetoes_issued=3,
            uptime_seconds=100.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score is not None
        assert 0.0 <= score.cp_score <= 1.0

    @pytest.mark.asyncio
    async def test_perfect_inputs_high_score(self):
        """Perfect inputs should give high CP score."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=GUE_TARGET,
            spectral_gap=1.0,
            coherence_index=1.0,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=100,
            vetoes_issued=10,  # 10% veto rate
            uptime_seconds=1000.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score.cp_score > 0.8


class TestComponentIsolation:
    """Test that broken components reduce score."""

    @pytest.mark.asyncio
    async def test_broken_hash_chain_reduces_score(self):
        """Broken hash chain should reduce identity component."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = False

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=10,
            vetoes_issued=3,
            uptime_seconds=100.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score.identity_component == 0.0

    @pytest.mark.asyncio
    async def test_low_r_ratio_reduces_score(self):
        """Low r_ratio should reduce spectral component."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=POISSON_BASELINE,  # Low end
            spectral_gap=0.1,
            coherence_index=0.0,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=10,
            vetoes_issued=3,
            uptime_seconds=100.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score.spectral_component < 0.5

    @pytest.mark.asyncio
    async def test_high_veto_rate_reduces_score(self):
        """High veto rate should reduce relay component."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=10,
            vetoes_issued=8,  # 80% veto rate
            uptime_seconds=100.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score.relay_component == 0.0

    @pytest.mark.asyncio
    async def test_inactive_relay_zero_component(self):
        """Inactive relay should have relay component = 0.0."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=False,
            spectral_health=None,
            decisions_made=0,
            vetoes_issued=0,
            uptime_seconds=0.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score.relay_component == 0.0


class TestMathValidation:
    """Test mathematical consistency."""

    @pytest.mark.asyncio
    async def test_components_sum_to_cp_score(self):
        """Components should mathematically form CP score."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=10,
            vetoes_issued=2,
            uptime_seconds=100.0,
        )

        weights = (0.4, 0.3, 0.3)
        scorer = ProximityScorer(monitor, anchor, relay, weights=weights)
        score = await scorer.compute()

        # Check that components sum to CP score (with tolerance)
        computed_cp = (
            weights[0] * score.spectral_component
            + weights[1] * score.identity_component
            + weights[2] * score.relay_component
        )
        assert abs(computed_cp - score.cp_score) < 0.001


class TestWeights:
    """Test weight configuration."""

    def test_invalid_weights_raise_error(self):
        """Invalid weights (don't sum to 1.0) should raise."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = AsyncMock(spec=SovereignRelay)

        with pytest.raises(AssertionError):
            ProximityScorer(
                monitor,
                anchor,
                relay,
                weights=(0.5, 0.3, 0.3),  # sums to 1.1
            )

    def test_default_weights_sum_to_one(self):
        """Default weights should sum to 1.0."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = AsyncMock(spec=SovereignRelay)

        scorer = ProximityScorer(monitor, anchor, relay)
        assert abs(sum(scorer._weights) - 1.0) < 0.001


class TestNoHealthReading:
    """Test behavior with no health reading."""

    @pytest.mark.asyncio
    async def test_no_health_reading_spectral_zero(self):
        """No health reading should give spectral component = 0.0."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = None

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True

        relay = AsyncMock(spec=SovereignRelay)
        relay.get_status.return_value = RelayStatus(
            active=True,
            spectral_health=None,
            decisions_made=10,
            vetoes_issued=2,
            uptime_seconds=100.0,
        )

        scorer = ProximityScorer(monitor, anchor, relay)
        score = await scorer.compute()

        assert score.spectral_component == 0.0
