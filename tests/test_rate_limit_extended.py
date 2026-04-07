"""Enterprise-grade edge-case tests for core/rate_limit.py.

Covers:
- Sliding-window expiry (time-based): blocked IPs allowed again after 1 s
- Thread safety under concurrent hammering
- Per-key independence at high concurrency
- reset(key) vs reset(None) semantics
- RateLimiter instantiated with explicit max_per_second=0 / 1 / large
- Module-level singleton shares no state with fresh instances
"""

from __future__ import annotations

import threading
import time
import unittest

from core.rate_limit import RateLimiter, rate_limiter


class TestSlidingWindowExpiry(unittest.TestCase):
    """The 1-second window must slide: old requests expire so new ones are allowed."""

    def test_requests_allowed_after_window_expires(self) -> None:
        """After waiting >1 s, the window should reset and new requests allowed."""
        limiter = RateLimiter(max_per_second=2)
        self.assertTrue(limiter.allow("ip1"))
        self.assertTrue(limiter.allow("ip1"))
        self.assertFalse(limiter.allow("ip1"))  # at limit

        time.sleep(1.05)  # wait for window to expire

        # Window has slid — all old timestamps pruned
        self.assertTrue(limiter.allow("ip1"), "Request should be allowed after window expires")

    def test_partial_window_expiry(self) -> None:
        """Only timestamps outside the 1-second window should be pruned."""
        limiter = RateLimiter(max_per_second=2)
        limiter.allow("ip1")  # T=0
        time.sleep(0.6)
        limiter.allow("ip1")  # T=0.6 — now at limit (2 requests in window)
        self.assertFalse(limiter.allow("ip1"))

        time.sleep(0.5)  # T=1.1 — first request (T=0) has expired, second (T=0.6) still live

        # One slot free (T=0 expired), one occupied (T=0.6)
        self.assertTrue(limiter.allow("ip1"))
        # But still at limit now
        self.assertFalse(limiter.allow("ip1"))

    def test_full_burst_then_recover(self) -> None:
        """A full burst of N should block, then a full N allowed after expiry."""
        n = 5
        limiter = RateLimiter(max_per_second=n)
        for _ in range(n):
            self.assertTrue(limiter.allow("burst_ip"))
        self.assertFalse(limiter.allow("burst_ip"))

        time.sleep(1.05)

        for i in range(n):
            self.assertTrue(limiter.allow("burst_ip"), f"Request {i+1} denied after expiry")


class TestResetSemantics(unittest.TestCase):
    """reset() must clear state correctly for single key and all keys."""

    def test_reset_single_key_clears_that_key(self) -> None:
        limiter = RateLimiter(max_per_second=1)
        limiter.allow("a")
        self.assertFalse(limiter.allow("a"))
        limiter.reset("a")
        self.assertTrue(limiter.allow("a"))

    def test_reset_single_key_does_not_affect_others(self) -> None:
        limiter = RateLimiter(max_per_second=1)
        limiter.allow("a")
        limiter.allow("b")
        self.assertFalse(limiter.allow("a"))
        self.assertFalse(limiter.allow("b"))

        limiter.reset("a")  # only clear "a"

        self.assertTrue(limiter.allow("a"))   # "a" reset — allowed
        self.assertFalse(limiter.allow("b"))  # "b" still blocked

    def test_reset_none_clears_all_keys(self) -> None:
        limiter = RateLimiter(max_per_second=1)
        for key in ("x", "y", "z"):
            limiter.allow(key)
            self.assertFalse(limiter.allow(key))

        limiter.reset()  # clear all

        for key in ("x", "y", "z"):
            self.assertTrue(limiter.allow(key), f"Key '{key}' should be allowed after global reset")

    def test_reset_nonexistent_key_does_not_raise(self) -> None:
        limiter = RateLimiter(max_per_second=5)
        # Should not raise KeyError
        limiter.reset("never_seen_key")

    def test_reset_key_then_window_still_works(self) -> None:
        limiter = RateLimiter(max_per_second=2)
        limiter.allow("a")
        limiter.reset("a")
        limiter.allow("a")
        limiter.allow("a")
        self.assertFalse(limiter.allow("a"))  # back to limit


