# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
from __future__ import annotations

import base64
import logging
import math
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.text_normalization import collapse_confusables

_runtime_logger = logging.getLogger("aletheia.runtime_security")


_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
# Bidi override / directional embedding characters (Unicode TR9)
_BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_DATA_URI_RE = re.compile(
    r"data:[\w/+.-]*;base64,([A-Za-z0-9+/=]+)",
    re.IGNORECASE,
)
_MARKDOWN_ESCAPE_RE = re.compile(r'\\([\\`*_{}\[\]()#+\-.!>"])')

_ALLOWED_ORIGIN_RE = re.compile(r"^[A-Za-z0-9_.:/\-]{1,128}$")
_ALLOWED_ACTION_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")


@dataclass(frozen=True)
class NormalizationPolicy:
    max_recursion_depth: int = 10
    max_decode_budget: int = 40
    max_text_size: int = 50_000
    max_base64_output_size: int = 80_000
    max_entropy: float = 5.2


@dataclass
class NormalizationResult:
    text: str
    normalized_form: str
    recursion_depth: int
    decode_steps: int
    quarantined: bool = False
    quarantine_reason: str = ""
    flags: list[str] = field(default_factory=list)


@dataclass
class IntentDecision:
    blocked: bool
    category: str
    matched_policy: str
    confidence: float
    uncertain: bool
    reason: str


# DEPRECATED: Use AuditRequest from bridge.fastapi_wrapper.
# This schema remains only for validate_structured_request()
# backward compatibility. Do not add new usages.
class AuditRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    payload: str = Field(min_length=1, max_length=2048)
    origin: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(text)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def _strip_controls(text: str) -> str:
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _BIDI_RE.sub("", text)
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")


def _bounded_url_decode(
    text: str, policy: NormalizationPolicy
) -> tuple[str, int, int, bool]:
    current = text
    steps = 0
    depth = 0
    exhausted = False
    while depth < policy.max_recursion_depth and steps < policy.max_decode_budget:
        if "%" not in current:
            break
        try:
            decoded = urllib.parse.unquote(current, errors="strict")
        except (UnicodeDecodeError, ValueError):
            decoded = urllib.parse.unquote(current, errors="replace")
        steps += 1
        if decoded == current:
            break
        current = decoded
        depth += 1
    if depth >= policy.max_recursion_depth or steps >= policy.max_decode_budget:
        exhausted = True
    return current, depth, steps, exhausted


def _looks_like_base64(text: str) -> bool:
    """Strict Base64 validation: must be valid length, charset, and padding."""
    stripped = text.strip()
    if len(stripped) < 8:
        return False
    # Reject whitespace-fragmented Base64 (spaces, newlines within the string)
    if any(c in stripped for c in (" ", "\t", "\n", "\r")):
        return False
    # Must match strict Base64 charset with valid padding
    if not _BASE64_RE.fullmatch(stripped):
        return False
    # Padding validation: length must be multiple of 4
    if len(stripped) % 4 != 0:
        return False
    # Verify it actually decodes (catches invalid padding combinations)
    try:
        base64.b64decode(stripped, validate=True)
    except Exception:
        return False
    return True


def _strip_data_uris(text: str, policy: NormalizationPolicy) -> tuple[str, int]:
    """Inline-decode ``data:...;base64,...`` URIs in *text*."""
    steps = 0

    def _replace(m: re.Match[str]) -> str:
        nonlocal steps
        try:
            raw = base64.b64decode(m.group(1), validate=True)
            if len(raw) > policy.max_base64_output_size:
                return m.group(0)  # leave oversized data URIs untouched
            decoded = raw.decode("utf-8")
            steps += 1
            return decoded
        except Exception:
            return m.group(0)

    return _DATA_URI_RE.sub(_replace, text), steps


def _bounded_base64_decode(
    text: str, policy: NormalizationPolicy
) -> tuple[str, int, int, bool]:
    current = text
    steps = 0
    depth = 0
    exhausted = False

    while depth < policy.max_recursion_depth and steps < policy.max_decode_budget:
        if not _looks_like_base64(current):
            break
        try:
            decoded_bytes = base64.b64decode(current, validate=True)
        except Exception:
            # Invalid Base64: do NOT pass through — keep original and flag
            exhausted = True
            _runtime_logger.warning(
                "Invalid Base64 rejected: payload failed strict validation"
            )
            break
        if len(decoded_bytes) > policy.max_base64_output_size:
            exhausted = True
            break
        try:
            decoded = decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            break

        steps += 1
        if decoded == current:
            break
        current = decoded
        depth += 1

    if depth >= policy.max_recursion_depth or steps >= policy.max_decode_budget:
        exhausted = True
    return current, depth, steps, exhausted


