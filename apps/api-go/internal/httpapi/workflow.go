package httpapi

import (
	"context"
	"fmt"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/contracts"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
)

func (handler Handler) GeneratePlan(response http.ResponseWriter, request *http.Request) {
	runState, ok := handler.getRunState(response, request)
	if !ok {
		return
	}
	if len(runState.Tasks) > 0 {
		writeError(
			response,
			http.StatusConflict,
			"Run "+runState.RunID+" already has registered tasks and cannot be planned again",
		)
		return
	}

	plan, providerUsage, err := handler.buildRunPlan(request.Context(), runState)
	if err != nil {
		if isProviderBudgetError(err) {
			writeError(response, http.StatusPaymentRequired, err.Error())
			return
		}
		handler.logError("build plan failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to build run plan")
		return
	}
	updatedRunState, err := domain.RegisterTasks(runState, plan.Tasks)
	if err != nil {
		writeError(response, http.StatusConflict, err.Error())
		return
	}

	taskIDs := make([]string, 0, len(plan.Tasks))
	for _, task := range plan.Tasks {
		taskIDs = append(taskIDs, task.TaskID)
	}
	planEvent, err := domain.NewRunEvent(
		runState.RunID,
		domain.RunEventTypePlanGenerated,
		map[string]any{
			"plan_id":          plan.PlanID,
			"template_name":    plan.TemplateName,
			"planning_backend": handler.dependencies.Settings.PlanningBackend,
		},
	)
	if err != nil {
		handler.logError("build plan event failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to build plan event")
		return
	}
	tasksEvent, err := domain.NewRunEvent(
		runState.RunID,
		domain.RunEventTypeTasksRegistered,
		map[string]any{"task_ids": taskIDs},
	)
	if err != nil {
		handler.logError("build tasks event failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to build tasks event")
		return
	}

	storedPlan, err := handler.dependencies.Store.SavePlanAndRunState(
		request.Context(),
		plan,
		updatedRunState,
		[]domain.RunEventRecord{planEvent, tasksEvent},
		providerUsage,
	)
	if err != nil {
		handler.logError("save plan failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to save run plan")
		return
	}

	writeJSON(response, http.StatusOK, domain.RunPlanResponse{Item: storedPlan})
}

func (handler Handler) buildRunPlan(
	ctx context.Context,
	runState domain.RunStateSnapshot,
) (domain.RunPlanReport, *domain.ProviderUsageRecord, error) {
	if handler.dependencies.Settings.PlanningBackend != "llm" {
		plan, err := domain.BuildRunPlan(runState)
		return plan, nil, err
	}
	policy := handler.providerPolicyForRun(runState)
	route := policy.Planning
	if err := handler.enforceProviderBudget(
		ctx,
		policy,
		runState.RunID,
		providerPolicyOperationPlanning,
	); err != nil {
		return domain.RunPlanReport{}, nil, err
	}
	if handler.dependencies.WorkerClient == nil {
		if route.FallbackEnabled {
			plan, err := domain.BuildRunPlan(runState)
			return plan, nil, err
		}
		return domain.RunPlanReport{}, nil, fmt.Errorf("planning backend is llm but worker client is not configured")
	}

	workerOutcome, err := handler.dependencies.WorkerClient.GeneratePlan(
		ctx,
		contracts.LLMWorkerPlanRequest{
			RunID:        runState.RunID,
			UserGoal:     runState.UserGoal,
			WorkflowType: string(runState.WorkflowType),
			ExecutionProfile: route.executionProfile("planner"),
		},
	)
	if err != nil {
		if route.FallbackEnabled {
			plan, buildErr := domain.BuildRunPlan(runState)
			return plan, nil, buildErr
		}
		return domain.RunPlanReport{}, nil, err
	}
	if workerOutcome.FallbackUsed && !route.FallbackEnabled {
		if workerOutcome.ErrorMessage != nil {
			return domain.RunPlanReport{}, nil, fmt.Errorf("%s", *workerOutcome.ErrorMessage)
		}
		return domain.RunPlanReport{}, nil, fmt.Errorf("LLM planning returned fallback output")
	}

	plan, err := domain.NewRunPlanFromPlannedTasks(
		runState,
		workerOutcome.Output.TemplateName,
		workerOutcome.Output.Summary,
		mapWorkerPlannedTasks(workerOutcome.Output.Tasks),
	)
	if err != nil {
		return domain.RunPlanReport{}, nil, err
	}

	providerUsage, err := buildPlanningProviderUsage(runState, route, workerOutcome)
	if err != nil {
		return domain.RunPlanReport{}, nil, err
	}
	return plan, providerUsage, nil
}

func mapWorkerPlannedTasks(items []contracts.PlannedTask) []domain.PlannedTask {
	mapped := make([]domain.PlannedTask, 0, len(items))
	for _, item := range items {
		mapped = append(mapped, domain.PlannedTask{
			TaskID:             item.TaskID,
			Title:              item.Title,
			Description:        item.Description,
			AssignedAgent:      item.AssignedAgent,
			DependencyIDs:      item.DependencyIDs,
			AcceptanceCriteria: item.AcceptanceCriteria,
		})
	}
	return mapped
}

func (handler Handler) GetLatestPlan(response http.ResponseWriter, request *http.Request) {
	runID := chi.URLParam(request, "run_id")
	if _, ok := handler.getRunState(response, request); !ok {
		return
	}

	plan, err := handler.dependencies.Store.GetLatestRunPlan(request.Context(), runID)
	if err != nil {
		handler.logError("get latest plan failed", err)
		writeError(response, http.StatusNotFound, "Latest plan does not exist for run "+runID)
		return
	}

	writeJSON(response, http.StatusOK, domain.RunPlanResponse{Item: plan})
}

