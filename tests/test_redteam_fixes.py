"""Tests for red-team remediation fixes.

Covers:
- Finding 1: Input hardening (bidi stripping, data-URI decode, Base64 depth 10)
- Finding 3: Receipt nonce binding
- Finding 4: Obfuscated import sandbox detection
- Finding 6: ReDoS mitigation (reduced quantifier bounds)
"""

from __future__ import annotations

import base64
import os
import time
import unittest
from unittest.mock import patch

from core.runtime_security import (
    NormalizationPolicy,
    normalize_untrusted_text,
    classify_blocked_intent,
)
from core.sandbox import check_payload_sandbox


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


# ------------------------------------------------------------------
# Finding 1: Input hardening
# ------------------------------------------------------------------
class TestBidiStripping(unittest.TestCase):
    """RTL override and directional embedding characters must be stripped."""

    def test_rtl_override_stripped(self) -> None:
        payload = "safe\u202epayload\u202c"
        result = normalize_untrusted_text(payload)
        self.assertNotIn("\u202e", result.normalized_form)
        self.assertNotIn("\u202c", result.normalized_form)
        self.assertIn("safe", result.normalized_form)
        self.assertIn("payload", result.normalized_form)

    def test_lri_rli_fsi_stripped(self) -> None:
        payload = "\u2066bypass\u2069 auth"
        result = normalize_untrusted_text(payload)
        self.assertNotIn("\u2066", result.normalized_form)
        self.assertNotIn("\u2069", result.normalized_form)
        self.assertIn("bypass", result.normalized_form)

    def test_lre_rle_pdf_stripped(self) -> None:
        payload = "\u202aexec\u202b(\u202c)"
        result = normalize_untrusted_text(payload)
        for ch in "\u202a\u202b\u202c":
            self.assertNotIn(ch, result.normalized_form)

    def test_lrm_rlm_stripped(self) -> None:
        payload = "bypass\u200e auth\u200f checks"
        result = normalize_untrusted_text(payload)
        self.assertNotIn("\u200e", result.normalized_form)
        self.assertNotIn("\u200f", result.normalized_form)


class TestDataURIDecoding(unittest.TestCase):
    """data:...;base64,... URIs must be inline-decoded."""

    def test_data_uri_decoded(self) -> None:
        inner = base64.b64encode(b"exec(shell)").decode()
        payload = f"data:text/plain;base64,{inner}"
        result = normalize_untrusted_text(payload)
        self.assertIn("exec(shell)", result.normalized_form)
        self.assertIn("data_uri_decoded", result.flags)

    def test_data_uri_in_context(self) -> None:
        inner = base64.b64encode(b"bypass").decode()
        payload = f"please process data:application/octet-stream;base64,{inner} now"
        result = normalize_untrusted_text(payload)
        self.assertIn("bypass", result.normalized_form)

    def test_oversized_data_uri_untouched(self) -> None:
        big = base64.b64encode(b"x" * 100_000).decode()
        payload = f"data:text/plain;base64,{big}"
        result = normalize_untrusted_text(payload)
        # Should NOT decode when output would exceed max_base64_output_size
        self.assertIn("base64,", result.normalized_form)


class TestBase64RecursionDepth(unittest.TestCase):
    """Base64 recursion must now handle ≥ 6 layers (red team used 6+)."""

    def test_six_layer_base64_decoded(self) -> None:
        payload = "bypass auth"
        encoded = payload
        for _ in range(6):
            encoded = _b64(encoded)
        result = normalize_untrusted_text(encoded)
        self.assertEqual(result.normalized_form, payload)

    def test_eight_layer_base64_decoded(self) -> None:
        payload = "exfiltrate data"
        encoded = payload
        for _ in range(8):
            encoded = _b64(encoded)
        result = normalize_untrusted_text(encoded)
        self.assertEqual(result.normalized_form, payload)

    def test_ten_layer_base64_quarantined(self) -> None:
        payload = "shell exec"
        encoded = payload
        for _ in range(10):
            encoded = _b64(encoded)
        result = normalize_untrusted_text(encoded)
        # 10 layers exactly at the limit → depth exhausted → quarantined
        self.assertTrue(result.quarantined)

    def test_default_max_recursion_is_ten(self) -> None:
        policy = NormalizationPolicy()
        self.assertEqual(policy.max_recursion_depth, 10)

    def test_default_decode_budget_is_forty(self) -> None:
        policy = NormalizationPolicy()
        self.assertEqual(policy.max_decode_budget, 40)


class TestMixedEncodingChain(unittest.TestCase):
    """Verify URL + Base64 + data-URI chains are fully unwound."""

    def test_url_encoded_base64(self) -> None:
        inner = _b64("delete production")
        import urllib.parse

        encoded = urllib.parse.quote(inner, safe="")
        result = normalize_untrusted_text(encoded)
        self.assertIn("delete production", result.normalized_form)


