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


if __name__ == "__main__":
    unittest.main()
