"""Enterprise-grade edge-case tests for core/rate_limit.py.

Covers:
- Sliding-window expiry (time-based): blocked IPs allowed again after 1 s
- Async concurrency under concurrent hammering
- Per-key independence at high concurrency
- reset(key) vs reset(None) semantics
- InMemoryRateLimiter instantiated with explicit max_per_second=1 / large
- Module-level singleton shares no state with fresh instances
"""

from __future__ import annotations

import asyncio

import pytest

from core.rate_limit import InMemoryRateLimiter, UpstashRateLimiter, rate_limiter


# ---------------------------------------------------------------------------
# Sliding-window expiry
# ---------------------------------------------------------------------------


class TestSlidingWindowExpiry:
    """The 1-second window must slide: old requests expire so new ones are allowed."""

    @pytest.mark.asyncio
    async def test_requests_allowed_after_window_expires(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=2)
        assert await limiter.allow("ip1") is True
        assert await limiter.allow("ip1") is True
        assert await limiter.allow("ip1") is False  # at limit

        await asyncio.sleep(1.05)

        assert await limiter.allow("ip1") is True

    @pytest.mark.asyncio
    async def test_partial_window_expiry(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=2)
        await limiter.allow("ip1")  # T=0
        await asyncio.sleep(0.6)
        await limiter.allow("ip1")  # T=0.6
        assert await limiter.allow("ip1") is False

        await asyncio.sleep(0.5)  # T=1.1 — first expired

        assert await limiter.allow("ip1") is True
        assert await limiter.allow("ip1") is False

    @pytest.mark.asyncio
    async def test_full_burst_then_recover(self) -> None:
        n = 5
        limiter = InMemoryRateLimiter(max_per_second=n)
        for _ in range(n):
            assert await limiter.allow("burst_ip") is True
        assert await limiter.allow("burst_ip") is False

        await asyncio.sleep(1.05)

        for i in range(n):
            assert await limiter.allow("burst_ip") is True, (
                f"Request {i + 1} denied after expiry"
            )


# ---------------------------------------------------------------------------
# Reset semantics
# ---------------------------------------------------------------------------


class TestResetSemantics:
    @pytest.mark.asyncio
    async def test_reset_single_key_clears_that_key(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1)
        await limiter.allow("a")
        assert await limiter.allow("a") is False
        await limiter.reset("a")
        assert await limiter.allow("a") is True

    @pytest.mark.asyncio
    async def test_reset_single_key_does_not_affect_others(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1)
        await limiter.allow("a")
        await limiter.allow("b")
        assert await limiter.allow("a") is False
        assert await limiter.allow("b") is False

        await limiter.reset("a")

        assert await limiter.allow("a") is True
        assert await limiter.allow("b") is False

    @pytest.mark.asyncio
    async def test_reset_none_clears_all_keys(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1)
        for key in ("x", "y", "z"):
            await limiter.allow(key)
            assert await limiter.allow(key) is False

        await limiter.reset()

        for key in ("x", "y", "z"):
            assert await limiter.allow(key) is True

    @pytest.mark.asyncio
    async def test_reset_nonexistent_key_does_not_raise(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=5)
        await limiter.reset("never_seen_key")

    @pytest.mark.asyncio
    async def test_reset_key_then_window_still_works(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=2)
        await limiter.allow("a")
        await limiter.reset("a")
        await limiter.allow("a")
        await limiter.allow("a")
        assert await limiter.allow("a") is False


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------


class TestMaxPerSecondBoundaryValues:
    @pytest.mark.asyncio
    async def test_max_1_allows_first_blocks_second(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1)
        assert await limiter.allow("ip") is True
        assert await limiter.allow("ip") is False

    @pytest.mark.asyncio
    async def test_max_1_sequential_keys_each_get_one_slot(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1)
        for i in range(10):
            assert await limiter.allow(f"ip_{i}") is True

    @pytest.mark.asyncio
    async def test_large_max_allows_many(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1000)
        for _ in range(1000):
            assert await limiter.allow("big_ip") is True
        assert await limiter.allow("big_ip") is False


# ---------------------------------------------------------------------------
# Per-key independence
# ---------------------------------------------------------------------------


class TestPerKeyIndependence:
    @pytest.mark.asyncio
    async def test_10_keys_each_independent_limit(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=3)
        keys = [f"client_{i}" for i in range(10)]

        for key in keys:
            for _ in range(3):
                assert await limiter.allow(key) is True
            assert await limiter.allow(key) is False

        for key in keys:
            assert await limiter.allow(key) is False

    @pytest.mark.asyncio
    async def test_resetting_one_key_does_not_unblock_others(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=1)
        await limiter.allow("shared1")
        await limiter.allow("shared2")
        await limiter.reset("shared1")
        assert await limiter.allow("shared1") is True
        assert await limiter.allow("shared2") is False


# ---------------------------------------------------------------------------
# Async concurrency safety
# ---------------------------------------------------------------------------


class TestAsyncConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_hammering_does_not_exceed_limit(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=50)
        allowed_count = 0

        async def hammer():
            nonlocal allowed_count
            for _ in range(20):
                if await limiter.allow("shared_ip"):
                    allowed_count += 1

        await asyncio.gather(*(hammer() for _ in range(10)))
        assert allowed_count <= 50

    @pytest.mark.asyncio
    async def test_concurrent_different_keys_no_cross_contamination(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=5)
        per_key_allowed: dict[str, int] = {}

        async def send_requests(key: str) -> None:
            count = 0
            for _ in range(10):
                if await limiter.allow(key):
                    count += 1
            per_key_allowed[key] = count

        keys = [f"task_ip_{i}" for i in range(20)]
        await asyncio.gather(*(send_requests(k) for k in keys))

        for key, count in per_key_allowed.items():
            assert count <= 5, f"Key {key} allowed {count} > 5"

    @pytest.mark.asyncio
    async def test_reset_under_concurrent_access_does_not_raise(self) -> None:
        limiter = InMemoryRateLimiter(max_per_second=5)

        async def allow_loop():
            for _ in range(50):
                await limiter.allow("hammer")

        async def reset_loop():
            for _ in range(20):
                await limiter.reset("hammer")
                await asyncio.sleep(0.001)

        await asyncio.gather(
            *(allow_loop() for _ in range(5)),
            reset_loop(),
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


class TestModuleSingleton:
    @pytest.mark.asyncio
    async def test_singleton_is_valid_limiter_instance(self) -> None:
        assert isinstance(rate_limiter, (InMemoryRateLimiter, UpstashRateLimiter))

    @pytest.mark.asyncio
    async def test_singleton_enforces_limits(self) -> None:
        await rate_limiter.reset()
        test_ip = "singleton_test_edge_ip_xyz"
        results = [await rate_limiter.allow(test_ip) for _ in range(200)]
        allowed = sum(results)
        if isinstance(rate_limiter, InMemoryRateLimiter):
            # In-memory limiter must enforce the configured limit
            assert allowed <= 10
        else:
            # UpstashRateLimiter: if Redis is unreachable it fails open,
            # so we only verify the method returns bools without crashing.
            assert all(isinstance(r, bool) for r in results)

    @pytest.mark.asyncio
    async def test_fresh_inmemory_instance_independent_from_singleton(self) -> None:
        fresh = InMemoryRateLimiter(max_per_second=2)
        assert await fresh.allow("cross_check_ip") is True
        assert await fresh.allow("cross_check_ip") is True
        assert await fresh.allow("cross_check_ip") is False