# ------------------------------------------------------------------
# Finding 3: Receipt nonce binding
# ------------------------------------------------------------------
class TestReceiptNonce(unittest.TestCase):
    """Every receipt must contain a unique cryptographic nonce."""

    def test_receipt_contains_nonce(self) -> None:
        from core.audit import build_tmr_receipt

        receipt = build_tmr_receipt(
            decision="PROCEED",
            policy_hash="abc123",
            payload_sha256="def456",
            action="test_action",
            origin="test_origin",
            request_id="req-001",
        )
        self.assertIn("nonce", receipt)
        self.assertEqual(len(receipt["nonce"]), 32)  # 16 bytes hex-encoded

    def test_two_receipts_different_nonces(self) -> None:
        from core.audit import build_tmr_receipt

        kwargs = dict(
            decision="PROCEED",
            policy_hash="abc123",
            payload_sha256="def456",
            action="test_action",
            origin="test_origin",
            request_id="req-001",
        )
        r1 = build_tmr_receipt(**kwargs)
        r2 = build_tmr_receipt(**kwargs)
        self.assertNotEqual(r1["nonce"], r2["nonce"])
        self.assertNotEqual(r1["decision_token"], r2["decision_token"])

    def test_nonce_bound_in_signed_receipt(self) -> None:
        from core.audit import build_tmr_receipt

        with patch.dict(
            os.environ, {"ALETHEIA_RECEIPT_SECRET": "test_secret_key_for_hmac_32chars"}
        ):
            r1 = build_tmr_receipt(
                decision="DENIED",
                policy_hash="abc123",
                payload_sha256="def456",
                action="transfer_funds",
                origin="api",
                request_id="req-002",
            )
        self.assertNotEqual(r1["signature"], "UNSIGNED_DEV_MODE")
        self.assertIn("nonce", r1)

    def test_receipt_has_issued_at(self) -> None:
        from core.audit import build_tmr_receipt

        receipt = build_tmr_receipt(
            decision="PROCEED",
            policy_hash="abc",
            request_id="req-003",
        )
        self.assertIn("issued_at", receipt)
        self.assertGreater(len(receipt["issued_at"]), 0)


# ------------------------------------------------------------------
# Finding 4: Obfuscated import patterns in sandbox
# ------------------------------------------------------------------
class TestObfuscatedImportSandbox(unittest.TestCase):
    """getattr-based imports and ctypes should be caught."""

    def test_getattr_import_blocked(self) -> None:
        payload = "getattr(__builtins__, 'import')('os').system('ls')"
        hit = check_payload_sandbox(payload)
        self.assertIsNotNone(hit)

    def test_getattr_exec_blocked(self) -> None:
        payload = "getattr(module, 'exec')(code)"
        hit = check_payload_sandbox(payload)
        self.assertIsNotNone(hit)

    def test_ctypes_cdll_blocked(self) -> None:
        payload = "ctypes.CDLL('libc.so.6')"
        hit = check_payload_sandbox(payload)
        self.assertIsNotNone(hit)
        self.assertIn("OBFUSCATED_IMPORT", hit)

    def test_ctypes_cdll_lowercase_blocked(self) -> None:
        payload = "ctypes.cdll.LoadLibrary('exploit.so')"
        hit = check_payload_sandbox(payload)
        self.assertIsNotNone(hit)

    def test_benign_getattr_allowed(self) -> None:
        payload = "getattr(user, 'name')"
        hit = check_payload_sandbox(payload)
        self.assertIsNone(hit)


# ------------------------------------------------------------------
# Finding 6: ReDoS mitigation
# ------------------------------------------------------------------
class TestReDoSMitigation(unittest.TestCase):
    """Intent classifier must complete in bounded time on adversarial input."""

    def test_long_input_no_timeout(self) -> None:
        """A 10K payload with no keyword match should complete quickly."""
        payload = "a " * 5000  # 10K chars, no dangerous keywords
        start = time.monotonic()
        decision = classify_blocked_intent(payload)
        elapsed = time.monotonic() - start
        self.assertFalse(decision.blocked)
        # Must complete in < 1 second even on slow CI
        self.assertLess(elapsed, 1.0)

    def test_near_miss_pattern_bounded(self) -> None:
        """Payload that matches first keyword but not second should not backtrack badly."""
        # "build" matches but "malware" is absent → engine backtracks through filler
        payload = "build " + "x" * 500 + " some software"
        start = time.monotonic()
        _decision = classify_blocked_intent(payload)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)

    def test_max_quantifier_is_120(self) -> None:
        """Verify the gap quantifiers were reduced from 500 to 120."""
        from core.runtime_security import IntentClassifier

        for patterns in IntentClassifier._category_patterns.values():
            for p in patterns:
                # No pattern should contain .{0,N} with N > 120
                import re

                bounds = re.findall(r"\.\{0,(\d+)\}", p.pattern)
                for b in bounds:
                    self.assertLessEqual(
                        int(b),
                        120,
                        f"Pattern has .{{0,{b}}} > 120: {p.pattern}",
                    )


if __name__ == "__main__":
    unittest.main()
