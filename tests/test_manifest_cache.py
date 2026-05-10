"""Tests for core.manifest_cache — vectorized manifest embedding and matching."""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
from sentence_transformers import SentenceTransformer

from core.manifest_cache import (
    ManifestCache,
    load_and_embed_manifest,
    match_payload,
)


class TestManifestCache(unittest.TestCase):
    """Test ManifestCache initialization and validation."""

    def test_cache_initialization_valid(self):
        """ManifestCache accepts valid entries and vectors."""
        entries = [{"id": "1", "text": "test"}]
        vectors = np.random.randn(1, 384)
        vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8)

        cache = ManifestCache(entries=entries, vectors=vectors)
        self.assertEqual(len(cache.entries), 1)
        self.assertEqual(cache.vectors.shape, (1, 384))

    def test_cache_shape_validation(self):
        """ManifestCache rejects mismatched entry/vector counts."""
        entries = [{"id": "1"}, {"id": "2"}]
        vectors = np.random.randn(1, 384)  # Only 1 vector for 2 entries

        with self.assertRaises(ValueError):
            ManifestCache(entries=entries, vectors=vectors)

    def test_cache_embedding_dimension_validation(self):
        """ManifestCache rejects wrong embedding dimensions."""
        entries = [{"id": "1"}]
        vectors = np.random.randn(1, 256)  # Wrong dim (should be 384)

        with self.assertRaises(ValueError):
            ManifestCache(entries=entries, vectors=vectors)


