# SPDX-License-Identifier: MIT
"""Extended tests for core/ws_audit.py.

Achieves ~69% → ~95% coverage of the WebSocket audit stream module, covering:
- AuditBroadcast: subscribe, unsubscribe, publish (tenant-scoped + admin __all__),
  back-pressure (full queue → stale removal)
- create_ws_token() + _verify_ws_jwt(): create/verify round-trip, expiry, tamper
- _authenticate_ws_token(): admin key path, JWT path, key_store path, fallback None
- ws_audit_handler(): missing token (4001), invalid token (4003), connection limit (4029)
- _redact_record(): PII scrubbing and sensitive field stripping
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AuditBroadcast
# ---------------------------------------------------------------------------

class TestAuditBroadcast:
    def setup_method(self) -> None:
        # Import fresh to avoid shared global state
        from core.ws_audit import AuditBroadcast
        self.broadcast = AuditBroadcast()

    def _make_ws(self) -> MagicMock:
        return MagicMock()

    def test_subscribe_returns_queue(self) -> None:
        ws = self._make_ws()
        q = self.broadcast.subscribe("tenant-1", ws)
        assert isinstance(q, asyncio.Queue)

    def test_tenant_count_zero_before_subscribe(self) -> None:
        assert self.broadcast.tenant_count("unknown") == 0

    def test_tenant_count_increments_on_subscribe(self) -> None:
        ws = self._make_ws()
        self.broadcast.subscribe("t1", ws)
        assert self.broadcast.tenant_count("t1") == 1

    def test_multiple_subscribers_same_tenant(self) -> None:
        for _ in range(3):
            self.broadcast.subscribe("t1", self._make_ws())
        assert self.broadcast.tenant_count("t1") == 3

    def test_unsubscribe_decrements_count(self) -> None:
        ws = self._make_ws()
        self.broadcast.subscribe("t1", ws)
        self.broadcast.unsubscribe("t1", ws)
        assert self.broadcast.tenant_count("t1") == 0

    def test_unsubscribe_nonexistent_tenant_no_error(self) -> None:
        # Should not raise
        self.broadcast.unsubscribe("ghost-tenant", self._make_ws())

    def test_unsubscribe_unknown_ws_no_error(self) -> None:
        ws1 = self._make_ws()
        ws2 = self._make_ws()
        self.broadcast.subscribe("t1", ws1)
        # Unsubscribe ws2 which was never subscribed
        self.broadcast.unsubscribe("t1", ws2)
        assert self.broadcast.tenant_count("t1") == 1

    def test_empty_tenant_key_removed_after_last_unsubscribe(self) -> None:
        ws = self._make_ws()
        self.broadcast.subscribe("t1", ws)
        self.broadcast.unsubscribe("t1", ws)
        # Internal dict should not retain empty sets
        assert "t1" not in self.broadcast._subs

    def test_publish_delivers_to_matching_tenant(self) -> None:
        ws = self._make_ws()
        q = self.broadcast.subscribe("tenant-x", ws)
        record = {"tenant_id": "tenant-x", "action": "allow", "user": "bob@test.com"}
        self.broadcast.publish(record)
        assert not q.empty()
        msg = q.get_nowait()
        data = json.loads(msg)
        assert data["action"] == "allow"

    def test_publish_does_not_deliver_to_other_tenant(self) -> None:
        ws1 = self._make_ws()
        ws2 = self._make_ws()
        q1 = self.broadcast.subscribe("tenant-a", ws1)
        q2 = self.broadcast.subscribe("tenant-b", ws2)
        self.broadcast.publish({"tenant_id": "tenant-a", "action": "allow"})
        assert not q1.empty()
        assert q2.empty()

    def test_publish_to_all_admin_subscription(self) -> None:
        """A subscriber under '__all__' tenant receives every record."""
        ws_admin = self._make_ws()
        q_admin = self.broadcast.subscribe("__all__", ws_admin)

        self.broadcast.publish({"tenant_id": "tenant-1", "action": "allow"})
        self.broadcast.publish({"tenant_id": "tenant-2", "action": "deny"})

        assert q_admin.qsize() == 2

    def test_publish_with_default_tenant_when_missing(self) -> None:
        ws = self._make_ws()
        q = self.broadcast.subscribe("default", ws)
        # Record without tenant_id → falls back to "default"
        self.broadcast.publish({"action": "allow"})
        assert not q.empty()

    def test_publish_removes_stale_full_queue_subscriber(self) -> None:
        ws = self._make_ws()
        # Create queue with maxsize=1
        q = asyncio.Queue(maxsize=1)
        self.broadcast._subs.setdefault("t1", set()).add((ws, q))
        # Fill the queue
        q.put_nowait("first message")
        # Publish another — queue is full, subscriber should be removed
        self.broadcast.publish({"tenant_id": "t1", "action": "test"})
        # Stale subscriber should have been discarded
        subs = self.broadcast._subs.get("t1", set())
        assert (ws, q) not in subs

    def test_pii_redacted_in_published_message(self) -> None:
        ws = self._make_ws()
        q = self.broadcast.subscribe("t1", ws)
        record = {
            "tenant_id": "t1",
            "user": "alice@example.com",
            "action": "allow",
        }
        self.broadcast.publish(record)
        msg = q.get_nowait()
        data = json.loads(msg)
        # PII (email) should be redacted in the published message
        assert "@" not in data.get("user", "")

    def test_sensitive_fields_stripped_from_published_message(self) -> None:
        ws = self._make_ws()
        q = self.broadcast.subscribe("t1", ws)
        record = {
            "tenant_id": "t1",
            "action": "allow",
            "payload_sha256": "abc123",
            "payload_preview": "secret preview",
            "receipt": "signed-receipt-data",
        }
        self.broadcast.publish(record)
        msg = q.get_nowait()
        data = json.loads(msg)
        assert "payload_sha256" not in data
        assert "payload_preview" not in data
        assert "receipt" not in data


# ---------------------------------------------------------------------------
# _redact_record helper
# ---------------------------------------------------------------------------

class TestRedactRecord:
    def test_strips_sensitive_fields(self) -> None:
        from core.ws_audit import _redact_record
        record = {
            "action": "allow",
            "payload_sha256": "hash",
            "payload_preview": "preview",
            "payload_length": 100,
            "receipt": "signed",
            "user": "alice",
        }
        out = _redact_record(record)
        for field in ("payload_sha256", "payload_preview", "payload_length", "receipt"):
            assert field not in out
        assert "action" in out
        assert "user" in out

    def test_pii_redacted_in_string_values(self) -> None:
        from core.ws_audit import _redact_record
        record = {"note": "Email: alice@example.com, SSN: 123-45-6789"}
        out = _redact_record(record)
        # The PII should be redacted
        assert "alice@example.com" not in out.get("note", "")

    def test_non_string_values_preserved(self) -> None:
        from core.ws_audit import _redact_record
        record = {"count": 42, "flag": True, "items": [1, 2, 3]}
        out = _redact_record(record)
        assert out["count"] == 42
        assert out["flag"] is True


# ---------------------------------------------------------------------------
# create_ws_token + _verify_ws_jwt
# ---------------------------------------------------------------------------

class TestWSJWT:
    def setup_method(self) -> None:
        # Ensure a known JWT secret is set for these tests
        os.environ["ALETHEIA_WS_JWT_SECRET"] = "test-ws-secret-key-for-pytest-only"
        # Reload the module to pick up the env var
        import importlib
        import core.ws_audit
        importlib.reload(core.ws_audit)
        from core.ws_audit import create_ws_token, _verify_ws_jwt
        self.create_ws_token = create_ws_token
        self._verify_ws_jwt = _verify_ws_jwt

    def teardown_method(self) -> None:
        os.environ.pop("ALETHEIA_WS_JWT_SECRET", None)

    def test_create_and_verify_round_trip(self) -> None:
        token = self.create_ws_token("my-tenant", ttl_seconds=300)
        tenant_id = self._verify_ws_jwt(token)
        assert tenant_id == "my-tenant"

    def test_expired_token_returns_none(self) -> None:
        # Create a token that's already expired
        token = self.create_ws_token("tenant-x", ttl_seconds=-1)
        result = self._verify_ws_jwt(token)
        assert result is None

    def test_tampered_signature_returns_none(self) -> None:
        token = self.create_ws_token("tenant-x")
        # Corrupt the signature portion
        parts = token.rsplit(".", 1)
        tampered = parts[0] + ".deadbeefdeadbeef"
        result = self._verify_ws_jwt(tampered)
        assert result is None

    def test_malformed_token_returns_none(self) -> None:
        result = self._verify_ws_jwt("not.a.valid.token.at.all")
        assert result is None

    def test_empty_token_returns_none(self) -> None:
        result = self._verify_ws_jwt("")
        assert result is None

    def test_token_format_has_two_parts(self) -> None:
        token = self.create_ws_token("t1")
        parts = token.rsplit(".", 1)
        assert len(parts) == 2

    def test_token_contains_nonce_for_uniqueness(self) -> None:
        t1 = self.create_ws_token("same-tenant")
        t2 = self.create_ws_token("same-tenant")
        assert t1 != t2  # nonce makes each token unique

    def test_verify_returns_none_when_no_secret_set(self) -> None:
        os.environ.pop("ALETHEIA_WS_JWT_SECRET", None)
        import importlib
        import core.ws_audit
        importlib.reload(core.ws_audit)
        result = core.ws_audit._verify_ws_jwt("any.token")
        assert result is None


# ---------------------------------------------------------------------------
# _authenticate_ws_token
# ---------------------------------------------------------------------------

class TestAuthenticateWSToken:
    def setup_method(self) -> None:
        os.environ["ALETHEIA_WS_JWT_SECRET"] = "test-ws-secret-key-for-pytest-only"
        import importlib
        import core.ws_audit
        importlib.reload(core.ws_audit)
        self.mod = core.ws_audit

    def teardown_method(self) -> None:
        os.environ.pop("ALETHEIA_WS_JWT_SECRET", None)
        os.environ.pop("ALETHEIA_ADMIN_KEY", None)

    def test_admin_key_returns_all_tenant(self) -> None:
        os.environ["ALETHEIA_ADMIN_KEY"] = "super-secret-admin-key"
        import importlib
        import core.ws_audit
        importlib.reload(core.ws_audit)
        result = core.ws_audit._authenticate_ws_token("super-secret-admin-key")
        assert result == "__all__"

    def test_wrong_admin_key_does_not_grant_all(self) -> None:
        os.environ["ALETHEIA_ADMIN_KEY"] = "correct-key"
        import importlib
        import core.ws_audit
        importlib.reload(core.ws_audit)
        result = core.ws_audit._authenticate_ws_token("wrong-key")
        # Should not return "__all__" for wrong key
        assert result != "__all__"

    def test_valid_jwt_returns_tenant_id(self) -> None:
        token = self.mod.create_ws_token("jwt-tenant", ttl_seconds=300)
        result = self.mod._authenticate_ws_token(token)
        assert result == "jwt-tenant"

    def test_expired_jwt_falls_through_to_none(self) -> None:
        token = self.mod.create_ws_token("tenant", ttl_seconds=-1)
        mock_ks = MagicMock()
        mock_ks.lookup_by_hash = MagicMock(return_value=None)
        with patch("core.key_store.key_store", mock_ks):
            result = self.mod._authenticate_ws_token(token)
        assert result is None

    def test_key_store_lookup_returns_tenant(self) -> None:
        mock_record = MagicMock()
        mock_record.tenant_id = "ks-tenant"
        mock_ks = MagicMock()
        mock_ks.lookup_by_hash = MagicMock(return_value=mock_record)

        with patch("core.key_store.key_store", mock_ks):
            result = self.mod._authenticate_ws_token("api-key-token")

        assert result == "ks-tenant"

    def test_key_store_none_tenant_defaults_to_default(self) -> None:
        mock_record = MagicMock()
        mock_record.tenant_id = None
        mock_ks = MagicMock()
        mock_ks.lookup_by_hash = MagicMock(return_value=mock_record)

        with patch("core.key_store.key_store", mock_ks):
            result = self.mod._authenticate_ws_token("api-key-token")

        assert result == "default"

    def test_unknown_token_returns_none(self) -> None:
        mock_ks = MagicMock()
        mock_ks.lookup_by_hash = MagicMock(return_value=None)
        with patch("core.key_store.key_store", mock_ks):
            result = self.mod._authenticate_ws_token("completely-unknown-token")
        assert result is None

    def test_key_store_exception_returns_none(self) -> None:
        mock_ks = MagicMock()
        mock_ks.lookup_by_hash = MagicMock(side_effect=RuntimeError("db down"))
        with patch("core.key_store.key_store", mock_ks):
            result = self.mod._authenticate_ws_token("some-token")
        assert result is None


# ---------------------------------------------------------------------------
# ws_audit_handler — missing/invalid token and connection limit
# ---------------------------------------------------------------------------

class TestWSAuditHandler:
    def _make_ws(
        self,
        token: str = "",
        client_state: str = "CONNECTED",
    ) -> MagicMock:
        """Create a mock WebSocket with configurable token query param."""
        from starlette.websockets import WebSocketState
        ws = MagicMock()
        ws.query_params = {"token": token}
        ws.close = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        ws.client_state = (
            WebSocketState.CONNECTED if client_state == "CONNECTED"
            else WebSocketState.DISCONNECTED
        )
        return ws

    @pytest.mark.asyncio
    async def test_missing_token_closes_4001(self) -> None:
        from core.ws_audit import ws_audit_handler
        ws = self._make_ws(token="")
        await ws_audit_handler(ws)
        ws.close.assert_called_once_with(code=4001, reason="Missing token parameter")
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_token_closes_4003(self) -> None:
        from core.ws_audit import ws_audit_handler
        ws = self._make_ws(token="bad-token-xyz")

        with patch("core.ws_audit._authenticate_ws_token", return_value=None):
            await ws_audit_handler(ws)

        ws.close.assert_called_once_with(code=4003, reason="Invalid or expired token")
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_limit_closes_4029(self) -> None:
        from core.ws_audit import ws_audit_handler, audit_broadcast

        ws = self._make_ws(token="valid-token")

        with patch("core.ws_audit._authenticate_ws_token", return_value="tenant-x"):
            with patch.object(
                audit_broadcast,
                "tenant_count",
                return_value=10,  # at max
            ):
                # _WS_MAX_PER_TENANT defaults to 10 from env
                with patch("core.ws_audit._WS_MAX_PER_TENANT", 10):
                    await ws_audit_handler(ws)

        ws.close.assert_called_once_with(
            code=4029, reason="Too many connections for this tenant"
        )

    @pytest.mark.asyncio
    async def test_admin_token_skips_connection_limit(self) -> None:
        """Admin ('__all__') connections bypass the per-tenant limit."""
        from core.ws_audit import ws_audit_handler, audit_broadcast
        from starlette.websockets import WebSocketDisconnect

        ws = self._make_ws(token="admin-token")
        # Simulate immediate disconnect after accept
        ws.accept = AsyncMock()

        async def _disconnect() -> None:
            raise WebSocketDisconnect()

        with patch("core.ws_audit._authenticate_ws_token", return_value="__all__"):
            with patch.object(audit_broadcast, "tenant_count", return_value=999):
                with patch.object(audit_broadcast, "subscribe", return_value=asyncio.Queue()):
                    with patch.object(audit_broadcast, "unsubscribe"):
                        # Handler should accept and then disconnect gracefully
                        with patch(
                            "asyncio.wait_for", side_effect=WebSocketDisconnect
                        ):
                            await ws_audit_handler(ws)

        # Should have called accept (not rejected early)
        ws.accept.assert_called_once()
        # Should not have been rejected with 4029
        for call in ws.close.call_args_list:
            assert call.kwargs.get("code") != 4029

    @pytest.mark.asyncio
    async def test_valid_token_accepts_connection(self) -> None:
        """A valid token results in ws.accept() being called."""
        from core.ws_audit import ws_audit_handler, audit_broadcast
        from starlette.websockets import WebSocketDisconnect

        ws = self._make_ws(token="valid-api-key")

        with patch("core.ws_audit._authenticate_ws_token", return_value="tenant-y"):
            with patch.object(audit_broadcast, "tenant_count", return_value=0):
                with patch.object(audit_broadcast, "subscribe", return_value=asyncio.Queue()):
                    with patch.object(audit_broadcast, "unsubscribe"):
                        with patch(
                            "asyncio.wait_for", side_effect=WebSocketDisconnect
                        ):
                            await ws_audit_handler(ws)

        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_called_on_disconnect(self) -> None:
        """broadcast.unsubscribe() must be called in the finally block."""
        from core.ws_audit import ws_audit_handler, audit_broadcast
        from starlette.websockets import WebSocketDisconnect

        ws = self._make_ws(token="valid-token")
        unsubscribe_mock = MagicMock()

        with patch("core.ws_audit._authenticate_ws_token", return_value="tenant-z"):
            with patch.object(audit_broadcast, "tenant_count", return_value=0):
                with patch.object(audit_broadcast, "subscribe", return_value=asyncio.Queue()):
                    with patch.object(audit_broadcast, "unsubscribe", unsubscribe_mock):
                        with patch(
                            "asyncio.wait_for", side_effect=WebSocketDisconnect
                        ):
                            await ws_audit_handler(ws)

        unsubscribe_mock.assert_called_once()
