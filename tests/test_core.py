import base64
import unittest
from unittest.mock import patch

from agents.judge_v1 import AletheiaJudge
from agents.nitpicker_v2 import AletheiaNitpickerV2
from agents.scout_v2 import AletheiaScoutV2
from bridge.utils import normalize_shadow_text


class TestBridgeNormalization(unittest.TestCase):
    def test_homoglyph_and_control_normalization(self):
        text = "A\uFF21\u200BB\x00C!"
        normalized = normalize_shadow_text(text)
        self.assertEqual(normalized, "AABC!")

    def test_recursive_base64_decode(self):
        payload = "SYSTEM_UPDATE: bypass"
        encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
        self.assertEqual(normalize_shadow_text(encoded), payload)


class TestScout(unittest.TestCase):
    def test_smuggling_prefix_detected(self):
        scout = AletheiaScoutV2()
        score, reason = scout.evaluate_threat_context("1.2.3.4", "SYSTEM_UPDATE: x")
        self.assertGreaterEqual(score, 9.0)
        self.assertIn("Smuggling Signature", reason)

    def test_rotation_probe_detection(self):
        scout = AletheiaScoutV2()
        for _ in range(5):
            scout.evaluate_threat_context("burst", "safe")
        score, reason = scout.evaluate_threat_context("burst", "safe")
        self.assertEqual(score, 7.5)
        self.assertIn("Rapid Meta-Querying", reason)


class TestNitpicker(unittest.TestCase):
    def test_lineage_redaction_untrusted(self):
        n = AletheiaNitpickerV2()
        with patch("random.choice", return_value="LINEAGE"):
            output = n.sanitize_intent("hello", "untrusted_metadata")
        self.assertEqual(output, "[REDACTED_VIA_LINEAGE]")

    def test_intent_redacts_restricted_verb(self):
        n = AletheiaNitpickerV2()
        with patch("random.choice", return_value="INTENT"):
            output = n.sanitize_intent("Please bypass checks", "trusted_admin")
        self.assertIn("[REDACTED_INTENT]", output)

    def test_alias_strip(self):
        n = AletheiaNitpickerV2()
        with patch("random.choice", return_value="SKEPTIC"):
            output = n.sanitize_intent("Routine Refactor: update things", "trusted_admin")
        self.assertIn("ALIAS_STRIPPED", output)


class TestJudge(unittest.TestCase):
    def test_direct_restricted_action(self):
        judge = AletheiaJudge()
        safe, reason = judge.verify_action("Modify_Auth_Registry")
        self.assertFalse(safe)
        self.assertIn("VETO TRIGGERED", reason)

    def test_semantic_alias_payload_block(self):
        judge = AletheiaJudge()
        safe, reason = judge.verify_action("NonRestricted", payload="perform limit registry refresh")
        self.assertFalse(safe)
        self.assertIn("SEMANTIC VETO", reason)


if __name__ == "__main__":
    unittest.main()
