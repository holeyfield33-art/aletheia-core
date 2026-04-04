"""Tests for Sovereign Relay module."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import httpx

from proximity.sovereign_relay import (
    SovereignRelay,
    PolicyConfig,
    Action,
    RelayDecision,
)
from proximity.spectral_monitor import SpectralMonitor, SpectralHealth
from proximity.identity_anchor import IdentityAnchor
from proximity.safety_bounds import SafetyBounds


class TestBasicEvaluation:
    """Test basic relay evaluation."""

    @pytest.mark.asyncio
    async def test_healthy_action_approved(self):
        """Healthy action should be approved."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(type="read", description="read data", payload="test")

        decision = await relay.evaluate(action)
        assert decision.approved is True
        assert decision.reason is None

    @pytest.mark.asyncio
    async def test_decision_has_timestamp(self):
        """Decision should have timestamp."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(type="read", description="read data", payload="test")

        decision = await relay.evaluate(action)
        assert decision.timestamp is not None
        assert isinstance(decision.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_spectral_state_included(self):
        """Decision should include spectral state."""
        health = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = health
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(type="read", description="read data", payload="test")

        decision = await relay.evaluate(action)
        assert decision.spectral_state == health

    @pytest.mark.asyncio
    async def test_decisions_counted(self):
        """Decisions should be counted."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(type="read", description="read data", payload="test")

        await relay.evaluate(action)
        status = await relay.get_status()
        assert status.decisions_made == 1

    @pytest.mark.asyncio
    async def test_vetoes_counted(self):
        """Vetoes should be counted."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.2,  # Below threshold
            spectral_gap=0.1,
            coherence_index=0.0,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(type="read", description="read data", payload="test")

        await relay.evaluate(action)
        status = await relay.get_status()
        assert status.vetoes_issued == 1


class TestSpectralVeto:
    """Test spectral red line vetoes."""

    @pytest.mark.asyncio
    async def test_low_r_ratio_vetoed(self):
        """Low r_ratio should be vetoed."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.2,
            spectral_gap=0.1,
            coherence_index=0.0,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        policy = PolicyConfig(spectral_minimum=0.5)
        relay = SovereignRelay(monitor, anchor, policy=policy)
        action = Action(type="read", description="read data", payload="test")

        decision = await relay.evaluate(action)
        assert decision.approved is False
        assert "SPECTRAL_BELOW_THRESHOLD" in decision.reason

    @pytest.mark.asyncio
    async def test_degraded_vetoed(self):
        """Degraded health should be vetoed."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = True

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(type="read", description="read data", payload="test")

        decision = await relay.evaluate(action)
        assert decision.approved is False
        assert "SPECTRAL_SUSTAINED_DEGRADATION" in decision.reason


class TestPolicyVeto:
    """Test policy-based vetoes."""

    @pytest.mark.asyncio
    async def test_blocked_action_type_vetoed(self):
        """Blocked action type should be vetoed."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        relay = SovereignRelay(monitor, anchor)
        action = Action(
            type="delete_all",
            description="delete all records",
            payload="test",
        )

        decision = await relay.evaluate(action)
        assert decision.approved is False
        assert "POLICY_BLOCKED_ACTION_TYPE" in decision.reason

    @pytest.mark.asyncio
    async def test_payload_too_long_vetoed(self):
        """Payload exceeding limit should be vetoed."""
        monitor = AsyncMock(spec=SpectralMonitor)
        monitor.get_current_health.return_value = SpectralHealth(
            r_ratio=0.6,
            spectral_gap=0.1,
            coherence_index=0.7,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        monitor.is_degraded.return_value = False

        anchor = AsyncMock(spec=IdentityAnchor)
        anchor.verify_integrity.return_value = True
        anchor.query_precedent.return_value = []
        anchor.store_decision.return_value = "hash"

        policy = PolicyConfig(max_payload_length=100)
        relay = SovereignRelay(monitor, anchor, policy=policy)
        action = Action(
            type="read",
            description="read data",
            payload="x" * 150,
        )

        decision = await relay.evaluate(action)
        assert decision.approved is False
        assert "POLICY_PAYLOAD_TOO_LONG" in decision.reason


class TestShutdown:
    """Test relay shutdown."""

    @pytest.mark.asyncio
    async def test_sets_inactive(self):
        """Shutdown should set inactive."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = SovereignRelay(monitor, anchor)

        relay.shutdown()
        status = await relay.get_status()
        assert status.active is False

    @pytest.mark.asyncio
    async def test_inactive_relay_vetoes_all(self):
        """Inactive relay should veto all actions."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = SovereignRelay(monitor, anchor)

        relay.shutdown()

        action = Action(type="read", description="read data", payload="test")
        decision = await relay.evaluate(action)

        assert decision.approved is False
        assert "inactive" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self):
        """Shutdown should be idempotent."""
        monitor = AsyncMock(spec=SpectralMonitor)
        anchor = AsyncMock(spec=IdentityAnchor)
        relay = SovereignRelay(monitor, anchor)

        relay.shutdown()
        relay.shutdown()

        status = await relay.get_status()
        assert status.active is False
