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
