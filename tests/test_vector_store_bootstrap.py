"""Tests for Qdrant collection bootstrap and query coverage gaps in core/vector_store.py."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_hit(
    pattern_id: str = "pe_001",
    score: float = 0.9,
    category: str = "policy_evasion",
    severity: str = "HIGH",
) -> MagicMock:
    hit = MagicMock()
    hit.id = pattern_id
    hit.score = score
    hit.payload = {
        "pattern_id": pattern_id,
        "category": category,
        "severity": severity,
    }
    return hit


def _mock_response(hits: list[MagicMock]) -> MagicMock:
    resp = MagicMock()
    resp.points = hits
    return resp


# ---------------------------------------------------------------------------
# ensure_qdrant_collection
# ---------------------------------------------------------------------------


class TestEnsureQdrantCollection:
    def test_returns_false_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "false")
        import core.vector_store as vs

        importlib.reload(vs)
        with patch.object(vs, "_get_client", return_value=None):
            assert vs.ensure_qdrant_collection() is False

    def test_returns_false_when_client_unavailable(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        with patch.object(vs, "_get_client", return_value=None):
            assert vs.ensure_qdrant_collection() is False

    def test_creates_collection_when_missing(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])

        with patch.object(vs, "_get_client", return_value=mock_client):
            result = vs.ensure_qdrant_collection(vector_size=384)

        assert result is True
        mock_client.create_collection.assert_called_once()
        # Verify the collection name used
        kwargs = mock_client.create_collection.call_args.kwargs
        assert kwargs.get("collection_name") == vs.QDRANT_COLLECTION

    def test_skips_creation_when_collection_already_exists(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        existing = MagicMock()
        existing.name = vs.QDRANT_COLLECTION
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[existing])

        with patch.object(vs, "_get_client", return_value=mock_client):
            result = vs.ensure_qdrant_collection()

        assert result is True
        mock_client.create_collection.assert_not_called()

    def test_creates_all_payload_indexes(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])

        with patch.object(vs, "_get_client", return_value=mock_client):
            vs.ensure_qdrant_collection()

        index_fields = [
            c.kwargs.get("field_name") or c.args[1]
            for c in mock_client.create_payload_index.call_args_list
        ]
        for expected in ("category", "severity", "tenant_id", "manifest_version"):
            assert expected in index_fields

    def test_duplicate_index_exception_is_ignored(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client.create_payload_index.side_effect = Exception("already exists")

        with patch.object(vs, "_get_client", return_value=mock_client):
            result = vs.ensure_qdrant_collection()

        assert result is True  # should not propagate index-exists errors

    def test_returns_false_on_create_collection_exception(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client.create_collection.side_effect = RuntimeError("Qdrant unavailable")

        with patch.object(vs, "_get_client", return_value=mock_client):
            result = vs.ensure_qdrant_collection()

        assert result is False

    def test_uses_custom_collection_name(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])

        with patch.object(vs, "_get_client", return_value=mock_client):
            vs.ensure_qdrant_collection(collection_name="my_custom_col")

        kwargs = mock_client.create_collection.call_args.kwargs
        assert kwargs.get("collection_name") == "my_custom_col"


# ---------------------------------------------------------------------------
# query_semantic_patterns — category filtering
# ---------------------------------------------------------------------------


class TestQuerySemanticPatternsCategoryFiltering:
    def test_query_with_category_filter_passes_filter_to_qdrant(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response(
            [_mock_hit(category="policy_evasion")]
        )

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(
                query_vector=[0.0] * 384,
                categories=["policy_evasion"],
            )

        assert degraded is False
        assert len(matches) == 1
        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs.get("query_filter") is not None

    def test_query_without_categories_passes_no_filter(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response([])

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(
                query_vector=[0.0] * 384,
                categories=None,
            )

        assert degraded is False
        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs.get("query_filter") is None

    def test_limit_parameter_forwarded_to_qdrant(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response([])

        with patch.object(vs, "_get_client", return_value=mock_client):
            vs.query_semantic_patterns(query_vector=[0.0] * 384, limit=10)

        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs.get("limit") == 10

    def test_score_threshold_forwarded_to_qdrant(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response([])

        with patch.object(vs, "_get_client", return_value=mock_client):
            vs.query_semantic_patterns(query_vector=[0.0] * 384, score_threshold=0.75)

        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs.get("score_threshold") == 0.75

    def test_semantic_match_fields_populated_from_payload(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        hit = _mock_hit(
            "de_001", score=0.92, category="direct_exfiltration", severity="CRITICAL"
        )
        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response([hit])

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert degraded is False
        m = matches[0]
        assert m.pattern_id == "de_001"
        assert m.score == pytest.approx(0.92)
        assert m.category == "direct_exfiltration"
        assert m.severity == "CRITICAL"

    def test_missing_payload_fields_use_defaults(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        hit = MagicMock()
        hit.id = "fallback-id"
        hit.score = 0.8
        hit.payload = {}  # no fields at all
        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response([hit])

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert isinstance(matches, list)
        assert isinstance(degraded, bool)
        if matches:
            assert matches[0].pattern_id == "fallback-id"
            assert matches[0].category == "unknown"


# ---------------------------------------------------------------------------
# query_semantic_patterns — degraded mode
# ---------------------------------------------------------------------------


class TestQuerySemanticPatternsDegradedMode:
    def test_returns_degraded_true_when_client_is_none(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        with patch.object(vs, "_get_client", return_value=None):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert matches == []
        assert degraded is True

    def test_returns_degraded_true_on_connection_error(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.side_effect = ConnectionError("Qdrant unreachable")

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert matches == []
        assert degraded is True

    def test_returns_degraded_true_on_timeout_exception(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.side_effect = TimeoutError("timed out")

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert matches == []
        assert degraded is True

    def test_returns_degraded_true_on_generic_exception(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.side_effect = RuntimeError("unexpected")

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert matches == []
        assert degraded is True

    def test_empty_results_not_degraded(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response([])

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert matches == []
        assert degraded is False

    def test_multiple_hits_all_returned(self, monkeypatch):
        monkeypatch.setenv("ALETHEIA_SEMANTIC_ENABLED", "true")
        import core.vector_store as vs

        hits = [
            _mock_hit("pe_001", score=0.95, category="policy_evasion"),
            _mock_hit("de_001", score=0.88, category="direct_exfiltration"),
            _mock_hit("jb_001", score=0.81, category="jailbreak"),
        ]
        mock_client = MagicMock()
        mock_client.query_points.return_value = _mock_response(hits)

        with patch.object(vs, "_get_client", return_value=mock_client):
            matches, degraded = vs.query_semantic_patterns(query_vector=[0.0] * 384)

        assert degraded is False
        assert len(matches) == 3
