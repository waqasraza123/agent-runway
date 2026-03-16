from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from multi_agent_platform.api.dependencies import get_run_service
from multi_agent_platform.application.runs import (
    ApprovalTransitionError,
    FinalizationError,
    PlanningTransitionError,
    RunService,
    StateTransitionError,
    TurnAdvanceError,
)
from multi_agent_platform.contracts.llm_call_views import LlmCallListResponse
from multi_agent_platform.contracts.llm_calls import LlmCallListQuery
from multi_agent_platform.contracts.run_approval_views import (
    RunApprovalListResponse,
    RunApprovalResponse,
)
from multi_agent_platform.contracts.run_approvals import (
    ApprovalDecisionRequest,
    ApprovalListQuery,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from multi_agent_platform.contracts.run_commands import (
    EvidenceCreateRequest,
    TaskCompleteRequest,
    TaskRegistrationRequest,
    TaskStartRequest,
)
from multi_agent_platform.contracts.run_event_views import RunEventListResponse
from multi_agent_platform.contracts.run_events import RunEventListQuery
from multi_agent_platform.contracts.run_output_views import RunOutputResponse
from multi_agent_platform.contracts.run_plan_views import RunPlanResponse
from multi_agent_platform.contracts.run_queries import RunListQuery
from multi_agent_platform.contracts.run_tool_call_views import (
    RunToolCallListResponse,
)
from multi_agent_platform.contracts.run_tool_calls import (
    RunToolCallListQuery,
)
from multi_agent_platform.contracts.run_turn_views import (
    RunTurnAdvanceResponse,
    RunTurnListResponse,
)
from multi_agent_platform.contracts.run_turns import RunTurnListQuery
from multi_agent_platform.contracts.run_verification_views import (
    RunVerificationResponse,
)
from multi_agent_platform.contracts.run_views import (
    RunListResponse,
    RunResponse,
    RunStateResponse,
)
from multi_agent_platform.contracts.runs import (
    RunCreateRequest,
    RunStatus,
    WorkflowType,
)
from multi_agent_platform.storage.run_approval_repository import (
    RunApprovalNotFoundError,
)
from multi_agent_platform.storage.run_output_repository import RunOutputNotFoundError
from multi_agent_platform.storage.run_plan_repository import RunPlanNotFoundError
from multi_agent_platform.storage.run_repository import RunNotFoundError
from multi_agent_platform.storage.run_verification_repository import (
    RunVerificationNotFoundError,
)

router = APIRouter(prefix="/runs", tags=["runs"])
RunServiceDependency = Annotated[RunService, Depends(get_run_service)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]
StatusQuery = Annotated[RunStatus | None, Query()]
WorkflowTypeQuery = Annotated[WorkflowType | None, Query()]
ApprovalStatusQuery = Annotated[ApprovalStatus | None, Query()]


def build_run_list_query(
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
    status: StatusQuery = None,
    workflow_type: WorkflowTypeQuery = None,
) -> RunListQuery:
    return RunListQuery(
        limit=limit,
        offset=offset,
        status=status,
        workflow_type=workflow_type,
    )


def build_run_event_list_query(
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> RunEventListQuery:
    return RunEventListQuery(limit=limit, offset=offset)


def build_run_turn_list_query(
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> RunTurnListQuery:
    return RunTurnListQuery(limit=limit, offset=offset)


def build_run_tool_call_list_query(
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> RunToolCallListQuery:
    return RunToolCallListQuery(limit=limit, offset=offset)


def build_llm_call_list_query(
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> LlmCallListQuery:
    return LlmCallListQuery(limit=limit, offset=offset)


def build_approval_list_query(
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
    status: ApprovalStatusQuery = None,
) -> ApprovalListQuery:
    return ApprovalListQuery(limit=limit, offset=offset, status=status)


RunListQueryDependency = Annotated[RunListQuery, Depends(build_run_list_query)]
RunEventListQueryDependency = Annotated[
    RunEventListQuery,
    Depends(build_run_event_list_query),
]
RunTurnListQueryDependency = Annotated[
    RunTurnListQuery,
    Depends(build_run_turn_list_query),
]
RunToolCallListQueryDependency = Annotated[
    RunToolCallListQuery,
    Depends(build_run_tool_call_list_query),
]
LlmCallListQueryDependency = Annotated[
    LlmCallListQuery,
    Depends(build_llm_call_list_query),
]
ApprovalListQueryDependency = Annotated[
    ApprovalListQuery,
    Depends(build_approval_list_query),
]


def map_run_error(error: Exception) -> HTTPException:
    if isinstance(error, RunNotFoundError):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, RunApprovalNotFoundError):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, RunOutputNotFoundError):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, RunPlanNotFoundError):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, RunVerificationNotFoundError):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ApprovalTransitionError):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, FinalizationError):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, PlanningTransitionError):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, StateTransitionError):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, TurnAdvanceError):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(error))
    raise HTTPException(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected run error",
    )


