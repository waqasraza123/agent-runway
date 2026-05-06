# Agent Runway Go Control Plane

This is the first hybrid control-plane slice for Agent Runway.

Current responsibilities:

- expose Go service health/readiness endpoints
- enforce opt-in bearer-token RBAC for workflow endpoints
- persist durable users, tenants, memberships, and run ownership
- emit structured request logs with request IDs and trace context
- export OTLP/HTTP server spans when configured
- own initial run creation and run reads
- own deterministic plan generation
- own deterministic and worker-backed LLM turn advancement
- own verification and finalization
- own approval request, listing, and decision flow
- persist turns, tool calls, LLM calls, evidence, and events
- persist approvals, verification reports, and final outputs
- expose persisted events, turns, tool calls, LLM calls, approvals, verifications, and outputs
- connect to PostgreSQL through `pgx`
- write run creation events
- call the private Python agent worker over HTTP
- hold Go structs for the worker-boundary contract
- provide sqlc query scaffolding for the existing run-state table

Run locally after installing Go:

```bash
go mod tidy
go run ./cmd/api
```

Environment:

```bash
HOST=0.0.0.0
PORT=8080
DATABASE_URL=postgres://user:password@localhost:5432/agent_runway?sslmode=disable
AGENT_WORKER_URL=http://127.0.0.1:8090
AGENT_WORKER_TOKEN=
EXECUTION_BACKEND=deterministic
LLM_PROVIDER_NAME=fake
LLM_MODEL_NAME=fake-model
LLM_MAX_RETRIES=0
LLM_TIMEOUT_SECONDS=
LLM_TEMPERATURE=
LLM_MAX_OUTPUT_TOKENS=
EXECUTION_FALLBACK_ENABLED=true
PLANNING_BACKEND=deterministic
PLANNING_PROVIDER_NAME=fake
PLANNING_MODEL_NAME=fake-model
PLANNING_MAX_RETRIES=0
PLANNING_TIMEOUT_SECONDS=
PLANNING_TEMPERATURE=
PLANNING_MAX_OUTPUT_TOKENS=
PLANNING_FALLBACK_ENABLED=true
TENANT_PROVIDER_POLICIES_JSON=
AUTH_MODE=disabled
AUTH_VIEWER_TOKENS=
AUTH_OPERATOR_TOKENS=
AUTH_ADMIN_TOKENS=
AUTH_DEFAULT_TENANT_ID=tenant_default
AUTH_TOKEN_PRINCIPALS_JSON=
OTEL_SERVICE_NAME=agent-runway-api-go
OTEL_RESOURCE_ENVIRONMENT=local
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=
OTEL_EXPORTER_OTLP_HEADERS=
OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS=2
OTEL_EXPORTER_OTLP_QUEUE_SIZE=256
```

Set `EXECUTION_BACKEND=llm` to call the private Python worker during `POST /runs/{run_id}/turns/advance`. Go still owns the final run state transition and database writes.

If the Python worker is unavailable, the Go control plane falls back to deterministic execution and persists an LLM-call record with the failure details.

Set `PLANNING_BACKEND=llm` to call the private Python worker during `POST /runs/{run_id}/plan`. Go still validates worker-generated tasks, persists the plan, updates run state, and writes lifecycle events. `PLANNING_FALLBACK_ENABLED=true` stores the deterministic template plan when provider planning fails. Set it to `false` to fail planning before tasks are registered.

Set `TENANT_PROVIDER_POLICIES_JSON` to override planning/execution provider routes and budgets by durable `tenant_id`. Go records provider usage in `provider_usage_records`, checks monthly and per-run budgets before worker calls, and returns HTTP `402` when a blocking budget is already exhausted.

Auth is disabled by default for local development. Set `AUTH_MODE=bearer` or `AUTH_MODE=api_key` to protect all workflow endpoints. `GET /health` and `GET /ready` stay public for platform probes. Tokens are comma-separated by role:

```bash
AUTH_MODE=bearer
AUTH_VIEWER_TOKENS=view-token-1,view-token-2
AUTH_OPERATOR_TOKENS=operator-token
AUTH_ADMIN_TOKENS=admin-token
```

Clients send either:

```text
Authorization: Bearer <token>
X-API-Key: <token>
```

Role inheritance is `admin > operator > viewer`. Viewers can read runs and artifacts. Operators can mutate workflow state. Admins currently inherit every operator and viewer permission.

When auth is enabled, each token resolves to a durable tenant/user principal. The Go API upserts the identity rows, stamps new runs with `tenant_id`, `owner_user_id`, and `created_by_user_id`, filters `GET /runs` to the caller's tenant, and returns `404` for cross-tenant run IDs. Configure `AUTH_TOKEN_PRINCIPALS_JSON` to map deployed tokens to stable tenant/user IDs.

The API accepts or generates request correlation headers and echoes them on every response:

```text
X-Request-ID: req_<32-hex-chars>
traceparent: 00-<32-hex-trace-id>-<16-hex-span-id>-01
```

Every request emits a structured `http_request` log with request ID, traceparent, method, path, status, bytes, duration, remote address, and user agent. Calls to the Python worker forward the same headers. Go-created run events persist `request_id` and `traceparent` so lifecycle rows can be joined back to API logs and traces.

Set `OTEL_EXPORTER_OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` to export server spans to an OpenTelemetry collector over OTLP/HTTP JSON. Export is asynchronous and drops spans instead of blocking request handling when the queue is full.

The current endpoints are:

- `GET /health`
- `GET /ready`
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

Finalization requires a run in `verifying`, a latest verification verdict of `pass`, and zero pending approvals. The next implementation step is signed JWT validation and worker-side spans for provider calls.
