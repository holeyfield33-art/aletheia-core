"""Resource-level circuit breaker for the economic anchor.

Distinct from the rate-limiter circuit breaker in ``core/rate_limit.py``
which handles Redis connection failures. This breaker protects against
resource exhaustion (token budget, velocity spikes, repeated failures).

States:
  CLOSED  — normal operation.
  OPEN    — all calls rejected until cooldown expires.
  HALF_OPEN — one probe call allowed; success → CLOSED, failure → OPEN.
"""
from __future__ import annotations

import logging
import threading
import time
from enum import Enum

_logger = logging.getLogger("aletheia.economics.breaker")


class BreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpen(Exception):
    """Raised when the breaker is open and calls are rejected."""


class ResourceCircuitBreaker:
    """Circuit breaker for resource exhaustion protection."""

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_sec: float = 60.0,
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_sec

        self._lock = threading.Lock()
        self._state = BreakerState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> BreakerState:
        with self._lock:
            return self._state

    def record_failure(self) -> None:
        """Record a failure. Opens the breaker if threshold is reached."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._threshold:
                if self._state != BreakerState.OPEN:
                    _logger.error(
                        "Circuit breaker OPEN after %d failures (cooldown=%.0fs)",
                        self._failure_count,
                        self._cooldown,
                    )
                self._state = BreakerState.OPEN

    def record_success(self) -> None:
        """Record a success. Resets the breaker to CLOSED."""
        with self._lock:
            if self._state == BreakerState.HALF_OPEN:
                _logger.info("Circuit breaker recovered → CLOSED")
            self._state = BreakerState.CLOSED
            self._failure_count = 0

    def check(self) -> bool:
        """Check whether a call is allowed.

        Returns True if allowed, False if the breaker is open.
        Transitions OPEN → HALF_OPEN after cooldown expires.
        """
        with self._lock:
            if self._state == BreakerState.CLOSED:
                return True
            if self._state == BreakerState.OPEN:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._cooldown:
                    self._state = BreakerState.HALF_OPEN
                    _logger.info("Circuit breaker cooldown expired → HALF_OPEN")
                    return True
                return False
            # HALF_OPEN — allow one probe
            return True

    def open(self) -> None:
        """Force the breaker open (manual trip)."""
        with self._lock:
            self._state = BreakerState.OPEN
            self._last_failure_time = time.monotonic()
            _logger.error("Circuit breaker manually opened")

    def reset(self) -> None:
        """Force reset to CLOSED (test helper)."""
        with self._lock:
            self._state = BreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0
