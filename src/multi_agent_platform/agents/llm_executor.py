from collections.abc import Mapping, Sequence

from multi_agent_platform.agents.executors import DeterministicTurnExecutor
from multi_agent_platform.agents.providers import LlmProvider
from multi_agent_platform.agents.runtime import TurnExecutionResult
from multi_agent_platform.contracts.runs import RunStateSnapshot, TaskRecord
from multi_agent_platform.contracts.turn_execution import (
    AgentExecutionProfile,
    ExecutionBackend,
    LlmExecutionOutcome,
    LlmTurnRequest,
    LlmTurnResponse,
    StructuredTurnOutput,
)


class LlmTurnExecutor:
    def __init__(
        self,
        providers: Mapping[str, LlmProvider],
        available_tool_names: Sequence[str] | None = None,
        fallback_executor: DeterministicTurnExecutor | None = None,
    ) -> None:
        self._providers = dict(providers)
        self._available_tool_names = list(available_tool_names or [])
        self._fallback_executor = fallback_executor or DeterministicTurnExecutor()

    def execute_turn(
        self,
        run_state: RunStateSnapshot,
        task: TaskRecord,
        execution_profile: AgentExecutionProfile | None = None,
    ) -> TurnExecutionResult:
        outcome = self.execute_turn_outcome(
            run_state,
            task,
            execution_profile,
        )
        return TurnExecutionResult(
            summary=outcome.output.summary,
            planned_tool_calls=outcome.output.planned_tool_calls,
        )

    def execute_structured_turn(
        self,
        run_state: RunStateSnapshot,
        task: TaskRecord,
        execution_profile: AgentExecutionProfile | None = None,
    ) -> LlmTurnResponse:
        outcome = self.execute_turn_outcome(
            run_state,
            task,
            execution_profile,
        )
        if outcome.llm_response is None:
            raise ValueError("LLM turn execution fell back to deterministic execution")
        return outcome.llm_response

    def execute_turn_outcome(
        self,
        run_state: RunStateSnapshot,
        task: TaskRecord,
        execution_profile: AgentExecutionProfile | None = None,
    ) -> LlmExecutionOutcome:
        profile = self._validate_execution_profile(task, execution_profile)
        provider = self._resolve_provider(profile)
        attempt_total = profile.max_retries + 1
        last_error_message: str | None = None

        for attempt_index in range(attempt_total):
            try:
                response = provider.generate_turn(self._build_request(run_state, task, profile))
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

        fallback_result = self._fallback_executor.execute_turn(
            run_state,
            task,
            AgentExecutionProfile(
                agent_name=task.assigned_agent,
                backend=ExecutionBackend.DETERMINISTIC,
            ),
        )
        return LlmExecutionOutcome(
            output=StructuredTurnOutput(
                summary=fallback_result.summary,
                planned_tool_calls=fallback_result.planned_tool_calls,
            ),
            error_message=last_error_message or "LLM execution failed",
            fallback_used=True,
            attempt_count=attempt_total,
        )

    def _build_request(
        self,
        run_state: RunStateSnapshot,
        task: TaskRecord,
        execution_profile: AgentExecutionProfile,
    ) -> LlmTurnRequest:
        return LlmTurnRequest(
            run_id=run_state.run_id,
            user_goal=run_state.user_goal,
            task=task,
            execution_profile=execution_profile,
            available_tool_names=self._available_tool_names,
        )

    def _resolve_provider(
        self,
        execution_profile: AgentExecutionProfile,
    ) -> LlmProvider:
        provider_name = execution_profile.llm_provider_name
        if provider_name is None:
            raise ValueError("LlmTurnExecutor requires llm_provider_name")

        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(f"No LLM provider registered for {provider_name}")
        return provider

    def _validate_execution_profile(
        self,
        task: TaskRecord,
        execution_profile: AgentExecutionProfile | None,
    ) -> AgentExecutionProfile:
        if execution_profile is None:
            raise ValueError("LlmTurnExecutor requires an execution profile")
        if execution_profile.agent_name != task.assigned_agent:
            raise ValueError(
                "Execution profile agent "
                f"{execution_profile.agent_name} does not match "
                f"task agent {task.assigned_agent}"
            )
        if execution_profile.backend is not ExecutionBackend.LLM:
            raise ValueError("LlmTurnExecutor requires llm backend")
        return execution_profile
