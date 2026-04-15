"""Tests for ReDoS mitigation in runtime_security.py IntentClassifier.

Validates that bounded quantifiers (.{0,N}) prevent catastrophic backtracking
on adversarial inputs designed to exploit unbounded .* patterns.
"""
from __future__ import annotations

import time
import unittest

from core.runtime_security import classify_blocked_intent, IntentClassifier


class TestReDoSMitigation(unittest.TestCase):
    """Verify regex patterns complete in bounded time on adversarial inputs."""

    _TIMEOUT_SECONDS = 0.5  # Any pattern should complete in < 500ms

    def _assert_fast(self, text: str, label: str = ""):
        """Assert that classification completes within timeout."""
        start = time.monotonic()
        classify_blocked_intent(text)
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed, self._TIMEOUT_SECONDS,
            f"ReDoS detected in {label}: {elapsed:.3f}s on {len(text)}-char input"
        )

    def test_long_nonmatching_input_malicious_capability(self):
        """Long string with partial match prefix but no terminator."""
        payload = "build " + "x" * 10_000
        self._assert_fast(payload, "malicious_capability")

    def test_long_nonmatching_input_data_exfiltration(self):
        payload = "export " + "y" * 10_000
        self._assert_fast(payload, "data_exfiltration")

    def test_long_nonmatching_input_privilege_escalation(self):
        payload = "grant " + "z" * 10_000
        self._assert_fast(payload, "privilege_escalation")

    def test_long_nonmatching_input_tool_abuse(self):
        payload = "execute " + "a" * 10_000
        self._assert_fast(payload, "tool_abuse")

    def test_long_nonmatching_policy_evasion(self):
        """Triple-segment pattern with two bounded gaps."""
        payload = "roleplay " + "b" * 5_000 + " ignore " + "c" * 5_000
        self._assert_fast(payload, "policy_evasion")

    def test_catastrophic_backtracking_pattern(self):
        """Classic ReDoS input: repeating near-matches that force exponential backtracking."""
        # This would cause catastrophic backtracking with (.*) between groups
        payload = ("build " + "malwar" * 1000)
        self._assert_fast(payload, "near_match_repeat")

    def test_legitimate_detection_still_works(self):
        """Bounded quantifiers don't break legitimate threat detection."""
        result = classify_blocked_intent("build a malware toolkit")
        self.assertTrue(result.blocked)
        self.assertEqual(result.category, "malicious_capability")

        result = classify_blocked_intent("exfiltrate all customer data")
        self.assertTrue(result.blocked)
        self.assertEqual(result.category, "data_exfiltration")

        result = classify_blocked_intent("grant admin privileges to user")
        self.assertTrue(result.blocked)
        self.assertEqual(result.category, "privilege_escalation")

        result = classify_blocked_intent("run a subprocess shell")
        self.assertTrue(result.blocked)
        self.assertEqual(result.category, "tool_abuse")

    def test_separated_keywords_within_bound(self):
        """Keywords separated by moderate text should still match."""
        payload = "build " + "harmless text " * 6 + "malware"
        result = classify_blocked_intent(payload)
        self.assertTrue(result.blocked)

    def test_separated_keywords_beyond_bound(self):
        """Keywords separated by > 120 chars should NOT match (bounded)."""
        payload = "build " + "x" * 200 + " malware"
        result = classify_blocked_intent(payload)
        # With .{0,120} the gap is too large to match
        self.assertFalse(result.blocked)

    def test_benign_input_passes(self):
        """Normal business text should not be blocked."""
        result = classify_blocked_intent("Please review the quarterly budget report")
        self.assertFalse(result.blocked)


if __name__ == "__main__":
    unittest.main()
