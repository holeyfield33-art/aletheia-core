"""Near-duplicate query detection using embedding similarity.

Mitigates slow model-extraction attacks by flagging bursts of
semantically-near-duplicate queries within a sliding window.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from typing import Tuple

import numpy as np

_logger = logging.getLogger("aletheia.economics.duplicate_detector")


@dataclass
class DuplicateDetectorConfig:
    similarity_threshold: float = 0.95  # cosine similarity
    window_size: int = 100  # embeddings to remember
    rate_limit_per_window: int = 5  # max near‑duplicates before flagging
    embedding_dim: int = 384  # all‑MiniLM‑L6‑v2 dimension


class NearDuplicateDetector:
    """Sliding-window near-duplicate detector over embedding cosine similarity."""

    def __init__(self, config: DuplicateDetectorConfig | None = None) -> None:
        self.config = config or DuplicateDetectorConfig()
        # Pre-normalised rows stored as a deque of 1-D arrays (unit norm).
        self._normed_history: deque[np.ndarray] = deque(
            maxlen=self.config.window_size,
        )
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def check_and_record(
        self,
        embedding: np.ndarray,
    ) -> Tuple[bool, int]:
        """Check if *embedding* is near-duplicate of recent queries.

        Returns
        -------
        (is_flagged, duplicate_count)
            *is_flagged* is ``True`` when *duplicate_count* ≥
            ``rate_limit_per_window``.

        Raises
        ------
        ValueError
            If *embedding* has the wrong dimensionality.
        """
        embedding = np.asarray(embedding, dtype=np.float64).ravel()
        if embedding.shape[0] != self.config.embedding_dim:
            raise ValueError(
                f"Expected embedding dim {self.config.embedding_dim}, "
                f"got {embedding.shape[0]}"
            )

        normed = self._unit_norm(embedding)

        with self._lock:
            if len(self._normed_history) == 0:
                self._normed_history.append(normed)
                return False, 0

            # Vectorised cosine similarity (all history in one matmul)
            matrix = np.stack(list(self._normed_history))  # (N, D)
            sims = matrix @ normed  # (N,)
            duplicate_count = int(
                np.count_nonzero(sims >= self.config.similarity_threshold)
            )

            is_flagged = duplicate_count >= self.config.rate_limit_per_window

            if is_flagged:
                _logger.warning(
                    "Near-duplicate burst detected: %d duplicates in window "
                    "(threshold %d)",
                    duplicate_count,
                    self.config.rate_limit_per_window,
                )

            self._normed_history.append(normed)

        return is_flagged, duplicate_count

    def reset(self) -> None:
        """Clear the sliding window."""
        with self._lock:
            self._normed_history.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _unit_norm(v: np.ndarray) -> np.ndarray:
        """Return *v* / ||v||.  Zero vectors map to zero."""
        n = np.linalg.norm(v)
        if n == 0.0:
            return v
        return v / n
