"""Aletheia Core — Shared embedding service.

Lazy-loads the SentenceTransformer model once and exposes cosine-similarity
helpers used by both Judge and Nitpicker.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from core.config import settings

_logger = logging.getLogger("aletheia.embeddings")
_lock = threading.Lock()
_model = None  # lazy singleton
_LOCK_TIMEOUT_SECONDS = 120  # generous; model download may be slow


def _get_model():
    """Thread-safe lazy load of the SentenceTransformer model."""
    global _model
    if _model is None:
        acquired = _lock.acquire(timeout=_LOCK_TIMEOUT_SECONDS)
        if not acquired:
            raise RuntimeError(
                f"Embedding model lock not acquired within {_LOCK_TIMEOUT_SECONDS}s. "
                "Possible deadlock."
            )
        try:
            if _model is None:
                import os
                from sentence_transformers import SentenceTransformer

                token = os.getenv("HUGGING_FACE_HUB_TOKEN")
                _model = SentenceTransformer(
                    settings.embedding_model,
                    use_auth_token=token if token else False,
                )
        finally:
            _lock.release()
    return _model


def warm_up() -> None:
    """Eagerly load the embedding model and run a throwaway encode.

    Call this at application startup (e.g. FastAPI lifespan) to avoid
    the ~2 s cold-start penalty on the first real request.
    """
    model = _get_model()
    # Run a trivial encode to JIT-compile any lazy internal buffers
    model.encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)


_MAX_ENCODE_TEXTS = 1000
_MAX_TOTAL_TEXT_BYTES = 500_000  # 500 KB total


def encode(texts: list[str]) -> NDArray[np.float32]:
    """Encode a batch of texts into normalized embeddings."""
    if not texts:
        raise ValueError("texts must be non-empty")
    if len(texts) > _MAX_ENCODE_TEXTS:
        raise ValueError(f"Too many texts to embed: {len(texts)} (max {_MAX_ENCODE_TEXTS})")
    total_size = sum(len(t) for t in texts)
    if total_size > _MAX_TOTAL_TEXT_BYTES:
        raise ValueError(
            f"Total text size {total_size} exceeds limit {_MAX_TOTAL_TEXT_BYTES}"
        )
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> NDArray[np.float32]:
    """Cosine similarity between two sets of normalized vectors.

    Returns a matrix of shape (len(a), len(b)).
    """
    # Vectors are already L2-normalized, so dot product == cosine similarity.
    return np.dot(a, b.T)
