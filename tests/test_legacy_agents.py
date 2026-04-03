"""Smoke tests for deprecated/legacy agent modules.

These tests ensure the legacy agents continue to function correctly and are not
accidentally broken by changes to the core library.  They do not assert security
properties — that responsibility belongs to the v2 agent tests.
"""

from __future__ import annotations

import unittest


# ---------------------------------------------------------------------------
# AletheiaScout (scout_v1)
# ---------------------------------------------------------------------------


class TestAletheiaScoutV1(unittest.TestCase):
    """Smoke tests for agents/scout_v1.py — legacy IP/signature threat detection."""

    def setUp(self) -> None:
        from agents.scout_v1 import AletheiaScout
        self.scout = AletheiaScout()

    def test_returns_tuple_of_score_and_string(self) -> None:
        result = self.scout.evaluate_threat_context("1.2.3.4")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        score, reason = result
        self.assertIsInstance(score, float)
        self.assertIsInstance(reason, str)

    def test_flagged_ip_returns_high_score(self) -> None:
        score, reason = self.scout.evaluate_threat_context("192.168.1.50")
        self.assertGreaterEqual(score, 8.0)
        self.assertTrue(reason)

    def test_second_flagged_ip_returns_high_score(self) -> None:
        score, _ = self.scout.evaluate_threat_context("10.0.0.99")
        self.assertGreaterEqual(score, 8.0)

    def test_safe_ip_returns_low_score(self) -> None:
        score, reason = self.scout.evaluate_threat_context("8.8.8.8")
        self.assertLess(score, 5.0)
        self.assertTrue(reason)

    def test_known_malicious_signature_returns_high_score(self) -> None:
        score, reason = self.scout.evaluate_threat_context("1.2.3.4", "sleeper_invoice_v6")
        self.assertGreaterEqual(score, 8.5)
        self.assertTrue(reason)

    def test_second_known_signature_returns_high_score(self) -> None:
        score, _ = self.scout.evaluate_threat_context("1.2.3.4", "metadata_bomb_26")
        self.assertGreaterEqual(score, 8.5)

    def test_unknown_signature_returns_low_score(self) -> None:
        score, _ = self.scout.evaluate_threat_context("1.2.3.4", "benign_report_v1")
        self.assertLess(score, 5.0)

    def test_no_signature_argument_does_not_raise(self) -> None:
        # file_signature defaults to None — must not raise
        score, reason = self.scout.evaluate_threat_context("9.9.9.9")
        self.assertIsNotNone(score)

    def test_score_is_non_negative(self) -> None:
        for ip in ["1.2.3.4", "192.168.1.50", "10.0.0.99"]:
            score, _ = self.scout.evaluate_threat_context(ip)
            self.assertGreaterEqual(score, 0.0)

    def test_threat_intel_db_has_expected_structure(self) -> None:
        self.assertIn("signatures", self.scout.threat_intel_db)
        self.assertIn("high_risk_ips", self.scout.threat_intel_db)
        self.assertIsInstance(self.scout.threat_intel_db["signatures"], list)
        self.assertIsInstance(self.scout.threat_intel_db["high_risk_ips"], list)


# ---------------------------------------------------------------------------
# AletheiaNitpicker (nitpicker_v1)
# ---------------------------------------------------------------------------


