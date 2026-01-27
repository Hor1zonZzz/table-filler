"""Tests for doc_assistant.agent module."""

import pytest


class TestRootAgent:
    """Tests for root_agent configuration."""

    def test_root_agent_exists(self):
        """Should have a root_agent defined."""
        from doc_assistant.agent import root_agent

        assert root_agent is not None

    def test_agent_has_correct_name(self):
        """Agent should have the correct name."""
        from doc_assistant.agent import root_agent

        assert root_agent.name == "doc_assistant"

    def test_agent_has_read_document_tool(self):
        """Agent should have read_document tool available."""
        from doc_assistant.agent import root_agent

        tool_names = [t.name if hasattr(t, "name") else t.__name__ for t in root_agent.tools]
        assert "read_document" in tool_names

    def test_agent_has_instruction(self):
        """Agent should have an instruction/system prompt."""
        from doc_assistant.agent import root_agent

        assert root_agent.instruction is not None
        assert len(root_agent.instruction) > 0

    def test_instruction_mentions_document(self):
        """Agent instruction should mention document handling."""
        from doc_assistant.agent import root_agent

        instruction_lower = root_agent.instruction.lower()
        assert "document" in instruction_lower or "文档" in instruction_lower


class TestModel:
    """Tests for model configuration."""

    def test_model_is_configured(self):
        """Should have a model configured."""
        from doc_assistant.agent import model

        assert model is not None
