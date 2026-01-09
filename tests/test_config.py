"""Tests for UG Game configuration management."""

import os
from unittest.mock import patch

from ug_game.core.config import UGGameSettings, settings


class TestUGGameSettings:
    """Test cases for UGGameSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        import os

        # Clear environment variables that would override defaults
        env_vars_to_clear = [
            "DEVELOPER_API_KEY",
            "SERVICE_ACCOUNT_API_KEY",
            "PLAYER_FEDERATED_ID",
            "API_BASE_URL",
            "WEBSOCKET_URL",
            "DEFAULT_PROMPT",
        ]
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Create a test settings class that doesn't load from env
            class TestSettings(UGGameSettings):
                class Config:
                    env_file = None
                    env_file_encoding = "utf-8"
                    case_sensitive = False

            config = TestSettings()

            assert config.developer_api_key is None
            assert config.service_account_api_key is None
            assert config.player_federated_id is None
            assert config.api_base_url == "https://pug.stg.uglabs.app"
            assert config.websocket_url == "wss://pug.stg.uglabs.app/interact"
            assert "helpful AI assistant" in config.default_prompt
        finally:
            # Restore original environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "DEVELOPER_API_KEY": "dev_key_123",
            "SERVICE_ACCOUNT_API_KEY": "service_key_456",
            "PLAYER_FEDERATED_ID": "player_fed_789",
            "API_BASE_URL": "https://custom.api.com",
            "WEBSOCKET_URL": "wss://custom.ws.com/chat",
            "DEFAULT_PROMPT": "Custom prompt",
        }

        # Create a test settings class with mocked environment
        class TestSettings(UGGameSettings):
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestSettings()

            assert config.developer_api_key.get_secret_value() == "dev_key_123"
            assert config.service_account_api_key.get_secret_value() == "service_key_456"
            assert config.player_federated_id == "player_fed_789"
            assert config.api_base_url == "https://custom.api.com"
            assert config.websocket_url == "wss://custom.ws.com/chat"
            assert config.default_prompt == "Custom prompt"

    def test_case_insensitive_environment_variables(self):
        """Test case insensitive environment variable loading."""
        env_vars = {
            "developer_api_key": "dev_key_lowercase",
            "SERVICE_ACCOUNT_API_KEY": "service_key_mixed",
            "player_federated_id": "player_fed_lowercase",
        }

        # Create a test settings class with mocked environment
        class TestSettings(UGGameSettings):
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestSettings()

            assert config.developer_api_key.get_secret_value() == "dev_key_lowercase"
            assert config.service_account_api_key.get_secret_value() == "service_key_mixed"
            assert config.player_federated_id == "player_fed_lowercase"

    def test_secret_str_handling(self):
        """Test that API keys are properly handled as SecretStr."""
        env_vars = {
            "DEVELOPER_API_KEY": "secret_dev_key",
            "SERVICE_ACCOUNT_API_KEY": "secret_service_key",
        }

        # Create a test settings class with mocked environment
        class TestSettings(UGGameSettings):
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestSettings()

            # Test that we can get the secret value
            assert config.developer_api_key.get_secret_value() == "secret_dev_key"
            assert config.service_account_api_key.get_secret_value() == "secret_service_key"

            # Test that repr doesn't show the secret
            assert "secret_dev_key" not in repr(config.developer_api_key)
            assert "secret_service_key" not in repr(config.service_account_api_key)

    def test_partial_environment_variables(self):
        """Test loading configuration with only some environment variables set."""
        env_vars = {"DEVELOPER_API_KEY": "only_dev_key"}

        # Create a test settings class with mocked environment
        class TestSettings(UGGameSettings):
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestSettings()

            assert config.developer_api_key.get_secret_value() == "only_dev_key"
            assert config.service_account_api_key is None
            assert config.player_federated_id is None
            # Other defaults should remain
            assert config.api_base_url == "https://pug.stg.uglabs.app"

    def test_empty_environment_variables(self):
        """Test behavior with empty environment variables."""
        env_vars = {
            "DEVELOPER_API_KEY": "",
            "SERVICE_ACCOUNT_API_KEY": "",
            "PLAYER_FEDERATED_ID": "",
        }

        # Create a test settings class with mocked environment
        class TestSettings(UGGameSettings):
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestSettings()

            # Empty strings should still be loaded
            assert config.developer_api_key.get_secret_value() == ""
            assert config.service_account_api_key.get_secret_value() == ""
            assert config.player_federated_id == ""

    def test_config_class_attributes(self):
        """Test Config class attributes."""

        # Create a test settings class to check config attributes
        class TestSettings(UGGameSettings):
            class Config:
                env_file = None
                env_file_encoding = "utf-8"
                case_sensitive = False

        config = TestSettings()

        # Check that Config attributes are set
        assert config.Config.env_file is None
        assert config.Config.env_file_encoding == "utf-8"
        assert config.Config.case_sensitive is False


class TestGlobalSettings:
    """Test cases for the global settings instance."""

    def test_global_settings_instance(self):
        """Test that the global settings instance is created."""
        assert isinstance(settings, UGGameSettings)

    def test_global_settings_defaults(self):
        """Test that global settings has expected defaults."""
        import os

        # Clear environment variables that would override defaults
        env_vars_to_clear = [
            "DEVELOPER_API_KEY",
            "SERVICE_ACCOUNT_API_KEY",
            "PLAYER_FEDERATED_ID",
            "API_BASE_URL",
            "WEBSOCKET_URL",
            "DEFAULT_PROMPT",
        ]
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            # Create a test settings class that doesn't load from env
            class TestSettings(UGGameSettings):
                class Config:
                    env_file = None
                    env_file_encoding = "utf-8"
                    case_sensitive = False

            fresh_settings = TestSettings()

            assert fresh_settings.developer_api_key is None
            assert fresh_settings.api_base_url == "https://pug.stg.uglabs.app"
        finally:
            # Restore original environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
