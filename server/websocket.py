# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""WebSocket endpoint for the Aletheia live audit stream.

Register with the FastAPI app in server/app.py:
    app.websocket("/ws/audit")(ws_audit_endpoint)
"""
from __future__ import annotations

from starlette.websockets import WebSocket


async def ws_audit_endpoint(ws: WebSocket) -> None:
    """Authenticated, tenant-scoped, PII-redacted live audit stream."""
    from core.ws_audit import ws_audit_handler

    await ws_audit_handler(ws)
