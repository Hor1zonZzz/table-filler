"""Memory-related callbacks for the Document Assistant agent.

NOTE: Session monitoring is now handled by MemoryPlugin (see plugins/memory_plugin.py).
This module retains only utility functions for debugging and manual memory operations.
"""

from __future__ import annotations

import logging
from typing import Any

from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)


def _extract_user_query(callback_context: CallbackContext) -> str | None:
    """Best-effort extraction of the user's text query from the callback context."""
    user_content = callback_context.user_content
    if not user_content or not user_content.parts:
        return None

    first_part = user_content.parts[0]
    return getattr(first_part, "text", None)


async def debug_before_model(callback_context: CallbackContext, llm_request: Any) -> None:
    """Debug callback that logs memory search results before model calls.

    This callback is optional and can be used for debugging memory retrieval.
    To use it, add `before_model_callback=debug_before_model` to the agent.

    Args:
        callback_context: The ADK callback context.
        llm_request: The outbound LLM request (unused, but part of the contract).
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return

    user_query = _extract_user_query(callback_context)
    if not user_query:
        logger.debug("[BeforeModel] No user query available.")
        return

    logger.debug("[BeforeModel] Callback triggered.")
    logger.debug("[BeforeModel] User query: %s...", user_query[:100])

    try:
        inv_ctx = callback_context._invocation_context  # noqa: SLF001
        memory_service = inv_ctx.memory_service
        if not memory_service:
            logger.debug("[BeforeModel] No memory_service available.")
            return

        app_name = inv_ctx.agent.name
        user_id = callback_context.user_id
        response = await memory_service.search_memory(
            app_name=app_name,
            user_id=user_id,
            query=user_query,
        )
        count = len(response.memories) if response.memories else 0
        logger.debug("[BeforeModel] Search results: %s memories found.", count)

        if not response.memories:
            return

        for index, memory in enumerate(response.memories):
            author = getattr(memory, "author", "N/A")
            content = getattr(memory, "content", None)
            preview = (
                content.parts[0].text[:80]
                if content and getattr(content, "parts", None)
                else "N/A"
            )
            logger.debug(
                "[BeforeModel] Memory %s: author=%s, text=%s...",
                index,
                author,
                preview,
            )
    except Exception:  # noqa: BLE001
        logger.exception("[BeforeModel] Error searching memory.")


async def save_session_to_memory(callback_context: CallbackContext) -> None:
    """Manually save the current session to memory.

    This function can be called to immediately save the session, bypassing
    the normal inactivity timer. Useful for explicit save triggers.

    Args:
        callback_context: The ADK callback context.
    """
    session_id = callback_context.session.id
    logger.info("Manual save triggered for session %s.", session_id)
    await callback_context.add_session_to_memory()
    logger.info("Session %s saved to memory.", session_id)
