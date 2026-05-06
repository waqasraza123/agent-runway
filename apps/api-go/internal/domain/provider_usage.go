package domain

import "time"

type ProviderUsageOperation string

const (
	ProviderUsageOperationPlanning  ProviderUsageOperation = "planning"
	ProviderUsageOperationExecution ProviderUsageOperation = "execution"
)

type ProviderUsageRecord struct {
	UsageID          string                 `json:"usage_id"`
	TenantID         string                 `json:"tenant_id"`
	RunID            string                 `json:"run_id"`
	Operation        ProviderUsageOperation `json:"operation"`
	ProviderName     string                 `json:"provider_name"`
	ModelName        string                 `json:"model_name"`
	InputTokens      int                    `json:"input_tokens"`
	OutputTokens     int                    `json:"output_tokens"`
	TotalTokens      int                    `json:"total_tokens"`
	EstimatedCostUSD *float64              `json:"estimated_cost_usd,omitempty"`
	CreatedAt        time.Time             `json:"created_at"`
	Payload          map[string]any        `json:"payload"`
}

func NewProviderUsageRecord(
	tenantID string,
	runID string,
	operation ProviderUsageOperation,
	providerName string,
	modelName string,
	usage LLMUsage,
	payload map[string]any,
) (ProviderUsageRecord, error) {
	usageID, err := NewID("usage")
	if err != nil {
		return ProviderUsageRecord{}, err
	}
	if payload == nil {
		payload = map[string]any{}
	}
	return ProviderUsageRecord{
		UsageID:          usageID,
		TenantID:         tenantID,
		RunID:            runID,
		Operation:        operation,
		ProviderName:     providerName,
		ModelName:        modelName,
		InputTokens:      usage.InputTokens,
		OutputTokens:     usage.OutputTokens,
		TotalTokens:      usage.TotalTokens,
		EstimatedCostUSD: usage.EstimatedCostUSD,
		CreatedAt:        time.Now().UTC(),
		Payload:          payload,
	}, nil
}
