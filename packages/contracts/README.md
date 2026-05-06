# Agent Runway Contracts

Shared API and service-boundary contracts for the hybrid Go + Python deployment.

## Public API

The current public API source of truth remains the Python FastAPI app while the Go control plane is being introduced. Export the current OpenAPI document with:

```bash
make export-openapi
```

The generated document is written to:

```text
packages/contracts/public/openapi.json
```

The Go control plane currently implements the initial run surface:

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

## Worker Boundary

The Go control plane calls the Python agent worker through:

```text
POST /internal/agent/turn
```

The request and response schema is defined in:

```text
packages/contracts/worker/agent-turn.schema.json
```

Only the Go control plane should call this endpoint. The Python worker returns structured execution output; it does not mutate run state.
