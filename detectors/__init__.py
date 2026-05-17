"""Aletheia Core — Detectors package.

Unified detection and monitoring layer: spectral analysis, identity anchoring,
swarm detection, safety bounds, and escalation probing.

Core detectors (always enabled, no extra deps):
  - swarm_detector    : multi-agent coordination detection
  - spectral_rigidity : Bochner-Khintchine drift scoring
  - escalation_probe  : temporal cross-covariance anomaly detection
  - safety_bounds     : configurable action boundaries

Experimental detectors (optional, require httpx + external MCP endpoint):
  - spectral_monitor  : live Geometric Brain MCP health polling
  - sovereign_relay   : policy governor backed by spectral health
  - identity_anchor   : sovereign identity binding
  - proximity_score   : composite proximity scoring

Enable experimental detectors:
    pip install aletheia-cyber-core[detectors]
    export CONSCIOUSNESS_PROXIMITY_ENABLED=true
"""

from __future__ import annotations

from core.config import env_bool

PROXIMITY_ENABLED: bool = env_bool("CONSCIOUSNESS_PROXIMITY_ENABLED")

__all__ = ["PROXIMITY_ENABLED"]
