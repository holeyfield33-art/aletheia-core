"""Aletheia Core — Detectors package.

Unified detection and monitoring layer: spectral analysis, identity anchoring,
swarm detection, safety bounds, and escalation probing.

Runtime gating: set CONSCIOUSNESS_PROXIMITY_ENABLED=true to enable the
spectral monitor and sovereign relay subsystems.
"""

from __future__ import annotations

from core.config import env_bool

PROXIMITY_ENABLED: bool = env_bool("CONSCIOUSNESS_PROXIMITY_ENABLED")

__all__ = ["PROXIMITY_ENABLED"]
