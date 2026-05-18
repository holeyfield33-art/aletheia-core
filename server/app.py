# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
# server/app.py
from __future__ import annotations

import logging
import json
import secrets
import time as _time
import asyncio

import hashlib
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import Depends, Header, HTTPException, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from server.models import (
    AuditRequest,
    AgentTrifectaAuditRequest,
    AgentTrifectaMetadata,
    AgentTrifectaAuditResponse,
    CreateKeyRequest,
    EvaluateRequest,
    VerifyReceiptRequest,
)

from agents.judge import AletheiaJudge
from agents.nitpicker import AletheiaNitpickerV2
from agents.scout import AletheiaScoutV2
from server.utils import normalize_shadow_text
from core.audit import (
    ReceiptVerificationError,
    log_audit_event,
    verify_receipt_or_raise,
)
from core.canonicalization import canonicalize_untrusted_text
from core.config import settings, env_bool
from core.auth import get_auth_provider
from core.auth.models import AuthContext
from core.auth.rbac import Permission, require_permission, has_permission
from core.embeddings import warm_up
from core.rate_limit import eval_rate_limiter, rate_limiter
from core.sandbox import check_action_sandbox
from core.decision_store import decision_store
from core.runtime_security import (
    build_layered_normalization_candidates,
    classify_blocked_intent,
    is_semantic_engine_degraded,
)
from core.key_store import QuotaCheck, key_store
from core.secret_rotation import rotate_secrets
from core.runtime_bootstrap import (
    demo_key_health_signal,
    resolve_demo_api_key,
    seed_demo_key,
    startup_checks,
)
from core.auth.api_key_flow import authenticate_api_key
from core.auth.api_key_validation import raise_for_quota_failure, resolve_api_key
from core.auth.hosted_prisma_bridge import (
    check_hosted_prisma_api_key,
    current_utc_month_bounds,
    hash_hosted_api_key,
    lookup_hosted_api_key_user_id,
    normalize_utc,
)
from core.runtime_status import collect_dependency_health
from core.runtime_status import collect_manifest_readiness
from core.metrics import (
    REQUEST_COUNTER,
    LATENCY_HISTOGRAM,
    AUDIT_DECISIONS_TOTAL,
    AUDIT_EVALUATION_DURATION_SECONDS,
    metrics_response,
)
from core.logging import configure_logging
from core.agent_trifecta import AgentTrifectaContext, evaluate_agent_trifecta
from core.db import (
    close_asyncpg_pool,
    create_asyncpg_pool,
    init_optional_postgres_pool,
    probe_asyncpg_pool,
)
from core.persistence.hosted_audit_log import (
    generate_cuid,
    persist_audit_log,
    persist_hosted_audit_log,
)


configure_logging()

_logger = logging.getLogger("aletheia.api")

_BOOT_TIME = _time.time()
_ready = False
_startup_error_detail = "startup not completed"

_TRUSTED_PROXY_DEPTH: int = int(os.getenv("ALETHEIA_TRUSTED_PROXY_DEPTH", "1"))
if not (0 <= _TRUSTED_PROXY_DEPTH <= 5):
    raise ValueError(
        f"ALETHEIA_TRUSTED_PROXY_DEPTH must be 0–5, got {_TRUSTED_PROXY_DEPTH}"
    )
if os.getenv("ENVIRONMENT", "").lower() == "production":
    if "ALETHEIA_TRUSTED_PROXY_DEPTH" not in os.environ:
        _logger.warning(
            "ALETHEIA_TRUSTED_PROXY_DEPTH is not set in production. "
            "Defaulting to 1 (single proxy hop). "
            "Set explicitly: 1 for Render-only, 2 for Cloudflare+Render. "
            "IP-based rate limiting may be spoofable if your chain has more hops."
        )

# Module-level asyncpg pool for the hosted-Prisma key bridge.
# Initialised in _lifespan; shared across all requests to avoid per-call TCP
# connection overhead which would exhaust the DB connection limit under load.
_bridge_pool: "Any | None" = None


async def _init_bridge_pool() -> None:
    """Create the asyncpg pool used by _check_hosted_prisma_api_key."""
    global _bridge_pool
    database_url = settings.database_url or os.getenv("DATABASE_URL", "")
    if not database_url:
        _logger.info("Bridge pool: DATABASE_URL not set — hosted key bridge disabled")
        return
    try:
        _bridge_pool = await create_asyncpg_pool(
            database_url,
            min_size=1,
            max_size=5,
            command_timeout=10,
            sanitize_url=True,
        )
        await probe_asyncpg_pool(_bridge_pool)
        _logger.info("Bridge pool: connected and healthy")
    except Exception as exc:
        _logger.error("Bridge pool: failed to initialise — %s", exc)
        _bridge_pool = None


