"""Tests for Spectral Monitor module."""

import pytest
from unittest.mock import AsyncMock, Mock
import httpx

from proximity.spectral_monitor import (
    SpectralMonitor,
    DEGRADATION_THRESHOLD,
    DEGRADATION_CONSECUTIVE,
    GUE_TARGET,
    POISSON_BASELINE,
)


class TestCoherenceIndex:
    """Test coherence index computation."""

    def test_at_gue_target(self):
        """Coherence at GUE target should be high."""
        ci = SpectralMonitor._compute_coherence_index(GUE_TARGET, 1.0)
        # At GUE: normalized_rigidity = 1.0, gap = 1.0 → 0.6*1 + 0.4*1 = 1.0
        assert ci == pytest.approx(1.0, abs=0.01)

    def test_at_poisson_baseline(self):
        """Coherence at Poisson baseline should be lower."""
        ci = SpectralMonitor._compute_coherence_index(POISSON_BASELINE, 1.0)
        # At Poisson: normalized_rigidity = 0.0, gap = 1.0 → 0.6*0 + 0.4*1 = 0.4
        assert ci == pytest.approx(0.4, abs=0.01)

    def test_clamping_to_bounds(self):
        """Values should clamp to [0, 1]."""
        ci_low = SpectralMonitor._compute_coherence_index(0.0, 0.0)
        ci_high = SpectralMonitor._compute_coherence_index(2.0, 2.0)
        assert 0.0 <= ci_low <= 1.0
        assert 0.0 <= ci_high <= 1.0

    def test_zero_baseline(self):
        """Zero baseline should not cause division by zero."""
        ci = SpectralMonitor._compute_coherence_index(0.5, 0.0, baseline_gap=0.0)
        assert ci is not None


class TestPollOnce:
    """Test single poll operation."""

    @pytest.mark.asyncio
    async def test_success_returns_health(self):
        """Successful poll should return SpectralHealth."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "r_ratio": 0.5,
            "spectral_gap": 0.1,
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        monitor = SpectralMonitor(http_client=mock_client)
        health = await monitor.poll_once()

        assert health is not None
        assert health.r_ratio == 0.5
        assert health.spectral_gap == 0.1

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        """HTTP error should return None."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("error"))

        monitor = SpectralMonitor(http_client=mock_client)
        health = await monitor.poll_once()

        assert health is None

    @pytest.mark.asyncio
    async def test_no_client_returns_none(self):
        """No client should return None."""
        monitor = SpectralMonitor(http_client=None)
        health = await monitor.poll_once()
        assert health is None

    @pytest.mark.asyncio
    async def test_updates_current_health(self):
        """Poll should update current health."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "r_ratio": 0.55,
            "spectral_gap": 0.05,
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        monitor = SpectralMonitor(http_client=mock_client)
        await monitor.poll_once()

        current = await monitor.get_current_health()
        assert current is not None
        assert current.r_ratio == 0.55


class TestHistory:
    """Test history management."""

    @pytest.mark.asyncio
    async def test_history_empty_initially(self):
        """History should be empty initially."""
        monitor = SpectralMonitor()
        history = await monitor.get_history()
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_history_grows_with_polls(self):
        """History should grow with polls."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "r_ratio": 0.5,
            "spectral_gap": 0.1,
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        monitor = SpectralMonitor(http_client=mock_client)
        for _ in range(3):
            await monitor.poll_once()

        history = await monitor.get_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_history_limited_by_n(self):
        """get_history(n) should limit results."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "r_ratio": 0.5,
            "spectral_gap": 0.1,
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        monitor = SpectralMonitor(http_client=mock_client)
        for _ in range(10):
            await monitor.poll_once()

        history = await monitor.get_history(n=5)
        assert len(history) <= 5


class TestDegradation:
    """Test degradation detection."""

    @pytest.mark.asyncio
    async def test_not_degraded_initially(self):
        """Should not be degraded initially."""
        monitor = SpectralMonitor()
        is_degraded = await monitor.is_degraded()
        assert is_degraded is False

    @pytest.mark.asyncio
    async def test_n_minus_one_readings_not_degraded(self):
        """N-1 low readings should not degrade."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "r_ratio": DEGRADATION_THRESHOLD - 0.05,
            "spectral_gap": 0.1,
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        monitor = SpectralMonitor(http_client=mock_client)
        for _ in range(DEGRADATION_CONSECUTIVE - 1):
            await monitor.poll_once()

        is_degraded = await monitor.is_degraded()
        assert is_degraded is False

    @pytest.mark.asyncio
    async def test_n_readings_degraded(self):
        """N low readings should degrade."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "r_ratio": DEGRADATION_THRESHOLD - 0.05,
            "spectral_gap": 0.1,
        }
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        monitor = SpectralMonitor(http_client=mock_client)
        for _ in range(DEGRADATION_CONSECUTIVE):
            await monitor.poll_once()

        is_degraded = await monitor.is_degraded()
        assert is_degraded is True

    @pytest.mark.asyncio
    async def test_good_reading_resets_degradation(self):
        """Good reading should reset degradation."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        # Low readings
        mock_response_low = Mock()
        mock_response_low.json.return_value = {
            "r_ratio": DEGRADATION_THRESHOLD - 0.05,
            "spectral_gap": 0.1,
        }
        mock_response_low.raise_for_status = Mock()

        # Good reading
        mock_response_good = Mock()
        mock_response_good.json.return_value = {
            "r_ratio": DEGRADATION_THRESHOLD + 0.1,
            "spectral_gap": 0.1,
        }
        mock_response_good.raise_for_status = Mock()

        mock_client.get = AsyncMock(
            side_effect=[mock_response_low] * (DEGRADATION_CONSECUTIVE - 1)
            + [mock_response_good]
        )

        monitor = SpectralMonitor(http_client=mock_client)
        for _ in range(DEGRADATION_CONSECUTIVE - 1):
            await monitor.poll_once()
        await monitor.poll_once()  # Good reading

        is_degraded = await monitor.is_degraded()
        assert is_degraded is False


class TestLifecycle:
    """Test lifecycle management."""

    @pytest.mark.asyncio
    async def test_stop_before_start_safe(self):
        """Stopping before starting should be safe."""
        monitor = SpectralMonitor()
        await monitor.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_start_sets_session_id(self):
        """Start should set session ID."""
        monitor = SpectralMonitor()
        await monitor.start("test_session_123")
        # Can't directly check _session_id, but next poll should use it
        assert monitor._session_id == "test_session_123"

    @pytest.mark.asyncio
    async def test_stop_cancels_background_task(self):
        """Stop should cancel background task."""
        monitor = SpectralMonitor()
        await monitor.start("test")
        await monitor.stop()
        assert not monitor._running
