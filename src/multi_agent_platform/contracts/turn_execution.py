from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from multi_agent_platform.contracts.runs import TaskRecord
from multi_agent_platform.tools.registry import PlannedToolCall


class ExecutionBackend(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class AgentExecutionProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    backend: ExecutionBackend = ExecutionBackend.DETERMINISTIC
    llm_provider_name: str | None = None
    model_name: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    timeout_seconds: float | None = Field(default=None, gt=0.0)
    max_retries: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_backend_settings(self) -> "AgentExecutionProfile":
        if self.backend is ExecutionBackend.DETERMINISTIC:
            if any(
                value is not None
                for value in (
                    self.llm_provider_name,
                    self.model_name,
                    self.temperature,
                    self.max_output_tokens,
                    self.timeout_seconds,
                )
            ):
                raise ValueError("Deterministic backend does not accept LLM configuration")
            return self
        if self.llm_provider_name is None:
            raise ValueError("LLM backend requires llm_provider_name")
        return self


class StructuredTurnOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    planned_tool_calls: list[PlannedToolCall] = Field(default_factory=list)


class LlmUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_total_tokens(self) -> "LlmUsage":
        minimum_total = self.input_tokens + self.output_tokens
        if self.total_tokens < minimum_total:
            raise ValueError("total_tokens must be at least input_tokens + output_tokens")
        return self


class LlmTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    user_goal: str
    task: TaskRecord
    execution_profile: AgentExecutionProfile
    available_tool_names: list[str] = Field(default_factory=list)


class LlmTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name: str
    model_name: str
    output: StructuredTurnOutput
    usage: LlmUsage = Field(default_factory=LlmUsage)
    finish_reason: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    raw_response_text: str | None = None


class LlmExecutionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: StructuredTurnOutput
    llm_response: LlmTurnResponse | None = None
    error_message: str | None = None
    fallback_used: bool = False
    attempt_count: int = Field(default=1, ge=1)
