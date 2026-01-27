"""Session monitor using delayed tasks for auto-saving inactive sessions.

This implementation uses event-driven delayed tasks instead of polling:
1. Each session activity resets a timer.
2. When the timer fires (no activity for the timeout period), the session is
   saved to memory incrementally.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from google.adk.sessions import Session as AdkSession
    from google.adk.sessions.base_session_service import BaseSessionService

logger = logging.getLogger(__name__)

SessionKey = tuple[str, str]


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
    """Protocol describing the memory service features used by the monitor."""

    async def add_session_to_memory(self, session: "AdkSession") -> None:
        """Persist session events to long-term memory."""


class SessionMonitor:
    """Monitor sessions for inactivity using delayed tasks.

    Instead of polling, this uses a timer per session:
    1. ``on_activity`` resets the timer.
    2. The timer fires after the timeout and saves only new events.
    """

    def __init__(
        self,
        session_service: "BaseSessionService",
        memory_service: _MemoryServiceProtocol,
        app_name: str,
        timeout_seconds: int = 300,
    ) -> None:
        """Initialize the session monitor.

        Args:
            session_service: The session service to get sessions from.
            memory_service: The memory service to save sessions to.
            app_name: The application name.
            timeout_seconds: Seconds of inactivity before saving to memory.
        """
        self._session_service = session_service
        self._memory_service = memory_service
        self._app_name = app_name
        self._timeout = timeout_seconds

        # Track timers per session: {(user_id, session_id): asyncio.TimerHandle}.
        self._timers: dict[SessionKey, asyncio.TimerHandle] = {}

        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        """Start the monitor by capturing the running event loop."""
        self._running = True
        self._loop = asyncio.get_event_loop()
        logger.info("SessionMonitor started: timeout=%ss.", self._timeout)

    async def stop(self) -> None:
        """Stop the monitor and cancel all pending timers."""
        self._running = False
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
        logger.info("SessionMonitor stopped.")

    def on_activity(self, user_id: str, session_id: str) -> None:
        """Reset the inactivity timer for a session.

        Args:
            user_id: The user ID.
            session_id: The session ID.
        """
        if not self._running or self._loop is None:
            return

        key: SessionKey = (user_id, session_id)

        existing_timer = self._timers.get(key)
        if existing_timer is not None:
            existing_timer.cancel()

        self._timers[key] = self._loop.call_later(
            self._timeout,
            self._schedule_timeout_task,
            user_id,
            session_id,
        )
        logger.debug("Timer reset for session %s... (%ss).", session_id[:8], self._timeout)

    def _schedule_timeout_task(self, user_id: str, session_id: str) -> None:
        """Schedule the timeout coroutine without blocking the loop callback."""
        asyncio.create_task(self._on_timeout(user_id, session_id))

    def _get_saved_event_count(self, user_id: str, session_id: str) -> int:
        """Return the number of events already saved for a session, if supported."""
        if isinstance(self._memory_service, _SupportsSessionProgress):
            return self._memory_service.get_saved_event_count(self._app_name, user_id, session_id)
        return 0

    def _set_saved_event_count(self, user_id: str, session_id: str, count: int) -> None:
        """Persist the saved event count for a session, if supported."""
        if isinstance(self._memory_service, _SupportsSessionProgress):
            self._memory_service.set_saved_event_count(self._app_name, user_id, session_id, count)

    async def _on_timeout(self, user_id: str, session_id: str) -> None:
        """Handle a session timeout by saving new events incrementally.

        Args:
            user_id: The user ID.
            session_id: The session ID.
        """
        key: SessionKey = (user_id, session_id)
        self._timers.pop(key, None)

        try:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
            )

            if not session or not session.events:
                logger.debug("Session %s... has no events, skipping.", session_id[:8])
                return

            saved_count = self._get_saved_event_count(user_id, session_id)
            total_count = len(session.events)

            if saved_count >= total_count:
                logger.debug("Session %s... has no new events, skipping.", session_id[:8])
                return

            new_events = session.events[saved_count:]

            # Import locally to avoid import-time side effects and reduce coupling.
            from google.adk.sessions import Session

            partial_session = Session(
                id=session.id,
                app_name=session.app_name,
                user_id=session.user_id,
                events=new_events,
                state=session.state,
            )

            await self._memory_service.add_session_to_memory(partial_session)
            self._set_saved_event_count(user_id, session_id, total_count)

            logger.info(
                (
                    "[SessionMonitor] Saved %s new events to memory: session=%s... "
                    "(total: %s, previously saved: %s)"
                ),
                len(new_events),
                session_id[:8],
                total_count,
                saved_count,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Error saving session %s... to memory.", session_id[:8])


# Global monitor instance.
_monitor: Optional[SessionMonitor] = None


def get_monitor() -> Optional[SessionMonitor]:
    """Return the global session monitor instance, if it has been set."""
    return _monitor


def set_monitor(monitor: SessionMonitor) -> None:
    """Set the global session monitor instance."""
    global _monitor
    _monitor = monitor

