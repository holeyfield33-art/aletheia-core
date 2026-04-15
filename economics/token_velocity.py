"""Sliding-window token velocity and budget tracking.

Enforces three limits:
1. Per-second velocity (sliding window) — burst protection.
2. Per-hour budget — sustained throughput cap.
3. Per-session budget — prevents runaway sessions.

Thread-safe: all mutable state is guarded by a lock.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass

_logger = logging.getLogger("aletheia.economics.velocity")


@dataclass(frozen=True)
class VelocityDecision:
    """Result of a velocity/budget check."""
    allowed: bool
    reason: str = ""
    tokens_in_window: int = 0
    hour_total: int = 0
    session_total: int = 0


class TokenVelocityTracker:
    """Sliding-window rate limiter for token consumption."""

    def __init__(
        self,
        max_tokens_per_sec: float = 100.0,
        max_hour_budget: int = 10_000,
        max_session_budget: int = 5_000,
    ) -> None:
        self._max_rate = max_tokens_per_sec
        self._max_hour = max_hour_budget
        self._max_session = max_session_budget
        self._window_sec = 1.0

        self._lock = threading.Lock()
        self._tokens_window: deque[tuple[float, int]] = deque()
        self._hour_total: int = 0
        self._hour_start: float = time.monotonic()
        self._session_total: int = 0

    def check_and_consume(self, token_count: int) -> VelocityDecision:
        """Check limits and consume tokens if allowed.

        Returns ``VelocityDecision(allowed=True)`` if the tokens
        were consumed, otherwise ``allowed=False`` with a reason.
        """
        if token_count < 0:
            return VelocityDecision(allowed=False, reason="Negative token count")

        with self._lock:
            now = time.monotonic()

            # Prune sliding window
            cutoff = now - self._window_sec
            while self._tokens_window and self._tokens_window[0][0] < cutoff:
                self._tokens_window.popleft()

            total_in_window = sum(cnt for _, cnt in self._tokens_window)

            # 1. Per-second velocity check
            if total_in_window + token_count > self._max_rate:
                return VelocityDecision(
                    allowed=False,
                    reason="Token velocity exceeded (per-second limit)",
                    tokens_in_window=total_in_window,
                    hour_total=self._hour_total,
                    session_total=self._session_total,
                )

            # 2. Per-hour budget (reset on boundary)
            if now - self._hour_start > 3600:
                self._hour_total = 0
                self._hour_start = now
            if self._hour_total + token_count > self._max_hour:
                return VelocityDecision(
                    allowed=False,
                    reason="Hourly token budget exceeded",
                    tokens_in_window=total_in_window,
                    hour_total=self._hour_total,
                    session_total=self._session_total,
                )

            # 3. Per-session budget
            if self._session_total + token_count > self._max_session:
                return VelocityDecision(
                    allowed=False,
                    reason="Session token budget exceeded",
                    tokens_in_window=total_in_window,
                    hour_total=self._hour_total,
                    session_total=self._session_total,
                )

            # Consume
            self._tokens_window.append((now, token_count))
            self._hour_total += token_count
            self._session_total += token_count

            return VelocityDecision(
                allowed=True,
                tokens_in_window=total_in_window + token_count,
                hour_total=self._hour_total,
                session_total=self._session_total,
            )

    def reset(self) -> None:
        """Reset all counters (test helper)."""
        with self._lock:
            self._tokens_window.clear()
            self._hour_total = 0
            self._hour_start = time.monotonic()
            self._session_total = 0

    @property
    def session_total(self) -> int:
        with self._lock:
            return self._session_total
