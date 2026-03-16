# Multi-Agent Platform

Production-grade multi-agent research and execution platform with deterministic planning, turn execution, tool calls, approvals, verification, final outputs, and switchable storage backends.

## Current status

Implemented and working:

- run creation and listing
- deterministic plan generation
- task registration and lifecycle
- deterministic turn advancement
- tool call execution and storage
- evidence recording
- approval request and decision flow
- verification reports
- final output synthesis
- in-memory storage backend
- SQL-backed durable storage backend
- FastAPI surface for the execution workflow
- unit and integration test coverage for the current platform spine

## Repository structure

- src/multi_agent_platform/api — API app, routes, dependency wiring
- src/multi_agent_platform/application — service layer and response builders
- src/multi_agent_platform/contracts — request, response, and domain cos
- src/multi_agent_platform/orchestration — run state transitions
- src/multi_agent_platform/planning — deterministic plan generation
- src/multi_agent_platform/agents — deterministic turn runtime
- src/multi_agent_platform/tools — deterministic tool registry
- src/multi_agent_platform/storage — in-memory and SQL persistence layers
- src/multi_agent_platform/config — runtime settings
- tests/unit — unit coverage for contracts, repositories, application, and API
- tests/integration — integration coverage for SQL persistence

## Storage backends

The platform supports two backends:

- memory for fast local iteration
- sql for durable local persistence and production-ready repository boundaries

Environment variables:

- STORAGE_BACKEND=memory|sql
- DATABASE_URL=sqlite:///./.workdir/multi_agent_platform.db

## Local setup

Bootstrap:

    uv sync --group dev

Run checks:

    make check

Run API locally:

    uv run uvicorn multi_agent_platform.main:app --reload

## Fast smoke flow

```
Memory modython -c "from fastapi.testclient import TestClient; from multi_agent_platform.api.dependencies import reset_api_state; from multi_agent_platform.main import app; reset_api_state(); client = TestClient(app); created = client.post(\"/runs\", json={\"user_goal\": \"Create a technical delivery plan\", \"workflow_type\": \"technical_plan\"}); run_id = created.json()[\"item\"][\"run_id\"]; client.post(f\"/runs/{run_id}/plan\"); client.post(f\"/runs/{run_id}/turns/advance\"); client.post(f\"/runs/{run_id}/turns/advance\"); client.post(f\"/runs/{run_id}/turns/advance\"); client.post(f\"/runs/{run_id}/verify\"); finalized = client.post(f\"/runs/{run_id}/finalize\"); print(finalized.status_code, finalized.json()[\"item\"][\"run_id\"])"
```

SQL mode:

    uv run python -c "import os; from fastapi.testclient import TestClient; from multi_agent_platform.api.dependencies import reset_api_state; from multi_agent_platform.main import app; os.environ[\"STORAGE_BACKEND\"] = \"sql\"; os.environ[\"DATABASE_URL\"] = \"sqlite:///./.workdir/multi_agent_platform.db\"; reset_api_state(); client = TestClient(app); created = client.post(\"/runs\", json={\"user_goal\": \"Create a technical delivery plan\", \"workflow_type\": \"technical_plan\"}); run_id = created.json()[\"item\"][\"run_id\"]; client.post(f\"/runs/{run_id}/plan\"); client.post(f\"/runs/{run_id}/turns/advance\"); client.post(f\"/runs/{run_id}/turns/advance\"); client.post(f\"/runs/{run_id}/turns/advance\"); client.post(f\"/runs/{run_id}/verify\"); client.post(f\"/runs/{run_id}/finalize\"); reset_api_state(); persisted = TestClient(app); state = persisted.get(f\"/runs/{run_id}/state\"); print(state.status_code, state.json()[\"item\"][\"status\"])"

## Known limitations

Current implementation is intentionally deterministic and backend-first.

Not included yet:

- Alembic migrations
- PostgreSQL deployment setup
- authentication and authorization
- async job processing
- external LLM provider execution
- UI frontend
- observability stack
- distributed workers

## Next practical upgrades

- Alembic migrations and schema versioning
- PostgreSQL deployment profile
- richer agent runtime policies
- pluggable real tool adapters
- LLM-backed planning and execution
- authentication and RBAC
- structured logging and tracing
- frontend operator console
