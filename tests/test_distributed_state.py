"""Tests for the distributed state backend (Redis + Lua)."""
from __future__ import annotations

import time
import unittest

import pytest
import redis

from economics.distributed_state import (
    DistributedBreakerState,
    DistributedStateManager,
    VelocityState,
)

# All tests require a live Redis on localhost:6379.
# CI environments without Redis will skip automatically.
_REDIS_AVAILABLE = False
try:
    _r = redis.Redis(host="localhost", port=6379, db=15, socket_connect_timeout=1)
    _r.ping()
    _REDIS_AVAILABLE = True
except Exception:
    pass

_skip_no_redis = pytest.mark.skipif(
    not _REDIS_AVAILABLE,
    reason="Redis not available on localhost:6379",
)


@pytest.fixture
def redis_client():
    r = redis.Redis(host="localhost", port=6379, db=15, decode_responses=False)
    r.flushdb()
    yield r
    r.flushdb()


@pytest.fixture
def state_manager(redis_client):
    return DistributedStateManager(redis_client, key_prefix="test")


@_skip_no_redis
class TestBreakerCRUD:
    def test_set_and_get(self, state_manager):
        state = DistributedBreakerState(
            state="CLOSED", failures=0, cooldown_expiry=0,
            updated_at=int(time.time() * 1000),
        )
        state_manager.set_breaker("session1", state)
        retrieved = state_manager.get_breaker("session1")
        assert retrieved is not None
        assert retrieved.state == "CLOSED"
        assert retrieved.failures == 0

    def test_get_missing_returns_none(self, state_manager):
        assert state_manager.get_breaker("nonexistent") is None

    def test_overwrite(self, state_manager):
        now = int(time.time() * 1000)
        state_manager.set_breaker("s1", DistributedBreakerState("CLOSED", 0, 0, now))
        state_manager.set_breaker("s1", DistributedBreakerState("OPEN", 5, now + 60000, now))
        retrieved = state_manager.get_breaker("s1")
        assert retrieved.state == "OPEN"
        assert retrieved.failures == 5


@_skip_no_redis
class TestAtomicTransition:
    def test_transition_to_open(self, state_manager):
        result = state_manager.atomic_transition_breaker(
            "session1", "OPEN", 3, int(time.time() * 1000) + 60000,
        )
        assert result[0] == 1
        breaker = state_manager.get_breaker("session1")
        assert breaker.state == "OPEN"

    def test_open_blocks_non_halfopen_transition(self, state_manager):
        # First set to OPEN
        state_manager.atomic_transition_breaker(
            "s1", "OPEN", 3, int(time.time() * 1000) + 60000,
        )
        # Try to go to CLOSED — should be blocked
        result = state_manager.atomic_transition_breaker(
            "s1", "CLOSED", 0, 0,
        )
        assert result[0] == 0
        assert state_manager.get_breaker("s1").state == "OPEN"

    def test_open_allows_halfopen_transition(self, state_manager):
        state_manager.atomic_transition_breaker(
            "s1", "OPEN", 3, int(time.time() * 1000) + 60000,
        )
        result = state_manager.atomic_transition_breaker(
            "s1", "HALF_OPEN", 3, 0,
        )
        assert result[0] == 1
        assert state_manager.get_breaker("s1").state == "HALF_OPEN"


@_skip_no_redis
class TestVelocityIncrement:
    def test_first_increment(self, state_manager):
        vel = state_manager.increment_velocity("session1", window_ms=1000)
        assert vel.count == 1

    def test_multiple_increments(self, state_manager):
        state_manager.increment_velocity("session1", window_ms=1000)
        vel2 = state_manager.increment_velocity("session1", window_ms=1000)
        assert vel2.count == 2

    def test_window_expiry_resets_count(self, state_manager):
        vel = state_manager.increment_velocity("session1", window_ms=100)
        assert vel.count == 1
        time.sleep(0.15)
        vel2 = state_manager.increment_velocity("session1", window_ms=100)
        assert vel2.count == 1  # Reset because window expired

    def test_get_velocity(self, state_manager):
        state_manager.increment_velocity("s1", window_ms=1000)
        state_manager.increment_velocity("s1", window_ms=1000)
        vel = state_manager.get_velocity("s1")
        assert vel is not None
        assert vel.count == 2

    def test_get_velocity_missing(self, state_manager):
        assert state_manager.get_velocity("missing") is None


@_skip_no_redis
class TestSwarmBucket:
    def test_first_update(self, state_manager):
        bucket = state_manager.update_swarm_bucket(
            "window1", drift=0.5, inconclusive=False, total_sessions=10,
        )
        assert bucket.sessions == 10
        assert bucket.inconclusive_count == 0
        assert bucket.trimmed_mean_drift == pytest.approx(0.5)

    def test_inconclusive_flag(self, state_manager):
        bucket = state_manager.update_swarm_bucket(
            "w1", drift=0.3, inconclusive=True, total_sessions=5,
        )
        assert bucket.inconclusive_count == 1

    def test_ema_drift(self, state_manager):
        state_manager.update_swarm_bucket("w1", drift=1.0, inconclusive=False, total_sessions=1)
        bucket = state_manager.update_swarm_bucket("w1", drift=0.0, inconclusive=False, total_sessions=1)
        # EMA: 0.3 * 0.0 + 0.7 * 1.0 = 0.7
        assert bucket.trimmed_mean_drift == pytest.approx(0.7, abs=0.01)

    def test_sessions_accumulate(self, state_manager):
        state_manager.update_swarm_bucket("w1", drift=0.1, inconclusive=False, total_sessions=10)
        bucket = state_manager.update_swarm_bucket("w1", drift=0.2, inconclusive=False, total_sessions=5)
        assert bucket.sessions == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
