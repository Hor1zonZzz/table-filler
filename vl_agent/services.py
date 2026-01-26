"""VL Agent Services.

Factory functions for creating ADK services based on configuration.
"""

from google.adk.sessions import DatabaseSessionService, InMemorySessionService

from .config import Config, StorageType


def create_session_service():
    """Create SessionService based on configuration.

    Returns:
        SessionService instance (InMemorySessionService or DatabaseSessionService)

    Raises:
        ValueError: If storage type is not supported
    """
    storage_type = Config.STORAGE_TYPE

    if storage_type == StorageType.MEMORY.value:
        return InMemorySessionService()

    elif storage_type in [StorageType.SQLITE.value, StorageType.POSTGRESQL.value]:
        return DatabaseSessionService(db_url=Config.DATABASE_URL)

    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
