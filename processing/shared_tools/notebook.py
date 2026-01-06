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
    Record a note to remember information found while viewing PDF pages.

    Use this tool immediately after finding important information on a page.
    Notes persist across page views, allowing you to accumulate data from
    multiple pages before compiling your final extraction result.

    This is essential for multi-page documents where related information
    (like party names on page 1, amounts on page 3) must be combined.

    Args:
        content: The information to record. Be specific and include the field
            name and value, e.g., "contract_id: ABC-2024-001" or
            "party_a: Acme Corporation".
        tag: Category for organizing notes. Use one of:
            - "field": For definite extracted field values
            - "uncertain": For values you're not confident about
            - "observation": For general notes about the document
            - "location": For noting where information was found

    Returns:
        A dictionary containing:
        - status: "success" if note was added
        - note_id: Unique identifier for this note (int)
        - message: Confirmation message (str)

    Example:
        >>> add_note("contract_id: ABC-2024-001", "field")
        {"status": "success", "note_id": 1, "message": "Note #1 added with tag 'field'"}

        >>> add_note("party_a: Acme Corporation", "field")
        >>> add_note("Amount unclear: might be 50000 or 500000", "uncertain")
        >>> add_note("Signature found on page 5", "location")
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
    Retrieve notes recorded during document processing.

    Use this tool to recall information you've noted from previous pages.
    Call this before generating your final extraction result to compile
    all collected data. You can filter by tag to focus on specific types
    of notes.

    Args:
        tag: Optional filter to retrieve only notes with a specific tag.
            Pass None to retrieve all notes. Common tags:
            - "field": Extracted field values
            - "uncertain": Uncertain values needing review
            - "observation": General observations
            - "location": Where information was found

    Returns:
        A dictionary containing:
        - status: "success"
        - total_notes: Total number of notes in notebook (int)
        - filtered_count: Number of notes matching the filter (int)
        - filter_tag: The tag used for filtering, or None
        - notes: List of note objects, each containing:
            - id: Note identifier
            - content: The recorded information
            - tag: Note category
            - timestamp: When the note was created
            - page: Which page the note was made on

    Example:
        >>> read_notes(None)           # Get all notes
        >>> read_notes("field")        # Get only field extraction notes
        >>> read_notes("uncertain")    # Get values that need review

        Typical workflow before final output:
        1. read_notes("field") -> get all extracted values
        2. read_notes("uncertain") -> check what needs attention
        3. Compile final extraction JSON
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
    Remove notes from the notebook.

    Use this tool sparingly. Typically, you want to keep all notes until
    extraction is complete. Only clear notes if you need to restart
    extraction or remove incorrect entries.

    Args:
        tag: If provided, only clear notes with this specific tag.
            If None, clear ALL notes from the notebook.

    Returns:
        A dictionary containing:
        - status: "success"
        - cleared_count: Number of notes that were removed (int)
        - remaining_count: Number of notes still in notebook (int)
        - message: Confirmation message (str)

    Example:
        >>> clear_notes("observation")  # Clear only observation notes
        {"status": "success", "cleared_count": 3, "remaining_count": 5, ...}

        >>> clear_notes(None)           # Clear all notes (use with caution)
        {"status": "success", "cleared_count": 8, "remaining_count": 0, ...}
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
