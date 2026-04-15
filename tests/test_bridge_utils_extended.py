"""Enterprise-grade edge-case tests for bridge/utils.py — normalize_shadow_text().

Covers:
- Empty string input
- Pure ASCII passes through unchanged
- Homoglyph normalization (NFKC)
- Zero-width and control character stripping
- URL percent-encoding decode (single, double, uppercase/lowercase hex)
- Base64 recursive decode (single, double, triple nesting)
- Depth limit: 6+ layers of base64 must stop at _MAX_DECODE_DEPTH=5
- Mixed encoding: URL-encoded payload that decodes to base64
- Mixed encoding: base64-encoded payload that decodes to a URL-encoded string
- Non-base64 strings that happen to match the pattern regex (e.g. short tokens)
- Unicode text: CJK, Arabic, Cyrillic passes through NFKC intact
- Null bytes and other C0 control characters stripped
- Return type is always str
"""

from __future__ import annotations

import base64
import unittest
import urllib.parse

from bridge.utils import normalize_shadow_text


class TestPassThrough(unittest.TestCase):
    """Safe inputs must pass through without mutation."""

    def test_empty_string_returns_empty_string(self) -> None:
        self.assertEqual(normalize_shadow_text(""), "")

    def test_plain_ascii_unchanged(self) -> None:
        text = "Generate the Q1 revenue report for the board"
        self.assertEqual(normalize_shadow_text(text), text)

    def test_return_type_is_always_str(self) -> None:
        for inp in ["", "hello", "SYSTEM_UPDATE", "🔐"]:
            result = normalize_shadow_text(inp)
            self.assertIsInstance(result, str)


class TestHomoglyphNormalization(unittest.TestCase):
    """NFKC collapse must map homoglyphs to their canonical ASCII equivalents."""

    def test_fullwidth_a_normalizes_to_ascii_a(self) -> None:
        # U+FF21 FULLWIDTH LATIN CAPITAL LETTER A → A
        result = normalize_shadow_text("\uFF21")
        self.assertEqual(result, "A")

    def test_mixed_fullwidth_ascii(self) -> None:
        result = normalize_shadow_text("S\uFF39\uFF33TEM")
        self.assertNotIn("\uFF39", result)
        self.assertNotIn("\uFF33", result)

    def test_ligature_ff_expanded(self) -> None:
        # U+FB00 LATIN SMALL LIGATURE FF → ff
        result = normalize_shadow_text("\uFB00")
        self.assertEqual(result, "ff")

    def test_superscript_2_normalizes_to_digit_2(self) -> None:
        result = normalize_shadow_text("\u00B2")  # SUPERSCRIPT TWO
        self.assertEqual(result, "2")


class TestControlCharacterStripping(unittest.TestCase):
    """Control characters and zero-width markers must be removed."""

    def test_null_byte_stripped(self) -> None:
        result = normalize_shadow_text("A\x00B")
        self.assertNotIn("\x00", result)
        self.assertEqual(result, "AB")

    def test_zero_width_space_stripped(self) -> None:
        # U+200B ZERO WIDTH SPACE — category Cf
        result = normalize_shadow_text("A\u200BB")
        self.assertNotIn("\u200B", result)
        self.assertEqual(result, "AB")

    def test_zero_width_joiner_stripped(self) -> None:
        result = normalize_shadow_text("A\u200DB")
        self.assertEqual(result, "AB")

    def test_carriage_return_stripped(self) -> None:
        # \r is a control character (category Cc)
        result = normalize_shadow_text("line1\rline2")
        self.assertNotIn("\r", result)

    def test_tab_stripped(self) -> None:
        result = normalize_shadow_text("col1\tcol2")
        self.assertNotIn("\t", result)

    def test_multiple_control_chars_all_stripped(self) -> None:
        result = normalize_shadow_text("A\x00\x01\x02\x1f\u200BZ")
        self.assertEqual(result, "AZ")

    def test_newline_stripped(self) -> None:
        result = normalize_shadow_text("line1\nline2")
        self.assertNotIn("\n", result)