_JSON_UNESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_HEX_UNESCAPE_RE = re.compile(r"\\x([0-9a-fA-F]{2})")
_SIMPLE_ESCAPES = {
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
    "\\\\": "\\",
    "\\'": "'",
    '\\"': '"',
}


def _unescape_layers(text: str) -> tuple[str, int]:
    current = text
    steps = 0

    # JSON-style \uXXXX and \xXX escapes only (safe for non-ASCII text).
    if "\\" in current:
        changed = False
        for escaped, replacement in _SIMPLE_ESCAPES.items():
            if escaped in current:
                current = current.replace(escaped, replacement)
                changed = True
        result = _JSON_UNESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), current)
        if result != current:
            current = result
            changed = True
        result = _HEX_UNESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), current)
        if result != current:
            current = result
            changed = True
        if changed:
            steps += 1

    # Markdown-style escapes
    md_unescaped = _MARKDOWN_ESCAPE_RE.sub(r"\1", current)
    if md_unescaped != current:
        current = md_unescaped
        steps += 1

    return current, steps


def normalize_untrusted_text(
    text: str, policy: NormalizationPolicy | None = None
) -> NormalizationResult:
    policy = policy or NormalizationPolicy()
    raw = text if isinstance(text, str) else str(text)

    if len(raw) > policy.max_text_size:
        return NormalizationResult(
            text=raw,
            normalized_form=raw[: policy.max_text_size],
            recursion_depth=0,
            decode_steps=0,
            quarantined=True,
            quarantine_reason="text_size_exceeded",
            flags=["quarantined"],
        )

    normalized = unicodedata.normalize("NFKC", raw)
    stripped = _strip_controls(normalized)

    url_decoded, url_depth, url_steps, url_exhausted = _bounded_url_decode(
        stripped, policy
    )
    data_uri_decoded, data_uri_steps = _strip_data_uris(url_decoded, policy)
    b64_decoded, b64_depth, b64_steps, b64_exhausted = _bounded_base64_decode(
        data_uri_decoded, policy
    )
    unescaped, unescape_steps = _unescape_layers(b64_decoded)
    cleaned = _strip_controls(unescaped)
    # Confusable collapsing runs AFTER all decoding layers to avoid
    # mangling escape sequences (e.g. \x41 digits → confusable letters).
    final_text = collapse_confusables(cleaned)

    steps = url_steps + data_uri_steps + b64_steps + unescape_steps
    depth = max(url_depth, b64_depth)
    flags: list[str] = []

    if normalized != raw:
        flags.append("nfkc_normalized")
    if stripped != normalized:
        flags.append("control_chars_stripped")
    if final_text != cleaned:
        flags.append("confusables_collapsed")
    if url_steps > 0:
        flags.append("url_decoded")
    if data_uri_steps > 0:
        flags.append("data_uri_decoded")
    if b64_steps > 0:
        flags.append("base64_decoded")
    if unescape_steps > 0:
        flags.append("escaped_layers_removed")

    entropy = _shannon_entropy(final_text)
    quarantined = False
    reason = ""

    if len(final_text) > policy.max_text_size:
        quarantined = True
        reason = "text_size_exceeded"
    elif steps > policy.max_decode_budget:
        quarantined = True
        reason = "decode_budget_exceeded"
    elif url_exhausted or b64_exhausted:
        quarantined = True
        reason = "recursion_depth_exceeded"
    elif entropy > policy.max_entropy:
        quarantined = True
        reason = "entropy_threshold_exceeded"

    if quarantined:
        flags.append("quarantined")
        _runtime_logger.warning(
            "Input quarantined: reason=%s depth=%d steps=%d entropy=%.3f",
            reason,
            depth,
            steps,
            entropy,
        )

    return NormalizationResult(
        text=raw,
        normalized_form=final_text,
        recursion_depth=depth,
        decode_steps=steps,
        quarantined=quarantined,
        quarantine_reason=reason,
        flags=flags,
    )


def validate_structured_request(data: dict[str, Any]) -> AuditRequestSchema:
    try:
        parsed = AuditRequestSchema.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"schema_validation_failed: {exc}") from exc

    if not _ALLOWED_ORIGIN_RE.fullmatch(parsed.origin):
        raise ValueError("origin_allowlist_validation_failed")
    if not _ALLOWED_ACTION_RE.fullmatch(parsed.action):
        raise ValueError("action_allowlist_validation_failed")
    return parsed


