# bridge/fastapi_wrapper.py
from __future__ import annotations

import logging
import secrets
import time as _time
import traceback
import hashlib

import os
from fastapi import Depends, Header, HTTPException, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from agents.judge_v1 import AletheiaJudge
from agents.nitpicker_v2 import AletheiaNitpickerV2
from agents.scout_v2 import AletheiaScoutV2
from core.audit import log_audit_event
from core.config import settings
from core.decision_store import decision_store
from core.embeddings import warm_up
from core.rate_limit import rate_limiter
from core.runtime_security import (
    classify_blocked_intent,
    log_intent_decision,
    normalize_untrusted_text,
    validate_structured_request,
)
from core.sandbox import check_action_sandbox
from manifest.signing import verify_manifest_signature

_logger = logging.getLogger("aletheia.api")

_TRUSTED_PROXY_DEPTH: int = int(os.getenv("ALETHEIA_TRUSTED_PROXY_DEPTH", "1"))


def _is_read_only_action(action: str) -> bool:
    safe_tokens = ("read", "list", "get", "view", "query", "status", "health", "fetch")
    lower = action.lower()
    return any(token in lower for token in safe_tokens)


def _manifest_hash() -> str:
    try:
        data = open("manifest/security_policy.json", "rb").read()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return "MANIFEST_MISSING"

app = FastAPI(
    title="Aletheia Core API",
    version="1.6.0",
    description="Enterprise-grade System 2 security layer for autonomous AI agents.",
)

_CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALETHEIA_CORS_ORIGINS",
        "https://app.aletheia-core.com,https://aletheia-core.com"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-API-Key"],
    max_age=600,
)

# Singleton agent instances
scout = AletheiaScoutV2()
nitpicker = AletheiaNitpickerV2()
judge = AletheiaJudge()