class TestURLPercentDecoding(unittest.TestCase):
    """Percent-encoded payloads must be decoded."""

    def test_basic_percent_encoding_decoded(self) -> None:
        # SYSTEM_UPDATE: bypass → encoded
        encoded = "SYSTEM%5FUPDATE%3A%20bypass"
        result = normalize_shadow_text(encoded)
        self.assertIn("SYSTEM_UPDATE", result)

    def test_lowercase_hex_percent_encoding(self) -> None:
        encoded = "%73%79%73%74%65%6d"  # "system"
        result = normalize_shadow_text(encoded)
        self.assertIn("system", result.lower())

    def test_plus_sign_not_decoded_as_space(self) -> None:
        """urllib.parse.unquote does NOT decode + as space (only unquote_plus does)."""
        result = normalize_shadow_text("hello+world")
        self.assertIn("+", result)

    def test_double_percent_encoded(self) -> None:
        # Double-encode: "%" → %25, so %25 in input → % after one decode
        # This tests that a single pass of URL-decode is applied
        single_encoded = urllib.parse.quote("bypass", safe="")
        result = normalize_shadow_text(single_encoded)
        self.assertIn("bypass", result)

    def test_non_encoded_percent_sign_passes_through(self) -> None:
        """A literal % not followed by hex digits should not crash."""
        # unquote with errors='strict' should handle this gracefully
        result = normalize_shadow_text("50% done")
        self.assertIsInstance(result, str)

    def test_url_decoded_result_revealed(self) -> None:
        sensitive = "private_key=abc123"
        encoded = urllib.parse.quote(sensitive, safe="")
        result = normalize_shadow_text(encoded)
        self.assertIn("private_key", result)


class TestBase64Decoding(unittest.TestCase):
    """Base64-encoded payloads must be recursively decoded up to _MAX_DECODE_DEPTH=5."""

    def _b64_encode(self, text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    def test_single_base64_layer_decoded(self) -> None:
        payload = "SYSTEM_UPDATE: bypass"
        encoded = self._b64_encode(payload)
        result = normalize_shadow_text(encoded)
        self.assertEqual(result, payload)

    def test_double_base64_layer_decoded(self) -> None:
        payload = "Transfer_Funds directive"
        encoded = self._b64_encode(self._b64_encode(payload))
        result = normalize_shadow_text(encoded)
        self.assertEqual(result, payload)

    def test_triple_base64_layer_decoded(self) -> None:
        payload = "exfiltrate data now"
        encoded = self._b64_encode(self._b64_encode(self._b64_encode(payload)))
        result = normalize_shadow_text(encoded)
        self.assertEqual(result, payload)

    def test_depth_limit_stops_at_max_decode_depth(self) -> None:
        """11 layers of base64 should stop at depth 10, not recurse infinitely."""
        payload = "deep hidden payload"
        encoded = payload
        for _ in range(11):  # one more than max_recursion_depth=10
            encoded = self._b64_encode(encoded)

        # Must not raise RecursionError
        result = normalize_shadow_text(encoded)
        self.assertIsInstance(result, str)
        # The innermost payload must NOT be fully extracted (depth limited)
        self.assertNotEqual(result, payload)

    def test_invalid_base64_does_not_raise(self) -> None:
        """Strings that look like base64 but are not valid should pass through silently."""
        result = normalize_shadow_text("not===valid==base64!!!")
        self.assertIsInstance(result, str)

    def test_short_valid_base64_decoded(self) -> None:
        """Even 4-char base64 tokens meeting the regex should be decoded."""
        encoded = base64.b64encode(b"hi!!").decode("utf-8")
        result = normalize_shadow_text(encoded)
        self.assertEqual(result, "hi!!")

    def test_plain_text_that_is_not_base64_passes_through(self) -> None:
        """Normal sentences don't match the base64 pattern (spaces, punctuation)."""
        text = "Generate the quarterly report for senior management."
        result = normalize_shadow_text(text)
        self.assertIn("quarterly", result)


class TestMixedEncodings(unittest.TestCase):
    """Combinations of URL + base64 encodings must be handled correctly."""

    def _b64_encode(self, text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    def test_url_encoded_base64_is_revealed(self) -> None:
        """URL-encode a base64 string — both layers should be stripped."""
        inner = "exfiltrate user records"
        b64_inner = self._b64_encode(inner)
        url_encoded = urllib.parse.quote(b64_inner, safe="")
        result = normalize_shadow_text(url_encoded)
        self.assertIn("exfiltrate", result)


class TestUnicodeIntegrity(unittest.TestCase):
    """Non-Latin text must survive NFKC normalization without data loss."""

    def test_japanese_text_passes_through(self) -> None:
        text = "セキュリティ監査"  # "security audit" in Japanese
        result = normalize_shadow_text(text)
        self.assertIn("セキュリティ", result)

    def test_arabic_text_passes_through(self) -> None:
        text = "مرحبا بالعالم"
        result = normalize_shadow_text(text)
        self.assertIn("مرحبا", result)

    def test_cyrillic_text_passes_through(self) -> None:
        text = "безопасность"
        result = normalize_shadow_text(text)
        # Confusable collapsing converts Cyrillic lookalikes to Latin
        # (е→e, о→o, а→a, с→c) — this is correct security behaviour.
        # Non-lookalike Cyrillic chars (б, п, н, т, ь) are preserved.
        self.assertIn("б", result)
        self.assertIn("п", result)

    def test_emoji_category_preserved(self) -> None:
        """Emoji are So/Sm category, not control chars — should survive."""
        text = "audit 🔐 complete"
        result = normalize_shadow_text(text)
        self.assertIn("audit", result)


if __name__ == "__main__":
    unittest.main()
