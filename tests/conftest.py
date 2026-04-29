"""Shared test fixtures for Aletheia Core test suite."""

from __future__ import annotations

import importlib.util
import os

# Auth is disabled for tests by default — existing tests don't supply API keys.
# Individual test classes can override this via patch.dict.
os.environ.setdefault("ALETHEIA_AUTH_DISABLED", "true")

# Shadow mode avoids the ALETHEIA_RECEIPT_SECRET requirement in startup checks.
os.environ.setdefault("ALETHEIA_MODE", "shadow")

# ---------------------------------------------------------------------------
# ML model mock — activated when huggingface_hub is not installed.
# Returns a deterministic fixed-dimension embedding so that semantic
# similarity tests can run without the full ML stack.
# ---------------------------------------------------------------------------
if importlib.util.find_spec("huggingface_hub") is None:
    import unittest.mock as _mock
    import numpy as _np

    class _StubModel:
        """Returns zero-vectors so cosine_similarity always returns 0.0."""

        def encode(
            self,
            texts: list[str],
            *,
            normalize_embeddings: bool = True,
            show_progress_bar: bool = False,
        ) -> "_np.ndarray":
            return _np.zeros((len(texts), 384), dtype=_np.float32)

    _stub = _StubModel()
    _patcher = _mock.patch(
        "core.model_loader.load_cached_sentence_transformer",
        return_value=_stub,
    )
    _patcher.start()
