"""Aletheia Core — Rate limiter with Upstash Redis backend.

Automatically selects backend based on environment:
- UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN set → Redis (distributed)
- Env vars absent → in-memory sliding window (single-node fallback)

The Redis backend uses Upstash's REST API over HTTPS — no redis-py,
no connection pool, no async driver complexity. Just httpx.

Redis strategy: sliding window using a sorted set per IP key.
Each request adds a score=timestamp member. Old members are pruned
on each check. This gives exact sliding-window semantics across
all workers and instances.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import OrderedDict

import httpx

from core.config import settings

_logger = logging.getLogger("aletheia.rate_limit")

_MAX_TRACKED_IPS = 50_000  # in-memory fallback cap
_REDIS_KEY_PREFIX = "aletheia:rl:"
_REDIS_WINDOW_SECONDS = 1  # sliding window size
_REDIS_TTL_SECONDS = 10    # key expiry — cleanup after inactivity


def _upstash_configured() -> bool:
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    return bool(url and token)


class UpstashRateLimiter:
    """Distributed sliding-window rate limiter using Upstash Redis REST API.

    Uses a Redis sorted set per IP. Each request is a member with
    score = current timestamp (float). Old members outside the window
    are pruned atomically using a pipeline of ZREMRANGEBYSCORE + ZCARD + ZADD.

    This gives exact sliding-window semantics across all workers and instances.
    No connection pool needed — Upstash REST API is stateless HTTPS.
    """

    def __init__(self, max_per_second: int | None = None) -> None:
        self._max = max_per_second or settings.rate_limit_per_second
        self._url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self._token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        _logger.info(
            "Rate limiter: Upstash Redis backend active at %s",
            self._url.split("//")[-1],  # log host only, not full URL
        )

    async def _redis(self, client: httpx.AsyncClient, *command) -> object:
        """Execute a single Redis command via Upstash REST API."""
        resp = await client.post(
            self._url,
            headers=self._headers,
            json=list(command),
            timeout=2.0,
        )
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Upstash error: {data['error']}")
        return data.get("result")

    async def _pipeline(self, client: httpx.AsyncClient, commands: list) -> list:
        """Execute multiple Redis commands in a pipeline (one HTTP request)."""
        resp = await client.post(
            f"{self._url}/pipeline",
            headers=self._headers,
            json=commands,
            timeout=2.0,
        )
        return [item.get("result") for item in resp.json()]

    async def allow(self, key: str) -> bool:
        """Return True if request is within limits, False to reject.

        Uses atomic pipeline: ZREMRANGEBYSCORE → ZCARD → ZADD → EXPIRE
        """
        redis_key = f"{_REDIS_KEY_PREFIX}{key}"
        now = time.time()
        window_start = now - _REDIS_WINDOW_SECONDS
        member = str(now)  # unique member = timestamp string

        try:
            async with httpx.AsyncClient() as client:
                results = await self._pipeline(client, [
                    # 1. Remove members outside the sliding window
                    ["ZREMRANGEBYSCORE", redis_key, "-inf", str(window_start)],
                    # 2. Count current members (requests in window)
                    ["ZCARD", redis_key],
                    # 3. Add this request
                    ["ZADD", redis_key, str(now), member],
                    # 4. Set expiry so keys auto-cleanup
                    ["EXPIRE", redis_key, str(_REDIS_TTL_SECONDS)],
                ])
                current_count = results[1]  # ZCARD result
                return int(current_count) < self._max

        except Exception as exc:
            # If Redis is unavailable, fail open (allow the request) and log.
            # Failing closed would take down the service if Redis has a blip.
            # Monitor aletheia_redis_errors_total in your alerting.
            _logger.warning(
                "Redis rate limiter error — failing open: %s", exc
            )
            return True

    async def reset(self, key: str | None = None) -> None:
        """Clear rate limit state. Used in tests and admin operations."""
        try:
            async with httpx.AsyncClient() as client:
                if key is None:
                    # Scan and delete all aletheia rate limit keys
                    result = await self._redis(
                        client, "KEYS", f"{_REDIS_KEY_PREFIX}*"
                    )
                    if result:
                        await self._redis(client, "DEL", *result)
                else:
                    await self._redis(client, "DEL", f"{_REDIS_KEY_PREFIX}{key}")
        except Exception as exc:
            _logger.warning("Redis reset error: %s", exc)

    def reset_sync(self, key: str | None = None) -> None:
        """Synchronous reset for test compatibility."""
        asyncio.run(self.reset(key))


class InMemoryRateLimiter:
    """Fallback in-memory sliding-window rate limiter.

    Used when UPSTASH_REDIS_REST_URL is not configured.
    Single-node only — does not synchronize across workers.
    State resets on process restart.

    This is the documented limitation when Redis is not configured.
    """

    def __init__(self, max_per_second: int | None = None) -> None:
        self._max = max_per_second or settings.rate_limit_per_second
        self._lock = asyncio.Lock()
        self._windows: OrderedDict[str, list[float]] = OrderedDict()
        _logger.warning(
            "Rate limiter: in-memory fallback active. "
            "Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN for "
            "distributed rate limiting."
        )

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - 1.0

        async with self._lock:
            # LRU eviction at capacity
            if key not in self._windows and len(self._windows) >= _MAX_TRACKED_IPS:
                self._windows.popitem(last=False)

            timestamps = list(self._windows.get(key, []))
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self._max:
                self._windows[key] = timestamps
                return False

            timestamps.append(now)
            self._windows[key] = timestamps
            self._windows.move_to_end(key)
            return True

    async def reset(self, key: str | None = None) -> None:
        async with self._lock:
            if key is None:
                self._windows.clear()
            else:
                self._windows.pop(key, None)

    def reset_sync(self, key: str | None = None) -> None:
        if key is None:
            self._windows.clear()
        else:
            self._windows.pop(key, None)


def create_rate_limiter(max_per_second: int | None = None):
    """Factory: return Redis limiter if configured, else in-memory fallback."""
    if _upstash_configured():
        return UpstashRateLimiter(max_per_second)
    return InMemoryRateLimiter(max_per_second)


# Module-level singleton — backend selected at import time
rate_limiter = create_rate_limiter()
