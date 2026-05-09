# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Runtime dependency status helpers for health and readiness endpoints."""

from __future__ import annotations

from dataclasses import dataclass

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
