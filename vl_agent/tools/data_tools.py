"""Data management tools for extracted results."""

import json
from google.adk.tools import ToolContext


def _get_rows(tool_context: ToolContext) -> list[dict]:
    """Load extracted rows from state."""
    raw = tool_context.state.get("extracted_rows", "[]")
    return json.loads(raw) if raw else []


def _save_rows(tool_context: ToolContext, rows: list[dict]) -> None:
    """Save extracted rows to state."""
    tool_context.state["extracted_rows"] = json.dumps(rows, ensure_ascii=False)


def data_list(tool_context: ToolContext) -> str:
    """List all extracted data rows.

    Returns:
        Formatted table of extracted data with row numbers.
    """
    rows = _get_rows(tool_context)
    if not rows:
        return "No data extracted yet."

    lines = [f"Extracted data ({len(rows)} rows):"]
    for i, row in enumerate(rows, start=1):
        row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
        lines.append(f"  [{i}] {row_str}")
    return "\n".join(lines)
