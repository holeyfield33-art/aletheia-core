"""Tests for the economic anchor: ZSP, token velocity, circuit breaker."""
from __future__ import annotations

import time
import unittest

from economics.zero_standing_privileges import (
    RequestPrivileges,
    ZSPEnforcer,
)
from economics.token_velocity import TokenVelocityTracker
from economics.circuit_breaker import (
    BreakerState,
    ResourceCircuitBreaker,
)


# ---------------------------------------------------------------------------
# Zero Standing Privileges
# ---------------------------------------------------------------------------
class TestZSPEnforcer(unittest.TestCase):
    def test_empty_resources_rejected(self) -> None:
        zsp = ZSPEnforcer()
        result = zsp.enforce("sess1", RequestPrivileges())
        self.assertFalse(result.allowed)
        self.assertIn("ZSP", result.reason)

    def test_declared_resources_allowed(self) -> None:
        zsp = ZSPEnforcer()
        priv = RequestPrivileges.from_list(["tool:calculator"])
        result = zsp.enforce("sess1", priv)
        self.assertTrue(result.allowed)

    def test_allowlist_enforcement(self) -> None:
        zsp = ZSPEnforcer(allowed_resources={"tool:calculator", "tool:search"})
        # Allowed
        priv = RequestPrivileges.from_list(["tool:calculator"])
        self.assertTrue(zsp.enforce("sess1", priv).allowed)
        # Disallowed
        priv = RequestPrivileges.from_list(["tool:admin_panel"])
        result = zsp.enforce("sess1", priv)
        self.assertFalse(result.allowed)
        self.assertIn("Disallowed", result.reason)

    def test_mixed_allowed_disallowed(self) -> None:
        zsp = ZSPEnforcer(allowed_resources={"tool:calc"})
        priv = RequestPrivileges.from_list(["tool:calc", "tool:hack"])
        result = zsp.enforce("sess1", priv)
        self.assertFalse(result.allowed)

    def test_violation_counter(self) -> None:
        zsp = ZSPEnforcer()
        self.assertEqual(zsp.violation_count, 0)
        zsp.enforce("s", RequestPrivileges())
        self.assertEqual(zsp.violation_count, 1)
        zsp.enforce("s", RequestPrivileges())
        self.assertEqual(zsp.violation_count, 2)

    def test_no_allowlist_permits_any(self) -> None:
        """Without an allowlist, any declared resources are accepted."""
        zsp = ZSPEnforcer()
        priv = RequestPrivileges.from_list(["anything:goes"])
        self.assertTrue(zsp.enforce("s", priv).allowed)

    def test_from_list_none(self) -> None:
        priv = RequestPrivileges.from_list(None)
        self.assertEqual(priv.required_resources, ())


# ---------------------------------------------------------------------------
# Token Velocity Tracker
# ---------------------------------------------------------------------------
class TestTokenVelocityTracker(unittest.TestCase):
    def test_basic_consumption(self) -> None:
        tv = TokenVelocityTracker(max_tokens_per_sec=100, max_session_budget=1000)
        result = tv.check_and_consume(50)
        self.assertTrue(result.allowed)
        self.assertEqual(result.tokens_in_window, 50)

    def test_velocity_exceeded(self) -> None:
        tv = TokenVelocityTracker(max_tokens_per_sec=10, max_session_budget=1000)
        r1 = tv.check_and_consume(10)
        self.assertTrue(r1.allowed)
        r2 = tv.check_and_consume(1)
        self.assertFalse(r2.allowed)
        self.assertIn("per-second", r2.reason)

    def test_session_budget_exceeded(self) -> None:
        tv = TokenVelocityTracker(
            max_tokens_per_sec=10000, max_session_budget=100, max_hour_budget=10000
        )
        r1 = tv.check_and_consume(100)
        self.assertTrue(r1.allowed)
        r2 = tv.check_and_consume(1)
        self.assertFalse(r2.allowed)
        self.assertIn("Session", r2.reason)

    def test_hour_budget_exceeded(self) -> None:
        tv = TokenVelocityTracker(
            max_tokens_per_sec=10000, max_hour_budget=50, max_session_budget=10000
        )
        r1 = tv.check_and_consume(50)
        self.assertTrue(r1.allowed)
        r2 = tv.check_and_consume(1)
        self.assertFalse(r2.allowed)
        self.assertIn("Hourly", r2.reason)

    def test_negative_tokens_rejected(self) -> None:
        tv = TokenVelocityTracker()
        result = tv.check_and_consume(-1)
        self.assertFalse(result.allowed)

    def test_reset(self) -> None:
        tv = TokenVelocityTracker(max_tokens_per_sec=10, max_session_budget=100)
        tv.check_and_consume(10)
        self.assertEqual(tv.session_total, 10)
        tv.reset()
        self.assertEqual(tv.session_total, 0)

    def test_zero_tokens(self) -> None:
        tv = TokenVelocityTracker()
        result = tv.check_and_consume(0)
        self.assertTrue(result.allowed)


# ---------------------------------------------------------------------------
# Resource Circuit Breaker
# ---------------------------------------------------------------------------
class TestResourceCircuitBreaker(unittest.TestCase):
    def test_initial_state_closed(self) -> None:
        cb = ResourceCircuitBreaker()
        self.assertEqual(cb.state, BreakerState.CLOSED)
        self.assertTrue(cb.check())

    def test_opens_after_threshold(self) -> None:
        cb = ResourceCircuitBreaker(failure_threshold=3, cooldown_sec=60.0)
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.check())  # Still closed
        cb.record_failure()
        self.assertEqual(cb.state, BreakerState.OPEN)
        self.assertFalse(cb.check())

    def test_success_resets(self) -> None:
        cb = ResourceCircuitBreaker(failure_threshold=3, cooldown_sec=60.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        self.assertEqual(cb.state, BreakerState.CLOSED)
        # Should be able to take 3 more failures
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.check())

    def test_manual_open(self) -> None:
        cb = ResourceCircuitBreaker()
        cb.open()
        self.assertEqual(cb.state, BreakerState.OPEN)
        self.assertFalse(cb.check())

    def test_cooldown_transition_to_half_open(self) -> None:
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        self.assertEqual(cb.state, BreakerState.OPEN)
        time.sleep(0.02)
        self.assertTrue(cb.check())
        self.assertEqual(cb.state, BreakerState.HALF_OPEN)

    def test_half_open_success_closes(self) -> None:
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        time.sleep(0.02)
        cb.check()  # transitions to HALF_OPEN
        cb.record_success()
        self.assertEqual(cb.state, BreakerState.CLOSED)

    def test_reset(self) -> None:
        cb = ResourceCircuitBreaker(failure_threshold=1)
        cb.record_failure()
        self.assertEqual(cb.state, BreakerState.OPEN)
        cb.reset()
        self.assertEqual(cb.state, BreakerState.CLOSED)


if __name__ == "__main__":
    unittest.main()
