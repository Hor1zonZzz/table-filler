"""Factory for creating dynamic data_append tool based on schema."""

import json
from typing import Optional
from pydantic import create_model
from google.adk.tools import FunctionTool, ToolContext


# Type mapping from schema type to Python type
TYPE_MAP = {
    "string": str,
    "number": float,
    "date": str,
    "boolean": bool,
}


def create_data_append_tool(schema_fields: list[dict]) -> FunctionTool:
    """Create a data_append FunctionTool with schema-based parameters.

    Args:
        schema_fields: List of field definitions from state["schema_fields"]

    Returns:
        FunctionTool with dynamic parameters matching the schema.
    """
    # Build Pydantic model fields
    model_fields = {}
    for field in schema_fields:
        name = field["name"]
        py_type = TYPE_MAP.get(field.get("type", "string"), str)
        required = field.get("required", True)
        default = field.get("default")

        if required:
            model_fields[name] = (py_type, ...)  # Required field
        else:
            model_fields[name] = (Optional[py_type], default)

    # Create dynamic Pydantic model
    RowData = create_model("RowData", **model_fields)

    # Create the actual append function
    def data_append(tool_context: ToolContext, row: RowData) -> str:
        """Append a row of extracted data.

        Args:
            row: Data row with fields matching the confirmed schema.

        Returns:
            Success message with row number.
        """
        # Convert Pydantic model to dict
        row_dict = row.model_dump()

        # Load and append
        raw = tool_context.state.get("extracted_rows", "[]")
        rows = json.loads(raw) if raw else []
        rows.append(row_dict)
        tool_context.state["extracted_rows"] = json.dumps(rows, ensure_ascii=False)

        return f"success: appended as row {len(rows)}"

    return FunctionTool(data_append)
