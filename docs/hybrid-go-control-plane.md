# Hybrid Go Control Plane

## Purpose

The Go control plane is the production target for Agent Runway's public backend API. It owns durable workflow state, run state transitions, and database writes. The Python service remains the reference implementation during migration and the long-term private execution worker for LLM/provider-heavy work.

## Current Go-Owned Surface

The Go service in `apps/api-go` currently owns:

- `GET /health`
- `GET /ready`
- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/state`
- `POST /runs/{run_id}/plan`
- `GET /runs/{run_id}/plans/latest`
- `POST /runs/{run_id}/turns/advance` in deterministic and worker-backed LLM modes
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

The Python FastAPI app remains the reference for endpoints that are not listed above.

The Go service also owns opt-in API-boundary RBAC, durable token-to-principal identity, and tenant-scoped run ownership for the workflow endpoints. See `docs/go-auth-rbac.md` and `docs/identity-ownership.md`.

The Go service owns request correlation, structured HTTP logs, durable event correlation metadata, and optional OTLP/HTTP server span export for the workflow endpoints. See `docs/go-observability.md`.

## State Ownership

Go owns run state mutation for the endpoints it serves. Python must not mutate run state when called as a worker. This keeps state transitions auditable and prevents split-brain behavior between services.

Current Go state transitions:

- Run creation starts a run in `planning`.
- Plan generation registers deterministic template tasks and leaves the run in `planning`.
- Turn advancement starts the next ready task, executes deterministic logic or calls the Python worker for LLM execution, records tool calls and evidence, completes the task, and moves the run to `executing` or `verifying`.
- Approval requests create pending review gates, approval decisions move pending records to approved, rejected, or revision requested, and both paths append lifecycle events.
- Verification records a pass/fail report based on task completion, active-task state, and task presence.
- Finalization requires `verifying` status, a passing latest verification, and zero pending approvals before writing the final output and moving the run to `completed`.

## Persistence Model

Go writes to the existing Alembic-managed tables:

- `tenants`
- `users`
- `tenant_memberships`
- `run_states`
- `run_events`
- `run_plans`
- `run_turns`
- `run_tool_calls`
- `run_llm_calls`
- `run_approvals`
- `run_verifications`
- `run_outputs`
- `provider_usage_records`

The tables continue to store full JSON payloads in the same model shape used by Python. Go also maintains indexed columns such as `status`, `workflow_type`, `created_at`, `task_id`, `turn_id`, `request_id`, and `traceparent`.

Run ownership is stored both in indexed `run_states` columns and in the run-state JSON payload:

- `tenant_id`
- `owner_user_id`
- `created_by_user_id`

Plan generation is persisted transactionally:

1. enforce the caller's tenant ownership on the run
2. insert `run_plans`
3. update `run_states`
4. append `plan_generated`
5. append `tasks_registered`

Turn advancement is persisted transactionally:

1. enforce the caller's tenant ownership on the run
2. update `run_states`
3. insert `run_tool_calls`
4. insert `run_llm_calls` when `EXECUTION_BACKEND=llm`
5. insert `run_turns`
6. append `task_started`, `tool_executed`, `evidence_recorded`, `task_completed`, and `turn_executed`

Approval requests are persisted transactionally:

1. insert `run_approvals`
2. append `approval_requested`

Approval decisions are persisted transactionally:

1. update `run_approvals`
2. append `approval_decided`

Verification is persisted transactionally:

1. insert `run_verifications`
2. append `verification_completed`

Finalization is persisted transactionally:

1. insert `run_outputs`
2. update `run_states` to `completed` with `final_output_ref`
3. append `run_finalized`

Every Go-created event is stamped with the request metadata from the API boundary before insert:

- `request_id`
- `traceparent`

Provider usage is persisted when worker-backed planning or execution returns token/cost metadata. The ledger powers tenant monthly and per-run budget checks before future provider calls.

## Deterministic Execution

The first Go execution path intentionally matches the existing Python deterministic behavior:

- planner uses `goal_analyzer`
- researcher uses `evidence_lookup`
- writer uses `summary_writer`
- executor uses `execution_checker`
- unknown agents use `generic_tool`

Tool outputs are deterministic strings derived from the active task title. Evidence is stored inside the run state payload and references the persisted tool call.

## Python Worker Boundary

The private Python worker lives in `services/agent_worker` and exposes:

- `GET /health`
- `POST /internal/agent/plan`
- `POST /internal/agent/turn`

The worker returns structured planning or turn outcomes and does not write to the database.

Go selects worker-backed LLM execution when `EXECUTION_BACKEND=llm`. The Python worker returns a structured turn outcome. Go still owns the final run state update, event append, turn record, tool-call records, LLM-call record, and fallback persistence.

Go selects worker-backed LLM planning when `PLANNING_BACKEND=llm`. The Python worker returns a structured plan. Go still validates tasks, persists the plan, registers tasks, and appends planning events.

If the Python worker is unreachable or returns a transport-level error, Go falls back to deterministic turn execution and still persists an LLM-call record with `fallback_used=true` and the error message. This keeps the run advancing while preserving the failed LLM execution attempt for audit.

Go forwards `X-Request-ID` and `traceparent` to the worker. The worker echoes both headers and logs them with its request record. When OTLP export is enabled, Go also exports an HTTP server span for the public API request.

## Operational Notes

Use `make hybrid-up` for local multi-service wiring with Postgres, Alembic migrations, Python worker, and Go API.

Use `make api-go-dev` only after installing Go and running `go mod tidy` in `apps/api-go`.

No Go-native migration runner is introduced yet. Alembic remains the migration authority. The Go SQL files mirror the schema shape for operators who manage the Go deployment path directly.

## Next Implementation Order

1. Add worker-side spans for provider calls and execution turns.
2. Replace static token credentials with signed JWT validation.
3. Add operator-facing provider usage and budget reporting.
4. Port the remaining manual task/evidence mutation endpoints or intentionally deprecate them behind the Go workflow API.
