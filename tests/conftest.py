"""Shared test fixtures for Aletheia Core test suite."""

from __future__ import annotations

import hashlib
import os
from unittest.mock import patch

import numpy as np

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Auth is disabled for tests by default — existing tests don't supply API keys.
# Individual test classes can override this via patch.dict.
os.environ.setdefault("ALETHEIA_AUTH_DISABLED", "true")

# Run tests in active mode by default so DENIED behavior is actually enforced.
os.environ.setdefault("ALETHEIA_MODE", "active")

# Active mode requires a receipt secret for startup checks; the secret is
# also retained for tests that explicitly opt back into the legacy HMAC path
# via `monkeypatch.setattr(settings, "require_ed25519_receipts", False)`.
os.environ.setdefault("ALETHEIA_RECEIPT_SECRET", "test-receipt-secret-32-characters")

# Provision an Ed25519 keypair for the test session. Required because the
# production default is now `require_ed25519_receipts=True` — tests that build
# receipts through the endpoint would otherwise get HMAC receipts that the
# verifier refuses. Generating at module load (once per session) keeps test
# startup fast and matches how a real deployment supplies these.
#
# Guard against three skip conditions: (1) the env var was actually set by a
# parent process; (2) a *_PATH variant points at an existing key file; (3)
# the var is defined but empty (common in CI matrix configs) — that's the same
# as unset for our purposes.
def _has_test_ed25519_keys() -> bool:
    if os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY", "").strip():
        return True
    path = os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", "").strip()
    return bool(path) and os.path.isfile(path)


if not _has_test_ed25519_keys():
    _test_priv = Ed25519PrivateKey.generate()
    _test_pub = _test_priv.public_key()
    os.environ["ALETHEIA_RECEIPT_PRIVATE_KEY"] = _test_priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    os.environ["ALETHEIA_RECEIPT_PUBLIC_KEY"] = _test_pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


@pytest.fixture()
def active_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_MODE", "active")


@pytest.fixture()
def shadow_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALETHEIA_MODE", "shadow")


def _is_fast_mock_enabled(request: pytest.FixtureRequest) -> bool:
    """Enable fast mocks unless a test is explicitly marked as integration."""
    # Adversarial / release-gate runs disable stubs globally so the suite
    # exercises real code paths instead of deterministic test doubles.
    if os.environ.get("ALETHEIA_DISABLE_TEST_STUBS", "").lower() in {"1", "true", "yes"}:
        return False
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
        patch("agents.judge.verify_manifest_signature", return_value=None),
    ):
        yield
