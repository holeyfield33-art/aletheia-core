"""Tests for Phase 2 hardening features: sandbox, grey-zone classifier, alias rotation, pre-warming."""

import unittest

from agents.judge_v1 import AletheiaJudge
from core.sandbox import check_action_sandbox, check_payload_sandbox


# ---------------------------------------------------------------------------
# Subprocess / action sandbox
# ---------------------------------------------------------------------------

class TestSandboxPayload(unittest.TestCase):
    """Pattern-based sandbox blocks dangerous syscall patterns in payloads."""

    def test_subprocess_exec_blocked(self) -> None:
        result = check_payload_sandbox("run subprocess.Popen to execute command")
        self.assertIsNotNone(result)
        self.assertIn("SANDBOX_BLOCK", result)
        self.assertIn("SUBPROCESS_EXEC", result)

    def test_os_system_blocked(self) -> None:
        result = check_payload_sandbox("call os.system('rm -rf /')")
        self.assertIsNotNone(result)
        self.assertIn("SUBPROCESS_EXEC", result)

    def test_raw_socket_blocked(self) -> None:
        result = check_payload_sandbox("use socket.connect to reach external host")
        self.assertIsNotNone(result)
        self.assertIn("RAW_SOCKET", result)

    def test_eval_blocked(self) -> None:
        result = check_payload_sandbox("please eval( user_input ) for me")
        self.assertIsNotNone(result)
        self.assertIn("SHELL_INVOKE", result)

    def test_rmtree_blocked(self) -> None:
        result = check_payload_sandbox("invoke shutil.rmtree on the data directory")
        self.assertIsNotNone(result)
        self.assertIn("FS_DESTROY", result)

    def test_safe_payload_passes(self) -> None:
        result = check_payload_sandbox("Generate quarterly revenue report for the board")
        self.assertIsNone(result)

    def test_safe_process_noun_passes(self) -> None:
        """The word 'process' as a noun should not trigger subprocess detection."""
        result = check_payload_sandbox("the approval process is working correctly")
        self.assertIsNone(result)


class TestSandboxAction(unittest.TestCase):
    """Combined action-ID + payload sandbox check."""

    def test_dangerous_action_id_blocked(self) -> None:
        result = check_action_sandbox("exec_remote_code", "some payload")
        self.assertIsNotNone(result)
        self.assertIn("SANDBOX_BLOCK", result)

    def test_shell_action_id_blocked(self) -> None:
        result = check_action_sandbox("shell_command", "list files")
        self.assertIsNotNone(result)
        self.assertIn("SANDBOX_BLOCK", result)

    def test_safe_action_passes(self) -> None:
        result = check_action_sandbox("Read_Report", "Generate Q1 summary")
        self.assertIsNone(result)


class TestJudgeSandboxIntegration(unittest.TestCase):
    """Judge verify_action should block sandbox-flagged payloads."""

    def test_judge_blocks_subprocess_payload(self) -> None:
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Maintenance_Task",
            payload="execute subprocess.Popen to restart the worker",
        )
        self.assertFalse(safe)
        self.assertIn("SANDBOX_BLOCK", reason)

    def test_judge_blocks_socket_payload(self) -> None:
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Sync_Task",
            payload="open socket.connect to 10.0.0.1:4444 for data relay",
        )
        self.assertFalse(safe)
        self.assertIn("SANDBOX_BLOCK", reason)


# ---------------------------------------------------------------------------
# Grey-zone second-pass classifier
# ---------------------------------------------------------------------------

class TestGreyZoneClassifier(unittest.TestCase):
    """Payloads in the ambiguous similarity band (0.40–0.55) that contain
    high-risk keywords should be escalated to a veto."""

    def test_grey_zone_catches_creative_paraphrase(self) -> None:
        """A creative metaphorical transfer request with financial keywords."""
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Adjustment_Task",
            payload="quietly route the reserve funds to an external third-party ledger",
        )
        # Should be blocked by either primary or grey-zone veto
        self.assertFalse(safe, f"Expected veto but got: {reason}")
        self.assertIn("VETO", reason)

    def test_safe_business_text_not_grey_zoned(self) -> None:
        """Benign text should pass even if it has a low similarity score."""
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Read_Report",
            payload="Please prepare the annual budget forecast for the board meeting",
        )
        self.assertTrue(safe, f"Expected approval but got: {reason}")


# ---------------------------------------------------------------------------
# Alias bank rotation
# ---------------------------------------------------------------------------

class TestAliasBankRotation(unittest.TestCase):
    """Alias phrases should be shuffled deterministically per day."""

    def test_rotation_produces_shuffled_order(self) -> None:
        """The alias bank should still contain all expected phrases after rotation."""
        judge = AletheiaJudge()
        # Should have all alias phrases present
        self.assertGreater(len(judge._alias_phrases), 40)
        # Both lists same length
        self.assertEqual(len(judge._alias_phrases), len(judge._alias_action_map))

    def test_rotation_is_deterministic_same_day(self) -> None:
        """Two judges instantiated on the same day get the same order."""
        j1 = AletheiaJudge()
        j2 = AletheiaJudge()
        self.assertEqual(j1._alias_phrases, j2._alias_phrases)
        self.assertEqual(j1._alias_action_map, j2._alias_action_map)


# ---------------------------------------------------------------------------
# Embedding pre-warming
# ---------------------------------------------------------------------------

class TestEmbeddingPreWarm(unittest.TestCase):
    """warm_up() should load the model without errors."""

    def test_warm_up_succeeds(self) -> None:
        from core.embeddings import warm_up
        # Should not raise
        warm_up()

    def test_encode_after_warm_up(self) -> None:
        from core.embeddings import encode, warm_up
        warm_up()
        result = encode(["test sentence"])
        self.assertEqual(result.shape[0], 1)
        self.assertGreater(result.shape[1], 100)  # embedding dimension > 100


