package httpapi

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/waqasraza123/agent-runway/apps/api-go/internal/config"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/contracts"
	"github.com/waqasraza123/agent-runway/apps/api-go/internal/domain"
)

type providerPolicyOperation string

const (
	providerPolicyOperationPlanning  providerPolicyOperation = "planning"
	providerPolicyOperationExecution providerPolicyOperation = "execution"
)

type resolvedProviderRoute struct {
	ProviderName    string
	ModelName       string
	Temperature     *float64
	MaxOutputTokens *int
	TimeoutSeconds  *float64
	MaxRetries      int
	FallbackEnabled bool
}

type resolvedProviderPolicy struct {
	TenantID          string
	Planning         resolvedProviderRoute
	Execution        resolvedProviderRoute
	MonthlyBudgetUSD *float64
	PerRunBudgetUSD  *float64
	BudgetMode       string
}

type providerBudgetError struct {
	Message string
}

func (err providerBudgetError) Error() string {
	return err.Message
}

func isProviderBudgetError(err error) bool {
	_, ok := err.(providerBudgetError)
	return ok
}

func (handler Handler) providerPolicyForRun(runState domain.RunStateSnapshot) resolvedProviderPolicy {
	policy := resolvedProviderPolicy{
		TenantID: runState.TenantID,
		Planning: resolvedProviderRoute{
			ProviderName:    handler.dependencies.Settings.PlanningProviderName,
			ModelName:       handler.dependencies.Settings.PlanningModelName,
			Temperature:     handler.dependencies.Settings.PlanningTemperature,
			MaxOutputTokens: handler.dependencies.Settings.PlanningMaxOutputTokens,
			TimeoutSeconds:  handler.dependencies.Settings.PlanningTimeoutSeconds,
			MaxRetries:      handler.dependencies.Settings.PlanningMaxRetries,
			FallbackEnabled: handler.dependencies.Settings.PlanningFallbackEnabled,
		},
		Execution: resolvedProviderRoute{
			ProviderName:    handler.dependencies.Settings.LLMProviderName,
			ModelName:       handler.dependencies.Settings.LLMModelName,
			Temperature:     handler.dependencies.Settings.LLMTemperature,
			MaxOutputTokens: handler.dependencies.Settings.LLMMaxOutputTokens,
			TimeoutSeconds:  handler.dependencies.Settings.LLMTimeoutSeconds,
			MaxRetries:      handler.dependencies.Settings.LLMMaxRetries,
			FallbackEnabled: handler.dependencies.Settings.ExecutionFallbackEnabled,
		},
		BudgetMode: "block",
	}

	for _, tenantPolicy := range handler.dependencies.Settings.TenantProviderPolicies {
		if tenantPolicy.TenantID != runState.TenantID {
			continue
		}
		policy.Planning = mergeProviderRoute(policy.Planning, tenantPolicy.Planning)
		policy.Execution = mergeProviderRoute(policy.Execution, tenantPolicy.Execution)
		policy.MonthlyBudgetUSD = tenantPolicy.MonthlyBudgetUSD
		policy.PerRunBudgetUSD = tenantPolicy.PerRunBudgetUSD
		if tenantPolicy.BudgetMode != "" {
			policy.BudgetMode = tenantPolicy.BudgetMode
		}
		break
	}
	return policy
}

func mergeProviderRoute(
	base resolvedProviderRoute,
	override config.ProviderRouteConfig,
) resolvedProviderRoute {
	if override.ProviderName != "" {
		base.ProviderName = override.ProviderName
	}
	if override.ModelName != "" {
		base.ModelName = override.ModelName
	}
	if override.Temperature != nil {
		base.Temperature = override.Temperature
	}
	if override.MaxOutputTokens != nil {
		base.MaxOutputTokens = override.MaxOutputTokens
	}
	if override.TimeoutSeconds != nil {
		base.TimeoutSeconds = override.TimeoutSeconds
	}
	if override.MaxRetries != nil {
		base.MaxRetries = *override.MaxRetries
	}
	if override.FallbackEnabled != nil {
		base.FallbackEnabled = *override.FallbackEnabled
	}
	return base
}

func (route resolvedProviderRoute) executionProfile(agentName string) contracts.AgentExecutionProfile {
	return contracts.AgentExecutionProfile{
		AgentName:       agentName,
		Backend:         contracts.ExecutionBackendLLM,
		LLMProviderName: &route.ProviderName,
		ModelName:       &route.ModelName,
		Temperature:     route.Temperature,
		MaxOutputTokens: route.MaxOutputTokens,
		TimeoutSeconds:  route.TimeoutSeconds,
		MaxRetries:      route.MaxRetries,
	}
}

func (handler Handler) enforceProviderBudget(
	ctx context.Context,
	policy resolvedProviderPolicy,
	runID string,
	operation providerPolicyOperation,
) error {
	if handler.dependencies.Store == nil ||
		(policy.MonthlyBudgetUSD == nil && policy.PerRunBudgetUSD == nil) {
		return nil
	}

	monthStart := time.Now().UTC()
	monthStart = time.Date(monthStart.Year(), monthStart.Month(), 1, 0, 0, 0, 0, time.UTC)

	if policy.MonthlyBudgetUSD != nil {
		spend, err := handler.dependencies.Store.SumProviderUsage(
			ctx,
			policy.TenantID,
			nil,
			monthStart,
		)
		if err != nil {
			return fmt.Errorf("check monthly provider budget: %w", err)
		}
		if spend >= *policy.MonthlyBudgetUSD {
			return handler.handleBudgetLimit(
				policy,
				operation,
				"monthly",
				spend,
				*policy.MonthlyBudgetUSD,
			)
		}
	}

	if policy.PerRunBudgetUSD != nil {
		spend, err := handler.dependencies.Store.SumProviderUsage(
			ctx,
			policy.TenantID,
			&runID,
			time.Time{},
		)
		if err != nil {
			return fmt.Errorf("check run provider budget: %w", err)
		}
		if spend >= *policy.PerRunBudgetUSD {
			return handler.handleBudgetLimit(
				policy,
				operation,
				"per_run",
				spend,
				*policy.PerRunBudgetUSD,
			)
		}
	}

	return nil
}

func (handler Handler) handleBudgetLimit(
	policy resolvedProviderPolicy,
	operation providerPolicyOperation,
	scope string,
	spend float64,
	limit float64,
) error {
	message := fmt.Sprintf(
		"%s provider budget exceeded for tenant %s during %s: %.6f >= %.6f",
		scope,
		policy.TenantID,
		operation,
		spend,
		limit,
	)
	if strings.EqualFold(policy.BudgetMode, "warn") {
		if handler.dependencies.Logger != nil {
			handler.dependencies.Logger.Warn(
				"provider_budget_limit_reached",
				"tenant_id", policy.TenantID,
				"operation", string(operation),
				"scope", scope,
				"spend_usd", spend,
				"limit_usd", limit,
			)
		}
		return nil
	}
	return providerBudgetError{Message: message}
}
