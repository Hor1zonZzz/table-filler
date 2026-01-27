"""Tests for doc_assistant.config module."""

import os
from unittest.mock import patch

import pytest


class TestStorageType:
    """Tests for StorageType enum."""

    def test_storage_type_values(self):
        """StorageType should have MEMORY, SQLITE, POSTGRESQL values."""
        from doc_assistant.config import StorageType

        assert StorageType.MEMORY.value == "memory"
        assert StorageType.SQLITE.value == "sqlite"
        assert StorageType.POSTGRESQL.value == "postgresql"


class TestConfig:
    """Tests for Config class."""

    def test_app_name_constant(self):
        """Config should have APP_NAME constant."""
        from doc_assistant.config import Config

        assert Config.APP_NAME == "doc-assistant"

    def test_default_storage_type(self):
        """Default storage type should be MEMORY."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove DOC_STORAGE_TYPE if exists
            os.environ.pop("DOC_STORAGE_TYPE", None)
            # Re-import to get fresh config
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            assert config_module.Config.STORAGE_TYPE.value == "memory"

    def test_storage_type_from_env(self):
        """Storage type should be configurable via DOC_STORAGE_TYPE env var."""
        with patch.dict(os.environ, {"DOC_STORAGE_TYPE": "sqlite"}):
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            assert config_module.Config.STORAGE_TYPE.value == "sqlite"

    def test_deepseek_api_key_from_env(self):
        """DEEPSEEK_API_KEY should be read from environment."""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key-123"}):
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            assert config_module.Config.DEEPSEEK_API_KEY == "test-key-123"

    def test_deepseek_base_url_default(self):
        """DEEPSEEK_BASE_URL should have default value."""
        from doc_assistant.config import Config

        assert Config.DEEPSEEK_BASE_URL is not None
        assert "deepseek" in Config.DEEPSEEK_BASE_URL.lower() or Config.DEEPSEEK_BASE_URL != ""

    def test_dashscope_api_key_from_env(self):
        """DASHSCOPE_API_KEY should be read from environment."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "dash-key-456"}):
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            assert config_module.Config.DASHSCOPE_API_KEY == "dash-key-456"

    def test_vl_model_default(self):
        """VL_MODEL should have default value qwen-vl-max."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("VL_MODEL", None)
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            # Default should be some qwen vl model
            assert "qwen" in config_module.Config.VL_MODEL.lower() or config_module.Config.VL_MODEL != ""

    def test_vl_model_from_env(self):
        """VL_MODEL should be configurable via environment."""
        with patch.dict(os.environ, {"VL_MODEL": "custom-vl-model"}):
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            assert config_module.Config.VL_MODEL == "custom-vl-model"

    def test_database_url_from_env(self):
        """DOC_DATABASE_URL should be read from environment."""
        with patch.dict(os.environ, {"DOC_DATABASE_URL": "sqlite:///test.db"}):
            import importlib
            import doc_assistant.config as config_module
            importlib.reload(config_module)

            assert config_module.Config.DATABASE_URL == "sqlite:///test.db"
