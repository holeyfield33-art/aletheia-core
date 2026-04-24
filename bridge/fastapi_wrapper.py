# bridge/fastapi_wrapper.py
from __future__ import annotations

import logging
import secrets
import time as _time

import hashlib
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, Header, HTTPException, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from agents.judge_v1 import AletheiaJudge
from agents.nitpicker_v2 import AletheiaNitpickerV2
from agents.scout_v2 import AletheiaScoutV2
from bridge.utils import normalize_shadow_text
from core.audit import log_audit_event
from core.config import settings, env_bool, upstash_configured
from core.auth import get_auth_provider
from core.auth.models import AuthContext
from core.auth.rbac import Permission, require_permission, has_permission
from core.embeddings import warm_up
from core.rate_limit import rate_limiter
from core.sandbox import check_action_sandbox
from core.decision_store import decision_store
from core.runtime_security import classify_blocked_intent
from core.key_store import key_store
from core.secret_rotation import install_sigusr1_handler, rotate_secrets
from core.metrics import (
    REQUEST_COUNTER,
    LATENCY_HISTOGRAM,
    metrics_response,
)

_logger = logging.getLogger("aletheia.api")

_TRUSTED_PROXY_DEPTH: int = int(os.getenv("ALETHEIA_TRUSTED_PROXY_DEPTH", "1"))
if not (0 <= _TRUSTED_PROXY_DEPTH <= 5):
    raise ValueError(
        f"ALETHEIA_TRUSTED_PROXY_DEPTH must be 0–5, got {_TRUSTED_PROXY_DEPTH}"
    )
