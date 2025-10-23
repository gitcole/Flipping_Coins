"""
Unit tests for Configuration System.

Tests cover configuration loading, validation, environment variable mapping,
YAML configuration files, and settings management.
"""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from tests.utils.base_test import UnitTestCase
from src.core.config.settings import Settings, RobinhoodSettings, TradingSettings
from src.core.config.manager import (
    ConfigurationManager,
    ConfigurationError,
    initialize_config,
    get_settings,
    get_config_manager
)


class TestSettings(UnitTestCase):
    """Test cases for Settings class."""

    def test_default_settings_creation(self):
        """Test creating settings with default values."""
        settings = Settings()

        assert settings.app.name == "crypto-trading-bot"
        assert settings.app.version == "1.0.0"
        assert settings.app.debug is False
        assert settings.app.log_level == "INFO"
        assert settings.app.environment == "development"

        assert settings.trading.enabled is True
        assert settings.trading.max_positions == 10
        assert settings.trading.default_risk_per_trade == 0.02

        assert settings.robinhood.api_key is None
        assert settings.robinhood.private_key is None
        assert settings.robinhood.public_key is None
        assert settings.robinhood.sandbox is False

    def test_settings_from_environment(self):
        """Test creating settings from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "test-bot",
            "APP_VERSION": "2.0.0",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "TRADING_ENABLED": "false",
            "MAX_POSITIONS": "5",
            "ROBINHOOD_API_KEY": "test_api_key",
            "ROBINHOOD_PUBLIC_KEY": "test_public_key",
            "ROBINHOOD_SANDBOX": "true"
        }, clear=True):
            settings = Settings()

            assert settings.app.name == "test-bot"
            assert settings.app.version == "2.0.0"
            assert settings.app.debug is True
            assert settings.app.log_level == "DEBUG"

            assert settings.trading.enabled is False
            assert settings.trading.max_positions == 5

            assert settings.robinhood.api_key == "test_api_key"
            assert settings.robinhood.public_key == "test_public_key"
            assert settings.robinhood.sandbox is True

    def test_settings_validation(self):
        """Test settings validation."""
        # Test valid settings
        settings = Settings(
            app=dict(log_level="WARNING"),
            trading=dict(max_positions=50)
        )
        assert settings.app.log_level == "WARNING"
        assert settings.trading.max_positions == 50

        # Test invalid log level
        with pytest.raises(ValueError, match="Log level must be one of"):
            Settings(app=dict(log_level="INVALID"))

        # Test invalid environment
        with pytest.raises(ValueError, match="Environment must be one of"):
            Settings(app=dict(environment="invalid"))

    def test_robinhood_settings_validation(self):
        """Test Robinhood-specific settings."""
        # Test with API key only
        settings = Settings(robinhood=dict(api_key="test_key"))
        assert settings.robinhood.api_key == "test_key"
        assert settings.robinhood.private_key is None
        assert settings.robinhood.public_key is None

        # Test with private key only
        settings = Settings(robinhood=dict(private_key="test_private"))
        assert settings.robinhood.private_key == "test_private"
        assert settings.robinhood.public_key is None

        # Test with public key only
        settings = Settings(robinhood=dict(public_key="test_public"))
        assert settings.robinhood.public_key == "test_public"
        assert settings.robinhood.private_key is None

    def test_settings_redis_url(self):
        """Test Redis URL generation."""
        settings = Settings(
            database=dict(
                redis=dict(
                    host="redis-server",
                    port=6380,
                    db=2,
                    password="secret"
                )
            )
        )

        assert settings.get_redis_url() == "redis://:secret@redis-server:6380/2"

        # Test without password
        settings.database.redis.password = None
        assert settings.get_redis_url() == "redis://redis-server:6380/2"

    def test_settings_environment_checks(self):
        """Test environment checking methods."""
        # Test development environment
        settings = Settings(app=dict(environment="development"))
        assert settings.is_development() is True
        assert settings.is_production() is False

        # Test production environment
        settings.app.environment = "production"
        assert settings.is_development() is False
        assert settings.is_production() is True

    def test_settings_trading_enabled(self):
        """Test trading enabled logic."""
        # Trading enabled by default
        settings = Settings()
        assert settings.should_enable_trading() is True

        # Trading disabled
        settings.trading.enabled = False
        assert settings.should_enable_trading() is False

        # Debug mode should disable trading
        settings.trading.enabled = True
        settings.app.debug = True
        assert settings.should_enable_trading() is False


class TestConfigurationManager(UnitTestCase):
    """Test cases for ConfigurationManager class."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.manager = ConfigurationManager()

    def test_initialization(self):
        """Test configuration manager initialization."""
        assert self.manager._settings is None
        assert len(self.manager._config_paths) == 0
        assert len(self.manager._env_files) == 0
        assert len(self.manager._config_cache) == 0

    def test_add_config_path(self):
        """Test adding configuration file paths."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("app:\n  name: test\n")
            config_path = f.name

        try:
            self.manager.add_config_path(config_path)
            assert Path(config_path) in self.manager._config_paths
        finally:
            os.unlink(config_path)

    def test_add_config_path_nonexistent(self):
        """Test adding non-existent configuration file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            self.manager.add_config_path("nonexistent.yaml")

    def test_add_env_file(self):
        """Test adding environment files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("TEST_VAR=test_value\n")
            env_path = f.name

        try:
            self.manager.add_env_file(env_path)
            assert env_path in self.manager._env_files
        finally:
            os.unlink(env_path)

    def test_add_env_file_nonexistent(self):
        """Test adding non-existent environment file."""
        with pytest.raises(ConfigurationError, match="Environment file not found"):
            self.manager.add_env_file("nonexistent.env")

    def test_load_from_yaml(self):
        """Test loading configuration from YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
