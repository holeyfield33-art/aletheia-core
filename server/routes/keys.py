# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Key management and secret rotation route handlers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from core.auth.rbac import Permission, require_permission
from core.key_store import key_store
from core.secret_rotation import rotate_secrets
from server._state import judge
from server.models import CreateKeyRequest

router = APIRouter()


@router.post(
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


@router.get(
    "/v1/keys", dependencies=[Depends(require_permission(Permission.KEYS_LIST))]
)
async def list_keys() -> JSONResponse:
    """List all API keys (metadata only — no raw keys or hashes)."""
    records = key_store.list_keys()
    return JSONResponse(
        content={"keys": [r.to_public_dict() for r in records]},
    )


@router.delete(
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


@router.get(
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


@router.post(
    "/v1/rotate",
    dependencies=[Depends(require_permission(Permission.SECRETS_ROTATE))],
)
async def rotate_secrets_endpoint() -> JSONResponse:
    """Hot-rotate secrets without restart. Admin-only, rate-limited by cooldown."""
    result = rotate_secrets(
        reload_api_keys_fn=None,
        reload_judge_fn=judge.load_policy,
    )
    status_code = 200 if result.get("status") == "rotated" else 429
    return JSONResponse(content=result, status_code=status_code)
