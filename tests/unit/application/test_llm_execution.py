from multi_agent_platform.agents.fake_provider import FakeLlmProvider
from multi_agent_platform.agents.llm_executor import LlmTurnExecutor
from multi_agent_platform.application.runs import RunService
from multi_agent_platform.contracts.llm_calls import LlmCallListQuery
from multi_agent_platform.contracts.runs import RunCreateRequest, WorkflowType
from multi_agent_platform.contracts.turn_execution import ExecutionBackend
from multi_agent_platform.storage.llm_call_repository import InMemoryLlmCallRepository
from multi_agent_platform.storage.run_approval_repository import (
    InMemoryRunApprovalRepository,
)
from multi_agent_platform.storage.run_event_repository import InMemoryRunEventRepository
from multi_agent_platform.storage.run_output_repository import InMemoryRunOutputRepository
from multi_agent_platform.storage.run_plan_repository import InMemoryRunPlanRepository
from multi_agent_platform.storage.run_repository import InMemoryRunRepository
from multi_agent_platform.storage.run_tool_call_repository import (
    InMemoryRunToolCallRepository,
)
from multi_agent_platform.storage.run_turn_repository import InMemoryRunTurnRepository
from multi_agent_platform.storage.run_verification_repository import (
    InMemoryRunVerificationRepository,
)
from multi_agent_platform.tools.registry import list_available_tool_names


def build_run_service() -> RunService:
    provider = FakeLlmProvider()
    return RunService(
        run_repository=InMemoryRunRepository(),
        run_event_repository=InMemoryRunEventRepository(),
        run_verification_repository=InMemoryRunVerificationRepository(),
        run_approval_repository=InMemoryRunApprovalRepository(),
        run_plan_repository=InMemoryRunPlanRepository(),
        run_turn_repository=InMemoryRunTurnRepository(),
        run_tool_call_repository=InMemoryRunToolCallRepository(),
        run_output_repository=InMemoryRunOutputRepository(),
        turn_executor=LlmTurnExecutor(
            providers={provider.provider_name: provider},
            available_tool_names=list_available_tool_names(),
        ),
        llm_call_repository=InMemoryLlmCallRepository(),
        execution_backend=ExecutionBackend.LLM,
        llm_provider_name="fake",
        llm_model_name="fake-model",
    )


def test_run_service_persists_llm_call_records() -> None:
    run_service = build_run_service()
    created_run = run_service.create_run(
        RunCreateRequest(
            user_goal="Create a technical delivery plan",
            workflow_type=WorkflowType.TECHNICAL_PLAN,
        )
    )
    run_id = created_run.item.run_id

    run_service.generate_plan(run_id)
    turn_response = run_service.advance_turn(run_id)
    llm_call_page = run_service.list_llm_calls(
        run_id,
        LlmCallListQuery(limit=10, offset=0),
    )

    assert llm_call_page.page.total_count == 1
    assert llm_call_page.items[0].provider_name == "fake"
    assert llm_call_page.items[0].model_name == "fake-model"
    assert llm_call_page.items[0].turn_id == turn_response.turn.turn_id
    assert llm_call_page.items[0].structured_output.summary == turn_response.turn.summary
