"""Aletheia Core — Consciousness Proximity Module.

Gated behind CONSCIOUSNESS_PROXIMITY_ENABLED=true.
All layers are READ-ONLY observers or governors.
Shutdown is always privileged and instant.
Nothing in this module executes on import.
"""

from __future__ import annotations

from core.config import env_bool

PROXIMITY_ENABLED: bool = env_bool("CONSCIOUSNESS_PROXIMITY_ENABLED")

__all__ = ["PROXIMITY_ENABLED"]
