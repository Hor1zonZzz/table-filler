"""Tests for doc_assistant.main module."""

import pytest


class TestMainModule:
    """Tests for main module structure."""

    def test_main_function_exists(self):
        """Should have a main async function."""
        from doc_assistant.main import main

        assert main is not None
        assert callable(main)

    def test_welcome_message_defined(self):
        """Should have a welcome message constant."""
        from doc_assistant.main import WELCOME_MESSAGE

        assert WELCOME_MESSAGE is not None
        assert len(WELCOME_MESSAGE) > 0

    def test_welcome_message_has_instructions(self):
        """Welcome message should have usage instructions."""
        from doc_assistant.main import WELCOME_MESSAGE

        msg_lower = WELCOME_MESSAGE.lower()
        # Should mention PDF or document
        assert "pdf" in msg_lower or "document" in msg_lower or "文档" in msg_lower
