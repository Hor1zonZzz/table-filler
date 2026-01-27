"""Tests for doc_assistant.services module."""

import os
from unittest.mock import patch

import pytest


class TestCreateSessionService:
    """Tests for create_session_service function."""

    def test_returns_in_memory_session_service_by_default(self):
        """Should return InMemorySessionService when storage type is MEMORY."""
        from google.adk.sessions import InMemorySessionService

        with patch.dict(os.environ, {"DOC_STORAGE_TYPE": "memory"}):
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            from doc_assistant.services import create_session_service

            service = create_session_service()
            assert isinstance(service, InMemorySessionService)

    def test_returns_database_session_service_for_sqlite(self):
        """Should return DatabaseSessionService when storage type is SQLITE."""
        from google.adk.sessions import DatabaseSessionService

        with patch.dict(
            os.environ,
            {
                "DOC_STORAGE_TYPE": "sqlite",
                "DOC_DATABASE_URL": "sqlite+aiosqlite:///./test.db",
            },
        ):
            import importlib
            import doc_assistant.config as config_module
            import doc_assistant.services as services_module
            importlib.reload(config_module)
            importlib.reload(services_module)

            service = services_module.create_session_service()
            assert isinstance(service, DatabaseSessionService)

    @pytest.mark.skip(reason="Requires asyncpg driver which is not installed")
    def test_returns_database_session_service_for_postgresql(self):
        """Should return DatabaseSessionService when storage type is POSTGRESQL."""
        from google.adk.sessions import DatabaseSessionService

        with patch.dict(
            os.environ,
            {
                "DOC_STORAGE_TYPE": "postgresql",
                "DOC_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            },
        ):
            import importlib
            import doc_assistant.config as config_module
            import doc_assistant.services as services_module
            importlib.reload(config_module)
            importlib.reload(services_module)

            service = services_module.create_session_service()
            assert isinstance(service, DatabaseSessionService)
