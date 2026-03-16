from multi_agent_platform.agents.executors import (
    DeterministicTurnExecutor,
    TurnExecutor,
)
from multi_agent_platform.agents.fake_provider import FakeLlmProvider
from multi_agent_platform.agents.llm_executor import LlmTurnExecutor
from multi_agent_platform.application.runs import RunService
from multi_agent_platform.config.settings import (
    Settings,
    get_settings,
    reset_settings_cache,
)
from multi_agent_platform.contracts.turn_execution import ExecutionBackend
from multi_agent_platform.storage.db.session import (
    ensure_database_schema,
    get_session_factory,
)
from multi_agent_platform.storage.llm_call_repository import (
    InMemoryLlmCallRepository,
)
from multi_agent_platform.storage.run_approval_repository import InMemoryRunApprovalRepository
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
from multi_agent_platform.storage.sql_repository import (
    SqlAlchemyRunApprovalRepository,
    SqlAlchemyRunEventRepository,
    SqlAlchemyRunLlmCallRepository,
    SqlAlchemyRunOutputRepository,
    SqlAlchemyRunPlanRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyRunToolCallRepository,
    SqlAlchemyRunTurnRepository,
    SqlAlchemyRunVerificationRepository,
)
from multi_agent_platform.tools.registry import list_available_tool_names

_run_service: RunService | None = None


def build_turn_executor(settings: Settings) -> TurnExecutor:
    if settings.execution_backend == "llm":
        if settings.llm_provider_name != "fake":
            raise ValueError(f"Unsupported LLM provider {settings.llm_provider_name}")
        provider = FakeLlmProvider()
        return LlmTurnExecutor(
            providers={provider.provider_name: provider},
            available_tool_names=list_available_tool_names(),
        )
    return DeterministicTurnExecutor()


def build_memory_run_service(settings: Settings) -> RunService:
    return RunService(
        run_repository=InMemoryRunRepository(),
        run_event_repository=InMemoryRunEventRepository(),
        run_verification_repository=InMemoryRunVerificationRepository(),
        run_approval_repository=InMemoryRunApprovalRepository(),
        run_plan_repository=InMemoryRunPlanRepository(),
        run_turn_repository=InMemoryRunTurnRepository(),
        run_tool_call_repository=InMemoryRunToolCallRepository(),
        run_output_repository=InMemoryRunOutputRepository(),
        turn_executor=build_turn_executor(settings),
        llm_call_repository=InMemoryLlmCallRepository(),
        execution_backend=ExecutionBackend(settings.execution_backend),
        llm_provider_name=settings.llm_provider_name,
        llm_model_name=settings.llm_model_name,
    )


def build_sql_run_service(settings: Settings) -> RunService:
    ensure_database_schema(settings.database_url)
    session_factory = get_session_factory(settings.database_url)
    return RunService(
        run_repository=SqlAlchemyRunRepository(session_factory),
        run_event_repository=SqlAlchemyRunEventRepository(session_factory),
        run_verification_repository=SqlAlchemyRunVerificationRepository(session_factory),
        run_approval_repository=SqlAlchemyRunApprovalRepository(session_factory),
        run_plan_repository=SqlAlchemyRunPlanRepository(session_factory),
        run_turn_repository=SqlAlchemyRunTurnRepository(session_factory),
        run_tool_call_repository=SqlAlchemyRunToolCallRepository(session_factory),
        run_output_repository=SqlAlchemyRunOutputRepository(session_factory),
        turn_executor=build_turn_executor(settings),
        llm_call_repository=SqlAlchemyRunLlmCallRepository(session_factory),
        execution_backend=ExecutionBackend(settings.execution_backend),
        llm_provider_name=settings.llm_provider_name,
        llm_model_name=settings.llm_model_name,
    )


def get_run_service() -> RunService:
    global _run_service
    if _run_service is None:
        settings = get_settings()
        if settings.storage_backend == "sql":
            _run_service = build_sql_run_service(settings)
        else:
            _run_service = build_memory_run_service(settings)
    return _run_service


def reset_api_state() -> None:
    global _run_service
    _run_service = None
    reset_settings_cache()
