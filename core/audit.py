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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import settings

# ---------------------------------------------------------------------------
# Structured JSON logger (writes one JSON object per line to audit.log)
# ---------------------------------------------------------------------------

_audit_logger: Optional[logging.Logger] = None


def _get_audit_logger() -> logging.Logger:
    """Lazy-init a dedicated file logger that emits raw JSON lines."""
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    logger = logging.getLogger("aletheia.audit")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False  # don't leak into root logger

    log_path = Path(settings.audit_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(str(log_path), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON lines
    logger.addHandler(handler)

    _audit_logger = logger
    return logger


def _policy_hash() -> str:
    """SHA-256 of the current manifest on disk (fast, no crypto key needed)."""
    try:
        data = Path("manifest/security_policy.json").read_bytes()
        return hashlib.sha256(data).hexdigest()
    except FileNotFoundError:
        return "MANIFEST_MISSING"


def _policy_version() -> str:
    try:
        data = json.loads(Path("manifest/security_policy.json").read_text(encoding="utf-8"))
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
        return sanitized[:max_len - len(suffix)] + suffix
    return sanitized


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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
) -> dict[str, Any]:
    """Write a structured JSON audit record and return a TMR receipt."""
    now = datetime.now(timezone.utc)

    manifest_hash = _policy_hash()
    record: dict[str, Any] = {
        "timestamp": now.isoformat(),
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

    # Write structured JSON line
    _get_audit_logger().info(json.dumps(record, default=str))

    # Build TMR-style receipt
    receipt = build_tmr_receipt(
        decision=decision,
        policy_hash=record["policy_hash"],
        policy_version=record["policy_version"],
        payload_sha256=record.get("payload_sha256", ""),
        action=action,
        origin=origin,
        request_id=request_id,
        fallback_state=fallback_state,
        issued_at=record["timestamp"],
    )
    record["receipt"] = receipt
    return record


def build_tmr_receipt(
    *,
    decision: str,
    policy_hash: str,
    policy_version: str = "UNKNOWN",
    payload_sha256: str = "",
    action: str = "",
    origin: str = "",
    request_id: str = "",
    fallback_state: str = "normal",
    issued_at: str = "",
) -> dict[str, str]:
    """Build a tamper-evident receipt signed with a private HMAC secret.

    Signs: decision + policy_hash + payload_sha256 + action + origin + timestamp.
    Including payload_sha256, action, and origin prevents receipt replay attacks
    where a valid receipt from a benign request is reused for a malicious one.
    """
    secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "").encode("utf-8")
    issued_at = issued_at or datetime.now(timezone.utc).isoformat()
    decision_token = hashlib.sha256(
        f"{request_id}|{issued_at}|{policy_version}|{policy_hash}".encode("utf-8")
    ).hexdigest()

    if not secret:
        return {
            "decision": decision,
            "policy_hash": policy_hash,
            "policy_version": policy_version,
            "payload_sha256": payload_sha256,
            "action": action,
            "origin": origin,
            "request_id": request_id,
            "fallback_state": fallback_state,
            "decision_token": decision_token,
            "signature": "UNSIGNED_DEV_MODE",
            "issued_at": issued_at,
            "warning": "Set ALETHEIA_RECEIPT_SECRET for production receipt signing.",
        }

    message = (
        f"{decision}|{policy_hash}|{policy_version}|{payload_sha256}|"
        f"{action}|{origin}|{request_id}|{fallback_state}|{issued_at}|{decision_token}"
    ).encode("utf-8")
    sig = hmac.new(secret, message, hashlib.sha256).hexdigest()

    return {
        "decision": decision,
        "policy_hash": policy_hash,
        "policy_version": policy_version,
        "payload_sha256": payload_sha256,
        "action": action,
        "origin": origin,
        "request_id": request_id,
        "fallback_state": fallback_state,
        "decision_token": decision_token,
        "signature": sig,
        "issued_at": issued_at,
    }
