import os
from collections.abc import Mapping

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi import status as http_status

from multi_agent_platform.agents.fake_provider import FakeLlmProvider
from multi_agent_platform.agents.openai_provider import OpenAiCompatibleProvider
from multi_agent_platform.agents.providers import LlmProvider
from multi_agent_platform.agents.runtime import build_planned_tool_call, build_turn_summary
from multi_agent_platform.contracts.turn_execution import (
    LlmExecutionOutcome,
    LlmTurnRequest,
    StructuredTurnOutput,
)


def create_app() -> FastAPI:
    application = FastAPI(title="Agent Runway Agent Worker", version="0.1.0")
    executor = AgentWorkerExecutor()

    @application.get("/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/internal/agent/turn", response_model=LlmExecutionOutcome)
    def execute_agent_turn(
        request: LlmTurnRequest,
        _: None = Depends(require_worker_token),
    ) -> LlmExecutionOutcome:
        return executor.execute_turn(request)

    return application


def require_worker_token(authorization: str | None = Header(default=None)) -> None:
    expected_token = os.getenv("AGENT_WORKER_TOKEN")
    if expected_token is None or expected_token.strip() == "":
        return

    expected_header = f"Bearer {expected_token.strip()}"
    if authorization != expected_header:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker token",
        )


class AgentWorkerExecutor:
    def execute_turn(self, request: LlmTurnRequest) -> LlmExecutionOutcome:
        profile = request.execution_profile
        providers = self._build_providers()
        provider_name = profile.llm_provider_name
        provider = providers.get(provider_name or "")
        if provider is None:
            return self._fallback(request, f"No LLM provider registered for {provider_name}")

        attempt_total = profile.max_retries + 1
        last_error_message: str | None = None

        for attempt_index in range(attempt_total):
            try:
                response = provider.generate_turn(request)
            except Exception as error:
                last_error_message = str(error)
                if attempt_index == attempt_total - 1:
                    break
                continue
            return LlmExecutionOutcome(
                output=response.output,
                llm_response=response,
                attempt_count=attempt_index + 1,
            )

        return self._fallback(
            request,
            last_error_message or "LLM execution failed",
            attempt_count=attempt_total,
        )

    def _build_providers(self) -> Mapping[str, LlmProvider]:
        providers: dict[str, LlmProvider] = {"fake": FakeLlmProvider()}
        openai_api_key = os.getenv("LLM_API_KEY")
        if openai_api_key is not None and openai_api_key.strip():
            providers["openai"] = OpenAiCompatibleProvider(
                api_key=openai_api_key,
                base_url=os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1"),
                default_model_name=os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini"),
            )
        return providers

    def _fallback(
        self,
        request: LlmTurnRequest,
        error_message: str,
        *,
        attempt_count: int = 1,
    ) -> LlmExecutionOutcome:
        task = request.task
        output = StructuredTurnOutput(
            summary=build_turn_summary(task.assigned_agent, task.title),
            planned_tool_calls=[
                build_planned_tool_call(
                    agent_name=task.assigned_agent,
                    user_goal=request.user_goal,
                    task_title=task.title,
                )
            ],
        )
        return LlmExecutionOutcome(
            output=output,
            llm_response=None,
            error_message=error_message,
            fallback_used=True,
            attempt_count=attempt_count,
        )


app = create_app()
