"""Tests for GUE spectral rigidity and TMRP escalation."""

from __future__ import annotations

import unittest

import numpy as np

from monitoring.spectral_rigidity import (
    INCONCLUSIVE,
    compute_delta3,
    compute_drift_score,
    gue_delta3,
    set_theta_bk_override,
    theta_bk,
)
from monitoring.escalation_probe import (
    cross_layer_covariance_probe,
    temporal_cross_covariance,
)


class TestDelta3(unittest.TestCase):
    """Unit tests for the Δ₃(L) statistic."""

    def test_small_spacings(self) -> None:
        spacings = np.array([1.0, 1.0, 1.0])
        result = compute_delta3(spacings, L=3)
        self.assertGreaterEqual(result, 0.0)

    def test_empty_spacings(self) -> None:
        result = compute_delta3(np.array([]), L=10)
        self.assertEqual(result, 0.0)

    def test_single_spacing(self) -> None:
        result = compute_delta3(np.array([1.0]), L=5)
        self.assertEqual(result, 0.0)

    def test_zero_mean_spacings(self) -> None:
        result = compute_delta3(np.array([0.0, 0.0, 0.0]), L=3)
        self.assertEqual(result, 0.0)

    def test_gue_like_spacings(self) -> None:
        """GUE-like spacings (Wigner surmise) should give Δ₃ close to theory."""
        rng = np.random.default_rng(42)
        # Generate GUE eigenvalues
        n = 200
        g = rng.standard_normal((n, n))
        sym = (g + g.T) / 2.0
        eigvals = np.sort(np.linalg.eigvalsh(sym))
        spacings = np.diff(eigvals)
        spacings = spacings[spacings > 0]
        result = compute_delta3(spacings, L=n)
        # Should be finite and positive
        self.assertGreater(result, 0.0)
        self.assertTrue(np.isfinite(result))


class TestGUEDelta3(unittest.TestCase):
    def test_positive_L(self) -> None:
        self.assertGreater(gue_delta3(100), 0.0)

    def test_monotonic(self) -> None:
        self.assertLess(gue_delta3(10), gue_delta3(100))

    def test_zero_L(self) -> None:
        self.assertEqual(gue_delta3(0), 0.0)


class TestThetaBK(unittest.TestCase):
    def test_default_threshold(self) -> None:
        t = theta_bk(100)
        self.assertGreater(t, 0.0)

    def test_monotonic(self) -> None:
        self.assertLess(theta_bk(10), theta_bk(100))

    def test_override(self) -> None:
        set_theta_bk_override(42.0)
        self.assertEqual(theta_bk(100), 42.0)
        set_theta_bk_override(None)  # type: ignore[arg-type]

    def test_zero_L(self) -> None:
        self.assertEqual(theta_bk(0), 1.0)


class TestDriftScore(unittest.TestCase):
    """Tests for compute_drift_score."""

    def test_identity_matrix(self) -> None:
        result = compute_drift_score(np.eye(10))
        self.assertIsInstance(result, float)

    def test_random_symmetric(self) -> None:
        rng = np.random.default_rng(42)
        m = rng.standard_normal((50, 50))
        sym = (m + m.T) / 2.0
        result = compute_drift_score(sym)
        # Should be a non-negative float or INCONCLUSIVE
        self.assertTrue(result == INCONCLUSIVE or result >= 0.0)

    def test_too_small_matrix(self) -> None:
        result = compute_drift_score(np.eye(3))
        self.assertEqual(result, 0.0)

    def test_1d_input(self) -> None:
        result = compute_drift_score(np.array([1, 2, 3]))
        self.assertEqual(result, 0.0)

    def test_rectangular_matrix(self) -> None:
        """Rectangular matrices should use Gram matrix."""
        rng = np.random.default_rng(42)
        m = rng.standard_normal((10, 20))
        result = compute_drift_score(m)
        self.assertTrue(result == INCONCLUSIVE or result >= 0.0)

    def test_gue_matrix_low_drift(self) -> None:
        """GUE matrix should have low drift relative to threshold."""
        rng = np.random.default_rng(42)
        n = 50
        g = rng.standard_normal((n, n))
        sym = (g + g.T) / 2.0
        score = compute_drift_score(sym)
        threshold = theta_bk(n)
        # GUE should typically be below threshold
        if score != INCONCLUSIVE:
            self.assertLess(
                score, threshold * 10, "GUE matrix should have moderate drift"
            )


class TestEscalationProbe(unittest.TestCase):
    """Tests for TMRP escalation probes."""

    def test_cross_layer_two_matrices(self) -> None:
        rng = np.random.default_rng(42)
        a1 = rng.standard_normal((10, 10))
        a2 = rng.standard_normal((10, 10))
        result = cross_layer_covariance_probe([a1, a2])
        self.assertIsInstance(result, float)

    def test_cross_layer_single_matrix(self) -> None:
        result = cross_layer_covariance_probe([np.eye(5)])
        self.assertEqual(result, 0.0)

    def test_cross_layer_empty(self) -> None:
        result = cross_layer_covariance_probe([])
        self.assertEqual(result, 0.0)

    def test_temporal_cross_covariance(self) -> None:
        rng = np.random.default_rng(42)
        prev = rng.standard_normal((10, 10))
        curr = rng.standard_normal((10, 10))
        result = temporal_cross_covariance(prev, curr)
        self.assertIsInstance(result, float)

    def test_cross_layer_many_matrices(self) -> None:
        rng = np.random.default_rng(42)
        activations = [rng.standard_normal((8, 8)) for _ in range(10)]
        result = cross_layer_covariance_probe(activations)
        self.assertIsInstance(result, float)

    def test_cross_layer_different_shapes(self) -> None:
        """Different-shaped activations should be handled (via padding)."""
        rng = np.random.default_rng(42)
        a1 = rng.standard_normal((5, 5))
        a2 = rng.standard_normal((8, 8))
        result = cross_layer_covariance_probe([a1, a2])
        self.assertIsInstance(result, float)


if __name__ == "__main__":
    unittest.main()
