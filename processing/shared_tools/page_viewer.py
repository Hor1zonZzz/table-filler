"""Page viewer tools for VL agents to view PDF pages as images."""

from typing import Any

from google.adk.tools import ToolContext
import google.genai.types as types


def get_page_count(tool_context: ToolContext) -> dict[str, Any]:
    """
    Get the total number of pages in the current PDF document.

    Use this tool at the start of document processing to understand the document
    size and plan your page viewing strategy. Always call this before using
    view_page() to know the valid page range.

    Returns:
        A dictionary containing:
        - total_pages: The number of pages in the PDF (int)
        - message: Human-readable summary of page count (str)

    Example:
        >>> get_page_count()
        {"total_pages": 5, "message": "This PDF has 5 page(s)."}
    """
    images = tool_context.state.get("temp:pdf_images", [])
    return {
        "total_pages": len(images),
        "message": f"This PDF has {len(images)} page(s).",
    }


def view_page(
    page_number: int,
    tool_context: ToolContext,
) -> types.Content:
    """
    View a specific page of the PDF document as an image.

    Use this tool to visually examine PDF pages, just like a human flipping
    through a document. The page image will be displayed for you to analyze
    and extract information from. Call this for each page you need to read.

    This is your primary tool for reading document content. The image returned
    can be analyzed to find text, tables, signatures, stamps, and other visual
    elements.

    Args:
        page_number: The page number to view, starting from 1 (first page is 1,
            not 0). Must be between 1 and the total page count.

    Returns:
        The page image as visual content that you can see and analyze directly.
        If there's an error (invalid page number, no PDF loaded), returns an
        error message instead.

    Example:
        >>> view_page(1)   # View the first page
        >>> view_page(3)   # View the third page

        Typical workflow:
        1. get_page_count() -> 5 pages
        2. view_page(1) -> see first page, extract info
        3. add_note("contract_id: ABC-123", "field")
        4. view_page(2) -> see second page, continue extraction
    """
    images = tool_context.state.get("temp:pdf_images", [])

    if not images:
        return types.Content(
            parts=[types.Part.from_text("Error: No PDF images loaded. The PDF may not have been processed yet.")]
        )

    total_pages = len(images)

    # Validate page number (1-indexed)
    if page_number < 1 or page_number > total_pages:
        return types.Content(
            parts=[types.Part.from_text(
                f"Error: Invalid page number {page_number}. "
                f"Valid range is 1 to {total_pages}."
            )]
        )

    # Get the image (convert to 0-indexed)
    image_base64 = images[page_number - 1]

    # Record which page was viewed (for tracking)
    viewed_pages = tool_context.state.get("temp:viewed_pages", [])
    if page_number not in viewed_pages:
        viewed_pages.append(page_number)
        tool_context.state["temp:viewed_pages"] = viewed_pages

    # Track current viewing page for notebook
    tool_context.state["temp:current_viewing_page"] = page_number

    # Return image as content that VL model can see
    import base64
    image_bytes = base64.b64decode(image_base64)

    return types.Content(
        parts=[
            types.Part.from_text(f"Page {page_number} of {total_pages}:"),
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ]
    )