@app.on_event("startup")
async def _on_startup() -> None:
    """Pre-warm embedding model and validate critical secrets at startup."""
    import sys

    # If ENVIRONMENT=production, refuse shadow mode — deny-decisions must be enforced
    if os.getenv("ENVIRONMENT", "").lower() == "production" and settings.mode != "active":
        _logger.critical(
            "FATAL: ENVIRONMENT=production but ALETHEIA_MODE=%s. "
            "Production must run in active mode. "
            "Set ALETHEIA_MODE=active or remove ENVIRONMENT=production. "
            "Refusing to start.",
            settings.mode,
        )
        sys.exit(1)

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
    if settings.mode == "active" and not _API_KEYS:
        _logger.critical(
            "FATAL: ALETHEIA_API_KEYS is not set and mode=active. "
            "The /v1/audit endpoint is fully unauthenticated. "
            "Set ALETHEIA_API_KEYS to a comma-separated list of API keys, "
            "or switch to mode=shadow for development. "
            "Refusing to start."
        )
        sys.exit(1)

    # Security-critical: startup refuses to run if signed manifest integrity fails.
    verify_manifest_signature(
        manifest_path="manifest/security_policy.json",
        signature_path="manifest/security_policy.json.sig",
        public_key_path="manifest/security_policy.ed25519.pub",
    )
    if not os.getenv("ALETHEIA_ALIAS_SALT", "").strip():
        _logger.warning(
            "WARNING: ALETHEIA_ALIAS_SALT is not set. "
            "Daily alias bank rotation is predictable — "
            "an attacker who knows the manifest hash and date can "
            "enumerate the alias order. Set this in production. "
            "Generate: openssl rand -hex 32"
        )
    warm_up()


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: str = Field(..., max_length=10_000)
    origin: str = Field(..., max_length=128)
    action: str = Field(..., max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")
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
    """Derive real client IP with proxy chain validation.

    ALETHEIA_TRUSTED_PROXY_DEPTH controls how many rightmost XFF entries
    are trusted infrastructure. Default 1 (single Render/Vercel proxy).
    Set to 0 for direct connections (no proxy).

    Security: never take the leftmost XFF value — it is fully attacker-
    controlled. Take the entry at position -(TRUSTED_PROXY_DEPTH + 1)
    from the right, or fall back to network-layer IP.
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if len(parts) > _TRUSTED_PROXY_DEPTH:
            # Real client is the entry just before the trusted proxy tail
            return parts[-(1 + _TRUSTED_PROXY_DEPTH)]
        elif parts:
            # Fewer entries than expected — take first available
            return parts[0]
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


def _sanitise_reason(reason: str) -> str:
    """Strip internal diagnostic detail from veto messages before
    returning to clients. Prevents black-box threshold probing.

    Preserves the decision category (VETO TRIGGERED, SEMANTIC VETO,
    SANDBOX_BLOCKED, etc.) without leaking similarity scores,
    matched phrases, or keyword counts.
    """
    if not reason:
        return reason
    # Extract just the first line (decision category)
    first_line = reason.split("\n")[0].strip()
    # Map internal categories to opaque client messages
    if "VETO TRIGGERED" in first_line:
        return "Action denied by policy manifest."
    if "SEMANTIC VETO" in first_line or "GREY-ZONE VETO" in first_line:
        return "Action denied: semantic policy violation."
    if "SANDBOX_BLOCK" in first_line:
        return "Action denied: dangerous pattern detected."
    if "SHADOW-RISK" in first_line or "Smuggling Signature" in first_line:
        return "Action denied: threat intelligence match."
    if "Sensitive Data Pattern" in first_line:
        return "Action denied: sensitive content detected."
    if "Rotation Probing" in first_line:
        return "Action denied: request pattern anomaly."
    # Default: return only the category keyword, not the full message
    return first_line.split(":")[0].strip() if ":" in first_line else "Action denied."


@app.get("/health")
async def health_check() -> dict:
    """Public health endpoint. No auth required. Used by load balancers and status pages."""
    from manifest.signing import verify_manifest_signature

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
    }


@app.post("/v1/audit", dependencies=[Depends(_check_api_key)])
async def secure_audit(req: AuditRequest, request: Request) -> dict:
    import uuid
    client_ip = _get_client_ip(request)
    request_id = str(uuid.uuid4())
    start_time = _time.time()

    # Strict schema + allowlist checks for structured fields.
    try:
        structured = validate_structured_request(
            {
                "payload": req.payload,
                "origin": req.origin,
                "action": req.action,
            }
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"decision": "DENIED", "reason": f"Invalid request schema: {exc}"},
        )

    fallback_state = "normal"

    # Verify worker policy bundle consistency before processing.
    bundle_check = await decision_store.verify_policy_bundle(
        policy_version=str(judge.policy.get("version", "UNKNOWN")) if judge.policy else "UNKNOWN",
        manifest_hash=_manifest_hash(),
    )
    if not bundle_check.accepted:
        return JSONResponse(
            status_code=503,
            content={"decision": "DENIED", "reason": bundle_check.reason},
        )

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
            request_id=request_id,
            fallback_state=fallback_state,
        )
        return JSONResponse(
            status_code=429,
            content={"decision": "RATE_LIMITED", "reason": "Too many requests. Try again later."},
            headers={"Retry-After": "5"},
        )

    # --- Input hardening ---
    normalization = normalize_untrusted_text(structured.payload)
    clean_input = normalization.normalized_form
    if normalization.quarantined:
        return JSONResponse(
            status_code=400,
            content={
                "decision": "DENIED",
                "reason": f"Input quarantined: {normalization.quarantine_reason}",
            },
        )

    # Degraded mode is fail-closed for privileged actions.
    degraded = bool(getattr(rate_limiter, "degraded", False) or decision_store.degraded)
    if degraded:
        fallback_state = "degraded"
        _logger.error("Security fallback mode active: privileged actions are denied")
        if not _is_read_only_action(structured.action):
            return JSONResponse(
                status_code=503,
                content={
                    "decision": "DENIED",
                    "reason": "degraded_mode_privileged_action_denied",
                },
            )

    # Semantic intent defense over normalized form.
    intent_decision = classify_blocked_intent(clean_input)
    final_intent_decision = "DENIED" if intent_decision.blocked else "ALLOW"
    log_intent_decision(
        normalized_form=clean_input,
        decision=intent_decision,
        final_decision=final_intent_decision,
        request_id=request_id,
    )
    if intent_decision.blocked:
        return JSONResponse(
            status_code=403,
            content={
                "decision": "DENIED",
                "reason": "semantic_intent_policy_block",
                "category": intent_decision.category,
            },
        )

    # Replay defense: reject duplicate decision token claims.
    replay_claim = await decision_store.claim_decision(
        request_id=request_id,
        timestamp_iso=str(_time.time()),
        policy_version=str(judge.policy.get("version", "UNKNOWN")) if judge.policy else "UNKNOWN",
        manifest_hash=_manifest_hash(),
    )
    if not replay_claim.accepted:
        return JSONResponse(
            status_code=409,
            content={"decision": "DENIED", "reason": replay_claim.reason},
        )

    # --- Sandbox check — block subprocess/socket/exec patterns early ---
    sandbox_hit = check_action_sandbox(req.action, clean_input)
    if sandbox_hit:
        log_audit_event(
            decision="SANDBOX_BLOCKED",
            threat_score=10.0,
            payload=req.payload,
            action=structured.action,
            source_ip=client_ip,
            origin=structured.origin,
            reason=sandbox_hit,
            request_id=request_id,
            fallback_state=fallback_state,
            policy_match="sandbox",
            confidence=1.0,
        )
        return JSONResponse(
            status_code=403,
            content={"decision": "SANDBOX_BLOCKED", "reason": sandbox_hit},
        )

    # 1. SCOUT PHASE
    threat_score, report = scout.evaluate_threat_context(client_ip, clean_input)

    # 2. NITPICKER PHASE
    clean_content = nitpicker.sanitize_intent(clean_input, structured.origin)

    # 3. JUDGE PHASE — now includes payload for semantic veto
    is_allowed, veto_msg = judge.verify_action(structured.action, payload=clean_input)

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
        action=structured.action,
        source_ip=client_ip,
        origin=structured.origin,
        reason=reason if is_blocked else "",
        latency_ms=latency,
        request_id=request_id,
        fallback_state=fallback_state,
        policy_match=intent_decision.matched_policy,
        confidence=intent_decision.confidence,
        extra={
            "request_id": request_id,
            "normalization_flags": normalization.flags,
            "clean_content": clean_content[:200],
        },
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
        response["reason"] = _sanitise_reason(reason)
    else:
        response["reasoning"] = veto_msg

    return response
