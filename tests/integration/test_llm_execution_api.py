from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from multi_agent_platform.api.dependencies import reset_api_state
from multi_agent_platform.main import app


@pytest.fixture
def configure_llm_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    monkeypatch.setenv("EXECUTION_BACKEND", "llm")
    monkeypatch.setenv("LLM_PROVIDER_NAME", "fake")
    monkeypatch.setenv("LLM_MODEL_NAME", "fake-model")
    reset_api_state()
    yield
    reset_api_state()


def test_api_lists_llm_call_records(
    configure_llm_execution: None,
) -> None:
    client = TestClient(app)

    create_response = client.post(
        "/runs",
        json={
            "user_goal": "Create a technical delivery plan",
            "workflow_type": "technical_plan",
        },
    )
    run_id = create_response.json()["item"]["run_id"]

    client.post(f"/runs/{run_id}/plan")
    client.post(f"/runs/{run_id}/turns/advance")
    llm_calls_response = client.get(f"/runs/{run_id}/llm-calls?limit=10&offset=0")

    assert llm_calls_response.status_code == 200
    payload = llm_calls_response.json()
    assert payload["page"]["total_count"] == 1
    assert payload["items"][0]["provider_name"] == "fake"
    assert payload["items"][0]["model_name"] == "fake-model"
