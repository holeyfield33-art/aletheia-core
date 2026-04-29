"""Tests for near-duplicate query detection (Phase 5)."""

from __future__ import annotations

import threading
import unittest

import numpy as np

from economics.duplicate_detector import (
    DuplicateDetectorConfig,
    NearDuplicateDetector,
)


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


def _random_emb(gen: np.random.Generator, dim: int = 384) -> np.ndarray:
    v = gen.standard_normal(dim)
    return v / np.linalg.norm(v)


class TestBasicDetection(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = DuplicateDetectorConfig(
            similarity_threshold=0.95,
            window_size=50,
            rate_limit_per_window=3,
            embedding_dim=384,
        )
        self.det = NearDuplicateDetector(self.cfg)

    def test_first_query_never_flagged(self) -> None:
        emb = _random_emb(_rng())
        flagged, count = self.det.check_and_record(emb)
        self.assertFalse(flagged)
        self.assertEqual(count, 0)

    def test_unique_queries_not_flagged(self) -> None:
        gen = _rng(1)
        for _ in range(20):
            flagged, _ = self.det.check_and_record(_random_emb(gen))
            self.assertFalse(flagged)

    def test_identical_queries_flagged_after_threshold(self) -> None:
        emb = _random_emb(_rng())
        for i in range(self.cfg.rate_limit_per_window):
            flagged, _ = self.det.check_and_record(emb)
            # First rate_limit_per_window insertions: count < threshold
            self.assertFalse(flagged)
        # Next one should trip
        flagged, count = self.det.check_and_record(emb)
        self.assertTrue(flagged)
        self.assertGreaterEqual(count, self.cfg.rate_limit_per_window)

    def test_near_duplicate_above_threshold(self) -> None:
        gen = _rng(5)
        base = _random_emb(gen)
        for _ in range(self.cfg.rate_limit_per_window):
            # Tiny perturbation → cosine > 0.95
            noisy = base + gen.standard_normal(384) * 0.001
            self.det.check_and_record(noisy)
        flagged, _ = self.det.check_and_record(base)
        self.assertTrue(flagged)


class TestWindowEviction(unittest.TestCase):
    def test_old_entries_evicted(self) -> None:
        cfg = DuplicateDetectorConfig(
            window_size=5,
            rate_limit_per_window=3,
            embedding_dim=384,
        )
        det = NearDuplicateDetector(cfg)
        gen = _rng(10)
        dup = _random_emb(gen)
        # Fill window with dups
        for _ in range(5):
            det.check_and_record(dup)
        # Push them out with unique queries
        for _ in range(5):
            det.check_and_record(_random_emb(gen))
        # Now the dup should no longer be in the window
        flagged, count = det.check_and_record(dup)
        self.assertEqual(count, 0)
        self.assertFalse(flagged)


class TestDimensionValidation(unittest.TestCase):
    def test_wrong_dim_raises(self) -> None:
        det = NearDuplicateDetector(DuplicateDetectorConfig(embedding_dim=384))
        with self.assertRaises(ValueError) as ctx:
            det.check_and_record(np.zeros(128))
        self.assertIn("384", str(ctx.exception))

    def test_2d_input_flattened(self) -> None:
        det = NearDuplicateDetector(DuplicateDetectorConfig(embedding_dim=384))
        emb = _random_emb(_rng()).reshape(1, 384)
        flagged, count = det.check_and_record(emb)
        self.assertFalse(flagged)
        self.assertEqual(count, 0)


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors(self) -> None:
        v = _random_emb(_rng())
        normed = NearDuplicateDetector._unit_norm(v)
        sim = float(np.dot(normed, normed))
        self.assertAlmostEqual(sim, 1.0, places=6)

    def test_orthogonal_vectors(self) -> None:
        a = np.zeros(384)
        b = np.zeros(384)
        a[0] = 1.0
        b[1] = 1.0
        na = NearDuplicateDetector._unit_norm(a)
        nb = NearDuplicateDetector._unit_norm(b)
        self.assertAlmostEqual(float(np.dot(na, nb)), 0.0)

    def test_zero_vector_safe(self) -> None:
        normed = NearDuplicateDetector._unit_norm(np.zeros(384))
        self.assertAlmostEqual(np.linalg.norm(normed), 0.0)


class TestReset(unittest.TestCase):
    def test_reset_clears_history(self) -> None:
        det = NearDuplicateDetector(
            DuplicateDetectorConfig(
                rate_limit_per_window=2,
                embedding_dim=384,
            )
        )
        emb = _random_emb(_rng())
        for _ in range(3):
            det.check_and_record(emb)
        det.reset()
        flagged, count = det.check_and_record(emb)
        self.assertFalse(flagged)
        self.assertEqual(count, 0)


class TestThreadSafety(unittest.TestCase):
    def test_concurrent_inserts_no_crash(self) -> None:
        det = NearDuplicateDetector(
            DuplicateDetectorConfig(
                window_size=200,
                embedding_dim=384,
            )
        )
        gen = _rng(99)
        embeddings = [_random_emb(gen) for _ in range(50)]
        errors: list[Exception] = []

        def worker(embs: list[np.ndarray]) -> None:
            try:
                for e in embs:
                    det.check_and_record(e)
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=worker, args=(embeddings[:25],))
        t2 = threading.Thread(target=worker, args=(embeddings[25:],))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(errors, [])

    def test_concurrent_duplicates_all_counted(self) -> None:
        """All duplicate inserts should be recorded in the history."""
        det = NearDuplicateDetector(
            DuplicateDetectorConfig(
                window_size=200,
                rate_limit_per_window=100,
                embedding_dim=384,
            )
        )
        emb = _random_emb(_rng(42))
        n_threads = 4
        n_per_thread = 10

        def worker() -> None:
            for _ in range(n_per_thread):
                det.check_and_record(emb)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All 40 insertions should be in history
        self.assertEqual(len(det._normed_history), n_threads * n_per_thread)


class TestDefaultConfig(unittest.TestCase):
    def test_none_config_uses_defaults(self) -> None:
        det = NearDuplicateDetector()
        self.assertEqual(det.config.embedding_dim, 384)
        self.assertEqual(det.config.window_size, 100)


if __name__ == "__main__":
    unittest.main()