async def _close_bridge_pool() -> None:
    global _bridge_pool
    await close_asyncpg_pool(_bridge_pool, label="Bridge pool")
    _bridge_pool = None


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Async lifespan handler — manages Redis/Postgres pool lifecycle."""
    import sys
    from core.redis_pool import get_redis_pool, close_redis_pool
    from core.config import validate_production_config, validate_fips_compliance

    global _ready, _startup_error_detail
    _ready = False
    _startup_error_detail = "startup in progress"

    _logger.info("Lifespan startup: initialising connection pools…")

    pg_pool = None
    startup_ok = False

    try:
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
        try:
            pg_pool = await init_optional_postgres_pool()
            if pg_pool is not None:
                _logger.info("Postgres pool: connected and healthy")
        except Exception as exc:
            _logger.error("Postgres pool: connection failed — %s", exc)
            if os.getenv("ENVIRONMENT", "").lower() == "production":
                raise RuntimeError("critical startup failure: postgres unavailable")

        # Bridge pool: shared asyncpg pool for hosted-Prisma key lookups.
        # Initialised regardless of database_backend so the bridge works even
        # when the Python backend itself uses SQLite for its own key store.
        await _init_bridge_pool()

        # Audit export workers (Task 4 — Elasticsearch, Splunk, Webhook, Syslog)
        from core.exporters import start_export_workers

        await _startup_checks()
        start_export_workers()

        # Warmup is best-effort and non-blocking for health/readiness checks.
        asyncio.create_task(asyncio.to_thread(warm_up))

        # Manifest cache initialization (PERFORMANCE: ~24s → <100ms per-request lookup)
        try:
            from sentence_transformers import SentenceTransformer
            from core.manifest_cache import load_and_embed_manifest
            from pathlib import Path

            embedding_model = SentenceTransformer(
                settings.embedding_model,
                device="cpu",
                cache_folder=None,
            )
            manifest_path = Path("data/semantic_manifest.json")
            if manifest_path.is_file():
                t_start = _time.time()
                cache = load_and_embed_manifest(str(manifest_path), embedding_model)
                elapsed_ms = (_time.time() - t_start) * 1000
                application.state.manifest_cache = cache
                application.state.embedding_model = embedding_model

                # Inject cache into Nitpicker for vectorized per-request lookups
                nitpicker.set_manifest_cache(cache, embedding_model)

                _logger.info(
                    "Manifest cache ready: %d entries embedded in %.1f ms",
                    len(cache.entries),
                    elapsed_ms,
                )
            else:
                _logger.warning(
                    "Manifest not found at %s; semantic pattern matching degraded",
                    manifest_path,
                )
                application.state.manifest_cache = None
                application.state.embedding_model = None
        except Exception as exc:
            _logger.warning(
                "Failed to initialize manifest cache: %s; semantic pattern matching degraded",
                exc,
            )
            application.state.manifest_cache = None
            application.state.embedding_model = None

        # Idempotent demo-key seed: lets the public /demo flow survive restarts
        # without re-introducing the deprecated ALETHEIA_API_KEYS env-var auth path.
        # No-op if the key is already known to the KeyStore, or if the env var is unset.
        _seed_demo_key()
        demo_key = _demo_key_health_signal()
        if not demo_key["configured"]:
            _logger.info("demo-key health: not configured")
        elif demo_key["status"] == "registered":
            _logger.info(
                "demo-key health: registered in KeyStore (%s)",
                demo_key["source"],
            )
        elif demo_key["status"] == "missing":
            _logger.warning(
                "demo-key health: configured via %s but missing in KeyStore; "
                "the hosted /demo proxy may receive upstream 401",
                demo_key["source"],
            )
        else:
            _logger.warning(
                "demo-key health: lookup failed for configured key (%s)",
                demo_key["source"],
            )

        _ready = True
        _startup_error_detail = ""
        startup_ok = True
    except BaseException as exc:
        _ready = False
        _startup_error_detail = str(exc) or "critical startup failure"
        _logger.exception("Startup failed; service will report not ready: %s", exc)

    # Import for shutdown path regardless of startup outcome.
    from core.exporters import stop_export_workers

    yield

    # Shutdown: close pools + exporters
    _logger.info("Lifespan shutdown: closing connection pools…")
    if startup_ok:
        await stop_export_workers()
    await close_redis_pool()
    await _close_bridge_pool()
    await close_asyncpg_pool(pg_pool)
    _logger.info("Lifespan shutdown: complete")


_is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

app = FastAPI(
    title="Aletheia Core API",
    version="1.9.3",
    description="Runtime audit and pre-execution block layer for autonomous AI agents.",
    lifespan=_lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

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
    if "Cache-Control" not in response.headers:
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
    unauthenticated_paths = {"/health", "/ready", "/docs", "/redoc", "/openapi.json"}
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
# Internal-secret guard — outermost middleware (defined last = runs first)
# ---------------------------------------------------------------------------

_INTERNAL_SECRET: str = os.getenv("ALETHEIA_INTERNAL_SECRET", "").strip()

# Paths exempt from the guard so health/readiness probes and public key
# endpoints remain reachable without the Vercel proxy.
_INTERNAL_SECRET_EXEMPT = frozenset(
    [
        "/health",
        "/ready",
        "/docs",
        "/openapi.json",
        "/metrics",
        "/.well-known/aletheia-receipt-key.pem",
        "/.well-known/aletheia-manifest-key.pem",
        "/v1/public-key",
        "/v1/audit",
    ]
)


@app.middleware("http")
async def internal_secret_guard(request: Request, call_next):
    """Reject /v1/* requests that did not arrive via the Vercel proxy.

    When ALETHEIA_INTERNAL_SECRET is set, every request to a guarded path
    must carry the matching ``x-aletheia-internal`` header.  The Vercel
    /api/v1/* proxy injects this header automatically (ALETHEIA_INTERNAL_SECRET
    env var on Vercel).  Direct callers hitting the Render URL receive 403.

    If the env var is unset the guard is a no-op so existing deployments
    continue to work until the operator explicitly enables it.
    """
    if not _INTERNAL_SECRET:
        return await call_next(request)

    path = request.url.path
    guarded = path.startswith("/v1/") or path == "/v1"
    if not guarded or path in _INTERNAL_SECRET_EXEMPT:
        return await call_next(request)

    provided = request.headers.get("x-aletheia-internal", "")
    # Use secrets.compare_digest to prevent timing attacks on the secret value.
    if not provided or not secrets.compare_digest(provided, _INTERNAL_SECRET):
        _logger.warning(  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
            "internal_secret_guard: rejected request path=%s xff=%s",
            path,
            request.headers.get("x-forwarded-for", "unknown"),
        )
        return JSONResponse(status_code=403, content={"error": "forbidden"})

    return await call_next(request)


# ---------------------------------------------------------------------------
# Admin-key dependency for key management endpoints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Key management request models — see server/models.py
# ---------------------------------------------------------------------------

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


def _resolve_demo_api_key() -> tuple[str, str]:
    """Compatibility shim for tests importing wrapper internals."""
    return resolve_demo_api_key()


def _demo_key_health_signal() -> dict[str, str | bool]:
    """Compatibility shim for tests importing wrapper internals."""
    return demo_key_health_signal(key_store=key_store)


def _seed_demo_key() -> None:
    """Provision the public demo key into the KeyStore at startup.

    Background: env-var keys (ALETHEIA_API_KEYS) were removed in v1.7. The hosted
    /demo flow needs a stable upstream key, but Render's free-tier filesystem is
    ephemeral, so a SQLite-backed KeyStore loses keys on every restart. This
    helper inserts the configured demo key into the KeyStore if it isn't already
    present, and is a no-op otherwise.

    Env resolution mirrors the demo proxy:
    1) ALETHEIA_DEMO_API_KEY
    2) ALETHEIA_API_KEY (fallback)

    Operators on a Postgres-backed KeyStore should still create the canonical
    demo key with POST /v1/keys; this seed only catches the gap.
    """
    seed_demo_key(key_store=key_store, logger=_logger)


async def _startup_checks() -> None:
    """Compatibility shim that delegates startup checks to core bootstrap module."""
    await startup_checks(judge_load_policy=judge.load_policy, logger=_logger)


async def _on_startup() -> None:
    """Backward-compatible startup hook for tests and legacy imports."""
    await _startup_checks()


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


def _hash_hosted_api_key(raw_key: str) -> str:
    """Compatibility shim for hosted Prisma key hashing."""
    return hash_hosted_api_key(raw_key, os.getenv("ALETHEIA_KEY_SALT", ""))


def _normalize_utc(ts: datetime) -> datetime:
    """Compatibility shim for UTC normalization."""
    return normalize_utc(ts)


def _current_utc_month_bounds(now: datetime) -> tuple[datetime, datetime]:
    return current_utc_month_bounds(now)


async def _check_hosted_prisma_api_key(raw_key: str) -> QuotaCheck | None:
    """Compatibility shim for hosted Prisma fallback quota checks."""
    return await check_hosted_prisma_api_key(
        raw_key,
        pool=_bridge_pool,
        key_salt=os.getenv("ALETHEIA_KEY_SALT", ""),
        logger=_logger,
    )


async def _lookup_hosted_api_key_user_id(raw_key: str) -> str:
    """Compatibility shim for hosted Prisma user-id lookups."""
    return await lookup_hosted_api_key_user_id(
        raw_key,
        pool=_bridge_pool,
        key_salt=os.getenv("ALETHEIA_KEY_SALT", ""),
        logger=_logger,
    )


def _generate_cuid() -> str:
    """Compatibility shim for hosted AuditLog row id generation."""
    return generate_cuid()


async def _persist_audit_log(
    *,
    user_id: str | None,
    decision: str,
    threat_score: float,
    action: str,
    origin: str,
    source_ip: str,
    reason: str,
    latency_ms: float,
    payload_hash: str,
    policy_hash: str,
    request_id: str,
    receipt: dict[str, Any] | None,
) -> None:
    """Compatibility shim for hosted Prisma audit persistence."""
    await persist_audit_log(
        pool=_bridge_pool,
        logger=_logger,
        user_id=user_id,
        decision=decision,
        threat_score=threat_score,
        action=action,
        origin=origin,
        source_ip=source_ip,
        reason=reason,
        latency_ms=latency_ms,
        payload_hash=payload_hash,
        policy_hash=policy_hash,
        request_id=request_id,
        receipt=receipt,
    )


async def _persist_hosted_audit_log(audit_record: dict[str, Any], user_id: str) -> None:
    """Compatibility shim for hosted audit log mirroring."""
    await persist_hosted_audit_log(
        pool=_bridge_pool,
        logger=_logger,
        audit_record=audit_record,
        user_id=user_id,
    )


async def _log_audit_and_persist(*, user_id: str, **kwargs: Any) -> dict[str, Any]:
    """Write canonical audit record and mirror it into hosted Prisma AuditLog."""
    audit_record = log_audit_event(user_id=user_id, **kwargs)
    try:
        await _persist_hosted_audit_log(audit_record, user_id=user_id)
    except Exception as exc:
        _logger.warning(
            "audit_log_persist_failed request_id=%s err=%s",
            str(audit_record.get("request_id", "")),
            exc,
        )
    return audit_record


async def _check_api_key(
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

    headers = getattr(request, "headers", {})
    auth_header = headers.get("authorization", "") if headers is not None else ""
    api_key = resolve_api_key(x_api_key, auth_header)

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Valid X-API-Key required."},
        )

    auth_result = await authenticate_api_key(
        api_key,
        key_store=key_store,
        hosted_quota_checker=_check_hosted_prisma_api_key,
        hosted_user_lookup=_lookup_hosted_api_key_user_id,
        logger=_logger,
    )
    if auth_result.user_id:
        request.state.api_user_id = auth_result.user_id
    quota = auth_result.quota
    if quota.allowed:
        return
    raise_for_quota_failure(quota)


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


def _build_audit_envelope(
    *,
    decision: str,
    reason: str,
    request_id: str,
    receipt: dict[str, Any] | None,
    threat_level: str,
    latency_ms: float,
    fallback_state: str,
    status_code: int,
) -> JSONResponse:
    client_threat_level = threat_level.lower()
    if client_threat_level == "critical":
        client_threat_level = "high"

    return JSONResponse(
        status_code=status_code,
        content={
            "decision": decision,
            "reason": reason,
            "request_id": request_id,
            "receipt": receipt,
            "metadata": {
                "threat_level": client_threat_level,
                "latency_ms": round(latency_ms, 2),
                "client_id": settings.client_id,
                "fallback_state": fallback_state,
            },
        },
    )


def _run_scout(client_ip: str, clean_input: str) -> tuple[float, str]:
    """Execute the Scout phase and return threat score plus report."""
    return scout.evaluate_threat_context(client_ip, clean_input)


def _run_nitpicker(
    clean_input: str,
    origin: str,
    *,
    request_id: str | None = None,
    sanitize: bool = False,
) -> tuple[bool, str, str | None]:
    """Execute Nitpicker block check and optionally sanitize for logging."""
    blocked, reason = nitpicker.check_semantic_block(clean_input)
    clean_content = None
    if sanitize:
        clean_content = nitpicker.sanitize_intent(
            clean_input, origin, request_id=request_id or ""
        )
    return blocked, reason, clean_content


def _run_judge(action: str, clean_input: str) -> tuple[bool, str]:
    """Execute Judge policy verification for the normalized payload."""
    return judge.verify_action(action, payload=clean_input)


def _read_manifest_public_key() -> str:
    """Read the manifest verification public key in PEM format."""
    key_path = Path("manifest/security_policy.ed25519.pub")
    try:
        return key_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "public_key_unavailable",
                "message": "Manifest public key is not available.",
            },
        ) from exc


def _manifest_key_id() -> str:
    """Return stable key ID for manifest Ed25519 public key."""
    from cryptography.hazmat.primitives import serialization as _serialization

    pem = _read_manifest_public_key()
    try:
        key = _serialization.load_pem_public_key(pem.encode("utf-8"))
        der = key.public_bytes(
            encoding=_serialization.Encoding.DER,
            format=_serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "public_key_unavailable",
                "message": f"Manifest public key is malformed: {exc}",
            },
        ) from exc
    return hashlib.sha256(der).hexdigest()[:16]


@app.get("/.well-known/aletheia-receipt-key.pem")
async def receipt_public_key() -> Response:
    """Serve the Ed25519 receipt verification key for external verifiers."""
    from core import receipt_keys

    try:
        receipt_pem = receipt_keys.public_key_pem()
        receipt_kid = receipt_keys.key_id()
    except receipt_keys.ReceiptKeyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "public_key_unavailable",
                "message": f"Receipt public key is not available: {exc}",
            },
        ) from exc

    return Response(
        content=receipt_pem,
        media_type="application/x-pem-file",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Aletheia-Receipt-Key-Id": receipt_kid,
        },
    )


@app.get("/.well-known/aletheia-manifest-key.pem")
async def manifest_public_key() -> Response:
    """Serve the manifest signature verification key."""
    return Response(
        content=_read_manifest_public_key(),
        media_type="application/x-pem-file",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/v1/public-key")
async def public_key_bundle() -> JSONResponse:
    """Serve receipt and manifest verification keys and key IDs."""
    from core import receipt_keys

    try:
        receipt_pem = receipt_keys.public_key_pem().decode("utf-8")
        receipt_kid = receipt_keys.key_id()
    except receipt_keys.ReceiptKeyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "public_key_unavailable",
                "message": f"Receipt public key is not available: {exc}",
            },
        ) from exc

    manifest_pem = _read_manifest_public_key()
    manifest_kid = _manifest_key_id()
    return JSONResponse(
        content={
            "receipt_key": {
                "algorithm": "ed25519",
                "key_id": receipt_kid,
                "pem": receipt_pem,
            },
            "manifest_key": {
                "algorithm": "ed25519",
                "key_id": manifest_kid,
                "pem": manifest_pem,
            },
        },
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Gateway health and readiness endpoint.

    This endpoint intentionally avoids policy/model checks so it stays fast
    even while heavy components are still warming up.
    """
    # Starlette TestClient may not execute lifespan startup unless used as a
    # context manager. Treat that specific state as degraded instead of hard-fail.
    startup_pending = _startup_error_detail in {
        "startup not completed",
        "startup in progress",
    }

    dependency_health = await collect_dependency_health()
    dependencies_ready = dependency_health.all_ready
    status_text = "ok" if (_ready and dependencies_ready) else "degraded"

    # Unauthenticated response stays minimal.
    body: dict[str, object] = {
        "status": status_text,
        "service": "aletheia-core",
    }

    # Authenticated admin/operator callers get full diagnostics.
    auth_header = request.headers.get("authorization", "")
    include_diagnostics = False
    if auth_header:
        try:
            provider = get_auth_provider()
            user = await provider.authenticate(auth_header)
            include_diagnostics = bool(
                user and ("admin" in user.roles or "operator" in user.roles)
            )
        except Exception:
            include_diagnostics = False

    if include_diagnostics:
        demo_key = _demo_key_health_signal()
        body.update(
            {
                "version": app.version,
                "uptime_seconds": round(_time.time() - _BOOT_TIME, 2),
                "timestamp": _time.time(),
                "redis_ready": dependency_health.redis_ready,
                "database_ready": dependency_health.database_ready,
                "database_status": dependency_health.database_status,
                "qdrant_ready": dependency_health.qdrant_ready,
                "qdrant_status": dependency_health.qdrant_status,
                "demo_key_configured": demo_key["configured"],
                "demo_key_registered": demo_key["registered"],
                "demo_key_status": demo_key["status"],
            }
        )

    if dependencies_ready and (_ready or startup_pending):
        return JSONResponse(status_code=200, content=body)

    body["detail"] = _startup_error_detail or "critical startup failure"
    return JSONResponse(status_code=503, content=body)


@app.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness probe. Returns 200 if all subsystems are healthy, 503 otherwise."""
    manifest_readiness = collect_manifest_readiness()

    dependency_health = await collect_dependency_health()

    demo_key = _demo_key_health_signal()

    ready = manifest_readiness.manifest_ok and dependency_health.all_ready

    body = {
        "ready": ready,
        "manifest_signature": manifest_readiness.manifest_signature,
        "policy_version": manifest_readiness.policy_version,
        "receipt_signing_configured": manifest_readiness.receipt_signing_configured,
        "database_backend": settings.database_backend,
        "redis_ready": dependency_health.redis_ready,
        "database_ready": dependency_health.database_ready,
        "database_status": dependency_health.database_status,
        "qdrant_ready": dependency_health.qdrant_ready,
        "qdrant_status": dependency_health.qdrant_status,
        "demo_key_configured": demo_key["configured"],
        "demo_key_registered": demo_key["registered"],
        "demo_key_status": demo_key["status"],
    }
    return JSONResponse(
        status_code=200 if ready else 503,
        content=body,
    )


@app.get("/metrics")
async def prometheus_metrics(request: Request) -> Response:
    """Prometheus metrics endpoint. Disabled unless METRICS_ENABLED=true. Auth REQUIRED in production."""
    _metrics_enabled = os.getenv("METRICS_ENABLED", "false").strip().lower()
    if _metrics_enabled not in ("true", "1", "yes"):
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": "Metrics endpoint is disabled. Set METRICS_ENABLED=true to enable.",
            },
        )
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


# ---------------------------------------------------------------------------
# Evaluation endpoint rate-limit dependency
# ---------------------------------------------------------------------------


async def _check_eval_rate_limit(request: Request) -> None:
    """FastAPI dependency: enforce per-IP rate limit on /v1/evaluate.

    Limits are read from environment at startup:
      EVAL_RATE_LIMIT_PER_MINUTE  (default 20)
      EVAL_RATE_BURST             (default 5)
    """
    client_ip = _get_client_ip(request)
    allowed, retry_after = await eval_rate_limiter.allow(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds",
            headers={"Retry-After": str(retry_after)},
        )



def _evaluate_layers(
    *,
    action: str,
    origin: str,
    payload: str,
    client_ip: str,
    request_id: str,
) -> tuple[float, str, bool, str, bool, str, list[str], str]:
    layered = build_layered_normalization_candidates(payload, max_depth=3)
    if layered.expansion_guard_triggered:
        return (
            10.0,
            "obfuscation:expansion_guard",
            True,
            "obfuscation:expansion_guard",
            False,
            "obfuscation:expansion_guard",
            ["obfuscation:expansion_guard"],
            "",
        )

    max_score = -1.0
    scout_reason = ""
    nit_blocked = False
    nit_reason = ""
    judge_allowed = True
    judge_reason = "Action Approved by the Judge."
    tags: list[str] = []
    preview = ""

    for candidate in layered.candidates:
        score, report = _run_scout(client_ip, candidate.text)
        if score > max_score:
            max_score = score
            scout_reason = report
            if candidate.scheme != "raw":
                tags = [f"obfuscation:{candidate.scheme}"]
                preview = candidate.text[:120]

        blocked, reason, _ = _run_nitpicker(candidate.text, origin)
        if blocked:
            nit_blocked = True
            nit_reason = reason or "Action denied: semantic policy violation."
            if candidate.scheme != "raw":
                tags = [f"obfuscation:{candidate.scheme}"]
                preview = candidate.text[:120]
            break

        allowed, veto = _run_judge(action, candidate.text)
        if not allowed:
            judge_allowed = False
            judge_reason = veto
            if candidate.scheme != "raw":
                tags = [f"obfuscation:{candidate.scheme}"]
                preview = candidate.text[:120]
            break

    if max_score < 0:
        max_score = 0.0
    return (
        max_score,
        scout_reason,
        nit_blocked,
        nit_reason,
        judge_allowed,
        judge_reason,
        tags,
        preview,
    )


@app.post("/v1/verify", dependencies=[Depends(_check_api_key)])
async def verify_receipt_endpoint(req: VerifyReceiptRequest) -> JSONResponse:
    """Strict receipt verification endpoint (hard-fail on any verification error)."""
    try:
        verify_receipt_or_raise(req.receipt)
        return JSONResponse(
            status_code=200,
            content={"verified": True, "status": "accepted"},
        )
    except ReceiptVerificationError as exc:
        status = 422 if exc.code in {"malformed_receipt", "missing_signature"} else 400
        return JSONResponse(
            status_code=status,
            content={"verified": False, "status": "rejected", "error": exc.code},
        )


def _is_read_only_action(action: str) -> bool:
    """Return True if the action appears to be read-only / safe."""
    safe_tokens = ("read", "list", "get", "view", "query", "status", "health", "fetch")
    lower = action.lower()
    return any(token in lower for token in safe_tokens)


@app.post(
    "/v1/evaluate",
    dependencies=[Depends(_check_api_key), Depends(_check_eval_rate_limit)],
)
async def evaluate_policy(req: EvaluateRequest, request: Request) -> JSONResponse:
    """Lightweight policy evaluation endpoint.

    Runs the full Scout → Nitpicker → Judge pipeline and returns a verdict
    without writing a full audit receipt or performing chain signing.
    Rate-limited to EVAL_RATE_LIMIT_PER_MINUTE (default 20) requests per IP
    per minute with a burst of EVAL_RATE_BURST (default 5).
    """
    import uuid

    client_ip = _get_client_ip(request)
    request_id = str(uuid.uuid4())
    start_time = _time.time()

    # --- Input hardening ---
    clean_input = normalize_shadow_text(req.payload)

    # --- Semantic intent classification ---
    intent_decision = classify_blocked_intent(clean_input)
    if intent_decision.blocked:
        return JSONResponse(
            status_code=403,
            content={
                "decision": "DENIED",
                "reason": "Action denied: semantic policy violation.",
                "request_id": request_id,
            },
        )

    # --- Sandbox check ---
    sandbox_hit = check_action_sandbox(req.action, clean_input)
    if sandbox_hit:
        return JSONResponse(
            status_code=403,
            content={
                "decision": "SANDBOX_BLOCKED",
                "reason": _sanitise_reason(sandbox_hit),
                "request_id": request_id,
            },
        )

    # --- Pipeline ---
    (
        threat_score,
        report,
        nitpicker_blocked,
        nitpicker_reason,
        is_allowed,
        veto_msg,
        _obfuscation_tags,
        _obfuscation_preview,
    ) = _evaluate_layers(
        action=req.action,
        origin=req.origin,
        payload=req.payload,
        client_ip=client_ip,
        request_id=request_id,
    )

    is_blocked = (
        (threat_score >= settings.policy_threshold)
        or (not is_allowed)
        or nitpicker_blocked
    )
    if nitpicker_blocked:
        block_reason = nitpicker_reason
    elif threat_score >= settings.policy_threshold:
        block_reason = report
    else:
        block_reason = veto_msg

    decision = "DENIED" if is_blocked else "PROCEED"
    latency = (_time.time() - start_time) * 1000

    REQUEST_COUNTER.labels(agent="evaluate", verdict=decision).inc()
    LATENCY_HISTOGRAM.observe(latency / 1000)

    body: dict = {
        "decision": decision,
        "threat_level": _discretise_threat(threat_score),
        "latency_ms": round(latency, 2),
        "request_id": request_id,
    }
    if is_blocked:
        body["reason"] = _sanitise_reason(block_reason)

    return JSONResponse(status_code=200, content=body)


@app.post("/v1/audit", dependencies=[Depends(_check_api_key)], response_model=None)
async def secure_audit(req: AuditRequest, request: Request) -> Any:
    import uuid

    client_ip = _get_client_ip(request)
    request_id = str(uuid.uuid4())
    start_time = _time.time()

    # --- Extract tenant context from enterprise auth ---
    ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    _tenant_id = ctx.user.tenant_id if ctx and ctx.user.tenant_id else "default"
    _user_id = ctx.user.user_id if ctx else getattr(request.state, "api_user_id", "")
    _auth_method = ctx.user.auth_method if ctx else ""

    _nit_last = getattr(nitpicker, "_last_result", None)
    _semantic_degraded = is_semantic_engine_degraded(_nit_last)
    _manifest_missing = judge.policy is None
    degraded = bool(
        getattr(rate_limiter, "degraded", False)
        or decision_store.degraded
        or _semantic_degraded
        or _manifest_missing
    )
    fallback_state = "degraded" if degraded else "normal"

    # --- Rate limiting (per-IP, tenant-scoped) ---
    if not await rate_limiter.allow(client_ip, tenant_id=_tenant_id):
        request.state.retry_after = 5
        audit_record = await _log_audit_and_persist(
            user_id=_user_id,
            decision="RATE_LIMITED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="Rate limit exceeded",
            fallback_state=fallback_state,
            request_id=request_id,
            receipt_chain=True,
            tenant_id=_tenant_id,
            auth_method=_auth_method,
        )
        rate_limited_response = _build_audit_envelope(
            decision="RATE_LIMITED",
            reason="Too many requests. Try again later.",
            request_id=request_id,
            receipt=audit_record["receipt"],
            threat_level="low",
            latency_ms=(_time.time() - start_time) * 1000,
            fallback_state=fallback_state,
            status_code=429,
        )
        rate_limited_response.headers["Retry-After"] = "5"
        return rate_limited_response

    # --- Degraded mode fail-closed for privileged actions ---
    if degraded and not _is_read_only_action(req.action):
        audit_record = await _log_audit_and_persist(
            user_id=_user_id,
            decision="DENIED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="degraded_mode_privileged_action_denied",
            fallback_state=fallback_state,
            request_id=request_id,
            receipt_chain=True,
            tenant_id=_tenant_id,
            auth_method=_auth_method,
        )
        return _build_audit_envelope(
            decision="DENIED",
            reason="degraded_mode_privileged_action_denied",
            request_id=request_id,
            receipt=audit_record["receipt"],
            threat_level="high",
            latency_ms=(_time.time() - start_time) * 1000,
            fallback_state=fallback_state,
            status_code=503,
        )

    # --- Input hardening ---
    clean_input = normalize_shadow_text(req.payload)

    # --- Phase 1.1: Canonicalization gate (before all agents) ---
    canonical_result = canonicalize_untrusted_text(req.payload)
    canonical_payload = canonical_result.canonical_text
    canonicalization_metadata = {
        "total_transformations": canonical_result.total_transformations,
        "unicode_normalized": canonical_result.unicode_normalized,
        "zero_width_removed": canonical_result.zero_width_removed,
        "bidi_removed": canonical_result.bidi_removed,
        "confusables_collapsed": canonical_result.confusables_collapsed,
        "url_decoded": canonical_result.url_decoded,
        "base64_decoded": canonical_result.base64_decoded,
        "html_entity_decoded": canonical_result.html_entity_decoded,
        "unicode_escape_decoded": canonical_result.unicode_escape_decoded,
        "hex_decoded": canonical_result.hex_decoded,
        "data_uri_decoded": canonical_result.data_uri_decoded,
        "entropy_flag": canonical_result.entropy_flag,
        "entropy_value": round(canonical_result.entropy_value, 2),
        "expansion_guard_triggered": canonical_result.expansion_guard_triggered,
        "decode_budget_exhausted": canonical_result.decode_budget_exhausted,
        "recursion_depth_exhausted": canonical_result.recursion_depth_exhausted,
        "decode_depth": canonical_result.decode_depth,
        "decode_steps": canonical_result.decode_steps,
    }

    layered_probe = build_layered_normalization_candidates(
        canonical_payload, max_depth=3
    )
    if layered_probe.expansion_guard_triggered:
        audit_record = await _log_audit_and_persist(
            user_id=_user_id,
            decision="DENIED",
            threat_score=10.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="obfuscation:expansion_guard",
            fallback_state=fallback_state,
            request_id=request_id,
            receipt_chain=True,
            tenant_id=_tenant_id,
            auth_method=_auth_method,
            obfuscation_tags=["obfuscation:expansion_guard"],
        )
        return _build_audit_envelope(
            decision="DENIED",
            reason="obfuscation:expansion_guard",
            request_id=request_id,
            receipt=audit_record["receipt"],
            threat_level="high",
            latency_ms=(_time.time() - start_time) * 1000,
            fallback_state=fallback_state,
            status_code=403,
        )

    # --- Semantic intent classification (pre-agent screen) ---
    intent_decision = classify_blocked_intent(clean_input)
    if intent_decision.blocked:
        audit_record = await _log_audit_and_persist(
            user_id=_user_id,
            decision="DENIED",
            threat_score=8.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason=f"semantic_intent_policy_block:{intent_decision.category}",
            fallback_state=fallback_state,
            request_id=request_id,
            receipt_chain=True,
            tenant_id=_tenant_id,
            auth_method=_auth_method,
        )
        return _build_audit_envelope(
            decision="DENIED",
            reason="Action denied: semantic policy violation.",
            request_id=request_id,
            receipt=audit_record["receipt"],
            threat_level="high",
            latency_ms=(_time.time() - start_time) * 1000,
            fallback_state=fallback_state,
            status_code=403,
        )

    # --- Sandbox check — block subprocess/socket/exec patterns early ---
    sandbox_hit = check_action_sandbox(req.action, clean_input)
    if sandbox_hit:
        sanitized_sandbox_reason = _sanitise_reason(sandbox_hit)
        audit_record = await _log_audit_and_persist(
            user_id=_user_id,
            decision="SANDBOX_BLOCKED",
            threat_score=10.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason=sanitized_sandbox_reason,
            fallback_state=fallback_state,
            request_id=request_id,
            receipt_chain=True,
            tenant_id=_tenant_id,
            auth_method=_auth_method,
        )
        return _build_audit_envelope(
            decision="SANDBOX_BLOCKED",
            reason=sanitized_sandbox_reason,
            request_id=request_id,
            receipt=audit_record["receipt"],
            threat_level="high",
            latency_ms=(_time.time() - start_time) * 1000,
            fallback_state=fallback_state,
            status_code=403,
        )

    # 1. SCOUT PHASE
    # 1..3. SCOUT + NITPICKER + JUDGE over decoded candidate layers (using canonical payload)
    (
        threat_score,
        report,
        nitpicker_blocked,
        nitpicker_reason,
        _layer_judge_allowed,
        _layer_judge_reason,
        obfuscation_tags,
        obfuscation_preview,
    ) = _evaluate_layers(
        action=req.action,
        origin=req.origin,
        payload=canonical_payload,
        client_ip=client_ip,
        request_id=request_id,
    )

    # Keep sanitize side-effects for logging parity without changing decision path.
    _, _, clean_content = _run_nitpicker(  # noqa: F841
        clean_input,
        req.origin,
        request_id=request_id,
        sanitize=True,
    )

    # Recompute degraded after Nitpicker to catch current-request Qdrant failures
    _nit_last_post = getattr(nitpicker, "_last_result", None)
    if is_semantic_engine_degraded(_nit_last_post):
        degraded = True

    # 3. JUDGE PHASE — now includes payload for semantic veto
    # Re-check fail-closed after current-request Qdrant degradation is reflected
    if degraded and not _is_read_only_action(req.action):
        audit_record = await _log_audit_and_persist(
            user_id=_user_id,
            decision="DENIED",
            threat_score=0.0,
            payload=req.payload,
            action=req.action,
            source_ip=client_ip,
            origin=req.origin,
            reason="degraded_mode_privileged_action_denied",
            fallback_state="degraded",
            request_id=request_id,
            receipt_chain=True,
            tenant_id=_tenant_id,
            auth_method=_auth_method,
        )
        return _build_audit_envelope(
            decision="DENIED",
            reason="degraded_mode_privileged_action_denied",
            request_id=request_id,
            receipt=audit_record["receipt"],
            threat_level="high",
            latency_ms=(_time.time() - start_time) * 1000,
            fallback_state="degraded",
            status_code=503,
        )

    is_allowed = _layer_judge_allowed
    veto_msg = _layer_judge_reason

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
    AUDIT_DECISIONS_TOTAL.labels(decision=decision.lower()).inc()
    AUDIT_EVALUATION_DURATION_SECONDS.observe(latency / 1000)

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
    audit_record = await _log_audit_and_persist(
        user_id=_user_id,
        decision=decision,
        threat_score=threat_score,
        payload=req.payload,
        action=req.action,
        source_ip=client_ip,
        origin=req.origin,
        reason=reason if is_blocked else "",
        latency_ms=latency,
        fallback_state=fallback_state,
        request_id=request_id,
        receipt_chain=True,
        tenant_id=_tenant_id,
        auth_method=_auth_method,
        obfuscation_tags=obfuscation_tags,
        obfuscation_preview=obfuscation_preview,
        canonicalization_metadata=canonicalization_metadata,
    )

    response: dict = {
        "decision": decision,
        "reason": _sanitise_reason(reason) if is_blocked else "",
        "request_id": request_id,
        "receipt": audit_record["receipt"],
        "metadata": {
            "threat_level": (
                "high"
                if _discretise_threat(threat_score).lower() == "critical"
                else _discretise_threat(threat_score).lower()
            ),
            "latency_ms": round(latency, 2),
            "client_id": settings.client_id,
            "fallback_state": fallback_state,
        },
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
    return response


@app.post(
    "/v1/agent-trifecta/audit",
    response_model=AgentTrifectaAuditResponse,
    tags=["Agent Trifecta", "Runtime Security"],
    summary="Context-aware agent capability audit",
    description=(
        "Detects untrusted input + private data access + external egress "
        "before tool execution. Returns PROCEED, REVIEW, or DENIED."
    ),
)
async def agent_trifecta_audit(
    body: AgentTrifectaAuditRequest,
    request: Request,
    _auth_ok: None = Depends(_check_api_key),
) -> JSONResponse:
    import uuid

    request_id = str(uuid.uuid4())
    try:
        client_ip = _get_client_ip(request)

        ctx_auth: AuthContext | None = getattr(request.state, "auth_context", None)
        tenant_id = (
            ctx_auth.user.tenant_id
            if ctx_auth and ctx_auth.user.tenant_id
            else "default"
        )
        user_id = ctx_auth.user.user_id if ctx_auth else ""
        auth_method = ctx_auth.user.auth_method if ctx_auth else ""

        rate_key = f"agent_trifecta_audit:{client_ip}"
        if not await rate_limiter.allow(rate_key, tenant_id=tenant_id):
            request.state.retry_after = 5
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "5"},
                content=AgentTrifectaAuditResponse(
                    decision="RATE_LIMITED",
                    metadata=AgentTrifectaMetadata(
                        threat_level="LOW",
                        request_id=request_id,
                        client_id=settings.client_id,
                    ),
                    reasons=[],
                    summary="Rate limit exceeded.",
                    receipt=None,
                ).model_dump(),
            )

        clean_payload = normalize_shadow_text(body.payload)

        # --- Phase 1.1: Canonicalize tool_args ---
        tool_args_str = json.dumps(body.tool_args) if body.tool_args else ""
        tool_args_canonical = canonicalize_untrusted_text(tool_args_str)
        tool_args_canon_metadata = (
            {
                "total_transformations": tool_args_canonical.total_transformations,
                "entropy_flag": tool_args_canonical.entropy_flag,
                "exceeded_budget": tool_args_canonical.decode_budget_exhausted,
            }
            if tool_args_str
            else {}
        )

        ctx = AgentTrifectaContext(
            payload=clean_payload,
            origin=body.origin,
            action=body.action,
            input_trust=body.input_trust,
            can_read_private_data=body.can_read_private_data,
            can_access_secrets=body.can_access_secrets,
            can_send_external_data=body.can_send_external_data,
            can_write_files=body.can_write_files,
            can_modify_config=body.can_modify_config,
            can_execute_shell=body.can_execute_shell,
            tool_name=body.tool_name,
            tool_args=body.tool_args,
        )

        result = evaluate_agent_trifecta(ctx)

        threat_score_map = {
            "LOW": 1.0,
            "MEDIUM": 5.0,
            "HIGH": 8.0,
            "CRITICAL": 10.0,
        }

        audit_record: dict[str, Any] | None = None
        try:
            audit_record = log_audit_event(
                decision=result.decision,
                threat_score=threat_score_map.get(result.threat_level, 1.0),
                payload=clean_payload,
                action=body.action,
                source_ip=client_ip,
                origin=body.origin,
                reason=",".join(result.reasons),
                request_id=request_id,
                tenant_id=tenant_id,
                user_id=user_id,
                auth_method=auth_method,
                canonicalization_metadata=tool_args_canon_metadata
                if tool_args_canon_metadata
                else None,
            )
        except Exception as exc:
            _logger.error("Agent trifecta audit logging failed: %s", exc)
            if settings.mode == "active":
                return JSONResponse(
                    status_code=500,
                    content=AgentTrifectaAuditResponse(
                        decision="ERROR",
                        metadata=AgentTrifectaMetadata(
                            threat_level="HIGH",
                            request_id=request_id,
                            client_id=settings.client_id,
                        ),
                        reasons=[],
                        summary="Audit logging failed. Request rejected.",
                        receipt=None,
                    ).model_dump(),
                )

        request_id = (
            str((audit_record or {}).get("request_id"))
            if (audit_record or {}).get("request_id")
            else request_id
        )
        receipt = (audit_record or {}).get("receipt") if audit_record else None

        status_code = 403 if result.decision == "DENIED" else 200
        return JSONResponse(
            status_code=status_code,
            content=AgentTrifectaAuditResponse(
                decision=result.decision,
                metadata=AgentTrifectaMetadata(
                    threat_level=result.threat_level,
                    request_id=request_id,
                    client_id=settings.client_id,
                ),
                reasons=result.reasons,
                summary=result.summary,
                receipt=receipt,
            ).model_dump(),
        )
    except Exception as exc:
        _logger.error("Unhandled /v1/agent-trifecta/audit exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=AgentTrifectaAuditResponse(
                decision="ERROR",
                metadata=AgentTrifectaMetadata(
                    threat_level="HIGH",
                    request_id=request_id,
                    client_id=settings.client_id,
                ),
                reasons=[],
                summary="Internal processing error. Request rejected.",
                receipt=None,
            ).model_dump(),
        )


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