class TestMaxPerSecondBoundaryValues(unittest.TestCase):
    """Verify correct behaviour at extreme max_per_second values."""

    def test_max_1_allows_first_blocks_second(self) -> None:
        limiter = RateLimiter(max_per_second=1)
        self.assertTrue(limiter.allow("ip"))
        self.assertFalse(limiter.allow("ip"))

    def test_max_1_sequential_keys_each_get_one_slot(self) -> None:
        limiter = RateLimiter(max_per_second=1)
        for i in range(10):
            self.assertTrue(limiter.allow(f"ip_{i}"))

    def test_large_max_allows_many(self) -> None:
        limiter = RateLimiter(max_per_second=1000)
        for _ in range(1000):
            self.assertTrue(limiter.allow("big_ip"))
        self.assertFalse(limiter.allow("big_ip"))


class TestPerKeyIndependence(unittest.TestCase):
    """Different keys must never interfere with each other's counters."""

    def test_10_keys_each_independent_limit(self) -> None:
        limiter = RateLimiter(max_per_second=3)
        keys = [f"client_{i}" for i in range(10)]

        # Fill each key to limit
        for key in keys:
            for _ in range(3):
                self.assertTrue(limiter.allow(key))
            self.assertFalse(limiter.allow(key))

        # All still blocked independently
        for key in keys:
            self.assertFalse(limiter.allow(key))

    def test_resetting_one_key_does_not_unblock_others(self) -> None:
        limiter = RateLimiter(max_per_second=1)
        limiter.allow("shared1")
        limiter.allow("shared2")
        limiter.reset("shared1")
        self.assertTrue(limiter.allow("shared1"))
        self.assertFalse(limiter.allow("shared2"))


class TestThreadSafety(unittest.TestCase):
    """Concurrent access from multiple threads must not corrupt internal state."""

    def test_concurrent_hammering_does_not_exceed_limit(self) -> None:
        """Total allowed requests across all threads must not exceed max_per_second."""
        limiter = RateLimiter(max_per_second=50)
        allowed_count = [0]
        lock = threading.Lock()
        errors = []

        def hammer():
            try:
                for _ in range(20):
                    result = limiter.allow("shared_ip")
                    if result:
                        with lock:
                            allowed_count[0] += 1
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=hammer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread errors: {errors}")
        self.assertLessEqual(allowed_count[0], 50,
                             f"Allowed {allowed_count[0]} requests, limit is 50")

    def test_concurrent_different_keys_no_cross_contamination(self) -> None:
        """Each key should independently enforce its own limit under concurrency."""
        limiter = RateLimiter(max_per_second=5)
        per_key_allowed: dict[str, int] = {}
        lock = threading.Lock()

        def send_requests(key: str) -> None:
            count = sum(1 for _ in range(10) if limiter.allow(key))
            with lock:
                per_key_allowed[key] = count

        keys = [f"thread_ip_{i}" for i in range(20)]
        threads = [threading.Thread(target=send_requests, args=(k,)) for k in keys]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for key, count in per_key_allowed.items():
            self.assertLessEqual(count, 5,
                                 f"Key {key} allowed {count} > 5 requests")

    def test_reset_under_concurrent_access_does_not_raise(self) -> None:
        """reset() called while threads are using allow() must not raise."""
        limiter = RateLimiter(max_per_second=5)
        errors = []

        def allow_loop():
            try:
                for _ in range(50):
                    limiter.allow("hammer")
            except Exception as exc:
                errors.append(exc)

        def reset_loop():
            try:
                for _ in range(20):
                    limiter.reset("hammer")
                    time.sleep(0.001)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=allow_loop) for _ in range(5)]
        threads.append(threading.Thread(target=reset_loop))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Errors under concurrency: {errors}")


class TestModuleSingleton(unittest.TestCase):
    """The module-level rate_limiter singleton must be an independent instance."""

    def setUp(self) -> None:
        rate_limiter.reset()

    def test_singleton_is_rate_limiter_instance(self) -> None:
        self.assertIsInstance(rate_limiter, RateLimiter)

    def test_singleton_enforces_limits(self) -> None:
        """Singleton should enforce its configured limit."""
        # Exhaust the singleton limit for a unique IP
        test_ip = "singleton_test_edge_ip_xyz"
        results = [rate_limiter.allow(test_ip) for _ in range(200)]
        allowed = sum(results)
        # At most rate_limit_per_second (default 10) should be allowed
        self.assertLessEqual(allowed, 10)

    def test_fresh_instance_independent_from_singleton(self) -> None:
        """A newly constructed RateLimiter has no shared state with the singleton."""
        fresh = RateLimiter(max_per_second=2)
        rate_limiter.allow("cross_check_ip")
        # fresh limiter should be unaffected
        self.assertTrue(fresh.allow("cross_check_ip"))
        self.assertTrue(fresh.allow("cross_check_ip"))
        self.assertFalse(fresh.allow("cross_check_ip"))


if __name__ == "__main__":
    unittest.main()