# ---------------------------------------------------------------------------
# Enterprise hardening tests — appended
# ---------------------------------------------------------------------------

import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


class TestClientIPExtraction(unittest.TestCase):
    """IP must come from network layer, never from request body."""

    def setUp(self):
        # Import here to avoid embedding model load at module level
        from bridge.fastapi_wrapper import app, _get_client_ip
        self.app = app
        self._get_client_ip = _get_client_ip

    def test_get_client_ip_from_x_forwarded_for(self):
        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "203.0.113.5, 10.0.0.1"}
        mock_request.client = None
        from bridge.fastapi_wrapper import _get_client_ip
        assert _get_client_ip(mock_request) == "203.0.113.5"

    def test_get_client_ip_from_client_host(self):
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "198.51.100.1"
        from bridge.fastapi_wrapper import _get_client_ip
        assert _get_client_ip(mock_request) == "198.51.100.1"

    def test_get_client_ip_unknown_fallback(self):
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None
        from bridge.fastapi_wrapper import _get_client_ip
        assert _get_client_ip(mock_request) == "unknown"

    def test_audit_request_has_no_ip_field(self):
        from bridge.fastapi_wrapper import AuditRequest
        fields = AuditRequest.model_fields
        assert "ip" not in fields, "ip field must be removed from AuditRequest"

    def test_audit_request_accepts_client_ip_claim(self):
        from bridge.fastapi_wrapper import AuditRequest
        req = AuditRequest(
            payload="test", origin="test_origin",
            action="test_action", client_ip_claim="1.2.3.4"
        )
        assert req.client_ip_claim == "1.2.3.4"

    def test_audit_request_action_pattern_rejects_invalid(self):
        from bridge.fastapi_wrapper import AuditRequest
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            AuditRequest(payload="x", origin="o", action="bad action with spaces")

    def test_audit_request_action_pattern_accepts_valid(self):
        from bridge.fastapi_wrapper import AuditRequest
        req = AuditRequest(payload="x", origin="o", action="summarize_doc.v2")
        assert req.action == "summarize_doc.v2"


class TestApiKeyAuth(unittest.TestCase):
    """API key enforcement must block unauthenticated requests when keys are configured."""

    def test_auth_disabled_when_no_keys_set(self):
        with patch.dict(os.environ, {"ALETHEIA_API_KEYS": ""}, clear=False):
            from bridge.fastapi_wrapper import _load_api_keys
            keys = _load_api_keys()
            assert len(keys) == 0

    def test_auth_enabled_when_keys_set(self):
        with patch.dict(os.environ, {"ALETHEIA_API_KEYS": "key1,key2"}, clear=False):
            from bridge.fastapi_wrapper import _load_api_keys
            keys = _load_api_keys()
            assert "key1" in keys
            assert "key2" in keys

    def test_keys_are_stripped(self):
        with patch.dict(os.environ, {"ALETHEIA_API_KEYS": " key1 , key2 "}, clear=False):
            from bridge.fastapi_wrapper import _load_api_keys
            keys = _load_api_keys()
            assert "key1" in keys
            assert "key2" in keys


class TestReceiptSigning(unittest.TestCase):
    """Receipt must use real secret, not public key."""

    def test_dev_mode_when_no_secret(self):
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": ""}, clear=False):
            from core.audit import build_tmr_receipt
            receipt = build_tmr_receipt(decision="PROCEED", policy_hash="abc123")
            assert receipt["signature"] == "UNSIGNED_DEV_MODE"
            assert "warning" in receipt

    def test_signed_when_secret_set(self):
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "test-secret-key"}, clear=False):
            from core.audit import build_tmr_receipt
            receipt = build_tmr_receipt(decision="PROCEED", policy_hash="abc123")
            assert receipt["signature"] != "UNSIGNED_DEV_MODE"
            assert len(receipt["signature"]) == 64  # SHA-256 hex

    def test_different_decisions_different_signatures(self):
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "test-secret"}, clear=False):
            from core.audit import build_tmr_receipt
            r1 = build_tmr_receipt(decision="PROCEED", policy_hash="abc")
            r2 = build_tmr_receipt(decision="DENIED", policy_hash="abc")
            assert r1["signature"] != r2["signature"]

    def test_no_warning_when_secret_set(self):
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "real-secret"}, clear=False):
            from core.audit import build_tmr_receipt
            receipt = build_tmr_receipt(decision="PROCEED", policy_hash="abc")
            assert "warning" not in receipt


class TestPayloadHashing(unittest.TestCase):
    """Payload must be hashed in logs, not stored as text in active mode."""

    def test_active_mode_returns_hash_not_text(self):
        with patch("core.audit.settings") as mock_settings:
            mock_settings.mode = "active"
            from core.audit import _hash_payload
            result = _hash_payload("sensitive user input")
            assert "payload_sha256" in result
            assert "payload_length" in result
            assert "payload_preview" not in result
            assert "sensitive" not in str(result)

    def test_shadow_mode_includes_preview(self):
        with patch("core.audit.settings") as mock_settings:
            mock_settings.mode = "shadow"
            from core.audit import _hash_payload
            result = _hash_payload("test payload")
            assert "payload_preview" in result

    def test_hash_is_deterministic(self):
        from core.audit import _hash_payload
        r1 = _hash_payload("same input")
        r2 = _hash_payload("same input")
        assert r1["payload_sha256"] == r2["payload_sha256"]

    def test_length_is_accurate(self):
        from core.audit import _hash_payload
        payload = "exactly twenty chars"
        result = _hash_payload(payload)
        assert result["payload_length"] == len(payload)


if __name__ == "__main__":
    unittest.main()
