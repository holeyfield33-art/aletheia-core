# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Manifest embedding cache for startup-time computation.

Loads semantic_manifest.json and pre-computes all embeddings at startup,
then provides vectorized cosine similarity matching for per-request lookups.

This eliminates per-request embedding computation (~24s → <100ms latency).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
else:
    # Keep module importable in lightweight CI environments where
    # sentence-transformers is intentionally omitted.
    SentenceTransformer = Any


_logger = logging.getLogger("aletheia.manifest_cache")


@dataclass
class ManifestCache:
    """Pre-computed manifest embeddings and vectors."""

    entries: list[dict]  # raw manifest entries
    vectors: np.ndarray  # shape (N, 384), L2-normalized
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        """Validate cache structure."""
        if self.vectors.shape[0] != len(self.entries):
            raise ValueError(
                f"Mismatch: {len(self.entries)} entries but {self.vectors.shape[0]} vectors"
            )
        if self.vectors.shape[1] != 384:
            raise ValueError(f"Expected vectors dim=384, got {self.vectors.shape[1]}")
        # Ensure vectors are L2-normalized for cosine similarity via dot product
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        if not np.allclose(norms, 1.0, atol=1e-5):
            _logger.warning("Vectors not L2-normalized; normalizing now")
            self.vectors = self.vectors / (norms + 1e-8)


def load_and_embed_manifest(
    path: str,
    model: SentenceTransformer,
) -> ManifestCache:
    """Load manifest and pre-compute all embeddings.

    Args:
        path: Path to semantic_manifest.json
        model: SentenceTransformer instance for encoding

    Returns:
        ManifestCache with all entries and their normalized vectors

    Raises:
        FileNotFoundError: If manifest file not found
        json.JSONDecodeError: If manifest is not valid JSON
        ValueError: If manifest structure is invalid
    """
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    if not isinstance(manifest_data, dict):
        raise ValueError("Manifest root must be a JSON object")

    entries = manifest_data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("Manifest entries must be a list")

    if not entries:
        raise ValueError("Manifest has no entries")

    # Extract text field from each entry; raise if missing
    texts = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} is not a dict: {entry}")
        text = entry.get("text")
        if not isinstance(text, str):
            raise ValueError(f"Entry {i} missing or invalid 'text' field: {entry}")
        texts.append(text)

    # Encode all texts at once (vectorized)
    t0 = time.time()
    embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
    elapsed_ms = (time.time() - t0) * 1000

    if embeddings.shape[0] != len(entries):
        raise ValueError(
            f"Encoding returned {embeddings.shape[0]} vectors, expected {len(entries)}"
        )

    if embeddings.shape[1] != 384:
        raise ValueError(f"Expected embedding dim=384, got {embeddings.shape[1]}")

    # Normalize for L2 cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-8)

    _logger.info(
        "Manifest cache loaded: %d entries, %d dims, %.1f ms",
        len(entries),
        embeddings.shape[1],
        elapsed_ms,
    )

    model_name = getattr(model, "model_name", None) or "all-MiniLM-L6-v2"

    return ManifestCache(
        entries=entries,
        vectors=embeddings,
        model_name=model_name,
    )


def match_payload(
    text: str,
    model: SentenceTransformer,
    cache: ManifestCache,
    threshold: float,
) -> list[dict]:
    """Vectorized cosine similarity match against cached manifest.

    Encodes input text once and computes similarity to all cached vectors
    via single matrix multiplication. Returns entries above threshold,
    enriched with "score" field, sorted descending by score.

    Args:
        text: Input payload to match
        model: SentenceTransformer instance for encoding
        cache: Pre-computed ManifestCache
        threshold: Cosine similarity threshold [0, 1]

    Returns:
        List of matched entries (cache.entries with "score" field added),
        sorted descending by score. Empty list if no matches above threshold.

    Raises:
        ValueError: If model or cache invalid
    """
    if not text or not isinstance(text, str):
        return []

    if threshold < 0 or threshold > 1:
        raise ValueError(f"Threshold must be in [0, 1], got {threshold}")

    # Encode text once, normalize
    text_vec = model.encode(text, convert_to_numpy=True)
    if text_vec.shape[0] != 384:
        raise ValueError(f"Expected text embedding dim=384, got {text_vec.shape[0]}")
    text_vec = text_vec / (np.linalg.norm(text_vec) + 1e-8)

    # Vectorized cosine similarity: (1, 384) @ (384, N) = (1, N)
    scores = np.dot(text_vec, cache.vectors.T).flatten()

    # Find above-threshold matches
    above_threshold = np.where(scores >= threshold)[0]
    if len(above_threshold) == 0:
        return []

    # Construct result entries with scores, sorted descending
    results = []
    for idx in above_threshold:
        entry_copy = dict(cache.entries[idx])
        entry_copy["score"] = float(scores[idx])
        results.append(entry_copy)

    results.sort(key=lambda e: e["score"], reverse=True)
    return results