app:
  name: "yaml-test"
  version: "1.0.0"
trading:
  enabled: false
  max_positions: 20
            """)
            config_path = f.name

        try:
            config = self.manager.load_from_yaml(config_path)

            assert config["app"]["name"] == "yaml-test"
            assert config["app"]["version"] == "1.0.0"
            assert config["trading"]["enabled"] is False
            assert config["trading"]["max_positions"] == 20
        finally:
            os.unlink(config_path)

    def test_load_from_env(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
APP_NAME=env-test
TRADING_ENABLED=false
MAX_POSITIONS=15
ROBINHOOD_API_KEY=test_key
            """)
            env_path = f.name

        try:
            config = self.manager.load_from_env(env_path)

            assert config["APP_NAME"] == "env-test"
            assert config["TRADING_ENABLED"] == "false"
            assert config["MAX_POSITIONS"] == "15"
            assert config["ROBINHOOD_API_KEY"] == "test_key"
        finally:
            os.unlink(env_path)

    def test_merge_configs(self):
        """Test configuration merging."""
        config1 = {
            "app": {"name": "test1", "version": "1.0"},
            "trading": {"enabled": True}
        }

        config2 = {
            "app": {"name": "test2"},
            "trading": {"max_positions": 10}
        }

        config3 = {
            "app": {"debug": True}
        }

        merged = self.manager.merge_configs(config1, config2, config3)

        # Later configs should override earlier ones
        assert merged["app"]["name"] == "test2"
        assert merged["app"]["version"] == "1.0"
        assert merged["app"]["debug"] is True
        assert merged["trading"]["enabled"] is True
        assert merged["trading"]["max_positions"] == 10

    def test_load_configuration_from_files(self):
        """Test loading configuration from multiple files."""
        # Create YAML config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
            yaml_f.write("""
app:
  name: "file-test"
  version: "1.0.0"
trading:
  enabled: false
  max_positions: 20
            """)
            yaml_path = yaml_f.name

        # Create .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_f:
            env_f.write("""
ROBINHOOD_API_KEY=file_test_key
ROBINHOOD_SANDBOX=true
LOG_LEVEL=DEBUG
            """)
            env_path = env_f.name

        try:
            # Add files to manager
            self.manager.add_config_path(yaml_path)
            self.manager.add_env_file(env_path)

            # Load configuration
            settings = self.manager.load_configuration()

            # Check merged configuration
            assert settings.app.name == "file-test"
            assert settings.app.log_level == "DEBUG"
            assert settings.trading.enabled is False
            assert settings.trading.max_positions == 20
            assert settings.robinhood.api_key == "file_test_key"
            assert settings.robinhood.sandbox is True

        finally:
            os.unlink(yaml_path)
            os.unlink(env_path)

    def test_load_configuration_caching(self):
        """Test configuration caching."""
        with patch.dict(os.environ, {"APP_NAME": "cached-test"}, clear=True):
            settings1 = self.manager.load_configuration()
            settings2 = self.manager.load_configuration()

            # Should return the same instance (cached)
            assert settings1 is settings2

    def test_load_configuration_forced_reload(self):
        """Test forced configuration reload."""
        with patch.dict(os.environ, {"APP_NAME": "reload-test"}, clear=True):
            settings1 = self.manager.load_configuration()

            # Change environment
            os.environ["APP_NAME"] = "changed-test"

            # Without reload, should return cached version
            settings2 = self.manager.load_configuration(reload=False)
            assert settings2.app.name == "reload-test"

            # With reload, should get new values
            settings3 = self.manager.load_configuration(reload=True)
            assert settings3.app.name == "changed-test"

    def test_configuration_validation(self):
        """Test configuration validation."""
        with patch.dict(os.environ, {
            "APP_NAME": "valid-test",
            "LOG_LEVEL": "INFO",
            "TRADING_ENABLED": "true"
        }, clear=True):
            settings = self.manager.load_configuration()
            assert self.manager.validate_settings(settings) is True

    def test_configuration_validation_failure(self):
        """Test configuration validation failure."""
        # Create invalid settings
        invalid_settings = Settings(app=dict(log_level="INVALID"))

        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            self.manager.validate_settings(invalid_settings)

    def test_get_config_value(self):
        """Test getting configuration values by key."""
        with patch.dict(os.environ, {
            "APP_NAME": "key-test",
            "TRADING_MAX_POSITIONS": "25"
        }, clear=True):
            self.manager.load_configuration()

            assert self.manager.get_config_value("app.name") == "key-test"
            assert self.manager.get_config_value("trading.max_positions") == "25"
            assert self.manager.get_config_value("nonexistent.key", "default") == "default"

    def test_set_config_value(self):
        """Test setting configuration values."""
        with patch.dict(os.environ, {"APP_NAME": "original"}, clear=True):
            self.manager.load_configuration()

            # Set new value
            self.manager.set_config_value("app.name", "modified")

            # Check that it was updated
            assert self.manager.get_config_value("app.name") == "modified"
            assert self.manager._settings.app.name == "modified"

    def test_get_environment_info(self):
        """Test getting environment information."""
        info = self.manager.get_environment_info()

        assert "config_paths" in info
        assert "env_files" in info
        assert "loaded" in info
        assert info["loaded"] is False  # Not loaded yet

        # Load configuration
        with patch.dict(os.environ, {"APP_NAME": "env-info"}, clear=True):
            self.manager.load_configuration()

        info = self.manager.get_environment_info()
        assert info["loaded"] is True
        assert info["environment"] == "development"  # default value


