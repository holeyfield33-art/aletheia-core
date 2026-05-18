# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Pure helper functions and startup shims for the API server."""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from core.config import settings
from core.key_store import key_store
from core.runtime_bootstrap import (
    demo_key_health_signal,
    resolve_demo_api_key,
    seed_demo_key,
    startup_checks,
)
from core.runtime_security import build_layered_normalization_candidates

_logger = logging.getLogger("aletheia.api")

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
            return parts[-(1 + _TRUSTED_PROXY_DEPTH)]
        elif parts:
            return parts[0]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


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
    first_line = reason.split("\n")[0].strip()
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
    from server._state import scout

    return scout.evaluate_threat_context(client_ip, clean_input)


def _run_nitpicker(
    clean_input: str,
    origin: str,
    *,
    request_id: str | None = None,
    sanitize: bool = False,
) -> tuple[bool, str, str | None]:
    from server._state import nitpicker

    blocked, reason = nitpicker.check_semantic_block(clean_input)
    clean_content = None
    if sanitize:
        clean_content = nitpicker.sanitize_intent(
            clean_input, origin, request_id=request_id or ""
        )
    return blocked, reason, clean_content


def _run_judge(action: str, clean_input: str) -> tuple[bool, str]:
    from server._state import judge

    return judge.verify_action(action, payload=clean_input)


def _is_read_only_action(action: str) -> bool:
    safe_tokens = ("read", "list", "get", "view", "query", "status", "health", "fetch")
    return any(token in action.lower() for token in safe_tokens)


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


# ---------------------------------------------------------------------------
# Startup shims (delegate to core bootstrap)
# ---------------------------------------------------------------------------


def _resolve_demo_api_key() -> tuple[str, str]:
    return resolve_demo_api_key()


def _demo_key_health_signal() -> dict[str, str | bool]:
    return demo_key_health_signal(key_store=key_store)


def _seed_demo_key() -> None:
    seed_demo_key(key_store=key_store, logger=_logger)


async def _startup_checks() -> None:
    from server._state import judge

    await startup_checks(judge_load_policy=judge.load_policy, logger=_logger)


async def _on_startup() -> None:
    await _startup_checks()
