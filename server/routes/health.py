# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Health, readiness, metrics, and public-key routes."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time as _time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from core.auth import get_auth_provider
from core.config import settings
from core.metrics import metrics_response
from core.runtime_status import collect_dependency_health, collect_manifest_readiness
from server._app_state import _BOOT_TIME
from server._helpers import _demo_key_health_signal

import server._app_state as _state

_logger = logging.getLogger("aletheia.api")

router = APIRouter()


def _read_manifest_public_key() -> str:
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


@router.get("/.well-known/aletheia-receipt-key.pem")
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


@router.get("/.well-known/aletheia-manifest-key.pem")
async def manifest_public_key() -> Response:
    """Serve the manifest signature verification key."""
    return Response(
        content=_read_manifest_public_key(),
        media_type="application/x-pem-file",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/v1/public-key")
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


@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Gateway health and readiness endpoint.

    This endpoint intentionally avoids policy/model checks so it stays fast
    even while heavy components are still warming up.
    """
    startup_pending = _state._startup_error_detail in {
        "startup not completed",
        "startup in progress",
    }

    dependency_health = await collect_dependency_health()
    dependencies_ready = dependency_health.all_ready
    status_text = "ok" if (_state._ready and dependencies_ready) else "degraded"

    body: dict[str, object] = {
        "status": status_text,
        "service": "aletheia-core",
    }

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
                "version": request.app.version,
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

    if dependencies_ready and (_state._ready or startup_pending):
        return JSONResponse(status_code=200, content=body)

    body["detail"] = _state._startup_error_detail or "critical startup failure"
    return JSONResponse(status_code=503, content=body)


@router.get("/ready")
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
    return JSONResponse(status_code=200 if ready else 503, content=body)


@router.get("/metrics")
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
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            return JSONResponse(
                status_code=403,
                content={
                    "error": "metrics_disabled",
                    "message": "ALETHEIA_METRICS_TOKEN not configured. Metrics disabled in production.",
                },
            )
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
