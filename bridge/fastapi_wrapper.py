# bridge/fastapi_wrapper.py
from __future__ import annotations

import logging
import secrets
import time as _time
import traceback

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import Depends, Header, HTTPException, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from agents.judge_v1 import AletheiaJudge
from agents.nitpicker_v2 import AletheiaNitpickerV2
from agents.scout_v2 import AletheiaScoutV2
from bridge.utils import normalize_shadow_text
from core.audit import log_audit_event
from core.config import settings
from core.embeddings import warm_up
from core.rate_limit import rate_limiter
from core.sandbox import check_action_sandbox
from core.decision_store import decision_store
from core.runtime_security import classify_blocked_intent
from core.key_store import key_store, DEFAULT_QUOTAS

_logger = logging.getLogger("aletheia.api")

_TRUSTED_PROXY_DEPTH: int = int(os.getenv("ALETHEIA_TRUSTED_PROXY_DEPTH", "1"))

app = FastAPI(
    title="Aletheia Core API",
    version="1.6.0",
    description="Enterprise-grade System 2 security layer for autonomous AI agents.",
)

_BOOT_TIME = _time.time()

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
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "X-Admin-Key"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Security + rate limit headers middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_and_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    # Rate limit headers
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
    if hasattr(request.state, "retry_after"):
        response.headers["Retry-After"] = str(request.state.retry_after)
    return response


# ---------------------------------------------------------------------------
# Admin-key dependency for key management endpoints
# ---------------------------------------------------------------------------

def _check_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    """Require X-Admin-Key header for key management operations."""
    admin_key = os.getenv("ALETHEIA_ADMIN_KEY", "").strip()
    if not admin_key:
        raise HTTPException(
            status_code=503,
            detail={"error": "key_management_unavailable",
                     "message": "Key management is not configured. Set ALETHEIA_ADMIN_KEY."},
        )
    if not x_admin_key or not secrets.compare_digest(x_admin_key, admin_key):
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Valid X-Admin-Key required."},
        )


# ---------------------------------------------------------------------------
# Key management request models
# ---------------------------------------------------------------------------

class CreateKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=64)
    plan: str = Field(default="trial", pattern=r"^(trial|pro)$")


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
    """Dependency: validate X-API-Key header and enforce quota.

    Auth is disabled when ALETHEIA_API_KEYS is not set (dev/open mode).
    Auth is enabled when ALETHEIA_API_KEYS contains one or more keys.

    Two key sources are checked in order:
    1. Environment keys (``ALETHEIA_API_KEYS``) — admin / demo keys, no quota.
    2. Key store (SQLite) — trial / pro keys with monthly quota enforcement.
    """
    if not _API_KEYS:
        return  # auth disabled — open mode

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Valid X-API-Key required."},
        )

    # 1. Check env-based keys (admin / demo — no quota)
    if any(secrets.compare_digest(x_api_key, allowed) for allowed in _API_KEYS):
        return

    # 2. Check key store (trial / pro — quota enforced)
    quota = key_store.check_and_increment(x_api_key)
    if quota.allowed:
        return

    # Determine appropriate error
    if "Invalid" in quota.reason:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Invalid API key."},
        )
    if "revoked" in quota.reason.lower():
        raise HTTPException(
            status_code=403,
            detail={"error": "key_revoked", "message": quota.reason},
        )
    if "monthly request limit" in quota.reason.lower():
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": quota.reason,
                "requests_used": quota.requests_used,
                "monthly_quota": quota.monthly_quota,
            },
            headers={"Retry-After": "86400"},
        )
    raise HTTPException(
        status_code=403,
        detail={"error": "forbidden", "message": quota.reason},
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
    import datetime

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
        "service": "aletheia-core",
        "version": app.version,
        "uptime_seconds": round(_time.time() - _BOOT_TIME, 2),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "manifest_signature": manifest_status,
    }


