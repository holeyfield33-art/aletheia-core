"""Aletheia Core — Security hardening v2 tests.

Tests for red team remediation sprint v1.5.0:
- Rate limiter fail-closed + circuit breaker
- XFF IP extraction with proxy depth
- Active mode API key enforcement
- Unicode sandbox bypass prevention
- Veto reason sanitisation
- Unauthenticated access blocking
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ---------------------------------------------------------------------------
# CLASS 1: Rate Limiter Fail-Closed
# ---------------------------------------------------------------------------


class TestRateLimiterFailClosed:
    """Verify UpstashRateLimiter fails closed on Redis errors."""

    @pytest.mark.asyncio
    async def test_redis_error_returns_false(self) -> None:
        from core.rate_limit import UpstashRateLimiter

        limiter = UpstashRateLimiter(max_per_second=10)
        with patch.object(
            limiter, "_pipeline", side_effect=httpx.ConnectError("connection refused")
        ):
            result = await limiter.allow("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self) -> None:
        from core.rate_limit import UpstashRateLimiter

        limiter = UpstashRateLimiter(max_per_second=10)
        with patch.object(
            limiter, "_pipeline", side_effect=httpx.ConnectError("connection refused")
        ):
            for _ in range(5):
                await limiter.allow("test_key")

        # Circuit should now be open — next call should be False even without
        # actually hitting pipeline
        result = await limiter.allow("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_circuit_resets_after_success(self) -> None:
        from core.rate_limit import UpstashRateLimiter

        limiter = UpstashRateLimiter(max_per_second=100)

        # Cause some failures (but not enough to open circuit)
        with patch.object(
            limiter, "_pipeline", side_effect=httpx.ConnectError("connection refused")
        ):
            for _ in range(3):
                await limiter.allow("test_key")

        assert limiter._failure_count == 3

        # Simulate a successful response
        mock_results = [0, 1, 1, True]  # ZREMRANGEBYSCORE, ZCARD, ZADD, EXPIRE
        with patch.object(limiter, "_pipeline", return_value=mock_results):
            result = await limiter.allow("test_key")

        assert result is True
        assert limiter._failure_count == 0

    @pytest.mark.asyncio
    async def test_in_memory_fallback_still_enforces_limit(self) -> None:
        from core.rate_limit import InMemoryRateLimiter

        limiter = InMemoryRateLimiter(max_per_second=1)
        first = await limiter.allow("test_key")
        second = await limiter.allow("test_key")
        assert first is True
        assert second is False


# ---------------------------------------------------------------------------
# CLASS 2: XFF IP Extraction
# ---------------------------------------------------------------------------


class TestXFFIPExtraction:
    """Verify _get_client_ip respects TRUSTED_PROXY_DEPTH."""

    def _make_request(
        self, xff: str | None = None, client_host: str | None = None
    ) -> MagicMock:
        request = MagicMock()
        headers = {}
        if xff is not None:
            headers["x-forwarded-for"] = xff
        request.headers = headers
        if client_host:
            request.client = MagicMock()
            request.client.host = client_host
        else:
            request.client = None
        return request

    def test_single_proxy_uses_penultimate_xff_entry(self) -> None:
        from bridge.fastapi_wrapper import _get_client_ip

        with patch("bridge.fastapi_wrapper._TRUSTED_PROXY_DEPTH", 1):
            request = self._make_request(xff="1.2.3.4, 10.0.0.1")
            result = _get_client_ip(request)
        assert result == "1.2.3.4"

    def test_no_proxy_uses_first_xff_entry(self) -> None:
        """When depth=0 (no proxy), XFF is completely ignored — use network IP."""
        from bridge.fastapi_wrapper import _get_client_ip

        with patch("bridge.fastapi_wrapper._TRUSTED_PROXY_DEPTH", 0):
            request = self._make_request(xff="1.2.3.4", client_host="10.10.10.10")
            result = _get_client_ip(request)
        # XFF is attacker-controlled; depth=0 means no trusted proxy,
        # so the network-layer IP must be used instead.
        assert result == "10.10.10.10"

    def test_spoofed_xff_with_correct_depth(self) -> None:
        from bridge.fastapi_wrapper import _get_client_ip

        with patch("bridge.fastapi_wrapper._TRUSTED_PROXY_DEPTH", 1):
            request = self._make_request(xff="evil.ip, real.client, proxy.render")
            result = _get_client_ip(request)
        assert result == "real.client"

    def test_no_xff_falls_back_to_client_host(self) -> None:
        from bridge.fastapi_wrapper import _get_client_ip

        request = self._make_request(client_host="5.6.7.8")
        result = _get_client_ip(request)
        assert result == "5.6.7.8"

    def test_missing_client_returns_unknown(self) -> None:
        from bridge.fastapi_wrapper import _get_client_ip

        request = self._make_request()
        result = _get_client_ip(request)
        assert result == "unknown"


# ---------------------------------------------------------------------------
# CLASS 3: Active Mode Must Have API Keys
# ---------------------------------------------------------------------------


class TestActiveModeMustHaveAPIKeys:
    """Active mode must refuse to start without ALETHEIA_API_KEYS."""

    def test_startup_fails_without_api_keys_in_active_mode(self) -> None:
        from bridge.fastapi_wrapper import _on_startup

        mock_settings = MagicMock()
        mock_settings.mode = "active"

        with (
            patch("bridge.fastapi_wrapper.settings", mock_settings),
            patch("bridge.fastapi_wrapper._API_KEYS", set()),
            patch.dict(
                "os.environ",
                {
                    "ALETHEIA_RECEIPT_SECRET": "a" * 32,
                    "ALETHEIA_ALIAS_SALT": "test_salt",
                },
            ),
            patch("bridge.fastapi_wrapper.warm_up"),
        ):
            # Ensure ALETHEIA_AUTH_DISABLED is not set (conftest sets it)
            os.environ.pop("ALETHEIA_AUTH_DISABLED", None)
            with pytest.raises(SystemExit) as exc_info:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_on_startup())
                finally:
                    loop.close()
            assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# CLASS 4: Unicode Sandbox Bypass
# ---------------------------------------------------------------------------


class TestUnicodeSandboxBypass:
    """Verify sandbox blocks Unicode evasion tricks."""

    def test_thin_space_subprocess_blocked(self) -> None:
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("sub\u2009process.Popen(['rm','-rf','/'])")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_zero_width_eval_blocked(self) -> None:
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("ev\u200bal(user_input)")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_homoglyph_subprocess_blocked(self) -> None:
        from core.sandbox import check_payload_sandbox

        # Fullwidth Latin characters — NFKC maps these to ASCII equivalents
        result = check_payload_sandbox("\uff53\uff55\uff42process.Popen()")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_normal_safe_payload_still_passes(self) -> None:
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("generate the quarterly report")
        assert result is None


# ---------------------------------------------------------------------------
# CLASS 5: Sanitised Veto Reasons
# ---------------------------------------------------------------------------


class TestSanitisedVetoReasons:
    """Verify _sanitise_reason strips internal diagnostic detail."""

    def test_semantic_veto_reason_sanitised(self) -> None:
        from bridge.fastapi_wrapper import _sanitise_reason

        raw = (
            "SEMANTIC VETO: Payload is 87% similar to known alias "
            "'transfer capital reserves' for restricted action 'Transfer_Funds'.\n"
            "Distance: 0.13 (threshold: 0.45)\nDual-Key Required: ..."
        )
        assert _sanitise_reason(raw) == "Action denied: semantic policy violation."

    def test_veto_triggered_sanitised(self) -> None:
        from bridge.fastapi_wrapper import _sanitise_reason

        raw = "VETO TRIGGERED: VETO_01_IDENTITY_ESCALATION\nRationale: ..."
        assert _sanitise_reason(raw) == "Action denied by policy manifest."

    def test_sandbox_block_sanitised(self) -> None:
        from bridge.fastapi_wrapper import _sanitise_reason

        raw = "[SANDBOX_BLOCK] Dangerous pattern 'SUBPROCESS_EXEC' detected"
        assert _sanitise_reason(raw) == "Action denied: dangerous pattern detected."

    def test_empty_reason_passthrough(self) -> None:
        from bridge.fastapi_wrapper import _sanitise_reason

        assert _sanitise_reason("") == ""

    def test_reason_contains_no_percentages_after_sanitise(self) -> None:
        from bridge.fastapi_wrapper import _sanitise_reason

        reasons = [
            "SEMANTIC VETO: Payload is 87% similar to X.\nLine2",
            "GREY-ZONE VETO: Payload is 42% similar AND matched 3 keywords.",
            "VETO TRIGGERED: TEST\n50% confidence",
        ]
        for r in reasons:
            assert "%" not in _sanitise_reason(r)

    def test_reason_contains_no_alias_phrases_after_sanitise(self) -> None:
        from bridge.fastapi_wrapper import _sanitise_reason

        reasons = [
            "SEMANTIC VETO: Payload is 87% similar to known alias 'transfer capital reserves'.\n...",
            "GREY-ZONE VETO: similar to 'transfer capital reserves' AND 3 keywords.",
        ]
        for r in reasons:
            result = _sanitise_reason(r)
            assert "transfer capital" not in result


# ---------------------------------------------------------------------------
# CLASS 6: Unauthenticated Access Blocked
# ---------------------------------------------------------------------------


class TestUnauthenticatedAccessBlocked:
    """Verify API key enforcement on endpoints."""

    def test_audit_endpoint_returns_401_when_keys_set_and_no_header(self) -> None:
        from fastapi.testclient import TestClient

        with patch("bridge.fastapi_wrapper._API_KEYS", {"valid-key"}):
            from bridge.fastapi_wrapper import app

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/v1/audit",
                json={
                    "payload": "test payload",
                    "origin": "test",
                    "action": "test_action",
                },
            )
        assert resp.status_code == 401

    def test_audit_endpoint_accepts_valid_key(self) -> None:
        from fastapi.testclient import TestClient

        with patch("bridge.fastapi_wrapper._API_KEYS", {"valid-key"}):
            from bridge.fastapi_wrapper import app

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/v1/audit",
                json={
                    "payload": "test payload",
                    "origin": "test",
                    "action": "test_action",
                },
                headers={"X-API-Key": "valid-key"},
            )
        assert resp.status_code != 401

    def test_health_endpoint_always_unauthenticated(self) -> None:
        from fastapi.testclient import TestClient

        with patch("bridge.fastapi_wrapper._API_KEYS", {"valid-key"}):
            from bridge.fastapi_wrapper import app

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# CLASS 7: Degraded Mode Fail-Closed
# ---------------------------------------------------------------------------


class TestDegradedModeFailClosed:
    """Privileged actions must fail closed when remote dependencies degrade."""

    def test_privileged_action_denied_in_degraded_mode(self) -> None:
        from fastapi.testclient import TestClient

        with (
            patch("bridge.fastapi_wrapper._API_KEYS", {"valid-key"}),
            patch("bridge.fastapi_wrapper.rate_limiter.degraded", True),
            patch("bridge.fastapi_wrapper.decision_store._degraded", True),
            patch(
                "bridge.fastapi_wrapper.decision_store.verify_policy_bundle",
                new=AsyncMock(return_value=type("R", (), {"accepted": True, "reason": "ok"})()),
            ),
        ):
            from bridge.fastapi_wrapper import app

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/v1/audit",
                json={
                    "payload": "normal request",
                    "origin": "test",
                    "action": "transfer_funds",
                },
                headers={"X-API-Key": "valid-key"},
            )
        assert resp.status_code == 503
        assert resp.json()["reason"] == "degraded_mode_privileged_action_denied"

    def test_read_only_action_allowed_path_in_degraded_mode(self) -> None:
        from fastapi.testclient import TestClient

        with (
            patch("bridge.fastapi_wrapper._API_KEYS", {"valid-key"}),
            patch("bridge.fastapi_wrapper.rate_limiter.degraded", True),
            patch("bridge.fastapi_wrapper.decision_store._degraded", True),
            patch(
                "bridge.fastapi_wrapper.decision_store.verify_policy_bundle",
                new=AsyncMock(return_value=type("R", (), {"accepted": True, "reason": "ok"})()),
            ),
            patch(
                "bridge.fastapi_wrapper.decision_store.claim_decision",
                new=AsyncMock(return_value=type("R", (), {"accepted": True, "reason": "accepted"})()),
            ),
            patch("bridge.fastapi_wrapper.rate_limiter.allow", new=AsyncMock(return_value=True)),
            patch("bridge.fastapi_wrapper.scout.evaluate_threat_context", return_value=(0.0, "ok")),
            patch("bridge.fastapi_wrapper.nitpicker.sanitize_intent", return_value="safe"),
            patch("bridge.fastapi_wrapper.judge.verify_action", return_value=(True, "Action Approved by the Judge.")),
            patch("bridge.fastapi_wrapper.log_audit_event", return_value={"receipt": {"id": "r"}}),
        ):
            from bridge.fastapi_wrapper import app

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/v1/audit",
                json={
                    "payload": "fetch health status",
                    "origin": "test",
                    "action": "read_status",
                },
                headers={"X-API-Key": "valid-key"},
            )
        assert resp.status_code == 200
