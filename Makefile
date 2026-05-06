.PHONY: bootstrap lint format format-check typecheck test check migrate migration-check export-openapi agent-worker-dev api-go-dev hybrid-up smoke-memory smoke-sql smoke-llm-fake release-check

bootstrap:
	uv sync --group dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest -q

check:
	$(MAKE) lint
	$(MAKE) format-check
	$(MAKE) typecheck
	$(MAKE) test

migrate:
	uv run alembic upgrade head

migration-check:
	uv run python -m multi_agent_platform.storage.db.migration_check

export-openapi:
	uv run python scripts/export_openapi.py

agent-worker-dev:
	uv run uvicorn services.agent_worker.app:app --host 0.0.0.0 --port 8090 --reload

api-go-dev:
	cd apps/api-go && go run ./cmd/api

hybrid-up:
	docker compose -f infra/docker/compose.hybrid.yml up --build

smoke-memory:
	uv run python -c 'from fastapi.testclient import TestClient; from multi_agent_platform.api.dependencies import reset_api_state; from multi_agent_platform.main import app; reset_api_state(); client = TestClient(app); created = client.post("/runs", json={"user_goal": "Create a technical delivery plan", "workflow_type": "technical_plan"}); run_id = created.json()["item"]["run_id"]; client.post(f"/runs/{run_id}/plan"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/verify"); finalized = client.post(f"/runs/{run_id}/finalize"); print(finalized.status_code, finalized.json()["item"]["run_id"])'

smoke-sql:
	uv run python -c 'import os; from fastapi.testclient import TestClient; from multi_agent_platform.api.dependencies import reset_api_state; from multi_agent_platform.main import app; from multi_agent_platform.storage.db.migrations import migrate_database_schema; os.environ["STORAGE_BACKEND"] = "sql"; os.environ["DATABASE_URL"] = "sqlite:///./.workdir/multi_agent_platform.db"; migrate_database_schema(os.environ["DATABASE_URL"]); reset_api_state(); client = TestClient(app); created = client.post("/runs", json={"user_goal": "Create a technical delivery plan", "workflow_type": "technical_plan"}); run_id = created.json()["item"]["run_id"]; client.post(f"/runs/{run_id}/plan"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/verify"); client.post(f"/runs/{run_id}/finalize"); reset_api_state(); persisted = TestClient(app); state = persisted.get(f"/runs/{run_id}/state"); print(state.status_code, state.json()["item"]["status"])'

smoke-llm-fake:
	uv run python -c 'import os; from fastapi.testclient import TestClient; from multi_agent_platform.api.dependencies import reset_api_state; from multi_agent_platform.main import app; os.environ["EXECUTION_BACKEND"] = "llm"; os.environ["LLM_PROVIDER_NAME"] = "fake"; os.environ["LLM_MODEL_NAME"] = "fake-model"; reset_api_state(); client = TestClient(app); created = client.post("/runs", json={"user_goal": "Create a technical delivery plan", "workflow_type": "technical_plan"}); run_id = created.json()["item"]["run_id"]; client.post(f"/runs/{run_id}/plan"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/turns/advance"); client.post(f"/runs/{run_id}/verify"); finalized = client.post(f"/runs/{run_id}/finalize"); llm_calls = client.get(f"/runs/{run_id}/llm-calls?limit=10&offset=0"); print(finalized.status_code, llm_calls.json()["page"]["total_count"])'

release-check:
	$(MAKE) check
	$(MAKE) migration-check
	$(MAKE) smoke-memory
	$(MAKE) smoke-sql
	$(MAKE) smoke-llm-fake
