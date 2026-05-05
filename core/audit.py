# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Structured audit logging and TMR-style receipts.

Every audit decision is:
1. Written as a JSON line to the configured audit log file.
2. Returned as a cryptographic TMR receipt (decision + policy_hash + HMAC).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from core.config import settings

# ---------------------------------------------------------------------------
# PII redaction — applied before writing audit log entries
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
]


def redact_pii(text: str) -> str:
    """Replace PII patterns with redacted placeholders.

    PII is always redacted — no override is permitted.
    Uses a random nonce per redaction to prevent rainbow-table
    reconstruction of the original value from the fingerprint.
    """
    for label, pattern in _PII_PATTERNS:

        def _replacer(m: re.Match[str], _label: str = label) -> str:
            nonce = os.urandom(4).hex()
            return f"[REDACTED:{_label}:{nonce}]"

        text = pattern.sub(_replacer, text)
    return text


# ---------------------------------------------------------------------------
# Structured JSON logger (writes one JSON object per line to audit.log)
# ---------------------------------------------------------------------------

_audit_logger: Optional[logging.Logger] = None

# ---------------------------------------------------------------------------
# Hash-chain state — each audit record includes a hash of the prior record
# so that deletion, reordering, or tampering is detectable.
# ---------------------------------------------------------------------------
_prev_record_hash: str = "GENESIS"
_audit_seq: int = 0
import threading as _threading  # noqa: E402

_chain_lock = _threading.Lock()
_receipt_chain_lock = _threading.Lock()
_prev_receipt_chain_hash: str = "GENESIS"
_receipt_chain_seq: int = 0


def _next_receipt_chain(record_hash: str) -> tuple[int, str]:
    """Advance the public receipt chain and return (index, hash)."""
    global _prev_receipt_chain_hash, _receipt_chain_seq

    with _receipt_chain_lock:
        _receipt_chain_seq += 1
        index = _receipt_chain_seq
        chain_hash = hashlib.sha256(
            f"{_prev_receipt_chain_hash}|{record_hash}|{index}".encode("utf-8")
        ).hexdigest()
        _prev_receipt_chain_hash = chain_hash
        return index, chain_hash


def _load_last_audit_record(log_path: Path) -> Optional[dict[str, Any]]:
    """Best-effort fetch of the most recent valid JSON audit record.

    Reads only the tail of the file to avoid loading large logs into memory.
    """
    if not log_path.exists():
        return None

    try:
        with log_path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size <= 0:
                return None

            read_size = min(size, 1_048_576)  # 1 MiB tail scan
            fh.seek(-read_size, os.SEEK_END)
            tail = fh.read(read_size)
    except OSError:
        return None

    for raw_line in reversed(tail.splitlines()):
        if not raw_line.strip():
            continue
        try:
            parsed = json.loads(raw_line.decode("utf-8"))
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _bootstrap_chain_state(log_path: Path) -> None:
    """Initialize in-memory chain cursor from the latest persisted audit record."""
    global _prev_record_hash, _audit_seq

    last_record = _load_last_audit_record(log_path)
    if not last_record:
        with _chain_lock:
            _prev_record_hash = "GENESIS"
            _audit_seq = 0
        return

    last_hash = last_record.get("record_hash")
    raw_seq = last_record.get("seq", 0)
    try:
        seq = int(raw_seq)
    except (TypeError, ValueError):
        seq = 0

    with _chain_lock:
        _prev_record_hash = (
            last_hash if isinstance(last_hash, str) and last_hash else "GENESIS"
        )
        _audit_seq = max(0, seq)


