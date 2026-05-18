# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""FastAPI application factory.

All route handlers live in server/routes/.
Shared state lives in server/_app_state.py (ready flag) and server/_state.py (agents).
Bridge pool management lives in server/_bridge.py.
Helper functions live in server/_helpers.py.
FastAPI Depends() live in server/_deps.py.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time as _time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.embeddings import warm_up
from core.logging import configure_logging
from server._bridge import _close_bridge_pool, _init_bridge_pool
from server._helpers import (
    _demo_key_health_signal,
    _on_startup,
    _resolve_demo_api_key,
    _sanitise_reason,
    _seed_demo_key,
    _startup_checks,
    _get_client_ip,
    _discretise_threat,
)
from server._state import nitpicker, scout, judge
from server._deps import _check_api_key
from server.middleware import (
    add_security_and_rate_limit_headers,
    enterprise_auth_middleware,
    internal_secret_guard,
)
from server.models import AuditRequest
from server.routes.audit import router as audit_router
from server.routes.health import router as health_router
from server.routes.keys import router as keys_router
from server.websocket import ws_audit_endpoint

import server._app_state as _app_state

configure_logging()
_logger = logging.getLogger("aletheia.api")

# Re-export for backward compatibility with tests and external callers.
from core.rate_limit import rate_limiter  # noqa: E402


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Async lifespan handler — manages Redis/Postgres pool lifecycle."""
    from core.db import close_asyncpg_pool, init_optional_postgres_pool
    from core.exporters import start_export_workers, stop_export_workers
    from core.redis_pool import close_redis_pool, get_redis_pool
    from core.config import validate_fips_compliance, validate_production_config

    _app_state._ready = False
    _app_state._startup_error_detail = "startup in progress"

    _logger.info("Lifespan startup: initialising connection pools…")

    pg_pool = None
    startup_ok = False

    try:
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

        pool = await get_redis_pool()
        if pool is not None:
            try:
                await pool.ping()  # type: ignore[union-attr]
                _logger.info("Redis pool: connected and healthy")
            except Exception as exc:
                _logger.error("Redis pool: ping failed — %s", exc)
        else:
            _logger.info("Redis pool: not configured (using Upstash or in-memory)")

        try:
            pg_pool = await init_optional_postgres_pool()
            if pg_pool is not None:
                _logger.info("Postgres pool: connected and healthy")
        except Exception as exc:
            _logger.error("Postgres pool: connection failed — %s", exc)
            if os.getenv("ENVIRONMENT", "").lower() == "production":
                raise RuntimeError("critical startup failure: postgres unavailable")

        await _init_bridge_pool()

        await _startup_checks()
        start_export_workers()

        asyncio.create_task(asyncio.to_thread(warm_up))

        try:
            from pathlib import Path

            from core.manifest_cache import load_and_embed_manifest
            from sentence_transformers import SentenceTransformer

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

        _app_state._ready = True
        _app_state._startup_error_detail = ""
        startup_ok = True
    except BaseException as exc:
        _app_state._ready = False
        _app_state._startup_error_detail = str(exc) or "critical startup failure"
        _logger.exception("Startup failed; service will report not ready: %s", exc)

    from core.exporters import stop_export_workers  # noqa: F811

    yield

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
if _is_production and "*" in _CORS_ORIGINS:
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

# FastAPI applies middleware LIFO: internal_secret_guard runs first.
app.middleware("http")(add_security_and_rate_limit_headers)
app.middleware("http")(enterprise_auth_middleware)
app.middleware("http")(internal_secret_guard)


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


app.include_router(health_router)
app.include_router(audit_router)
app.include_router(keys_router)
app.websocket("/ws/audit")(ws_audit_endpoint)
