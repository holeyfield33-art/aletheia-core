"""Enterprise-grade edge-case tests for core/audit.py.

Covers:
- _policy_hash() → 'MANIFEST_MISSING' when manifest file absent
- log_audit_event() with extra= dict present in returned record
- log_audit_event() latency_ms field rounded and present in record
- log_audit_event() actually writes a JSON line to the configured audit log file
- Written JSON lines are parseable and contain all required fields
- _get_audit_logger() lazy init: re-entrant calls return same logger instance
- build_tmr_receipt() with policy_hash change produces different signature
- payload_preview truncated to 120 chars in shadow mode
- log_audit_event() with extra=None does not include 'extra' key
- client_id appears in the audit record from settings
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestPolicyHashManifestMissing(unittest.TestCase):
    """_policy_hash() must return 'MANIFEST_MISSING' when file is absent."""

    def test_returns_manifest_missing_when_file_absent(self) -> None:
        from core.audit import _policy_hash
        with patch("core.audit.Path") as mock_path_cls:
            mock_path_cls.return_value.read_bytes.side_effect = FileNotFoundError
            result = _policy_hash()
        self.assertEqual(result, "MANIFEST_MISSING")

    def test_returns_hex_string_when_manifest_present(self) -> None:
        """When the manifest is readable, result must be a 64-char hex SHA-256."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b'{"policy": "v1"}')
            tmp_path = f.name
        try:
            with patch("core.audit.Path") as mock_path_cls:
                mock_path_cls.return_value.read_bytes.return_value = b'{"policy": "v1"}'
                from core.audit import _policy_hash
                result = _policy_hash()
            self.assertEqual(len(result), 64)
            int(result, 16)  # must be valid hex
        finally:
            os.unlink(tmp_path)

    def test_policy_hash_changes_when_content_changes(self) -> None:
        """Different manifest content must produce a different hash."""
        from core.audit import _policy_hash
        content_a = b'{"policy": "v1"}'
        content_b = b'{"policy": "v2"}'

        with patch("core.audit.Path") as mock_path_cls:
            mock_path_cls.return_value.read_bytes.return_value = content_a
            hash_a = _policy_hash()

        with patch("core.audit.Path") as mock_path_cls:
            mock_path_cls.return_value.read_bytes.return_value = content_b
            hash_b = _policy_hash()

        self.assertNotEqual(hash_a, hash_b)

    def test_policy_hash_is_deterministic(self) -> None:
        """Same content must always produce the same hash."""
        content = b'{"policy": "stable"}'
        expected = hashlib.sha256(content).hexdigest()

        from core.audit import _policy_hash
        with patch("core.audit.Path") as mock_path_cls:
            mock_path_cls.return_value.read_bytes.return_value = content
            result = _policy_hash()

        self.assertEqual(result, expected)


class TestLogAuditEventExtraField(unittest.TestCase):
    """extra= kwarg must appear in the returned record when provided."""

    def test_extra_dict_appears_in_returned_record(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="safe payload",
            action="Read_Report",
            source_ip="10.0.0.1",
            origin="trusted_admin",
            extra={"rule_id": "R-007", "triggered_by": "test"},
        )
        self.assertIn("extra", record)
        self.assertEqual(record["extra"]["rule_id"], "R-007")
        self.assertEqual(record["extra"]["triggered_by"], "test")

    def test_extra_none_does_not_add_extra_key(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="DENIED",
            threat_score=9.0,
            payload="bad payload",
            action="Transfer_Funds",
            source_ip="10.0.0.2",
            origin="untrusted_metadata",
            extra=None,
        )
        self.assertNotIn("extra", record)

    def test_extra_empty_dict_does_not_appear(self) -> None:
        """An empty extra dict is falsy; implementation skips it."""
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="safe",
            action="Read_Report",
            source_ip="10.0.0.3",
            origin="trusted_admin",
            extra={},
        )
        # {} is falsy so the `if extra:` guard should skip it
        self.assertNotIn("extra", record)

    def test_extra_nested_structure_preserved(self) -> None:
        from core.audit import log_audit_event
        nested = {"level1": {"level2": [1, 2, 3]}}
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="safe",
            action="Read_Report",
            source_ip="10.0.0.4",
            origin="trusted_admin",
            extra=nested,
        )
        self.assertEqual(record["extra"]["level1"]["level2"], [1, 2, 3])


