"""Helpers for loading Hugging Face sentence-transformer models with local caching."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path

from filelock import FileLock

_logger = logging.getLogger("aletheia.model_loader")


def _cache_root() -> Path:
    """Return the model cache root directory."""
    override = os.getenv("ALETHEIA_MODEL_CACHE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "aletheia" / "models"


def _model_hash(model_name: str) -> str:
    return hashlib.sha256(model_name.encode("utf-8")).hexdigest()


def _has_cached_weights(model_dir: Path) -> bool:
    if not model_dir.is_dir():
        return False
    return any(model_dir.rglob("pytorch_model.bin")) or any(
        model_dir.rglob("*.safetensors")
    )


def load_cached_sentence_transformer(
    model_name: str, token: str | None = None
) -> object:
    """Load a SentenceTransformer from a local cache or download it once.

    Cache path format:
        ~/.cache/aletheia/models/{sha256(model_name)}

    Override root with:
        ALETHEIA_MODEL_CACHE_DIR
    """
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    cache_root = _cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)

    model_dir = cache_root / _model_hash(model_name)
    if _has_cached_weights(model_dir):
        _logger.info("Loading model from local cache: %s", model_dir)
        return SentenceTransformer(str(model_dir))

    lock_path = cache_root / f"{model_dir.name}.lock"
    with FileLock(str(lock_path)):
        if not _has_cached_weights(model_dir):
            if model_dir.exists():
                shutil.rmtree(model_dir)

            tmp_dir = cache_root / f".{model_dir.name}.tmp"
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

            _logger.info("Downloading model %s into %s", model_name, model_dir)
            snapshot_download(  # nosec B615 – model_name is config-controlled, not user input
                repo_id=model_name,
                local_dir=str(tmp_dir),
                token=token or None,
            )
            tmp_dir.rename(model_dir)

        if not _has_cached_weights(model_dir):
            raise RuntimeError(
                f"Cached model at {model_dir} is missing pytorch_model.bin after download"
            )

    _logger.info("Loading model from local cache: %s", model_dir)
    return SentenceTransformer(str(model_dir))
