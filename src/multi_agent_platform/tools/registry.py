from pydantic import BaseModel, ConfigDict


def list_available_tool_names() -> list[str]:
    return [
        "goal_analyzer",
        "evidence_lookup",
        "summary_writer",
        "execution_checker",
        "generic_tool",
    ]


class PlannedToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    tool_input: dict[str, str]


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    tool_input: dict[str, str]
    tool_output: dict[str, str]


def execute_planned_tool_call(
    planned_tool_call: PlannedToolCall,
) -> ToolExecutionResult:
    tool_name = planned_tool_call.tool_name
    tool_input = planned_tool_call.tool_input

    if tool_name == "goal_analyzer":
        tool_output = {
            "goal_outline": f"Analyzed goal for {tool_input['task_title']}",
            "execution_hint": "Proceed with structured planning",
        }
    elif tool_name == "evidence_lookup":
        tool_output = {
            "evidence_summary": f"Collected evidence for {tool_input['task_title']}",
            "risk_note": "Dependencies should be validated before delivery",
        }
    elif tool_name == "summary_writer":
        tool_output = {
            "draft_summary": f"Prepared summary for {tool_input['task_title']}",
            "quality_check": "Draft is ready for review",
        }
    elif tool_name == "execution_checker":
        tool_output = {
            "execution_status": f"Prepared execution notes for {tool_input['task_title']}",
            "next_step": "Review execution outcome",
        }
    else:
        tool_output = {
            "result": f"Completed deterministic tool execution for {tool_input['task_title']}",
        }

    return ToolExecutionResult(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
    )
