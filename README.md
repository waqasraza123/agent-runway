# Agent Runway

Agent Runway is a backend-first execution platform for auditable AI workflows. It turns a business goal into a tracked run, creates a plan, advances execution through deterministic or provider-backed agent turns, records tool calls and evidence, verifies completion, and produces a final output.

It is designed for teams that need AI workflow automation with traceability instead of one-off chat responses.

## What It Does

- Creates and tracks workflow runs from a user goal.
- Generates deterministic task plans for repeatable execution.
- Advances work through deterministic or LLM-backed turns.
- Executes registered tools and records structured tool-call artifacts.
- Stores events, turns, approvals, verifications, outputs, and LLM call records.
- Supports human approval checkpoints.
- Produces verification reports before final output synthesis.
- Exposes the workflow through a FastAPI API and a lightweight browser console.

## Product Use Cases

Agent Runway is useful for workflow automation that needs a durable audit trail:

- technical planning and delivery breakdowns
- vendor or proposal analysis
- research workflows with evidence capture
- operational checklists with approval gates
- AI-assisted decision support where each step must be inspectable

## Execution Flow

1. Create a run from a business goal.
2. Generate the run plan.
3. Advance turns until planned tasks are completed.
4. Record tool calls, evidence, events, and LLM call artifacts.
5. Request and resolve approvals when needed.
6. Verify the run.
7. Finalize the output.

## API Highlights

Key workflow endpoints:

- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/state`
- `POST /runs/{run_id}/plan`
- `POST /runs/{run_id}/turns/advance`
- `GET /runs/{run_id}/turns`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/tool-calls`
- `GET /runs/{run_id}/llm-calls`
- `GET /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals/{approval_id}/decide`
- `POST /runs/{run_id}/verify`
- `POST /runs/{run_id}/finalize`
- `GET /runs/{run_id}/outputs/latest`

FastAPI also exposes interactive API docs at `/docs` when the service is running.

## Run Locally

Install dependencies:

```bash
uv sync --group dev
```

Run the API and browser console:

