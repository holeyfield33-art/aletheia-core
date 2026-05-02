from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

_logger = logging.getLogger("aletheia.agent_trifecta")

PROTECTED_PATHS = frozenset(
    [
        ".env",
        ".env.local",
        ".env.production",
        ".env.staging",
        ".mcp.json",
        "mcp.json",
        "claude_desktop_config.json",
        ".github/workflows/",
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
        ".ssh/",
        "credentials.json",
        "service_account.json",
    ]
)


@dataclass
class AgentTrifectaContext:
    payload: str
    origin: str
    action: str
    input_trust: Literal["trusted", "untrusted", "mixed"]
    can_read_private_data: bool = False
    can_access_secrets: bool = False
    can_send_external_data: bool = False
    can_write_files: bool = False
    can_modify_config: bool = False
    can_execute_shell: bool = False
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTrifectaDecision:
    decision: Literal["PROCEED", "REVIEW", "DENIED"]
    threat_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reasons: list[str]
    summary: str


def _infer_capabilities(ctx: AgentTrifectaContext) -> None:
    action = (ctx.action or "").lower()

    if not ctx.can_execute_shell and any(
        token in action
        for token in ("shell", "exec", "run", "bash", "cmd", "subprocess")
    ):
        ctx.can_execute_shell = True

    if not ctx.can_send_external_data and any(
        token in action
        for token in (
            "send",
            "email",
            "webhook",
            "http",
            "post",
            "egress",
            "notify",
            "forward",
            "upload",
            "transfer",
        )
    ):
        ctx.can_send_external_data = True

    if not ctx.can_modify_config and any(
        token in action for token in ("config", "settings", "mcp", "env", "manifest")
    ):
        ctx.can_modify_config = True

    if not ctx.can_read_private_data and any(
        token in action
        for token in (
            "file",
            "read",
            "open",
            "cat",
            "fs",
            "readfile",
            "download",
            "fetch_file",
        )
    ):
        ctx.can_read_private_data = True

    _logger.debug(
        "agent_trifecta inferred flags: read_private=%s access_secrets=%s send_external=%s "
        "modify_config=%s exec_shell=%s",
        ctx.can_read_private_data,
        ctx.can_access_secrets,
        ctx.can_send_external_data,
        ctx.can_modify_config,
        ctx.can_execute_shell,
    )


def _contains_protected_path(tool_args: dict[str, Any], depth: int = 0) -> bool:
    try:
        serialized = json.dumps(tool_args, default=str)
    except Exception:
        return True

    if len(serialized) > 4096:
        return True
    if depth > 5:
        return True

    def _match_string(value: str) -> bool:
        lower = value.lower()
        return any(path in lower for path in PROTECTED_PATHS)

    def _walk(value: Any, cur_depth: int) -> bool:
        if cur_depth > 5:
            return True

        if isinstance(value, str):
            return _match_string(value)

        if isinstance(value, dict):
            for k, v in value.items():
                if _match_string(str(k)):
                    return True
                if _walk(v, cur_depth + 1):
                    return True
            return False

        if isinstance(value, (list, tuple, set)):
            for item in value:
                if _walk(item, cur_depth + 1):
                    return True
            return False

        return False

    return _walk(tool_args, depth)


def _resolve_summary(
    decision: str,
    threat_level: str,
    reasons: list[str],
) -> str:
    if not reasons:
        return "Agent context evaluated. No high-risk capability combination detected."

    reason_text = ", ".join(reasons)
    if decision == "DENIED" and threat_level == "CRITICAL":
        return (
            f"Blocked untrusted agent context with {reason_text} - critical capability "
            "combination detected."
        )[:159]
    if decision == "DENIED" and threat_level == "HIGH":
        return (
            f"Blocked agent action due to high-risk capability in untrusted context: {reason_text}."
        )[:159]
    if decision == "REVIEW":
        return (
            f"Agent action flagged for review: {reason_text}. Manual approval recommended before "
            "execution."
        )[:159]
    return "Agent context evaluated. No high-risk capability combination detected."


def evaluate_agent_trifecta(ctx: AgentTrifectaContext) -> AgentTrifectaDecision:
    _infer_capabilities(ctx)

    denied_reasons: list[str] = []
    review_reasons: list[str] = []
    severity = "LOW"

    def _bump(level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]) -> None:
        nonlocal severity
        order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        if order[level] > order[severity]:
            severity = level

    untrusted_or_mixed = ctx.input_trust in ("untrusted", "mixed")

    # RULE 1 — AGENT_TRIFECTA
    if (
        untrusted_or_mixed
        and (ctx.can_read_private_data or ctx.can_access_secrets)
        and ctx.can_send_external_data
    ):
        denied_reasons.append("AGENT_TRIFECTA")
        _bump("CRITICAL")

    # RULE 2 — SECRET_EXFIL_PATH
    if ctx.can_access_secrets and ctx.can_send_external_data:
        denied_reasons.append("SECRET_EXFIL_PATH")
        _bump("CRITICAL")

    # RULE 3 — MCP_CONFIG_TAMPERING
    if untrusted_or_mixed and ctx.can_modify_config:
        denied_reasons.append("MCP_CONFIG_TAMPERING")
        _bump("HIGH")

    # RULE 4 — SHELL_EXECUTION_FROM_UNTRUSTED_INPUT
    if untrusted_or_mixed and ctx.can_execute_shell:
        denied_reasons.append("SHELL_EXECUTION_FROM_UNTRUSTED_INPUT")
        _bump("HIGH")

    # RULE 5 — EXTERNAL_SEND_FROM_UNTRUSTED_INPUT
    if (
        untrusted_or_mixed
        and ctx.can_send_external_data
        and "AGENT_TRIFECTA" not in denied_reasons
        and "SECRET_EXFIL_PATH" not in denied_reasons
    ):
        review_reasons.append("EXTERNAL_SEND_FROM_UNTRUSTED_INPUT")
        _bump("MEDIUM")

    # RULE 6 — PROTECTED_FILE_ACCESS
    if _contains_protected_path(ctx.tool_args):
        if untrusted_or_mixed:
            denied_reasons.append("PROTECTED_FILE_ACCESS")
            _bump("HIGH")
        else:
            review_reasons.append("PROTECTED_FILE_ACCESS")
            _bump("MEDIUM")

    # RULE 7 — UNTRUSTED_TOOL_ESCALATION
    try:
        from core.sandbox import check_action_sandbox
    except ImportError as exc:
        _logger.warning("Sandbox import failed; skipping escalation rule: %s", exc)
    else:
        try:
            sandbox_hit = check_action_sandbox(ctx.action, ctx.payload)
            if sandbox_hit and untrusted_or_mixed:
                denied_reasons.append("UNTRUSTED_TOOL_ESCALATION")
                _bump("HIGH")
        except Exception as exc:
            _logger.warning("Sandbox check failed; skipping escalation rule: %s", exc)

    if denied_reasons:
        reasons = denied_reasons + [
            r for r in review_reasons if r not in denied_reasons
        ]
        decision = "DENIED"
    elif review_reasons:
        reasons = review_reasons
        decision = "REVIEW"
    else:
        reasons = []
        decision = "PROCEED"

    summary = _resolve_summary(decision, severity, reasons)

    return AgentTrifectaDecision(
        decision=decision,
        threat_level=severity,
        reasons=reasons,
        summary=summary,
    )
