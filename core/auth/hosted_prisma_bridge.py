# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Hosted Prisma API-key fallback helpers."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from core.key_store import QuotaCheck


def hash_hosted_api_key(raw_key: str, key_salt: str) -> str:
    """Mirror Next.js key hashing for hosted Prisma ApiKey records."""
    if key_salt:
        return hmac.new(
            key_salt.encode("utf-8"), raw_key.encode("utf-8"), hashlib.sha256
        ).hexdigest()
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def normalize_utc(ts: datetime) -> datetime:
    """Normalize timestamps from Postgres for UTC-safe comparisons."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def current_utc_month_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return the current UTC month [start, end) boundaries."""
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)
    return period_start, period_end


async def check_hosted_prisma_api_key(
    raw_key: str,
    *,
    pool: Any,
    key_salt: str,
    logger: Any,
) -> QuotaCheck | None:
    """Validate and meter hosted Prisma ApiKey records when SQLite misses."""
    if pool is None:
        return None

    try:
        key_hash = hash_hosted_api_key(raw_key, key_salt)
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT id, status, "monthlyQuota", "requestsUsed",
                           "periodStart", "periodEnd"
                    FROM "ApiKey"
                    WHERE "keyHash" = $1
                    LIMIT 1
                    FOR UPDATE
                    """,
                    key_hash,
                )
                if not row:
                    return QuotaCheck(
                        allowed=False,
                        reason="Invalid API key.",
                        requests_used=0,
                        monthly_quota=0,
                    )

                status = (row["status"] or "").lower()
                if status != "active":
                    return QuotaCheck(
                        allowed=False,
                        reason="API key is revoked.",
                        requests_used=int(row["requestsUsed"]),
                        monthly_quota=int(row["monthlyQuota"]),
                    )

                now = datetime.now(timezone.utc)
                requests_used = int(row["requestsUsed"])
                monthly_quota = int(row["monthlyQuota"])
                period_start = normalize_utc(row["periodStart"])
                period_end = normalize_utc(row["periodEnd"])

                if now >= period_end:
                    period_start, period_end = current_utc_month_bounds(now)
                    requests_used = 0

                if requests_used >= monthly_quota:
                    return QuotaCheck(
                        allowed=False,
                        reason=(
                            f"Monthly request limit exceeded "
                            f"({requests_used}/{monthly_quota})."
                        ),
                        requests_used=requests_used,
                        monthly_quota=monthly_quota,
                    )

                next_used = requests_used + 1
                await conn.execute(
                    """
                    UPDATE "ApiKey"
                    SET "requestsUsed" = $2,
                        "periodStart" = $3,
                        "periodEnd" = $4,
                        "lastUsedAt" = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                    next_used,
                    period_start.replace(tzinfo=None),
                    period_end.replace(tzinfo=None),
                )

                return QuotaCheck(
                    allowed=True,
                    reason="OK",
                    requests_used=next_used,
                    monthly_quota=monthly_quota,
                )
    except Exception as exc:
        logger.warning("Hosted Prisma key lookup failed (fail-closed): %s", exc)
        return None


async def lookup_hosted_api_key_user_id(
    raw_key: str,
    *,
    pool: Any,
    key_salt: str,
    logger: Any,
) -> str:
    """Resolve Prisma ApiKey.userId for dashboard-scoped AuditLog persistence."""
    if pool is None:
        return ""

    try:
        key_hash = hash_hosted_api_key(raw_key, key_salt)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT "userId" FROM "ApiKey" WHERE "keyHash" = $1 LIMIT 1',
                key_hash,
            )
            if not row:
                return ""
            user_id = row["userId"]
            return str(user_id) if user_id else ""
    except Exception as exc:
        logger.warning("Hosted Prisma user lookup failed: %s", exc)
        return ""
