"""Aletheia Core — In-memory sliding-window rate limiter.

Thread-safe, zero-dependency. Enforces max N requests per second per key (IP).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from core.config import settings


_MAX_TRACKED_IPS = 50_000  # memory cap: ~50 KB overhead per entry


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
            # Memory cap: evict the entry with the oldest last-seen timestamp
            # before admitting a new key. Prevents DoS via unique-IP exhaustion.
            if key not in self._windows and len(self._windows) >= _MAX_TRACKED_IPS:
                oldest_key = min(
                    self._windows,
                    key=lambda k: self._windows[k][-1] if self._windows[k] else 0.0,
                )
                del self._windows[oldest_key]

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
