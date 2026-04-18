"""Aletheia Core — Semantic manifest schema.

Defines the Pydantic models for the semantic pattern manifest that
feeds the Qdrant index.  The manifest is a JSON file listing blocked
patterns with metadata (category, severity, actions, objects) plus
model/threshold configuration.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SemanticPatternEntry(BaseModel):
    """A single blocked pattern in the semantic manifest."""

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


class SemanticManifest(BaseModel):
    """Top-level schema for the semantic pattern manifest file."""

    version: str = Field(..., description="Manifest version (semver)")
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace model used for index embeddings",
    )
    vector_size: int = Field(default=384, ge=1, le=4096)
    score_threshold: float = Field(
        default=0.45,
        description="Default cosine similarity threshold for matches",
    )
    block_threshold: float = Field(
        default=0.60,
        description="Cosine similarity above which Qdrant match alone blocks",
    )
    entries: list[SemanticPatternEntry] = Field(
        default_factory=list,
        description="List of blocked semantic patterns",
    )

    @field_validator("score_threshold", "block_threshold")
    @classmethod
    def _threshold_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Threshold must be in [0.0, 1.0], got {v}")
        return v
