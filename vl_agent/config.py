"""VL Agent Configuration.

Manages configuration for storage and runtime settings.
"""

import os
from enum import Enum


class StorageType(Enum):
    """Supported storage types for session persistence."""

    MEMORY = "memory"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class Config:
    """VL Agent configuration from environment variables."""

    # Storage type (from env, defaults to memory)
    STORAGE_TYPE = os.getenv("VL_STORAGE_TYPE", "memory")

    # Database URL (for sqlite/postgresql)
    DATABASE_URL = os.getenv(
        "VL_DATABASE_URL", "sqlite+aiosqlite:///./vl_agent.db"
    )

    # App name for session management
    APP_NAME = "vl-table-extractor"
