"""Memory module for Document Assistant.

This module provides:
- SqliteMemoryService: Persistent SQLite-based memory storage
- debug_before_model: Optional debug callback for memory search logging
- save_session_to_memory: Utility for manual session saving

NOTE: Automatic session-to-memory saving is handled by MemoryPlugin
(see doc_assistant/plugins/memory_plugin.py). The SessionMonitor class
is retained for backwards compatibility but is not actively used.
"""

from .callbacks import debug_before_model, save_session_to_memory
from .sqlite_service import SqliteMemoryService

__all__ = [
    "debug_before_model",
    "save_session_to_memory",
    "SqliteMemoryService",
]
