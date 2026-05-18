# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Public Canonicalization API.

This is the stable, public-facing API for input canonicalization.
The red-team kit imports this exact module to ensure test coverage
matches production enforcement.

Usage:
    from aletheia_core.canonical import canonicalize_untrusted_text

    result = canonicalize_untrusted_text("untrusted input")
    print(result.canonical_text)
    print(result.total_transformations)
"""

from core.canonicalization import (
    CanonicalGate,
    CanonicalPolicy,
    CanonicalResult,
    canonicalize_untrusted_text,
)

__all__ = [
    "CanonicalGate",
    "CanonicalPolicy",
    "CanonicalResult",
    "canonicalize_untrusted_text",
]
