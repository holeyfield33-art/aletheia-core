"""Shared test fixtures for Aletheia Core test suite."""

from __future__ import annotations

import hashlib
import os
from unittest.mock import patch

import numpy as np

import pytest

# Auth is disabled for tests by default — existing tests don't supply API keys.
# Individual test classes can override this via patch.dict.
os.environ.setdefault("ALETHEIA_AUTH_DISABLED", "true")

# Run tests in active mode by default so DENIED behavior is actually enforced.
os.environ.setdefault("ALETHEIA_MODE", "active")

# Active mode requires a receipt secret for startup checks.
os.environ.setdefault("ALETHEIA_RECEIPT_SECRET", "test-receipt-secret-32-characters")


@pytest.fixture()
def active_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_MODE", "active")


@pytest.fixture()
def shadow_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_MODE", "shadow")


def _is_fast_mock_enabled(request: pytest.FixtureRequest) -> bool:
    """Enable fast mocks unless a test is explicitly marked as integration."""
    if request.node.get_closest_marker("integration") is not None:
        return False
    # Some modules already encode "real model required" intent via a helper.
    module = getattr(request.node, "module", None)
    if module is not None and hasattr(module, "_needs_real_model"):
        return False
    return True


class _StubModel:
    """Deterministic embedding stub with sentence-transformers-compatible API."""

    dim = 384

    def _vector_for_text(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
        seed = int.from_bytes(digest[:8], "big")
        rng = np.random.default_rng(seed)
        vec = rng.random(self.dim, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32)

    def encode(
        self,
        texts,
        *,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ):
        if isinstance(texts, str):
            items = [texts]
            is_single = True
        else:
            items = list(texts)
            is_single = False

        matrix = np.stack([self._vector_for_text(t) for t in items])
        if not normalize_embeddings:
            matrix = matrix * 10.0
        if is_single:
            return matrix[0]
        return matrix


class _QdrantCollection:
    status = "green"


class _QdrantCollectionsResponse:
    def __init__(self) -> None:
        self.collections: list[object] = []


class _QdrantClientStub:
    """Small in-memory stand-in for Qdrant client behavior used in tests."""

    def search(self, *args, **kwargs):
        return []

    def query_points(self, *args, **kwargs):
        return []

    def get_collection(self, *args, **kwargs):
        return _QdrantCollection()

    def get_collections(self, *args, **kwargs):
        return _QdrantCollectionsResponse()

    def create_collection(self, *args, **kwargs):
        return None

    def create_payload_index(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def mock_sentence_transformer(request: pytest.FixtureRequest):
    """Skip heavyweight model initialization in unit tests."""
    if not _is_fast_mock_enabled(request):
        yield
        return

    stub = _StubModel()
    with (
        patch("core.model_loader.load_cached_sentence_transformer", return_value=stub),
        patch("core.embeddings.load_cached_sentence_transformer", return_value=stub),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_qdrant_client(request: pytest.FixtureRequest):
    """Prevent external Qdrant network dependencies in fast test mode."""
    if not _is_fast_mock_enabled(request):
        yield
        return

    stub = _QdrantClientStub()
    with patch("qdrant_client.QdrantClient", return_value=stub):
        # Reset lazy singleton so tests never reuse a real client.
        try:
            import core.vector_store as _vs

            _vs._client = None
        except Exception:
            pass
        yield


@pytest.fixture(autouse=True)
def mock_manifest_signing(request: pytest.FixtureRequest):
    """Bypass filesystem/signature coupling in unit tests."""
    if not _is_fast_mock_enabled(request):
        yield
        return

    with (
        patch("manifest.signing.verify_manifest_signature", return_value=None),
        patch("agents.judge_v1.verify_manifest_signature", return_value=None),
    ):
        yield