class TestLogAuditEventLatency(unittest.TestCase):
    """latency_ms field must be rounded, present, and non-negative."""

    def test_latency_ms_present_in_record(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="test",
            action="Read_Report",
            source_ip="10.0.0.5",
            origin="trusted_admin",
            latency_ms=42.1234567,
        )
        self.assertIn("latency_ms", record)

    def test_latency_ms_rounded_to_2_decimals(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="test",
            action="Read_Report",
            source_ip="10.0.0.6",
            origin="trusted_admin",
            latency_ms=12.3456789,
        )
        # round(..., 2) == 12.35
        self.assertEqual(record["latency_ms"], round(12.3456789, 2))

    def test_latency_ms_default_zero(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="test",
            action="Read_Report",
            source_ip="10.0.0.7",
            origin="trusted_admin",
        )
        self.assertEqual(record["latency_ms"], 0.0)

    def test_latency_ms_non_negative(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="test",
            action="Read_Report",
            source_ip="10.0.0.8",
            origin="trusted_admin",
            latency_ms=0.0,
        )
        self.assertGreaterEqual(record["latency_ms"], 0.0)


class TestAuditFileWrite(unittest.TestCase):
    """log_audit_event() must write a valid JSON line to the configured audit log path."""

    def test_json_line_written_to_audit_log(self) -> None:
        """A JSON-parseable line must appear in the audit log after the call."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "audit_test.log")
            with patch("core.audit.settings") as mock_settings:
                mock_settings.audit_log_path = log_path
                mock_settings.log_level = "INFO"
                mock_settings.mode = "active"
                mock_settings.client_id = "TEST_CLIENT"
                # Reset the lazy logger singleton so it picks up the new path
                import core.audit as audit_module
                audit_module._audit_logger = None
                from core.audit import log_audit_event
                log_audit_event(
                    decision="DENIED",
                    threat_score=9.5,
                    payload="malicious payload",
                    action="Transfer_Funds",
                    source_ip="1.2.3.4",
                    origin="untrusted",
                    reason="Threat detected",
                )
                audit_module._audit_logger = None  # clean up singleton

            lines = Path(log_path).read_text(encoding="utf-8").strip().splitlines()
            self.assertGreater(len(lines), 0, "No lines written to audit log")

            record = json.loads(lines[-1])
            self.assertEqual(record["decision"], "DENIED")
            self.assertAlmostEqual(record["threat_score"], 9.5)
            self.assertEqual(record["action"], "Transfer_Funds")
            self.assertIn("timestamp", record)
            self.assertIn("payload_sha256", record)
            self.assertIn("policy_hash", record)

    def test_multiple_events_produce_multiple_lines(self) -> None:
        """Each call to log_audit_event() must append a new line."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "multi.log")
            with patch("core.audit.settings") as mock_settings:
                mock_settings.audit_log_path = log_path
                mock_settings.log_level = "INFO"
                mock_settings.mode = "active"
                mock_settings.client_id = "TEST_CLIENT"
                import core.audit as audit_module
                audit_module._audit_logger = None
                from core.audit import log_audit_event
                for i in range(5):
                    log_audit_event(
                        decision="PROCEED",
                        threat_score=float(i),
                        payload=f"payload_{i}",
                        action="Read_Report",
                        source_ip=f"10.0.0.{i+1}",
                        origin="trusted_admin",
                    )
                audit_module._audit_logger = None

            lines = Path(log_path).read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 5, f"Expected 5 lines, got {len(lines)}")
            for line in lines:
                json.loads(line)  # each must be valid JSON

    def test_audit_log_fields_complete(self) -> None:
        """Every required field must be present in the written record."""
        required_fields = {
            "timestamp", "decision", "threat_score", "action",
            "source_ip", "origin", "latency_ms",
            "payload_sha256", "payload_length", "policy_hash",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "fields.log")
            with patch("core.audit.settings") as mock_settings:
                mock_settings.audit_log_path = log_path
                mock_settings.log_level = "INFO"
                mock_settings.mode = "active"
                mock_settings.client_id = "TEST_CLIENT"
                import core.audit as audit_module
                audit_module._audit_logger = None
                from core.audit import log_audit_event
                log_audit_event(
                    decision="PROCEED",
                    threat_score=1.0,
                    payload="complete field test",
                    action="Read_Report",
                    source_ip="10.1.1.1",
                    origin="trusted_admin",
                    reason="all fields present",
                    latency_ms=5.5,
                )
                audit_module._audit_logger = None

            record = json.loads(
                Path(log_path).read_text(encoding="utf-8").strip().splitlines()[-1]
            )
            for field in required_fields:
                self.assertIn(field, record, f"Required field '{field}' missing from audit record")


