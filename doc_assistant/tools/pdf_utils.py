"""PDF utility functions for Document Assistant."""

import base64
import os

import fitz  # PyMuPDF


# DPI levels for adaptive rendering (from high to low)
DPI_LEVELS = [150, 120, 100, 72, 50]


def get_pdf_page_count(pdf_path: str) -> int:
    """Get the total number of pages in a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Number of pages in the PDF.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


def validate_pdf_path(pdf_path: str) -> tuple[bool, str]:
    """Validate that a path points to a valid PDF file.

    Args:
        pdf_path: Path to validate.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty string.
    """
    if not os.path.exists(pdf_path):
        return False, f"File not found: {pdf_path}"

    if not pdf_path.lower().endswith(".pdf"):
        return False, f"File is not a PDF: {pdf_path}"

    return True, ""


def render_pdf_page(pdf_path: str, page_num: int, dpi: int = 72) -> bytes:
    """Render a single PDF page to PNG bytes.

    Args:
        pdf_path: Path to the PDF file.
        page_num: Zero-indexed page number.
        dpi: Resolution in dots per inch.

    Returns:
        PNG image data as bytes.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        IndexError: If page_num is out of range.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        if page_num < 0 or page_num >= len(doc):
            raise IndexError(f"Page {page_num} is out of range (0-{len(doc) - 1})")

        page = doc[page_num]
        # Create transformation matrix based on DPI
        # Default PDF resolution is 72 DPI
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        # Render page to pixmap and convert to PNG
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    finally:
        doc.close()


def render_page_with_size_limit(
    pdf_path: str, page_num: int, max_bytes: int = 10 * 1024 * 1024
) -> tuple[str, int]:
    """Render a PDF page with adaptive DPI to stay within size limit.

    Tries progressively lower DPI values until the result is within
    the specified size limit.

    Args:
        pdf_path: Path to the PDF file.
        page_num: Zero-indexed page number.
        max_bytes: Maximum size in bytes for the result.

    Returns:
        Tuple of (base64_encoded_png, dpi_used).
    """
    for dpi in DPI_LEVELS:
        png_bytes = render_pdf_page(pdf_path, page_num, dpi)

        if len(png_bytes) <= max_bytes:
            return base64.b64encode(png_bytes).decode("utf-8"), dpi

    # If even lowest DPI exceeds limit, return it anyway
    png_bytes = render_pdf_page(pdf_path, page_num, DPI_LEVELS[-1])
    return base64.b64encode(png_bytes).decode("utf-8"), DPI_LEVELS[-1]