class TestInitializeConfig(UnitTestCase):
    """Test cases for initialize_config function."""

    def test_initialize_config_default_paths(self):
        """Test initialization with default configuration paths."""
        with patch.dict(os.environ, {"ROBINHOOD_API_KEY": "default_key"}, clear=True):
            # Create a temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write("app:\n  name: default-config\n")
                config_path = f.name

            # Create a temporary .env file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                f.write("ROBINHOOD_SANDBOX=true\n")
                env_path = f.name

            try:
                # Change to temp directory
                original_cwd = os.getcwd()
                temp_dir = os.path.dirname(config_path)
                os.chdir(temp_dir)

                settings = initialize_config()

                assert settings.app.name == "default-config"
                assert settings.robinhood.api_key == "default_key"
                assert settings.robinhood.sandbox is True

            finally:
                os.chdir(original_cwd)
                os.unlink(config_path)
                os.unlink(env_path)

    def test_initialize_config_custom_paths(self):
        """Test initialization with custom configuration paths."""
        with patch.dict(os.environ, {"APP_NAME": "custom-test"}, clear=True):
            # Create custom config files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write("app:\n  version: '2.0.0'\n")
                yaml_path = f.name

            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                f.write("LOG_LEVEL=WARNING\n")
                env_path = f.name

            try:
                settings = initialize_config(
                    config_paths=[yaml_path],
                    env_files=[env_path]
                )

                assert settings.app.version == "2.0.0"
                assert settings.app.log_level == "WARNING"

            finally:
                os.unlink(yaml_path)
                os.unlink(env_path)

    def test_global_config_manager(self):
        """Test global configuration manager functionality."""
        # Test getting global manager
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2  # Should return same instance

        # Test get_settings function
        with patch.dict(os.environ, {"APP_NAME": "global-test"}, clear=True):
            # Should raise error if not initialized
            with pytest.raises(ConfigurationError, match="Configuration not initialized"):
                get_settings()

            # Initialize and then get settings
            initialize_config()
            settings = get_settings()
            assert settings.app.name == "global-test"