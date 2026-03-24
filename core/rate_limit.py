"""Aletheia Core — In-memory sliding-window rate limiter.

Thread-safe, zero-dependency. Enforces max N requests per second per key (IP).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from core.config import settings


class RateLimiter:
    """Sliding-window counter rate limiter (per-key, 1-second window)."""

    def __init__(self, max_per_second: int | None = None) -> None:
        self._max = max_per_second or settings.rate_limit_per_second
        self._lock = threading.Lock()
        # key → list of request timestamps (epoch floats)
        self._windows: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """Return True if the request is within limits, False to reject."""
        now = time.monotonic()
        cutoff = now - 1.0  # 1-second window

        with self._lock:
            timestamps = self._windows[key]
            # Prune expired entries
            self._windows[key] = timestamps = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self._max:
                return False
            timestamps.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        """Clear state for a single key or all keys."""
        with self._lock:
            if key is None:
                self._windows.clear()
            else:
                self._windows.pop(key, None)


# Module-level singleton
rate_limiter = RateLimiter()
