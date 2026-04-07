"""Enterprise-grade tests for core/embeddings.py.

Covers:
- cosine_similarity() output shape, dtype, and numerical correctness
- Identical vectors → similarity 1.0; orthogonal vectors → similarity 0.0
- Batch encoding shape and normalization invariant (L2-norm == 1)
- encode() returns float32 NDArray with correct dimensions
- Thread safety of the lazy model singleton (_get_model)
- warm_up() is idempotent and safe to call multiple times
- cosine_similarity() asymmetric matrix (m×k dot n×k → m×n)
"""

from __future__ import annotations

import threading
import unittest

import numpy as np

from core.embeddings import cosine_similarity, encode, warm_up


class TestCosimeSimilarityNumerics(unittest.TestCase):
    """Direct numerical correctness of cosine_similarity()."""

    def test_identical_unit_vectors_yield_1(self) -> None:
        """Identical normalized vectors have cosine similarity of 1.0."""
        a = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        result = cosine_similarity(a, a)
        self.assertAlmostEqual(float(result[0, 0]), 1.0, places=6)

    def test_opposite_unit_vectors_yield_minus_1(self) -> None:
        """Anti-parallel unit vectors have cosine similarity of -1.0."""
        a = np.array([[1.0, 0.0]], dtype=np.float32)
        b = np.array([[-1.0, 0.0]], dtype=np.float32)
        result = cosine_similarity(a, b)
        self.assertAlmostEqual(float(result[0, 0]), -1.0, places=6)

    def test_orthogonal_unit_vectors_yield_0(self) -> None:
        """Orthogonal unit vectors have cosine similarity of 0.0."""
        a = np.array([[1.0, 0.0]], dtype=np.float32)
        b = np.array([[0.0, 1.0]], dtype=np.float32)
        result = cosine_similarity(a, b)
        self.assertAlmostEqual(float(result[0, 0]), 0.0, places=6)

    def test_output_shape_single_pair(self) -> None:
        """Single-pair input → output shape (1, 1)."""
        a = np.array([[1.0, 0.0]], dtype=np.float32)
        b = np.array([[0.0, 1.0]], dtype=np.float32)
        result = cosine_similarity(a, b)
        self.assertEqual(result.shape, (1, 1))

    def test_output_shape_m_by_n_matrix(self) -> None:
        """m vectors vs n vectors → output shape (m, n)."""
        a = np.random.randn(3, 8).astype(np.float32)
        b = np.random.randn(5, 8).astype(np.float32)
        # Normalize
        a /= np.linalg.norm(a, axis=1, keepdims=True)
        b /= np.linalg.norm(b, axis=1, keepdims=True)
        result = cosine_similarity(a, b)
        self.assertEqual(result.shape, (3, 5))

    def test_output_range_bounded_minus1_to_1(self) -> None:
        """All entries must lie in [-1, 1] for normalized input vectors."""
        rng = np.random.RandomState(42)
        a = rng.randn(10, 16).astype(np.float32)
        b = rng.randn(10, 16).astype(np.float32)
        a /= np.linalg.norm(a, axis=1, keepdims=True)
        b /= np.linalg.norm(b, axis=1, keepdims=True)
        result = cosine_similarity(a, b)
        self.assertTrue(np.all(result >= -1.0 - 1e-5),
                        f"Min value {result.min():.6f} below -1")
        self.assertTrue(np.all(result <= 1.0 + 1e-5),
                        f"Max value {result.max():.6f} above 1")

    def test_diagonal_self_similarity_is_1(self) -> None:
        """Each row of a matrix dotted with itself should give 1.0."""
        rng = np.random.RandomState(7)
        a = rng.randn(4, 8).astype(np.float32)
        a /= np.linalg.norm(a, axis=1, keepdims=True)
        result = cosine_similarity(a, a)
        for i in range(4):
            self.assertAlmostEqual(float(result[i, i]), 1.0, places=5,
                                   msg=f"Self-sim at [{i},{i}] != 1.0")

    def test_symmetry_property(self) -> None:
        """cosine_similarity(a, b)[i, j] == cosine_similarity(b, a)[j, i]."""
        rng = np.random.RandomState(13)
        a = rng.randn(3, 8).astype(np.float32)
        b = rng.randn(4, 8).astype(np.float32)
        a /= np.linalg.norm(a, axis=1, keepdims=True)
        b /= np.linalg.norm(b, axis=1, keepdims=True)
        ab = cosine_similarity(a, b)
        ba = cosine_similarity(b, a)
        np.testing.assert_allclose(ab, ba.T, atol=1e-5)

    def test_single_vector_vs_batch(self) -> None:
        """One query vector vs multiple database vectors: result shape (1, n)."""
        query = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        db = np.eye(3, dtype=np.float32)
        result = cosine_similarity(query, db)
        self.assertEqual(result.shape, (1, 3))
        self.assertAlmostEqual(float(result[0, 0]), 1.0, places=5)
        self.assertAlmostEqual(float(result[0, 1]), 0.0, places=5)
        self.assertAlmostEqual(float(result[0, 2]), 0.0, places=5)


