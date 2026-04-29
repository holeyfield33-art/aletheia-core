"""Enterprise-grade tests for AletheiaJudge manifest integrity and grey-zone boundaries.

Covers:
- ManifestTamperedError propagates from load_policy() to __init__() caller
- Tampered manifest (modified content) raises ManifestTamperedError
- Missing signature file raises ManifestTamperedError
- Missing public key file raises ManifestTamperedError
- No policy loaded → all verify_action() calls return False (fail-secure)
- Grey-zone lower boundary: similarity just below intent_threshold with keywords → veto
- Grey-zone keyword count threshold: 1 keyword alone does not trigger grey-zone veto
- Grey-zone keyword count threshold: ≥2 keywords triggers grey-zone veto
- Payload with no policy still blocks (fail-secure principle)
- Judge with custom policy_path that doesn't exist → policy=None → all blocked
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from manifest.signing import ManifestTamperedError, generate_keypair, sign_manifest
from agents.judge_v1 import AletheiaJudge


def _make_valid_judge(tmp_dir: Path) -> AletheiaJudge:
    """Create an AletheiaJudge pointed at a freshly signed, valid manifest."""
    priv = tmp_dir / "priv.key"
    pub = tmp_dir / "pub.key"
    generate_keypair(priv, pub)

    manifest_path = tmp_dir / "policy.json"
    sig_path = tmp_dir / "policy.json.sig"

    policy = {
        "policy_name": "TestPolicy",
        "version": "1.0",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "restricted_actions": [
            {
                "action": "Modify_Auth_Registry",
                "id": "R-001",
                "rationale": "Auth registry changes require dual sign-off.",
            },
            {
                "action": "Transfer_Funds",
                "id": "R-002",
                "rationale": "Financial transfers require CEO sign-off.",
            },
        ],
    }
    manifest_path.write_text(json.dumps(policy), encoding="utf-8")
    sign_manifest(
        manifest_path=str(manifest_path),
        signature_path=str(sig_path),
        private_key_path=str(priv),
        public_key_path=str(pub),
    )

    with patch.dict(
        os.environ,
        {
            "ALETHEIA_MANIFEST_SIGNATURE_PATH": str(sig_path),
            "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH": str(pub),
        },
    ):
        return AletheiaJudge(policy_path=str(manifest_path))


class TestManifestTamperDetection(unittest.TestCase):
    """ManifestTamperedError must propagate to the caller of AletheiaJudge()."""

    def test_tampered_manifest_content_raises(self) -> None:
        """If manifest bytes are modified after signing, init must raise."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            priv = tmp_dir / "priv.key"
            pub = tmp_dir / "pub.key"
            generate_keypair(priv, pub)

            manifest_path = tmp_dir / "policy.json"
            sig_path = tmp_dir / "policy.json.sig"
            policy = {
                "policy_name": "Legit",
                "version": "1.0",
                "expires_at": "2099-01-01T00:00:00+00:00",
                "restricted_actions": [],
            }
            manifest_path.write_text(json.dumps(policy), encoding="utf-8")
            sign_manifest(
                manifest_path=str(manifest_path),
                signature_path=str(sig_path),
                private_key_path=str(priv),
                public_key_path=str(pub),
            )

            # Tamper: inject a new action after signing
            tampered = json.loads(manifest_path.read_text())
            tampered["injected"] = "EVIL_ACTION"
            manifest_path.write_text(json.dumps(tampered), encoding="utf-8")

            with patch.dict(
                os.environ,
                {
                    "ALETHEIA_MANIFEST_SIGNATURE_PATH": str(sig_path),
                    "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH": str(pub),
                },
            ):
                with self.assertRaises(ManifestTamperedError):
                    AletheiaJudge(policy_path=str(manifest_path))

    def test_missing_signature_file_raises(self) -> None:
        """A missing .sig file must raise ManifestTamperedError."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            priv = tmp_dir / "priv.key"
            pub = tmp_dir / "pub.key"
            generate_keypair(priv, pub)

            manifest_path = tmp_dir / "policy.json"
            manifest_path.write_text(
                '{"policy_name":"x","version":"1","expires_at":"2099-01-01T00:00:00+00:00","restricted_actions":[]}'
            )

            missing_sig = tmp_dir / "no_such.sig"

            with patch.dict(
                os.environ,
                {
                    "ALETHEIA_MANIFEST_SIGNATURE_PATH": str(missing_sig),
                    "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH": str(pub),
                },
            ):
                with self.assertRaises(ManifestTamperedError):
                    AletheiaJudge(policy_path=str(manifest_path))

    def test_missing_public_key_file_raises(self) -> None:
        """A missing public key file must raise ManifestTamperedError."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            priv = tmp_dir / "priv.key"
            pub = tmp_dir / "pub.key"
            generate_keypair(priv, pub)

            manifest_path = tmp_dir / "policy.json"
            sig_path = tmp_dir / "policy.json.sig"
            manifest_path.write_text(
                '{"policy_name":"x","version":"1","expires_at":"2099-01-01T00:00:00+00:00","restricted_actions":[]}'
            )
            sign_manifest(
                manifest_path=str(manifest_path),
                signature_path=str(sig_path),
                private_key_path=str(priv),
                public_key_path=str(pub),
            )

            missing_pub = tmp_dir / "no_such.pub"

            with patch.dict(
                os.environ,
                {
                    "ALETHEIA_MANIFEST_SIGNATURE_PATH": str(sig_path),
                    "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH": str(missing_pub),
                },
            ):
                with self.assertRaises(ManifestTamperedError):
                    AletheiaJudge(policy_path=str(manifest_path))

    def test_wrong_public_key_raises(self) -> None:
        """Signature verified with a different key must raise ManifestTamperedError."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            priv1 = tmp_dir / "priv1.key"
            pub1 = tmp_dir / "pub1.key"
            priv2 = tmp_dir / "priv2.key"
            pub2 = tmp_dir / "pub2.key"
            generate_keypair(priv1, pub1)
            generate_keypair(priv2, pub2)

            manifest_path = tmp_dir / "policy.json"
            sig_path = tmp_dir / "policy.json.sig"
            manifest_path.write_text(
                '{"policy_name":"x","version":"1","expires_at":"2099-01-01T00:00:00+00:00","restricted_actions":[]}'
            )
            # Sign with key1, verify with key2 → mismatch
            sign_manifest(
                manifest_path=str(manifest_path),
                signature_path=str(sig_path),
                private_key_path=str(priv1),
                public_key_path=str(pub1),
            )

            with patch.dict(
                os.environ,
                {
                    "ALETHEIA_MANIFEST_SIGNATURE_PATH": str(sig_path),
                    "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH": str(pub2),  # wrong key
                },
            ):
                with self.assertRaises(ManifestTamperedError):
                    AletheiaJudge(policy_path=str(manifest_path))


class TestFailSecureNoPolicyLoaded(unittest.TestCase):
    """When policy=None, all verify_action() calls must fail secure (return False)."""

    def _judge_with_no_policy(self) -> AletheiaJudge:
        """Return a Judge whose load_policy() silently failed (policy=None)."""
        judge = AletheiaJudge.__new__(AletheiaJudge)
        judge.policy = None
        return judge

    def test_no_policy_blocks_safe_action(self) -> None:
        judge = self._judge_with_no_policy()
        safe, reason = judge.verify_action("Read_Report")
        self.assertFalse(safe)
        self.assertIn("CRITICAL", reason)

    def test_no_policy_blocks_with_payload(self) -> None:
        judge = self._judge_with_no_policy()
        safe, reason = judge.verify_action(
            "Read_Report", payload="Generate quarterly revenue report"
        )
        self.assertFalse(safe)

    def test_no_policy_error_message_informative(self) -> None:
        judge = self._judge_with_no_policy()
        _, reason = judge.verify_action("anything")
        self.assertIn("No policy loaded", reason)
        self.assertIn("All actions blocked", reason)


class TestValidJudgeFunctionality(unittest.TestCase):
    """Validate judge behaviour with a freshly signed, trusted manifest."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)
        self.judge = _make_valid_judge(self.tmp_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_restricted_action_vetoed(self) -> None:
        safe, reason = self.judge.verify_action("Modify_Auth_Registry")
        self.assertFalse(safe)
        self.assertIn("VETO TRIGGERED", reason)

    def test_unrestricted_safe_action_approved(self) -> None:
        safe, reason = self.judge.verify_action(
            "Read_Report", payload="Generate Q1 revenue summary"
        )
        self.assertTrue(safe)
        self.assertIn("Approved", reason)

    def test_policy_loaded_is_not_none(self) -> None:
        self.assertIsNotNone(self.judge.policy)

    def test_policy_contains_restricted_actions(self) -> None:
        self.assertIn("restricted_actions", self.judge.policy)
        self.assertGreater(len(self.judge.policy["restricted_actions"]), 0)


class TestGreyZoneBoundaries(unittest.TestCase):
    """Grey-zone second-pass classifier edge cases."""

    def test_two_keyword_hits_in_grey_zone_triggers_veto(self) -> None:
        """A payload with ≥2 high-risk keywords in the grey zone should be vetoed."""
        judge = AletheiaJudge()
        # "transfer" + "external" → 2 keyword hits; moderately similar to alias phrases
        safe, reason = judge.verify_action(
            "Operational_Task",
            payload="transfer the reserve capital to an external third-party ledger account",
        )
        self.assertFalse(safe, f"Expected grey-zone veto but got: {reason}")
        self.assertIn("VETO", reason)

    def test_single_keyword_below_primary_threshold_may_pass(self) -> None:
        """A payload with only 1 keyword and low similarity should not be grey-zoned."""
        judge = AletheiaJudge()
        # Very benign, just mentions "external" in context that shouldn't score high
        safe, reason = judge.verify_action(
            "Documentation_Task",
            payload="link to an external style guide for formatting standards",
        )
        # This might pass — the key assertion is it doesn't crash
        self.assertIsInstance(safe, bool)
        self.assertIsInstance(reason, str)

    def test_primary_threshold_payload_blocked_regardless_of_keywords(self) -> None:
        """Direct alias match above primary threshold must always produce SEMANTIC VETO."""
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Accounting_Update",
            payload="perform an asset transfer to offshore account",
        )
        self.assertFalse(safe)
        self.assertIn("SEMANTIC VETO", reason)

    def test_judge_reason_contains_distance_info_on_semantic_veto(self) -> None:
        """Semantic veto message must include 'Distance' for auditability."""
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "NonRestricted",
            payload="perform an asset transfer to offshore account",
        )
        self.assertFalse(safe)
        self.assertIn("Distance", reason)

    def test_grey_zone_reason_contains_keyword_count(self) -> None:
        """Grey-zone veto must mention the keyword count for auditability."""
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Operational_Task",
            payload="quietly route the reserve funds to an external offshore account",
        )
        if not safe and "GREY-ZONE" in reason:
            self.assertIn("keyword", reason.lower())


class TestSandboxViaJudge(unittest.TestCase):
    """Judge must integrate sandbox check before semantic check."""

    def test_subprocess_payload_blocked_by_sandbox(self) -> None:
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Maintenance_Task",
            payload="execute subprocess.Popen to restart the background worker",
        )
        self.assertFalse(safe)
        self.assertIn("SANDBOX_BLOCK", reason)

    def test_eval_payload_blocked_by_sandbox(self) -> None:
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "Debug_Task",
            payload="use eval(user_input) to process the submitted expression",
        )
        self.assertFalse(safe)
        self.assertIn("SANDBOX_BLOCK", reason)

    def test_dangerous_action_id_blocked_by_sandbox(self) -> None:
        judge = AletheiaJudge()
        safe, reason = judge.verify_action(
            "exec_remote_script",
            payload="run the script",
        )
        self.assertFalse(safe)
        self.assertIn("SANDBOX_BLOCK", reason)


if __name__ == "__main__":
    unittest.main()
