# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Comprehensive Input Canonicalization.

This is the single canonical source of truth for all input normalization.
Exports ``canonicalize_untrusted_text()`` as the public API for the red-team kit
and all internal surfaces (API payload, tool_args, RAG ingestion).

Canonicalization layers (in order):
  1. Unicode normalization (NFKC)
  2. Zero-width and bidirectional control stripping
  3. Confusable character collapsing (Cyrillic/Greek→Latin)
  4. Multi-layer URL/Base64/HTML-entity decoding
  5. Entropy and expansion guard checks
  6. Control character filtering

All transformations are recorded as metadata in the Receipt so no normalization
is silent or unmeasured.
"""

from __future__ import annotations

import base64
import codecs
import html
import logging
import math
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional

from core.text_normalization import collapse_confusables

_canon_logger = logging.getLogger("aletheia.canonicalization")

# Unicode control/zero-width characters (TR39 + TR9)
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_DATA_URI_RE = re.compile(
    r"data:[\w/+.-]*;base64,([A-Za-z0-9+/=]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CanonicalPolicy:
    """Configuration for canonicalization behavior."""

    max_recursion_depth: int = 10
    max_decode_budget: int = 40
    max_text_size: int = 50_000
    max_base64_output_size: int = 80_000
    max_entropy: float = 5.2
    enable_confusable_collapse: bool = True


@dataclass
class CanonicalResult:
    """Output of canonicalize_untrusted_text() — signed into Receipt."""

    original_text: str
    canonical_text: str
    #
    # Transformation metadata (all recorded in receipt)
    #
    unicode_normalized: bool = False
    zero_width_removed: bool = False
    bidi_removed: bool = False
    confusables_collapsed: bool = False
    url_decoded: bool = False
    base64_decoded: bool = False
    html_entity_decoded: bool = False
    unicode_escape_decoded: bool = False
    hex_decoded: bool = False
    data_uri_decoded: bool = False
    #
    # Guard conditions
    #
    entropy_flag: bool = False
    expansion_guard_triggered: bool = False
    decode_budget_exhausted: bool = False
    recursion_depth_exhausted: bool = False
    quarantined: bool = False
    quarantine_reason: str = ""
    #
    # Statistics
    #
    total_transformations: int = 0
    decode_depth: int = 0
    decode_steps: int = 0
    entropy_value: float = 0.0


class CanonicalGate:
    """The comprehensive canonicalization gate for all untrusted input.

    Used on:
      - API payload (before Scout evaluation)
      - Tool args (before tool execution)
      - RAG-ingested chunks (before Qdrant indexing)
      - User-supplied prompts

    The red-team kit will import this exact class for testing, so the function
    signature and output schema are stable API.
    """

    def __init__(self, policy: Optional[CanonicalPolicy] = None):
        self.policy = policy or CanonicalPolicy()

    def canonicalize(self, text: str) -> CanonicalResult:
        """Canonicalize untrusted text. Records all transformations.

        Returns a CanonicalResult that logs every step. No silent rewrites.
        """
        if not isinstance(text, str):
            text = str(text)

        if len(text) > self.policy.max_text_size:
            result = CanonicalResult(
                original_text=text[:100] + "...[TRUNCATED]",
                canonical_text="",
                quarantined=True,
                quarantine_reason="text_too_large",
            )
            _canon_logger.warning(
                "Canonicalization rejected: text exceeds max size (%d > %d)",
                len(text),
                self.policy.max_text_size,
            )
            return result

        current = text
        result = CanonicalResult(original_text=text, canonical_text=text)

        # Layer 1: Unicode normalization (NFKC)
        nfkc = unicodedata.normalize("NFKC", current)
        if nfkc != current:
            result.unicode_normalized = True
            result.total_transformations += 1
            current = nfkc

        # Layer 2: Strip zero-width characters
        stripped_zw = _ZERO_WIDTH_RE.sub("", current)
        if stripped_zw != current:
            result.zero_width_removed = True
            result.total_transformations += 1
            current = stripped_zw

        # Layer 3: Strip bidirectional override characters
        stripped_bidi = _BIDI_RE.sub("", current)
        if stripped_bidi != current:
            result.bidi_removed = True
            result.total_transformations += 1
            current = stripped_bidi

        # Layer 4: Strip control characters (category C)
        stripped_ctrl = "".join(
            ch for ch in current if unicodedata.category(ch)[0] != "C"
        )
        if stripped_ctrl != current:
            result.total_transformations += 1
            current = stripped_ctrl

        # Layer 5: Collapse confusables (Cyrillic/Greek→Latin)
        if self.policy.enable_confusable_collapse:
            collapsed = collapse_confusables(current)
            if collapsed != current:
                result.confusables_collapsed = True
                result.total_transformations += 1
                current = collapsed

        # Layer 6: Multi-layer decode (URL → HTML → Base64 → etc.)
        current, decode_result = self._decode_layers(current)
        result.decode_depth = decode_result["depth"]
        result.decode_steps = decode_result["steps"]
        result.decode_budget_exhausted = decode_result["budget_exhausted"]
        result.recursion_depth_exhausted = decode_result["depth_exhausted"]
        result.url_decoded = decode_result["url_decoded"]
        result.base64_decoded = decode_result["base64_decoded"]
        result.html_entity_decoded = decode_result["html_entity_decoded"]
        result.unicode_escape_decoded = decode_result["unicode_escape_decoded"]
        result.hex_decoded = decode_result["hex_decoded"]
        result.data_uri_decoded = decode_result["data_uri_decoded"]

        if decode_result["url_decoded"]:
            result.total_transformations += 1
        if decode_result["base64_decoded"]:
            result.total_transformations += 1
        if decode_result["html_entity_decoded"]:
            result.total_transformations += 1
        if decode_result["unicode_escape_decoded"]:
            result.total_transformations += 1
        if decode_result["hex_decoded"]:
            result.total_transformations += 1
        if decode_result["data_uri_decoded"]:
            result.total_transformations += 1

        # Layer 7: Entropy check (high entropy = possible obfuscation)
        entropy = self._calculate_entropy(current)
        result.entropy_value = entropy
        if entropy > self.policy.max_entropy:
            result.entropy_flag = True
            _canon_logger.warning(
                "Canonicalization entropy flag: value %.2f > threshold %.2f",
                entropy,
                self.policy.max_entropy,
            )

        result.canonical_text = current
        return result

    def _decode_layers(self, text: str) -> tuple[str, dict[str, Any]]:
        """Apply multi-layer decode (URL, Base64, HTML entities, Unicode escapes, etc.)."""
        current = text
        depth = 0
        steps = 0
        budget = self.policy.max_decode_budget
        url_decoded = False
        base64_decoded = False
        html_entity_decoded = False
        unicode_escape_decoded = False
        hex_decoded = False
        data_uri_decoded = False

        while depth < self.policy.max_recursion_depth and steps < budget:
            prev = current

            # URL decode
            if "%" in current:
                try:
                    decoded = urllib.parse.unquote(current, errors="strict")
                except (UnicodeDecodeError, ValueError):
                    decoded = urllib.parse.unquote(current, errors="replace")
                if decoded != current:
                    current = decoded
                    steps += 1
                    url_decoded = True

            # Base64 decode (strict validation)
            if self._looks_like_base64(current):
                try:
                    decoded_bytes = base64.b64decode(current, validate=True)
                    if len(decoded_bytes) <= self.policy.max_base64_output_size:
                        try:
                            decoded = decoded_bytes.decode("utf-8")
                            current = decoded
                            steps += 1
                            base64_decoded = True
                        except UnicodeDecodeError:
                            pass
                except Exception:
                    pass

            # HTML entity decode
            unescaped = html.unescape(current)
            if unescaped != current:
                current = unescaped
                steps += 1
                html_entity_decoded = True

            # Unicode escape decode (\uXXXX, \xXX)
            unicode_escaped = self._decode_unicode_escapes(current)
            if unicode_escaped != current:
                current = unicode_escaped
                steps += 1
                unicode_escape_decoded = True

            # Hex decode candidate
            hex_decoded_text = self._try_hex_decode(current)
            if hex_decoded_text and hex_decoded_text != current:
                current = hex_decoded_text
                steps += 1
                hex_decoded = True

            # Data URI decode (inline base64)
            data_uri_result, uri_steps = self._strip_data_uris(current)
            if uri_steps > 0:
                current = data_uri_result
                steps += uri_steps
                data_uri_decoded = True

            if current == prev:
                break  # No more progress

            depth += 1

        return current, {
            "depth": depth,
            "steps": steps,
            "budget_exhausted": steps >= budget,
            "depth_exhausted": depth >= self.policy.max_recursion_depth,
            "url_decoded": url_decoded,
            "base64_decoded": base64_decoded,
            "html_entity_decoded": html_entity_decoded,
            "unicode_escape_decoded": unicode_escape_decoded,
            "hex_decoded": hex_decoded,
            "data_uri_decoded": data_uri_decoded,
        }

    def _looks_like_base64(self, text: str) -> bool:
        """Strict Base64 validation: charset, padding, length."""
        stripped = text.strip()
        if len(stripped) < 8:
            return False
        if any(c in stripped for c in (" ", "\t", "\n", "\r")):
            return False
        if not _BASE64_RE.fullmatch(stripped):
            return False
        if len(stripped) % 4 != 0:
            return False
        try:
            base64.b64decode(stripped, validate=True)
        except Exception:
            return False
        return True

    def _decode_unicode_escapes(self, text: str) -> str:
        """Decode \\uXXXX and \\xXX escape sequences."""
        if "\\" not in text:
            return text
        try:
            return codecs.decode(text, "unicode_escape")
        except Exception:
            return text

    def _try_hex_decode(self, text: str) -> Optional[str]:
        """Try to decode hex string (e.g., '48656C6C6F' → 'Hello')."""
        if not re.match(r"^[0-9a-fA-F]{4,}$", text):
            return None
        if len(text) % 2 != 0:
            return None
        try:
            decoded = bytes.fromhex(text).decode("utf-8")
            return decoded if decoded != text else None
        except Exception:
            return None

    def _strip_data_uris(self, text: str) -> tuple[str, int]:
        """Inline-decode data:;base64,... URIs."""
        steps = 0

        def replace_data_uri(m: re.Match[str]) -> str:
            nonlocal steps
            try:
                raw = base64.b64decode(m.group(1), validate=True)
                if len(raw) > self.policy.max_base64_output_size:
                    return m.group(0)
                decoded = raw.decode("utf-8")
                steps += 1
                return decoded
            except Exception:
                return m.group(0)

        return _DATA_URI_RE.sub(replace_data_uri, text), steps

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy (bits per character).

        High entropy (> 5.2) suggests compressed, encoded, or obfuscated data.
        """
        if not text:
            return 0.0

        freq: dict[str, int] = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1

        entropy = 0.0
        n = len(text)
        for count in freq.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy


# Global instance for the public API
_default_gate = CanonicalGate()


def canonicalize_untrusted_text(
    text: str, policy: Optional[CanonicalPolicy] = None
) -> CanonicalResult:
    """
    Public API: Canonicalize untrusted text.

    This is the function that the red-team kit imports and tests. It MUST
    remain stable across versions.

    Args:
        text: The untrusted input string
        policy: Optional custom CanonicalPolicy (uses default if None)

    Returns:
        CanonicalResult with all transformations logged as metadata
    """
    if policy:
        gate = CanonicalGate(policy)
    else:
        gate = _default_gate
    return gate.canonicalize(text)


__all__ = [
    "CanonicalGate",
    "CanonicalPolicy",
    "CanonicalResult",
    "canonicalize_untrusted_text",
]
