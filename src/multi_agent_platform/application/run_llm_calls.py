from multi_agent_platform.contracts.llm_call_views import (
    LlmCallListResponse,
    LlmCallResponse,
)
from multi_agent_platform.contracts.llm_calls import LlmCallPage, LlmCallRecord


def build_llm_call_response(llm_call_record: LlmCallRecord) -> LlmCallResponse:
    return LlmCallResponse(item=llm_call_record)


def build_llm_call_list_response(llm_call_page: LlmCallPage) -> LlmCallListResponse:
    return LlmCallListResponse(
        items=llm_call_page.items,
        page=llm_call_page.page,
    )