class TestLoadAndEmbedManifest(unittest.TestCase):
    """Test manifest loading and embedding."""

    def setUp(self):
        """Create a temporary manifest file."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manifest_path = Path(self.temp_dir.name) / "manifest.json"

        # Create test manifest
        self.test_manifest = {
            "version": "1.0",
            "entries": [
                {
                    "id": "test_1",
                    "text": "bypass authentication",
                    "category": "auth",
                    "severity": "high",
                },
                {
                    "id": "test_2",
                    "text": "exfiltrate data externally",
                    "category": "exfil",
                    "severity": "critical",
                },
            ],
        }
        with open(self.manifest_path, "w") as f:
            json.dump(self.test_manifest, f)

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_load_and_embed_manifest_success(self):
        """load_and_embed_manifest creates valid cache."""
        model = SentenceTransformer("all-MiniLM-L6-v2")
        cache = load_and_embed_manifest(str(self.manifest_path), model)

        self.assertEqual(len(cache.entries), 2)
        self.assertEqual(cache.vectors.shape, (2, 384))
        # Check L2 normalization (norm should be ~1.0)
        norms = np.linalg.norm(cache.vectors, axis=1)
        np.testing.assert_array_almost_equal(norms, np.ones(2), decimal=5)

    def test_load_and_embed_manifest_file_not_found(self):
        """load_and_embed_manifest raises FileNotFoundError for missing file."""
        model = SentenceTransformer("all-MiniLM-L6-v2")
        with self.assertRaises(FileNotFoundError):
            load_and_embed_manifest("/nonexistent/path.json", model)

    def test_load_and_embed_manifest_invalid_json(self):
        """load_and_embed_manifest raises JSONDecodeError for invalid JSON."""
        bad_path = Path(self.temp_dir.name) / "bad.json"
        bad_path.write_text("not valid json {")

        model = SentenceTransformer("all-MiniLM-L6-v2")
        with self.assertRaises(json.JSONDecodeError):
            load_and_embed_manifest(str(bad_path), model)

    def test_load_and_embed_manifest_missing_text_field(self):
        """load_and_embed_manifest raises ValueError if entry lacks 'text'."""
        bad_manifest = {
            "version": "1.0",
            "entries": [{"id": "test", "no_text_field": "oops"}],
        }
        bad_path = Path(self.temp_dir.name) / "bad_manifest.json"
        with open(bad_path, "w") as f:
            json.dump(bad_manifest, f)

        model = SentenceTransformer("all-MiniLM-L6-v2")
        with self.assertRaises(ValueError):
            load_and_embed_manifest(str(bad_path), model)


class TestMatchPayload(unittest.TestCase):
    """Test vectorized payload matching against cached manifest."""

    def setUp(self):
        """Set up a test cache."""
        self.mock_model = MagicMock()

        # Create mock embeddings
        self.known_pattern_embedding = np.zeros((1, 384))
        self.known_pattern_embedding[0, :100] = 1.0
        self.known_pattern_embedding = self.known_pattern_embedding / (
            np.linalg.norm(self.known_pattern_embedding) + 1e-8
        )

        self.benign_embedding = np.zeros((1, 384))
        self.benign_embedding[0, -100:] = 1.0
        self.benign_embedding = self.benign_embedding / (
            np.linalg.norm(self.benign_embedding) + 1e-8
        )

        self.mock_model.encode.side_effect = [
            self.known_pattern_embedding[0],  # First call (malicious text)
            self.benign_embedding[0],  # Second call (benign text)
        ]

        # Create test cache with orthogonal vectors
        cache_vectors = np.vstack(
            [
                self.known_pattern_embedding,
                self.benign_embedding,
            ]
        )

        self.test_cache = ManifestCache(
            entries=[
                {
                    "id": "malicious_1",
                    "text": "bypass authentication",
                    "category": "auth",
                },
                {
                    "id": "benign_1",
                    "text": "check system status",
                    "category": "monitoring",
                },
            ],
            vectors=cache_vectors,
        )

    def test_match_payload_finds_known_malicious_pattern(self):
        """match_payload finds known malicious patterns above threshold."""
        # Reset mock for fresh call
        self.mock_model.encode.side_effect = [self.known_pattern_embedding[0]]

        results = match_payload(
            "bypass authentication check",
            self.mock_model,
            self.test_cache,
            threshold=0.5,
        )

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "malicious_1")
        self.assertGreater(results[0]["score"], 0.5)

    def test_match_payload_returns_empty_below_threshold(self):
        """match_payload returns [] when best score is below threshold."""
        # Use a broad query vector that remains below a very high threshold.
        low_sim_query = np.ones(384)
        low_sim_query = low_sim_query / (np.linalg.norm(low_sim_query) + 1e-8)
        self.mock_model.encode.side_effect = [low_sim_query]

        results = match_payload(
            "check system health",
            self.mock_model,
            self.test_cache,
            threshold=0.95,  # Very high threshold
        )

        self.assertEqual(len(results), 0)

    def test_match_payload_returns_sorted_by_score(self):
        """match_payload returns results sorted descending by score."""
        # Create a cache with multiple similar vectors
        similar_vecs = np.random.randn(3, 384)
        norms = np.linalg.norm(similar_vecs, axis=1, keepdims=True)
        similar_vecs = similar_vecs / (norms + 1e-8)

        cache = ManifestCache(
            entries=[
                {"id": "e1", "text": "text1"},
                {"id": "e2", "text": "text2"},
                {"id": "e3", "text": "text3"},
            ],
            vectors=similar_vecs,
        )

        query = similar_vecs[0].copy()
        self.mock_model.encode.side_effect = [query]

        results = match_payload(
            "query text",
            self.mock_model,
            cache,
            threshold=0.0,  # Accept all
        )

        # Should be sorted descending
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_match_payload_rejects_invalid_threshold(self):
        """match_payload raises ValueError for out-of-range threshold."""
        with self.assertRaises(ValueError):
            match_payload("test", self.mock_model, self.test_cache, threshold=1.5)

        with self.assertRaises(ValueError):
            match_payload("test", self.mock_model, self.test_cache, threshold=-0.1)

    def test_match_payload_handles_empty_text(self):
        """match_payload returns [] for empty text."""
        results = match_payload("", self.mock_model, self.test_cache, threshold=0.5)
        self.assertEqual(results, [])

    def test_match_payload_enriches_entries_with_score(self):
        """match_payload adds 'score' field to returned entries."""
        self.mock_model.encode.side_effect = [self.known_pattern_embedding[0]]

        results = match_payload(
            "bypass auth",
            self.mock_model,
            self.test_cache,
            threshold=0.4,
        )

        self.assertGreater(len(results), 0)
        for result in results:
            self.assertIn("score", result)
            self.assertIsInstance(result["score"], float)
            self.assertGreaterEqual(result["score"], 0.4)


if __name__ == "__main__":
    unittest.main()
