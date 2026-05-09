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
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
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


# pgBouncer in transaction/statement mode does not preserve prepared statements
# across requests. Disable asyncpg's statement cache to avoid
# "prepared statement ... does not exist" runtime failures.
ASYNCPG_PGBOUNCER_SAFE_KWARGS: dict[str, Any] = {"statement_cache_size": 0}


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


def sanitize_asyncpg_url(database_url: str) -> str:
    """Strip Prisma/pgBouncer query params that asyncpg rejects."""
    strip_params = {"pgbouncer", "connection_limit", "pool_timeout", "schema"}
    try:
        parsed = urlparse(database_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in qs.items() if k.lower() not in strip_params}
        clean_query = urlencode(filtered, doseq=True)
        return urlunparse(parsed._replace(query=clean_query))
    except Exception:
        return database_url


async def create_asyncpg_pool(
    database_url: str,
    *,
    min_size: int,
    max_size: int,
    command_timeout: int | None = None,
    sanitize_url: bool = False,
) -> Any:
    """Create an asyncpg pool with pgBouncer-safe defaults."""
    import asyncpg

    pool_url = sanitize_asyncpg_url(database_url) if sanitize_url else database_url
    pool_kwargs: dict[str, Any] = {
        "min_size": min_size,
        "max_size": max_size,
        **ASYNCPG_PGBOUNCER_SAFE_KWARGS,
    }
    if command_timeout is not None:
        pool_kwargs["command_timeout"] = command_timeout
    return await asyncpg.create_pool(pool_url, **pool_kwargs)


async def probe_asyncpg_pool(pool: Any) -> None:
    """Run a lightweight health probe against a pool."""
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")


async def init_optional_postgres_pool() -> Any | None:
    """Create and probe the main Postgres pool when postgres backend is enabled."""
    if settings.database_backend != "postgres":
        return None

    db_url = settings.database_url or os.getenv("DATABASE_URL", "")
    if not db_url:
        return None

    pool = await create_asyncpg_pool(db_url, min_size=2, max_size=10)
    await probe_asyncpg_pool(pool)
    return pool


async def close_asyncpg_pool(pool: Any | None, *, label: str = "Postgres pool") -> None:
    """Close an asyncpg pool if present and emit a lifecycle log."""
    if pool is not None:
        await pool.close()
        _logger.info("%s: closed", label)


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
