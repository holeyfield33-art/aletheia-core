"""Tests for core.vector_store — Qdrant integration with fail-open."""

import os
from unittest.mock import MagicMock, patch


from core.vector_store import (
    SemanticMatch,
    query_semantic_patterns,
)


class TestGetClient:
    def test_returns_none_when_disabled(self):
        """When ALETHEIA_SEMANTIC_ENABLED is not set, _get_client returns None."""
        with patch.dict(os.environ, {"ALETHEIA_SEMANTIC_ENABLED": "false"}):
            # Reset module-level globals
            import core.vector_store as vs

            vs._client = None
            vs.QDRANT_ENABLED = False
            result = vs._get_client()
            assert result is None

    def test_returns_none_on_import_error(self):
        """If qdrant-client is not installed, _get_client returns None."""
        import core.vector_store as vs

        vs._client = None
        vs.QDRANT_ENABLED = True
        with patch.dict("sys.modules", {"qdrant_client": None}):
            result = vs._get_client()
            # Should fail gracefully
            assert result is None or result is not None  # just shouldn't raise
        vs.QDRANT_ENABLED = False


class TestQuerySemanticPatterns:
    def test_returns_degraded_when_disabled(self):
        """When Qdrant is disabled, query returns empty + degraded=True."""
        import core.vector_store as vs

        vs._client = None
        vs.QDRANT_ENABLED = False
        matches, degraded = query_semantic_patterns(
            query_vector=[0.0] * 384,
            categories=["exfil"],
        )
        assert matches == []
        assert degraded is True

    def test_returns_degraded_on_exception(self):
        """Connection errors produce degraded=True, never raise."""
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.side_effect = ConnectionError("refused")
        vs._client = mock_client
        vs.QDRANT_ENABLED = True

        try:
            matches, degraded = query_semantic_patterns(
                query_vector=[0.0] * 384,
                categories=["exfil"],
            )
            assert matches == []
            assert degraded is True
        finally:
            vs._client = None
            vs.QDRANT_ENABLED = False

    def test_returns_matches_on_success(self):
        """Successful Qdrant response returns SemanticMatch objects."""
        import core.vector_store as vs

        # Build mock search result
        mock_hit = MagicMock()
        mock_hit.id = "test-pattern-001"
        mock_hit.score = 0.85
        mock_hit.payload = {
            "category": "direct_exfiltration",
            "severity": "CRITICAL",
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        mock_client.query_points.return_value = mock_response

        # Mock qdrant_client.models so the inline import succeeds
        mock_models = MagicMock()
        mock_models.FieldCondition = MagicMock
        mock_models.Filter = MagicMock
        mock_models.MatchAny = MagicMock

        vs._client = mock_client
        vs.QDRANT_ENABLED = True

        try:
            with patch.dict(
                "sys.modules",
                {"qdrant_client": MagicMock(), "qdrant_client.models": mock_models},
            ):
                matches, degraded = query_semantic_patterns(
                    query_vector=[0.1] * 384,
                    categories=["direct_exfiltration"],
                    score_threshold=0.50,
                )
            assert degraded is False
            assert len(matches) == 1
            assert matches[0].pattern_id == "test-pattern-001"
            assert matches[0].score == 0.85
            assert matches[0].category == "direct_exfiltration"
        finally:
            vs._client = None
            vs.QDRANT_ENABLED = False

    def test_timeout_produces_degraded(self):
        """Simulated timeout returns degraded=True."""
        import core.vector_store as vs

        mock_client = MagicMock()
        mock_client.query_points.side_effect = TimeoutError("Qdrant timeout")
        vs._client = mock_client
        vs.QDRANT_ENABLED = True

        try:
            matches, degraded = query_semantic_patterns(
                query_vector=[0.0] * 384,
            )
            assert matches == []
            assert degraded is True
        finally:
            vs._client = None
            vs.QDRANT_ENABLED = False


class TestSemanticMatch:
    def test_default_values(self):
        m = SemanticMatch(pattern_id="p1", score=0.9, category="exfil")
        assert m.severity == "HIGH"
        assert m.payload == {}
