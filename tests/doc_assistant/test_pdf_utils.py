"""Tests for doc_assistant.tools.pdf_utils module."""

import base64
import os
import tempfile

import fitz  # PyMuPDF
import pytest


@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file for testing."""
    # Use tempfile.mktemp instead to avoid Windows file locking issues
    pdf_path = tempfile.mktemp(suffix=".pdf")
    doc = fitz.open()
    for i in range(3):  # Create 3 pages
        page = doc.new_page(width=595, height=842)  # A4 size
        text = f"Test Page {i + 1}"
        page.insert_text((100, 100), text, fontsize=24)
    doc.save(pdf_path)
    doc.close()
    yield pdf_path
    # Cleanup
    if os.path.exists(pdf_path):
        os.unlink(pdf_path)


@pytest.fixture
def single_page_pdf_path():
    """Create a single-page PDF for testing."""
    pdf_path = tempfile.mktemp(suffix=".pdf")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((100, 100), "Single Page Content", fontsize=24)
    doc.save(pdf_path)
    doc.close()
    yield pdf_path
    if os.path.exists(pdf_path):
        os.unlink(pdf_path)


class TestGetPdfPageCount:
    """Tests for get_pdf_page_count function."""

    def test_returns_correct_page_count(self, sample_pdf_path):
        """Should return the correct number of pages."""
        from doc_assistant.tools.pdf_utils import get_pdf_page_count

        count = get_pdf_page_count(sample_pdf_path)
        assert count == 3

    def test_single_page_pdf(self, single_page_pdf_path):
        """Should return 1 for single page PDF."""
        from doc_assistant.tools.pdf_utils import get_pdf_page_count

        count = get_pdf_page_count(single_page_pdf_path)
        assert count == 1

    def test_raises_error_for_nonexistent_file(self):
        """Should raise error for non-existent file."""
        from doc_assistant.tools.pdf_utils import get_pdf_page_count

        with pytest.raises(FileNotFoundError):
            get_pdf_page_count("/nonexistent/path/file.pdf")


class TestValidatePdfPath:
    """Tests for validate_pdf_path function."""

    def test_valid_pdf_path(self, sample_pdf_path):
        """Should return True for valid PDF path."""
        from doc_assistant.tools.pdf_utils import validate_pdf_path

        is_valid, message = validate_pdf_path(sample_pdf_path)
        assert is_valid is True
        assert message == ""

    def test_nonexistent_file(self):
        """Should return False for non-existent file."""
        from doc_assistant.tools.pdf_utils import validate_pdf_path

        is_valid, message = validate_pdf_path("/nonexistent/path/file.pdf")
        assert is_valid is False
        assert "not found" in message.lower() or "exist" in message.lower()

    def test_wrong_extension(self, sample_pdf_path):
        """Should return False for non-PDF extension."""
        from doc_assistant.tools.pdf_utils import validate_pdf_path

        # Rename to .txt temporarily
        txt_path = sample_pdf_path.replace(".pdf", ".txt")
        os.rename(sample_pdf_path, txt_path)
        try:
            is_valid, message = validate_pdf_path(txt_path)
            assert is_valid is False
            assert "pdf" in message.lower()
        finally:
            os.rename(txt_path, sample_pdf_path)


class TestRenderPdfPage:
    """Tests for render_pdf_page function."""

    def test_renders_page_to_png_bytes(self, sample_pdf_path):
        """Should render a page to PNG bytes."""
        from doc_assistant.tools.pdf_utils import render_pdf_page

        result = render_pdf_page(sample_pdf_path, page_num=0, dpi=72)
        assert isinstance(result, bytes)
        # PNG files start with specific magic bytes
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_renders_different_pages(self, sample_pdf_path):
        """Should render different pages correctly."""
        from doc_assistant.tools.pdf_utils import render_pdf_page

        page0 = render_pdf_page(sample_pdf_path, page_num=0, dpi=72)
        page1 = render_pdf_page(sample_pdf_path, page_num=1, dpi=72)

        # Different pages should produce different images
        assert page0 != page1

    def test_higher_dpi_produces_larger_image(self, single_page_pdf_path):
        """Higher DPI should produce larger image data."""
        from doc_assistant.tools.pdf_utils import render_pdf_page

        low_dpi = render_pdf_page(single_page_pdf_path, page_num=0, dpi=72)
        high_dpi = render_pdf_page(single_page_pdf_path, page_num=0, dpi=150)

        assert len(high_dpi) > len(low_dpi)

    def test_raises_error_for_invalid_page_num(self, sample_pdf_path):
        """Should raise error for invalid page number."""
        from doc_assistant.tools.pdf_utils import render_pdf_page

        with pytest.raises((IndexError, ValueError)):
            render_pdf_page(sample_pdf_path, page_num=100, dpi=72)


class TestRenderPageWithSizeLimit:
    """Tests for render_page_with_size_limit function."""

    def test_returns_base64_string(self, single_page_pdf_path):
        """Should return base64 encoded string."""
        from doc_assistant.tools.pdf_utils import render_page_with_size_limit

        result, dpi_used = render_page_with_size_limit(
            single_page_pdf_path, page_num=0, max_bytes=10 * 1024 * 1024
        )

        assert isinstance(result, str)
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_returns_dpi_used(self, single_page_pdf_path):
        """Should return the DPI that was used."""
        from doc_assistant.tools.pdf_utils import render_page_with_size_limit

        result, dpi_used = render_page_with_size_limit(
            single_page_pdf_path, page_num=0, max_bytes=10 * 1024 * 1024
        )

        assert isinstance(dpi_used, int)
        assert dpi_used > 0

    def test_adapts_dpi_for_size_limit(self, single_page_pdf_path):
        """Should lower DPI if result exceeds size limit."""
        from doc_assistant.tools.pdf_utils import render_page_with_size_limit

        # Use very small size limit to force DPI reduction
        result, dpi_used = render_page_with_size_limit(
            single_page_pdf_path, page_num=0, max_bytes=1000  # Very small
        )

        # Should use lowest DPI possible
        assert dpi_used <= 72

    def test_result_size_within_limit(self, single_page_pdf_path):
        """Result should be within the specified size limit."""
        from doc_assistant.tools.pdf_utils import render_page_with_size_limit

        max_bytes = 50000  # 50KB
        result, dpi_used = render_page_with_size_limit(
            single_page_pdf_path, page_num=0, max_bytes=max_bytes
        )

        # Decoded size should be within limit (or as small as possible)
        decoded = base64.b64decode(result)
        # Note: It might still exceed if even lowest DPI exceeds limit
        # In that case, it should use lowest DPI
        assert len(decoded) <= max_bytes or dpi_used == 50