func (handler Handler) AdvanceTurn(response http.ResponseWriter, request *http.Request) {
	runState, ok := handler.getRunState(response, request)
	if !ok {
		return
	}

	events := make([]domain.RunEventRecord, 0)
	if runState.CurrentTaskID == nil {
		nextTask := domain.FindNextReadyTask(runState)
		if nextTask == nil {
			writeError(response, http.StatusConflict, "Run "+runState.RunID+" has no ready task to advance")
			return
		}
		runState = domain.StartTask(runState, nextTask.TaskID)
		taskStartedEvent, err := domain.NewRunEvent(
			runState.RunID,
			domain.RunEventTypeTaskStarted,
			map[string]any{"task_id": nextTask.TaskID},
		)
		if err != nil {
			handler.logError("build task started event failed", err)
			writeError(response, http.StatusInternalServerError, "Failed to build task event")
			return
		}
		events = append(events, taskStartedEvent)
	}

	activeTask := domain.FindActiveTask(runState)
	if activeTask == nil {
		writeError(response, http.StatusConflict, "Run "+runState.RunID+" does not have an active task")
		return
	}

	turnID, err := domain.NewID("turn")
	if err != nil {
		handler.logError("build turn id failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to build turn")
		return
	}
	executionOutcome, err := handler.executeTurn(request.Context(), runState, *activeTask, turnID)
	if err != nil {
		if isProviderBudgetError(err) {
			writeError(response, http.StatusPaymentRequired, err.Error())
			return
		}
		handler.logError("execute turn failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to execute turn")
		return
	}
	turnResult := executionOutcome.Result
	toolCalls := make([]domain.RunToolCallRecord, 0, len(turnResult.PlannedToolCalls))
	llmCalls := make([]domain.LLMCallRecord, 0, 1)
	providerUsage := make([]domain.ProviderUsageRecord, 0, 1)
	if executionOutcome.LLMCall != nil {
		llmCalls = append(llmCalls, *executionOutcome.LLMCall)
	}
	if executionOutcome.ProviderUsage != nil {
		providerUsage = append(providerUsage, *executionOutcome.ProviderUsage)
	}
	toolCallIDs := make([]string, 0, len(turnResult.PlannedToolCalls))
	evidenceIDs := make([]string, 0, len(turnResult.PlannedToolCalls))

	for _, plannedToolCall := range turnResult.PlannedToolCalls {
		toolCall, err := domain.NewToolCallRecord(
			runState.RunID,
			turnID,
			*activeTask,
			plannedToolCall,
		)
		if err != nil {
			handler.logError("build tool call failed", err)
			writeError(response, http.StatusInternalServerError, "Failed to build tool call")
			return
		}
		toolCalls = append(toolCalls, toolCall)
		toolCallIDs = append(toolCallIDs, toolCall.ToolCallID)

		toolEvent, err := domain.NewRunEvent(
			runState.RunID,
			domain.RunEventTypeToolExecuted,
			map[string]any{
				"tool_call_id": toolCall.ToolCallID,
				"tool_name":    toolCall.ToolName,
				"task_id":      activeTask.TaskID,
			},
		)
		if err != nil {
			handler.logError("build tool event failed", err)
			writeError(response, http.StatusInternalServerError, "Failed to build tool event")
			return
		}
		events = append(events, toolEvent)

		evidenceRecord, err := domain.BuildEvidenceFromToolCall(toolCall)
		if err != nil {
			handler.logError("build evidence failed", err)
			writeError(response, http.StatusInternalServerError, "Failed to build evidence")
			return
		}
		runState.Evidence = append(runState.Evidence, evidenceRecord)
		evidenceIDs = append(evidenceIDs, evidenceRecord.EvidenceID)

		evidenceEvent, err := domain.NewRunEvent(
			runState.RunID,
			domain.RunEventTypeEvidenceRecorded,
			map[string]any{"evidence_id": evidenceRecord.EvidenceID},
		)
		if err != nil {
			handler.logError("build evidence event failed", err)
			writeError(response, http.StatusInternalServerError, "Failed to build evidence event")
			return
		}
		events = append(events, evidenceEvent)
	}

	completedTaskID := activeTask.TaskID
	runState = domain.CompleteTask(runState, completedTaskID)
	taskCompletedEvent, err := domain.NewRunEvent(
		runState.RunID,
		domain.RunEventTypeTaskCompleted,
		map[string]any{"task_id": completedTaskID},
	)
	if err != nil {
		handler.logError("build task completed event failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to build task completed event")
		return
	}
	events = append(events, taskCompletedEvent)

	turn := domain.NewTurnRecord(
		turnID,
		runState.RunID,
		*activeTask,
		turnResult,
		toolCallIDs,
		evidenceIDs,
		runState.Status,
	)
	turnEvent, err := domain.NewRunEvent(
		runState.RunID,
		domain.RunEventTypeTurnExecuted,
		map[string]any{
			"turn_id":    turn.TurnID,
			"task_id":    turn.TaskID,
			"agent_name": turn.AgentName,
		},
	)
	if err != nil {
		handler.logError("build turn event failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to build turn event")
		return
	}
	events = append(events, turnEvent)

	storedTurn, storedRunState, err := handler.dependencies.Store.SaveTurnAdvance(
		request.Context(),
		runState,
		turn,
		toolCalls,
		llmCalls,
		providerUsage,
		events,
	)
	if err != nil {
		handler.logError("save turn advance failed", err)
		writeError(response, http.StatusInternalServerError, "Failed to advance turn")
		return
	}

	writeJSON(
		response,
		http.StatusOK,
		domain.RunTurnAdvanceResponse{Turn: storedTurn, RunState: storedRunState},
	)
}
