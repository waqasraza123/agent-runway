from multi_agent_platform.agents.executors import (
    DeterministicTurnExecutor,
    TurnExecutor,
)
from multi_agent_platform.agents.llm_executor import LlmTurnExecutor
from multi_agent_platform.agents.runtime import TurnExecutionResult
from multi_agent_platform.application.run_approvals import (
    build_run_approval_list_response,
    build_run_approval_response,
)
from multi_agent_platform.application.run_events import build_run_event_list_response
from multi_agent_platform.application.run_llm_calls import build_llm_call_list_response
from multi_agent_platform.application.run_outputs import build_run_output_response
from multi_agent_platform.application.run_plans import build_run_plan_response
from multi_agent_platform.application.run_tool_calls import (
    build_run_tool_call_list_response,
)
from multi_agent_platform.application.run_turns import (
    build_run_turn_advance_response,
    build_run_turn_list_response,
)
from multi_agent_platform.application.run_verifications import (
    build_run_verification_report,
)
from multi_agent_platform.application.run_views import (
    build_run_list_response,
    build_run_response,
    build_run_state_response,
)
from multi_agent_platform.contracts.common import generate_identifier
from multi_agent_platform.contracts.llm_call_views import LlmCallListResponse
from multi_agent_platform.contracts.llm_calls import LlmCallListQuery, LlmCallRecord
from multi_agent_platform.contracts.run_approval_views import (
    RunApprovalListResponse,
    RunApprovalResponse,
)
from multi_agent_platform.contracts.run_approvals import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalListQuery,
    ApprovalRecord,
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
from multi_agent_platform.contracts.run_events import (
    RunEventListQuery,
    RunEventRecord,
    RunEventType,
)
from multi_agent_platform.contracts.run_output_views import RunOutputResponse
from multi_agent_platform.contracts.run_outputs import RunOutputRecord
from multi_agent_platform.contracts.run_plan_views import RunPlanResponse
from multi_agent_platform.contracts.run_queries import RunListQuery
from multi_agent_platform.contracts.run_tool_call_views import (
    RunToolCallListResponse,
)
from multi_agent_platform.contracts.run_tool_calls import (
    RunToolCallListQuery,
    RunToolCallRecord,
)
from multi_agent_platform.contracts.run_turn_views import (
    RunTurnAdvanceResponse,
    RunTurnListResponse,
)
from multi_agent_platform.contracts.run_turns import (
    RunTurnListQuery,
    RunTurnRecord,
)
from multi_agent_platform.contracts.run_verification_views import (
    RunVerificationResponse,
)
from multi_agent_platform.contracts.run_verifications import VerificationVerdict
from multi_agent_platform.contracts.run_views import (
    RunListResponse,
    RunResponse,
    RunStateResponse,
)
from multi_agent_platform.contracts.runs import (
    EvidenceRecord,
    RunCreateRequest,
    RunStateSnapshot,
    RunStatus,
    TaskRecord,
    TaskStatus,
)
from multi_agent_platform.contracts.turn_execution import (
    AgentExecutionProfile,
    ExecutionBackend,
    LlmTurnResponse,
)
from multi_agent_platform.orchestration.state import (
    StateTransitionError,
    complete_task,
    create_run_state,
    record_evidence,
    register_tasks,
    start_task,
)
from multi_agent_platform.planning.templates import build_run_plan
from multi_agent_platform.storage.llm_call_repository import (
    InMemoryLlmCallRepository,
    LlmCallRepository,
)
from multi_agent_platform.storage.run_approval_repository import (
    RunApprovalRepository,
)
from multi_agent_platform.storage.run_event_repository import RunEventRepository
from multi_agent_platform.storage.run_output_repository import RunOutputRepository
from multi_agent_platform.storage.run_plan_repository import RunPlanRepository
from multi_agent_platform.storage.run_repository import RunRepository
from multi_agent_platform.storage.run_tool_call_repository import (
    RunToolCallRepository,
)
from multi_agent_platform.storage.run_turn_repository import RunTurnRepository
from multi_agent_platform.storage.run_verification_repository import (
    RunVerificationRepository,
)
from multi_agent_platform.tools.registry import (
    execute_planned_tool_call,
    list_available_tool_names,
)