if os.getenv("ENVIRONMENT", "").lower() == "production" and _TRUSTED_PROXY_DEPTH == 1:
    _logger.warning(
        "ALETHEIA_TRUSTED_PROXY_DEPTH is at default value (1) in production. "
        "This may allow IP spoofing if your proxy chain has more than one hop. "
        "Set ALETHEIA_TRUSTED_PROXY_DEPTH explicitly to match your infrastructure. "
        "See docs/ENVIRONMENT_VARIABLES.md for guidance."
    )


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Async lifespan handler — manages Redis/Postgres pool lifecycle."""
    import sys
    from core.redis_pool import get_redis_pool, close_redis_pool
    from core.config import validate_production_config, validate_fips_compliance

    _logger.info("Lifespan startup: initialising connection pools…")

    # --- Production readiness gate ---
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        issues = validate_production_config()
        if issues:
            for issue in issues:
                _logger.critical("PRODUCTION CONFIG ERROR: %s", issue)
            _logger.critical(
                "FATAL: %d production config issue(s) found. Refusing to start.",
                len(issues),
            )
            sys.exit(1)

    # --- FIPS-140 compliance check ---
    if settings.fips_mode:
        violations = validate_fips_compliance()
        if violations:
            for v in violations:
                _logger.critical("FIPS VIOLATION: %s", v)
            _logger.critical(
                "FATAL: %d FIPS-140 violation(s) found. Refusing to start.",
                len(violations),
            )
            sys.exit(1)
        _logger.info("FIPS-140 mode: all checks passed")

    # Redis pool (standard, not Upstash)
    pool = await get_redis_pool()
    if pool is not None:
        try:
            await pool.ping()  # type: ignore[union-attr]
            _logger.info("Redis pool: connected and healthy")
        except Exception as exc:
            _logger.error("Redis pool: ping failed — %s", exc)
    else:
        _logger.info("Redis pool: not configured (using Upstash or in-memory)")

    # Postgres pool (optional)
    pg_pool = None
    if settings.database_backend == "postgres":
        db_url = settings.database_url or os.getenv("DATABASE_URL", "")
        if db_url:
            try:
                import asyncpg

                pg_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
                async with pg_pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                _logger.info("Postgres pool: connected and healthy")
            except Exception as exc:
                _logger.error("Postgres pool: connection failed — %s", exc)
                if os.getenv("ENVIRONMENT", "").lower() == "production":
                    import sys

                    _logger.critical(
                        "FATAL: cannot reach Postgres in production. Refusing to start."
                    )
                    sys.exit(1)

    # Audit export workers (Task 4 — Elasticsearch, Splunk, Webhook, Syslog)
    from core.exporters import start_export_workers, stop_export_workers

    await _startup_checks()
    start_export_workers()

    yield

    # Shutdown: close pools + exporters
    _logger.info("Lifespan shutdown: closing connection pools…")
    await stop_export_workers()
    await close_redis_pool()
    if pg_pool is not None:
        await pg_pool.close()
        _logger.info("Postgres pool: closed")
    _logger.info("Lifespan shutdown: complete")


app = FastAPI(
    title="Aletheia Core API",
    version="1.9.1",
    description="Runtime audit and pre-execution block layer for autonomous AI agents.",
    lifespan=_lifespan,
)

_BOOT_TIME = _time.time()

_CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALETHEIA_CORS_ORIGINS",
        "https://app.aletheia-core.com,https://aletheia-core.com",
    ).split(",")
    if o.strip()
]
# Block wildcard CORS in production
if os.getenv("ENVIRONMENT", "").lower() == "production" and "*" in _CORS_ORIGINS:
    _logger.critical(
        "FATAL: ALETHEIA_CORS_ORIGINS contains '*' in production. "
        "This allows any origin to make credentialed requests. "
        "Set explicit origins. Refusing to start."
    )
    sys.exit(1)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
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
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'"
    )
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=()"
    )
    # Rate limit headers
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Remaining"] = str(
            request.state.rate_limit_remaining
        )
    if hasattr(request.state, "retry_after"):
        response.headers["Retry-After"] = str(request.state.retry_after)
    return response


# ---------------------------------------------------------------------------
# Unified auth middleware (enterprise auth layer)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def enterprise_auth_middleware(request: Request, call_next):
    """Populate ``request.state.auth_context`` from the active auth provider.

    This middleware runs on every request.  Endpoints that need auth use
    ``require_permission()`` or ``require_role()`` dependencies which
    read ``request.state.auth_context``.  Unauthenticated requests get
    ``auth_context = None`` — the dependencies decide whether to reject.

    When ``ALETHEIA_AUTH_PROVIDER=api_key`` (the default), behaviour is
    identical to the original ``_check_api_key`` flow — this middleware
    just pre-populates the context for RBAC checks.
    """
    # Skip auth for fully unauthenticated endpoints (no optional auth either).
    unauthenticated_paths = {"/ready", "/docs", "/openapi.json"}
    if request.url.path in unauthenticated_paths:
        return await call_next(request)

    credential = request.headers.get("authorization", "") or request.headers.get(
        "x-api-key", ""
    )
    if credential:
        try:
            provider = get_auth_provider()
            user = await provider.authenticate(credential)
            if user:
                request.state.auth_context = AuthContext(user=user, token=credential)
        except Exception as exc:
            _logger.debug("Auth middleware error: %s", exc)

    # Always continue — individual endpoints decide if auth is required.
    return await call_next(request)


# ---------------------------------------------------------------------------
# Admin-key dependency for key management endpoints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Key management request models
# ---------------------------------------------------------------------------


class CreateKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=64)
    plan: str = Field(default="trial", pattern=r"^(trial|pro)$")
    role: str = Field(default="operator", pattern=r"^(viewer|auditor|operator|admin)$")


# Singleton agent instances
scout = AletheiaScoutV2()
nitpicker = AletheiaNitpickerV2()
judge = AletheiaJudge()

# Unified Sovereign Runtime (v1.7.0) — three-anchor pipeline
# Initialised lazily to avoid import-time TPM probing in tests.
_sovereign_runtime = None


def _get_sovereign_runtime():
    """Lazy singleton for the Unified Sovereign Runtime."""
    global _sovereign_runtime
    if _sovereign_runtime is None:
        from core.unified_audit import UnifiedSovereignRuntime

        _sovereign_runtime = UnifiedSovereignRuntime()
    return _sovereign_runtime


async def _startup_checks() -> None:
    """Pre-warm embedding model and validate critical secrets at startup."""
    import sys

    # If ENVIRONMENT=production, refuse shadow mode — deny-decisions must be enforced
    if (
        os.getenv("ENVIRONMENT", "").lower() == "production"
        and settings.mode != "active"
    ):
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
    if settings.mode == "active":
        _auth_disabled = env_bool("ALETHEIA_AUTH_DISABLED")
        if not _auth_disabled:
            # Verify KeyStore is operational
            pass  # KeyStore availability is checked by its own init
    # Block env-based API keys in production (removed — use KeyStore only)
    if os.getenv("ALETHEIA_API_KEYS", "").strip():
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            _logger.critical(
                "FATAL: ALETHEIA_API_KEYS is set in production. "
                "Environment-based API keys are no longer supported. "
                "Use the KeyStore (POST /v1/keys) to provision keys. "
                "Remove ALETHEIA_API_KEYS to proceed. Refusing to start."
            )
            sys.exit(1)
        _logger.warning(
            "ALETHEIA_API_KEYS is set but will be IGNORED. "
            "Environment-based API keys are deprecated. "
            "Use the KeyStore (POST /v1/keys) to provision keys."
        )
    # Block ALETHEIA_AUTH_DISABLED in production
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        if env_bool("ALETHEIA_AUTH_DISABLED"):
            _logger.critical(
                "FATAL: ALETHEIA_AUTH_DISABLED=true is not allowed in production. "
                "Configure ALETHEIA_API_KEYS instead. Refusing to start."
            )
            sys.exit(1)
    if not os.getenv("ALETHEIA_ALIAS_SALT", "").strip():
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            _logger.critical(
                "FATAL: ALETHEIA_ALIAS_SALT is not set in production. "
                "Daily alias bank rotation is predictable without a salt. "
                "Generate: openssl rand -hex 32. Refusing to start."
            )
            sys.exit(1)
        _logger.warning(
            "WARNING: ALETHEIA_ALIAS_SALT is not set. "
            "Daily alias bank rotation is predictable — "
            "an attacker who knows the manifest hash and date can "
            "enumerate the alias order. Set this in production. "
            "Generate: openssl rand -hex 32"
        )
    if not os.getenv("ALETHEIA_KEY_SALT", "").strip():
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            _logger.critical(
                "FATAL: ALETHEIA_KEY_SALT is not set in production. "
                "API key hashing is unsalted. "
                "Generate: openssl rand -hex 32. Refusing to start."
            )
            sys.exit(1)

    # Manifest hash pinning: verify manifest hasn't drifted from expected hash
    _pinned_hash = os.getenv("ALETHEIA_MANIFEST_HASH", "").strip()
    if _pinned_hash:
        try:
            actual_hash = hashlib.sha256(
                Path("manifest/security_policy.json").read_bytes()
            ).hexdigest()
            if not secrets.compare_digest(_pinned_hash, actual_hash):
                _logger.critical(
                    "FATAL: Manifest hash drift detected. "
                    "Expected %s, got %s. The signed policy may have been "
                    "tampered with or replaced. Refusing to start.",
                    _pinned_hash[:16] + "...",
                    actual_hash[:16] + "...",
                )
                sys.exit(1)
            _logger.info("Manifest hash pinning verified: %s", actual_hash[:16] + "...")
        except FileNotFoundError:
            _logger.critical(
                "FATAL: ALETHEIA_MANIFEST_HASH is set but "
                "manifest/security_policy.json is missing. Refusing to start."
            )
            sys.exit(1)
    elif os.getenv("ENVIRONMENT", "").lower() == "production":
        _logger.warning(
            "WARNING: ALETHEIA_MANIFEST_HASH is not set in production. "
            "Manifest drift detection is disabled. "
            "Pin the hash: sha256sum manifest/security_policy.json"
        )

    warm_up()

    # --- Production HA checks: require DATABASE_URL + REDIS_URL for postgres backend ---
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        if settings.database_backend == "postgres":
            if not settings.database_url and not os.getenv("DATABASE_URL", ""):
                _logger.critical(
                    "FATAL: database_backend=postgres but DATABASE_URL is not set "
                    "in production. Refusing to start."
                )
                sys.exit(1)
            db_url = settings.database_url or os.getenv("DATABASE_URL", "")
            if "sslmode" not in db_url and "sslmode=require" not in db_url:
                _logger.critical(
                    "FATAL: DATABASE_URL missing sslmode=require in production. "
                    "TLS is required. Add ?sslmode=require to your connection string."
                )
                sys.exit(1)
        if not os.getenv("REDIS_URL", "") and not upstash_configured():
            _logger.critical(
                "FATAL: Neither REDIS_URL nor UPSTASH_REDIS_REST_URL is set "
                "in production. Redis is required for distributed rate limiting "
                "and replay defense. Refusing to start."
            )
            sys.exit(1)

    # Install SIGUSR1 handler for hot secret rotation
    install_sigusr1_handler(
        reload_api_keys_fn=None,
        reload_judge_fn=judge.load_policy,
    )
    _logger.info("Secret rotation handler installed (kill -SIGUSR1 to rotate)")


async def _on_startup() -> None:
    """Backward-compatible startup hook for tests and legacy imports."""
    await _startup_checks()


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
        content={
            "decision": "ERROR",
            "reason": "Internal processing error. See audit log.",
        },
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
    if xff and _TRUSTED_PROXY_DEPTH > 0:
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


def _check_api_key(
    request: Request, x_api_key: str | None = Header(default=None)
) -> None:
    """Dependency: validate X-API-Key header and enforce quota.

    Also accepts enterprise auth (OIDC/SAML) when the auth middleware
    has already populated ``request.state.auth_context`` with a user
    holding the ``audit:submit`` permission.

    Auth is REQUIRED by default. To explicitly disable (dev only),
    set ALETHEIA_AUTH_DISABLED=true. This never works in production.

    Keys are authenticated exclusively via the KeyStore (SQLite/Postgres).
    Environment-variable keys (ALETHEIA_API_KEYS) are no longer accepted.
    """
    # Enterprise auth: if the middleware already authenticated the user,
    # check permission and skip API-key validation.
    ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    if ctx is not None and has_permission(ctx.user.roles, Permission.AUDIT_SUBMIT):
        return

    # Auth explicitly disabled (dev/testing only; blocked in production at startup)
    _auth_disabled = env_bool("ALETHEIA_AUTH_DISABLED")
    if _auth_disabled:
        return

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Valid X-API-Key required."},
        )

    # Authenticate via KeyStore only (trial / pro — quota enforced)
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
    if "SEMANTIC_BLOCK" in first_line:
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


def _verify_manifest() -> bool:
    """Check manifest signature integrity. Returns True if valid."""
    from manifest.signing import verify_manifest_signature

    try:
        verify_manifest_signature(
            manifest_path="manifest/security_policy.json",
            signature_path="manifest/security_policy.json.sig",
            public_key_path="manifest/security_policy.ed25519.pub",
        )
        return True
    except Exception:
        return False


@app.get("/health")
async def health_check(request: Request) -> dict:
    """Health endpoint. Public response is minimal; authenticated response includes diagnostics."""
    import datetime

    manifest_ok = _verify_manifest()
    manifest_status = "VALID" if manifest_ok else "INVALID"
    status = "ok" if manifest_ok else "degraded"

    # Check Redis connectivity
    redis_status = "not_configured"
    try:
        from core.redis_pool import get_redis_pool

        pool = await get_redis_pool()
        if pool is not None:
            await pool.ping()  # type: ignore[union-attr]
            redis_status = "ok"
    except Exception:
        redis_status = "error"
        status = "degraded"

    # Public response: minimal — no version, uptime, or manifest details
    ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    is_admin = ctx is not None and ctx.user.is_admin

    if not is_admin:
        return {"status": status, "service": "aletheia-core"}

    # Authenticated response: full diagnostics
    return {
        "status": status,
        "service": "aletheia-core",
        "version": app.version,
        "uptime_seconds": round(_time.time() - _BOOT_TIME, 2),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "manifest_signature": manifest_status,
        "database_backend": settings.database_backend,
        "redis": redis_status,
    }


@app.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness probe. Returns 200 if all subsystems are healthy, 503 otherwise."""
    import json as _json

    manifest_ok = _verify_manifest()

    # Load policy version from manifest
    try:
        with open("manifest/security_policy.json", "r", encoding="utf-8") as f:
            policy_data = _json.load(f)
        policy_version = policy_data.get("version", "unknown")
    except Exception:
        policy_version = "unknown"

    receipt_configured = bool(os.getenv("ALETHEIA_RECEIPT_SECRET", "").strip())

    # Redis readiness
    redis_ready = True
    try:
        from core.redis_pool import get_redis_pool

        pool = await get_redis_pool()
        if pool is not None:
            await pool.ping()  # type: ignore[union-attr]
    except Exception:
        redis_ready = False

    ready = manifest_ok and redis_ready

    body = {
        "ready": ready,
        "manifest_signature": "VALID" if manifest_ok else "INVALID",
        "policy_version": policy_version,
        "receipt_signing_configured": receipt_configured,
        "database_backend": settings.database_backend,
        "redis_ready": redis_ready,
    }
    return JSONResponse(
        status_code=200 if ready else 503,
        content=body,
    )


