# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Hosted Prisma AuditLog persistence helpers."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any


def generate_cuid() -> str:
    """Generate a Prisma-compatible compact ID for hosted AuditLog rows."""
    timestamp_ms = int(time.time() * 1000)
    random_block = secrets.token_hex(8)
    return f"c{timestamp_ms:x}{random_block}"[:25]


async def persist_audit_log(
    *,
    pool: Any,
    logger: Any,
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
    """Insert one row into Prisma AuditLog for dashboard visibility."""
    if pool is None:
        return

    try:
        async with pool.acquire() as conn:
            if user_id:
                await conn.execute(
                    """
                    INSERT INTO "User" (id, "updatedAt")
                    VALUES ($1, NOW())
                    ON CONFLICT (id) DO UPDATE SET "updatedAt" = EXCLUDED."updatedAt"
                    """,
                    user_id,
                )
            await conn.execute(
                """
                INSERT INTO "AuditLog" (
                    id, "userId", decision, "threatScore", action, origin,
                    "sourceIp", reason, "latencyMs", "payloadHash", "policyHash",
                    "requestId", receipt, "createdAt"
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, NOW())
                """,
                generate_cuid(),
                user_id or None,
                decision,
                float(threat_score),
                action,
                origin,
                source_ip or None,
                reason or None,
                float(latency_ms),
                payload_hash or None,
                policy_hash or None,
                request_id or None,
                json.dumps(receipt) if receipt else None,
            )
    except Exception as exc:
        logger.warning(
            "audit_log_persist_failed request_id=%s err=%s",
            request_id,
            exc,
        )


async def persist_hosted_audit_log(
    *,
    pool: Any,
    logger: Any,
    audit_record: dict[str, Any],
    user_id: str,
) -> None:
    """Best-effort mirror of /v1/audit decisions to Prisma AuditLog."""
    await persist_audit_log(
        pool=pool,
        logger=logger,
        user_id=user_id,
        decision=str(audit_record.get("decision", "")),
        threat_score=float(audit_record.get("threat_score", 0.0)),
        action=str(audit_record.get("action", "")),
        origin=str(audit_record.get("origin", "")),
        source_ip=str(audit_record.get("source_ip", "")),
        reason=str(audit_record.get("reason", "")),
        latency_ms=float(audit_record.get("latency_ms", 0.0)),
        payload_hash=str(audit_record.get("payload_sha256", "")),
        policy_hash=str(audit_record.get("policy_hash", "")),
        request_id=str(audit_record.get("request_id", "")),
        receipt=audit_record.get("receipt")
        if isinstance(audit_record.get("receipt"), dict)
        else None,
    )
