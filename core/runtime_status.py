# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Runtime dependency status helpers for health and readiness endpoints."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os

from core.db import check_database_health, check_qdrant_health


@dataclass(frozen=True)
class DependencyHealth:
    redis_ready: bool
    database_ready: bool
    database_status: str
    qdrant_ready: bool
    qdrant_status: str

    @property
    def all_ready(self) -> bool:
        return self.redis_ready and self.database_ready and self.qdrant_ready


@dataclass(frozen=True)
class ManifestReadiness:
    manifest_ok: bool
    policy_version: str
    receipt_signing_configured: bool

    @property
    def manifest_signature(self) -> str:
        return "VALID" if self.manifest_ok else "INVALID"


async def check_redis_health() -> bool:
    """Return whether Redis pool is reachable.

    If Redis is not configured and no pool exists, this remains healthy to match
    existing endpoint semantics.
    """
    try:
        from core.redis_pool import get_redis_pool

        pool = await get_redis_pool()
        if pool is not None:
            await pool.ping()  # type: ignore[union-attr]
        return True
    except Exception:
        return False


async def collect_dependency_health() -> DependencyHealth:
    """Collect Redis, database, and Qdrant status for runtime probes."""
    redis_ready = await check_redis_health()
    database_ready, database_status = await check_database_health()
    qdrant_ready, qdrant_status = await check_qdrant_health()
    return DependencyHealth(
        redis_ready=redis_ready,
        database_ready=database_ready,
        database_status=database_status,
        qdrant_ready=qdrant_ready,
        qdrant_status=qdrant_status,
    )


def verify_manifest_signature_status() -> bool:
    """Return True when the signed security manifest verifies."""
    from manifest.signing import verify_manifest_signature

    try:
        verify_manifest_signature(
            manifest_path="manifest/security_policy.json",
            signature_path="manifest/security_policy.json.sig",
            public_key_path="manifest/security_policy.ed25519.pub",
        )
        return True
    except Exception:
        return False


def load_policy_version() -> str:
    """Load policy manifest version for readiness diagnostics."""
    try:
        with open("manifest/security_policy.json", "r", encoding="utf-8") as f:
            policy_data = json.load(f)
        return str(policy_data.get("version", "unknown"))
    except Exception:
        return "unknown"


def collect_manifest_readiness() -> ManifestReadiness:
    """Collect manifest and receipt-signing readiness metadata."""
    return ManifestReadiness(
        manifest_ok=verify_manifest_signature_status(),
        policy_version=load_policy_version(),
        receipt_signing_configured=bool(
            os.getenv("ALETHEIA_RECEIPT_SECRET", "").strip()
        ),
    )
