"""Custom service registration for Document Assistant.

This module registers custom services that can be used with adk web:
- SqliteMemoryService: Persistent memory storage using SQLite

Usage:
    adk web doc_assistant --memory_service_uri sqlite:///./data/memory.db

Note: Session-to-memory saving is handled by MemoryPlugin.
      Use --extra_plugins "doc_assistant.plugins.MemoryPlugin" to enable.
"""

import logging
import os
from pathlib import Path

from google.adk.cli.service_registry import get_service_registry

logger = logging.getLogger(__name__)


def sqlite_memory_factory(uri: str, **kwargs):
    """Factory function for SqliteMemoryService.

    Args:
        uri: SQLite URI in format "sqlite:///path/to/db" or "sqlite:///:memory:"

    Returns:
        SqliteMemoryService instance.
    """
    from doc_assistant.memory import SqliteMemoryService

    # Parse the URI to extract the database path
    # Format: sqlite:///path/to/db or sqlite:///:memory:
    if uri.startswith("sqlite:///"):
        db_path = uri[len("sqlite:///"):]
        if db_path == ":memory:":
            db_path = ":memory:"
        else:
            # Ensure directory exists
            db_dir = Path(db_path).parent
            if db_dir and str(db_dir) != ".":
                db_dir.mkdir(parents=True, exist_ok=True)
    else:
        db_path = "memory.db"

    top_k = int(os.environ.get("MEMORY_SEARCH_TOP_K", "20"))
    logger.info(f"Creating SqliteMemoryService with db_path: {db_path}, top_k: {top_k}")
    return SqliteMemoryService(db_path=db_path, top_k=top_k)


# Register the custom memory service
registry = get_service_registry()
registry.register_memory_service("sqlite", sqlite_memory_factory)

logger.info("Registered SqliteMemoryService for 'sqlite://' URIs")
