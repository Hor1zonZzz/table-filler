"""Memory-related callbacks for the Document Assistant agent."""

from __future__ import annotations

import logging
import os
from typing import Any

from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

# Global flag to track if monitor has been initialized.
_monitor_initialized = False


def _is_session_monitor_enabled() -> bool:
    """Return whether the session monitor is enabled via environment variable."""
    return os.getenv("SESSION_MONITOR_ENABLED", "false").lower() == "true"


def _get_session_monitor_timeout(default: int = 300) -> int:
    """Return the configured session monitor timeout in seconds."""
    raw_value = os.getenv("SESSION_MONITOR_TIMEOUT", str(default))
    try:
        return int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SESSION_MONITOR_TIMEOUT=%r, falling back to %s seconds.",
            raw_value,
            default,
        )
        return default


async def _ensure_session_monitor_started(callback_context: CallbackContext) -> None:
    """Lazily start the session monitor on first invocation.

    This function is intentionally defensive. Any startup failure is logged and
    treated as a one-time initialization attempt to avoid repeated failures.
    """
    global _monitor_initialized

    if _monitor_initialized:
        return

    if not _is_session_monitor_enabled():
        _monitor_initialized = True
        return

    try:
        from .session_monitor import SessionMonitor, get_monitor, set_monitor

        if get_monitor() is not None:
            _monitor_initialized = True
            return

        # NOTE: The ADK exposes services via the invocation context. We avoid
        # importing these types at module import time to keep import side
        # effects minimal and to reduce coupling.
        inv_ctx = callback_context._invocation_context  # noqa: SLF001
        session_service = inv_ctx.session_service
        memory_service = inv_ctx.memory_service

        if not session_service or not memory_service:
            logger.warning("Cannot start SessionMonitor: missing services.")
            _monitor_initialized = True
            return

        timeout = _get_session_monitor_timeout()
        app_name = inv_ctx.agent.name

        monitor = SessionMonitor(
            session_service=session_service,
            memory_service=memory_service,
            app_name=app_name,
            timeout_seconds=timeout,
        )
        set_monitor(monitor)
        await monitor.start()

        logger.info("SessionMonitor started: app=%s, timeout=%ss.", app_name, timeout)
        _monitor_initialized = True
    except Exception:  # noqa: BLE001
        # We keep behavior consistent with the previous implementation by not
        # surfacing errors to the caller, but we make failures explicit.
        logger.exception("Failed to start SessionMonitor.")
        _monitor_initialized = True


def _notify_session_activity(callback_context: CallbackContext) -> None:
    """Notify the monitor of session activity to reset the inactivity timer."""
    from .session_monitor import get_monitor

    monitor = get_monitor()
    if monitor is None:
        return

    monitor.on_activity(
        user_id=callback_context.user_id,
        session_id=callback_context.session.id,
    )


def _extract_user_query(callback_context: CallbackContext) -> str | None:
    """Best-effort extraction of the user's text query from the callback context."""
    user_content = callback_context.user_content
    if not user_content or not user_content.parts:
        return None

    first_part = user_content.parts[0]
    return getattr(first_part, "text", None)


async def debug_before_model(callback_context: CallbackContext, llm_request: Any) -> None:
    """Debug callback that runs before each model call.

    Args:
        callback_context: The ADK callback context.
        llm_request: The outbound LLM request (unused, but part of the contract).
    """
    # Start session monitor if enabled.
    await _ensure_session_monitor_started(callback_context)

    # Notify activity (resets the inactivity timer).
    _notify_session_activity(callback_context)

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
        # Keep failures visible but do not break the request path.
        logger.exception("[BeforeModel] Error searching memory.")


async def after_model_callback(callback_context: CallbackContext, llm_response: Any) -> None:
    """Callback that runs after each model call to reset the inactivity timer.

    This ensures that model responses also trigger timer resets, preventing
    the timer from firing during long-running LLM calls.
    """
    _notify_session_activity(callback_context)


async def save_session_to_memory(callback_context: CallbackContext) -> None:
    """Manually save the session to memory when the flag is set.

    Set ``state['save_to_memory'] = True`` to trigger this callback.
    """
    await _ensure_session_monitor_started(callback_context)
    _notify_session_activity(callback_context)

    should_save = bool(callback_context.state.get("save_to_memory", False))
    if not should_save:
        return

    session_id = callback_context.session.id
    logger.info("Manual save triggered for session %s.", session_id)
    await callback_context.add_session_to_memory()
    callback_context.state["save_to_memory"] = False
    logger.info("Session %s saved to memory.", session_id)
