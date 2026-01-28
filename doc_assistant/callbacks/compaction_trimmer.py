"""
Compaction content trimmer callback for before_model_callback.

This module provides a callback that trims accumulated compaction contents
based on character length threshold to prevent context bloat during
long conversations.

TODO: Replace character-based trimming with tokenizer-based calculation
for more accurate LLM context management.
"""

import logging
import os
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_COMPACTION_CHAR_THRESHOLD = 1000
COMPACTION_MARKER = "For context:"


def _get_compaction_char_threshold() -> int:
    """Get compaction character threshold from environment variable."""
    return int(
        os.getenv("COMPACTION_CHAR_THRESHOLD", DEFAULT_COMPACTION_CHAR_THRESHOLD)
    )


def _is_compaction_content(content: types.Content) -> bool:
    """Check if content is a compaction summary.

    Compaction contents have first part text equal to "For context:".
    """
    if not content or not content.parts:
        return False

    first_part = content.parts[0]
    return first_part.text == COMPACTION_MARKER


def _get_content_text_length(content: types.Content) -> int:
    """Get total text length of content."""
    total = 0
    for part in content.parts:
        if part.text:
            total += len(part.text)
    return total


def create_compaction_trimmer():
    """Create compaction content trimmer callback.

    Creates a before_model_callback that trims accumulated compaction contents
    based on character length threshold configured via COMPACTION_CHAR_THRESHOLD
    environment variable.

    Returns:
        Async callback function for before_model_callback.
    """

    async def trim_compaction_contents(
        callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """Trim accumulated compaction contents based on threshold.

        Args:
            callback_context: Callback context (unused).
            llm_request: LLM request with contents to modify.

        Returns:
            None to continue normal model call.
        """
        contents = llm_request.contents
        if not contents:
            return None

        # Find all compaction contents with their indices
        compaction_indices = [
            i for i, content in enumerate(contents) if _is_compaction_content(content)
        ]

        if len(compaction_indices) <= 1:
            return None

        threshold = _get_compaction_char_threshold()

        # Calculate lengths for each compaction content
        compaction_data = [
            (idx, _get_content_text_length(contents[idx])) for idx in compaction_indices
        ]

        total_length = sum(length for _, length in compaction_data)

        if total_length <= threshold:
            return None

        # Select from newest to oldest until threshold reached
        indices_to_keep = set()
        current_length = 0

        for idx, length in reversed(compaction_data):
            if current_length + length <= threshold:
                indices_to_keep.add(idx)
                current_length += length
            else:
                break

        indices_to_remove = set(compaction_indices) - indices_to_keep

        if not indices_to_remove:
            return None

        # Filter contents
        new_contents = [
            content for i, content in enumerate(contents) if i not in indices_to_remove
        ]

        logger.info(
            "Compaction trimmer: removed %d contents, total %d -> %d",
            len(indices_to_remove),
            len(contents),
            len(new_contents),
        )

        llm_request.contents = new_contents
        return None

    return trim_compaction_contents
