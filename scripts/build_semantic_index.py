#!/usr/bin/env python3
"""Build the Qdrant semantic index from a signed semantic manifest.

Usage:
    python scripts/build_semantic_index.py \\
        --manifest manifest/semantic_patterns.json \\
        [--signature manifest/semantic_patterns.json.sig] \\
        [--pubkey manifest/security_policy.ed25519.pub] \\
        [--qdrant-url http://localhost:6333] \\
        [--collection aletheia_semantic_patterns] \\
        [--model BAAI/bge-small-en-v1.5] \\
        [--dry-run]

Steps:
    1. Load and parse the semantic manifest JSON
    2. (Optional) Verify Ed25519 detached signature
    3. Load embedding model (BAAI/bge-small-en-v1.5 by default, 384-dim)
    4. Generate embeddings for all manifest entries
    5. Upsert vectors + payload into Qdrant collection
    6. Create Qdrant snapshot
    7. Output signed index_receipt.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
import uuid
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_logger = logging.getLogger("build_semantic_index")


def _verify_signature(manifest_path: Path, sig_path: Path, pub_path: Path) -> None:
    """Verify Ed25519 detached signature on the manifest."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    pub_bytes = pub_path.read_bytes()
    public_key = load_pem_public_key(pub_bytes)
    if not isinstance(public_key, Ed25519PublicKey):
        raise TypeError("Public key is not Ed25519")

    manifest_bytes = manifest_path.read_bytes()
    sig_bytes = sig_path.read_bytes()

    # Support both raw and hex-encoded signatures
    if len(sig_bytes) == 128:
        sig_bytes = bytes.fromhex(sig_bytes.decode("ascii").strip())

    public_key.verify(sig_bytes, manifest_bytes)
    _logger.info("Manifest signature verified OK")


def _load_manifest(path: Path) -> dict:
    """Load and validate the semantic manifest."""
    # Import inline to avoid circular deps at module level
    from core.semantic_manifest import SemanticManifest

    raw = json.loads(path.read_text(encoding="utf-8"))
    manifest = SemanticManifest.model_validate(raw)
    _logger.info(
        "Manifest loaded: version=%s, entries=%d, model=%s",
        manifest.version,
        len(manifest.entries),
        manifest.embedding_model,
    )
    return manifest.model_dump()


def _build_index(
    manifest_data: dict,
    model_name: str,
    qdrant_url: str,
    collection: str,
    dry_run: bool,
) -> dict:
    """Generate embeddings and upsert to Qdrant.

    Returns a dict with ``indexed``, ``dry_run``, and optionally
    ``qdrant_snapshot_id``.
    """
    from sentence_transformers import SentenceTransformer

    entries = [e for e in manifest_data["entries"] if e.get("enabled", True)]
    if not entries:
        _logger.warning("No enabled entries in manifest — nothing to index")
        return {"indexed": 0}

    _logger.info("Loading embedding model: %s", model_name)
    model = SentenceTransformer(model_name)

    texts = [e["text"] for e in entries]
    _logger.info("Encoding %d patterns...", len(texts))
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    if dry_run:
        _logger.info("DRY RUN — skipping Qdrant upsert for %d vectors", len(texts))
        return {"indexed": len(texts), "dry_run": True}

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    client = QdrantClient(url=qdrant_url)

    # Ensure collection exists
    from core.vector_store import ensure_qdrant_collection

    # Temporarily enable Qdrant for bootstrap
    import core.vector_store as _vs

    _original_enabled = _vs.QDRANT_ENABLED
    _vs.QDRANT_ENABLED = True
    _vs._client = client
    try:
        ensure_qdrant_collection(
            vector_size=manifest_data.get("embedding_dim", manifest_data.get("vector_size", 384)),
            collection_name=collection,
        )
    finally:
        _vs.QDRANT_ENABLED = _original_enabled
        _vs._client = None

    # Build points
    points = []
    for i, entry in enumerate(entries):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, entry["id"]))
        # Support both v2 (metadata sub-object) and v1 (flat) entry shapes
        meta = entry.get("metadata", {})
        payload = {
            "pattern_id": entry["id"],
            "text": entry["text"],
            "category": entry["category"],
            "severity": entry.get("severity", "high"),
            "actions": meta.get("actions", entry.get("actions", [])),
            "objects": meta.get("objects", entry.get("objects", [])),
            "channels": meta.get("channels", []),
            "manifest_version": manifest_data["version"],
            "status": "active",
        }
        points.append(
            PointStruct(
                id=point_id,
                vector=embeddings[i].tolist(),
                payload=payload,
            )
        )

    # Upsert in batches of 100
    batch_size = 100
    for start in range(0, len(points), batch_size):
        batch = points[start : start + batch_size]
        client.upsert(collection_name=collection, points=batch)
        _logger.info("Upserted batch %d-%d", start, start + len(batch))

    _logger.info("Index built: %d vectors upserted", len(points))

    # Create snapshot
    snapshot_id: str | None = None
    try:
        snapshot = client.create_snapshot(collection_name=collection)
        snapshot_id = getattr(snapshot, "name", str(snapshot))
        _logger.info("Snapshot created: %s", snapshot_id)
    except Exception as exc:
        _logger.warning("Snapshot creation failed (non-fatal): %s", exc)

    return {"indexed": len(points), "qdrant_snapshot_id": snapshot_id}


