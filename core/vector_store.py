"""Aletheia Core — Qdrant vector store integration.

Provides a thin async-safe wrapper around the Qdrant client for semantic
pattern matching.  All operations honour a configurable timeout and
fail-open (never raise into the caller) — the static pattern bank in
Nitpicker stays the safety floor.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from core.config import env_bool

_logger = logging.getLogger("aletheia.vector_store")

# ---------------------------------------------------------------------------
# Configuration (env → defaults)
# ---------------------------------------------------------------------------

QDRANT_URL: str = os.getenv("ALETHEIA_QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY: Optional[str] = os.getenv("ALETHEIA_QDRANT_API_KEY")
QDRANT_COLLECTION: str = os.getenv(
    "ALETHEIA_QDRANT_COLLECTION", "aletheia_semantic_patterns"
)
QDRANT_TIMEOUT_MS: int = int(os.getenv("ALETHEIA_QDRANT_TIMEOUT_MS", "120"))
QDRANT_ENABLED: bool = env_bool("ALETHEIA_SEMANTIC_ENABLED")

# ---------------------------------------------------------------------------
# Lazy Qdrant client singleton
# ---------------------------------------------------------------------------

_client = None
_client_lock = threading.Lock()
_CLIENT_INIT_TIMEOUT = 10  # seconds


@dataclass
class SemanticMatch:
    """A single scored hit from the vector store."""

    pattern_id: str
    score: float
    category: str
    severity: str = "HIGH"
    payload: dict = field(default_factory=dict)


def _get_client():
    """Thread-safe lazy init of the Qdrant client.  Returns ``None`` if
    the client cannot be created (dependency missing, connection refused,
    etc.) — callers must treat ``None`` as *degraded mode*.
    """
    global _client
    if not QDRANT_ENABLED:
        return None
    if _client is not None:
        return _client
    acquired = _client_lock.acquire(timeout=_CLIENT_INIT_TIMEOUT)
    if not acquired:
        _logger.warning("Qdrant client lock timeout — running degraded")
        return None
    try:
        if _client is None:
            try:
                from qdrant_client import QdrantClient  # type: ignore[import-untyped]

                _client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=QDRANT_TIMEOUT_MS / 1000.0,
                )
                _logger.info("Qdrant client connected to %s", QDRANT_URL)
            except Exception as exc:
                _logger.warning("Qdrant client init failed — degraded: %s", exc)
                return None
        return _client
    finally:
        _client_lock.release()


# ---------------------------------------------------------------------------
# Collection bootstrap
# ---------------------------------------------------------------------------


def ensure_qdrant_collection(
    vector_size: int = 384,
    collection_name: str | None = None,
) -> bool:
    """Create the Qdrant collection with required payload indexes.

    Returns ``True`` if the collection exists (or was created), ``False``
    on any failure.  Safe to call repeatedly — no-ops if already present.
    """
    client = _get_client()
    if client is None:
        return False

    name = collection_name or QDRANT_COLLECTION
    try:
        from qdrant_client.models import (  # type: ignore[import-untyped]
            Distance,
            PayloadSchemaType,
            VectorParams,
        )

        collections = [c.name for c in client.get_collections().collections]
        if name not in collections:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            _logger.info("Created Qdrant collection %r (dim=%d)", name, vector_size)

        # Ensure payload indexes for filtered search
        for index_field, schema in (
            ("category", PayloadSchemaType.KEYWORD),
            ("actions", PayloadSchemaType.KEYWORD),
            ("objects", PayloadSchemaType.KEYWORD),
            ("severity", PayloadSchemaType.KEYWORD),
            ("status", PayloadSchemaType.KEYWORD),
            ("tenant_id", PayloadSchemaType.KEYWORD),
            ("manifest_version", PayloadSchemaType.KEYWORD),
        ):
            try:
                client.create_payload_index(
                    collection_name=name,
                    field_name=index_field,
                    field_schema=schema,
                )
            except Exception:
                pass  # index already exists

        return True
    except Exception as exc:
        _logger.warning("ensure_qdrant_collection failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Semantic query
# ---------------------------------------------------------------------------


def query_semantic_patterns(
    query_vector: list[float],
    categories: list[str] | None = None,
    score_threshold: float = 0.45,
    limit: int = 5,
    collection_name: str | None = None,
) -> tuple[list[SemanticMatch], bool]:
    """Search Qdrant for semantic pattern matches.

    Parameters
    ----------
    query_vector:
        Normalized embedding of the input payload (384-dim float list).
    categories:
        Optional list of symbolic categories to filter by (from
        ``symbolic_narrowing._categorize_intent``).
    score_threshold:
        Minimum cosine similarity to consider a match.
    limit:
        Max results returned.
    collection_name:
        Override collection name (test isolation).

    Returns
    -------
    (matches, degraded)
        ``matches`` is a list of ``SemanticMatch`` objects sorted by descending
        score.  ``degraded`` is ``True`` if the query could not execute
        (timeout, connection error, etc.) — the caller should fall back to
        static patterns.
    """
    client = _get_client()
    if client is None:
        return [], True

    name = collection_name or QDRANT_COLLECTION
    t0 = time.monotonic()
    try:
        from qdrant_client.models import (  # type: ignore[import-untyped]
            FieldCondition,
            Filter,
            MatchAny,
        )

        # Build optional category filter
        query_filter = None
        if categories:
            query_filter = Filter(
                should=[
                    FieldCondition(
                        key="category",
                        match=MatchAny(any=categories),
                    ),
                    FieldCondition(
                        key="actions",
                        match=MatchAny(any=categories),
                    ),
                ],
            )

        response = client.query_points(
            collection_name=name,
            query=query_vector,
            query_filter=query_filter,
            score_threshold=score_threshold,
            limit=limit,
            with_payload=True,
        )

        elapsed_ms = (time.monotonic() - t0) * 1000
        if elapsed_ms > QDRANT_TIMEOUT_MS:
            _logger.warning(
                "Qdrant query completed but exceeded timeout: %.1fms > %dms",
                elapsed_ms,
                QDRANT_TIMEOUT_MS,
            )

        matches = []
        for hit in response.points:
            payload = hit.payload or {}
            matches.append(
                SemanticMatch(
                    pattern_id=payload.get("pattern_id", str(hit.id)),
                    score=hit.score,
                    category=payload.get("category", "unknown"),
                    severity=payload.get("severity", "HIGH"),
                    payload=payload,
                )
            )

        _logger.debug(
            "Qdrant query returned %d hits in %.1fms (threshold=%.2f)",
            len(matches),
            elapsed_ms,
            score_threshold,
        )
        return matches, False

    except Exception as exc:
        elapsed_ms = (time.monotonic() - t0) * 1000
        _logger.warning(
            "Qdrant query failed after %.1fms — degraded: %s", elapsed_ms, exc
        )
        return [], True
