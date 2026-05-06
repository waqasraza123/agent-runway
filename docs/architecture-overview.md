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
- The current Python FastAPI app remains the reference implementation while the Go API reaches parity.

### API layer
FastAPI routes expose the workflow and translate application errors into HTTP responses.

### Application layer
The service layer coordinates repositories, state transitions, planning, turn execution, tools, verification, approvals, final outputs, and LLM call persistence.

### Contracts layer
Contracts define stable request, response, and domain models used across the platform.

### Orchestration layer
State transition functions own run-state mutation rules for tasks and evidence.

### Planning layer
Planning generates deterministic task sequences from the run goal and workflow type.

### Agent execution layer
Execution supports two backends:
- deterministic execution
- provider-backed LLM execution

The LLM path supports retry and deterministic fallback when provider execution fails.

### Tools layer
The registry executes deterministic tool adapters and returns structured outputs.

### Storage layer
Repositories persist run state, events, approvals, plans, turns, tool calls, verifications, outputs, and LLM call artifacts.

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
