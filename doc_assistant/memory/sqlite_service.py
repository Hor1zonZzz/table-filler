"""SQLite-based Memory Service for persistent long-term memory storage."""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, TypedDict

from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions import Session
from google.genai import types

logger = logging.getLogger(__name__)


class MemoryRecord(TypedDict):
    """Debug-friendly representation of a memory row."""

    id: int
    session_id: str
    author: str | None
    content: str
    timestamp: str | None
    created_at: str


ConnectionFactory = Callable[[], sqlite3.Connection]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class _SqliteConfig:
    """Configuration for the SQLite memory service."""

    db_path: str
    connection_factory: ConnectionFactory
    clock: Clock
    top_k: int


def _default_clock() -> datetime:
    """Return the current time."""
    return datetime.now()


def _build_connection_factory(db_path: str) -> ConnectionFactory:
    """Create a simple connection factory for the given database path."""
    return lambda: sqlite3.connect(db_path)


class SqliteMemoryService(BaseMemoryService):
    """SQLite-based memory service for persistent long-term memory storage.

    This service stores memory entries in a SQLite database, supporting:
    - Persistent storage across restarts
    - Keyword-based search (supports both English and Chinese)
    - Thread-safe operations
    """

    def __init__(
        self,
        db_path: str = "memory.db",
        *,
        connection_factory: ConnectionFactory | None = None,
        clock: Clock = _default_clock,
        top_k: int = 20,
    ) -> None:
        """Initialize the SQLite memory service.

        Args:
            db_path: Path to the SQLite database file.
            connection_factory: Optional factory for SQLite connections.
            clock: Injectable clock used for timestamps (test-friendly).
            top_k: Maximum number of memories returned by search_memory.
                   Values <= 0 disable the limit.
        """
        factory = connection_factory or _build_connection_factory(db_path)
        self._config = _SqliteConfig(
            db_path=db_path,
            connection_factory=factory,
            clock=clock,
            top_k=top_k,
        )
        self._lock = threading.Lock()
        self._init_db()

    @property
    def _db_path(self) -> str:
        """Return the configured database path."""
        return self._config.db_path

    def _connect(self) -> sqlite3.Connection:
        """Create a new database connection."""
        try:
            return self._config.connection_factory()
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            logger.exception("Failed to create SQLite connection.")
            raise RuntimeError("Unable to create SQLite connection.") from exc

    def _ensure_parent_dir(self) -> None:
        """Ensure the database parent directory exists."""
        db_dir = Path(self._db_path).parent
        if not db_dir:
            return
        if db_dir.exists():
            return
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self._ensure_parent_dir()

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_name TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        author TEXT,
                        content TEXT NOT NULL,
                        timestamp TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(app_name, user_id, session_id, content)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memories_user
                    ON memories(app_name, user_id)
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_save_progress (
                        app_name TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        saved_event_count INTEGER NOT NULL DEFAULT 0,
                        last_saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (app_name, user_id, session_id)
                    )
                    """
                )
                conn.commit()
        except sqlite3.Error as exc:
            logger.exception("Failed to initialize SQLite schema.")
            raise RuntimeError("Unable to initialize SQLite schema.") from exc

    def _extract_words(self, text: str) -> set[str]:
        """Extract words from text, supporting both English and Chinese.

        Args:
            text: The text to extract words from.

        Returns:
            A set of extracted words (lowercase for English).
        """
        english_words = set(re.findall(r"[A-Za-z]+", text.lower()))
        chinese_chars = set(re.findall(r"[\u4e00-\u9fff]", text))
        return english_words | chinese_chars

    def _iter_event_texts(self, session: Session) -> Iterable[tuple[str | None, str, str]]:
        """Yield (author, content, timestamp_iso) tuples from a session."""
        if not session.events:
            return

        for event in session.events:
            if not event.content or not event.content.parts:
                continue

            text_parts = [
                part.text
                for part in event.content.parts
                if hasattr(part, "text") and part.text
            ]
            if not text_parts:
                continue

            content = " ".join(text_parts)
            if event.timestamp:
                if isinstance(event.timestamp, float):
                    timestamp = datetime.fromtimestamp(event.timestamp).isoformat()
                else:
                    timestamp = event.timestamp.isoformat()
            else:
                timestamp = self._config.clock().isoformat()
            yield event.author, content, timestamp

    async def add_session_to_memory(self, session: Session) -> None:
        """Add session events to long-term memory.

        Args:
            session: The session containing events to store.
        """
        if not session.events:
            return

        with self._lock:
            try:
                with self._connect() as conn:
                    for author, content, timestamp in self._iter_event_texts(session):
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO memories
                            (app_name, user_id, session_id, author, content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                session.app_name,
                                session.user_id,
                                session.id,
                                author,
                                content,
                                timestamp,
                            ),
                        )
                    conn.commit()
            except sqlite3.Error as exc:
                logger.exception(
                    "Failed to add session to memory: app=%s user=%s session=%s.",
                    session.app_name,
                    session.user_id,
                    session.id,
                )
                raise RuntimeError("Unable to persist session memory.") from exc

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> "SearchMemoryResponse":
        """Search for memories matching the query.

        Args:
            app_name: The application name.
            user_id: The user ID.
            query: The search query.

        Returns:
            SearchMemoryResponse containing matching memories.
        """
        from google.adk.memory.base_memory_service import SearchMemoryResponse

        query_words = self._extract_words(query)
        if not query_words:
            return SearchMemoryResponse()

        response = SearchMemoryResponse()

        with self._lock:
            try:
                with self._connect() as conn:
                    cursor = conn.execute(
                        """
                        SELECT author, content, timestamp
                        FROM memories
                        WHERE app_name = ? AND user_id = ?
                        ORDER BY created_at DESC
                        """,
                        (app_name, user_id),
                    )

                    for author, content, timestamp in cursor.fetchall():
                        content_words = self._extract_words(content)
                        if not any(qw in content_words for qw in query_words):
                            continue

                        memory_content = types.Content(
                            parts=[types.Part(text=content)],
                            role="user" if author == "user" else "model",
                        )
                        response.memories.append(
                            MemoryEntry(content=memory_content, author=author, timestamp=timestamp)
                        )
                        if self._config.top_k > 0 and len(response.memories) >= self._config.top_k:
                            break
            except sqlite3.Error as exc:
                logger.exception("Failed to search memory: app=%s user=%s.", app_name, user_id)
                raise RuntimeError("Unable to search memory.") from exc

        return response

    def get_all_memories(self, app_name: str, user_id: str) -> list[MemoryRecord]:
        """Get all memories for a user (for debugging).

        Args:
            app_name: The application name.
            user_id: The user ID.

        Returns:
            List of memory records.
        """
        with self._lock:
            try:
                with self._connect() as conn:
                    cursor = conn.execute(
                        """
                        SELECT id, session_id, author, content, timestamp, created_at
                        FROM memories
                        WHERE app_name = ? AND user_id = ?
                        ORDER BY created_at DESC
                        """,
                        (app_name, user_id),
                    )

                    rows = cursor.fetchall()
            except sqlite3.Error as exc:
                logger.exception("Failed to load memories: app=%s user=%s.", app_name, user_id)
                raise RuntimeError("Unable to load memories.") from exc

        return [
            MemoryRecord(
                id=row[0],
                session_id=row[1],
                author=row[2],
                content=row[3],
                timestamp=row[4],
                created_at=row[5],
            )
            for row in rows
        ]

    def clear_memories(self, app_name: str, user_id: str) -> int:
        """Clear all memories for a user.

        Args:
            app_name: The application name.
            user_id: The user ID.

        Returns:
            Number of deleted records.
        """
        with self._lock:
            try:
                with self._connect() as conn:
                    cursor = conn.execute(
                        """
                        DELETE FROM memories
                        WHERE app_name = ? AND user_id = ?
                        """,
                        (app_name, user_id),
                    )
                    conn.commit()
                    return int(cursor.rowcount)
            except sqlite3.Error as exc:
                logger.exception("Failed to clear memories: app=%s user=%s.", app_name, user_id)
                raise RuntimeError("Unable to clear memories.") from exc

    def get_saved_event_count(self, app_name: str, user_id: str, session_id: str) -> int:
        """Get the number of events already saved for a session.

        Args:
            app_name: The application name.
            user_id: The user ID.
            session_id: The session ID.

        Returns:
            Number of events already saved (0 if not found).
        """
        with self._lock:
            try:
                with self._connect() as conn:
                    cursor = conn.execute(
                        """
                        SELECT saved_event_count FROM session_save_progress
                        WHERE app_name = ? AND user_id = ? AND session_id = ?
                        """,
                        (app_name, user_id, session_id),
                    )
                    row = cursor.fetchone()
            except sqlite3.Error as exc:
                logger.exception(
                    "Failed to get saved event count: app=%s user=%s session=%s.",
                    app_name,
                    user_id,
                    session_id,
                )
                raise RuntimeError("Unable to read session save progress.") from exc

        return int(row[0]) if row else 0

    def set_saved_event_count(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        count: int,
    ) -> None:
        """Update the saved event count for a session.

        Args:
            app_name: The application name.
            user_id: The user ID.
            session_id: The session ID.
            count: The new count of saved events.
        """
        with self._lock:
            try:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO session_save_progress
                        (app_name, user_id, session_id, saved_event_count, last_saved_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(app_name, user_id, session_id)
                        DO UPDATE SET
                            saved_event_count = excluded.saved_event_count,
                            last_saved_at = CURRENT_TIMESTAMP
                        """,
                        (app_name, user_id, session_id, count),
                    )
                    conn.commit()
            except sqlite3.Error as exc:
                logger.exception(
                    "Failed to set saved event count: app=%s user=%s session=%s count=%s.",
                    app_name,
                    user_id,
                    session_id,
                    count,
                )
                raise RuntimeError("Unable to update session save progress.") from exc
