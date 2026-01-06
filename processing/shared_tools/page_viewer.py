"""Page viewer tool for VL agents to view PDF pages as images."""

from typing import Any

from google.adk.tools import ToolContext
import google.genai.types as types


def get_page_count(tool_context: ToolContext) -> dict[str, Any]:
    """
    Get the total number of pages in the current PDF.

    Returns:
        Dictionary with total_pages count
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
    View a specific page of the PDF as an image.

    Use this tool to look at PDF pages like a human would flip through a document.
    The page image will be displayed for you to analyze.

    Args:
        page_number: Page number to view (1-indexed, first page is 1)
        tool_context: ADK tool context

    Returns:
        The page image content that you can see and analyze

    Example:
        view_page(1)  # View the first page
        view_page(3)  # View the third page
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

    # Return image as content that VL model can see
    # The image is sent as inline data
    import base64
    image_bytes = base64.b64decode(image_base64)

    return types.Content(
        parts=[
            types.Part.from_text(f"Page {page_number} of {total_pages}:"),
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        ]
    )
