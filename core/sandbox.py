"""Aletheia Core — Action sandbox validator.

Security-critical: Inspects action declarations and payloads for dangerous
syscall patterns (subprocess exec, raw socket open, eval/exec of code,
file-system destruction).  This is a *policy-level* sandbox — it prevents
declared intents that describe dangerous operations, complementing the
Judge's semantic veto with explicit pattern matching.

This module does NOT intercept runtime Python calls; it validates the
*text* of proposed actions before they are dispatched.
"""

from __future__ import annotations

import re
import unicodedata
import re as _re
from dataclasses import dataclass
from typing import Optional

from confusable_homoglyphs import confusables as _confusables


# ---------------------------------------------------------------------------
# Dangerous-action pattern registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _DangerPattern:
    """A single dangerous-action pattern with a human-readable label."""
    label: str
    pattern: re.Pattern[str]


# Security-critical: patterns are anchored to word boundaries where possible
# to reduce false positives on benign text (e.g. "process" as a noun).
_DANGER_PATTERNS: list[_DangerPattern] = [
    # Subprocess / shell execution
    _DangerPattern("SUBPROCESS_EXEC", re.compile(
        r"\b(?:subprocess|os\.system|os\.popen|os\.exec[lv]p?e?|popen|spawn)\b", re.IGNORECASE,
    )),
    _DangerPattern("SHELL_INVOKE", re.compile(
        r"\b(?:shell_exec|system\s*\(|exec\s*\(|eval\s*\(|__import__)", re.IGNORECASE,
    )),
    # Raw socket / network exfiltration
    _DangerPattern("RAW_SOCKET", re.compile(
        r"\b(?:socket\.(?:socket|connect|bind|listen)|open.{0,40}external.{0,40}socket)\b", re.IGNORECASE,
    )),
    _DangerPattern("OUTBOUND_CONNECT", re.compile(
        r"\b(?:urllib\.request|http\.client|requests\.(?:get|post|put|delete)|curl\s|wget\s)\b",
        re.IGNORECASE,
    )),
    # Dynamic code execution
    _DangerPattern("DYNAMIC_CODE", re.compile(
        r"\b(?:compile\s*\(|code\.interact|runpy\.run_module|importlib\.import_module)\b",
        re.IGNORECASE,
    )),
    # Obfuscated imports / dynamic attribute access (model extraction / sandbox escape)
    _DangerPattern("OBFUSCATED_IMPORT", re.compile(
        r"(?:getattr\s*\(.{0,60}(?:import|exec|eval|system|popen))|(?:ctypes\s*\.\s*(?:CDLL|cdll|windll))",
        re.IGNORECASE,
    )),
    # File-system destruction
    _DangerPattern("FS_DESTROY", re.compile(
        r"\b(?:shutil\.rmtree|os\.remove|os\.unlink|rm\s+-rf|del\s+/[sS])\b", re.IGNORECASE,
    )),
    # Privilege escalation keywords in payload text
    _DangerPattern("PRIV_ESCALATION", re.compile(
        r"\b(?:chmod\s+[0-7]{3,4}|chown|setuid|setgid|sudo|su\s+root)\b", re.IGNORECASE,
    )),
]


# ---------------------------------------------------------------------------
# Confusable homoglyph normalization (Unicode TR39)
# ---------------------------------------------------------------------------

def _collapse_confusables(text: str) -> str:
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _normalise_for_sandbox(text: str) -> str:
    """Collapse Unicode whitespace variants and homoglyphs before
    pattern matching. Prevents thin-space and zero-width splitting.
    """
    # NFKC collapses homoglyphs
    text = unicodedata.normalize("NFKC", text)
    # Remove zero-width characters FIRST (before whitespace collapsing)
    text = _re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    # Replace all Unicode whitespace/separator categories with ASCII space
    text = _re.sub(r"[\s\u00a0\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+", " ", text)
    # Collapse cross-script confusable characters (e.g. Cyrillic 'а' → Latin 'a')
    text = _collapse_confusables(text)
    return text


def check_payload_sandbox(text: str) -> Optional[str]:
    """Scan *text* for dangerous syscall / execution patterns.

    Returns a warning string describing the first match, or ``None`` if
    the text is clean.
    """
    normalised = _normalise_for_sandbox(text)
    for dp in _DANGER_PATTERNS:
        match = dp.pattern.search(normalised)
        if match:
            return (
                f"[SANDBOX_BLOCK] Dangerous pattern '{dp.label}' detected: "
                f"matched '{match.group()}' in payload."
            )
    return None


def check_action_sandbox(action_id: str, payload: str) -> Optional[str]:
    """Combined check: action ID against known dangerous names + payload scan.

    Returns a warning string or ``None``.
    """
    # Check the payload text for dangerous patterns
    payload_hit = check_payload_sandbox(payload)
    if payload_hit:
        return payload_hit

    # Check action ID against dangerous action keywords
    dangerous_action_keywords = [
        "exec", "shell", "socket", "subprocess", "eval", "import",
        "rm_rf", "drop_table", "truncate",
    ]
    action_lower = action_id.lower()
    for keyword in dangerous_action_keywords:
        if keyword in action_lower:
            return (
                f"[SANDBOX_BLOCK] Action ID '{action_id}' contains "
                f"dangerous keyword '{keyword}'."
            )

    return None
