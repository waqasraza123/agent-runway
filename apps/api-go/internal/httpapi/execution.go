package httpapi

import (
	"context"
	"fmt"

	"github.com/waqasraza123/agent-runway/apps/api-go/internal/contracts"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
)

var availableToolNames = []string{
	"goal_analyzer",
	"evidence_lookup",
	"summary_writer",
	"execution_checker",
	"generic_tool",
}

type turnExecutionOutcome struct {
	Result        domain.TurnExecutionResult
	LLMCall       *domain.LLMCallRecord
	ProviderUsage *domain.ProviderUsageRecord
}

func (handler Handler) executeTurn(
	ctx context.Context,
	runState domain.RunStateSnapshot,
	task domain.TaskRecord,
	turnID string,
) (turnExecutionOutcome, error) {
	if handler.dependencies.Settings.ExecutionBackend != "llm" {
		return turnExecutionOutcome{
			Result: domain.ExecuteDeterministicTurn(runState, task),
		}, nil
	}
	policy := handler.providerPolicyForRun(runState)
	route := policy.Execution
	if err := handler.enforceProviderBudget(
		ctx,
		policy,
		runState.RunID,
		providerPolicyOperationExecution,
	); err != nil {
		return turnExecutionOutcome{}, err
	}

	workerRequest := contracts.LLMWorkerTurnRequest{
		RunID:    runState.RunID,
		UserGoal: runState.UserGoal,
		Task: contracts.TaskRecord{
			TaskID:             task.TaskID,
			Title:              task.Title,
			Description:        task.Description,
			AssignedAgent:      task.AssignedAgent,
			Status:             task.Status,
			DependencyIDs:      task.DependencyIDs,
			AcceptanceCriteria: task.AcceptanceCriteria,
			RiskLevel:          task.RiskLevel,
			AttemptCount:       task.AttemptCount,
		},
		ExecutionProfile: route.executionProfile(task.AssignedAgent),
		AvailableToolNames: availableToolNames,
	}

	workerOutcome, err := handler.dependencies.WorkerClient.ExecuteTurn(ctx, workerRequest)
	if err != nil {
		if !route.FallbackEnabled {
			return turnExecutionOutcome{}, err
		}
		return handler.buildWorkerFallbackOutcome(runState, task, turnID, route, err.Error())
	}
	if workerOutcome.FallbackUsed && !route.FallbackEnabled {
		if workerOutcome.ErrorMessage != nil {
			return turnExecutionOutcome{}, fmt.Errorf("%s", *workerOutcome.ErrorMessage)
		}
		return turnExecutionOutcome{}, fmt.Errorf("LLM execution returned fallback output")
	}

	turnResult := domain.TurnExecutionResult{
		Summary:          workerOutcome.Output.Summary,
		PlannedToolCalls: mapPlannedToolCalls(workerOutcome.Output.PlannedToolCalls),
	}

	providerName := route.ProviderName
	modelName := route.ModelName
	var finishReason *string
	var latencyMS *int
	var rawResponseText *string
	usage := domain.LLMUsage{}
	responsePayload := map[string]any{
		"fallback_used": workerOutcome.FallbackUsed,
		"attempt_count": workerOutcome.AttemptCount,
	}

	if workerOutcome.LLMResponse != nil {
		providerName = workerOutcome.LLMResponse.ProviderName
		modelName = workerOutcome.LLMResponse.ModelName
		finishReason = workerOutcome.LLMResponse.FinishReason
		latencyMS = workerOutcome.LLMResponse.LatencyMS
		rawResponseText = workerOutcome.LLMResponse.RawResponseText
		usage = domain.LLMUsage{
			InputTokens:      workerOutcome.LLMResponse.Usage.InputTokens,
			OutputTokens:     workerOutcome.LLMResponse.Usage.OutputTokens,
			TotalTokens:      workerOutcome.LLMResponse.Usage.TotalTokens,
			EstimatedCostUSD: workerOutcome.LLMResponse.Usage.EstimatedCostUSD,
		}
		responsePayload["provider_name"] = providerName
		responsePayload["model_name"] = modelName
	}

	llmCall, err := domain.NewLLMCallRecord(
		runState.RunID,
		turnID,
		task,
		providerName,
		modelName,
		domain.StructuredTurnOutput{
			Summary:          workerOutcome.Output.Summary,
			PlannedToolCalls: mapPlannedToolCalls(workerOutcome.Output.PlannedToolCalls),
		},
		usage,
		availableToolNames,
		map[string]any{
			"run_id":               workerRequest.RunID,
			"task_id":              workerRequest.Task.TaskID,
			"agent_name":           workerRequest.ExecutionProfile.AgentName,
			"llm_provider_name":    providerName,
			"model_name":           modelName,
			"available_tool_names": availableToolNames,
		},
		responsePayload,
		finishReason,
		latencyMS,
		workerOutcome.ErrorMessage,
		rawResponseText,
		workerOutcome.AttemptCount,
		workerOutcome.FallbackUsed,
	)
	if err != nil {
		return turnExecutionOutcome{}, err
	}

	providerUsage, err := buildExecutionProviderUsage(runState, route, workerOutcome)
	if err != nil {
		return turnExecutionOutcome{}, err
	}

	return turnExecutionOutcome{
		Result:        turnResult,
		LLMCall:       &llmCall,
		ProviderUsage: providerUsage,
	}, nil
}

