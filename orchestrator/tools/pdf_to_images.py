"""PDF to Images conversion utility for VL model processing.

This module provides internal utilities for converting PDF documents to
base64-encoded images. It is used by the batch processor, not directly
exposed as an agent tool.
"""

import base64
from pathlib import Path

import fitz  # pymupdf


def pdf_to_images(
    pdf_path: str,
    dpi: int = 150,
) -> dict:
    """
    Convert all pages of a PDF document to base64-encoded PNG images.

    This is an internal utility function used by the batch processor to
    prepare PDF pages for VL model viewing. No OCR is performed - the
    images are meant to be viewed directly by vision-capable models.

    Images are kept in memory (not saved to disk) to minimize I/O overhead
    during batch processing.

    Args:
        pdf_path: Absolute path to the PDF file to convert.
            Example: "/data/contracts/contract001.pdf"
        dpi: Resolution for rendering pages. Default is 150 DPI, which
            provides a good balance between image quality and size.
            Higher values (e.g., 300) give better quality but larger images.

    Returns:
        A dictionary containing:
        - status: "success" or "error"
        - total_pages: Number of pages converted (int, only if successful)
        - images: List of base64-encoded PNG strings, one per page
            (only if successful)
        - error: Error message describing what went wrong (only if error)

    Example:
        >>> result = pdf_to_images("/data/contract.pdf")
        >>> if result["status"] == "success":
        ...     print(f"Converted {result['total_pages']} pages")
        ...     first_page_base64 = result["images"][0]

        >>> result = pdf_to_images("/invalid/path.pdf")
        >>> result
        {"status": "error", "error": "File not found: /invalid/path.pdf"}
    """
    path = Path(pdf_path)

    if not path.exists():
        return {
            "status": "error",
            "error": f"File not found: {pdf_path}",
        }

    if not path.suffix.lower() == ".pdf":
        return {
            "status": "error",
            "error": f"Not a PDF file: {pdf_path}",
        }

    try:
        doc = fitz.open(pdf_path)
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page to image at specified DPI
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.tobytes("png")
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            images.append(image_base64)

        doc.close()

        return {
            "status": "success",
            "total_pages": len(images),
            "images": images,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to process PDF: {str(e)}",
        }


def get_image_data_url(image_base64: str) -> str:
    """
    Convert a base64-encoded image to a data URL format.

    This utility function creates a data URL that can be used in HTML img
    tags or passed to APIs that expect data URL format.

    Args:
        image_base64: Base64-encoded PNG image string (without the data URL prefix).

    Returns:
        Complete data URL string in format: "data:image/png;base64,{image_data}"

    Example:
        >>> data_url = get_image_data_url(page_image_base64)
        >>> # data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
    """
    return f"data:image/png;base64,{image_base64}"
