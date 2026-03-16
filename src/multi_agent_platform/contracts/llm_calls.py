from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from multi_agent_platform.contracts.common import generate_identifier, utc_now
from multi_agent_platform.contracts.run_queries import PageInfo
from multi_agent_platform.contracts.turn_execution import LlmUsage, StructuredTurnOutput


class LlmCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_call_id: str = Field(default_factory=lambda: generate_identifier("llm_call"))
    run_id: str
    turn_id: str
    task_id: str
    agent_name: str
    provider_name: str
    model_name: str
    structured_output: StructuredTurnOutput
    usage: LlmUsage = Field(default_factory=LlmUsage)
    available_tool_names: list[str] = Field(default_factory=list)
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    finish_reason: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    error_message: str | None = None
    raw_response_text: str | None = None
    attempt_count: int = Field(default=1, ge=1)
    fallback_used: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class LlmCallListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class LlmCallPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LlmCallRecord]
    page: PageInfo
