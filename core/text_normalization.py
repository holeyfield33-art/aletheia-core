# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Shared text normalization utilities."""

from __future__ import annotations

from confusable_homoglyphs import confusables as _confusables


def collapse_confusables(text: str) -> str:
    """Replace cross-script confusable characters with their Latin equivalents.

    Uses Unicode TR39 confusable data to collapse Cyrillic/Greek/etc lookalikes
    that NFKC normalization does not handle (e.g. Cyrillic 'а' U+0430 → Latin 'a').
    Only affects non-ASCII characters — ASCII chars pass through unchanged.
    """
    result: list[str] = []
    for ch in text:
        # Skip ASCII characters — they are never replaced
        if ord(ch) < 128:
            result.append(ch)
            continue
        conf = _confusables.is_confusable(ch, preferred_aliases=["latin"], greedy=False)
        if conf:
            replaced = False
            for entry in conf:
                for homoglyph in entry.get("homoglyphs", []):
                    if "LATIN" in homoglyph.get("n", "").upper():
                        result.append(homoglyph["c"])
                        replaced = True
                        break
                if replaced:
                    break
            if not replaced:
                result.append(ch)
        else:
            result.append(ch)
    return "".join(result)
