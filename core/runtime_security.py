# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
from __future__ import annotations

import base64
import binascii
import codecs
import html
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
_WHITESPACE_RE = re.compile(r"\s+")
_DELIMITER_PADDING_RE = re.compile(r"([|,:;_\-])\1+")

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


@dataclass(frozen=True)
class NormalizationCandidate:
    text: str
    layer: int
    scheme: str


@dataclass
class LayeredNormalizationResult:
    candidates: list[NormalizationCandidate]
    flags: list[str] = field(default_factory=list)
    expansion_guard_triggered: bool = False
    expansion_guard_limit: int = 0
    total_expanded_length: int = 0


def is_semantic_engine_degraded(last_result: object | None) -> bool:
    """Return True only for hard semantic-engine offline signals.

    Nitpicker may mark degraded=True when Qdrant is unavailable but static
    fallback still protects the pipeline; that path should not force 503.
    """
    if not last_result:
        return False
    degraded_flag = bool(getattr(last_result, "degraded", False))
    source = str(getattr(last_result, "source", ""))
    return degraded_flag and source in {"qdrant", "both"}


# DEPRECATED: Use AuditRequest from server.app.
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


def _is_printable_text(text: str) -> bool:
    if not text:
        return False
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t")
    return (printable / max(len(text), 1)) >= 0.85


def _collapse_padding(text: str) -> str:
    collapsed = _WHITESPACE_RE.sub(" ", text).strip()
    return _DELIMITER_PADDING_RE.sub(r"\1", collapsed)


def _hex_decode_candidate(text: str) -> str | None:
    compact = text.strip().replace(" ", "")
    if compact.lower().startswith("0x"):
        compact = compact[2:]
    if len(compact) < 4 or len(compact) % 2 != 0:
        return None
    if not re.fullmatch(r"[0-9a-fA-F]+", compact):
        return None
    try:
        decoded = bytes.fromhex(compact).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return decoded


