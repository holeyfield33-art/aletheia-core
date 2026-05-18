# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Singleton agent instances shared across the server."""
from __future__ import annotations

from agents.judge import AletheiaJudge
from agents.nitpicker import AletheiaNitpickerV2
from agents.scout import AletheiaScoutV2

scout = AletheiaScoutV2()
nitpicker = AletheiaNitpickerV2()
judge = AletheiaJudge()

# Lazy singleton — avoids import-time TPM probing in tests.
_sovereign_runtime = None


def _get_sovereign_runtime():
    global _sovereign_runtime
    if _sovereign_runtime is None:
        from core.unified_audit import UnifiedSovereignRuntime

        _sovereign_runtime = UnifiedSovereignRuntime()
    return _sovereign_runtime