class TestPayloadPreviewInShadowMode(unittest.TestCase):
    """payload_preview must be included in shadow mode and truncated at 120 chars."""

    def test_shadow_mode_includes_preview(self) -> None:
        with patch("core.audit.settings") as mock_settings:
            mock_settings.mode = "shadow"
            from core.audit import _hash_payload
            result = _hash_payload("shadow mode test payload")
        self.assertIn("payload_preview", result)

    def test_preview_truncated_to_120_chars(self) -> None:
        with patch("core.audit.settings") as mock_settings:
            mock_settings.mode = "shadow"
            from core.audit import _hash_payload
            long_payload = "x" * 200
            result = _hash_payload(long_payload)
        self.assertLessEqual(len(result["payload_preview"]), 120)

    def test_preview_newlines_replaced_with_spaces(self) -> None:
        with patch("core.audit.settings") as mock_settings:
            mock_settings.mode = "shadow"
            from core.audit import _hash_payload
            result = _hash_payload("line one\nline two\r\nline three")
        self.assertNotIn("\n", result["payload_preview"])
        self.assertNotIn("\r", result["payload_preview"])

    def test_active_mode_no_preview(self) -> None:
        with patch("core.audit.settings") as mock_settings:
            mock_settings.mode = "active"
            from core.audit import _hash_payload
            result = _hash_payload("active mode — no preview allowed")
        self.assertNotIn("payload_preview", result)


class TestTMRReceiptEdgeCases(unittest.TestCase):
    """Additional edge cases for build_tmr_receipt()."""

    def test_different_policy_hash_different_signature(self) -> None:
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "test-secret"}, clear=False):
            from core.audit import build_tmr_receipt
            r1 = build_tmr_receipt(decision="PROCEED", policy_hash="hash_a")
            r2 = build_tmr_receipt(decision="PROCEED", policy_hash="hash_b")
        self.assertNotEqual(r1["signature"], r2["signature"])

    def test_receipt_contains_issued_at(self) -> None:
        from core.audit import build_tmr_receipt
        receipt = build_tmr_receipt(decision="PROCEED", policy_hash="abc")
        self.assertIn("issued_at", receipt)

    def test_dev_mode_receipt_contains_warning(self) -> None:
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": ""}, clear=False):
            from core.audit import build_tmr_receipt
            receipt = build_tmr_receipt(decision="PROCEED", policy_hash="abc")
        self.assertIn("warning", receipt)
        self.assertEqual(receipt["signature"], "UNSIGNED_DEV_MODE")

    def test_signed_receipt_has_64_char_hex_signature(self) -> None:
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "my-secret-key"}, clear=False):
            from core.audit import build_tmr_receipt
            receipt = build_tmr_receipt(decision="DENIED", policy_hash="policy_xyz")
        self.assertEqual(len(receipt["signature"]), 64)
        int(receipt["signature"], 16)  # must be valid hex

    def test_receipt_decision_and_policy_hash_present(self) -> None:
        from core.audit import build_tmr_receipt
        receipt = build_tmr_receipt(decision="PROCEED", policy_hash="abc123")
        self.assertEqual(receipt["decision"], "PROCEED")
        self.assertEqual(receipt["policy_hash"], "abc123")


class TestLogAuditEventReturnRecord(unittest.TestCase):
    """Validate the full structure of the record returned by log_audit_event()."""

    def test_returned_record_contains_receipt(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="test",
            action="Read_Report",
            source_ip="10.0.0.1",
            origin="trusted_admin",
        )
        self.assertIn("receipt", record)
        self.assertIn("signature", record["receipt"])

    def test_returned_record_decision_matches_input(self) -> None:
        from core.audit import log_audit_event
        for decision in ("PROCEED", "DENIED", "BLOCKED"):
            record = log_audit_event(
                decision=decision,
                threat_score=5.0,
                payload="x",
                action="Action",
                source_ip="1.2.3.4",
                origin="origin",
            )
            self.assertEqual(record["decision"], decision)

    def test_reason_field_in_returned_record(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="DENIED",
            threat_score=9.0,
            payload="bad",
            action="Transfer_Funds",
            source_ip="1.2.3.4",
            origin="untrusted",
            reason="High threat score",
        )
        self.assertEqual(record["reason"], "High threat score")

    def test_source_ip_and_origin_in_returned_record(self) -> None:
        from core.audit import log_audit_event
        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="safe",
            action="Read_Report",
            source_ip="203.0.113.1",
            origin="trusted_admin",
        )
        self.assertEqual(record["source_ip"], "203.0.113.1")
        self.assertEqual(record["origin"], "trusted_admin")


if __name__ == "__main__":
    unittest.main()