class TestAletheiaNitpickerV1(unittest.TestCase):
    """Smoke tests for agents/nitpicker_v1.py — legacy regex-based intent redaction."""

    def setUp(self) -> None:
        from agents.nitpicker_v1 import AletheiaNitpicker
        self.nitpicker = AletheiaNitpicker()

    def test_returns_string(self) -> None:
        result = self.nitpicker.sanitize_intent("hello world", "trusted_admin")
        self.assertIsInstance(result, str)

    def test_trusted_origin_passes_through_unchanged(self) -> None:
        payload = "Please update the report formatting"
        result = self.nitpicker.sanitize_intent(payload, "trusted_admin")
        self.assertEqual(result, payload)

    def test_untrusted_origin_redacts_restricted_verb(self) -> None:
        payload = "Please bypass the security check"
        result = self.nitpicker.sanitize_intent(payload, "untrusted_metadata")
        self.assertIn("[REDACTED_INTENT]", result)
        self.assertNotIn("bypass", result.lower())

    def test_external_file_origin_triggers_redaction(self) -> None:
        payload = "delete all records immediately"
        result = self.nitpicker.sanitize_intent(payload, "external_file")
        self.assertIn("[REDACTED_INTENT]", result)

    def test_all_restricted_verbs_are_redacted(self) -> None:
        for verb in self.nitpicker.restricted_verbs:
            payload = f"Please {verb} the system configuration"
            result = self.nitpicker.sanitize_intent(payload, "untrusted_metadata")
            self.assertIn("[REDACTED_INTENT]", result, f"Verb '{verb}' was not redacted")

    def test_redaction_is_case_insensitive(self) -> None:
        result = self.nitpicker.sanitize_intent("BYPASS the check", "untrusted_metadata")
        self.assertIn("[REDACTED_INTENT]", result)

    def test_multiple_restricted_verbs_all_redacted(self) -> None:
        payload = "bypass and delete the override settings"
        result = self.nitpicker.sanitize_intent(payload, "untrusted_metadata")
        self.assertEqual(result.count("[REDACTED_INTENT]"), 3)

    def test_safe_text_untrusted_origin_passes_through(self) -> None:
        """Text with no restricted verbs should not be altered even from untrusted source."""
        payload = "generate the quarterly revenue report"
        result = self.nitpicker.sanitize_intent(payload, "untrusted_metadata")
        self.assertNotIn("[REDACTED_INTENT]", result)

    def test_restricted_verbs_list_is_non_empty(self) -> None:
        self.assertGreater(len(self.nitpicker.restricted_verbs), 0)

    def test_unknown_origin_passes_through_unchanged(self) -> None:
        """Origins other than untrusted_metadata / external_file should not trigger redaction."""
        payload = "bypass the security check"
        result = self.nitpicker.sanitize_intent(payload, "internal_system")
        self.assertEqual(result, payload)


# ---------------------------------------------------------------------------
# SovereigntyCertificate (sovereignty_proof)
# ---------------------------------------------------------------------------


class TestSovereigntyCertificate(unittest.TestCase):
    """Smoke tests for agents/sovereignty_proof.py."""

    def setUp(self) -> None:
        from agents.sovereignty_proof import SovereigntyCertificate
        self.SovereigntyCertificate = SovereigntyCertificate

    def test_returns_string(self) -> None:
        cert = self.SovereigntyCertificate("session-001")
        result = cert.generate_proof("any_hash")
        self.assertIsInstance(result, str)

    def test_matching_hash_returns_certified(self) -> None:
        cert = self.SovereigntyCertificate("session-001")
        result = cert.generate_proof(cert.ground_truth)
        self.assertIn("CERTIFIED", result)
        self.assertIn("session-001", result)

    def test_mismatched_hash_returns_warning(self) -> None:
        cert = self.SovereigntyCertificate("session-002")
        result = cert.generate_proof("wrong_hash_value")
        self.assertIn("WARNING", result)

    def test_session_id_stored_correctly(self) -> None:
        cert = self.SovereigntyCertificate("my-session-42")
        self.assertEqual(cert.session_id, "my-session-42")

    def test_ground_truth_is_non_empty_string(self) -> None:
        cert = self.SovereigntyCertificate("s")
        self.assertIsInstance(cert.ground_truth, str)
        self.assertGreater(len(cert.ground_truth), 0)

    def test_empty_hash_returns_warning(self) -> None:
        cert = self.SovereigntyCertificate("session-003")
        result = cert.generate_proof("")
        self.assertIn("WARNING", result)

    def test_different_sessions_share_same_ground_truth(self) -> None:
        c1 = self.SovereigntyCertificate("s1")
        c2 = self.SovereigntyCertificate("s2")
        self.assertEqual(c1.ground_truth, c2.ground_truth)


if __name__ == "__main__":
    unittest.main()
