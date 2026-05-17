"""Tests for economics modules: circuit_breaker, token_velocity, zero_standing_privileges."""

from __future__ import annotations

import threading
import time


from guards.circuit_breaker import BreakerState, ResourceCircuitBreaker
from guards.token_velocity import TokenVelocityTracker
from guards.zero_standing_privileges import RequestPrivileges, ZSPEnforcer


# ---------------------------------------------------------------------------
# ResourceCircuitBreaker
# ---------------------------------------------------------------------------


class TestResourceCircuitBreakerStates:
    def test_initial_state_is_closed(self):
        cb = ResourceCircuitBreaker()
        assert cb.state == BreakerState.CLOSED

    def test_check_allows_when_closed(self):
        cb = ResourceCircuitBreaker()
        assert cb.check() is True

    def test_single_failure_below_threshold_stays_closed(self):
        cb = ResourceCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == BreakerState.CLOSED

    def test_failures_at_threshold_open_breaker(self):
        cb = ResourceCircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == BreakerState.OPEN

    def test_check_rejects_when_open(self):
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=999)
        cb.record_failure()
        assert cb.check() is False

    def test_check_transitions_open_to_half_open_after_cooldown(self):
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        time.sleep(0.02)
        assert cb.check() is True
        assert cb.state == BreakerState.HALF_OPEN

    def test_success_in_half_open_closes_breaker(self):
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        time.sleep(0.02)
        cb.check()  # triggers HALF_OPEN
        cb.record_success()
        assert cb.state == BreakerState.CLOSED

    def test_failure_in_half_open_reopens_breaker(self):
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        time.sleep(0.02)
        cb.check()  # HALF_OPEN
        cb.record_failure()
        assert cb.state == BreakerState.OPEN

    def test_record_success_resets_failure_count(self):
        cb = ResourceCircuitBreaker(failure_threshold=5)
        for _ in range(3):
            cb.record_failure()
        cb.record_success()
        assert cb.state == BreakerState.CLOSED
        # Should need full threshold again
        for _ in range(4):
            cb.record_failure()
        assert cb.state == BreakerState.CLOSED

    def test_manual_open_blocks_check(self):
        cb = ResourceCircuitBreaker(failure_threshold=100)
        cb.open()
        assert cb.state == BreakerState.OPEN
        assert cb.check() is False

    def test_reset_restores_closed_state(self):
        cb = ResourceCircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == BreakerState.OPEN
        cb.reset()
        assert cb.state == BreakerState.CLOSED
        assert cb.check() is True

    def test_extra_failures_beyond_threshold_stay_open(self):
        cb = ResourceCircuitBreaker(failure_threshold=2, cooldown_sec=999)
        for _ in range(10):
            cb.record_failure()
        assert cb.state == BreakerState.OPEN
        assert cb.check() is False

    def test_half_open_allows_exactly_one_probe(self):
        cb = ResourceCircuitBreaker(failure_threshold=1, cooldown_sec=0.01)
        cb.record_failure()
        time.sleep(0.02)
        # First check → HALF_OPEN, probe allowed
        assert cb.check() is True
        assert cb.state == BreakerState.HALF_OPEN
        # Second check while still HALF_OPEN also allowed (probe in progress)
        assert cb.check() is True

    def test_thread_safety_under_concurrent_failures(self):
        cb = ResourceCircuitBreaker(failure_threshold=50, cooldown_sec=999)
        errors: list[Exception] = []

        def fail_20() -> None:
            for _ in range(20):
                try:
                    cb.record_failure()
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=fail_20) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert cb.state == BreakerState.OPEN  # 100 > threshold=50


# ---------------------------------------------------------------------------
# TokenVelocityTracker
# ---------------------------------------------------------------------------


