"""
Distributed state backend for breaker, velocity, and swarm aggregation.
Uses Redis + Lua scripts for atomic read-modify-write operations.

Falls back gracefully when Redis is unavailable — external callers
should catch ``redis.ConnectionError`` and degrade to the in-process
state in ``circuit_breaker.py`` / ``token_velocity.py``.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Optional

import redis

_logger = logging.getLogger("aletheia.economics.distributed_state")


# ---------------------------------------------------------------------------
# State models
# ---------------------------------------------------------------------------
@dataclass
class DistributedBreakerState:
    """Serialisable breaker state for Redis storage."""

    state: str  # "CLOSED", "OPEN", "HALF_OPEN", "COOLDOWN"
    failures: int
    cooldown_expiry: int  # unix timestamp ms
    updated_at: int


@dataclass
class VelocityState:
    """Sliding-window velocity counter."""

    count: int
    window_start: int  # unix timestamp ms
    updated_at: int


@dataclass
class SwarmBucket:
    """Aggregated swarm metrics for a time window."""

    sessions: int
    inconclusive_count: int
    trimmed_mean_drift: float
    last_update: int


# ---------------------------------------------------------------------------
# Lua scripts (loaded once, executed atomically)
# ---------------------------------------------------------------------------
_LUA_BREAKER_TRANSITION = """
local key = KEYS[1]
local new_state = ARGV[1]
local failures = tonumber(ARGV[2])
local cooldown_expiry = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local current = redis.call('GET', key)
if current then
    local data = cjson.decode(current)
    -- Prevent illegal transitions
    if data.state == 'OPEN' and new_state ~= 'HALF_OPEN' then
        return {0, 'already_open'}
    end
    if data.state == 'COOLDOWN' and now < data.cooldown_expiry and new_state ~= 'COOLDOWN' then
        return {0, 'cooldown_active'}
    end
end

local new_data = cjson.encode({
    state = new_state,
    failures = failures,
    cooldown_expiry = cooldown_expiry,
    updated_at = now
})
redis.call('SET', key, new_data)
return {1, 'ok'}
"""

_LUA_VELOCITY_INCREMENT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])

local current = redis.call('GET', key)
if current then
    local data = cjson.decode(current)
    if now - data.window_start > window_ms then
        data = {count = 1, window_start = now, updated_at = now}
    else
        data.count = data.count + 1
        data.updated_at = now
    end
    redis.call('SET', key, cjson.encode(data))
    return cjson.encode(data)
else
    local data = {count = 1, window_start = now, updated_at = now}
    redis.call('SET', key, cjson.encode(data))
    return cjson.encode(data)
end
"""

_LUA_SWARM_UPDATE = """
local key = KEYS[1]
local drift = tonumber(ARGV[1])
local is_inconclusive = ARGV[2] == 'true'
local total_sessions = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local current = redis.call('GET', key)
if current then
    local data = cjson.decode(current)
    data.sessions = data.sessions + total_sessions
    if is_inconclusive then
        data.inconclusive_count = data.inconclusive_count + 1
    end
    -- Exponential moving average for drift
    local alpha = 0.3
    data.trimmed_mean_drift = alpha * drift + (1 - alpha) * data.trimmed_mean_drift
    data.last_update = now
    redis.call('SET', key, cjson.encode(data))
    return cjson.encode(data)
else
    local inc = 0
    if is_inconclusive then
        inc = 1
    end
    local data = {
        sessions = total_sessions,
        inconclusive_count = inc,
        trimmed_mean_drift = drift,
        last_update = now
    }
    redis.call('SET', key, cjson.encode(data))
    return cjson.encode(data)
end
"""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
class DistributedStateManager:
    """Redis-backed distributed state for breaker, velocity, and swarm data.

    All mutating operations use pre-registered Lua scripts so that
    read-modify-write is atomic even under concurrent access from
    multiple worker processes.
    """

    def __init__(self, redis_client: redis.Redis, key_prefix: str = "aletheia") -> None:
        self.redis = redis_client
        self.prefix = key_prefix
        self._register_scripts()

    def _register_scripts(self) -> None:
        """Register Lua scripts once at init (server-side SHA caching)."""
        self._breaker_script = self.redis.register_script(_LUA_BREAKER_TRANSITION)
        self._velocity_script = self.redis.register_script(_LUA_VELOCITY_INCREMENT)
        self._swarm_script = self.redis.register_script(_LUA_SWARM_UPDATE)

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------
    def get_breaker(self, session_id: str) -> Optional[DistributedBreakerState]:
        key = f"{self.prefix}:breaker:{session_id}"
        data = self.redis.get(key)
        if data:
            return DistributedBreakerState(**json.loads(data))
        return None

    def set_breaker(self, session_id: str, state: DistributedBreakerState) -> bool:
        key = f"{self.prefix}:breaker:{session_id}"
        self.redis.set(key, json.dumps(asdict(state)))
        return True

    def atomic_transition_breaker(
        self,
        session_id: str,
        new_state: str,
        failures: int,
        cooldown_expiry: int,
    ) -> tuple:
        """Atomic breaker state transition via Lua script."""
        key = f"{self.prefix}:breaker:{session_id}"
        now = int(time.time() * 1000)
        return self._breaker_script(
            keys=[key],
            args=[new_state, failures, cooldown_expiry, now],
        )

    # ------------------------------------------------------------------
    # Token velocity
    # ------------------------------------------------------------------
    def get_velocity(self, session_id: str) -> Optional[VelocityState]:
        key = f"{self.prefix}:velocity:{session_id}"
        data = self.redis.get(key)
        if data:
            return VelocityState(**json.loads(data))
        return None

    def increment_velocity(
        self, session_id: str, window_ms: int = 1000
    ) -> VelocityState:
        """Atomic increment with sliding-window reset."""
        key = f"{self.prefix}:velocity:{session_id}"
        now = int(time.time() * 1000)
        result = self._velocity_script(
            keys=[key],
            args=[now, window_ms],
        )
        return VelocityState(**json.loads(result))

    # ------------------------------------------------------------------
    # Swarm aggregation
    # ------------------------------------------------------------------
    def update_swarm_bucket(
        self,
        window_id: str,
        drift: float,
        inconclusive: bool,
        total_sessions: int,
    ) -> SwarmBucket:
        """Atomic swarm bucket update with exponential moving average."""
        key = f"{self.prefix}:swarm:{window_id}"
        now = int(time.time() * 1000)
        result = self._swarm_script(
            keys=[key],
            args=[drift, str(inconclusive).lower(), total_sessions, now],
        )
        return SwarmBucket(**json.loads(result))
