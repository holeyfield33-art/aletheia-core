# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""API-key authentication flow helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from core.key_store import QuotaCheck


@dataclass(frozen=True)
class APIKeyAuthResult:
    quota: QuotaCheck
    user_id: str = ""


async def authenticate_api_key(
    api_key: str,
    *,
    key_store: Any,
    hosted_quota_checker: Callable[[str], Awaitable[QuotaCheck | None]],
    hosted_user_lookup: Callable[[str], Awaitable[str]],
    logger: Any,
) -> APIKeyAuthResult:
    """Authenticate an API key with hosted fallback and optional user lookup."""
    quota = key_store.check_and_increment(api_key)
    if not quota.allowed and "Invalid" in quota.reason:
        hosted_quota = await hosted_quota_checker(api_key)
        if hosted_quota is not None:
            user_id = ""
            if hosted_quota.allowed:
                logger.info("api key authenticated via hosted Prisma fallback")
                user_id = await hosted_user_lookup(api_key)
            return APIKeyAuthResult(quota=hosted_quota, user_id=user_id)
    return APIKeyAuthResult(quota=quota)
