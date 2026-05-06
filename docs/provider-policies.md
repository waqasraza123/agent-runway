# Provider Policies

## Purpose

Agent Runway now separates workflow state ownership from provider execution policy.

The Go control plane owns public API requests, database writes, run transitions, planning persistence, and finalization gates. The Python worker owns provider-specific calls for LLM-backed planning and LLM-backed turn execution.

## Execution Policy

Turn execution is selected with:

```bash
EXECUTION_BACKEND=deterministic
EXECUTION_BACKEND=llm
```

LLM turn execution uses:

```bash
LLM_PROVIDER_NAME=fake
LLM_PROVIDER_NAME=openai
LLM_MODEL_NAME=fake-model
LLM_TEMPERATURE=
LLM_MAX_OUTPUT_TOKENS=
LLM_TIMEOUT_SECONDS=
LLM_MAX_RETRIES=0
EXECUTION_FALLBACK_ENABLED=true
```

When `EXECUTION_BACKEND=llm`, Go calls:

```text
POST /internal/agent/turn
```

If the worker transport fails or the worker returns fallback output:

- `EXECUTION_FALLBACK_ENABLED=true` lets the run advance with deterministic output and audit metadata.
- `EXECUTION_FALLBACK_ENABLED=false` fails the API request before mutating run state.

## Planning Policy

Planning is selected independently:

```bash
PLANNING_BACKEND=deterministic
PLANNING_BACKEND=llm
```

LLM planning uses:

```bash
PLANNING_PROVIDER_NAME=fake
PLANNING_PROVIDER_NAME=openai
PLANNING_MODEL_NAME=fake-model
PLANNING_TEMPERATURE=
PLANNING_MAX_OUTPUT_TOKENS=
PLANNING_TIMEOUT_SECONDS=
PLANNING_MAX_RETRIES=0
PLANNING_FALLBACK_ENABLED=true
```

When `PLANNING_BACKEND=llm`, Go calls:

```text
POST /internal/agent/plan
```

If the worker transport fails or the worker returns fallback output:

- `PLANNING_FALLBACK_ENABLED=true` stores the deterministic template plan.
- `PLANNING_FALLBACK_ENABLED=false` fails planning before tasks are registered.

## Provider Support

Current worker providers:

- `fake`: deterministic provider-shaped output for repeatable local runs.
- `openai`: OpenAI-compatible chat completions endpoint.

OpenAI-compatible environment:

```bash
LLM_API_KEY=<secret>
LLM_API_BASE_URL=https://api.openai.com/v1
```

`PLANNING_*` values override planning behavior only. If a planning-specific provider or model is not supplied, the deployment can reuse the `LLM_*` values.

## State Safety

Go validates and registers every worker-generated plan before persistence:

- at least one task is required
- duplicate task IDs are rejected
- dependencies must reference known tasks
- tasks become `ready` only when dependencies are complete

The worker also validates provider-generated plan dependencies before returning a plan. This keeps malformed provider output from becoming durable workflow state.

## Production Defaults

Recommended production posture:

```bash
EXECUTION_BACKEND=llm
EXECUTION_FALLBACK_ENABLED=true
PLANNING_BACKEND=llm
PLANNING_FALLBACK_ENABLED=true
LLM_PROVIDER_NAME=openai
PLANNING_PROVIDER_NAME=openai
```

Use strict mode for environments where provider output is mandatory:

```bash
EXECUTION_FALLBACK_ENABLED=false
PLANNING_FALLBACK_ENABLED=false
```

## Tenant-Specific Routing

Use `TENANT_PROVIDER_POLICIES_JSON` to override provider, model, retry, timeout, temperature, fallback, and budget behavior for a specific tenant. Tokens still resolve to tenants through `AUTH_TOKEN_PRINCIPALS_JSON`; provider policy is evaluated from the run's durable `tenant_id`.

Example:

```bash
TENANT_PROVIDER_POLICIES_JSON='[
  {
    "tenant_id": "tenant_acme",
    "planning": {
      "provider_name": "openai",
      "model_name": "gpt-4.1-mini",
      "max_output_tokens": 1800,
      "max_retries": 1,
      "fallback_enabled": true
    },
    "execution": {
      "provider_name": "openai",
      "model_name": "gpt-4.1",
      "temperature": 0.2,
      "timeout_seconds": 30,
      "max_retries": 1,
      "fallback_enabled": true
    },
    "monthly_budget_usd": 250.0,
    "per_run_budget_usd": 10.0,
    "budget_mode": "block"
  }
]'
```

Any omitted route field falls back to the global `PLANNING_*` or `LLM_*` setting.

## Budget Controls

The Go API stores provider usage in `provider_usage_records` whenever the worker returns provider usage for planning or turn execution. Each record includes:

- `tenant_id`
- `run_id`
- `operation`
- `provider_name`
- `model_name`
- token counts
- `estimated_cost_usd`
- full JSON payload

Before an LLM planning or execution call, Go sums the tenant's durable usage ledger:

- `monthly_budget_usd` checks tenant spend since the first day of the current UTC month.
- `per_run_budget_usd` checks total spend for the current run.

Budget modes:

- `block`: return HTTP `402` before calling the worker when spend is already at or above the configured limit.
- `warn`: log `provider_budget_limit_reached` and allow the call.

Budget enforcement is intentionally based on already-recorded usage. A single call can exceed the remaining budget if the provider cost is only known after completion; the next provider call is blocked once the ledger is over the limit.