class ApprovalTransitionError(ValueError):
    pass


class PlanningTransitionError(ValueError):
    pass


class TurnAdvanceError(ValueError):
    pass


class FinalizationError(ValueError):
    pass


class RunService:
    def __init__(
        self,
        run_repository: RunRepository,
        run_event_repository: RunEventRepository,
        run_verification_repository: RunVerificationRepository,
        run_approval_repository: RunApprovalRepository,
        run_plan_repository: RunPlanRepository,
        run_turn_repository: RunTurnRepository,
        run_tool_call_repository: RunToolCallRepository,
        run_output_repository: RunOutputRepository,
        turn_executor: TurnExecutor | None = None,
        llm_call_repository: LlmCallRepository | None = None,
        execution_backend: ExecutionBackend = ExecutionBackend.DETERMINISTIC,
        llm_provider_name: str = "fake",
        llm_model_name: str = "fake-model",
    ) -> None:
        self._run_repository = run_repository
        self._run_event_repository = run_event_repository
        self._run_verification_repository = run_verification_repository
        self._run_approval_repository = run_approval_repository
        self._run_plan_repository = run_plan_repository
        self._run_turn_repository = run_turn_repository
        self._run_tool_call_repository = run_tool_call_repository
        self._run_output_repository = run_output_repository
        self._turn_executor = turn_executor or DeterministicTurnExecutor()
        self._llm_call_repository = llm_call_repository or InMemoryLlmCallRepository()
        self._execution_backend = execution_backend
        self._llm_provider_name = llm_provider_name
        self._llm_model_name = llm_model_name

    def create_run(self, request: RunCreateRequest) -> RunResponse:
        run_state = create_run_state(request)
        created_run_state = self._run_repository.create(run_state)
        self._record_event(
            run_id=created_run_state.run_id,
            event_type=RunEventType.RUN_CREATED,
            payload={
                "workflow_type": created_run_state.workflow_type.value,
                "status": created_run_state.status.value,
            },
        )
        return build_run_response(created_run_state)

    def get_run(self, run_id: str) -> RunResponse:
        run_state = self._run_repository.get(run_id)
        return build_run_response(run_state)

    def get_run_state(self, run_id: str) -> RunStateResponse:
        run_state = self._run_repository.get(run_id)
        return build_run_state_response(run_state)

    def list_runs(self, query: RunListQuery) -> RunListResponse:
        run_state_page = self._run_repository.list(query)
        return build_run_list_response(run_state_page)

    def generate_plan(self, run_id: str) -> RunPlanResponse:
        run_state = self._run_repository.get(run_id)
        if run_state.tasks:
            raise PlanningTransitionError(
                f"Run {run_id} already has registered tasks and cannot be planned again"
            )
        run_plan = build_run_plan(run_state)
        stored_plan = self._run_plan_repository.save(run_plan)
        updated_run_state = register_tasks(
            run_state,
            [planned_task.to_task_record() for planned_task in stored_plan.tasks],
        )
        self._run_repository.update(updated_run_state)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.PLAN_GENERATED,
            payload={
                "plan_id": stored_plan.plan_id,
                "template_name": stored_plan.template_name,
            },
        )
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.TASKS_REGISTERED,
            payload={"task_ids": [task.task_id for task in stored_plan.tasks]},
        )
        return build_run_plan_response(stored_plan)

    def get_latest_plan(self, run_id: str) -> RunPlanResponse:
        self._run_repository.get(run_id)
        report = self._run_plan_repository.get_latest(run_id)
        return build_run_plan_response(report)

    def advance_turn(self, run_id: str) -> RunTurnAdvanceResponse:
        run_state = self._run_repository.get(run_id)
        if run_state.current_task_id is None:
            next_task = self._find_next_ready_task(run_state)
            if next_task is None:
                raise TurnAdvanceError(f"Run {run_id} has no ready task to advance")
            run_state = start_task(run_state, next_task.task_id)
            self._record_event(
                run_id=run_id,
                event_type=RunEventType.TASK_STARTED,
                payload={"task_id": next_task.task_id},
            )

        active_task = self._find_active_task(run_state)
        if active_task is None:
            raise TurnAdvanceError(f"Run {run_id} does not have an active task")

        turn_id = generate_identifier("turn")
        turn_result = self._execute_turn_result(run_state, active_task, turn_id)
        tool_call_ids: list[str] = []
        evidence_ids: list[str] = []

        for planned_tool_call in turn_result.planned_tool_calls:
            tool_execution = execute_planned_tool_call(planned_tool_call)
            tool_call_record = self._run_tool_call_repository.save(
                RunToolCallRecord(
                    run_id=run_id,
                    turn_id=turn_id,
                    task_id=active_task.task_id,
                    agent_name=active_task.assigned_agent,
                    tool_name=tool_execution.tool_name,
                    tool_input=tool_execution.tool_input,
                    tool_output=tool_execution.tool_output,
                )
            )
            tool_call_ids.append(tool_call_record.tool_call_id)
            self._record_event(
                run_id=run_id,
                event_type=RunEventType.TOOL_EXECUTED,
                payload={
                    "tool_call_id": tool_call_record.tool_call_id,
                    "tool_name": tool_call_record.tool_name,
                    "task_id": active_task.task_id,
                },
            )

            evidence_record = self._build_evidence_from_tool_call(tool_call_record)
            run_state = record_evidence(run_state, evidence_record)
            evidence_ids.append(evidence_record.evidence_id)
            self._record_event(
                run_id=run_id,
                event_type=RunEventType.EVIDENCE_RECORDED,
                payload={"evidence_id": evidence_record.evidence_id},
            )

        run_state = complete_task(run_state, active_task.task_id)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.TASK_COMPLETED,
            payload={"task_id": active_task.task_id},
        )
        stored_run_state = self._run_repository.update(run_state)

        turn_record = self._run_turn_repository.save(
            RunTurnRecord(
                turn_id=turn_id,
                run_id=run_id,
                task_id=active_task.task_id,
                agent_name=active_task.assigned_agent,
                summary=turn_result.summary,
                tool_call_ids=tool_call_ids,
                evidence_ids=evidence_ids,
                resulting_run_status=stored_run_state.status,
            )
        )
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.TURN_EXECUTED,
            payload={
                "turn_id": turn_record.turn_id,
                "task_id": turn_record.task_id,
                "agent_name": turn_record.agent_name,
            },
        )
        return build_run_turn_advance_response(turn_record, stored_run_state)

    def finalize_run(self, run_id: str) -> RunOutputResponse:
        run_state = self._run_repository.get(run_id)
        if run_state.status is not RunStatus.VERIFYING:
            raise FinalizationError(f"Run {run_id} must be verifying before it can be finalized")

        verification_report = self._run_verification_repository.get_latest(run_id)
        if verification_report.verdict is not VerificationVerdict.PASS:
            raise FinalizationError(
                f"Run {run_id} requires a passing verification before finalization"
            )

        pending_approvals = self._run_approval_repository.list(
            run_id,
            ApprovalListQuery(limit=100, offset=0, status=ApprovalStatus.PENDING),
        )
        if pending_approvals.page.total_count > 0:
            raise FinalizationError(f"Run {run_id} has pending approvals and cannot be finalized")

        turn_page = self._run_turn_repository.list(
            run_id,
            RunTurnListQuery(limit=100, offset=0),
        )
        tool_call_page = self._run_tool_call_repository.list(
            run_id,
            RunToolCallListQuery(limit=100, offset=0),
        )

        output_record = self._run_output_repository.save(
            RunOutputRecord(
                run_id=run_id,
                title=f"Final output for {run_state.user_goal}",
                summary=(
                    f"Completed run with {len(run_state.tasks)} tasks, "
                    f"{len(run_state.evidence)} evidence items, and "
                    f"{len(tool_call_page.items)} tool calls."
                ),
                key_findings=self._build_key_findings(
                    run_state,
                    turn_page.items,
                    tool_call_page.items,
                ),
                evidence_refs=[item.evidence_id for item in run_state.evidence],
                tool_call_refs=[item.tool_call_id for item in tool_call_page.items],
                turn_refs=[item.turn_id for item in turn_page.items],
            )
        )

        updated_run_state = run_state.model_copy(
            update={
                "status": RunStatus.COMPLETED,
                "final_output_ref": output_record.output_id,
            }
        )
        self._run_repository.update(updated_run_state)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.RUN_FINALIZED,
            payload={
                "output_id": output_record.output_id,
                "status": RunStatus.COMPLETED.value,
            },
        )
        return build_run_output_response(output_record)

    def get_latest_output(self, run_id: str) -> RunOutputResponse:
        self._run_repository.get(run_id)
        output_record = self._run_output_repository.get_latest(run_id)
        return build_run_output_response(output_record)

    def list_turns(
        self,
        run_id: str,
        query: RunTurnListQuery,
    ) -> RunTurnListResponse:
        self._run_repository.get(run_id)
        run_turn_page = self._run_turn_repository.list(run_id, query)
        return build_run_turn_list_response(run_turn_page)

    def list_tool_calls(
        self,
        run_id: str,
        query: RunToolCallListQuery,
    ) -> RunToolCallListResponse:
        self._run_repository.get(run_id)
        run_tool_call_page = self._run_tool_call_repository.list(run_id, query)
        return build_run_tool_call_list_response(run_tool_call_page)

    def list_llm_calls(
        self,
        run_id: str,
        query: LlmCallListQuery,
    ) -> LlmCallListResponse:
        self._run_repository.get(run_id)
        llm_call_page = self._llm_call_repository.list(run_id, query)
        return build_llm_call_list_response(llm_call_page)

    def list_run_events(
        self,
        run_id: str,
        query: RunEventListQuery,
    ) -> RunEventListResponse:
        self._run_repository.get(run_id)
        run_event_page = self._run_event_repository.list(run_id, query)
        return build_run_event_list_response(run_event_page)

    def request_approval(
        self,
        run_id: str,
        request: ApprovalRequestCreate,
    ) -> RunApprovalResponse:
        self._run_repository.get(run_id)
        approval_record = ApprovalRecord(
            run_id=run_id,
            requested_action=request.requested_action,
            reason=request.reason,
            risk_summary=request.risk_summary,
            proposed_next_step=request.proposed_next_step,
            supporting_evidence_refs=request.supporting_evidence_refs,
        )
        stored_record = self._run_approval_repository.create(approval_record)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.APPROVAL_REQUESTED,
            payload={
                "approval_id": stored_record.approval_id,
                "status": stored_record.status.value,
            },
        )
        return build_run_approval_response(stored_record)

    def decide_approval(
        self,
        run_id: str,
        approval_id: str,
        request: ApprovalDecisionRequest,
    ) -> RunApprovalResponse:
        self._run_repository.get(run_id)
        approval_record = self._run_approval_repository.get(run_id, approval_id)
        if approval_record.status is not ApprovalStatus.PENDING:
            raise ApprovalTransitionError(f"Approval {approval_id} is no longer pending")
        updated_record = approval_record.model_copy(
            update={
                "status": self._map_decision_to_status(request.decision),
                "reviewer_id": request.reviewer_id,
                "reviewer_note": request.reviewer_note,
                "decided_at": approval_record.requested_at.__class__.now(
                    approval_record.requested_at.tzinfo
                ),
            }
        )
        stored_record = self._run_approval_repository.update(updated_record)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.APPROVAL_DECIDED,
            payload={
                "approval_id": stored_record.approval_id,
                "decision": request.decision.value,
                "status": stored_record.status.value,
            },
        )
        return build_run_approval_response(stored_record)

    def list_approvals(
        self,
        run_id: str,
        query: ApprovalListQuery,
    ) -> RunApprovalListResponse:
        self._run_repository.get(run_id)
        approval_page = self._run_approval_repository.list(run_id, query)
        return build_run_approval_list_response(approval_page)

    def register_tasks(
        self,
        run_id: str,
        request: TaskRegistrationRequest,
    ) -> RunStateResponse:
        run_state = self._run_repository.get(run_id)
        task_records = request.to_task_records()
        updated_run_state = register_tasks(run_state, task_records)
        stored_run_state = self._run_repository.update(updated_run_state)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.TASKS_REGISTERED,
            payload={"task_ids": [task.task_id for task in task_records]},
        )
        return build_run_state_response(stored_run_state)

    def start_task(
        self,
        run_id: str,
        request: TaskStartRequest,
    ) -> RunStateResponse:
        run_state = self._run_repository.get(run_id)
        updated_run_state = start_task(run_state, request.task_id)
        stored_run_state = self._run_repository.update(updated_run_state)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.TASK_STARTED,
            payload={"task_id": request.task_id},
        )
        return build_run_state_response(stored_run_state)

    def complete_task(
        self,
        run_id: str,
        request: TaskCompleteRequest,
    ) -> RunStateResponse:
        run_state = self._run_repository.get(run_id)
        updated_run_state = complete_task(run_state, request.task_id)
        stored_run_state = self._run_repository.update(updated_run_state)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.TASK_COMPLETED,
            payload={"task_id": request.task_id},
        )
        return build_run_state_response(stored_run_state)

    def record_evidence(
        self,
        run_id: str,
        request: EvidenceCreateRequest,
    ) -> RunStateResponse:
        run_state = self._run_repository.get(run_id)
        updated_run_state = record_evidence(run_state, request.to_evidence_record())
        stored_run_state = self._run_repository.update(updated_run_state)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.EVIDENCE_RECORDED,
            payload={"evidence_id": request.evidence_id},
        )
        return build_run_state_response(stored_run_state)

    def verify_run(self, run_id: str) -> RunVerificationResponse:
        run_state = self._run_repository.get(run_id)
        report = build_run_verification_report(run_state)
        stored_report = self._run_verification_repository.save(report)
        self._record_event(
            run_id=run_id,
            event_type=RunEventType.VERIFICATION_COMPLETED,
            payload={"verdict": stored_report.verdict.value},
        )
        return RunVerificationResponse(item=stored_report)

    def get_latest_verification(self, run_id: str) -> RunVerificationResponse:
        self._run_repository.get(run_id)
        report = self._run_verification_repository.get_latest(run_id)
        return RunVerificationResponse(item=report)

    def _build_execution_profile(self, task: TaskRecord) -> AgentExecutionProfile:
        if self._execution_backend is ExecutionBackend.LLM:
            return AgentExecutionProfile(
                agent_name=task.assigned_agent,
                backend=ExecutionBackend.LLM,
                llm_provider_name=self._llm_provider_name,
                model_name=self._llm_model_name,
                timeout_seconds=30.0,
            )
        return AgentExecutionProfile(
            agent_name=task.assigned_agent,
            backend=ExecutionBackend.DETERMINISTIC,
        )

    def _execute_turn_result(
        self,
        run_state: RunStateSnapshot,
        task: TaskRecord,
        turn_id: str,
    ) -> TurnExecutionResult:
        execution_profile = self._build_execution_profile(task)
        if self._execution_backend is ExecutionBackend.LLM:
            if not isinstance(self._turn_executor, LlmTurnExecutor):
                raise ValueError("LLM execution backend requires LlmTurnExecutor")
            llm_response = self._turn_executor.execute_structured_turn(
                run_state,
                task,
                execution_profile,
            )
            self._llm_call_repository.save(
                self._build_llm_call_record(
                    run_state,
                    task,
                    turn_id,
                    execution_profile,
                    llm_response,
                )
            )
            return TurnExecutionResult(
                summary=llm_response.output.summary,
                planned_tool_calls=llm_response.output.planned_tool_calls,
            )
        return self._turn_executor.execute_turn(
            run_state,
            task,
            execution_profile,
        )

    def _build_llm_call_record(
        self,
        run_state: RunStateSnapshot,
        task: TaskRecord,
        turn_id: str,
        execution_profile: AgentExecutionProfile,
        llm_response: LlmTurnResponse,
    ) -> LlmCallRecord:
        return LlmCallRecord(
            run_id=run_state.run_id,
            turn_id=turn_id,
            task_id=task.task_id,
            agent_name=task.assigned_agent,
            provider_name=llm_response.provider_name,
            model_name=llm_response.model_name,
            structured_output=llm_response.output,
            usage=llm_response.usage,
            available_tool_names=list_available_tool_names(),
            request_payload={
                "run_id": run_state.run_id,
                "user_goal": run_state.user_goal,
                "task": task.model_dump(mode="json"),
                "execution_profile": execution_profile.model_dump(mode="json"),
            },
            response_payload=llm_response.model_dump(mode="json"),
            finish_reason=llm_response.finish_reason,
            latency_ms=llm_response.latency_ms,
            raw_response_text=llm_response.raw_response_text,
        )

    def _find_next_ready_task(
        self,
        run_state: RunStateSnapshot,
    ) -> TaskRecord | None:
        for task in run_state.tasks:
            if task.status is TaskStatus.READY:
                return task
        return None

    def _find_active_task(
        self,
        run_state: RunStateSnapshot,
    ) -> TaskRecord | None:
        current_task_id = run_state.current_task_id
        if current_task_id is None:
            return None
        for task in run_state.tasks:
            if task.task_id == current_task_id:
                return task
        return None

    def _build_evidence_from_tool_call(
        self,
        tool_call_record: RunToolCallRecord,
    ) -> EvidenceRecord:
        output_summary = "; ".join(
            f"{key}: {value}" for key, value in tool_call_record.tool_output.items()
        )
        return EvidenceRecord(
            evidence_id=generate_identifier("evidence"),
            source_type="tool_call",
            source_ref=tool_call_record.tool_call_id,
            summary=f"{tool_call_record.tool_name} produced {output_summary}",
            collected_by_agent=tool_call_record.agent_name,
            confidence=0.86,
        )

    def _build_key_findings(
        self,
        run_state: RunStateSnapshot,
        turn_records: list[RunTurnRecord],
        tool_call_records: list[RunToolCallRecord],
    ) -> list[str]:
        findings = [
            f"Completed {task.title}"
            for task in run_state.tasks
            if task.status is TaskStatus.COMPLETED
        ]
        findings.extend(
            f"{item.tool_name}: {'; '.join(item.tool_output.values())}"
            for item in tool_call_records
        )
        findings.extend(item.summary for item in turn_records)
        if not findings:
            findings.append("Run completed through deterministic execution.")
        return findings[:6]

    def _record_event(
        self,
        run_id: str,
        event_type: RunEventType,
        payload: dict[str, object],
    ) -> None:
        self._run_event_repository.append(
            RunEventRecord(
                run_id=run_id,
                event_type=event_type,
                payload=payload,
            )
        )

    def _map_decision_to_status(self, decision: ApprovalDecision) -> ApprovalStatus:
        if decision is ApprovalDecision.APPROVE:
            return ApprovalStatus.APPROVED
        if decision is ApprovalDecision.REJECT:
            return ApprovalStatus.REJECTED
        return ApprovalStatus.REVISION_REQUESTED


__all__ = [
    "ApprovalTransitionError",
    "FinalizationError",
    "PlanningTransitionError",
    "RunService",
    "StateTransitionError",
    "TurnAdvanceError",
]
