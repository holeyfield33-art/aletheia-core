"""Pydantic request and response models for the Aletheia API server."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core.agent_trifecta import Decision, ThreatLevel


class CreateKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=64)
    plan: str = Field(default="trial", pattern=r"^(trial|pro|max)$")
    role: str = Field(default="operator", pattern=r"^(viewer|auditor|operator|admin)$")


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: str = Field(..., max_length=2048)
    origin: str = Field(..., max_length=128)
    action: str = Field(..., max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")
    client_ip_claim: str | None = Field(default=None, max_length=64)


class AgentTrifectaAuditRequest(BaseModel):
    payload: str = Field(..., max_length=10_000)
    origin: str = Field(..., max_length=128)
    action: str = Field(
        ...,
        max_length=128,
        pattern=r"^[A-Za-z0-9_\-:.]+$",
    )
    input_trust: Literal["trusted", "untrusted", "mixed"]
    can_read_private_data: bool = False
    can_access_secrets: bool = False
    can_send_external_data: bool = False
    can_write_files: bool = False
    can_modify_config: bool = False
    can_execute_shell: bool = False
    tool_name: str | None = Field(default=None, max_length=128)
    tool_args: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", strict=True)


class AgentTrifectaMetadata(BaseModel):
    threat_level: ThreatLevel
    request_id: str
    client_id: str


# The HTTP audit endpoint can emit verdicts beyond the trifecta algorithm's
# own three — the route runs the rate limiter, sandbox, and exception handler
# in front of the trifecta, each of which short-circuits with its own
# response code. Keep the trifecta Literal tight; widen here at the API
# boundary.
ApiDecision = Decision | Literal["ERROR", "RATE_LIMITED", "SANDBOX_BLOCKED"]


class AgentTrifectaAuditResponse(BaseModel):
    decision: ApiDecision
    metadata: AgentTrifectaMetadata
    reasons: list[str]
    summary: str
    receipt: dict[str, Any] | None = None


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: str = Field(..., max_length=2048)
    origin: str = Field(..., max_length=128)
    action: str = Field(..., max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")


class VerifyReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt: dict[str, Any]
