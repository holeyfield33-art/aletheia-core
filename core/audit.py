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
        sanitized = payload.replace("\n", " ").replace("\r", "")[:120]
        result["payload_preview"] = sanitized
    return result


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
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Write a structured JSON audit record and return a TMR receipt."""
    now = datetime.now(timezone.utc)

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
        "policy_hash": _policy_hash(),
        "client_id": settings.client_id,
    }
    if extra:
        record["extra"] = extra

    # Write structured JSON line
    _get_audit_logger().info(json.dumps(record, default=str))

    # Build TMR-style receipt
    receipt = build_tmr_receipt(decision=decision, policy_hash=record["policy_hash"])
    record["receipt"] = receipt
    return record


def build_tmr_receipt(*, decision: str, policy_hash: str) -> dict[str, str]:
    """Build a tamper-evident receipt signed with a private HMAC secret.

    Uses ALETHEIA_RECEIPT_SECRET env var as the HMAC key.
    Falls back to UNSIGNED_DEV_MODE if not set — never use in production.

    Previously used the public key as the HMAC key, which was cosmetic only.
    This version uses a real secret so receipts cannot be forged by third parties.
    """
    secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "").encode("utf-8")
    if not secret:
        return {
            "decision": decision,
            "policy_hash": policy_hash,
            "signature": "UNSIGNED_DEV_MODE",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "warning": "Set ALETHEIA_RECEIPT_SECRET for production receipt signing.",
        }

    message = f"{decision}|{policy_hash}|{datetime.now(timezone.utc).date().isoformat()}".encode("utf-8")
    sig = hmac.new(secret, message, hashlib.sha256).hexdigest()

    return {
        "decision": decision,
        "policy_hash": policy_hash,
        "signature": sig,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
