import pytest

from multi_agent_platform.agents.fake_provider import FakeLlmProvider
from multi_agent_platform.agents.llm_executor import LlmTurnExecutor
from multi_agent_platform.contracts.runs import (
    RunStateSnapshot,
    RunStatus,
    TaskRecord,
    WorkflowType,
)
from multi_agent_platform.contracts.turn_execution import (
    AgentExecutionProfile,
    ExecutionBackend,
    LlmTurnRequest,
    LlmTurnResponse,
)


class FlakyProvider:
    provider_name = "fake"

    def __init__(self, failure_count: int) -> None:
        self._failure_count = failure_count
        self._delegate = FakeLlmProvider()

    def generate_turn(self, request: LlmTurnRequest) -> LlmTurnResponse:
        if self._failure_count > 0:
            self._failure_count -= 1
            raise RuntimeError("temporary provider failure")
        return self._delegate.generate_turn(request)


class AlwaysFailProvider:
    provider_name = "fake"

    def generate_turn(self, request: LlmTurnRequest) -> LlmTurnResponse:
        raise RuntimeError("provider unavailable")


def build_run_state() -> RunStateSnapshot:
    return RunStateSnapshot(
        run_id="run_1",
        workflow_type=WorkflowType.TECHNICAL_PLAN,
        status=RunStatus.EXECUTING,
        user_goal="Create a technical delivery plan",
    )


def build_task() -> TaskRecord:
    return TaskRecord(
        task_id="task_1",
        title="Break work into phases",
        description="Create the task breakdown",
        assigned_agent="planner",
        acceptance_criteria=["Phases are clear"],
    )


def build_profile(
    *,
    agent_name: str = "planner",
    backend: ExecutionBackend = ExecutionBackend.LLM,
    provider_name: str = "fake",
    max_retries: int = 0,
) -> AgentExecutionProfile:
    if backend is ExecutionBackend.LLM:
        return AgentExecutionProfile(
            agent_name=agent_name,
            backend=backend,
            llm_provider_name=provider_name,
            model_name="fake-model",
            max_retries=max_retries,
        )
    return AgentExecutionProfile(
        agent_name=agent_name,
        backend=backend,
    )


def test_llm_turn_executor_returns_turn_execution_result() -> None:
    executor = LlmTurnExecutor(
        providers={"fake": FakeLlmProvider()},
        available_tool_names=["goal_analyzer"],
    )

    result = executor.execute_turn(
        build_run_state(),
        build_task(),
        build_profile(),
    )

    assert result.planned_tool_calls[0].tool_name == "goal_analyzer"
    assert "Planner reviewed the task scope" in result.summary


def test_llm_turn_executor_returns_structured_response() -> None:
    executor = LlmTurnExecutor(
        providers={"fake": FakeLlmProvider()},
        available_tool_names=["goal_analyzer"],
    )

    response = executor.execute_structured_turn(
        build_run_state(),
        build_task(),
        build_profile(),
    )

    assert response.provider_name == "fake"
    assert response.output.planned_tool_calls[0].tool_name == "goal_analyzer"


def test_llm_turn_executor_retries_before_success() -> None:
    executor = LlmTurnExecutor(
        providers={"fake": FlakyProvider(failure_count=2)},
        available_tool_names=["goal_analyzer"],
    )

    outcome = executor.execute_turn_outcome(
        build_run_state(),
        build_task(),
        build_profile(max_retries=2),
    )

    assert outcome.fallback_used is False
    assert outcome.attempt_count == 3
    assert outcome.llm_response is not None
    assert outcome.output.planned_tool_calls[0].tool_name == "goal_analyzer"


def test_llm_turn_executor_falls_back_after_retry_exhaustion() -> None:
    executor = LlmTurnExecutor(
        providers={"fake": AlwaysFailProvider()},
        available_tool_names=["goal_analyzer"],
    )

    outcome = executor.execute_turn_outcome(
        build_run_state(),
        build_task(),
        build_profile(max_retries=1),
    )

    assert outcome.fallback_used is True
    assert outcome.attempt_count == 2
    assert outcome.llm_response is None
    assert outcome.error_message == "provider unavailable"
    assert "Planner reviewed the task scope" in outcome.output.summary


def test_llm_turn_executor_rejects_unknown_provider() -> None:
    executor = LlmTurnExecutor(providers={})

    with pytest.raises(ValueError):
        executor.execute_turn(
            build_run_state(),
            build_task(),
            build_profile(),
        )


def test_llm_turn_executor_rejects_deterministic_profile() -> None:
    executor = LlmTurnExecutor(providers={"fake": FakeLlmProvider()})

    with pytest.raises(ValueError):
        executor.execute_turn(
            build_run_state(),
            build_task(),
            AgentExecutionProfile(agent_name="planner"),
        )


def test_llm_turn_executor_rejects_profile_for_different_agent() -> None:
    executor = LlmTurnExecutor(providers={"fake": FakeLlmProvider()})

    with pytest.raises(ValueError):
        executor.execute_turn(
            build_run_state(),
            build_task(),
            build_profile(agent_name="researcher"),
        )
