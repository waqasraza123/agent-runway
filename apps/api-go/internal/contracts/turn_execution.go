package contracts

type ExecutionBackend string

const (
	ExecutionBackendDeterministic ExecutionBackend = "deterministic"
	ExecutionBackendLLM           ExecutionBackend = "llm"
)

type TaskRecord struct {
	TaskID             string   `json:"task_id"`
	Title              string   `json:"title"`
	Description        string   `json:"description"`
	AssignedAgent      string   `json:"assigned_agent"`
	Status             string   `json:"status"`
	DependencyIDs      []string `json:"dependency_ids"`
	AcceptanceCriteria []string `json:"acceptance_criteria"`
	RiskLevel          string   `json:"risk_level"`
	AttemptCount       int      `json:"attempt_count"`
}

type AgentExecutionProfile struct {
	AgentName       string           `json:"agent_name"`
	Backend         ExecutionBackend `json:"backend"`
	LLMProviderName *string          `json:"llm_provider_name,omitempty"`
	ModelName       *string          `json:"model_name,omitempty"`
	Temperature     *float64         `json:"temperature,omitempty"`
	MaxOutputTokens *int             `json:"max_output_tokens,omitempty"`
	TimeoutSeconds  *float64         `json:"timeout_seconds,omitempty"`
	MaxRetries      int              `json:"max_retries"`
}

type LLMUsage struct {
	InputTokens      int      `json:"input_tokens"`
	OutputTokens     int      `json:"output_tokens"`
	TotalTokens      int      `json:"total_tokens"`
	EstimatedCostUSD *float64 `json:"estimated_cost_usd,omitempty"`
}

type PlannedToolCall struct {
	ToolName  string            `json:"tool_name"`
	ToolInput map[string]string `json:"tool_input"`
}

type StructuredTurnOutput struct {
	Summary          string            `json:"summary"`
	PlannedToolCalls []PlannedToolCall `json:"planned_tool_calls"`
}

type LLMWorkerTurnRequest struct {
	RunID              string                `json:"run_id"`
	UserGoal           string                `json:"user_goal"`
	Task               TaskRecord            `json:"task"`
	ExecutionProfile   AgentExecutionProfile `json:"execution_profile"`
	AvailableToolNames []string              `json:"available_tool_names"`
}

type LLMTurnResponse struct {
	ProviderName    string               `json:"provider_name"`
	ModelName       string               `json:"model_name"`
	Output          StructuredTurnOutput `json:"output"`
	Usage           LLMUsage             `json:"usage"`
	FinishReason    *string              `json:"finish_reason,omitempty"`
	LatencyMS       *int                 `json:"latency_ms,omitempty"`
	RawResponseText *string              `json:"raw_response_text,omitempty"`
}

type LLMExecutionOutcome struct {
	Output        StructuredTurnOutput `json:"output"`
	LLMResponse   *LLMTurnResponse     `json:"llm_response,omitempty"`
	ErrorMessage  *string              `json:"error_message,omitempty"`
	FallbackUsed  bool                 `json:"fallback_used"`
	AttemptCount  int                  `json:"attempt_count"`
}
