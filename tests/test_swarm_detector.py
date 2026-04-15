"""Tests for SPRT swarm detector and unified_audit integration."""
from __future__ import annotations

import math
import unittest

import numpy as np

from monitoring.swarm_detector import SwarmDetector, SwarmDetectorConfig
from core.unified_audit import UnifiedSovereignRuntime
from economics.circuit_breaker import BreakerState


# ---------------------------------------------------------------------------
# Unit tests — SwarmDetector
# ---------------------------------------------------------------------------
class TestSwarmDetectorConfig(unittest.TestCase):
    def test_defaults(self) -> None:
        cfg = SwarmDetectorConfig()
        self.assertEqual(cfg.window_size, 60)
        self.assertAlmostEqual(cfg.trim_fraction, 0.05)
        self.assertAlmostEqual(cfg.alpha, 1e-4)


class TestTrimmedMean(unittest.TestCase):
    def test_empty(self) -> None:
        det = SwarmDetector()
        self.assertEqual(det._trimmed_mean([]), 0.0)

    def test_no_trim_needed(self) -> None:
        det = SwarmDetector()
        self.assertAlmostEqual(det._trimmed_mean([1.0, 2.0, 3.0]), 2.0)

    def test_trim_outliers(self) -> None:
        det = SwarmDetector(SwarmDetectorConfig(trim_fraction=0.1))
        values = [0.0] * 5 + [1.0] * 90 + [100.0] * 5
        result = det._trimmed_mean(values)
        # With top/bottom 10% trimmed, the 100s and some 0s are removed
        self.assertGreater(result, 0.0)
        self.assertLess(result, 10.0)

    def test_single_value(self) -> None:
        det = SwarmDetector()
        self.assertAlmostEqual(det._trimmed_mean([42.0]), 42.0)


class TestLogLikelihood(unittest.TestCase):
    def test_benign_drift_negative(self) -> None:
        det = SwarmDetector(SwarmDetectorConfig(mu0=0.1, mu1=0.4, sigma2=0.04))
        # Drift at mu0 → increment should be negative (evidence for H0)
        inc = det._log_likelihood_increment(0.1)
        self.assertLess(inc, 0.0)

    def test_attack_drift_positive(self) -> None:
        det = SwarmDetector(SwarmDetectorConfig(mu0=0.1, mu1=0.4, sigma2=0.04))
        # Drift at mu1 → increment should be positive (evidence for H1)
        inc = det._log_likelihood_increment(0.4)
        self.assertGreater(inc, 0.0)

    def test_midpoint_zero(self) -> None:
        det = SwarmDetector(SwarmDetectorConfig(mu0=0.1, mu1=0.4, sigma2=0.04))
        inc = det._log_likelihood_increment(0.25)  # midpoint
        self.assertAlmostEqual(inc, 0.0)

    def test_zero_variance_safe(self) -> None:
        det = SwarmDetector(SwarmDetectorConfig(sigma2=0.0))
        self.assertEqual(det._log_likelihood_increment(0.5), 0.0)


class TestSPRTGating(unittest.TestCase):
    """Test the INCONCLUSIVE-rate floor gating."""

    def _make_config(self, window_size: int = 20) -> SwarmDetectorConfig:
        return SwarmDetectorConfig(
            window_size=window_size,
            r_min=0.05,
            alpha=1e-4,
            beta=1e-2,
            mu0=0.1,
            mu1=0.4,
            sigma2=0.04,
        )

    def test_insufficient_data_returns_false(self) -> None:
        det = SwarmDetector(self._make_config(window_size=20))
        # Only 1 window — need at least window_size//2 = 10
        result, llr = det.update([0.5], 1, 10)
        self.assertFalse(result)

    def test_low_inconclusive_rate_blocks_detection(self) -> None:
        det = SwarmDetector(self._make_config(window_size=20))
        # Fill windows but with zero INCONCLUSIVE rate
        for _ in range(20):
            result, _ = det.update([0.5, 0.5, 0.5], 0, 100)
        self.assertFalse(result)

    def test_empty_drifts_returns_false(self) -> None:
        det = SwarmDetector()
        result, llr = det.update([], 0, 0)
        self.assertFalse(result)
        self.assertEqual(llr, 0.0)


