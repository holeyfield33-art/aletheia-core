# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Shared startup state — stdlib only, no server.* imports (avoids circular deps)."""
from __future__ import annotations

import time as _time

_BOOT_TIME: float = _time.time()
_ready: bool = False
_startup_error_detail: str = "startup not completed"
