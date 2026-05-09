# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""API-key parsing and deterministic error mapping helpers."""

from __future__ import annotations

from fastapi import HTTPException

from core.key_store import QuotaCheck


def resolve_api_key(x_api_key: str | None, authorization_header: str | None) -> str:
    """Resolve API key from X-API-Key or Bearer Authorization header."""
    api_key = (x_api_key or "").strip()
    if api_key:
        return api_key

    auth_header = (authorization_header or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return ""


def raise_for_quota_failure(quota: QuotaCheck) -> None:
    """Raise canonical HTTP errors for quota/auth failures."""
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
