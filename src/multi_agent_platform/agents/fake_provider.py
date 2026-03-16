from multi_agent_platform.agents.runtime import (
    build_planned_tool_call,
    build_turn_summary,
)
from multi_agent_platform.contracts.turn_execution import (
    LlmTurnRequest,
    LlmTurnResponse,
    LlmUsage,
    StructuredTurnOutput,
)


class FakeLlmProvider:
    provider_name = "fake"

    def generate_turn(self, request: LlmTurnRequest) -> LlmTurnResponse:
        execution_profile = request.execution_profile
        requested_provider_name = execution_profile.llm_provider_name
        if requested_provider_name != self.provider_name:
            raise ValueError(f"FakeLlmProvider cannot satisfy provider {requested_provider_name}")

        structured_output = StructuredTurnOutput(
            summary=build_turn_summary(
                request.task.assigned_agent,
                request.task.title,
            ),
            planned_tool_calls=[
                build_planned_tool_call(
                    agent_name=request.task.assigned_agent,
                    user_goal=request.user_goal,
                    task_title=request.task.title,
                )
            ],
        )

        input_tokens = max(
            1,
            len(request.user_goal.split()) + len(request.task.title.split()),
        )
        output_tokens = max(1, len(structured_output.summary.split()))

        return LlmTurnResponse(
            provider_name=self.provider_name,
            model_name=execution_profile.model_name or "fake-model",
            output=structured_output,
            usage=LlmUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                estimated_cost_usd=0.0,
            ),
            finish_reason="stop",
            latency_ms=1,
            raw_response_text=structured_output.model_dump_json(),
        )
