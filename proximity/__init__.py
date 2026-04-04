"""Aletheia Core — Consciousness Proximity Module.

Gated behind CONSCIOUSNESS_PROXIMITY_ENABLED=true.
All layers are READ-ONLY observers or governors.
Shutdown is always privileged and instant.
Nothing in this module executes on import.
"""
from __future__ import annotations
import os

PROXIMITY_ENABLED: bool = os.getenv(
    "CONSCIOUSNESS_PROXIMITY_ENABLED", "false"
).lower() in ("1", "true", "yes")

__all__ = ["PROXIMITY_ENABLED"]
