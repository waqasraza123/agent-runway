# Release summary

## Version

v0.1.0

## Project overview

Agent Runway is a backend-first AI workflow automation system. It turns a business goal into a persisted run, generates a deterministic plan, advances tasks through deterministic or provider-backed turns, executes deterministic tools, records evidence, supports approval workflows, verifies completion, and produces a final output.

## Implemented scope

- run creation and listing
- deterministic plan generation
- task registration and lifecycle
- deterministic and provider-backed turn advancement
- deterministic fallback when LLM execution fails
- deterministic tool execution
- evidence capture and persistence
- approval request and decision flow
- verification reports
- final output synthesis
- persisted LLM call artifacts and usage records
- in-memory storage backend
- SQL-backed durable storage backend
- Alembic schema migrations
- PostgreSQL-ready database URL support
- hybrid Go control-plane scaffold
- Go-owned run create/list/read endpoints
- Go-owned deterministic and worker-backed LLM planning
- Go-owned deterministic turn advancement
- Go-owned worker-backed LLM turn advancement
- Go-owned artifact list endpoints for events, turns, tool calls, and LLM calls
- Go-owned verification and finalization endpoints
- Go-owned final output persistence
- Go-owned approval request, listing, and decision endpoints
- Go-owned opt-in auth/RBAC for workflow endpoints
- Go-owned durable user, tenant, membership, and run ownership records
- Go-owned tenant-scoped run list, read, and mutation checks
- Go-owned structured request logs and Python worker trace propagation
- Go-owned durable request metadata on run events
- Go-owned OTLP/HTTP server span export
- Go-owned tenant-specific provider routing and model policy
- Go-owned provider usage ledger and budget guards
- private Python agent-worker scaffold
- shared worker-boundary contracts
- FastAPI endpoints for the current execution workflow
- unit and integration coverage for the implemented spine

## Storage modes

### Memory mode

Fast local iteration with in-process state.

Environment:
- `STORAGE_BACKEND=memory`

### SQL mode

Durable persistence using SQLAlchemy and Alembic migrations.

Environment:
- `STORAGE_BACKEND=sql`
- `DATABASE_URL=sqlite:///./.workdir/multi_agent_platform.db`

Migration command:
- `make migrate`

## Execution modes

### Deterministic mode

Environment:
- `EXECUTION_BACKEND=deterministic`

### LLM mode

Environment:
- `EXECUTION_BACKEND=llm`
- `LLM_PROVIDER_NAME=fake|openai`
- `LLM_MODEL_NAME=...`

Optional provider settings:
- `LLM_API_BASE_URL=https://api.openai.com/v1`
- `LLM_API_KEY=...`

## Main API flow

1. `POST /runs`
2. `POST /runs/{run_id}/plan`
3. `POST /runs/{run_id}/turns/advance`
4. repeat turn advancement until verifying
5. `POST /runs/{run_id}/verify`
6. `POST /runs/{run_id}/finalize`
7. `GET /runs/{run_id}/state`
8. `GET /runs/{run_id}/outputs/latest`

## Supporting API areas

- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/turns`
- `GET /runs/{run_id}/tool-calls`
- `GET /runs/{run_id}/llm-calls`
- `GET /runs/{run_id}/plans/latest`
- `GET /runs/{run_id}/verifications/latest`
- `GET /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals`
- `POST /runs/{run_id}/approvals/{approval_id}/decide`
- `POST /runs/{run_id}/tasks`
- `POST /runs/{run_id}/tasks/{task_id}/start`
- `POST /runs/{run_id}/tasks/{task_id}/complete`
- `POST /runs/{run_id}/evidence`

## Standard local commands

Bootstrap:
    uv sync --group dev

Quality gate:
    make check

Full release-ready validation:
    make release-check

Run API locally:
    uv run uvicorn multi_agent_platform.main:app --reload

Run hybrid services:
    make hybrid-up

## Smoke commands

Memory mode:
    make smoke-memory

SQL mode:
    make smoke-sql

Fake LLM mode:
    make smoke-llm-fake

## Current limitations

- no frontend operator console
- no distributed worker layer
- no worker-side provider/database spans yet
- signed JWT validation for external identity providers is not implemented yet

## Recommended next roadmap

- add worker-side provider/database spans
- add signed JWT validation for external identity providers
- add frontend operator console

## Release note

This version is a presentable backend MVP with deterministic and provider-backed execution modes. It is suitable for demos, portfolio presentation, client walkthroughs, and the next production-hardening phase.