def _get_audit_logger() -> logging.Logger:
    """Lazy-init a dedicated file logger that emits raw JSON lines."""
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    logger = logging.getLogger("aletheia.audit")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False  # don't leak into root logger

    log_path = Path(settings.audit_log_path)
    # Security: forbid path traversal in audit log path
    if ".." in log_path.parts:
        raise ValueError(
            f"Invalid audit_log_path: '{settings.audit_log_path}' — "
            "must not contain '..' components"
        )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(str(log_path), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON lines
    logger.addHandler(handler)

    # Restrict audit log file permissions (owner read/write only)
    try:
        import stat

        log_path.touch(exist_ok=True)
        log_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except OSError:
        pass  # best-effort on platforms that don't support chmod

    # Recover hash-chain cursor on process start/restart.
    _bootstrap_chain_state(log_path)

    _audit_logger = logger
    return logger


def _policy_hash() -> str:
    """SHA-256 of the current manifest on disk (fast, no crypto key needed)."""
    try:
        data = Path("manifest/security_policy.json").read_bytes()
        return hashlib.sha256(data).hexdigest()
    except FileNotFoundError:
        if settings.mode == "active":
            raise RuntimeError(
                "FATAL: manifest/security_policy.json missing — "
                "cannot produce audit records in active mode"
            )
        return "MANIFEST_MISSING"


def _policy_version() -> str:
    try:
        data = json.loads(
            Path("manifest/security_policy.json").read_text(encoding="utf-8")
        )
        return str(data.get("version", "UNKNOWN"))
    except Exception:
        return "UNKNOWN"


def _hash_payload(payload: str) -> dict[str, str | int]:
    """Return payload fingerprint for audit log. Never store raw user input in prod.

    In active mode: SHA-256 hash + length only (no content).
    In shadow/debug mode: adds a short sanitized preview.
    """
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    result: dict[str, str | int] = {
        "payload_sha256": sha,
        "payload_length": len(payload),
    }
    if settings.mode != "active":
        result["payload_preview"] = safe_payload_preview(payload)
    return result


def safe_payload_preview(payload: str, max_len: int = 120) -> str:
    """Return a truncated, control-character-stripped preview of a payload.

    Safe for inclusion in logs and diagnostic output — never returns raw
    user input and always truncates to *max_len* characters.
    """
    sanitized = payload.replace("\n", " ").replace("\r", "").replace("\t", " ")
    if len(sanitized) > max_len:
        suffix = "...[TRUNCATED]"
        return sanitized[: max_len - len(suffix)] + suffix
    return sanitized


def extract_trace_context() -> dict[str, str]:
    """Extract OTel trace context if opentelemetry is available.

    Returns a dict with ``trace_id`` and ``span_id`` (hex strings) when
    an active OTel span exists, or an empty dict otherwise.
    Lightweight — never raises, never imports heavy dependencies at module level.
    """
    try:
        from opentelemetry import trace  # type: ignore[import-untyped,unused-ignore]

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class Receipt(BaseModel):
    """Canonical TMR receipt payload used for signing and verification."""

    decision: str
    reason: str = ""
    policy_hash: str
    policy_version: str = "UNKNOWN"
    payload_sha256: str = ""
    prompt: Optional[str] = None
    action: str = ""
    origin: str = ""
    request_id: str = ""
    fallback_state: str = "normal"
    decision_token: str
    nonce: str
    issued_at: str
    timestamp: str = ""
    chain_index: int = 0
    chain_hash: str = ""
    signature: str = ""
    warning: Optional[str] = Field(default=None)
    signature_algorithm: str = "hmac-sha256"
    key_id: Optional[str] = Field(default=None)

    @field_validator("prompt")
    @classmethod
    def _validate_prompt_length(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 4096:
            raise ValueError("prompt must be <= 4096 characters")
        return value

    def _canonical_string(self) -> str:
        """Canonical string used for signing.

        For backward compatibility with pre-migration HMAC receipts, the
        signature_algorithm and key_id fields are appended only when
        signature_algorithm is not the legacy default or key_id is present.
        """
        canonical = (
            f"{self.decision}|{self.policy_hash}|{self.policy_version}|"
            f"{self.payload_sha256}"
        )
        if self.prompt is not None:
            canonical += f"|prompt:{self.prompt}"
        canonical += (
            f"|{self.action}|{self.origin}|{self.request_id}|"
            f"{self.fallback_state}|{self.issued_at}|"
            f"{self.decision_token}|{self.nonce}"
        )
        # Keep backward compatibility: include extended fields only when present.
        if self.reason or self.timestamp or self.chain_index > 0 or self.chain_hash:
            canonical += (
                f"|reason:{self.reason}|ts:{self.timestamp}|"
                f"chain_index:{self.chain_index}|chain_hash:{self.chain_hash}"
            )
        if self.signature_algorithm != "hmac-sha256" or self.key_id:
            canonical += f"|alg:{self.signature_algorithm}"
            if self.key_id:
                canonical += f"|kid:{self.key_id}"
        return canonical


def log_audit_event(
    *,
    decision: str,
    threat_score: float,
    payload: str,
    action: str,
    source_ip: str,
    origin: str,
    reason: str = "",
    latency_ms: float = 0.0,
    request_id: str = "",
    fallback_state: str = "normal",
    policy_match: str = "",
    confidence: float = 0.0,
    replay_token_outcome: str = "",
    status_code: int = 0,
    extra: Optional[dict[str, Any]] = None,
    receipt_chain: bool = False,
    tenant_id: str = "default",
    user_id: str = "",
    auth_method: str = "",
) -> dict[str, Any]:
    """Write a structured JSON audit record and return a TMR receipt."""
    global _prev_record_hash, _audit_seq
    now = datetime.now(timezone.utc)

    manifest_hash = _policy_hash()

    with _chain_lock:
        _audit_seq += 1
        seq = _audit_seq
        prev_hash = _prev_record_hash

    record: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "seq": seq,
        "prev_hash": prev_hash,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "auth_method": auth_method,
        "decision": decision,
        "threat_score": threat_score,
        "action": action,
        "source_ip": source_ip,
        "origin": origin,
        "reason": reason,
        "latency_ms": round(latency_ms, 2),
        **_hash_payload(payload),
        "policy_hash": manifest_hash,
        "manifest_fingerprint": manifest_hash[:16] if manifest_hash else "",
        "policy_version": _policy_version(),
        "client_id": settings.client_id,
        "request_id": request_id,
        "fallback_state": fallback_state,
        "policy_match": policy_match,
        "confidence": confidence,
    }
    if replay_token_outcome:
        record["replay_token_outcome"] = replay_token_outcome
    if status_code:
        record["status_code"] = status_code
    if extra:
        record["extra"] = extra

    # OTel trace context (when opentelemetry is installed)
    trace_ctx = extract_trace_context()
    if trace_ctx:
        record["trace_id"] = trace_ctx["trace_id"]
        record["span_id"] = trace_ctx["span_id"]

    # PII redaction: scrub string fields before writing to audit log
    for key in ("reason", "origin", "action"):
        if isinstance(record.get(key), str):
            record[key] = redact_pii(record[key])

    # Compute record hash for chain integrity
    record_json = json.dumps(record, sort_keys=True, default=str)
    record_hash = hashlib.sha256(record_json.encode("utf-8")).hexdigest()
    record["record_hash"] = record_hash

    # Update chain state
    with _chain_lock:
        _prev_record_hash = record_hash

    # Write structured JSON line
    _get_audit_logger().info(json.dumps(record, default=str))

    # --- Task 4: Dispatch to external exporters + WebSocket broadcast ---
    try:
        from core.metrics import TENANT_REQUESTS

        TENANT_REQUESTS.labels(tenant_id=tenant_id, verdict=decision).inc()
    except Exception:
        pass

    try:
        from core.exporters import enqueue_audit_record

        enqueue_audit_record(record)
    except Exception:
        pass  # exporters are optional — never block the audit pipeline

    try:
        from core.ws_audit import audit_broadcast

        audit_broadcast.publish(record)
    except Exception:
        pass  # WS broadcast is optional

    # Build TMR-style receipt
    receipt_chain_index = 0
    receipt_chain_hash = ""
    if receipt_chain:
        receipt_chain_index, receipt_chain_hash = _next_receipt_chain(record_hash)

    receipt = build_tmr_receipt(
        decision=decision,
        reason=record.get("reason", ""),
        policy_hash=record["policy_hash"],
        policy_version=record["policy_version"],
        payload_sha256=record.get("payload_sha256", ""),
        prompt=redact_pii(payload),
        action=action,
        origin=origin,
        request_id=request_id,
        fallback_state=fallback_state,
        issued_at=record["timestamp"],
        timestamp=record["timestamp"],
        chain_index=receipt_chain_index,
        chain_hash=receipt_chain_hash,
    )
    record["receipt"] = receipt
    return record


def build_tmr_receipt(
    *,
    decision: str,
    reason: str = "",
    policy_hash: str,
    policy_version: str = "UNKNOWN",
    payload_sha256: str = "",
    prompt: Optional[str] = None,
    action: str = "",
    origin: str = "",
    request_id: str = "",
    fallback_state: str = "normal",
    issued_at: str = "",
    timestamp: str = "",
    chain_index: int = 0,
    chain_hash: str = "",
) -> dict[str, Any]:
    """Build a tamper-evident receipt.

    Signs with Ed25519 if ALETHEIA_RECEIPT_PRIVATE_KEY is configured;
    falls back to HMAC-SHA256 if only ALETHEIA_RECEIPT_SECRET is set.
    Returns an unsigned receipt with a warning if neither is configured.
    """
    from core import receipt_keys

    issued_at = issued_at or datetime.now(timezone.utc).isoformat()
    nonce = os.urandom(16).hex()
    decision_token = hashlib.sha256(
        f"{request_id}|{issued_at}|{policy_version}|{policy_hash}|{nonce}".encode(
            "utf-8"
        )
    ).hexdigest()

    receipt_payload: dict[str, Any] = {
        "decision": decision,
        "reason": reason,
        "policy_hash": policy_hash,
        "policy_version": policy_version,
        "payload_sha256": payload_sha256,
        "action": action,
        "origin": origin,
        "request_id": request_id,
        "fallback_state": fallback_state,
        "decision_token": decision_token,
        "nonce": nonce,
        "issued_at": issued_at,
        "timestamp": timestamp or issued_at,
        "chain_index": chain_index,
        "chain_hash": chain_hash,
    }
    if prompt is not None:
        receipt_payload["prompt"] = prompt

    if receipt_keys.is_configured():
        receipt_payload["signature_algorithm"] = "ed25519"
        receipt_payload["key_id"] = receipt_keys.key_id()

        receipt = Receipt.model_validate(receipt_payload)
        priv = receipt_keys.load_private_key()
        sig_bytes = priv.sign(receipt._canonical_string().encode("utf-8"))

        signed: dict[str, Any] = receipt.model_dump(exclude_none=True)
        signed["signature"] = sig_bytes.hex()
        return signed

    secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "").encode("utf-8")
    receipt_payload["signature_algorithm"] = "hmac-sha256"

    receipt = Receipt.model_validate(receipt_payload)

    if not secret:
        unsigned = receipt.model_dump(exclude_none=True)
        unsigned["signature"] = "UNSIGNED_DEV_MODE"
        unsigned["warning"] = (
            "Set ALETHEIA_RECEIPT_PRIVATE_KEY (preferred) or "
            "ALETHEIA_RECEIPT_SECRET (legacy) for production receipt signing."
        )
        return dict(unsigned)

    sig = hmac.new(
        secret,
        receipt._canonical_string().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    signed: dict[str, Any] = receipt.model_dump(exclude_none=True)
    signed["signature"] = sig
    return signed


def verify_receipt(receipt: dict[str, Any]) -> bool:
    """Verify a TMR receipt signature.

    Algorithm dispatched by receipt['signature_algorithm']:
      - "ed25519": verify with public key from receipt_keys
      - "hmac-sha256" (default for legacy receipts): verify with
        ALETHEIA_RECEIPT_SECRET
    """

    provided_sig = receipt.get("signature")
    if not isinstance(provided_sig, str) or not provided_sig:
        return False
    if provided_sig == "UNSIGNED_DEV_MODE":
        return False

    try:
        parsed = Receipt.model_validate(receipt)
    except Exception:
        return False

    algorithm = parsed.signature_algorithm

    if algorithm == "ed25519":
        from cryptography.exceptions import InvalidSignature
        from core import receipt_keys

        try:
            pub = receipt_keys.load_public_key()
        except receipt_keys.ReceiptKeyError:
            return False
        try:
            sig_bytes = bytes.fromhex(provided_sig)
        except ValueError:
            return False
        try:
            pub.verify(sig_bytes, parsed._canonical_string().encode("utf-8"))
            return True
        except InvalidSignature:
            return False

    if algorithm == "hmac-sha256":
        secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "").encode("utf-8")
        if not secret:
            return False

        expected_sig = hmac.new(
            secret,
            parsed._canonical_string().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(provided_sig, expected_sig)

    return False