```bash
uv run uvicorn multi_agent_platform.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Run the quality gate:

```bash
make check
```

Run the release smoke checks:

```bash
make release-check
```

## Hybrid Go And Python Backend

Agent Runway is moving toward a hybrid backend:

- Go control plane in `apps/api-go`
- Python agent worker in `services/agent_worker`
- shared contracts in `packages/contracts`
- local hybrid runtime in `infra/docker`

In this model, Go owns the public API, database access, orchestration, and run state transitions. Python owns LLM/provider execution and returns structured turn outcomes over a private internal HTTP API.

The Go control plane currently owns:

- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/state`
- `POST /runs/{run_id}/plan`
- `GET /runs/{run_id}/plans/latest`
- `POST /runs/{run_id}/turns/advance`
- `POST /runs/{run_id}/verify`
- `GET /runs/{run_id}/verifications/latest`
- `POST /runs/{run_id}/finalize`
- `GET /runs/{run_id}/outputs/latest`
- `GET /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals/{approval_id}/decide`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/turns`
- `GET /runs/{run_id}/tool-calls`
- `GET /runs/{run_id}/llm-calls`
- `GET /health`
- `GET /ready`

The remaining workflow endpoints continue to use the Python FastAPI app as the reference implementation until they are ported. In `PLANNING_BACKEND=llm` mode, Go calls the private Python worker for plan generation, validates the returned tasks, and persists the plan itself. In `EXECUTION_BACKEND=llm` mode, Go calls the private Python worker for turn execution and then persists the resulting state, turn, tool-call, evidence, event, and LLM-call records itself. Go also owns approval checkpoints, verifies completed runs, enforces the finalization gate, writes final outputs, and records lifecycle events. If the worker is unavailable, Go can fall back to deterministic planning or execution according to the configured fallback policy.

The Go control plane supports opt-in RBAC with bearer or `X-API-Key` tokens. `GET /health` and `GET /ready` remain public for platform probes; workflow endpoints require viewer, operator, or admin access when `AUTH_MODE` is enabled. Authenticated tokens resolve to durable user and tenant records, and Go enforces tenant ownership on run lists, reads, and mutations.

The Go control plane also emits structured request logs, persists `X-Request-ID` plus `traceparent` on run events, propagates both headers to the Python worker, and can export OTLP/HTTP server spans to an OpenTelemetry collector.

Run the Python worker locally:

```bash
make agent-worker-dev
```

Run the Go control plane locally:

```bash
make api-go-dev
```

Use deterministic turn execution by default:

```bash
EXECUTION_BACKEND=deterministic
```

Use worker-backed LLM execution:

```bash
EXECUTION_BACKEND=llm
LLM_PROVIDER_NAME=fake
LLM_MODEL_NAME=fake-model
AGENT_WORKER_URL=http://127.0.0.1:8090
```

Run both services with Postgres:

```bash
make hybrid-up
```

Export the current FastAPI OpenAPI contract:

```bash
make export-openapi
```

The Go toolchain is required for `make api-go-dev`. After installing Go, run this once from `apps/api-go` to resolve module checksums:

```bash
go mod tidy
```

## Configuration

Storage backends:

```bash
STORAGE_BACKEND=memory
STORAGE_BACKEND=sql
```

Default SQL database:

```bash
DATABASE_URL=sqlite:///./.workdir/multi_agent_platform.db
```

Run migrations before using SQL storage:

```bash
make migrate
```

For PostgreSQL, install the same app with a PostgreSQL URL:

```bash
STORAGE_BACKEND=sql
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
make migrate
```

Execution backends:

```bash
EXECUTION_BACKEND=deterministic
EXECUTION_BACKEND=llm
EXECUTION_FALLBACK_ENABLED=true
```

LLM provider settings:

```bash
LLM_PROVIDER_NAME=fake
LLM_PROVIDER_NAME=openai
LLM_MODEL_NAME=fake-model
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=...
```

`LLM_API_KEY` is required when `LLM_PROVIDER_NAME=openai`.

Planning backends:

```bash
PLANNING_BACKEND=deterministic
PLANNING_BACKEND=llm
PLANNING_PROVIDER_NAME=fake
PLANNING_PROVIDER_NAME=openai
PLANNING_MODEL_NAME=fake-model
PLANNING_MAX_RETRIES=0
PLANNING_FALLBACK_ENABLED=true
TENANT_PROVIDER_POLICIES_JSON='[{"tenant_id":"tenant_acme","execution":{"provider_name":"openai","model_name":"gpt-4.1"},"monthly_budget_usd":250,"per_run_budget_usd":10,"budget_mode":"block"}]'
```

`TENANT_PROVIDER_POLICIES_JSON` is optional. When set, it overrides planning/execution provider routes by durable `tenant_id` and enables monthly or per-run budget checks from the provider usage ledger.

Go API auth:

```bash
AUTH_MODE=disabled
AUTH_MODE=bearer
AUTH_MODE=api_key
AUTH_VIEWER_TOKENS=<comma-separated-read-tokens>
AUTH_OPERATOR_TOKENS=<comma-separated-write-tokens>
AUTH_ADMIN_TOKENS=<comma-separated-admin-tokens>
AUTH_DEFAULT_TENANT_ID=tenant_default
AUTH_TOKEN_PRINCIPALS_JSON='[{"token":"operator-token","tenant_id":"tenant_acme","user_id":"user_alice","subject":"user:alice@example.com"}]'
```

Use `AUTH_MODE=bearer` or `AUTH_MODE=api_key` outside local development. Clients can authenticate with `Authorization: Bearer <token>` or `X-API-Key: <token>`.

`AUTH_TOKEN_PRINCIPALS_JSON` is optional but recommended in deployed environments so each token maps to a stable tenant/user identity. The token must still be present in one of the role token lists.

Go API observability:

```bash
OTEL_SERVICE_NAME=agent-runway-api-go
OTEL_RESOURCE_ENVIRONMENT=production
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_HEADERS=
OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS=2
OTEL_EXPORTER_OTLP_QUEUE_SIZE=256
```

Set `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` instead of `OTEL_EXPORTER_OTLP_ENDPOINT` when your collector exposes a custom traces path.

## Deploy On Render

Use Render as a Python web service.

1. Push this repository to GitHub, GitLab, or Bitbucket.
2. In Render, create a new **Web Service** from the repository.
3. Set the runtime to **Python 3**.
4. Set the build command:

```bash
uv sync --frozen --no-dev
```

5. Set the start command:

```bash
uv run uvicorn multi_agent_platform.main:app --host 0.0.0.0 --port $PORT
```

6. Add environment variables:

```bash
PYTHON_VERSION=3.12.11
STORAGE_BACKEND=memory
EXECUTION_BACKEND=deterministic
LLM_PROVIDER_NAME=fake
LLM_MODEL_NAME=fake-model
```

7. Deploy the service.
8. After deploy, open the Render URL. The browser console loads at `/`, and the API docs load at `/docs`.

For an LLM-backed demo, change the execution variables:

```bash
EXECUTION_BACKEND=llm
LLM_PROVIDER_NAME=openai
LLM_MODEL_NAME=<your-model-name>
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=<your-api-key>
```

Storage note: use `STORAGE_BACKEND=memory` for the fastest Render demo. Use PostgreSQL for durable Render data.

For durable Render data, create a Render PostgreSQL database and set:

```bash
STORAGE_BACKEND=sql
DATABASE_URL=<your-render-postgres-url>
```

Then run migrations as a Render pre-deploy command or one-off shell command:

```bash
uv run alembic upgrade head
```

Do not use the default SQLite URL for production Render data.

## Smoke Flows

Run the built-in smoke flows locally:

```bash
make smoke-memory
make smoke-sql
make smoke-llm-fake
```

## Repository Structure

- `apps/api-go` contains the Go control-plane service.
- `services/agent_worker` contains the private Python LLM/agent worker.
- `packages/contracts` contains shared API and worker-boundary contracts.
- `infra/docker` contains local hybrid runtime wiring.
- `src/multi_agent_platform/api` exposes the FastAPI app and routes.
- `src/multi_agent_platform/application` coordinates workflow services.
- `src/multi_agent_platform/contracts` defines request, response, and domain models.
- `src/multi_agent_platform/orchestration` owns run state transitions.
- `src/multi_agent_platform/planning` generates deterministic plans.
- `src/multi_agent_platform/agents` contains deterministic and provider-backed execution.
- `src/multi_agent_platform/tools` contains deterministic tool execution.
- `src/multi_agent_platform/storage` contains memory and SQL repositories.
- `src/multi_agent_platform/web` contains the lightweight browser console.
- `tests/unit` and `tests/integration` cover the implemented platform spine.

## Current Production Notes

Agent Runway is backend-MVP ready for demos, architecture walkthroughs, portfolio presentation, and further hardening.

The next production upgrades are signed JWT validation, worker-side spans, and a fuller operator console.

## License

MIT
