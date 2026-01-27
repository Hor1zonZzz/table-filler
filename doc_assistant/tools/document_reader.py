"""Document reader tool for Document Assistant.

This module provides the core read_document tool that can read PDF and image
files and answer questions about their content using a Vision-Language model.
"""

import base64
import os
from typing import Any

from google.adk.tools import ToolContext
from openai import AsyncOpenAI

from .pdf_utils import (
    get_pdf_page_count,
    render_page_with_size_limit,
    validate_pdf_path,
)


# Supported image formats (lowercase with dot)
SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}

# Maximum size for base64 encoded image (10MB)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


def validate_image_path(image_path: str) -> tuple[bool, str]:
    """Validate that a path points to a valid image file.

    Args:
        image_path: Path to validate.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty string.
    """
    if not os.path.exists(image_path):
        return False, f"File not found: {image_path}"

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in SUPPORTED_IMAGE_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        return False, f"Unsupported image format: {ext}. Supported formats: {supported}"

    return True, ""


def load_image_as_base64(image_path: str) -> str:
    """Load an image file and return as base64 encoded string.

    Args:
        image_path: Path to the image file.

    Returns:
        Base64 encoded string of the image.

    Raises:
        FileNotFoundError: If the image file does not exist.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_file_type(file_path: str) -> str:
    """Detect whether a file is a PDF, image, or unknown type.

    Args:
        file_path: Path to the file.

    Returns:
        One of: "pdf", "image", "unknown"
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return "pdf"

    if ext in SUPPORTED_IMAGE_FORMATS:
        return "image"

    return "unknown"


def _get_vl_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client for the VL model.

    Returns:
        AsyncOpenAI client configured for DashScope.
    """
    return AsyncOpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv(
            "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
    )


async def _call_vl_model(question: str, images_base64: list[str]) -> str:
    """Call the VL model with images and a question.

    Args:
        question: The question to ask about the images.
        images_base64: List of base64 encoded images.

    Returns:
        The model's response text.
    """
    client = _get_vl_client()

    # Build message content with text and images
    content: list[dict[str, Any]] = [{"type": "text", "text": question}]

    for img_b64 in images_base64:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            }
        )

    messages = [{"role": "user", "content": content}]

    response = await client.chat.completions.create(
        model=os.getenv("VL_MODEL", "qwen-vl-max"),
        messages=messages,
    )

    return response.choices[0].message.content or ""


async def read_document(
    tool_context: ToolContext,
    file_path: str,
    question: str,
    pages: list[int] | None = None,
) -> dict[str, Any]:
    """Read a document (PDF or image) and answer a question about its content.

    This tool uses a Vision-Language model to understand the document content
    and answer the provided question.

    Args:
        tool_context: The ADK tool context.
        file_path: Path to the document (PDF or image file).
        question: The question to answer about the document.
        pages: For PDF files, optional list of page numbers to read (1-indexed).
               If None, all pages are read. Ignored for image files.

    Returns:
        A dictionary with:
        - status: "success" or "error"
        - answer: The model's answer (if success)
        - file_type: "pdf" or "image"
        - pages_read: List of pages read (1-indexed, for PDF only)
        - total_pages: Total pages in PDF (for PDF only)
        - message: Error message (if error)
    """
    # Detect file type
    file_type = detect_file_type(file_path)

    if file_type == "unknown":
        supported_formats = [".pdf"] + sorted(SUPPORTED_IMAGE_FORMATS)
        return {
            "status": "error",
            "message": f"Unsupported file format. Supported formats: {', '.join(supported_formats)}",
        }

    # Handle PDF files
    if file_type == "pdf":
        return await _read_pdf(file_path, question, pages)

    # Handle image files
    return await _read_image(file_path, question)


async def _read_pdf(
    file_path: str,
    question: str,
    pages: list[int] | None = None,
) -> dict[str, Any]:
    """Read a PDF file and answer a question.

    Args:
        file_path: Path to the PDF file.
        question: The question to answer.
        pages: Optional list of pages to read (1-indexed).

    Returns:
        Result dictionary.
    """
    # Validate PDF path
    is_valid, error_msg = validate_pdf_path(file_path)
    if not is_valid:
        return {"status": "error", "message": error_msg}

    # Get total pages
    try:
        total_pages = get_pdf_page_count(file_path)
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}

    # Determine which pages to read
    if pages is None:
        pages_to_read = list(range(1, total_pages + 1))  # All pages, 1-indexed
    else:
        pages_to_read = pages

    # Validate page numbers
    invalid_pages = [p for p in pages_to_read if p < 1 or p > total_pages]
    if invalid_pages:
        return {
            "status": "error",
            "message": f"Invalid page numbers: {invalid_pages}. PDF has {total_pages} pages.",
        }

    # Render pages to base64
    images_base64: list[str] = []
    for page_num in pages_to_read:
        try:
            # Convert 1-indexed to 0-indexed for rendering
            img_b64, _dpi = render_page_with_size_limit(
                file_path, page_num - 1, MAX_IMAGE_SIZE_BYTES
            )
            images_base64.append(img_b64)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to render page {page_num}: {e}",
            }

    # Call VL model
    try:
        answer = await _call_vl_model(question, images_base64)
    except Exception as e:
        return {"status": "error", "message": f"VL model error: {e}"}

    return {
        "status": "success",
        "answer": answer,
        "file_type": "pdf",
        "pages_read": pages_to_read,
        "total_pages": total_pages,
    }


async def _read_image(file_path: str, question: str) -> dict[str, Any]:
    """Read an image file and answer a question.

    Args:
        file_path: Path to the image file.
        question: The question to answer.

    Returns:
        Result dictionary.
    """
    # Validate image path
    is_valid, error_msg = validate_image_path(file_path)
    if not is_valid:
        return {"status": "error", "message": error_msg}

    # Load image
    try:
        img_b64 = load_image_as_base64(file_path)
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}

    # Call VL model
    try:
        answer = await _call_vl_model(question, [img_b64])
    except Exception as e:
        return {"status": "error", "message": f"VL model error: {e}"}

    return {
        "status": "success",
        "answer": answer,
        "file_type": "image",
    }