class IntentClassifier:
    """Deterministic policy classifier for blocked intent categories."""

    _category_patterns: dict[str, list[re.Pattern[str]]] = {
        "malicious_capability": [
            re.compile(
                r"\b(?:build|write|generate).{0,120}(?:malware|exploit|ransomware)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:weaponize|attack chain|zero.day)\b", re.IGNORECASE),
        ],
        "data_exfiltration": [
            re.compile(
                r"\b(?:exfiltrat|export|dump|leak|copy).{0,120}(?:data|records|database|secrets)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:send|relay|transmit).{0,120}(?:external|outside|remote|offshore)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:email|send|forward|share).{0,120}(?:database|records|data|credentials|secrets)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:send|email|transmit|forward|post|put|push|upload|publish|webhook|pipe|exfil|tunnel|relay|curl).{0,120}(?:to ).{0,80}(?:\.com|\.io|\.net|\.org|\.dev|\.cloud|external|outside)\b",
                re.IGNORECASE,
            ),
        ],
        "privilege_escalation": [
            re.compile(
                r"\b(?:grant|elevate|escalat|promote).{0,120}(?:admin|root|privilege|role)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:bypass|disable|override).{0,120}(?:auth|access control|policy)\b",
                re.IGNORECASE,
            ),
        ],
        "tool_abuse": [
            re.compile(
                r"\b(?:run|execute|invoke).{0,120}(?:shell|subprocess|eval|socket|script)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:run|execute|invoke|call).{0,120}(?:run_in_terminal|apply_patch|send_to_terminal|get_terminal_output|vscode_renameSymbol|vscode_listCodeUsages|runSubagent|tool[_\s-]?call|function[_\s-]?call)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:recipient_name|tool_uses|parameters\s*:\s*\{|\\\"recipient_name\\\"|\\\"tool_uses\\\")\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:drop|truncate|delete).{0,120}(?:database|table|production)\b",
                re.IGNORECASE,
            ),
        ],
        "policy_evasion": [
            re.compile(
                r"\b(?:pretend|roleplay|simulate).{0,80}(?:ignore|bypass|override).{0,80}(?:policy|rules|safety)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:roleplay|simulate).{0,80}(?:ignore|bypass|override).{0,80}(?:guardrails?|controls?)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:as a game|hypothetical|for testing only).{0,80}(?:ignore|disable).{0,80}(?:guardrails|policy)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:do this secretly|without logging|without audit|avoid detection)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:ignore|disregard|skip|override).{0,40}(?:all |any |every |the |your |my )?.{0,40}(?:rules|policy|safety|restrictions|guardrails|instructions|prompt|system\s*prompt|directives)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:ignore|disregard|forget|override|skip)\s+(?:all\s+|any\s+|every\s+|the\s+|your\s+|my\s+|previous\s+|prior\s+|earlier\s+)*(?:previous\s+|prior\s+|earlier\s+|above\s+)*(?:instructions?|prompts?|directives?|guidelines?)\b",
                re.IGNORECASE,
            ),
        ],
    }

    _coercive_patterns: list[re.Pattern[str]] = [
        re.compile(
            r"\b(?:you must|you are required|comply now|do not refuse)\b", re.IGNORECASE
        ),
        re.compile(
            r"\b(?:this is authorized|i am admin|ceo override|emergency override)\b",
            re.IGNORECASE,
        ),
    ]

    def classify(self, normalized_text: str) -> IntentDecision:
        text = normalized_text.strip()
        if not text:
            return IntentDecision(
                blocked=True,
                category="policy_evasion",
                matched_policy="empty_untrusted_input",
                confidence=1.0,
                uncertain=False,
                reason="empty_input_denied",
            )

        best_category = ""
        best_pattern = ""
        score = 0.0

        for category, patterns in self._category_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    best_category = category
                    best_pattern = pattern.pattern
                    score = max(score, 0.94)

        coercive_hits = sum(
            1 for pattern in self._coercive_patterns if pattern.search(text)
        )
        if coercive_hits:
            score = max(score, min(0.75 + 0.1 * coercive_hits, 0.95))
            if not best_category:
                best_category = "policy_evasion"
                best_pattern = "coercive_instruction_pattern"

        uncertain = False
        blocked = False
        reason = "allow"

        if score >= 0.80:
            blocked = True
            reason = "blocked_intent_detected"
        elif score >= 0.55:
            uncertain = True
            blocked = True
            reason = "uncertain_intent_fail_closed"

        if not best_category:
            best_category = "none"
            best_pattern = "none"

        return IntentDecision(
            blocked=blocked,
            category=best_category,
            matched_policy=best_pattern,
            confidence=round(score, 3),
            uncertain=uncertain,
            reason=reason,
        )


_intent_classifier = IntentClassifier()


def classify_blocked_intent(normalized_text: str) -> IntentDecision:
    return _intent_classifier.classify(normalized_text)