func (handler Handler) buildWorkerFallbackOutcome(
	runState domain.RunStateSnapshot,
	task domain.TaskRecord,
	turnID string,
	route resolvedProviderRoute,
	errorMessage string,
) (turnExecutionOutcome, error) {
	turnResult := domain.ExecuteDeterministicTurn(runState, task)
	errorMessageRef := errorMessage
	llmCall, err := domain.NewLLMCallRecord(
		runState.RunID,
		turnID,
		task,
		route.ProviderName,
		route.ModelName,
		domain.StructuredTurnOutput{
			Summary:          turnResult.Summary,
			PlannedToolCalls: turnResult.PlannedToolCalls,
		},
		domain.LLMUsage{},
		availableToolNames,
		map[string]any{
			"run_id":               runState.RunID,
			"task_id":              task.TaskID,
			"agent_name":           task.AssignedAgent,
			"llm_provider_name":    route.ProviderName,
			"model_name":           route.ModelName,
			"available_tool_names": availableToolNames,
		},
		map[string]any{
			"fallback_used": true,
			"error_message":  errorMessage,
		},
		nil,
		nil,
		&errorMessageRef,
		nil,
		1,
		true,
	)
	if err != nil {
		return turnExecutionOutcome{}, err
	}
	return turnExecutionOutcome{
		Result:  turnResult,
		LLMCall: &llmCall,
	}, nil
}

func buildPlanningProviderUsage(
	runState domain.RunStateSnapshot,
	route resolvedProviderRoute,
	workerOutcome contracts.LLMPlanningOutcome,
) (*domain.ProviderUsageRecord, error) {
	if workerOutcome.LLMResponse == nil {
		return nil, nil
	}
	usage := domain.LLMUsage{
		InputTokens:      workerOutcome.LLMResponse.Usage.InputTokens,
		OutputTokens:     workerOutcome.LLMResponse.Usage.OutputTokens,
		TotalTokens:      workerOutcome.LLMResponse.Usage.TotalTokens,
		EstimatedCostUSD: workerOutcome.LLMResponse.Usage.EstimatedCostUSD,
	}
	record, err := domain.NewProviderUsageRecord(
		runState.TenantID,
		runState.RunID,
		domain.ProviderUsageOperationPlanning,
		workerOutcome.LLMResponse.ProviderName,
		workerOutcome.LLMResponse.ModelName,
		usage,
		map[string]any{
			"configured_provider_name": route.ProviderName,
			"configured_model_name":    route.ModelName,
			"fallback_used":            workerOutcome.FallbackUsed,
			"attempt_count":            workerOutcome.AttemptCount,
		},
	)
	if err != nil {
		return nil, err
	}
	return &record, nil
}

func buildExecutionProviderUsage(
	runState domain.RunStateSnapshot,
	route resolvedProviderRoute,
	workerOutcome contracts.LLMExecutionOutcome,
) (*domain.ProviderUsageRecord, error) {
	if workerOutcome.LLMResponse == nil {
		return nil, nil
	}
	usage := domain.LLMUsage{
		InputTokens:      workerOutcome.LLMResponse.Usage.InputTokens,
		OutputTokens:     workerOutcome.LLMResponse.Usage.OutputTokens,
		TotalTokens:      workerOutcome.LLMResponse.Usage.TotalTokens,
		EstimatedCostUSD: workerOutcome.LLMResponse.Usage.EstimatedCostUSD,
	}
	record, err := domain.NewProviderUsageRecord(
		runState.TenantID,
		runState.RunID,
		domain.ProviderUsageOperationExecution,
		workerOutcome.LLMResponse.ProviderName,
		workerOutcome.LLMResponse.ModelName,
		usage,
		map[string]any{
			"configured_provider_name": route.ProviderName,
			"configured_model_name":    route.ModelName,
			"fallback_used":            workerOutcome.FallbackUsed,
			"attempt_count":            workerOutcome.AttemptCount,
		},
	)
	if err != nil {
		return nil, err
	}
	return &record, nil
}

func mapPlannedToolCalls(items []contracts.PlannedToolCall) []domain.PlannedToolCall {
	mapped := make([]domain.PlannedToolCall, 0, len(items))
	for _, item := range items {
		mapped = append(mapped, domain.PlannedToolCall{
			ToolName:  item.ToolName,
			ToolInput: item.ToolInput,
		})
	}
	return mapped
}
