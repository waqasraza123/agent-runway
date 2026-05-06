# Architecture overview

## Purpose

The platform is a backend-first multi-agent execution system that turns a user goal into a persisted run, generates a plan, advances execution turns, executes tools, records evidence, verifies completion, and produces a final output.

## Layering

## Hybrid target architecture

The next backend architecture is a hybrid Go and Python deployment.

- Go is the control plane for the public API, persistence, orchestration, and run state transitions.
- Python is the private agent worker for LLM/provider execution.
- Go calls Python through `POST /internal/agent/turn`.
- Python returns structured execution outcomes and does not mutate run state directly.
- The Go control plane owns initial run creation, run reads, deterministic planning, worker-backed LLM planning, deterministic turn advancement, worker-backed LLM turn advancement, approvals, verification, and finalization.
- The Go control plane exposes persisted workflow artifact reads for events, turns, tool calls, LLM calls, approvals, verifications, and final outputs.
- The Go control plane enforces opt-in bearer-token RBAC, durable user/tenant identity, and tenant-scoped run ownership for workflow endpoints.
- The Go control plane resolves tenant-specific provider routes and checks provider budgets before worker-backed LLM calls.
- The Go control plane emits structured request logs, persists request IDs plus W3C trace context on run events, propagates both values to the Python worker, and exports OTLP/HTTP spans when configured.
- The current Python FastAPI app remains the reference implementation for endpoints that have not yet been ported.

See `docs/hybrid-go-control-plane.md` for the current Go ownership boundary and migration order.

### API layer
FastAPI routes expose the workflow and translate application errors into HTTP responses.

### Application layer
The service layer coordinates repositories, state transitions, planning, turn execution, tools, verification, approvals, final outputs, and LLM call persistence.

### Contracts layer
Contracts define stable request, response, and domain models used across the platform.

### Orchestration layer
State transition functions own run-state mutation rules for tasks and evidence.

### Planning layer
Planning generates deterministic task sequences from the run goal and workflow type, or delegates provider-backed planning to the private Python worker while keeping task registration and persistence in Go.

### Agent execution layer
Execution supports two backends:
- deterministic execution
- provider-backed LLM execution

The LLM path supports retry and deterministic fallback when provider execution fails.

### Tools layer
The registry executes deterministic tool adapters and returns structured outputs.

### Storage layer
Repositories persist tenants, users, memberships, run ownership, run state, events, approvals, plans, turns, tool calls, verifications, outputs, LLM call artifacts, and provider usage records.

The platform supports both in-memory and SQL-backed implementations behind the same service boundary.

### Config layer
Settings select the storage backend, execution backend, provider, model, and database URL.

## Current execution flow

1. create run
2. generate plan
3. register tasks
4. advance turn through deterministic or LLM execution
5. persist LLM call record when the LLM backend is active
6. execute deterministic tool calls and record evidence
7. verify run
8. finalize output
9. persist terminal completed state

## Current storage modes

- memory
- sql

SQL mode targets SQLite locally and preserves a Postgres-ready repository boundary through SQLAlchemy models and sessions.

## Current provider modes

- fake provider for smoke and test execution
- OpenAI-compatible provider for real provider-backed execution