def _write_receipt(
    output_path: Path,
    manifest_path: Path,
    manifest_data: dict,
    index_result: dict,
    collection: str,
    private_key_path: Path | None = None,
    public_key_path: Path | None = None,
) -> None:
    """Write a signed index receipt.

    The receipt includes the full structure required by the directive:
    manifest_version, manifest_hash, collection_name, vector_count,
    embedding_model, embedding_dim, distance_metric, qdrant_snapshot_id,
    built_at, and per-category thresholds.

    If a private key is available, the receipt is Ed25519-signed using the
    same signing function as the manifest CLI.
    """
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    # Extract thresholds from manifest (use defaults if absent)
    thresholds_raw = manifest_data.get("thresholds", {})
    thresholds = {
        "direct_exfiltration": thresholds_raw.get("direct_exfiltration", 0.86),
        "policy_evasion": thresholds_raw.get("policy_evasion", 0.84),
        "hybrid_composite": thresholds_raw.get("hybrid_composite", 0.82),
        "recon_alias": thresholds_raw.get("recon_alias", 0.88),
    }

    receipt = {
        "manifest_version": manifest_data.get("version", "unknown"),
        "manifest_hash": f"sha256:{manifest_hash}",
        "collection_name": collection,
        "vector_count": index_result.get("indexed", 0),
        "embedding_model": manifest_data.get("embedding_model", "BAAI/bge-small-en-v1.5"),
        "embedding_dim": manifest_data.get("embedding_dim", 384),
        "distance_metric": "cosine",
        "qdrant_snapshot_id": index_result.get("qdrant_snapshot_id"),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "thresholds": thresholds,
    }

    if index_result.get("dry_run"):
        receipt["dry_run"] = True

    # Sign the receipt if a private key is available
    if private_key_path and private_key_path.exists():
        try:
            from cryptography.hazmat.primitives.serialization import (
                load_pem_private_key,
            )
            import base64

            key_bytes = private_key_path.read_bytes()
            private_key = load_pem_private_key(key_bytes, password=None)
            receipt_bytes = json.dumps(receipt, sort_keys=True).encode("utf-8")
            signature = private_key.sign(receipt_bytes)
            receipt["signature"] = base64.b64encode(signature).decode("ascii")
            receipt["signature_algorithm"] = "ed25519"
            _logger.info("Receipt signed with Ed25519 key")
        except Exception as exc:
            _logger.warning("Receipt signing failed (non-fatal): %s", exc)

    output_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    _logger.info("Receipt written to %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Qdrant semantic index from signed manifest"
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to semantic_patterns.json",
    )
    parser.add_argument(
        "--signature",
        type=Path,
        default=None,
        help="Path to detached Ed25519 signature (optional)",
    )
    parser.add_argument(
        "--pubkey",
        type=Path,
        default=Path("manifest/security_policy.ed25519.pub"),
        help="Path to Ed25519 public key",
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant server URL",
    )
    parser.add_argument(
        "--collection",
        default="aletheia_semantic_patterns",
        help="Qdrant collection name",
    )
    parser.add_argument(
        "--model",
        default="BAAI/bge-small-en-v1.5",
        help="Embedding model name",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("index_receipt.json"),
        help="Output receipt path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate embeddings but skip Qdrant upsert",
    )
    parser.add_argument(
        "--private-key",
        type=Path,
        default=None,
        help="Path to Ed25519 private key for receipt signing (optional)",
    )
    args = parser.parse_args()

    # 1. Verify signature if provided
    if args.signature:
        _verify_signature(args.manifest, args.signature, args.pubkey)
    else:
        _logger.warning("No signature provided — manifest is UNVERIFIED")

    # 2. Load and validate manifest
    manifest_data = _load_manifest(args.manifest)

    # 2b. Validate entries for duplicates
    from core.semantic_manifest import SemanticManifest as _SM

    _m = _SM.model_validate(manifest_data)
    dup_errors = _m.validate_entries()
    if dup_errors:
        for err in dup_errors:
            _logger.error("Manifest validation: %s", err)
        sys.exit(1)

    # 3. Determine model (manifest overrides CLI if present)
    model_name = manifest_data.get("embedding_model", args.model)

    # 4. Build index
    index_result = _build_index(
        manifest_data=manifest_data,
        model_name=model_name,
        qdrant_url=args.qdrant_url,
        collection=args.collection,
        dry_run=args.dry_run,
    )

    # 5. Write receipt (with signing if key is available)
    _write_receipt(
        args.output,
        args.manifest,
        manifest_data,
        index_result,
        collection=args.collection,
        private_key_path=args.private_key,
    )

    _logger.info("Done.")


if __name__ == "__main__":
    main()
