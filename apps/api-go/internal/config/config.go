package config

import (
	"encoding/json"
	"os"
	"strconv"
	"strings"
)

type AuthTokenPrincipal struct {
	Token       string `json:"token"`
	UserID      string `json:"user_id"`
	TenantID    string `json:"tenant_id"`
	Subject     string `json:"subject"`
	DisplayName string `json:"display_name"`
}

type ProviderRouteConfig struct {
	ProviderName    string   `json:"provider_name"`
	ModelName       string   `json:"model_name"`
	Temperature     *float64 `json:"temperature"`
	MaxOutputTokens *int     `json:"max_output_tokens"`
	TimeoutSeconds  *float64 `json:"timeout_seconds"`
	MaxRetries      *int     `json:"max_retries"`
	FallbackEnabled *bool    `json:"fallback_enabled"`
}

type TenantProviderPolicyConfig struct {
	TenantID          string              `json:"tenant_id"`
	Planning          ProviderRouteConfig `json:"planning"`
	Execution         ProviderRouteConfig `json:"execution"`
	MonthlyBudgetUSD *float64          `json:"monthly_budget_usd"`
	PerRunBudgetUSD  *float64          `json:"per_run_budget_usd"`
	BudgetMode       string             `json:"budget_mode"`
}

type Settings struct {
	Host                     string
	Port                     string
	DatabaseURL              string
	AgentWorkerURL           string
	AgentWorkerToken         string
	ExecutionBackend         string
	LLMProviderName          string
	LLMModelName             string
	LLMTemperature           *float64
	LLMMaxOutputTokens       *int
	LLMTimeoutSeconds        *float64
	LLMMaxRetries            int
	ExecutionFallbackEnabled bool
	PlanningBackend          string
	PlanningProviderName     string
	PlanningModelName        string
	PlanningTemperature      *float64
	PlanningMaxOutputTokens  *int
	PlanningTimeoutSeconds   *float64
	PlanningMaxRetries       int
	PlanningFallbackEnabled  bool
	AuthMode                 string
	AuthViewerTokens         []string
	AuthOperatorTokens       []string
	AuthAdminTokens          []string
	AuthDefaultTenantID      string
	AuthTokenPrincipals      []AuthTokenPrincipal
	OTLPTracesEndpoint       string
	OTLPHeaders              map[string]string
	OTLPTimeoutSeconds       float64
	OTLPQueueSize            int
	ServiceName              string
	ServiceEnvironment       string
	TenantProviderPolicies   []TenantProviderPolicyConfig
}

func Load() Settings {
	return Settings{
		Host:                     readEnv("HOST", "0.0.0.0"),
		Port:                     readEnv("PORT", "8080"),
		DatabaseURL:              os.Getenv("DATABASE_URL"),
		AgentWorkerURL:           readEnv("AGENT_WORKER_URL", "http://127.0.0.1:8090"),
		AgentWorkerToken:         os.Getenv("AGENT_WORKER_TOKEN"),
		ExecutionBackend:         strings.ToLower(readEnv("EXECUTION_BACKEND", "deterministic")),
		LLMProviderName:          readEnv("LLM_PROVIDER_NAME", "fake"),
		LLMModelName:             readEnv("LLM_MODEL_NAME", "fake-model"),
		LLMTemperature:           readOptionalFloat("LLM_TEMPERATURE"),
		LLMMaxOutputTokens:       readOptionalInt("LLM_MAX_OUTPUT_TOKENS"),
		LLMTimeoutSeconds:        readOptionalFloat("LLM_TIMEOUT_SECONDS"),
		LLMMaxRetries:            readInt("LLM_MAX_RETRIES", 0),
		ExecutionFallbackEnabled: readBool("EXECUTION_FALLBACK_ENABLED", true),
		PlanningBackend:          strings.ToLower(readEnv("PLANNING_BACKEND", "deterministic")),
		PlanningProviderName:     readEnv("PLANNING_PROVIDER_NAME", readEnv("LLM_PROVIDER_NAME", "fake")),
		PlanningModelName:        readEnv("PLANNING_MODEL_NAME", readEnv("LLM_MODEL_NAME", "fake-model")),
		PlanningTemperature:      readOptionalFloat("PLANNING_TEMPERATURE"),
		PlanningMaxOutputTokens:  readOptionalInt("PLANNING_MAX_OUTPUT_TOKENS"),
		PlanningTimeoutSeconds:   readOptionalFloat("PLANNING_TIMEOUT_SECONDS"),
		PlanningMaxRetries:       readInt("PLANNING_MAX_RETRIES", readInt("LLM_MAX_RETRIES", 0)),
		PlanningFallbackEnabled:  readBool("PLANNING_FALLBACK_ENABLED", true),
		AuthMode:                 strings.ToLower(readEnv("AUTH_MODE", "disabled")),
		AuthViewerTokens:         readCSV("AUTH_VIEWER_TOKENS"),
		AuthOperatorTokens:       readCSV("AUTH_OPERATOR_TOKENS"),
		AuthAdminTokens:          readCSV("AUTH_ADMIN_TOKENS"),
		AuthDefaultTenantID:      readEnv("AUTH_DEFAULT_TENANT_ID", "tenant_default"),
		AuthTokenPrincipals:      readAuthTokenPrincipals("AUTH_TOKEN_PRINCIPALS_JSON"),
		OTLPTracesEndpoint:       readOTLPTracesEndpoint(),
		OTLPHeaders:              readKeyValueCSV("OTEL_EXPORTER_OTLP_HEADERS"),
		OTLPTimeoutSeconds:       readFloat("OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS", 2),
		OTLPQueueSize:            readInt("OTEL_EXPORTER_OTLP_QUEUE_SIZE", 256),
		ServiceName:              readEnv("OTEL_SERVICE_NAME", "agent-runway-api-go"),
		ServiceEnvironment:       readEnv("OTEL_RESOURCE_ENVIRONMENT", readEnv("DEPLOY_ENVIRONMENT", "local")),
		TenantProviderPolicies:   readTenantProviderPolicies("TENANT_PROVIDER_POLICIES_JSON"),
	}
}

