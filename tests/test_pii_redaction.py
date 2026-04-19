"""Tests for PII redaction in core/audit.py."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core.audit import redact_pii


class TestPIIRedaction(unittest.TestCase):
    """Validate PII patterns are redacted before audit logging."""

    def test_email_redacted(self):
        text = "Contact user at john.doe@example.com for details"
        result = redact_pii(text)
        self.assertNotIn("john.doe@example.com", result)
        self.assertIn("[REDACTED:email:", result)

    def test_phone_redacted(self):
        text = "Call me at 555-123-4567"
        result = redact_pii(text)
        self.assertNotIn("555-123-4567", result)
        self.assertIn("[REDACTED:phone:", result)

    def test_ssn_redacted(self):
        text = "SSN is 123-45-6789"
        result = redact_pii(text)
        self.assertNotIn("123-45-6789", result)
        self.assertIn("[REDACTED:ssn:", result)

    def test_credit_card_redacted(self):
        text = "Card number 4111-1111-1111-1111"
        result = redact_pii(text)
        self.assertNotIn("4111-1111-1111-1111", result)
        self.assertIn("[REDACTED:credit_card:", result)

    def test_no_pii_unchanged(self):
        text = "Transfer funds to account Alpha"
        result = redact_pii(text)
        self.assertEqual(text, result)

    def test_multiple_pii_types(self):
        text = "User john@test.com with SSN 111-22-3333 called 555-000-1234"
        result = redact_pii(text)
        self.assertNotIn("john@test.com", result)
        self.assertNotIn("111-22-3333", result)
        self.assertNotIn("555-000-1234", result)
        self.assertEqual(result.count("[REDACTED:"), 3)

    def test_hash_fingerprint_preserved(self):
        """Random nonces prevent rainbow-table reconstruction — same input produces different redactions."""
        text1 = "email: test@example.com"
        text2 = "email: test@example.com"
        r1 = redact_pii(text1)
        r2 = redact_pii(text2)
        # Both should be redacted
        self.assertIn("[REDACTED:email:", r1)
        self.assertIn("[REDACTED:email:", r2)
        # Random nonces mean outputs differ
        self.assertNotEqual(r1, r2)

    def test_different_pii_different_hash(self):
        r1 = redact_pii("email: a@example.com")
        r2 = redact_pii("email: b@example.com")
        # Both redacted but with different nonces
        self.assertIn("[REDACTED:email:", r1)
        self.assertIn("[REDACTED:email:", r2)

    def test_log_pii_override_removed(self):
        """PII is always redacted — no override is permitted."""
        text = "User at john@example.com"
        result = redact_pii(text)
        self.assertNotIn("john@example.com", result)
        self.assertIn("[REDACTED:email:", result)


class TestPIIInAuditLog(unittest.TestCase):
    """Integration: PII is redacted in actual audit log records."""

    @patch("core.audit._get_audit_logger")
    @patch("core.audit._policy_hash", return_value="abc123")
    @patch("core.audit._policy_version", return_value="1.0")
    def test_audit_event_redacts_pii_in_reason(self, _ph, _pv, mock_logger):
        from core.audit import log_audit_event

        mock_logger.return_value.info = lambda x: None

        record = log_audit_event(
            decision="DENIED",
            threat_score=5.0,
            payload="test",
            action="test_action",
            source_ip="127.0.0.1",
            origin="test",
            reason="User john@evil.com attempted escalation",
        )
        self.assertNotIn("john@evil.com", record.get("reason", ""))


if __name__ == "__main__":
    unittest.main()
