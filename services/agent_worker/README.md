# Agent Runway Python Agent Worker

Private worker service for LLM/provider-backed turn execution.

Run locally:

```bash
uv run uvicorn services.agent_worker.app:app --host 0.0.0.0 --port 8090 --reload
```

Endpoints:

- `GET /health`
- `POST /internal/agent/turn`

Environment:

```bash
AGENT_WORKER_TOKEN=
LLM_API_KEY=
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4.1-mini
```

If `AGENT_WORKER_TOKEN` is set, requests to `/internal/agent/turn` must include:

```text
Authorization: Bearer <token>
```

This service returns structured turn execution outcomes. It does not mutate run state.
