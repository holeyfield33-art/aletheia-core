# bridge/fastapi_wrapper.py
from __future__ import annotations

import logging
import time
import traceback

from fastapi import FastAPI, Request
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
    version="1.3.0",
    description="Enterprise-grade System 2 security layer for autonomous AI agents.",
)

# Singleton agent instances
scout = AletheiaScoutV2()
nitpicker = AletheiaNitpickerV2()
judge = AletheiaJudge()


@app.on_event("startup")
async def _on_startup() -> None:
    """Pre-warm the embedding model to eliminate cold-start latency."""
    warm_up()


class AuditRequest(BaseModel):
    payload: str = Field(..., max_length=10_000)
    origin: str
    action: str
    ip: str


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


@app.post("/v1/audit")
async def secure_audit(req: AuditRequest) -> dict:
    start_time = time.time()

    # --- Rate limiting (per-IP, in-memory sliding window) ---
    if not rate_limiter.allow(req.ip):
        log_audit_event(
            decision="RATE_LIMITED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=req.ip,
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
            source_ip=req.ip,
            origin=req.origin,
            reason=sandbox_hit,
        )
        return JSONResponse(
            status_code=403,
            content={"decision": "SANDBOX_BLOCKED", "reason": sandbox_hit},
        )

    # 1. SCOUT PHASE
    threat_score, report = scout.evaluate_threat_context(req.ip, clean_input)

    # 2. NITPICKER PHASE
    clean_content = nitpicker.sanitize_intent(clean_input, req.origin)

    # 3. JUDGE PHASE — now includes payload for semantic veto
    is_allowed, veto_msg = judge.verify_action(req.action, payload=clean_input)

    # DECISION: block if threat score exceeds threshold OR Judge veto
    is_blocked = (threat_score >= settings.policy_threshold) or (not is_allowed)
    reason = report if threat_score >= settings.policy_threshold else veto_msg
    latency = (time.time() - start_time) * 1000

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
        source_ip=req.ip,
        origin=req.origin,
        reason=reason if is_blocked else "",
        latency_ms=latency,
    )

    response: dict = {
        "decision": decision,
        "metadata": {
            "threat_level": threat_score,
            "latency_ms": round(latency, 2),
            "redacted_payload": clean_content if decision == "PROCEED" else "BLOCK_ACTIVE",
            "client_id": settings.client_id,
        },
        "receipt": audit_record["receipt"],
    }
    if shadow_verdict:
        response["shadow_verdict"] = shadow_verdict
        response["reason"] = reason
    elif is_blocked:
        response["reason"] = reason
    else:
        response["reasoning"] = veto_msg

    return response
