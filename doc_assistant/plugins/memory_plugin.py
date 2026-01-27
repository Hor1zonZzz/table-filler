"""Memory Plugin for automatic session-to-memory saving based on Invocation completion.

This plugin uses ADK's Plugin system to track Invocation completions and trigger
session saving after a configurable period of inactivity. This is more robust than
the previous approach of using LLM callbacks (before_model/after_model) because:

1. `after_run_callback` fires exactly once per user message (Invocation)
2. It fires after ALL processing is complete (LLM calls, tool executions, etc.)
3. It provides a clear signal of "activity" without timing ambiguities
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

from google.adk.plugins import BasePlugin

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.sessions import Session as AdkSession


logger = logging.getLogger(__name__)

SessionKey = tuple[str, str, str]  # (app_name, user_id, session_id)


@runtime_checkable
class _SupportsSessionProgress(Protocol):
    """Protocol for memory services that track incremental save progress."""

    def get_saved_event_count(self, app_name: str, user_id: str, session_id: str) -> int:
        """Return the number of session events already persisted."""

    def set_saved_event_count(
        self, app_name: str, user_id: str, session_id: str, count: int
    ) -> None:
        """Persist the number of session events that have been saved."""


@runtime_checkable
class _MemoryServiceProtocol(Protocol):
    """Protocol describing the memory service features used by the plugin."""

    async def add_session_to_memory(self, session: "AdkSession") -> None:
        """Persist session events to long-term memory."""


class MemoryPlugin(BasePlugin):
    """Plugin for automatic session-to-memory saving based on Invocation completion.

    This plugin resets a timer after each Invocation completes. When the timer fires
    (no new Invocation for the timeout period), the session is incrementally saved
    to long-term memory.

    Advantages over LLM callback-based approach:
    - Single point of timer reset per user message (not multiple resets per LLM call)
    - Timer only starts after ALL processing is complete
    - Works correctly with tool calls that don't involve LLM callbacks
    - Simpler and more predictable behavior
    """

    def __init__(
        self,
        name: str = "memory_plugin",
        timeout_seconds: int | None = None,
    ) -> None:
        """Initialize the memory plugin.

        Args:
            name: Plugin name (passed by ADK when instantiating via --extra_plugins).
            timeout_seconds: Seconds of inactivity before saving to memory.
                            Defaults to MEMORY_PLUGIN_TIMEOUT env var or 20 seconds.
        """
        super().__init__(name=name)

        if timeout_seconds is None:
            timeout_seconds = self._get_timeout_from_env()
        self._timeout_seconds = timeout_seconds

        # Track timers per session: {(app_name, user_id, session_id): asyncio.TimerHandle}
        self._timers: dict[SessionKey, asyncio.TimerHandle] = {}

        # Event loop reference (captured on first use)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info(
            "[MemoryPlugin] Initialized with timeout=%ss.",
            self._timeout_seconds,
        )

    @staticmethod
    def _get_timeout_from_env(default: int = 20) -> int:
        """Get timeout from environment variable."""
        raw_value = os.getenv("MEMORY_PLUGIN_TIMEOUT", str(default))
        try:
            return int(raw_value)
        except ValueError:
            logger.warning(
                "[MemoryPlugin] Invalid MEMORY_PLUGIN_TIMEOUT=%r, using default %ss.",
                raw_value,
                default,
            )
            return default

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or capture the event loop."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    async def after_run_callback(
        self, *, invocation_context: "InvocationContext"
    ) -> None:
        """Called after each Invocation completes.

        This is the ideal point to reset the inactivity timer because:
        1. All LLM calls for this user message are done
        2. All tool executions are done
        3. All events have been generated

        Args:
            invocation_context: The ADK invocation context.
        """
        # Extract identifiers
        session = invocation_context.session
        if session is None:
            logger.debug("[MemoryPlugin] No session in context, skipping.")
            return

        session_id = session.id
        user_id = session.user_id
        app_name = invocation_context.agent.name

        # Check if memory service is available
        memory_service = invocation_context.memory_service
        if memory_service is None:
            logger.debug("[MemoryPlugin] No memory_service available, skipping.")
            return

        session_service = invocation_context.session_service
        if session_service is None:
            logger.debug("[MemoryPlugin] No session_service available, skipping.")
            return

        key: SessionKey = (app_name, user_id, session_id)

        # Cancel existing timer for this session
        existing_timer = self._timers.get(key)
        if existing_timer is not None:
            existing_timer.cancel()

        # Set new timer
        loop = self._get_loop()
        self._timers[key] = loop.call_later(
            self._timeout_seconds,
            self._schedule_timeout_task,
            app_name,
            user_id,
            session_id,
            memory_service,
            session_service,
        )

        logger.info(
            "[MemoryPlugin] Timer reset for session %s... (%ss).",
            session_id[:8] if len(session_id) >= 8 else session_id,
            self._timeout_seconds,
        )

    def _schedule_timeout_task(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        memory_service: _MemoryServiceProtocol,
        session_service: object,
    ) -> None:
        """Schedule the async timeout handler without blocking the loop callback."""
        asyncio.create_task(
            self._on_timeout(app_name, user_id, session_id, memory_service, session_service)
        )

    def _get_saved_event_count(
        self,
        memory_service: _MemoryServiceProtocol,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> int:
        """Return the number of events already saved for a session, if supported."""
        if isinstance(memory_service, _SupportsSessionProgress):
            return memory_service.get_saved_event_count(app_name, user_id, session_id)
        return 0

    def _set_saved_event_count(
        self,
        memory_service: _MemoryServiceProtocol,
        app_name: str,
        user_id: str,
        session_id: str,
        count: int,
    ) -> None:
        """Persist the saved event count for a session, if supported."""
        if isinstance(memory_service, _SupportsSessionProgress):
            memory_service.set_saved_event_count(app_name, user_id, session_id, count)

    async def _on_timeout(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        memory_service: _MemoryServiceProtocol,
        session_service: object,
    ) -> None:
        """Handle a session timeout by saving new events incrementally.

        Args:
            app_name: The application name.
            user_id: The user ID.
            session_id: The session ID.
            memory_service: The memory service instance.
            session_service: The session service instance.
        """
        key: SessionKey = (app_name, user_id, session_id)
        self._timers.pop(key, None)

        try:
            # Get the session from the session service
            session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )

            if not session or not session.events:
                logger.debug(
                    "[MemoryPlugin] Session %s... has no events, skipping.",
                    session_id[:8] if len(session_id) >= 8 else session_id,
                )
                return

            # Check incremental progress
            saved_count = self._get_saved_event_count(
                memory_service, app_name, user_id, session_id
            )
            total_count = len(session.events)

            if saved_count >= total_count:
                logger.debug(
                    "[MemoryPlugin] Session %s... has no new events, skipping.",
                    session_id[:8] if len(session_id) >= 8 else session_id,
                )
                return

            # Extract only new events
            new_events = session.events[saved_count:]

            # Create partial session with only new events
            from google.adk.sessions import Session

            partial_session = Session(
                id=session.id,
                app_name=session.app_name,
                user_id=session.user_id,
                events=new_events,
                state=session.state,
            )

            # Save to memory
            await memory_service.add_session_to_memory(partial_session)

            # Update progress
            self._set_saved_event_count(
                memory_service, app_name, user_id, session_id, total_count
            )

            logger.info(
                "[MemoryPlugin] Saved %s new events to memory: session=%s... "
                "(total: %s, previously saved: %s).",
                len(new_events),
                session_id[:8] if len(session_id) >= 8 else session_id,
                total_count,
                saved_count,
            )

        except Exception:  # noqa: BLE001
            logger.exception(
                "[MemoryPlugin] Error saving session %s... to memory.",
                session_id[:8] if len(session_id) >= 8 else session_id,
            )

    async def close(self) -> None:
        """Cancel all pending timers and clean up resources."""
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
        logger.info("[MemoryPlugin] Closed, all timers cancelled.")