class TestTokenVelocityTracker:
    def test_allows_tokens_within_per_second_rate(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100)
        result = tracker.check_and_consume(50)
        assert result.allowed is True
        assert result.tokens_in_window == 50

    def test_blocks_when_per_second_velocity_exceeded(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100)
        tracker.check_and_consume(80)
        result = tracker.check_and_consume(30)  # 80+30 > 100
        assert result.allowed is False
        assert "per-second" in result.reason

    def test_session_total_accumulates_across_calls(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=1000, max_session_budget=500)
        tracker.check_and_consume(100)
        tracker.check_and_consume(200)
        assert tracker.session_total == 300

    def test_blocks_on_session_budget_exceeded(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=1000, max_session_budget=100)
        tracker.check_and_consume(80)
        result = tracker.check_and_consume(30)  # 80+30 > 100
        assert result.allowed is False
        assert "Session" in result.reason

    def test_blocks_on_hourly_budget_exceeded(self):
        tracker = TokenVelocityTracker(
            max_tokens_per_sec=10_000,
            max_hour_budget=100,
            max_session_budget=10_000,
        )
        tracker.check_and_consume(90)
        result = tracker.check_and_consume(20)  # 90+20 > 100
        assert result.allowed is False
        assert "Hourly" in result.reason

    def test_negative_token_count_rejected(self):
        tracker = TokenVelocityTracker()
        result = tracker.check_and_consume(-1)
        assert result.allowed is False
        assert "Negative" in result.reason

    def test_zero_tokens_allowed(self):
        tracker = TokenVelocityTracker()
        result = tracker.check_and_consume(0)
        assert result.allowed is True

    def test_reset_clears_all_counters(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100, max_session_budget=100)
        tracker.check_and_consume(90)
        tracker.reset()
        assert tracker.session_total == 0
        result = tracker.check_and_consume(90)
        assert result.allowed is True

    def test_sliding_window_expires_old_tokens(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100)
        tracker.check_and_consume(90)
        time.sleep(1.1)  # wait for 1-second window to expire
        result = tracker.check_and_consume(90)
        assert result.allowed is True

    def test_decision_fields_populated_on_rejection(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100)
        tracker.check_and_consume(80)
        result = tracker.check_and_consume(30)
        assert result.allowed is False
        assert result.tokens_in_window == 80
        assert result.session_total == 80
        assert result.reason != ""

    def test_session_total_not_incremented_on_rejection(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100, max_session_budget=1000)
        tracker.check_and_consume(80)
        tracker.check_and_consume(30)  # rejected
        assert tracker.session_total == 80

    def test_thread_safety_concurrent_consumes(self):
        tracker = TokenVelocityTracker(
            max_tokens_per_sec=10_000, max_session_budget=10_000
        )
        results: list[bool] = []
        lock = threading.Lock()

        def consume_10() -> None:
            for _ in range(10):
                r = tracker.check_and_consume(1)
                with lock:
                    results.append(r.allowed)

        threads = [threading.Thread(target=consume_10) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)
        assert tracker.session_total == 50

    def test_exact_budget_boundary_allowed(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=100, max_session_budget=100)
        result = tracker.check_and_consume(100)
        assert result.allowed is True

    def test_one_over_budget_rejected(self):
        tracker = TokenVelocityTracker(max_tokens_per_sec=1000, max_session_budget=100)
        result = tracker.check_and_consume(101)
        assert result.allowed is False


# ---------------------------------------------------------------------------
# ZSPEnforcer
# ---------------------------------------------------------------------------


class TestZSPEnforcer:
    def test_allows_declared_resource_in_allowlist(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read", "db:write"})
        result = enforcer.enforce("s1", RequestPrivileges.from_list(["db:read"]))
        assert result.allowed is True

    def test_blocks_resource_not_in_allowlist(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        result = enforcer.enforce("s1", RequestPrivileges.from_list(["db:write"]))
        assert result.allowed is False
        assert "db:write" in result.reason

    def test_blocks_empty_resource_declaration(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        result = enforcer.enforce("s1", RequestPrivileges.from_list([]))
        assert result.allowed is False
        assert "declare" in result.reason

    def test_blocks_none_resource_declaration(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        result = enforcer.enforce("s1", RequestPrivileges.from_list(None))
        assert result.allowed is False

    def test_violation_counter_increments_on_each_block(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        enforcer.enforce("s1", RequestPrivileges.from_list([]))
        enforcer.enforce("s2", RequestPrivileges.from_list([]))
        assert enforcer.violation_count == 2

    def test_violation_counter_unchanged_on_success(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        enforcer.enforce("s1", RequestPrivileges.from_list(["db:read"]))
        assert enforcer.violation_count == 0

    def test_open_allowlist_accepts_any_declared_resource(self):
        enforcer = ZSPEnforcer()  # no restriction
        result = enforcer.enforce("s1", RequestPrivileges.from_list(["anything:here"]))
        assert result.allowed is True

    def test_multiple_resources_all_in_allowlist_accepted(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read", "cache:read", "api:call"})
        result = enforcer.enforce(
            "s1", RequestPrivileges.from_list(["db:read", "cache:read"])
        )
        assert result.allowed is True

    def test_partial_allowlist_match_denied(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        result = enforcer.enforce(
            "s1", RequestPrivileges.from_list(["db:read", "db:write"])
        )
        assert result.allowed is False

    def test_from_list_produces_correct_tuple(self):
        priv = RequestPrivileges.from_list(["a", "b", "c"])
        assert priv.required_resources == ("a", "b", "c")

    def test_from_list_empty_produces_empty_tuple(self):
        priv = RequestPrivileges.from_list([])
        assert priv.required_resources == ()

    def test_from_list_none_produces_empty_tuple(self):
        priv = RequestPrivileges.from_list(None)
        assert priv.required_resources == ()

    def test_disallowed_resource_listed_in_reason(self):
        enforcer = ZSPEnforcer(allowed_resources={"db:read"})
        result = enforcer.enforce("s1", RequestPrivileges.from_list(["secrets:vault"]))
        assert "secrets:vault" in result.reason

    def test_mixed_allowed_and_denied_increments_violation(self):
        enforcer = ZSPEnforcer(allowed_resources={"ok"})
        enforcer.enforce("s1", RequestPrivileges.from_list(["ok", "not-ok"]))
        assert enforcer.violation_count == 1
