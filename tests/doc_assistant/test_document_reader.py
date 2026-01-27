"""Tests for doc_assistant.tools.document_reader module."""

import base64
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest


# Fixtures
@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file for testing."""
    pdf_path = tempfile.mktemp(suffix=".pdf")
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), f"Test Page {i + 1}", fontsize=24)
    doc.save(pdf_path)
    doc.close()
    yield pdf_path
    if os.path.exists(pdf_path):
        os.unlink(pdf_path)


@pytest.fixture
def sample_image_path():
    """Create a sample PNG image for testing."""
    img_path = tempfile.mktemp(suffix=".png")
    # Create a simple image using PyMuPDF
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((50, 100), "Test Image", fontsize=16)
    pix = page.get_pixmap()
    pix.save(img_path)
    doc.close()
    yield img_path
    if os.path.exists(img_path):
        os.unlink(img_path)


# Test classes
class TestSupportedImageFormats:
    """Tests for SUPPORTED_IMAGE_FORMATS constant."""

    def test_includes_common_formats(self):
        """Should include common image formats."""
        from doc_assistant.tools.document_reader import SUPPORTED_IMAGE_FORMATS

        assert ".png" in SUPPORTED_IMAGE_FORMATS
        assert ".jpg" in SUPPORTED_IMAGE_FORMATS
        assert ".jpeg" in SUPPORTED_IMAGE_FORMATS


class TestValidateImagePath:
    """Tests for validate_image_path function."""

    def test_valid_image_path(self, sample_image_path):
        """Should return True for valid image path."""
        from doc_assistant.tools.document_reader import validate_image_path

        is_valid, message = validate_image_path(sample_image_path)
        assert is_valid is True
        assert message == ""

    def test_nonexistent_file(self):
        """Should return False for non-existent file."""
        from doc_assistant.tools.document_reader import validate_image_path

        is_valid, message = validate_image_path("/nonexistent/image.png")
        assert is_valid is False
        assert "not found" in message.lower() or "exist" in message.lower()

    def test_unsupported_format(self, sample_pdf_path):
        """Should return False for unsupported format."""
        from doc_assistant.tools.document_reader import validate_image_path

        is_valid, message = validate_image_path(sample_pdf_path)
        assert is_valid is False
        assert "supported" in message.lower() or "format" in message.lower()


class TestLoadImageAsBase64:
    """Tests for load_image_as_base64 function."""

    def test_returns_base64_string(self, sample_image_path):
        """Should return base64 encoded string."""
        from doc_assistant.tools.document_reader import load_image_as_base64

        result = load_image_as_base64(sample_image_path)
        assert isinstance(result, str)
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_raises_for_nonexistent_file(self):
        """Should raise error for non-existent file."""
        from doc_assistant.tools.document_reader import load_image_as_base64

        with pytest.raises(FileNotFoundError):
            load_image_as_base64("/nonexistent/image.png")


class TestDetectFileType:
    """Tests for detect_file_type function."""

    def test_detects_pdf(self, sample_pdf_path):
        """Should detect PDF files."""
        from doc_assistant.tools.document_reader import detect_file_type

        result = detect_file_type(sample_pdf_path)
        assert result == "pdf"

    def test_detects_image(self, sample_image_path):
        """Should detect image files."""
        from doc_assistant.tools.document_reader import detect_file_type

        result = detect_file_type(sample_image_path)
        assert result == "image"

    def test_returns_unknown_for_other_types(self):
        """Should return 'unknown' for unsupported types."""
        from doc_assistant.tools.document_reader import detect_file_type

        result = detect_file_type("/path/to/file.txt")
        assert result == "unknown"


class TestReadDocument:
    """Tests for read_document tool function."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock ToolContext."""
        ctx = MagicMock()
        ctx.state = {}
        return ctx

    @pytest.fixture
    def mock_vl_response(self):
        """Create a mock VL API response."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is the extracted content."))
        ]
        return mock_response

    async def test_reads_pdf_successfully(
        self, mock_tool_context, sample_pdf_path, mock_vl_response
    ):
        """Should read PDF and return answer."""
        from doc_assistant.tools.document_reader import read_document

        with patch(
            "doc_assistant.tools.document_reader._call_vl_model",
            new_callable=AsyncMock,
            return_value="This is the extracted content.",
        ):
            result = await read_document(
                mock_tool_context,
                file_path=sample_pdf_path,
                question="What is the content?",
            )

        assert result["status"] == "success"
        assert "answer" in result
        assert result["file_type"] == "pdf"
        assert "pages_read" in result

    async def test_reads_specific_pages(
        self, mock_tool_context, sample_pdf_path, mock_vl_response
    ):
        """Should read only specified pages."""
        from doc_assistant.tools.document_reader import read_document

        with patch(
            "doc_assistant.tools.document_reader._call_vl_model",
            new_callable=AsyncMock,
            return_value="Content from pages 1 and 3.",
        ):
            result = await read_document(
                mock_tool_context,
                file_path=sample_pdf_path,
                question="What is on pages 1 and 3?",
                pages=[1, 3],  # 1-indexed
            )

        assert result["status"] == "success"
        assert result["pages_read"] == [1, 3]

    async def test_reads_image_successfully(
        self, mock_tool_context, sample_image_path, mock_vl_response
    ):
        """Should read image and return answer."""
        from doc_assistant.tools.document_reader import read_document

        with patch(
            "doc_assistant.tools.document_reader._call_vl_model",
            new_callable=AsyncMock,
            return_value="Image content description.",
        ):
            result = await read_document(
                mock_tool_context,
                file_path=sample_image_path,
                question="Describe this image.",
            )

        assert result["status"] == "success"
        assert result["file_type"] == "image"
        assert "answer" in result

    async def test_returns_error_for_nonexistent_file(self, mock_tool_context):
        """Should return error for non-existent file."""
        from doc_assistant.tools.document_reader import read_document

        result = await read_document(
            mock_tool_context,
            file_path="/nonexistent/file.pdf",
            question="What is this?",
        )

        assert result["status"] == "error"
        assert "message" in result

    async def test_returns_error_for_unsupported_format(self, mock_tool_context):
        """Should return error for unsupported file format."""
        from doc_assistant.tools.document_reader import read_document

        result = await read_document(
            mock_tool_context,
            file_path="/path/to/file.txt",
            question="What is this?",
        )

        assert result["status"] == "error"
        assert "message" in result
        assert "supported" in result["message"].lower() or "format" in result["message"].lower()

    async def test_handles_invalid_page_numbers(
        self, mock_tool_context, sample_pdf_path
    ):
        """Should handle invalid page numbers gracefully."""
        from doc_assistant.tools.document_reader import read_document

        result = await read_document(
            mock_tool_context,
            file_path=sample_pdf_path,
            question="What is on page 100?",
            pages=[100],  # Invalid page
        )

        assert result["status"] == "error"
        assert "message" in result


class TestCallVlModel:
    """Tests for _call_vl_model helper function."""

    async def test_constructs_correct_message_format(self):
        """Should construct correct message format for VL API."""
        from doc_assistant.tools.document_reader import _call_vl_model

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Response text"))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "doc_assistant.tools.document_reader._get_vl_client",
            return_value=mock_client,
        ):
            result = await _call_vl_model(
                question="Test question",
                images_base64=["base64image1", "base64image2"],
            )

        # Verify the call was made
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args

        # Check message structure
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

        # Content should have text and images
        content = messages[0]["content"]
        assert any(c["type"] == "text" for c in content)
        assert sum(1 for c in content if c["type"] == "image_url") == 2

    async def test_returns_model_response(self):
        """Should return the model's response text."""
        from doc_assistant.tools.document_reader import _call_vl_model

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="The answer is 42."))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "doc_assistant.tools.document_reader._get_vl_client",
            return_value=mock_client,
        ):
            result = await _call_vl_model(
                question="What is the answer?",
                images_base64=["somebase64"],
            )

        assert result == "The answer is 42."
