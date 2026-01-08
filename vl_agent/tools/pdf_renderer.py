"""PDF rendering utilities using PyMuPDF.

This module provides low-level PDF rendering functions used by the
PDF loading tools. It handles the conversion of PDF pages to PNG images.
"""

from pathlib import Path

import fitz  # pymupdf


def render_pdf_page(pdf_path: str, page_num: int, dpi: int = 150) -> bytes:
    """Render a single PDF page to PNG bytes.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        dpi: Resolution for rendering (default 150)

    Returns:
        PNG image bytes
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    image_bytes = pix.tobytes("png")
    doc.close()
    return image_bytes


def get_pdf_page_count(pdf_path: str) -> int:
    """Get total page count of a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Number of pages in the PDF
    """
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def validate_pdf_path(pdf_path: str) -> tuple[bool, str]:
    """Validate that the path points to a valid PDF file.

    Args:
        pdf_path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(pdf_path)

    if not path.exists():
        return False, f"File not found: {pdf_path}"

    if not path.suffix.lower() == ".pdf":
        return False, f"Not a PDF file: {pdf_path}"

    return True, ""
