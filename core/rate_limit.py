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
import random
import time
from collections import OrderedDict
from typing import Any, Generator

import httpx

from core.config import settings, upstash_configured
from core.persistence import redis_tenant_key

_logger = logging.getLogger("aletheia.rate_limit")

_MAX_TRACKED_IPS = 50_000  # in-memory fallback cap
_REDIS_KEY_PREFIX = "aletheia:rl:"
_REDIS_WINDOW_SECONDS = 1  # sliding window size
_REDIS_TTL_SECONDS = 10  # key expiry — cleanup after inactivity


class _CompletedReset:
    """Synchronous reset result that can also be awaited."""

    def __await__(self) -> Generator[None, None, None]:
        if False:
            yield None
        return None


class _ScheduledReset:
    """Wrapper that exposes a scheduled task as an awaitable."""

    def __init__(self, task: asyncio.Task[None]) -> None:
        self._task = task

    def __await__(self) -> Generator[Any, None, None]:
        return self._task.__await__()


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
        self._failure_count: int = 0
        self._circuit_open_until: float = 0.0
        self._FAILURE_THRESHOLD: int = 5
        self._CIRCUIT_RESET_SECONDS: float = 30.0
        self.backend = "upstash"
        self.degraded = False
        _logger.info("Rate limiter: Upstash Redis backend active")

    async def _redis(self, client: httpx.AsyncClient, *command: object) -> object:
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

    async def allow(self, key: str, *, tenant_id: str | None = None) -> bool:
        """Return True if request is within limits, False to reject.

        Uses atomic pipeline: ZREMRANGEBYSCORE → ZCARD → ZADD → EXPIRE
        """
        import time as _t

        if self._circuit_open_until > _t.monotonic():
            # Allow ~10% of requests through to probe for recovery
            # and prevent complete self-DoS during Redis outages.
            if random.random() < 0.10:
                _logger.info(
                    "Redis circuit open — allowing probe request for key: %s", key
                )
                return True
            _logger.warning(
                "Redis circuit open — rate limiter blocking request for key: %s", key
            )
            return False

        redis_key = redis_tenant_key(tenant_id, "rl", key)
        now = time.time()
        window_start = now - _REDIS_WINDOW_SECONDS
        member = str(now)  # unique member = timestamp string

        try:
            async with httpx.AsyncClient() as client:
                results = await self._pipeline(
                    client,
                    [
                        # 1. Remove members outside the sliding window
                        ["ZREMRANGEBYSCORE", redis_key, "-inf", str(window_start)],
                        # 2. Count current members (requests in window)
                        ["ZCARD", redis_key],
                        # 3. Add this request
                        ["ZADD", redis_key, str(now), member],
                        # 4. Set expiry so keys auto-cleanup
                        ["EXPIRE", redis_key, str(_REDIS_TTL_SECONDS)],
                    ],
                )
                current_count = results[1]  # ZCARD result
                self._failure_count = 0
                if self.degraded:
                    self._circuit_open_until = 0.0
                    self.degraded = False
                    _logger.info("Redis rate limiter recovered — circuit closed")
                return int(current_count) < self._max

        except Exception as exc:
            self._failure_count += 1
            self.degraded = True
            if self._failure_count >= self._FAILURE_THRESHOLD:
                # Add jitter to prevent thundering herd on recovery
                jitter = random.uniform(0, 10)
                self._circuit_open_until = (
                    _t.monotonic() + self._CIRCUIT_RESET_SECONDS + jitter
                )
                _logger.error(
                    "Redis rate limiter circuit opened after %d failures — "
                    "all requests blocked for %.0f seconds. "
                    "Check UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN.",
                    self._failure_count,
                    self._CIRCUIT_RESET_SECONDS,
                )
            else:
                _logger.warning(
                    "Redis rate limiter error (failure %d/%d) — blocking request: %s",
                    self._failure_count,
                    self._FAILURE_THRESHOLD,
                    exc,
                )
            return False

    async def _reset_async(self, key: str | None = None) -> None:
        """Clear rate limit state. Used in tests and admin operations."""
        try:
            async with httpx.AsyncClient() as client:
                if key is None:
                    # Scan and delete all aletheia rate limit keys
                    result = await self._redis(client, "KEYS", f"{_REDIS_KEY_PREFIX}*")
                    if result:
                        keys = list(result) if result else []  # type: ignore[call-overload]
                        await self._redis(client, "DEL", *keys)
                else:
                    await self._redis(client, "DEL", f"{_REDIS_KEY_PREFIX}{key}")
        except Exception as exc:
            _logger.warning("Redis reset error: %s", exc)

    def reset(self, key: str | None = None) -> _CompletedReset | _ScheduledReset:
        """Clear rate limit state in sync and async test contexts.

        Sync callers can invoke this without awaiting and async callers can still
        use ``await limiter.reset()``.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._reset_async(key))
            return _CompletedReset()

        task = loop.create_task(self._reset_async(key))
        return _ScheduledReset(task)

    def reset_sync(self, key: str | None = None) -> None:
        """Synchronous reset for test compatibility."""
        self.reset(key)


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
        self.backend = "inmemory"
        self.degraded = False
        _logger.warning(
            "Rate limiter: in-memory fallback active. "
            "Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN for "
            "distributed rate limiting."
        )

    async def allow(self, key: str, *, tenant_id: str | None = None) -> bool:
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

    async def _reset_async(self, key: str | None = None) -> None:
        async with self._lock:
            if key is None:
                self._windows.clear()
            else:
                self._windows.pop(key, None)

    def reset(self, key: str | None = None) -> _CompletedReset | _ScheduledReset:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            if key is None:
                self._windows.clear()
            else:
                self._windows.pop(key, None)
            return _CompletedReset()

        task = loop.create_task(self._reset_async(key))
        return _ScheduledReset(task)

    def reset_sync(self, key: str | None = None) -> None:
        self.reset(key)


def create_rate_limiter(
    max_per_second: int | None = None,
) -> "UpstashRateLimiter | InMemoryRateLimiter":
    """Factory: return Redis limiter if configured, else in-memory fallback.

    In production (ENVIRONMENT=production), Redis is required.
    In-memory fallback is single-node only — not suitable for production.
    """
    if upstash_configured():
        return UpstashRateLimiter(max_per_second)
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        _logger.critical(
            "FATAL: UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN not set "
            "in production. Distributed rate limiting is required. "
            "In-memory fallback is not safe for multi-worker deployments."
        )
        import sys

        sys.exit(1)
    return InMemoryRateLimiter(max_per_second)


# Backward-compatible alias
RateLimiter = InMemoryRateLimiter

# Module-level singleton — backend selected at import time
rate_limiter = create_rate_limiter()


# ---------------------------------------------------------------------------
# Evaluation-endpoint rate limiter (per-minute with burst)
# Configurable via:
#   EVAL_RATE_LIMIT_PER_MINUTE  (default 20)
#   EVAL_RATE_BURST             (default 5)
# ---------------------------------------------------------------------------

_EVAL_MINUTE_WINDOW = 60.0  # seconds
_EVAL_BURST_WINDOW = 3.0  # seconds — burst is assessed over this span


class EvalInMemoryRateLimiter:
    """Per-minute + burst in-memory rate limiter for /v1/evaluate.

    Two sliding windows are maintained per IP:
    - 60-second window:  at most ``max_per_minute`` requests allowed
    - 3-second  window:  at most ``burst`` requests allowed (prevents spikes)

    Returns ``(allowed: bool, retry_after_seconds: int)``.
    Single-node only; does not synchronise across workers.
    """

    def __init__(self) -> None:
        self._max_per_minute: int = int(os.getenv("EVAL_RATE_LIMIT_PER_MINUTE", "20"))
        self._burst: int = int(os.getenv("EVAL_RATE_BURST", "5"))
        self._lock = asyncio.Lock()
        self._minute_windows: OrderedDict[str, list[float]] = OrderedDict()
        self._burst_windows: OrderedDict[str, list[float]] = OrderedDict()
        _logger.info(
            "Eval rate limiter (in-memory): %d req/min, burst=%d",
            self._max_per_minute,
            self._burst,
        )

    async def allow(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()

        async with self._lock:
            # --- per-minute window ---
            minute_cutoff = now - _EVAL_MINUTE_WINDOW
            minute_ts = [
                t for t in self._minute_windows.get(key, []) if t > minute_cutoff
            ]

            if len(minute_ts) >= self._max_per_minute:
                oldest = min(minute_ts)
                retry_after = max(1, int(oldest + _EVAL_MINUTE_WINDOW - now) + 1)
                return False, retry_after

            # --- burst window ---
            burst_cutoff = now - _EVAL_BURST_WINDOW
            burst_ts = [t for t in self._burst_windows.get(key, []) if t > burst_cutoff]

            if len(burst_ts) >= self._burst:
                return False, max(1, int(_EVAL_BURST_WINDOW) + 1)

            # --- allow: record timestamp in both windows ---
            minute_ts.append(now)
            burst_ts.append(now)

            if (
                key not in self._minute_windows
                and len(self._minute_windows) >= _MAX_TRACKED_IPS
            ):
                self._minute_windows.popitem(last=False)
            self._minute_windows[key] = minute_ts
            self._minute_windows.move_to_end(key)

            if (
                key not in self._burst_windows
                and len(self._burst_windows) >= _MAX_TRACKED_IPS
            ):
                self._burst_windows.popitem(last=False)
            self._burst_windows[key] = burst_ts
            self._burst_windows.move_to_end(key)

            return True, 0

    async def reset(self, key: str | None = None) -> None:
        async with self._lock:
            if key is None:
                self._minute_windows.clear()
                self._burst_windows.clear()
            else:
                self._minute_windows.pop(key, None)
                self._burst_windows.pop(key, None)


class EvalUpstashRateLimiter:
    """Upstash-backed per-minute + burst rate limiter for /v1/evaluate.

    Uses two sorted-set keys per IP:
    - ``aletheia:eval_rl:min:{ip}``   — 60-second sliding window
    - ``aletheia:eval_rl:burst:{ip}`` — 3-second burst window
    """

    _MIN_PREFIX = "aletheia:eval_rl:min:"
    _BURST_PREFIX = "aletheia:eval_rl:burst:"

    def __init__(self) -> None:
        self._max_per_minute: int = int(os.getenv("EVAL_RATE_LIMIT_PER_MINUTE", "20"))
        self._burst: int = int(os.getenv("EVAL_RATE_BURST", "5"))
        self._url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self._token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        _logger.info(
            "Eval rate limiter (Upstash): %d req/min, burst=%d",
            self._max_per_minute,
            self._burst,
        )

    async def _pipeline(self, commands: list) -> list:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._url}/pipeline",
                headers=self._headers,
                json=commands,
                timeout=2.0,
            )
            return [item.get("result") for item in resp.json()]

    async def allow(self, key: str) -> tuple[bool, int]:
        import time as _t

        now = _t.time()
        min_key = f"{self._MIN_PREFIX}{key}"
        burst_key = f"{self._BURST_PREFIX}{key}"
        member = str(now)

        try:
            results = await self._pipeline(
                [
                    [
                        "ZREMRANGEBYSCORE",
                        min_key,
                        "-inf",
                        str(now - _EVAL_MINUTE_WINDOW),
                    ],
                    ["ZCARD", min_key],
                    [
                        "ZREMRANGEBYSCORE",
                        burst_key,
                        "-inf",
                        str(now - _EVAL_BURST_WINDOW),
                    ],
                    ["ZCARD", burst_key],
                    ["ZADD", min_key, str(now), member],
                    ["EXPIRE", min_key, "120"],
                    ["ZADD", burst_key, str(now), member],
                    ["EXPIRE", burst_key, "10"],
                ]
            )
            min_count = int(results[1])
            burst_count = int(results[3])

            if min_count >= self._max_per_minute:
                return False, 60
            if burst_count >= self._burst:
                return False, max(1, int(_EVAL_BURST_WINDOW) + 1)
            return True, 0
        except Exception as exc:
            _logger.warning(
                "Eval Upstash rate limiter error — allowing request: %s", exc
            )
            # Fail-open: don't block legitimate traffic on Redis errors
            return True, 0

    async def reset(self, key: str | None = None) -> None:
        pass  # Best-effort; keys expire automatically


def create_eval_rate_limiter() -> EvalUpstashRateLimiter | EvalInMemoryRateLimiter:
    """Return the appropriate eval rate limiter based on environment."""
    if upstash_configured():
        return EvalUpstashRateLimiter()
    return EvalInMemoryRateLimiter()


# Module-level singleton for /v1/evaluate
eval_rate_limiter = create_eval_rate_limiter()
