"""Tests for core.semantic_manifest — Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from core.semantic_manifest import (
    EntryMetadata,
    SemanticEntry,
    SemanticManifest,
    SemanticPatternEntry,
    ThresholdsConfig,
)


class TestThresholdsConfig:
    def test_default_values(self):
        t = ThresholdsConfig()
        assert t.direct_exfiltration == 0.86
        assert t.policy_evasion == 0.84
        assert t.hybrid_composite == 0.82
        assert t.recon_alias == 0.88

    def test_get_threshold_for_known_category(self):
        t = ThresholdsConfig()
        assert t.get_threshold_for_category("direct_exfiltration") == 0.86

    def test_get_threshold_for_unknown_category(self):
        t = ThresholdsConfig()
        assert t.get_threshold_for_category("unknown_cat") == 0.85

    def test_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            ThresholdsConfig(direct_exfiltration=1.5)


class TestEntryMetadata:
    def test_defaults(self):
        m = EntryMetadata()
        assert m.actions == []
        assert m.objects == []
        assert m.channels == []

    def test_with_values(self):
        m = EntryMetadata(actions=["exfil"], objects=["data_asset"], channels=["email"])
        assert m.channels == ["email"]


class TestSemanticEntry:
    def test_valid_entry(self):
        entry = SemanticEntry(
            id="pat_001",
            text="exfiltrate data externally",
            category="direct_exfiltration",
            severity="high",
        )
        assert entry.id == "pat_001"
        assert entry.enabled is True
        assert entry.metadata.actions == []

    def test_severity_normalized_to_lower(self):
        entry = SemanticEntry(
            id="pat_002",
            text="delete all records",
            category="policy_evasion",
            severity="Critical",
        )
        assert entry.severity == "critical"

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError, match="severity"):
            SemanticEntry(
                id="pat_003",
                text="some pattern",
                category="direct_exfiltration",
                severity="EXTREME",
            )

    def test_invalid_category_rejected(self):
        with pytest.raises(ValidationError, match="category"):
            SemanticEntry(
                id="pat_004",
                text="some pattern",
                category="invalid_category",
            )

    def test_text_min_length(self):
        with pytest.raises(ValidationError):
            SemanticEntry(
                id="pat_005",
                text="ab",  # too short
                category="direct_exfiltration",
            )

    def test_metadata_with_channels(self):
        entry = SemanticEntry(
            id="pat_006",
            text="send via email",
            category="direct_exfiltration",
            metadata=EntryMetadata(
                actions=["exfil"],
                objects=["data_asset"],
                channels=["email", "api"],
            ),
        )
        assert entry.metadata.channels == ["email", "api"]


class TestSemanticPatternEntry:
    """Backward-compat v1 entry."""

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


class TestSemanticManifest:
    def test_valid_manifest(self):
        manifest = SemanticManifest(
            version="1.0.0",
            entries=[
                SemanticEntry(
                    id="pat_001",
                    text="bypass authentication",
                    category="policy_evasion",
                ),
            ],
        )
        assert manifest.version == "1.0.0"
        assert manifest.embedding_dim == 384
        assert manifest.vector_size == 384  # backfilled
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
            embedding_dim=384,
        )
        assert manifest.embedding_model == "BAAI/bge-small-en-v1.5"

    def test_get_threshold_for_category(self):
        manifest = SemanticManifest(version="1.0.0")
        assert manifest.get_threshold_for_category("direct_exfiltration") == 0.86
        assert manifest.get_threshold_for_category("unknown") == 0.85

    def test_validate_entries_no_duplicates(self):
        manifest = SemanticManifest(
            version="1.0.0",
            entries=[
                SemanticEntry(id="a", text="pattern one", category="policy_evasion"),
                SemanticEntry(id="b", text="pattern two", category="direct_exfiltration"),
            ],
        )
        assert manifest.validate_entries() == []

    def test_validate_entries_with_duplicates(self):
        manifest = SemanticManifest(
            version="1.0.0",
            entries=[
                SemanticEntry(id="dup", text="pattern one", category="policy_evasion"),
                SemanticEntry(id="dup", text="pattern two", category="direct_exfiltration"),
            ],
        )
        errors = manifest.validate_entries()
        assert len(errors) == 1
        assert "dup" in errors[0]

    def test_thresholds_config_embedded(self):
        manifest = SemanticManifest(
            version="1.0.0",
            thresholds=ThresholdsConfig(direct_exfiltration=0.90),
        )
        assert manifest.thresholds.direct_exfiltration == 0.90
        assert manifest.thresholds.policy_evasion == 0.84  # default unchanged

    def test_embedding_dim_backfills_vector_size(self):
        manifest = SemanticManifest(version="1.0.0", embedding_dim=512)
        assert manifest.vector_size == 512
