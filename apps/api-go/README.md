# Agent Runway Go Control Plane

This is the first hybrid control-plane slice for Agent Runway.

Current responsibilities:

- expose Go service health/readiness endpoints
- own initial run creation and run reads
- own deterministic plan generation
- own deterministic and worker-backed LLM turn advancement
- persist turns, tool calls, LLM calls, evidence, and events
- expose persisted events, turns, tool calls, and LLM calls
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
```

Set `EXECUTION_BACKEND=llm` to call the private Python worker during `POST /runs/{run_id}/turns/advance`. Go still owns the final run state transition and database writes.

If the Python worker is unavailable, the Go control plane falls back to deterministic execution and persists an LLM-call record with the failure details.

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
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/turns`
- `GET /runs/{run_id}/tool-calls`
- `GET /runs/{run_id}/llm-calls`

The next implementation step is to port verification and finalization.
