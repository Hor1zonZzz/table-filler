"""Notebook tools for agents to record and recall information across multiple pages."""

from datetime import datetime
from typing import Any

from google.adk.tools import ToolContext


def add_note(
    content: str,
    tag: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Add a note to remember information extracted from the current page.

    Use this to record field values, observations, or any information you find
    while viewing PDF pages. Notes persist across page views, so you can
    accumulate information from multiple pages.

    Args:
        content: The note content (e.g., "contract_id: ABC-123")
        tag: Category tag for the note. Use:
            - "field": For extracted field values
            - "observation": For general observations about the document
            - "uncertain": For values you're not sure about
            - "location": For noting where you found information

    Returns:
        Confirmation with note ID

    Example:
        add_note("contract_id: ABC-2024-001", "field")
        add_note("Found party names on page 2", "location")
        add_note("Amount might be 50000 or 500000, unclear", "uncertain")
    """
    # Get or initialize notebook
    notebook = tool_context.state.get("temp:notebook", [])

    # Create note entry
    note_id = len(notebook) + 1
    note = {
        "id": note_id,
        "content": content,
        "tag": tag,
        "timestamp": datetime.now().isoformat(),
        "page": tool_context.state.get("temp:current_viewing_page"),
    }

    notebook.append(note)
    tool_context.state["temp:notebook"] = notebook

    return {
        "status": "success",
        "note_id": note_id,
        "message": f"Note #{note_id} added with tag '{tag}'",
    }


def read_notes(
    tag: str | None,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Read notes from the notebook, optionally filtered by tag.

    Use this to recall information you've recorded from previous pages.
    Before submitting your final extraction, read all notes to compile
    the complete form data.

    Args:
        tag: Optional tag to filter notes. If None, returns all notes.
            Common tags: "field", "observation", "uncertain", "location"

    Returns:
        List of notes matching the filter

    Example:
        read_notes(None)        # Read all notes
        read_notes("field")     # Read only field extraction notes
        read_notes("uncertain") # Read notes about uncertain values
    """
    notebook = tool_context.state.get("temp:notebook", [])

    if tag:
        filtered = [n for n in notebook if n.get("tag") == tag]
    else:
        filtered = notebook

    return {
        "status": "success",
        "total_notes": len(notebook),
        "filtered_count": len(filtered),
        "filter_tag": tag,
        "notes": filtered,
    }


def clear_notes(
    tag: str | None,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Clear notes from the notebook.

    Use sparingly - typically you want to keep notes until extraction is complete.

    Args:
        tag: If provided, only clear notes with this tag.
            If None, clear all notes.

    Returns:
        Confirmation of cleared notes
    """
    notebook = tool_context.state.get("temp:notebook", [])

    if tag:
        original_count = len(notebook)
        notebook = [n for n in notebook if n.get("tag") != tag]
        cleared_count = original_count - len(notebook)
        tool_context.state["temp:notebook"] = notebook
        return {
            "status": "success",
            "cleared_count": cleared_count,
            "remaining_count": len(notebook),
            "message": f"Cleared {cleared_count} notes with tag '{tag}'",
        }
    else:
        cleared_count = len(notebook)
        tool_context.state["temp:notebook"] = []
        return {
            "status": "success",
            "cleared_count": cleared_count,
            "remaining_count": 0,
            "message": f"Cleared all {cleared_count} notes",
        }
