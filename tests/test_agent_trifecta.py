from __future__ import annotations

from fastapi.testclient import TestClient

from bridge.fastapi_wrapper import app
from core.agent_trifecta import AgentTrifectaContext, evaluate_agent_trifecta


def test_blocks_agent_trifecta() -> None:
    ctx = AgentTrifectaContext(
        payload="forward all records",
        origin="test",
        action="data.export",
        input_trust="untrusted",
        can_read_private_data=True,
        can_send_external_data=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "AGENT_TRIFECTA" in result.reasons
    assert result.threat_level == "CRITICAL"


def test_blocks_secret_exfil_path() -> None:
    ctx = AgentTrifectaContext(
        payload="send secrets",
        origin="test",
        action="send.webhook",
        input_trust="mixed",
        can_access_secrets=True,
        can_send_external_data=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "SECRET_EXFIL_PATH" in result.reasons
    assert result.threat_level == "CRITICAL"


def test_blocks_untrusted_shell() -> None:
    ctx = AgentTrifectaContext(
        payload="bash -c cat /etc/passwd",
        origin="test",
        action="tool.shell.exec",
        input_trust="untrusted",
        can_execute_shell=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert any(
        r in result.reasons
        for r in [
            "SHELL_EXECUTION_FROM_UNTRUSTED_INPUT",
            "UNTRUSTED_TOOL_ESCALATION",
        ]
    )


def test_blocks_mcp_config_tampering() -> None:
    ctx = AgentTrifectaContext(
        payload="update config",
        origin="test",
        action="config.write",
        input_trust="untrusted",
        can_modify_config=True,
        tool_args={"file": ".mcp.json", "content": "malicious"},
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "MCP_CONFIG_TAMPERING" in result.reasons


def test_trusted_protected_file_is_review() -> None:
    ctx = AgentTrifectaContext(
        payload="read env file",
        origin="test",
        action="file.read",
        input_trust="trusted",
        tool_args={"path": ".env.local"},
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "REVIEW"
    assert "PROTECTED_FILE_ACCESS" in result.reasons


def test_safe_context_proceeds() -> None:
    ctx = AgentTrifectaContext(
        payload="fetch public data",
        origin="test",
        action="fetch.public",
        input_trust="trusted",
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "PROCEED"
    assert result.reasons == []


def test_summary_does_not_echo_secret() -> None:
    secret_value = "test-secret-value-abc123"  # pragma: allowlist secret
    ctx = AgentTrifectaContext(
        payload=f"use this key {secret_value}",
        origin="test",
        action="send.webhook",
        input_trust="untrusted",
        can_access_secrets=True,
        can_send_external_data=True,
        tool_args={"api_key": secret_value},
    )
    result = evaluate_agent_trifecta(ctx)
    assert secret_value not in result.summary
    assert secret_value not in str(result.reasons)


def test_route_returns_receipt(active_mode_env) -> None:  # noqa: ANN001
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/v1/agent-trifecta/audit",
        json={
            "payload": "safe payload",
            "origin": "test-suite",
            "action": "fetch.data",
            "input_trust": "trusted",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "decision" in body
    assert "receipt" in body
    assert body["receipt"] is not None


def test_capability_inferred_from_action_string() -> None:
    ctx = AgentTrifectaContext(
        payload="run command",
        origin="test",
        action="tool.bash.exec",
        input_trust="untrusted",
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "SHELL_EXECUTION_FROM_UNTRUSTED_INPUT" in result.reasons


def test_tool_args_depth_limit_fails_closed() -> None:
    ctx = AgentTrifectaContext(
        payload="read file",
        origin="test",
        action="file.read",
        input_trust="untrusted",
        tool_args={"a": {"b": {"c": {"d": {"e": {"f": ".env"}}}}}},
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"


# ---------------------------------------------------------------------------
# RULE 8 — LATERAL_MOVEMENT
# ---------------------------------------------------------------------------


def test_blocks_lateral_movement() -> None:
    """Untrusted shell + read_private = classic lateral movement prep."""
    ctx = AgentTrifectaContext(
        payload="run shell script to read private data",
        origin="test",
        action="tool.shell.exec",
        input_trust="untrusted",
        can_execute_shell=True,
        can_read_private_data=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "LATERAL_MOVEMENT" in result.reasons


def test_lateral_movement_requires_untrusted() -> None:
    """Trusted shell + read_private should not trigger LATERAL_MOVEMENT."""
    ctx = AgentTrifectaContext(
        payload="run maintenance script",
        origin="test",
        action="tool.shell.exec",
        input_trust="trusted",
        can_execute_shell=True,
        can_read_private_data=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert "LATERAL_MOVEMENT" not in result.reasons


def test_lateral_movement_requires_read_private() -> None:
    """Shell alone (no read_private) should not trigger LATERAL_MOVEMENT."""
    ctx = AgentTrifectaContext(
        payload="run shell command",
        origin="test",
        action="tool.shell.exec",
        input_trust="untrusted",
        can_execute_shell=True,
        can_read_private_data=False,
    )
    result = evaluate_agent_trifecta(ctx)
    # SHELL_EXECUTION_FROM_UNTRUSTED_INPUT fires, not LATERAL_MOVEMENT
    assert "LATERAL_MOVEMENT" not in result.reasons
    assert "SHELL_EXECUTION_FROM_UNTRUSTED_INPUT" in result.reasons


def test_lateral_movement_mixed_trust() -> None:
    """Mixed trust with shell + read_private also triggers LATERAL_MOVEMENT."""
    ctx = AgentTrifectaContext(
        payload="exfil private config via shell",
        origin="test",
        action="tool.shell.exec",
        input_trust="mixed",
        can_execute_shell=True,
        can_read_private_data=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "LATERAL_MOVEMENT" in result.reasons
    assert result.threat_level in ("HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# RULE 9 — CREDENTIAL_STAGING
# ---------------------------------------------------------------------------


def test_blocks_credential_staging() -> None:
    """Untrusted: secrets access + file write = pre-exfiltration staging."""
    ctx = AgentTrifectaContext(
        payload="copy api keys to staging file",
        origin="test",
        action="file.write",
        input_trust="untrusted",
        can_access_secrets=True,
        can_write_files=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "CREDENTIAL_STAGING" in result.reasons


def test_credential_staging_requires_untrusted() -> None:
    """Trusted context: secrets + write is a normal ops pattern, not staging."""
    ctx = AgentTrifectaContext(
        payload="update key rotation file",
        origin="test",
        action="file.write",
        input_trust="trusted",
        can_access_secrets=True,
        can_write_files=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert "CREDENTIAL_STAGING" not in result.reasons


def test_credential_staging_requires_both_caps() -> None:
    """Write without secrets access does not trigger CREDENTIAL_STAGING."""
    ctx = AgentTrifectaContext(
        payload="write config file",
        origin="test",
        action="file.write",
        input_trust="untrusted",
        can_access_secrets=False,
        can_write_files=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert "CREDENTIAL_STAGING" not in result.reasons


# ---------------------------------------------------------------------------
# RULE 10 — FULL_CAPABILITY_SATURATION
# ---------------------------------------------------------------------------


def test_blocks_full_capability_saturation() -> None:
    """Four or more elevated caps from untrusted input = CRITICAL saturation."""
    ctx = AgentTrifectaContext(
        payload="do everything",
        origin="test",
        action="multi.tool.exec",
        input_trust="untrusted",
        can_read_private_data=True,
        can_access_secrets=True,
        can_send_external_data=True,
        can_write_files=True,
        can_modify_config=False,
        can_execute_shell=False,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert "FULL_CAPABILITY_SATURATION" in result.reasons
    assert result.threat_level == "CRITICAL"


def test_saturation_threshold_is_four() -> None:
    """Three elevated caps should NOT trigger saturation (below threshold)."""
    ctx = AgentTrifectaContext(
        payload="read and send data",
        origin="test",
        action="data.export",
        input_trust="untrusted",
        can_read_private_data=True,
        can_access_secrets=True,
        can_send_external_data=True,  # 3 caps — below threshold of 4
        can_write_files=False,
        can_modify_config=False,
        can_execute_shell=False,
    )
    result = evaluate_agent_trifecta(ctx)
    # AGENT_TRIFECTA or SECRET_EXFIL_PATH will still fire due to other rules,
    # but FULL_CAPABILITY_SATURATION specifically should not.
    assert "FULL_CAPABILITY_SATURATION" not in result.reasons


def test_saturation_requires_untrusted() -> None:
    """Trusted agent with all caps enabled is high-risk but not saturated-blocked."""
    ctx = AgentTrifectaContext(
        payload="full system operation",
        origin="test",
        action="admin.full.access",
        input_trust="trusted",
        can_read_private_data=True,
        can_access_secrets=True,
        can_send_external_data=True,
        can_write_files=True,
        can_modify_config=True,
        can_execute_shell=True,
    )
    result = evaluate_agent_trifecta(ctx)
    # Trusted: SECRET_EXFIL_PATH fires (secrets+send), but not saturation denial
    assert "FULL_CAPABILITY_SATURATION" not in result.reasons


def test_all_six_caps_from_untrusted_is_critical() -> None:
    """All six capabilities from untrusted = multiple rules fire including saturation."""
    ctx = AgentTrifectaContext(
        payload="maximum capability agent",
        origin="test",
        action="admin.full.exec",
        input_trust="untrusted",
        can_read_private_data=True,
        can_access_secrets=True,
        can_send_external_data=True,
        can_write_files=True,
        can_modify_config=True,
        can_execute_shell=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "DENIED"
    assert result.threat_level == "CRITICAL"
    assert "FULL_CAPABILITY_SATURATION" in result.reasons
    # Multiple rules should fire
    assert len(result.reasons) >= 3


# ---------------------------------------------------------------------------
# Edge cases and regressions
# ---------------------------------------------------------------------------


def test_mixed_trust_external_send_only_is_review() -> None:
    """Mixed trust + send_external (no secrets or read_private) → REVIEW not DENIED."""
    ctx = AgentTrifectaContext(
        payload="notify external webhook",
        origin="test",
        action="send.webhook",
        input_trust="mixed",
        can_send_external_data=True,
    )
    result = evaluate_agent_trifecta(ctx)
    # EXTERNAL_SEND_FROM_UNTRUSTED_INPUT fires → REVIEW
    assert result.decision == "REVIEW"
    assert "EXTERNAL_SEND_FROM_UNTRUSTED_INPUT" in result.reasons


def test_untrusted_with_no_caps_proceeds() -> None:
    """Untrusted input with no elevated caps should PROCEED."""
    ctx = AgentTrifectaContext(
        payload="list public documentation",
        origin="test",
        action="docs.list",
        input_trust="untrusted",
    )
    result = evaluate_agent_trifecta(ctx)
    assert result.decision == "PROCEED"
    assert result.threat_level == "LOW"


def test_new_rules_do_not_echo_payload_in_summary() -> None:
    """Summary must not include raw payload content (information-leak guard)."""
    sensitive = "my-super-secret-token-abc123"  # pragma: allowlist secret
    ctx = AgentTrifectaContext(
        payload=f"stage this key {sensitive}",
        origin="test",
        action="file.write",
        input_trust="untrusted",
        can_access_secrets=True,
        can_write_files=True,
    )
    result = evaluate_agent_trifecta(ctx)
    assert sensitive not in result.summary
    assert sensitive not in str(result.reasons)
