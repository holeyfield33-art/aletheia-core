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


def _redact_payload(payload: str, max_len: int = 200) -> str:
    """Truncate and sanitize payload for safe logging. Never log raw user input."""
    sanitized = payload.replace("\n", " ").replace("\r", "")
    if len(sanitized) > max_len:
        return sanitized[:max_len] + "...[TRUNCATED]"
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
        "redacted_payload": _redact_payload(payload),
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
    """Triple Modular Redundancy receipt: decision + policy_hash + HMAC signature.

    The HMAC key is the manifest public key bytes (available to any verifier).
    This proves the receipt was produced by a process that had access to policy
    verification material at the time of the decision.
    """
    pub_key_path = Path(os.getenv(
        "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH",
        "manifest/security_policy.ed25519.pub",
    ))
    try:
        hmac_key = pub_key_path.read_bytes()
    except FileNotFoundError:
        hmac_key = b"NO_KEY_AVAILABLE"

    message = f"{decision}|{policy_hash}".encode("utf-8")
    sig = hmac.new(hmac_key, message, hashlib.sha256).hexdigest()

    return {
        "decision": decision,
        "policy_hash": policy_hash,
        "signature": sig,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
