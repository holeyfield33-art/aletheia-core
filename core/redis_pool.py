"""Aletheia Core — Unified async Redis connection pool.

Provides a single ``get_redis_pool()`` factory that supports:
- Standard ``redis://`` / ``rediss://`` URLs (via ``redis.asyncio``)
- Upstash REST API (via existing httpx-based adapters)

All Redis keys MUST be built with ``redis_tenant_key()`` from
``core.persistence`` to enforce tenant isolation.

In production (``ENVIRONMENT=production``), a Redis URL is required
when ``ALETHEIA_DATABASE_BACKEND=postgres``.  The in-memory fallback
is only available for development.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

_logger = logging.getLogger("aletheia.redis_pool")

_pool: Optional[object] = None


def redis_url() -> str:
    """Return the configured Redis URL, or empty string if not set."""
    return os.getenv("REDIS_URL", "").strip()


def redis_configured() -> bool:
    """True when a standard Redis URL is available."""
    return bool(redis_url())


async def get_redis_pool():
    """Return or create the global ``redis.asyncio`` connection pool.

    Returns ``None`` when no Redis URL is configured.  Callers must
    handle the ``None`` case (fall back to in-memory or Upstash).
    """
    global _pool
    if _pool is not None:
        return _pool

    url = redis_url()
    if not url:
        return None

    try:
        import redis.asyncio as aioredis
    except ImportError:
        _logger.error(
            "redis[asyncio] package not installed. "
            "Install with: pip install 'redis[asyncio]>=5.0'"
        )
        return None

    # Enforce TLS in production
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    if is_production and not (url.startswith("rediss://") or "ssl=true" in url.lower()):
        _logger.critical(
            "FATAL: REDIS_URL does not use TLS (rediss://) in production. "
            "Set a rediss:// URL or append ?ssl=true."
        )
        import sys
        sys.exit(1)

    _pool = aioredis.from_url(
        url,
        decode_responses=True,
        max_connections=20,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    _logger.info("Redis async pool created from REDIS_URL")
    return _pool


async def close_redis_pool() -> None:
    """Close the global pool (call during shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()  # type: ignore[union-attr]
        _pool = None


def reset_redis_pool() -> None:
    """Reset pool reference (testing only)."""
    global _pool
    _pool = None