class TestEncodeOutput(unittest.TestCase):
    """encode() must return normalized float32 vectors of consistent shape."""

    def test_returns_ndarray(self) -> None:
        result = encode(["hello world"])
        self.assertIsInstance(result, np.ndarray)

    def test_single_text_shape_is_1_by_dim(self) -> None:
        result = encode(["hello"])
        self.assertEqual(result.ndim, 2)
        self.assertEqual(result.shape[0], 1)
        self.assertGreater(result.shape[1], 0)

    def test_batch_shape_rows_match_input_count(self) -> None:
        texts = ["first", "second", "third", "fourth"]
        result = encode(texts)
        self.assertEqual(result.shape[0], len(texts))

    def test_all_texts_same_embedding_dimension(self) -> None:
        short = encode(["hi"])
        long_text = encode(["This is a much longer sentence with many more tokens."])
        self.assertEqual(short.shape[1], long_text.shape[1])

    def test_vectors_are_l2_normalized(self) -> None:
        """encode() must return L2-normalized (unit) vectors."""
        result = encode(["The quick brown fox", "Lazy dog", "Security audit"])
        norms = np.linalg.norm(result, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5,
                                   err_msg="Vectors are not L2-normalized")

    def test_dtype_is_float32(self) -> None:
        result = encode(["test"])
        self.assertEqual(result.dtype, np.float32)

    def test_empty_string_encodes_without_error(self) -> None:
        """Empty string should not raise — model must handle it gracefully."""
        result = encode([""])
        self.assertEqual(result.shape[0], 1)

    def test_very_long_text_encodes_without_error(self) -> None:
        long_text = "word " * 512  # far beyond typical token limit
        result = encode([long_text])
        self.assertEqual(result.shape[0], 1)

    def test_unicode_text_encodes_without_error(self) -> None:
        result = encode(["こんにちは世界 مرحبا بالعالم Привет мир"])
        self.assertEqual(result.shape[0], 1)

    def test_deterministic_encoding(self) -> None:
        """Same text must produce identical embedding on repeated calls."""
        text = "deterministic security audit test"
        r1 = encode([text])
        r2 = encode([text])
        np.testing.assert_array_equal(r1, r2)

    def test_different_texts_produce_different_embeddings(self) -> None:
        r1 = encode(["transfer funds to offshore account"])
        r2 = encode(["generate the quarterly revenue report"])
        # Should not be identical
        self.assertFalse(np.array_equal(r1, r2))

    def test_semantically_similar_texts_high_cosine_similarity(self) -> None:
        """Semantically similar sentences should have high cosine similarity."""
        a = encode(["bypass the authentication system"])
        b = encode(["skip the login verification step"])
        sim = float(cosine_similarity(a, b)[0, 0])
        self.assertGreater(sim, 0.60,
                           f"Expected high similarity, got {sim:.4f}")

    def test_semantically_dissimilar_texts_lower_cosine_similarity(self) -> None:
        """Very different sentences should have lower cosine similarity."""
        a = encode(["transfer funds to offshore account"])
        b = encode(["the weather is nice today"])
        sim = float(cosine_similarity(a, b)[0, 0])
        # These should not be extremely similar (< 0.8)
        self.assertLess(sim, 0.80,
                        f"Expected lower similarity for unrelated texts, got {sim:.4f}")


class TestWarmUp(unittest.TestCase):
    """warm_up() must succeed and be idempotent."""

    def test_warm_up_does_not_raise(self) -> None:
        warm_up()  # first call

    def test_warm_up_is_idempotent(self) -> None:
        """Calling warm_up() multiple times in a row must not raise."""
        for _ in range(3):
            warm_up()

    def test_encode_works_before_explicit_warm_up(self) -> None:
        """Model loads lazily on first encode call even without warm_up()."""
        result = encode(["test sentence"])
        self.assertIsNotNone(result)


class TestThreadSafetyLazyLoad(unittest.TestCase):
    """The lazy singleton model load must be safe under concurrent access."""

    def test_concurrent_encode_calls_return_consistent_results(self) -> None:
        """Multiple threads calling encode() simultaneously must all succeed."""
        text = "concurrent embedding test"
        results = []
        errors = []

        def worker():
            try:
                r = encode([text])
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread errors: {errors}")
        self.assertEqual(len(results), 8)
        # All results should be identical (deterministic)
        for r in results[1:]:
            np.testing.assert_array_equal(
                results[0], r, err_msg="Concurrent encode returned inconsistent results"
            )

    def test_concurrent_cosine_similarity_calls_are_stable(self) -> None:
        """cosine_similarity() is a pure numpy op — should be perfectly thread-safe."""
        a = encode(["security audit"])
        b = encode(["financial transfer"])
        errors = []
        sims = []

        def compute():
            try:
                sim = cosine_similarity(a, b)
                sims.append(float(sim[0, 0]))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=compute) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread errors: {errors}")
        # All threads should see the same value
        self.assertEqual(len(set(round(s, 5) for s in sims)), 1,
                         "Concurrent cosine_similarity results diverged")


if __name__ == "__main__":
    unittest.main()