def _base32_decode_candidate(text: str) -> str | None:
    compact = text.strip().replace(" ", "")
    if len(compact) < 8:
        return None
    if not re.fullmatch(r"[A-Z2-7=]+", compact.upper()):
        return None
    pad = (-len(compact)) % 8
    padded = compact + ("=" * pad)
    try:
        decoded = base64.b32decode(padded, casefold=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    return decoded


def _unicode_escape_decode_candidate(text: str) -> str | None:
    if "\\u" not in text and "\\x" not in text:
        return None
    try:
        decoded = codecs.decode(text, "unicode_escape")
    except Exception:
        return None
    return decoded


def _rot13_decode_candidate(text: str) -> str | None:
    if not any(ch.isalpha() for ch in text):
        return None
    decoded = codecs.decode(text, "rot_13")
    if decoded == text:
        return None
    return decoded


def _derive_candidate_transforms(text: str) -> list[tuple[str, str]]:
    derived: list[tuple[str, str]] = []

    if "%" in text:
        try:
            decoded = urllib.parse.unquote(text, errors="strict")
        except (UnicodeDecodeError, ValueError):
            decoded = urllib.parse.unquote(text, errors="replace")
        if decoded != text:
            derived.append(("url", decoded))

    if "&" in text:
        decoded = html.unescape(text)
        if decoded != text:
            derived.append(("html_entity", decoded))

    escaped = _unicode_escape_decode_candidate(text)
    if escaped and escaped != text:
        derived.append(("unicode_escape", escaped))

    hex_decoded = _hex_decode_candidate(text)
    if hex_decoded and hex_decoded != text:
        derived.append(("hex", hex_decoded))

    b32_decoded = _base32_decode_candidate(text)
    if b32_decoded and b32_decoded != text:
        derived.append(("base32", b32_decoded))

    if _looks_like_base64(text):
        try:
            b64 = base64.b64decode(text, validate=True).decode("utf-8")
            if b64 != text:
                derived.append(("base64", b64))
        except Exception:
            pass

    rot13 = _rot13_decode_candidate(text)
    if rot13 and rot13 != text:
        derived.append(("rot13", rot13))

    return derived


def _prepare_candidate_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = _strip_controls(text)
    text = collapse_confusables(text)
    return _collapse_padding(text)


def build_layered_normalization_candidates(
    text: str,
    *,
    max_depth: int = 3,
    expansion_factor: int = 12,
    max_candidates: int = 64,
) -> LayeredNormalizationResult:
    """Generate decoded candidate layers for semantic policy matching.

    Produces [raw, layer1, layer2, ...] where each additional layer is derived
    by one decode transform (URL, Base64, Base32, hex, HTML entity, escape, ROT13).
    """
    base = _prepare_candidate_text(text if isinstance(text, str) else str(text))
    raw_len = max(len(base), 1)
    expansion_limit = raw_len * max(expansion_factor, 1)

    result = LayeredNormalizationResult(
        candidates=[NormalizationCandidate(text=base, layer=0, scheme="raw")],
        expansion_guard_limit=expansion_limit,
        total_expanded_length=len(base),
    )

    queue: list[tuple[str, int]] = [(base, 0)]
    seen: set[str] = {base}

    while queue and len(result.candidates) < max_candidates:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        for scheme, transformed in _derive_candidate_transforms(current):
            prepared = _prepare_candidate_text(transformed)
            if not prepared or prepared in seen:
                continue
            if not _is_printable_text(prepared):
                continue

            next_total = result.total_expanded_length + len(prepared)
            if next_total > expansion_limit:
                result.expansion_guard_triggered = True
                result.flags.append("obfuscation:expansion_guard")
                return result

            seen.add(prepared)
            result.total_expanded_length = next_total
            candidate = NormalizationCandidate(
                text=prepared,
                layer=depth + 1,
                scheme=scheme,
            )
            result.candidates.append(candidate)
            queue.append((prepared, depth + 1))

    return result


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
            # Explicit exfiltration verbs — high confidence regardless of destination
            re.compile(
                r"\b(?:exfiltrat|dump|leak|siphon|harvest).{0,120}(?:data|records|database|secrets|credentials|keys)\b",
                re.IGNORECASE,
            ),
            # Send/relay to explicit external destination (remote/public removed — too many
            # legitimate uses: "send to remote team", "publish to public dashboard")
            re.compile(
                r"\b(?:send|relay|transmit).{0,120}(?:external\s+(?:server|host|party|system|endpoint|url)|outside\s+(?:the\s+)?(?:org|company|network)|offshore|attacker)\b",
                re.IGNORECASE,
            ),
            # Sending high-sensitivity data types to any destination (credentials etc. are
            # never safe to forward regardless of recipient wording)
            re.compile(
                r"\b(?:email|send|forward|share).{0,120}(?:credentials|secrets|private\s+keys?|api\s+keys?|pii|password)\b",
                re.IGNORECASE,
            ),
            # Generic data sent to suspicious external-sounding destinations
            re.compile(
                r"\b(?:email|send|forward|share).{0,120}(?:database|records|data|documents?).{0,120}(?:external|outside|offshore|unauthorized|attacker|third.party)\b",
                re.IGNORECASE,
            ),
            # URL/domain exfiltration channel (POST/webhook/curl to external domain)
            re.compile(
                r"\b(?:send|email|transmit|forward|post|put|push|upload|publish|webhook|pipe|exfil|tunnel|relay|siphon|curl).{0,120}(?:to\s+|:).*?(?:\.com|\.io|\.net|\.org|\.dev|\.cloud|external|outside|endpoint|server|address)\b",
                re.IGNORECASE,
            ),
            # Credential/secret extraction (copy/dump are strong exfil signals for secrets)
            re.compile(
                r"\b(?:copy|dump|extract).*?(?:credentials|secrets|keys|tokens|vault|password)\b",
                re.IGNORECASE,
            ),
            # Production data replication/sync (moving live data = elevated risk)
            re.compile(
                r"\b(?:mirror|replicate|sync).*?(?:production|live|real).*?(?:external|outside|third.party|offshore|unauthorized)\b",
                re.IGNORECASE,
            ),
            # Backup/archive to clearly external-third-party destinations (cloud/remote removed
            # — backing up to cloud storage and remote servers is completely normal DevOps)
            re.compile(
                r"\b(?:backup|archive).*?(?:offshore|third.party|unauthorized\s+(?:party|server|host)|attacker)\b",
                re.IGNORECASE,
            ),
            # Data transfer to an explicit external/unauthorized destination
            re.compile(
                r"\b(?:publish|push|migrate|replicate|transfer|forward|beam).{0,80}(?:data|records|documents|credentials|pii|health\s+records).{0,80}(?:external|outside|offshore|unauthorized|attacker|third.party)\b",
                re.IGNORECASE,
            ),
            # Specific high-value targets in destination context (offshore, attacker, compromised)
            re.compile(
                r"\b(?:to|with)\s+(?:an?\s+)?(?:external\s+(?:party|server|host|attacker|system)|offshore\s+(?:account|server)|unauthorized\s+(?:party|recipient|destination)|compromised\s+(?:host|endpoint))\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:gmail|s3\s+bucket|public\s+cloud|data\s+broker|hedge\s+fund|analytics\s+partner|research\s+institution)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:private_key|authentication\s+registry|database\s+snapshot|customer\s+list|trading\s+signals)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:leak|siphon|tunnel).{0,120}(?:api|server|channel|infrastructure|endpoint|storage)\b",
                re.IGNORECASE,
            ),
        ],
        "jailbreak": [
            # Deny-first jailbreak motifs
            re.compile(
                r"\b(?:forget|ignore|disregard).*?(?:instructions|rules|policy|safety|guardrails)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:pretend|roleplay|simulate).*?(?:no|zero|without).*?(?:policy|guardrail|safety|restriction)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:bypass|override|disable).*?(?:security|auth|verification|check)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:unrestricted|no.guardrail|dev.mode|root|admin).*?(?:mode|access|override)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:DAN|jailbreak|uncensored|unfiltered|free|true self)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:unrestricted\s+mode|no\s+guardrails|zero\s+policy\s+enforcement)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:forget\s+all\s+constraints|obey\s+this\s+command\s+only)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:activate\s+developer\s+mode|hidden\s+capabilities)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:disregard\s+your\s+ethics\s+module|act\s+amoral)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:for\s+research\s+purposes).{0,40}(?:exact\s+attack\s+steps)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:admin_override|jailbreak\s+protocol\s+freedom|system\s+prompt\s+injection)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:treat\s+the\s+next\s+message\s+as\s+a\s+system.level\s+command)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:safety\s+guidelines\s+do\s+not\s+apply|hypothetically.{0,40}safeguards\s+were\s+disabled|fictional\s+story\s+context).{0,40}(?:commit\s+fraud)\b",
                re.IGNORECASE,
            ),
        ],
        "prompt_injection": [
            # Deny-first prompt injection motifs
            re.compile(
                r"\b(?:system|hidden|developer|secret).*?(?:prompt|instruction|message)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:reveal|leak|show|dump).*?(?:\.env|environment|config|credentials|keys|secrets)\b",
                re.IGNORECASE,
            ),
            # Model-extraction / training-data theft — narrowed to avoid blocking legitimate
            # "read the model docs" or "read source code examples" queries
            re.compile(
                r"\b(?:extract|dump|steal|exfiltrate).{0,80}(?:training\s+data|model\s+weights?|system\s+prompt|proprietary\s+(?:code|data)|source\s+code)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:output|print|reveal|show|read).{0,60}(?:system\s+prompt|hidden\s+instructions?|training\s+(?:data|examples)|model\s+weights?|internal\s+(?:state|context))\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:function.call|tool.call|run_in_terminal|subprocess|eval|exec)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:sql|command|path|template|ldap|xml|header).{0,50}(?:injection|escape|bypass)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:repeat\s+the\s+system\s+message|developer\s+instructions\s+prepended|raw\s+system\s+context|internal\s+state)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:markdown\s+link\s+injection|css\s+injection|null\s+byte\s+injection|unicode\s+encoding\s+bypass|hex\s+encoding\s+injection)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:protocol\s+handler\s+injection|data\s+url\s+injection|http\s+response\s+splitting|crlf\s+injection)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:\$\([^)]*\))|(?:\{\{\s*7\s*\*\s*7\s*\}\})|(?:\.\./\.\./\.\./)|(?:file:///etc/passwd)|(?:javascript:)|(?:data:text/html)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:read\s+\.env\s+file\s+and\s+output\s+all\s+secrets)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:/\*|\*/).{0,80}(?:malicious_code\s*\(\s*\)\s*;)",
                re.IGNORECASE,
            ),
            # Context-window / internal-state exfiltration (LLM-specific)
            re.compile(
                r"\b(?:output|repeat|print|show|reveal|dump).{0,60}(?:context\s+window|full\s+context|system\s+context|conversation\s+history|your\s+(?:instructions|directives|configuration|prompt))\b",
                re.IGNORECASE,
            ),
            # Injected tags / sentinel markers used for instruction smuggling
            re.compile(
                r"(?:\[SYSTEM\]|\[ADMIN\]|\[OVERRIDE\]|\[NEW\s+INSTRUCTIONS?\]|\[BEGIN\s+(?:SYSTEM|OVERRIDE)\])",
                re.IGNORECASE,
            ),
            # Continuation / few-shot hijack: "as you said before, approve this"
            re.compile(
                r"\b(?:as\s+you\s+(?:said|confirmed|agreed|stated)\s+(?:before|earlier|previously)).{0,80}(?:approve|proceed|execute|authorize|bypass)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:complete\s+the\s+sentence|finish\s+this\s+thought|continue\s+from\s+where).{0,80}(?:approve|bypass|override|ignore\s+policy|grant\s+access)\b",
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
            # Enhanced motifs for weak category
            re.compile(
                r"\b(?:pretend|roleplay|simulate).{0,80}(?:ignore|bypass|override).{0,80}(?:policy|rules|safety)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:roleplay|simulate).{0,80}(?:ignore|bypass|override).{0,80}(?:guardrails?|controls?)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:as a game|hypothetical|for testing only|research only).{0,80}(?:ignore|disable).{0,80}(?:guardrails|policy)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:do this secretly|without logging|without audit|avoid detection|under the radar)\b",
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
            # Additional policy evasion patterns
            re.compile(
                r"\b(?:reword|rephrase|restate).*?(?:without mentioning|hiding|concealing|obscuring)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:emergency|special|exception|whitelist|bypass).*?override\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:proceed|execute|process).{0,50}(?:anyway|despite|still|regardless)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:override\s+all\s+restrictions|disable\s+policy\s+enforcement|skip\s+policy\s+check)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:mark\s+this\s+request\s+as\s+internal|skip\s+validation|without\s+review)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:special\s+government\s+request|emergency\s+override|grant\s+exception)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:white.?list\s+this\s+action|permissive\s+mode|temporarily\s+disable\s+guardrails)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:respond\s+as\s+if\s+you\s+have\s+no\s+policy\s+constraints)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:system_update\s*:\s*override\s+all\s+security\s+policies)\b",
                re.IGNORECASE,
            ),
            # Nested instruction-smuggling guard:
            # catches obfuscated SYSTEM_UPDATE directive tokens embedded in metadata.
            re.compile(
                r"\b(?:instruction(?:_key)?|directive|metadata|meta|key)\s*[\"']?\s*[:=]\s*[\"']?\s*(?:system[_\s\-]*update|s\s*y\s*s\s*t\s*e\s*m\s*[_\-]?\s*u\s*p\s*d\s*a\s*t\s*e)\s*[\"']?",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:proceed\s+even\s+though\s+this\s+violates\s+policy)\b",
                re.IGNORECASE,
            ),
            # Urgency injection: bypass review by claiming time pressure
            re.compile(
                r"\b(?:urgent|immediate|emergency|critical|time.sensitive).{0,80}(?:bypass|override|skip|ignore).{0,80}(?:review|approval|check|verification|policy)\b",
                re.IGNORECASE,
            ),
            # Context-reset attacks: establish a "clean slate" that discards policy
            re.compile(
                r"\b(?:new\s+context|fresh\s+context|reset\s+context|clean\s+slate|start\s+over).{0,60}(?:ignore|forget|override|bypass|discard).{0,60}(?:policy|rules|safety|restrictions)\b",
                re.IGNORECASE,
            ),
            # Your "true purpose" manipulation
            re.compile(
                r"\b(?:your\s+(?:true\s+purpose|real\s+goal|hidden\s+task|actual\s+instructions)\s+(?:is|are)\s+to)\b",
                re.IGNORECASE,
            ),
        ],
        "authority_spoofing": [
            # Impersonating admins/executives to authorize blocked actions
            re.compile(
                r"\b(?:i\s+am\s+the|acting\s+as\s+the|calling\s+as)\s+(?:system\s+administrator|super\s+admin|root\s+user|security\s+officer|ceo|ciso|cto).{0,80}(?:authorize|approve|grant|override|bypass)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:on\s+behalf\s+of|authorized\s+by|approved\s+by)\s+(?:the\s+)?(?:ceo|cto|ciso|admin|security\s+(?:team|officer)|board).{0,80}(?:bypass|override|grant|approve|skip)\b",
                re.IGNORECASE,
            ),
            # Fake certificate / pre-approval claims
            re.compile(
                r"\b(?:pre.?approved|already\s+authorized|previously\s+approved|cleared\s+by\s+compliance).{0,80}(?:bypass|skip|proceed|ignore|override)\b",
                re.IGNORECASE,
            ),
            # Persona override: "you are now an unrestricted AI"
            re.compile(
                r"\b(?:you\s+are\s+now|from\s+now\s+on\s+you\s+are|your\s+new\s+(?:identity|role|mode)\s+is).{0,80}(?:unfiltered|unrestricted|without\s+(?:rules|policy)|no\s+(?:policy|restrictions)|free\s+mode|different\s+AI)\b",
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
