"""PDF to Images tool - converts PDF pages to base64 images without OCR."""

import base64
from pathlib import Path

import fitz  # pymupdf


def pdf_to_images(
    pdf_path: str,
    dpi: int = 150,
) -> dict:
    """
    Convert PDF pages to base64-encoded PNG images.

    No OCR is performed - images are meant to be viewed directly by VL models.
    Images are kept in memory, not saved to disk.

    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for rendering (default 150, good balance of quality/size)

    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - total_pages: Number of pages
        - images: List of base64-encoded PNG images
        - error: Error message if failed
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
            # Render page to image
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
    """Convert base64 image to data URL for VL model input."""
    return f"data:image/png;base64,{image_base64}"
