"""Table schema configuration tool for VL agent."""

import json

from google.adk.tools import ToolContext


def set_config(
    tool_context: ToolContext,
    columns: list[dict],
) -> str:
    """Configure table schema for extraction.

    Args:
        tool_context: ADK ToolContext for state management.
        columns: List of column definitions. Each column is a dict with:
            - name (str): Column name / field name
            - type (str): Data type - "string", "number", "date", "boolean"
            - description (str): Description to help identify this field

    Returns:
        "success" or error message string.
    """
    # Debug: print state
    state = tool_context.state
    print(f"[DEBUG] ToolContext state keys (before): {list(state._state.keys()) if hasattr(state, '_state') else 'N/A'}")

    if not columns:
        return "fail: columns cannot be empty"

    for col in columns:
        if not isinstance(col, dict):
            return "fail: each column must be a dict"
        if "name" not in col:
            return "fail: each column must have 'name'"

    tool_context.state["table_schema"] = json.dumps(columns, ensure_ascii=False)
    print(f"[DEBUG] table_schema value: {tool_context.state.get('table_schema')}")
    return "success"
