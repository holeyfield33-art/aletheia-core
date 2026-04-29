from __future__ import annotations

import importlib

import numpy as np
from fastapi.testclient import TestClient


def _build_test_client(monkeypatch) -> TestClient:
    import core.embeddings as emb

    class DummyModel:
        def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
            return np.zeros((len(texts), 8), dtype=np.float32)

    monkeypatch.setattr(
        emb,
        "load_cached_sentence_transformer",
        lambda *args, **kwargs: DummyModel(),
    )
    monkeypatch.setattr(emb, "_model", None)
    monkeypatch.setenv("ALETHEIA_AUTH_DISABLED", "true")

    module = importlib.import_module("bridge.fastapi_wrapper")
    module = importlib.reload(module)
    return TestClient(module.app, raise_server_exceptions=False)


def test_evaluate_rejects_oversized_payload(monkeypatch):
    client = _build_test_client(monkeypatch)
    body = {
        "payload": "x" * 2049,
        "origin": "trusted_admin",
        "action": "Read_Status",
    }
    resp = client.post("/v1/evaluate", json=body)
    assert resp.status_code == 422


def test_audit_rejects_oversized_payload(monkeypatch):
    client = _build_test_client(monkeypatch)
    body = {
        "payload": "x" * 2049,
        "origin": "trusted_admin",
        "action": "Read_Status",
    }
    resp = client.post("/v1/audit", json=body)
    assert resp.status_code == 422


def test_embeddings_truncate_input_before_model_encode(monkeypatch):
    import core.embeddings as emb

    captured: dict[str, object] = {}

    class DummyModel:
        def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
            captured["texts"] = texts
            return np.zeros((len(texts), 4), dtype=np.float32)

    monkeypatch.setattr(emb, "_get_model", lambda: DummyModel())

    long_text = "a" * 5000
    out = emb.encode([long_text])

    assert out.shape == (1, 4)
    seen = captured["texts"]
    assert isinstance(seen, list)
    assert len(seen) == 1
    assert len(seen[0]) == 2800