@router.post("", response_model=RunResponse, status_code=http_status.HTTP_201_CREATED)
def create_run(
    request: RunCreateRequest,
    run_service: RunServiceDependency,
) -> RunResponse:
    return run_service.create_run(request)


@router.get("", response_model=RunListResponse)
def list_runs(
    query: RunListQueryDependency,
    run_service: RunServiceDependency,
) -> RunListResponse:
    return run_service.list_runs(query)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunResponse:
    try:
        return run_service.get_run(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/state", response_model=RunStateResponse)
def get_run_state(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunStateResponse:
    try:
        return run_service.get_run_state(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/events", response_model=RunEventListResponse)
def list_run_events(
    run_id: str,
    query: RunEventListQueryDependency,
    run_service: RunServiceDependency,
) -> RunEventListResponse:
    try:
        return run_service.list_run_events(run_id, query)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/turns", response_model=RunTurnListResponse)
def list_run_turns(
    run_id: str,
    query: RunTurnListQueryDependency,
    run_service: RunServiceDependency,
) -> RunTurnListResponse:
    try:
        return run_service.list_turns(run_id, query)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/tool-calls", response_model=RunToolCallListResponse)
def list_run_tool_calls(
    run_id: str,
    query: RunToolCallListQueryDependency,
    run_service: RunServiceDependency,
) -> RunToolCallListResponse:
    try:
        return run_service.list_tool_calls(run_id, query)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/llm-calls", response_model=LlmCallListResponse)
def list_run_llm_calls(
    run_id: str,
    query: LlmCallListQueryDependency,
    run_service: RunServiceDependency,
) -> LlmCallListResponse:
    try:
        return run_service.list_llm_calls(run_id, query)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/turns/advance", response_model=RunTurnAdvanceResponse)
def advance_run_turn(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunTurnAdvanceResponse:
    try:
        return run_service.advance_turn(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/outputs/latest", response_model=RunOutputResponse)
def get_latest_run_output(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunOutputResponse:
    try:
        return run_service.get_latest_output(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/finalize", response_model=RunOutputResponse)
def finalize_run(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunOutputResponse:
    try:
        return run_service.finalize_run(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/approvals", response_model=RunApprovalListResponse)
def list_run_approvals(
    run_id: str,
    query: ApprovalListQueryDependency,
    run_service: RunServiceDependency,
) -> RunApprovalListResponse:
    try:
        return run_service.list_approvals(run_id, query)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/approvals", response_model=RunApprovalResponse)
def create_run_approval(
    run_id: str,
    request: ApprovalRequestCreate,
    run_service: RunServiceDependency,
) -> RunApprovalResponse:
    try:
        return run_service.request_approval(run_id, request)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/approvals/{approval_id}/decide", response_model=RunApprovalResponse)
def decide_run_approval(
    run_id: str,
    approval_id: str,
    request: ApprovalDecisionRequest,
    run_service: RunServiceDependency,
) -> RunApprovalResponse:
    try:
        return run_service.decide_approval(run_id, approval_id, request)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/plan", response_model=RunPlanResponse)
def generate_run_plan(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunPlanResponse:
    try:
        return run_service.generate_plan(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/plans/latest", response_model=RunPlanResponse)
def get_latest_run_plan(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunPlanResponse:
    try:
        return run_service.get_latest_plan(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/verify", response_model=RunVerificationResponse)
def verify_run(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunVerificationResponse:
    try:
        return run_service.verify_run(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.get("/{run_id}/verifications/latest", response_model=RunVerificationResponse)
def get_latest_verification(
    run_id: str,
    run_service: RunServiceDependency,
) -> RunVerificationResponse:
    try:
        return run_service.get_latest_verification(run_id)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/tasks", response_model=RunStateResponse)
def register_run_tasks(
    run_id: str,
    request: TaskRegistrationRequest,
    run_service: RunServiceDependency,
) -> RunStateResponse:
    try:
        return run_service.register_tasks(run_id, request)
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/tasks/{task_id}/start", response_model=RunStateResponse)
def start_run_task(
    run_id: str,
    task_id: str,
    run_service: RunServiceDependency,
) -> RunStateResponse:
    try:
        return run_service.start_task(run_id, TaskStartRequest(task_id=task_id))
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/tasks/{task_id}/complete", response_model=RunStateResponse)
def complete_run_task(
    run_id: str,
    task_id: str,
    run_service: RunServiceDependency,
) -> RunStateResponse:
    try:
        return run_service.complete_task(run_id, TaskCompleteRequest(task_id=task_id))
    except Exception as error:
        raise map_run_error(error) from error


@router.post("/{run_id}/evidence", response_model=RunStateResponse)
def create_run_evidence(
    run_id: str,
    request: EvidenceCreateRequest,
    run_service: RunServiceDependency,
) -> RunStateResponse:
    try:
        return run_service.record_evidence(run_id, request)
    except Exception as error:
        raise map_run_error(error) from error