@app.get("/metrics")
async def prometheus_metrics(request: Request) -> Response:
    """Prometheus metrics endpoint. Auth REQUIRED in production."""
    _metrics_token = os.getenv("ALETHEIA_METRICS_TOKEN", "").strip()
    if not _metrics_token:
        # In production, refuse unauthenticated metrics
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            return JSONResponse(
                status_code=403,
                content={
                    "error": "metrics_disabled",
                    "message": "ALETHEIA_METRICS_TOKEN not configured. Metrics disabled in production.",
                },
            )
        # Non-production: allow unauthenticated access with a warning
        _logger.warning(
            "ALETHEIA_METRICS_TOKEN not set — /metrics is publicly accessible"
        )
    else:
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {_metrics_token}"
        if not auth_header or not secrets.compare_digest(auth_header, expected):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Valid metrics token required.",
                },
            )
    from starlette.responses import Response as StarletteResponse

    body, content_type = metrics_response()
    return StarletteResponse(content=body, media_type=content_type)


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

    # --- Extract tenant context from enterprise auth ---
    ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    _tenant_id = ctx.user.tenant_id if ctx and ctx.user.tenant_id else "default"
    _user_id = ctx.user.user_id if ctx else ""
    _auth_method = ctx.user.auth_method if ctx else ""

    # --- Degraded mode determination ---
    degraded = bool(getattr(rate_limiter, "degraded", False) or decision_store.degraded)
    fallback_state = "degraded" if degraded else "normal"

    # --- Rate limiting (per-IP, tenant-scoped) ---
    if not await rate_limiter.allow(client_ip, tenant_id=_tenant_id):
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
            tenant_id=_tenant_id,
            user_id=_user_id,
            auth_method=_auth_method,
        )
        return JSONResponse(
            status_code=429,
            content={
                "decision": "RATE_LIMITED",
                "reason": "Too many requests. Try again later.",
            },
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
            tenant_id=_tenant_id,
            user_id=_user_id,
            auth_method=_auth_method,
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
            tenant_id=_tenant_id,
            user_id=_user_id,
            auth_method=_auth_method,
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
            tenant_id=_tenant_id,
            user_id=_user_id,
            auth_method=_auth_method,
        )
        return JSONResponse(
            status_code=403,
            content={
                "decision": "SANDBOX_BLOCKED",
                "reason": _sanitise_reason(sandbox_hit),
            },
        )

    # 1. SCOUT PHASE
    threat_score, report = scout.evaluate_threat_context(client_ip, clean_input)

    # 2. NITPICKER PHASE — semantic block check feeds the decision
    nitpicker_blocked, nitpicker_reason = nitpicker.check_semantic_block(clean_input)
    clean_content = nitpicker.sanitize_intent(  # noqa: F841 — logged by sanitize_intent
        clean_input, req.origin, request_id=request_id
    )

    # 3. JUDGE PHASE — now includes payload for semantic veto
    is_allowed, veto_msg = judge.verify_action(req.action, payload=clean_input)

    # DECISION: block if ANY agent denies (defense-in-depth)
    is_blocked = (
        (threat_score >= settings.policy_threshold)
        or (not is_allowed)
        or nitpicker_blocked
    )
    if nitpicker_blocked:
        reason = nitpicker_reason
    elif threat_score >= settings.policy_threshold:
        reason = report
    else:
        reason = veto_msg
    latency = (_time.time() - start_time) * 1000

    decision = "DENIED" if is_blocked else "PROCEED"

    # Record Prometheus metrics
    REQUEST_COUNTER.labels(agent="pipeline", verdict=decision).inc()
    LATENCY_HISTOGRAM.observe(latency / 1000)  # seconds

    # Shadow mode override: log the block but let the request through.
    # Safety: shadow mode is NEVER allowed when ENVIRONMENT=production,
    # even if settings.shadow_mode was toggled at runtime.
    shadow_verdict = None
    _env_is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    if is_blocked and settings.shadow_mode:
        if _env_is_production:
            _logger.error(
                "SHADOW_MODE_BLOCKED: shadow_mode=true but ENVIRONMENT=production. "
                "Refusing to override DENIED decision for action=%s origin=%s. "
                "Fix configuration: set ALETHEIA_MODE=active for production.",
                req.action,
                req.origin,
            )
        else:
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
        tenant_id=_tenant_id,
        user_id=_user_id,
        auth_method=_auth_method,
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

    # --- Semantic engine block (from Nitpicker Qdrant integration) ---
    nit_result = getattr(nitpicker, "_last_result", None)
    semantic_engine: dict = {
        "enabled": False,
        "degraded": False,
        "manifest_version": None,
        "categories_checked": [],
        "top_match": None,
        "error": None,
    }
    if nit_result is not None:
        semantic_engine["enabled"] = True
        semantic_engine["degraded"] = nit_result.degraded
        semantic_engine["manifest_version"] = nit_result.manifest_version
        semantic_engine["categories_checked"] = nit_result.categories
        if nit_result.top_match_id:
            semantic_engine["top_match"] = {
                "id": nit_result.top_match_id,
                "score": round(nit_result.top_match_score, 4),
                "threshold": round(nit_result.top_match_threshold, 4),
                "category": nit_result.top_match_category,
            }
        if nit_result.error:
            semantic_engine["error"] = nit_result.error

    response["metadata"]["semantic_engine"] = semantic_engine
    audit_record["receipt"]["semantic_engine"] = semantic_engine

    # --- Unified Sovereign Runtime: chain signing (Gate C1) ---
    try:
        sovereign = _get_sovereign_runtime()
        chain_request = {
            "action": req.action,
            "payload": req.payload,
            "origin": req.origin,
        }
        chain_result = sovereign.post_execution_sign(chain_request, dict(response))
        if chain_result.status == "PROCEED":
            response["metadata"]["chain_signature"] = chain_result.chain_signature
            response["metadata"]["chain_nonce"] = chain_result.chain_nonce
    except Exception as exc:
        _logger.warning("Sovereign chain signing skipped: %s", exc)

    if shadow_verdict:
        # Shadow verdict logged internally only — never expose to client
        _logger.info(
            "shadow_verdict=DENIED action=%s origin=%s", req.action, req.origin
        )
    elif is_blocked:
        response["reason"] = _sanitise_reason(reason)

    return response


