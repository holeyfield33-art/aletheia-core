#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Index semantic_manifest.json to Qdrant Cloud collection.

Reads data/semantic_manifest.json, embeds entries with all-MiniLM-L6-v2,
and upserts to the "aletheia_semantic_patterns" collection on Qdrant Cloud.
Recreates collection if it already exists.

Environment variables:
    QDRANT_URL: Qdrant server URL (e.g., https://example.qdrant.io:6333)
    QDRANT_API_KEY: API key for Qdrant Cloud
    ALETHEIA_DATA_MANIFEST: Path to manifest JSON (default: data/semantic_manifest.json)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_logger = logging.getLogger("aletheia.index_qdrant")


COLLECTION_NAME = "aletheia_semantic_patterns"
MANIFEST_PATH = os.getenv("ALETHEIA_DATA_MANIFEST", "data/semantic_manifest.json")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def main() -> None:
    """Index manifest to Qdrant."""
    # Read environment
    qdrant_url = os.environ.get("QDRANT_URL")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")

    if not qdrant_url:
        _logger.error("QDRANT_URL environment variable not set")
        sys.exit(1)

    if not qdrant_api_key:
        _logger.error("QDRANT_API_KEY environment variable not set")
        sys.exit(1)

    # Load manifest
    manifest_file = Path(MANIFEST_PATH)
    if not manifest_file.is_file():
        _logger.error("Manifest file not found: %s", MANIFEST_PATH)
        sys.exit(1)

    try:
        with open(manifest_file) as f:
            manifest_data = json.load(f)
    except json.JSONDecodeError as e:
        _logger.error("Failed to parse manifest JSON: %s", e)
        sys.exit(1)

    entries = manifest_data.get("entries", [])
    if not entries:
        _logger.error("No entries in manifest")
        sys.exit(1)

    _logger.info("Loaded manifest: %s (%d entries)", MANIFEST_PATH, len(entries))

    # Initialize Qdrant client
    _logger.info("Connecting to Qdrant at %s…", qdrant_url)
    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)
        # Test connection
        client.get_collections()
        _logger.info("Connected to Qdrant")
    except Exception as e:
        _logger.error("Failed to connect to Qdrant: %s", e)
        sys.exit(1)

    # Initialize embedding model
    _logger.info("Loading embedding model: %s…", EMBEDDING_MODEL)
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        _logger.info("Embedding model loaded")
    except Exception as e:
        _logger.error("Failed to load embedding model: %s", e)
        sys.exit(1)

    # Recreate collection
    _logger.info("Recreating collection '%s'…", COLLECTION_NAME)
    try:
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        _logger.info("Collection recreated")
    except Exception as e:
        _logger.error("Failed to recreate collection: %s", e)
        sys.exit(1)

    # Encode and upsert
    _logger.info("Encoding %d entries…", len(entries))
    t_start = time.time()
    try:
        points = []
        texts = [e.get("text", "") for e in entries]

        # Encode all at once
        embeddings = model.encode(texts, batch_size=32, convert_to_numpy=True)

        for i, (embedding, entry) in enumerate(zip(embeddings, entries)):
            points.append(
                PointStruct(
                    id=i,
                    vector=embedding.tolist(),
                    payload=entry,
                )
            )

        elapsed_encode = time.time() - t_start
        _logger.info("Encoded %d entries in %.2f seconds", len(points), elapsed_encode)

        # Upsert to Qdrant
        _logger.info("Upserting %d points to Qdrant…", len(points))
        t_upsert = time.time()
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )
        elapsed_upsert = time.time() - t_upsert
        _logger.info("Upserted %d points in %.2f seconds", len(points), elapsed_upsert)

        total_elapsed = time.time() - t_start
        _logger.info(
            "✓ Successfully indexed %d entries in %.2f seconds",
            len(points),
            total_elapsed,
        )

    except Exception as e:
        _logger.error("Failed to encode or upsert: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
