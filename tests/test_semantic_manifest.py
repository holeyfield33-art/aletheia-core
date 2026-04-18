"""Tests for core.semantic_manifest — Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from core.semantic_manifest import SemanticManifest, SemanticPatternEntry


class TestSemanticPatternEntry:
    def test_valid_entry(self):
        entry = SemanticPatternEntry(
            id="pat_001",
            text="exfiltrate data externally",
            category="direct_exfiltration",
            severity="HIGH",
            actions=["exfil"],
            objects=["data_asset"],
        )
        assert entry.id == "pat_001"
        assert entry.enabled is True

    def test_severity_normalized_to_upper(self):
        entry = SemanticPatternEntry(
            id="pat_002",
            text="delete all records",
            category="data_destruction",
            severity="critical",
        )
        assert entry.severity == "CRITICAL"

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError, match="severity"):
            SemanticPatternEntry(
                id="pat_003",
                text="some pattern",
                category="test",
                severity="EXTREME",
            )

    def test_text_min_length(self):
        with pytest.raises(ValidationError):
            SemanticPatternEntry(
                id="pat_004",
                text="ab",  # too short
                category="test",
            )


class TestSemanticManifest:
    def test_valid_manifest(self):
        manifest = SemanticManifest(
            version="1.0.0",
            entries=[
                SemanticPatternEntry(
                    id="pat_001",
                    text="bypass authentication",
                    category="auth_bypass",
                ),
            ],
        )
        assert manifest.version == "1.0.0"
        assert manifest.vector_size == 384
        assert manifest.score_threshold == 0.45
        assert manifest.block_threshold == 0.60
        assert len(manifest.entries) == 1

    def test_threshold_validation_out_of_range(self):
        with pytest.raises(ValidationError, match="Threshold"):
            SemanticManifest(
                version="1.0.0",
                score_threshold=1.5,
            )

    def test_threshold_validation_negative(self):
        with pytest.raises(ValidationError, match="Threshold"):
            SemanticManifest(
                version="1.0.0",
                block_threshold=-0.1,
            )

    def test_empty_entries_allowed(self):
        manifest = SemanticManifest(version="1.0.0")
        assert manifest.entries == []

    def test_custom_model(self):
        manifest = SemanticManifest(
            version="2.0.0",
            embedding_model="BAAI/bge-small-en-v1.5",
            vector_size=384,
        )
        assert manifest.embedding_model == "BAAI/bge-small-en-v1.5"
