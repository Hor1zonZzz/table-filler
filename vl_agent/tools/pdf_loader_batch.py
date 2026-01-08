"""Batch PDF loading tool for Strategy 3.

This tool loads ALL pages of a PDF at once, allowing the VL model
to see and analyze all pages in a single conversation turn.
"""

from google.adk.tools import ToolContext
from google.genai import types

from .pdf_renderer import get_pdf_page_count, render_pdf_page, validate_pdf_path


async def load_all_pdf_pages(
    tool_context: ToolContext,
    pdf_path: str,
    dpi: int = 150,
) -> dict:
    """Load ALL pages of a PDF as image artifacts.

    This tool renders every page of the PDF to an image and saves them
    as artifacts. All pages will be injected into the conversation via
    the before_model_callback, allowing the VL model to see and analyze
    the entire document at once.

    Args:
        pdf_path: Local file path to the PDF document
        dpi: Resolution for rendering (default 150, max 300 recommended)

    Returns:
        dict with:
            - status: "success" or "error"
            - tool_response_artifact_ids: List of artifact IDs (one per page)
            - total_pages: Number of pages loaded
            - message: Description

    Note:
        For large PDFs (10+ pages), this may consume significant context
        window space. Consider using sequential loading for large documents.
    """
    # Validate PDF path
    is_valid, error_msg = validate_pdf_path(pdf_path)
    if not is_valid:
        return {
            "status": "error",
            "tool_response_artifact_ids": [],
            "total_pages": 0,
            "message": error_msg,
        }

    # Get page count
    total_pages = get_pdf_page_count(pdf_path)

    if total_pages == 0:
        return {
            "status": "error",
            "tool_response_artifact_ids": [],
            "total_pages": 0,
            "message": "PDF has no pages",
        }

    # Render and save each page
    artifact_ids = []
    for page_num in range(total_pages):
        # Render page to PNG
        image_bytes = render_pdf_page(pdf_path, page_num, dpi)

        # Create Part and save as artifact
        part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        artifact_id = f"pdf_p{page_num + 1}_{tool_context.function_call_id}.png"
        await tool_context.save_artifact(filename=artifact_id, artifact=part)
        artifact_ids.append(artifact_id)

    # Store metadata in state
    tool_context.state["temp:pdf_path"] = pdf_path
    tool_context.state["temp:pdf_total_pages"] = total_pages
    tool_context.state["temp:pdf_artifact_ids"] = artifact_ids

    return {
        "status": "success",
        "tool_response_artifact_ids": artifact_ids,
        "total_pages": total_pages,
        "message": f"Loaded all {total_pages} pages. Analyze each page in order.",
    }
