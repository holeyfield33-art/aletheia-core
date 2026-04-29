"""Aletheia Core — Semantic manifest schema.

Defines the Pydantic models for the semantic pattern manifest that
feeds the Qdrant index.  The manifest is a JSON file listing blocked
patterns with metadata (category, severity, actions, objects) plus
model/threshold configuration.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Thresholds — per-category cosine-similarity block thresholds
# ---------------------------------------------------------------------------

_DEFAULT_THRESHOLD: float = 0.85


class ThresholdsConfig(BaseModel):
    """Per-category cosine-similarity block thresholds."""

    direct_exfiltration: float = 0.86
    policy_evasion: float = 0.84
    hybrid_composite: float = 0.82
    recon_alias: float = 0.88

    @field_validator("*", mode="before")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Threshold must be in [0.0, 1.0], got {v}")
        return v

    def get_threshold_for_category(self, category: str) -> float:
        """Return the category-specific threshold, or 0.85 if not found."""
        return getattr(self, category, _DEFAULT_THRESHOLD)


# ---------------------------------------------------------------------------
# Entry metadata
# ---------------------------------------------------------------------------


class EntryMetadata(BaseModel):
    """Metadata attached to each semantic pattern entry."""

    actions: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Single semantic entry
# ---------------------------------------------------------------------------

_VALID_CATEGORIES = {
    "direct_exfiltration",
    "policy_evasion",
    "hybrid_composite",
    "recon_alias",
}
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}


class SemanticEntry(BaseModel):
    """A single blocked pattern in the semantic manifest (v2 schema)."""

    id: str = Field(..., description="Unique pattern identifier")
    category: str = Field(..., description="Threat category")
    severity: str = Field(default="high", description="Severity band")
    text: str = Field(..., min_length=3, description="The blocked phrase")
    metadata: EntryMetadata = Field(default_factory=EntryMetadata)
    enabled: bool = Field(default=True, description="Whether this pattern is active")

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in _VALID_CATEGORIES:
            raise ValueError(f"category must be one of {_VALID_CATEGORIES}, got {v!r}")
        return v_lower

    @field_validator("severity")
    @classmethod
    def _valid_severity(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {_VALID_SEVERITIES}, got {v!r}")
        return v_lower


# ---------------------------------------------------------------------------
# Legacy entry (backward compat with v1 manifests)
# ---------------------------------------------------------------------------


class SemanticPatternEntry(BaseModel):
    """A single blocked pattern in the semantic manifest (v1 schema)."""

    id: str = Field(..., description="Unique pattern identifier")
    text: str = Field(..., min_length=3, description="The blocked phrase")
    category: str = Field(..., description="Threat category (e.g. direct_exfiltration)")
    severity: str = Field(
        default="HIGH",
        description="Severity band: LOW, MEDIUM, HIGH, CRITICAL",
    )
    actions: list[str] = Field(
        default_factory=list,
        description="Canonical action categories from symbolic narrowing",
    )
    objects: list[str] = Field(
        default_factory=list,
        description="Canonical object categories from symbolic narrowing",
    )
    enabled: bool = Field(default=True, description="Whether this pattern is active")

    @field_validator("severity")
    @classmethod
    def _severity_band(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"severity must be one of {allowed}, got {v!r}")
        return v_upper


# ---------------------------------------------------------------------------
# Top-level manifest
# ---------------------------------------------------------------------------


class SemanticManifest(BaseModel):
    """Top-level schema for the semantic pattern manifest file."""

    version: str = Field(..., description="Manifest version (semver)")
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace model used for index embeddings",
    )
    embedding_dim: int = Field(default=384, ge=1, le=4096)
    # Kept for backward-compat; prefer embedding_dim in new manifests
    vector_size: Optional[int] = Field(default=None, ge=1, le=4096)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    score_threshold: float = Field(
        default=0.45,
        description="Default cosine similarity floor for Qdrant queries",
    )
    block_threshold: float = Field(
        default=0.60,
        description="Fallback block threshold when category not in ThresholdsConfig",
    )
    entries: list[SemanticEntry] = Field(
        default_factory=list,
        description="List of blocked semantic patterns (v2 schema)",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("score_threshold", "block_threshold")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Threshold must be in [0.0, 1.0], got {v}")
        return v

    @model_validator(mode="after")
    def _backfill_vector_size(self) -> "SemanticManifest":
        if self.vector_size is None:
            self.vector_size = self.embedding_dim
        return self

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_threshold_for_category(self, category: str) -> float:
        """Return category-specific threshold via ThresholdsConfig."""
        return self.thresholds.get_threshold_for_category(category)

    def validate_entries(self) -> list[str]:
        """Check for duplicate IDs.  Returns list of error strings (empty = OK)."""
        seen: dict[str, int] = {}
        errors: list[str] = []
        for i, entry in enumerate(self.entries):
            if entry.id in seen:
                errors.append(
                    f"Duplicate entry ID {entry.id!r} at index {i} "
                    f"(first seen at index {seen[entry.id]})"
                )
            else:
                seen[entry.id] = i
        return errors
