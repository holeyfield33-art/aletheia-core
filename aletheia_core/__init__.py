# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — runtime audit and pre-execution block layer for AI agents.

Quick-start (Python embedding):

    from aletheia_core import Scout, Nitpicker, Judge

    scout    = Scout()
    nitpicker = Nitpicker()
    judge    = Judge()

    threat_score, report = scout.evaluate_threat_context(client_ip, payload)
    blocked, reason      = nitpicker.check_semantic_block(payload)
    allowed, veto        = judge.verify_action(action, payload=payload)

For HTTP usage, run the FastAPI server:

    uvicorn server.app:app --host 0.0.0.0 --port 8000

See README.md for the full quickstart.
"""
from __future__ import annotations

try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError

    try:
        __version__: str = _pkg_version("aletheia-cyber-core")
    except PackageNotFoundError:
        __version__ = "2.0.0"
except ImportError:
    __version__ = "2.0.0"

from agents.scout import AletheiaScoutV2 as Scout
from agents.nitpicker import AletheiaNitpickerV2 as Nitpicker
from agents.judge import AletheiaJudge as Judge
from core.agent_trifecta import AgentTrifectaContext, evaluate_agent_trifecta

__all__ = [
    "Scout",
    "Nitpicker",
    "Judge",
    "AgentTrifectaContext",
    "evaluate_agent_trifecta",
    "__version__",
]