func (settings Settings) HTTPAddress() string {
	return settings.Host + ":" + settings.Port
}

func (settings Settings) AuthEnabled() bool {
	return settings.AuthMode != "" && settings.AuthMode != "disabled"
}

func (settings Settings) HasAuthTokens() bool {
	return len(settings.AuthViewerTokens) > 0 ||
		len(settings.AuthOperatorTokens) > 0 ||
		len(settings.AuthAdminTokens) > 0
}

func readEnv(name string, fallback string) string {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	return value
}

func readInt(name string, fallback int) int {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func readBool(name string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(name)))
	if value == "" {
		return fallback
	}
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}

func readOptionalInt(name string) *int {
	value := os.Getenv(name)
	if value == "" {
		return nil
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return nil
	}
	return &parsed
}

func readCSV(name string) []string {
	value := os.Getenv(name)
	if value == "" {
		return []string{}
	}
	parts := strings.Split(value, ",")
	items := make([]string, 0, len(parts))
	for _, part := range parts {
		item := strings.TrimSpace(part)
		if item != "" {
			items = append(items, item)
		}
	}
	return items
}

func readOptionalFloat(name string) *float64 {
	value := os.Getenv(name)
	if value == "" {
		return nil
	}
	parsed, err := strconv.ParseFloat(value, 64)
	if err != nil {
		return nil
	}
	return &parsed
}

func readFloat(name string, fallback float64) float64 {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.ParseFloat(value, 64)
	if err != nil {
		return fallback
	}
	return parsed
}

func readKeyValueCSV(name string) map[string]string {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return map[string]string{}
	}
	items := map[string]string{}
	for _, part := range strings.Split(value, ",") {
		key, itemValue, ok := strings.Cut(part, "=")
		if !ok {
			continue
		}
		key = strings.TrimSpace(key)
		itemValue = strings.TrimSpace(itemValue)
		if key != "" && itemValue != "" {
			items[key] = itemValue
		}
	}
	return items
}

func readOTLPTracesEndpoint() string {
	if value := strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")); value != "" {
		return value
	}
	endpoint := strings.TrimRight(strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")), "/")
	if endpoint == "" {
		return ""
	}
	return endpoint + "/v1/traces"
}

func readAuthTokenPrincipals(name string) []AuthTokenPrincipal {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return []AuthTokenPrincipal{}
	}
	var principals []AuthTokenPrincipal
	if err := json.Unmarshal([]byte(value), &principals); err != nil {
		return []AuthTokenPrincipal{}
	}
	normalized := make([]AuthTokenPrincipal, 0, len(principals))
	for _, principal := range principals {
		principal.Token = strings.TrimSpace(principal.Token)
		principal.UserID = strings.TrimSpace(principal.UserID)
		principal.TenantID = strings.TrimSpace(principal.TenantID)
		principal.Subject = strings.TrimSpace(principal.Subject)
		principal.DisplayName = strings.TrimSpace(principal.DisplayName)
		if principal.Token != "" && principal.UserID != "" && principal.TenantID != "" {
			normalized = append(normalized, principal)
		}
	}
	return normalized
}

func readTenantProviderPolicies(name string) []TenantProviderPolicyConfig {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return []TenantProviderPolicyConfig{}
	}
	var policies []TenantProviderPolicyConfig
	if err := json.Unmarshal([]byte(value), &policies); err != nil {
		return []TenantProviderPolicyConfig{}
	}
	normalized := make([]TenantProviderPolicyConfig, 0, len(policies))
	for _, policy := range policies {
		policy.TenantID = strings.TrimSpace(policy.TenantID)
		policy.Planning = normalizeProviderRoute(policy.Planning)
		policy.Execution = normalizeProviderRoute(policy.Execution)
		policy.BudgetMode = strings.ToLower(strings.TrimSpace(policy.BudgetMode))
		if policy.TenantID != "" {
			normalized = append(normalized, policy)
		}
	}
	return normalized
}

func normalizeProviderRoute(route ProviderRouteConfig) ProviderRouteConfig {
	route.ProviderName = strings.TrimSpace(route.ProviderName)
	route.ModelName = strings.TrimSpace(route.ModelName)
	return route
}
