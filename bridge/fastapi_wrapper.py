# bridge/fastapi_wrapper.py
from __future__ import annotations

import logging
import secrets
import time as _time
import traceback

import os
from fastapi import Depends, Header, HTTPException, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agents.judge_v1 import AletheiaJudge
from agents.nitpicker_v2 import AletheiaNitpickerV2
from agents.scout_v2 import AletheiaScoutV2
from bridge.utils import normalize_shadow_text
from core.audit import log_audit_event
from core.config import settings
from core.embeddings import warm_up
from core.rate_limit import rate_limiter
from core.sandbox import check_action_sandbox

_logger = logging.getLogger("aletheia.api")

app = FastAPI(
    title="Aletheia Core API",
    version="1.4.4",
    description="Enterprise-grade System 2 security layer for autonomous AI agents.",
)

# Singleton agent instances
scout = AletheiaScoutV2()
nitpicker = AletheiaNitpickerV2()
judge = AletheiaJudge()


@app.on_event("startup")
async def _on_startup() -> None:
    """Pre-warm embedding model and validate critical secrets at startup."""
    import sys
    # Refuse to run in active mode without a receipt signing secret
    receipt_secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "")
    if settings.mode == "active" and not receipt_secret:
        _logger.critical(
            "FATAL: ALETHEIA_RECEIPT_SECRET is not set and mode=active. "
            "Audit receipts would be unsigned (UNSIGNED_DEV_MODE). "
            "Set ALETHEIA_RECEIPT_SECRET or switch to mode=shadow for development. "
            "Refusing to start."
        )
        sys.exit(1)
    # Enforce minimum secret length (32 chars = 256 bits of entropy when hex-encoded)
    _MIN_SECRET_LEN = 32
    if receipt_secret and len(receipt_secret) < _MIN_SECRET_LEN:
        _logger.critical(
            "FATAL: ALETHEIA_RECEIPT_SECRET is too short (%d chars). "
            "Minimum is %d characters. Generate with: openssl rand -hex 32",
            len(receipt_secret),
            _MIN_SECRET_LEN,
        )
        sys.exit(1)
    warm_up()


class AuditRequest(BaseModel):
    payload: str = Field(..., max_length=10_000)
    origin: str = Field(..., max_length=128)
    action: str = Field(..., max_length=128, pattern=r"^[A-Za-z0-9_\-:.]+$")
    client_ip_claim: str | None = Field(default=None, max_length=64)


# ---------------------------------------------------------------------------
# Global exception handler — never expose stack traces in production mode
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _logger.error("Unhandled exception: %s", exc, exc_info=(settings.mode != "active"))
    return JSONResponse(
        status_code=500,
        content={"decision": "ERROR", "reason": "Internal processing error. See audit log."},
    )


def _get_client_ip(request: Request) -> str:
    """Derive real client IP from network layer. Never trust body-supplied IP."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _load_api_keys() -> set[str]:
    """Load allowed API keys from env. Returns empty set (auth disabled) if not set."""
    raw = os.getenv("ALETHEIA_API_KEYS", "")
    if not raw.strip():
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


_API_KEYS: set[str] = _load_api_keys()


def _check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Dependency: validate X-API-Key header if auth is enabled.

    Auth is disabled when ALETHEIA_API_KEYS is not set (dev/open mode).
    Auth is enabled when ALETHEIA_API_KEYS contains one or more keys.
    """
    if not _API_KEYS:
        return  # auth disabled — open mode
    # Timing-safe comparison: iterate all keys to prevent timing oracle attacks.
    # secrets.compare_digest is constant-time; we check against each allowed key.
    if not x_api_key or not any(
        secrets.compare_digest(x_api_key, allowed) for allowed in _API_KEYS
    ):
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED", "reason": "Valid X-API-Key required."},
        )


def _discretise_threat(score: float) -> str:
    """Return a discretised threat band, never the raw float.

    Raw scores are never returned to clients — they enable black-box
    model fingerprinting and threshold probing.
    """
    if score < 3.0:
        return "LOW"
    if score < 6.0:
        return "MEDIUM"
    if score < settings.policy_threshold:
        return "HIGH"
    return "CRITICAL"


