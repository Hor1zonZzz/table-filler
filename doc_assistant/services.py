"""Custom service registration for Document Assistant.

This module registers custom services that can be used with adk web:
- SqliteMemoryService: Persistent memory storage using SQLite

Usage:
    adk web doc_assistant --memory_service_uri sqlite:///./data/memory.db
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

    logger.info(f"Creating SqliteMemoryService with db_path: {db_path}")
    return SqliteMemoryService(db_path=db_path)


# Register the custom memory service
registry = get_service_registry()
registry.register_memory_service("sqlite", sqlite_memory_factory)

logger.info("Registered SqliteMemoryService for 'sqlite://' URIs")


# ============================================================
# Session Monitor Auto-Start (via environment variables)
# ============================================================

def _maybe_start_session_monitor():
    """Start session monitor if configured via environment variables.

    Environment variables:
        SESSION_MONITOR_ENABLED: Set to "true" to enable (default: false)
        SESSION_MONITOR_TIMEOUT: Inactivity timeout in seconds (default: 300)
        SESSION_MONITOR_INTERVAL: Check interval in seconds (default: 60)
    """
    enabled = os.getenv("SESSION_MONITOR_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.debug("Session monitor is disabled (set SESSION_MONITOR_ENABLED=true to enable)")
        return

    # Session monitor will be started lazily when first invocation happens
    # because we don't have access to session_service and memory_service here
    logger.info(
        "Session monitor is enabled. It will start on first agent invocation. "
        f"Timeout: {os.getenv('SESSION_MONITOR_TIMEOUT', '300')}s, "
        f"Interval: {os.getenv('SESSION_MONITOR_INTERVAL', '60')}s"
    )


_maybe_start_session_monitor()