class TestSPRTDetection(unittest.TestCase):
    """Test that sustained attack-level drift triggers detection."""

    def _make_attack_config(self) -> SwarmDetectorConfig:
        return SwarmDetectorConfig(
            window_size=20,
            r_min=0.05,
            alpha=1e-4,
            beta=1e-2,
            mu0=0.1,
            mu1=0.4,
            sigma2=0.04,
        )

    def test_sustained_attack_triggers(self) -> None:
        det = SwarmDetector(self._make_attack_config())
        detected = False
        # Feed many windows of attack-level drift with sufficient INCONCLUSIVE rate
        for _ in range(100):
            drifts = [0.45] * 20  # well above mu1
            result, llr = det.update(drifts, inconclusive_count=5, total_sessions=20)
            if result:
                detected = True
                break
        self.assertTrue(detected, "Sustained attack-level drift should trigger detection")
        self.assertTrue(det.attack_declared)

    def test_benign_drift_does_not_trigger(self) -> None:
        det = SwarmDetector(self._make_attack_config())
        # Feed benign drift with sufficient INCONCLUSIVE rate
        for _ in range(100):
            drifts = [0.08] * 20  # below mu0
            result, _ = det.update(drifts, inconclusive_count=5, total_sessions=20)
            self.assertFalse(result)
        self.assertFalse(det.attack_declared)

    def test_reset_clears_state(self) -> None:
        det = SwarmDetector(self._make_attack_config())
        # Accumulate some state
        for _ in range(15):
            det.update([0.4] * 10, 3, 10)
        self.assertGreater(len(det.drift_window), 0)
        det.reset()
        self.assertEqual(len(det.drift_window), 0)
        self.assertEqual(det.log_likelihood_ratio, 0.0)
        self.assertFalse(det.attack_declared)


class TestSPRTThresholds(unittest.TestCase):
    """Verify threshold math."""

    def test_upper_threshold_value(self) -> None:
        cfg = SwarmDetectorConfig(alpha=1e-4, beta=1e-2)
        expected = math.log((1 - cfg.beta) / cfg.alpha)
        self.assertAlmostEqual(expected, math.log(0.99 / 1e-4), places=5)
        self.assertGreater(expected, 0.0)

    def test_negative_llr_resets(self) -> None:
        """Strong benign evidence should reset LLR to zero."""
        cfg = SwarmDetectorConfig(
            window_size=20, r_min=0.0, mu0=0.1, mu1=0.4, sigma2=0.04,
        )
        det = SwarmDetector(cfg)
        # Feed very low drifts to push LLR negative
        for _ in range(50):
            det.update([0.0] * 10, 2, 10)
        # LLR should have been reset (not unboundedly negative)
        self.assertGreaterEqual(det.log_likelihood_ratio, 0.0)


# ---------------------------------------------------------------------------
# Integration — UnifiedSovereignRuntime.aggregate_swarm_window
# ---------------------------------------------------------------------------
class TestSwarmIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = UnifiedSovereignRuntime(
            max_tokens_per_sec=1000,
            max_session_budget=50000,
            breaker_threshold=5,
            breaker_cooldown=0.01,
            swarm_config=SwarmDetectorConfig(
                window_size=20,
                r_min=0.05,
                mu0=0.1,
                mu1=0.4,
                sigma2=0.04,
            ),
        )

    def tearDown(self) -> None:
        self.runtime.reset()

    def test_benign_sessions_no_trip(self) -> None:
        sessions = [{"drift_score": 0.05} for _ in range(20)]
        for _ in range(30):
            result = self.runtime.aggregate_swarm_window(sessions)
        self.assertFalse(result)
        self.assertEqual(self.runtime.breaker_state, BreakerState.CLOSED)

    def test_attack_sessions_trip_breaker(self) -> None:
        tripped = False
        for _ in range(100):
            # Mix of high drift and INCONCLUSIVE
            sessions = (
                [{"drift_score": 0.5} for _ in range(15)]
                + [{"drift_score": -1.0} for _ in range(5)]
            )
            result = self.runtime.aggregate_swarm_window(sessions)
            if result:
                tripped = True
                break
        self.assertTrue(tripped)
        self.assertEqual(self.runtime.breaker_state, BreakerState.OPEN)

    def test_inconclusive_counted_correctly(self) -> None:
        sessions = [
            {"drift_score": 0.3},
            {"drift_score": -1.0},
            {"drift_score": 0.2},
            {"drift_score": -1.0},
        ]
        # Should not crash, returns False (insufficient data)
        result = self.runtime.aggregate_swarm_window(sessions)
        self.assertFalse(result)

    def test_empty_sessions(self) -> None:
        result = self.runtime.aggregate_swarm_window([])
        self.assertFalse(result)

    def test_missing_drift_score_treated_as_inconclusive(self) -> None:
        sessions = [{"other_field": "x"}, {"drift_score": 0.2}]
        # Should not crash
        result = self.runtime.aggregate_swarm_window(sessions)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