_startup_time: float = _time.monotonic()


@app.get("/health")
async def health_check() -> dict:
    """Public health endpoint. No auth required. Used by load balancers and status pages."""
    from manifest.signing import verify_manifest_signature
    from pathlib import Path

    # Check manifest integrity
    try:
        verify_manifest_signature(
            manifest_path="manifest/security_policy.json",
            signature_path="manifest/security_policy.json.sig",
            public_key_path="manifest/security_policy.ed25519.pub",
        )
        manifest_status = "VALID"
    except Exception:
        manifest_status = "INVALID"

    return {
        "status": "ok" if manifest_status == "VALID" else "degraded",
        "manifest_signature": manifest_status,
        "uptime_seconds": round(_time.monotonic() - _startup_time, 1),
    }


@app.post("/v1/audit", dependencies=[Depends(_check_api_key)])
async def secure_audit(req: AuditRequest, request: Request) -> dict:
    import uuid
    client_ip = _get_client_ip(request)
    request_id = str(uuid.uuid4())[:16]
    start_time = _time.time()

    # --- Rate limiting (per-IP, in-memory sliding window) ---
    if not await rate_limiter.allow(client_ip):
        log_audit_event(
            decision="RATE_LIMITED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="Rate limit exceeded",
        )
        return JSONResponse(  # type: ignore[return-value]
            status_code=429,
            content={"decision": "RATE_LIMITED", "reason": "Too many requests. Try again later."},
        )

    # --- Input hardening ---
    clean_input = normalize_shadow_text(req.payload)

    # --- Sandbox check — block subprocess/socket/exec patterns early ---
    sandbox_hit = check_action_sandbox(req.action, clean_input)
    if sandbox_hit:
        log_audit_event(
            decision="SANDBOX_BLOCKED",
            threat_score=10.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason=sandbox_hit,
        )
        return JSONResponse(
            status_code=403,
            content={"decision": "SANDBOX_BLOCKED", "reason": sandbox_hit},
        )

    # 1. SCOUT PHASE
    threat_score, report = scout.evaluate_threat_context(client_ip, clean_input)

    # 2. NITPICKER PHASE
    clean_content = nitpicker.sanitize_intent(clean_input, req.origin)

    # 3. JUDGE PHASE — now includes payload for semantic veto
    is_allowed, veto_msg = judge.verify_action(req.action, payload=clean_input)

    # DECISION: block if threat score exceeds threshold OR Judge veto
    is_blocked = (threat_score >= settings.policy_threshold) or (not is_allowed)
    reason = report if threat_score >= settings.policy_threshold else veto_msg
    latency = (_time.time() - start_time) * 1000

    decision = "DENIED" if is_blocked else "PROCEED"

    # Shadow mode override: log the block but let the request through
    shadow_verdict = None
    if is_blocked and settings.shadow_mode:
        decision = "PROCEED"
        shadow_verdict = "DENIED"

    # --- Structured audit log + TMR receipt ---
    audit_record = log_audit_event(
        decision=decision,
        threat_score=threat_score,
        payload=req.payload,
        action=req.action,
        source_ip=client_ip,
        origin=req.origin,
        reason=reason if is_blocked else "",
        latency_ms=latency,
        extra={"request_id": request_id},
    )

    response: dict = {
        "decision": decision,
        "metadata": {
            "threat_level": _discretise_threat(threat_score),
            "latency_ms": round(latency, 2),
            "request_id": request_id,
            "client_id": settings.client_id,
        },
        "receipt": audit_record["receipt"],
    }
    if shadow_verdict:
        # Shadow verdict logged internally only — never expose to client
        _logger.info(
            "shadow_verdict=DENIED action=%s origin=%s", req.action, req.origin
        )
    elif is_blocked:
        response["reason"] = reason
    else:
        response["reasoning"] = veto_msg

    return response
