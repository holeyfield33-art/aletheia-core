# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Audit, evaluate, and agent-trifecta route handlers."""
from __future__ import annotations

import logging
import os
import time as _time
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.agent_trifecta import AgentTrifectaContext, evaluate_agent_trifecta
from core.audit import (
    ReceiptVerificationError,
    log_audit_event,
    verify_receipt_or_raise,
)
from core.auth.models import AuthContext
from core.config import settings
from core.decision_store import decision_store
from core.metrics import (
    AUDIT_DECISIONS_TOTAL,
    AUDIT_EVALUATION_DURATION_SECONDS,
    LATENCY_HISTOGRAM,
    REQUEST_COUNTER,
)
from core.rate_limit import rate_limiter
from core.runtime_security import (
    build_layered_normalization_candidates,
    classify_blocked_intent,
    is_semantic_engine_degraded,
)
from core.sandbox import check_action_sandbox
from server._bridge import _log_audit_and_persist
from server._deps import _check_api_key, _check_eval_rate_limit
from server._helpers import (
    _build_audit_envelope,
    _discretise_threat,
    _evaluate_layers,
    _get_client_ip,
    _is_read_only_action,
    _run_nitpicker,
    _sanitise_reason,
)
from server._state import _get_sovereign_runtime, nitpicker
from server.models import (
    AgentTrifectaAuditRequest,
    AgentTrifectaAuditResponse,
    AgentTrifectaMetadata,
    AuditRequest,
    EvaluateRequest,
    VerifyReceiptRequest,
)
from server.utils import normalize_shadow_text

_logger = logging.getLogger("aletheia.api")

router = APIRouter()


@router.post("/v1/verify", dependencies=[Depends(_check_api_key)])
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


@router.post(
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

    clean_input = normalize_shadow_text(req.payload)

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


@router.post("/v1/audit", dependencies=[Depends(_check_api_key)], response_model=None)
async def secure_audit(req: AuditRequest, request: Request) -> Any:
    import uuid

    client_ip = _get_client_ip(request)
    request_id = str(uuid.uuid4())
    start_time = _time.time()

    ctx: AuthContext | None = getattr(request.state, "auth_context", None)
    _tenant_id = ctx.user.tenant_id if ctx and ctx.user.tenant_id else "default"
    _user_id = ctx.user.user_id if ctx else getattr(request.state, "api_user_id", "")
    _auth_method = ctx.user.auth_method if ctx else ""

    _nit_last = getattr(nitpicker, "_last_result", None)
    _semantic_degraded = is_semantic_engine_degraded(_nit_last)

    from server._state import judge

    _manifest_missing = judge.policy is None
    degraded = bool(
        getattr(rate_limiter, "degraded", False)
        or decision_store.degraded
        or _semantic_degraded
        or _manifest_missing
    )
    fallback_state = "degraded" if degraded else "normal"

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

    clean_input = normalize_shadow_text(req.payload)

    layered_probe = build_layered_normalization_candidates(req.payload, max_depth=3)
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
        payload=req.payload,
        client_ip=client_ip,
        request_id=request_id,
    )

    _, _, clean_content = _run_nitpicker(  # noqa: F841
        clean_input,
        req.origin,
        request_id=request_id,
        sanitize=True,
    )

    _nit_last_post = getattr(nitpicker, "_last_result", None)
    if is_semantic_engine_degraded(_nit_last_post):
        degraded = True

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

    REQUEST_COUNTER.labels(agent="pipeline", verdict=decision).inc()
    LATENCY_HISTOGRAM.observe(latency / 1000)
    AUDIT_DECISIONS_TOTAL.labels(decision=decision.lower()).inc()
    AUDIT_EVALUATION_DURATION_SECONDS.observe(latency / 1000)

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
        _logger.info(
            "shadow_verdict=DENIED action=%s origin=%s", req.action, req.origin
        )
    return response


@router.post(
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


