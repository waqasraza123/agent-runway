from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from multi_agent_platform.api.dependencies import reset_api_state
from multi_agent_platform.main import app
from multi_agent_platform.storage.db.migrations import migrate_database_schema


@pytest.fixture
def configure_sql_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    database_file = tmp_path / "multi_agent_platform.db"
    database_url = f"sqlite:///{database_file}"
    monkeypatch.setenv("STORAGE_BACKEND", "sql")
    monkeypatch.setenv("DATABASE_URL", database_url)
    migrate_database_schema(database_url)
    reset_api_state()
    yield
    reset_api_state()


def test_sql_backend_persists_run_data_across_service_reset(
    configure_sql_storage: None,
) -> None:
    first_client = TestClient(app)

    create_response = first_client.post(
        "/runs",
        json={
            "user_goal": "Create a technical delivery plan",
            "workflow_type": "technical_plan",
        },
    )
    run_id = create_response.json()["item"]["run_id"]

    first_client.post(f"/runs/{run_id}/plan")
    first_client.post(f"/runs/{run_id}/turns/advance")
    first_client.post(f"/runs/{run_id}/turns/advance")
    first_client.post(f"/runs/{run_id}/turns/advance")
    first_client.post(f"/runs/{run_id}/verify")
    finalize_response = first_client.post(f"/runs/{run_id}/finalize")

    assert finalize_response.status_code == 200

    reset_api_state()

    second_client = TestClient(app)
    state_response = second_client.get(f"/runs/{run_id}/state")
    output_response = second_client.get(f"/runs/{run_id}/outputs/latest")
    tool_calls_response = second_client.get(f"/runs/{run_id}/tool-calls?limit=10&offset=0")
    events_response = second_client.get(f"/runs/{run_id}/events?limit=20&offset=0")

    assert state_response.status_code == 200
    assert state_response.json()["item"]["status"] == "completed"
    assert output_response.status_code == 200
    assert output_response.json()["item"]["run_id"] == run_id
    assert tool_calls_response.json()["page"]["total_count"] == 3
    assert events_response.json()["page"]["total_count"] >= 1
