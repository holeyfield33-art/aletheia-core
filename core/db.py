# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Database helpers for health checks and optional slow-query logging."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from core.config import settings
from core.vector_store import QDRANT_ENABLED, _get_client

_logger = logging.getLogger("aletheia.db")

_DATABASE_LOG_QUERIES = os.getenv("DATABASE_LOG_QUERIES", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
_SLOW_QUERY_MS = int(os.getenv("DATABASE_SLOW_QUERY_MS", "100"))


def _log_if_slow(query: str, elapsed_ms: float) -> None:
    if _DATABASE_LOG_QUERIES and elapsed_ms > _SLOW_QUERY_MS:
        _logger.warning(
            "slow_database_query",
            extra={
                "elapsed_ms": round(elapsed_ms, 2),
                "threshold_ms": _SLOW_QUERY_MS,
                "query": query,
            },
        )


async def execute_postgres_query(query: str, *args: Any) -> Any:
    """Execute one Postgres query and optionally log slow queries."""
    import asyncpg

    database_url = settings.database_url or os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    started = time.perf_counter()
    conn = await asyncpg.connect(database_url)
    try:
        result = await conn.fetch(query, *args)
    finally:
        await conn.close()

    _log_if_slow(query, (time.perf_counter() - started) * 1000)
    return result


async def check_database_health() -> tuple[bool, str]:
    """Return backend database readiness and a status detail string."""
    if settings.database_backend == "postgres":
        database_url = settings.database_url or os.getenv("DATABASE_URL", "")
        if not database_url:
            return False, "postgres_not_configured"
        try:
            import asyncpg

            conn = await asyncpg.connect(database_url)
            started = time.perf_counter()
            await conn.execute("SELECT 1")
            await conn.close()
            _log_if_slow("SELECT 1", (time.perf_counter() - started) * 1000)
            return True, "postgres_ok"
        except Exception as exc:
            _logger.error("database health check failed: %s", exc)
            return False, "postgres_unavailable"

    sqlite_path = os.getenv(
        "ALETHEIA_DECISION_DB_PATH",
        os.path.join(tempfile.gettempdir(), "aletheia", "decisions.sqlite3"),
    )
    try:
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        conn = sqlite3.connect(sqlite_path)
        conn.execute("SELECT 1")
        conn.close()
        _log_if_slow("SELECT 1", (time.perf_counter() - started) * 1000)
        return True, "sqlite_ok"
    except Exception as exc:
        _logger.error("sqlite health check failed: %s", exc)
        return False, "sqlite_unavailable"


async def check_qdrant_health() -> tuple[bool, str]:
    """Return Qdrant readiness and detail. Disabled mode is considered ready."""
    if not QDRANT_ENABLED:
        return True, "qdrant_disabled"

    client = _get_client()
    if client is None:
        return False, "qdrant_unavailable"

    try:
        await asyncio.to_thread(client.get_collections)
        return True, "qdrant_ok"
    except Exception as exc:
        _logger.error("qdrant health check failed: %s", exc)
        return False, "qdrant_error"
