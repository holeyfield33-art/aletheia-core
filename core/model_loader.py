"""Helpers for loading sentence-embedding models with local caching.

Uses fastembed (ONNX Runtime backend) so that PyTorch is not required.
This keeps the Render free-tier build well under the 512 MB RAM limit.
The public return value exposes a .encode() shim compatible with the
previous sentence-transformers API used by core/embeddings.py.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

_logger = logging.getLogger("aletheia.model_loader")

# Default cache location used by fastembed; can be overridden.
_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "aletheia" / "models"


def _cache_dir() -> Path:
    override = os.getenv("ALETHEIA_MODEL_CACHE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return _DEFAULT_CACHE_DIR


class _SentenceTransformerCompat:
    """Thin shim so callers can use .encode(texts, normalize_embeddings=True)."""

    def __init__(self, model_name: str, cache_dir: Path) -> None:
        from fastembed import TextEmbedding

        cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_dir),
        )

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,  # fastembed always normalizes; param kept for API compat
        show_progress_bar: bool = False,  # ignored; fastembed doesn't show progress bars
    ):
        import numpy as np

        embeddings = list(self._model.embed(texts))
        return np.array(embeddings, dtype=np.float32)


def load_cached_sentence_transformer(
    model_name: str, token: str | None = None
) -> _SentenceTransformerCompat:
    """Return a fastembed-backed encoder with the sentence-transformers .encode() API.

    The model is downloaded once by fastembed into ALETHEIA_MODEL_CACHE_DIR
    (default ~/.cache/aletheia/models/) and reused on subsequent calls.

    The ``token`` parameter is accepted for API compatibility but fastembed
    downloads from its own mirror and does not use HuggingFace auth tokens.
    """
    if token:
        _logger.debug(
            "HF token provided but fastembed does not use HF auth tokens. Ignoring."
        )
    return _SentenceTransformerCompat(model_name, _cache_dir())