# ---------------------------------------------------------------------------
# Key management endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/keys", dependencies=[Depends(require_permission(Permission.KEYS_CREATE))]
)
async def create_key(req: CreateKeyRequest) -> JSONResponse:
    """Create a new API key.  Returns the raw key exactly once."""
    raw_key, record = key_store.create_key(name=req.name, plan=req.plan, role=req.role)
    return JSONResponse(
        content={
            "key": raw_key,
            **record.to_public_dict(),
        },
        status_code=201,
    )


@app.get("/v1/keys", dependencies=[Depends(require_permission(Permission.KEYS_LIST))])
async def list_keys() -> JSONResponse:
    """List all API keys (metadata only — no raw keys or hashes)."""
    records = key_store.list_keys()
    return JSONResponse(
        content={"keys": [r.to_public_dict() for r in records]},
    )


@app.delete(
    "/v1/keys/{key_id}",
    dependencies=[Depends(require_permission(Permission.KEYS_REVOKE))],
)
async def revoke_key(key_id: str) -> JSONResponse:
    """Revoke an API key by ID."""
    if not key_id or len(key_id) > 64:
        raise HTTPException(status_code=400, detail={"error": "invalid_key_id"})
    success = key_store.revoke_key(key_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "key_not_found",
                "message": "Key not found or already revoked.",
            },
        )
    return JSONResponse(content={"status": "revoked", "id": key_id})


@app.get(
    "/v1/keys/{key_id}/usage",
    dependencies=[Depends(require_permission(Permission.KEYS_USAGE))],
)
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


# ---------------------------------------------------------------------------
# Secret rotation endpoint
# ---------------------------------------------------------------------------


@app.post(
    "/v1/rotate", dependencies=[Depends(require_permission(Permission.SECRETS_ROTATE))]
)
async def rotate_secrets_endpoint() -> JSONResponse:
    """Hot-rotate secrets without restart. Admin-only, rate-limited by cooldown."""
    result = rotate_secrets(
        reload_api_keys_fn=None,
        reload_judge_fn=judge.load_policy,
    )
    status_code = 200 if result.get("status") == "rotated" else 429
    return JSONResponse(content=result, status_code=status_code)


# ---------------------------------------------------------------------------
# WebSocket audit stream (Task 4 — Live Observability)
# ---------------------------------------------------------------------------

from starlette.websockets import WebSocket as _StarletteWS  # noqa: E402


@app.websocket("/ws/audit")
async def ws_audit_endpoint(ws: _StarletteWS) -> None:
    """Authenticated, tenant-scoped, PII-redacted live audit stream."""
    from core.ws_audit import ws_audit_handler

    await ws_audit_handler(ws)
