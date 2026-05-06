from pathlib import Path

from multi_agent_platform.contracts.llm_calls import LlmCallListQuery, LlmCallRecord
from multi_agent_platform.contracts.turn_execution import LlmUsage, StructuredTurnOutput
from multi_agent_platform.storage.db.migrations import migrate_database_schema
from multi_agent_platform.storage.db.session import get_session_factory
from multi_agent_platform.storage.sql_repository import SqlAlchemyRunLlmCallRepository
from multi_agent_platform.tools.registry import PlannedToolCall


def build_record(
    *,
    run_id: str = "run_1",
    turn_id: str = "turn_1",
    task_id: str = "task_1",
) -> LlmCallRecord:
    return LlmCallRecord(
        run_id=run_id,
        turn_id=turn_id,
        task_id=task_id,
        agent_name="planner",
        provider_name="fake",
        model_name="fake-model",
        structured_output=StructuredTurnOutput(
            summary="Planner prepared the structured next step.",
            planned_tool_calls=[
                PlannedToolCall(
                    tool_name="goal_analyzer",
                    tool_input={"task_title": "Break work into phases"},
                )
            ],
        ),
        usage=LlmUsage(
            input_tokens=12,
            output_tokens=8,
            total_tokens=20,
            estimated_cost_usd=0.0,
        ),
        available_tool_names=["goal_analyzer"],
        request_payload={"user_goal": "Create a technical delivery plan"},
        response_payload={"provider": "fake"},
        finish_reason="stop",
        latency_ms=1,
        raw_response_text="structured output",
    )


def test_sql_llm_call_repository_saves_gets_and_lists_records(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'llm_calls.db'}"
    migrate_database_schema(database_url)
    repository = SqlAlchemyRunLlmCallRepository(get_session_factory(database_url))

    first_record = repository.save(build_record(turn_id="turn_1", task_id="task_1"))
    second_record = repository.save(build_record(turn_id="turn_2", task_id="task_2"))

    fetched_record = repository.get(first_record.run_id, first_record.llm_call_id)
    page = repository.list(first_record.run_id, LlmCallListQuery(limit=10, offset=0))

    assert fetched_record.llm_call_id == first_record.llm_call_id
    assert page.page.total_count == 2
    assert page.items[0].llm_call_id == second_record.llm_call_id
