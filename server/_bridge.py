# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""asyncpg bridge pool and hosted-Prisma persistence shims.

The pool is initialised during lifespan startup via _init_bridge_pool() and
closed via _close_bridge_pool(). All helper functions reference the module-level
_bridge_pool at call time so they see the post-startup value.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from core.auth.hosted_prisma_bridge import (
    check_hosted_prisma_api_key,
    current_utc_month_bounds,
    hash_hosted_api_key,
    lookup_hosted_api_key_user_id,
    normalize_utc,
)
from core.config import settings
from core.db import close_asyncpg_pool, create_asyncpg_pool, probe_asyncpg_pool
from core.key_store import QuotaCheck
from core.persistence.hosted_audit_log import (
    generate_cuid,
    persist_audit_log,
    persist_hosted_audit_log,
)

_logger = logging.getLogger("aletheia.api")

_bridge_pool: Any | None = None


async def _init_bridge_pool() -> None:
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


def _hash_hosted_api_key(raw_key: str) -> str:
    return hash_hosted_api_key(raw_key, os.getenv("ALETHEIA_KEY_SALT", ""))


def _normalize_utc(ts: datetime) -> datetime:
    return normalize_utc(ts)


def _current_utc_month_bounds(now: datetime) -> tuple[datetime, datetime]:
    return current_utc_month_bounds(now)


async def _check_hosted_prisma_api_key(raw_key: str) -> QuotaCheck | None:
    return await check_hosted_prisma_api_key(
        raw_key,
        pool=_bridge_pool,
        key_salt=os.getenv("ALETHEIA_KEY_SALT", ""),
        logger=_logger,
    )


async def _lookup_hosted_api_key_user_id(raw_key: str) -> str:
    return await lookup_hosted_api_key_user_id(
        raw_key,
        pool=_bridge_pool,
        key_salt=os.getenv("ALETHEIA_KEY_SALT", ""),
        logger=_logger,
    )


def _generate_cuid() -> str:
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


async def _persist_hosted_audit_log(
    audit_record: dict[str, Any], user_id: str
) -> None:
    await persist_hosted_audit_log(
        pool=_bridge_pool,
        logger=_logger,
        audit_record=audit_record,
        user_id=user_id,
    )


async def _log_audit_and_persist(*, user_id: str, **kwargs: Any) -> dict[str, Any]:
    from core.audit import log_audit_event

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