@app.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness probe. Returns 200 if all subsystems are healthy, 503 otherwise."""
    import json as _json

    from manifest.signing import verify_manifest_signature

    try:
        verify_manifest_signature(
            manifest_path="manifest/security_policy.json",
            signature_path="manifest/security_policy.json.sig",
            public_key_path="manifest/security_policy.ed25519.pub",
        )
        manifest_ok = True
    except Exception:
        manifest_ok = False

    # Load policy version from manifest
    try:
        with open("manifest/security_policy.json", "r", encoding="utf-8") as f:
            policy_data = _json.load(f)
        policy_version = policy_data.get("version", "unknown")
    except Exception:
        policy_version = "unknown"

    receipt_configured = bool(os.getenv("ALETHEIA_RECEIPT_SECRET", "").strip())
    ready = manifest_ok

    body = {
        "ready": ready,
        "manifest_signature": "VALID" if manifest_ok else "INVALID",
        "policy_version": policy_version,
        "receipt_signing_configured": receipt_configured,
    }
    return JSONResponse(
        status_code=200 if ready else 503,
        content=body,
    )


def _is_read_only_action(action: str) -> bool:
    """Return True if the action appears to be read-only / safe."""
    safe_tokens = ("read", "list", "get", "view", "query", "status", "health", "fetch")
    lower = action.lower()
    return any(token in lower for token in safe_tokens)


@app.post("/v1/audit", dependencies=[Depends(_check_api_key)])
async def secure_audit(req: AuditRequest, request: Request) -> dict:
    import uuid
    client_ip = _get_client_ip(request)
    request_id = str(uuid.uuid4())[:16]
    start_time = _time.time()

    # --- Degraded mode determination ---
    degraded = bool(
        getattr(rate_limiter, "degraded", False) or decision_store.degraded
    )
    fallback_state = "degraded" if degraded else "normal"

    # --- Rate limiting (per-IP, in-memory sliding window) ---
    if not await rate_limiter.allow(client_ip):
        request.state.retry_after = 5
        log_audit_event(
            decision="RATE_LIMITED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="Rate limit exceeded",
            fallback_state=fallback_state,
        )
        return JSONResponse(
            status_code=429,
            content={"decision": "RATE_LIMITED", "reason": "Too many requests. Try again later."},
            headers={"Retry-After": "5"},
        )

    # --- Degraded mode fail-closed for privileged actions ---
    if degraded and not _is_read_only_action(req.action):
        log_audit_event(
            decision="DENIED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="degraded_mode_privileged_action_denied",
            fallback_state=fallback_state,
        )
        return JSONResponse(
            status_code=503,
            content={
                "decision": "DENIED",
                "reason": "degraded_mode_privileged_action_denied",
            },
        )

    # --- Input hardening ---
    clean_input = normalize_shadow_text(req.payload)

    # --- Semantic intent classification (pre-agent screen) ---
    intent_decision = classify_blocked_intent(clean_input)
    if intent_decision.blocked:
        log_audit_event(
            decision="DENIED",
            threat_score=8.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason=f"semantic_intent_policy_block:{intent_decision.category}",
            fallback_state=fallback_state,
        )
        return JSONResponse(
            status_code=403,
            content={
                "decision": "DENIED",
                "reason": "Action denied: semantic policy violation.",
            },
        )

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
            fallback_state=fallback_state,
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
        fallback_state=fallback_state,
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
        response["reason"] = _sanitise_reason(reason)
    else:
        response["reasoning"] = veto_msg

    return response

# ---------------------------------------------------------------------------
# Key management endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/keys", dependencies=[Depends(_check_admin_key)])
async def create_key(req: CreateKeyRequest) -> JSONResponse:
    """Create a new API key.  Returns the raw key exactly once."""
    raw_key, record = key_store.create_key(name=req.name, plan=req.plan)
    return JSONResponse(
        content={
            "key": raw_key,
            **record.to_public_dict(),
        },
        status_code=201,
    )


@app.get("/v1/keys", dependencies=[Depends(_check_admin_key)])
async def list_keys() -> JSONResponse:
    """List all API keys (metadata only — no raw keys or hashes)."""
    records = key_store.list_keys()
    return JSONResponse(
        content={"keys": [r.to_public_dict() for r in records]},
    )


@app.delete("/v1/keys/{key_id}", dependencies=[Depends(_check_admin_key)])
async def revoke_key(key_id: str) -> JSONResponse:
    """Revoke an API key by ID."""
    if not key_id or len(key_id) > 64:
        raise HTTPException(status_code=400, detail={"error": "invalid_key_id"})
    success = key_store.revoke_key(key_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": "key_not_found", "message": "Key not found or already revoked."},
        )
    return JSONResponse(content={"status": "revoked", "id": key_id})


@app.get("/v1/keys/{key_id}/usage", dependencies=[Depends(_check_admin_key)])
async def get_key_usage(key_id: str) -> JSONResponse:
    """Get usage statistics for a specific key."""
    if not key_id or len(key_id) > 64:
        raise HTTPException(status_code=400, detail={"error": "invalid_key_id"})
    record = key_store.get_by_id(key_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"error": "key_not_found", "message": "Key not found."},
        )
    return JSONResponse(content=record.to_public_dict())
