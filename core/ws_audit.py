# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — WebSocket audit stream.

Provides an authenticated, tenant-scoped, PII-redacted live stream of
audit events via ``/ws/audit``.

Supports three authentication modes:
  1. API key via ``?token=<key>`` query parameter
  2. Admin key via ``?token=<admin_key>``
  3. Short-lived JWT via ``?token=<jwt>`` (signed with ALETHEIA_WS_JWT_SECRET)

Includes per-tenant rate limiting and ping/pong heartbeat keepalive.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from core.audit import redact_pii
from core.metrics import WS_CONNECTIONS

_logger = logging.getLogger("aletheia.ws_audit")

# Fields never sent over the WebSocket
_STRIP_FIELDS = frozenset(
    {
        "payload_sha256",
        "payload_preview",
        "payload_length",
        "receipt",
    }
)

# Per-tenant rate limiting: max WS connections per tenant
_WS_MAX_PER_TENANT: int = int(os.getenv("ALETHEIA_WS_MAX_PER_TENANT", "10"))

# Heartbeat interval in seconds
_WS_HEARTBEAT_INTERVAL: int = int(os.getenv("ALETHEIA_WS_HEARTBEAT_SECONDS", "30"))


def _redact_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with PII scrubbed and sensitive fields stripped."""
    out: dict[str, Any] = {}
    for key, val in record.items():
        if key in _STRIP_FIELDS:
            continue
        if isinstance(val, str):
            val = redact_pii(val)
        out[key] = val
    return out


class AuditBroadcast:
    """Fan-out audit records to WebSocket subscribers, scoped by tenant."""

    def __init__(self) -> None:
        # tenant_id → set of (WebSocket, asyncio.Queue)
        self._subs: dict[str, set[tuple[WebSocket, asyncio.Queue]]] = {}

    def tenant_count(self, tenant_id: str) -> int:
        """Return the number of active connections for a tenant."""
        return len(self._subs.get(tenant_id, set()))

    def subscribe(self, tenant_id: str, ws: WebSocket) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subs.setdefault(tenant_id, set()).add((ws, queue))
        WS_CONNECTIONS.inc()
        return queue

    def unsubscribe(self, tenant_id: str, ws: WebSocket) -> None:
        subs = self._subs.get(tenant_id)
        if not subs:
            return
        to_remove = {item for item in subs if item[0] is ws}
        subs -= to_remove
        if not subs:
            self._subs.pop(tenant_id, None)
        WS_CONNECTIONS.dec()

    def publish(self, record: dict[str, Any]) -> None:
        """Non-blocking fan-out of an audit record to matching tenant subscribers."""
        tenant_id = record.get("tenant_id", "default")
        redacted = _redact_record(record)
        msg = json.dumps(redacted, default=str)

        for target_tenant in (tenant_id, "__all__"):
            subs = self._subs.get(target_tenant)
            if not subs:
                continue
            stale = []
            for ws, q in subs:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    stale.append((ws, q))
            for item in stale:
                subs.discard(item)


audit_broadcast = AuditBroadcast()


async def ws_audit_handler(ws: WebSocket) -> None:
    """WebSocket handler for ``/ws/audit``.

    Authentication: requires ``token`` query parameter matching an API key,
    the admin key, or a short-lived JWT.  Tenant scoping is derived from the key.
    Includes per-tenant connection limit and ping/pong heartbeat.
    """
    token = ws.query_params.get("token", "")
    if not token:
        await ws.close(code=4001, reason="Missing token parameter")
        return

    # Authenticate
    tenant_id = _authenticate_ws_token(token)
    if tenant_id is None:
        await ws.close(code=4003, reason="Invalid or expired token")
        return

    # Per-tenant rate limit
    if (
        tenant_id != "__all__"
        and audit_broadcast.tenant_count(tenant_id) >= _WS_MAX_PER_TENANT
    ):
        await ws.close(code=4029, reason="Too many connections for this tenant")
        return

    await ws.accept()
    queue = audit_broadcast.subscribe(tenant_id, ws)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(
                    queue.get(), timeout=_WS_HEARTBEAT_INTERVAL
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await ws.send_json({"type": "ping", "ts": int(time.time())})
                except Exception:
                    break
                continue
            if ws.client_state == WebSocketState.DISCONNECTED:
                break
            await ws.send_text(msg)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        _logger.debug("WS audit stream error: %s", exc)
    finally:
        audit_broadcast.unsubscribe(tenant_id, ws)


# ---------------------------------------------------------------------------
# JWT token support for short-lived WebSocket auth
# ---------------------------------------------------------------------------

_WS_JWT_SECRET = os.getenv("ALETHEIA_WS_JWT_SECRET", "").encode("utf-8")


def create_ws_token(tenant_id: str, ttl_seconds: int = 300) -> str:
    """Create a short-lived HMAC-SHA256 signed token for WebSocket auth.

    Format: base64(json({"tenant_id": ..., "exp": ...})).hex_signature
    Uses a simple HMAC scheme — no external JWT library required.
    """
    import base64

    payload = json.dumps(
        {
            "tenant_id": tenant_id,
            "exp": int(time.time()) + ttl_seconds,
            "nonce": secrets.token_hex(8),
        }
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii")
    sig = hmac.new(
        _WS_JWT_SECRET or b"dev-only", encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{sig}"


def _verify_ws_jwt(token: str) -> str | None:
    """Verify a short-lived JWT token. Returns tenant_id or None."""
    if not _WS_JWT_SECRET:
        return None  # JWT auth disabled when no secret is set
    import base64

    try:
        encoded, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(
            _WS_JWT_SECRET, encoded.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if payload.get("exp", 0) < time.time():
            return None  # Expired
        return str(payload.get("tenant_id", "default"))
    except Exception:
        return None


def _authenticate_ws_token(token: str) -> str | None:
    """Validate the WS token and return the tenant_id, or None."""
    # Admin key → all tenants
    admin_key = os.getenv("ALETHEIA_ADMIN_KEY", "").strip()
    if admin_key and secrets.compare_digest(token, admin_key):
        return "__all__"

    # Short-lived JWT (if ALETHEIA_WS_JWT_SECRET is configured)
    jwt_result = _verify_ws_jwt(token)
    if jwt_result is not None:
        return jwt_result

    # API key lookup via key_store
    try:
        from core.key_store import key_store

        record = key_store.lookup_by_hash(token)
        if record is not None:
            return record.tenant_id or "default"
    except Exception:
        pass

    return None
