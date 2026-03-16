import json
from collections.abc import Callable
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from multi_agent_platform.contracts.turn_execution import (
    LlmTurnRequest,
    LlmTurnResponse,
    LlmUsage,
    StructuredTurnOutput,
)

Transport = Callable[
    [str, dict[str, str], dict[str, object], float],
    dict[str, object],
]


def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw_response = response.read().decode("utf-8")
    except HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"OpenAI request failed with status {error.code}: {response_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"OpenAI request failed: {error.reason}") from error

    loaded = json.loads(raw_response)
    if not isinstance(loaded, dict):
        raise ValueError("OpenAI response must be a JSON object")
    return cast(dict[str, object], loaded)


class OpenAiCompatibleProvider:
    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model_name: str = "gpt-4.1-mini",
        request_timeout_seconds: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        cleaned_api_key = api_key.strip()
        if not cleaned_api_key:
            raise ValueError("OpenAI API key must not be blank")
        self._api_key = cleaned_api_key
        self._base_url = base_url.rstrip("/")
        self._default_model_name = default_model_name
        self._request_timeout_seconds = request_timeout_seconds
        self._transport = transport or _post_json

    def generate_turn(self, request: LlmTurnRequest) -> LlmTurnResponse:
        timeout_seconds = (
            request.execution_profile.timeout_seconds
            or self._request_timeout_seconds
        )
        response_data = self._transport(
            f"{self._base_url}/chat/completions",
            {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            self._build_payload(request),
            timeout_seconds,
        )
        return self._parse_response(request, response_data)

    def _build_payload(self, request: LlmTurnRequest) -> dict[str, object]:
        execution_profile = request.execution_profile
        payload: dict[str, object] = {
            "model": execution_profile.model_name or self._default_model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._build_system_prompt(),
                },
                {
                    "role": "user",
                    "content": self._build_user_prompt(request),
                },
            ],
            "response_format": {"type": "json_object"},
        }
        if execution_profile.temperature is not None:
            payload["temperature"] = execution_profile.temperature
        if execution_profile.max_output_tokens is not None:
            payload["max_tokens"] = execution_profile.max_output_tokens
        return payload

    def _build_system_prompt(self) -> str:
        return (
            "You are an execution engine for a backend-first multi-agent platform. "
            "Return only valid JSON. Do not include markdown fences or extra text."
        )

    def _build_user_prompt(self, request: LlmTurnRequest) -> str:
        allowed_tool_names = request.available_tool_names or ["generic_tool"]
        example_payload = {
            "summary": "Planner prepared the structured next step.",
            "planned_tool_calls": [
                {
                    "tool_name": allowed_tool_names[0],
                    "tool_input": {
                        "user_goal": request.user_goal,
                        "task_title": request.task.title,
                        "agent_name": request.task.assigned_agent,
                    },
                }
            ],
        }
        prompt_lines = [
            f"user_goal: {request.user_goal}",
            f"task_title: {request.task.title}",
            f"task_description: {request.task.description}",
            f"assigned_agent: {request.task.assigned_agent}",
            f"acceptance_criteria: {request.task.acceptance_criteria}",
            f"allowed_tool_names: {allowed_tool_names}",
            "Return a JSON object with keys summary and planned_tool_calls.",
            "summary must be a concise string. planned_tool_calls must be a list.",
            "Each planned_tool_call must include tool_name and tool_input.",
            "tool_input values must all be strings.",
            "Choose only from the allowed tool names.",
            f"Example JSON shape: {json.dumps(example_payload)}",
        ]
        return "\n".join(prompt_lines)

    def _parse_response(
        self,
        request: LlmTurnRequest,
        response_data: dict[str, object],
    ) -> LlmTurnResponse:
        choices = response_data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("OpenAI response must include choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ValueError("OpenAI choice must be an object")

        message_payload = first_choice.get("message")
        if not isinstance(message_payload, dict):
            raise ValueError("OpenAI choice must include a message")

        raw_response_text = self._extract_response_text(message_payload.get("content"))
        structured_output = StructuredTurnOutput.model_validate(
            json.loads(raw_response_text)
        )
        self._validate_tool_names(request, structured_output)

        model_name = response_data.get("model")
        finish_reason = first_choice.get("finish_reason")

        return LlmTurnResponse(
            provider_name=self.provider_name,
            model_name=(
                model_name
                if isinstance(model_name, str) and model_name
                else request.execution_profile.model_name or self._default_model_name
            ),
            output=structured_output,
            usage=self._build_usage(response_data.get("usage")),
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            raw_response_text=raw_response_text,
        )

    def _extract_response_text(self, content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                text_value = item.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
            combined = "".join(text_parts).strip()
            if combined:
                return combined
        raise ValueError("OpenAI message content must contain text")

    def _build_usage(self, usage_payload: object) -> LlmUsage:
        if not isinstance(usage_payload, dict):
            return LlmUsage()

        prompt_tokens_value = usage_payload.get("prompt_tokens")
        completion_tokens_value = usage_payload.get("completion_tokens")
        total_tokens_value = usage_payload.get("total_tokens")

        prompt_tokens: int = (
            prompt_tokens_value if isinstance(prompt_tokens_value, int) else 0
        )
        completion_tokens: int = (
            completion_tokens_value if isinstance(completion_tokens_value, int) else 0
        )
        total_tokens: int = (
            total_tokens_value
            if isinstance(total_tokens_value, int)
            else prompt_tokens + completion_tokens
        )

        return LlmUsage(
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def _validate_tool_names(
        self,
        request: LlmTurnRequest,
        structured_output: StructuredTurnOutput,
    ) -> None:
        allowed_tool_names = set(request.available_tool_names)
        if not allowed_tool_names:
            return
        for planned_tool_call in structured_output.planned_tool_calls:
            if planned_tool_call.tool_name not in allowed_tool_names:
                raise ValueError(
                    "Unsupported tool name returned by provider: "
                    f"{planned_tool_call.tool_name}"
                )