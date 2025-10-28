"""Configuration manager for the crypto trading bot."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union

import structlog
import yaml
from dotenv import load_dotenv

from .settings import Settings


class ConfigurationError(Exception):
    """Raised when there's an error in configuration loading or validation."""
    pass


class ConfigurationManager:
    """Manages application configuration with support for multiple sources."""

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._settings: Optional[Settings] = None
        self._lock = threading.RLock()
        self._config_paths: List[Path] = []
        self._env_files: List[str] = []
        self._config_cache: Dict[str, Union[Settings, dict]] = {}

    def add_config_path(self, path: Union[str, Path]) -> None:
        """Add a configuration file path.

        Args:
            path: Path to configuration file (YAML, JSON, etc.)

        Raises:
            ConfigurationError: If path doesn't exist or is invalid.
        """
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        if config_path not in self._config_paths:
            self._config_paths.append(config_path)

        # Clear cache when adding new paths
        self._config_cache.clear()

    def add_env_file(self, env_file: Union[str, Path]) -> None:
        """Add an environment file path.

        Args:
            env_file: Path to .env file

        Raises:
            ConfigurationError: If file doesn't exist or is invalid.
        """
        env_path = Path(env_file)

        if not env_path.exists():
            raise ConfigurationError(f"Environment file not found: {env_file}")

        if str(env_path) not in self._env_files:
            self._env_files.append(str(env_path))

        # Clear cache when adding new files
        self._config_cache.clear()

    def load_from_yaml(self, file_path: Union[str, Path]) -> dict:
        """Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: If file cannot be loaded or parsed.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load YAML config from {file_path}: {e}")

    def load_from_env(self, env_file: Union[str, Path]) -> dict:
        """Load configuration from .env file.

        Args:
            env_file: Path to .env file

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: If file cannot be loaded.
        """
        try:
            from dotenv import dotenv_values
            return dict(dotenv_values(env_file))
        except Exception as e:
            raise ConfigurationError(f"Failed to load env file from {env_file}: {e}")

    def merge_configs(self, *configs: dict) -> dict:
        """Deep merge multiple configuration dictionaries.

        Args:
            *configs: Configuration dictionaries to merge

        Returns:
            Merged configuration dictionary

        Note:
            Later dictionaries override earlier ones for conflicting keys.
            Nested dictionaries are merged recursively.
        """
        def deep_merge(base: dict, overlay: dict) -> dict:
            """Recursively merge two dictionaries."""
            result = base.copy()

            for key, value in overlay.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value

            return result

        merged = {}
        for config in configs:
            if config:
                merged = deep_merge(merged, config)

        return merged

    def load_configuration(self, reload: bool = False) -> Settings:
        """Load and merge all configuration sources.

        Args:
            reload: Force reload even if already loaded

        Returns:
            Settings object with merged configuration

        Raises:
            ConfigurationError: If configuration cannot be loaded or validated.
        """
        with self._lock:
            # Return cached settings if available and not forcing reload
            if self._settings is not None and not reload:
                return self._settings

            try:
                # Load configurations from all sources
                config_parts = []

                # Load from YAML files
                for config_path in self._config_paths:
                    config_part = self.load_from_yaml(config_path)
                    if config_part:
                        config_parts.append(config_part)

                # Load from environment files
                for env_file in self._env_files:
                    env_config = self.load_from_env(env_file)
                    if env_config:
                        config_parts.append(env_config)

                # Load from environment variables
                env_config = self._load_from_environment()
                if env_config:
                    config_parts.append(env_config)

                # Merge all configurations
                merged_config = self.merge_configs(*config_parts)

                # Create and validate settings
                self._settings = Settings(**merged_config)

                # Cache the configuration
                self._config_cache['settings'] = self._settings
                self._config_cache['config_dict'] = merged_config

                return self._settings

            except Exception as e:
                raise ConfigurationError(f"Failed to load configuration: {e}")

    def _load_from_environment(self) -> dict:
        """Load configuration from environment variables.

        Returns:
            Dictionary of environment variables with proper type conversion.
        """
        logger = structlog.get_logger(__name__)
        config = {}

        logger.debug("Loading configuration from environment variables")

        # Map environment variables to configuration keys
        env_mapping = {
            'APP_NAME': 'app.name',
            'APP_VERSION': 'app.version',
            'DEBUG': 'app.debug',
            'LOG_LEVEL': 'app.log_level',
            'API_BASE_URL': 'api.base_url',
            'API_TIMEOUT': 'api.timeout',
            'API_RETRIES': 'api.retries',
            'API_RATE_LIMIT_PER_MINUTE': 'api.rate_limit_per_minute',
            'WEBSOCKET_PING_INTERVAL': 'websocket.ping_interval',
            'WEBSOCKET_TIMEOUT': 'websocket.timeout',
            'WEBSOCKET_MAX_RECONNECTS': 'websocket.max_reconnects',
            'TRADING_ENABLED': 'trading.enabled',
            'MAX_POSITIONS': 'trading.max_positions',
            'DEFAULT_RISK_PER_TRADE': 'trading.default_risk_per_trade',
            'MIN_ORDER_SIZE': 'trading.min_order_size',
            'MAX_PORTFOLIO_RISK': 'risk.max_portfolio_risk',
            'MAX_CORRELATION': 'risk.max_correlation',
            'STOP_LOSS_DEFAULT': 'risk.stop_loss_default',
            'TAKE_PROFIT_DEFAULT': 'risk.take_profit_default',
            'MAX_DRAWDOWN': 'risk.max_drawdown',
            'REDIS_HOST': 'database.redis.host',
            'REDIS_PORT': 'database.redis.port',
            'REDIS_DB': 'database.redis.db',
            'REDIS_PASSWORD': 'database.redis.password',
            'EXCHANGE_API_KEY': 'exchange.api_key',
            'EXCHANGE_SECRET_KEY': 'exchange.secret_key',
            'EXCHANGE_SANDBOX': 'exchange.sandbox',
            'EXCHANGE_TESTNET': 'exchange.testnet',
            'MARKET_MAKING_ENABLED': 'strategies.market_making.enabled',
            'SPREAD_PERCENTAGE': 'strategies.market_making.spread_percentage',
            'ORDER_REFRESH_TIME': 'strategies.market_making.order_refresh_time',
            'INVENTORY_RANGE': 'strategies.market_making.inventory_range',
            'LOG_TO_FILE': 'logging.log_to_file',
            'LOG_FILE_PATH': 'logging.log_file_path',
            'LOG_MAX_FILE_SIZE': 'logging.log_max_file_size',
            'LOG_BACKUP_COUNT': 'logging.log_backup_count',
            'TELEGRAM_BOT_TOKEN': 'notifications.telegram_bot_token',
            'TELEGRAM_CHAT_ID': 'notifications.telegram_chat_id',
            'EMAIL_SMTP_SERVER': 'notifications.email_smtp_server',
            'EMAIL_SMTP_PORT': 'notifications.email_smtp_port',
            'EMAIL_USERNAME': 'notifications.email_username',
            'EMAIL_PASSWORD': 'notifications.email_password',
            'ROBINHOOD_API_KEY': 'robinhood.api_key',
            'ROBINHOOD_PRIVATE_KEY': 'robinhood.private_key',
            'ROBINHOOD_PUBLIC_KEY': 'robinhood.public_key',
            'ROBINHOOD_SANDBOX': 'robinhood.sandbox',
        }

        def set_nested_value(data: dict, keys: List[str], value: str) -> None:
            """Set a nested dictionary value from a list of keys."""
            for key in keys[:-1]:
                if key not in data:
                    data[key] = {}
                data = data[key]
            data[keys[-1]] = value

        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                keys = config_path.split('.')
                set_nested_value(config, keys, value)

        # Log what was loaded (without sensitive values)
        safe_config = {}
        for key, value in config.items():
            if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
                safe_config[key] = "***"
            else:
                safe_config[key] = value

        logger.debug("Configuration loaded from environment", config=safe_config)
        return config

    def get_settings(self) -> Settings:
        """Get the current settings.

        Returns:
            Current Settings object

        Raises:
            ConfigurationError: If settings haven't been loaded yet.
        """
        if self._settings is None:
            raise ConfigurationError("Configuration not loaded. Call load_configuration() first.")
        return self._settings

    def get_config_dict(self) -> dict:
        """Get the current configuration as a dictionary.

        Returns:
            Current configuration dictionary

        Raises:
            ConfigurationError: If configuration hasn't been loaded yet.
        """
        if 'config_dict' not in self._config_cache:
            raise ConfigurationError("Configuration not loaded. Call load_configuration() first.")
        return self._config_cache['config_dict']

    def reload_configuration(self) -> Settings:
        """Force reload of configuration from all sources.

        Returns:
            Updated Settings object
        """
        return self.load_configuration(reload=True)

    def save_to_yaml(self, file_path: Union[str, Path], settings: Optional[Settings] = None) -> None:
        """Save current settings to a YAML file.

        Args:
            file_path: Path where to save the YAML file
            settings: Settings to save (defaults to current settings)

        Raises:
            ConfigurationError: If settings cannot be saved.
        """
        if settings is None:
            settings = self.get_settings()

        try:
            config_dict = settings.dict()

            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(config_dict, file, default_flow_style=False, indent=2)

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {file_path}: {e}")

    def validate_settings(self, settings: Optional[Settings] = None) -> bool:
        """Validate the current settings.

        Args:
            settings: Settings to validate (defaults to current settings)

        Returns:
            True if validation passes

        Raises:
            ConfigurationError: If validation fails.
        """
        if settings is None:
            settings = self.get_settings()

        try:
            # Validate by creating a new instance
            Settings(**settings.dict())
            return True
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")

    def get_config_value(self, key: str, default: any = None) -> any:
        """Get a specific configuration value by dot notation key.

        Args:
            key: Configuration key (e.g., 'app.name', 'api.timeout')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Raises:
            ConfigurationError: If configuration not loaded.
        """
        config_dict = self.get_config_dict()

        def get_nested_value(data: dict, keys: List[str]) -> any:
            """Get a nested dictionary value from a list of keys."""
            for key in keys:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return default
            return data

        keys = key.split('.')
        return get_nested_value(config_dict, keys)

    def set_config_value(self, key: str, value: any) -> None:
        """Set a configuration value by dot notation key.

        Args:
            key: Configuration key (e.g., 'app.name', 'api.timeout')
            value: Value to set

        Note:
            This only affects the in-memory configuration.
            Use save_to_yaml() to persist changes.
        """
        with self._lock:
            if 'config_dict' not in self._config_cache:
                raise ConfigurationError("Configuration not loaded. Call load_configuration() first.")

            config_dict = self._config_cache['config_dict']

            def set_nested_value(data: dict, keys: List[str], val: any) -> None:
                """Set a nested dictionary value from a list of keys."""
                for k in keys[:-1]:
                    if k not in data:
                        data[k] = {}
                    data = data[k]
                data[keys[-1]] = val

            keys = key.split('.')
            set_nested_value(config_dict, keys, value)

            # Recreate settings with updated config
            self._settings = Settings(**config_dict)

    def get_environment_info(self) -> Dict[str, any]:
        """Get information about the current environment and configuration sources.

        Returns:
            Dictionary with environment information.
        """
        return {
            'config_paths': [str(p) for p in self._config_paths],
            'env_files': self._env_files.copy(),
            'environment': self.get_settings().app.environment if self._settings else None,
            'debug_mode': self.get_settings().app.debug if self._settings else None,
            'loaded': self._settings is not None,
        }

    def reset(self) -> None:
        """Reset the configuration manager to initial state."""
        with self._lock:
            self._settings = None
            self._config_paths.clear()
            self._env_files.clear()
            self._config_cache.clear()


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance.

    Returns:
        Global ConfigurationManager instance
    """
    global _config_manager

    with _config_lock:
        if _config_manager is None:
            _config_manager = ConfigurationManager()

    return _config_manager


def initialize_config(
    config_paths: Optional[List[Union[str, Path]]] = None,
    env_files: Optional[List[str]] = None,
) -> Settings:
    """Initialize configuration with common settings.

    Args:
        config_paths: List of configuration file paths
        env_files: List of environment file paths

    Returns:
        Settings object with loaded configuration
    """
    logger = structlog.get_logger(__name__)
    manager = get_config_manager()

    logger.info("Initializing configuration", config_paths=config_paths, env_files=env_files)

    # Add default configuration paths
    if config_paths:
        for path in config_paths:
            manager.add_config_path(path)
    else:
        # Default config paths
        default_paths = [
            Path("config/default.yaml"),
            Path("config/config.yaml"),
            Path("config/.env"),
        ]

        logger.debug("Checking default config paths", paths=[str(p) for p in default_paths])
        for path in default_paths:
            if path.exists():
                if path.suffix == '.yaml':
                    manager.add_config_path(path)
                    logger.debug("Added config path", path=str(path))
                else:
                    manager.add_env_file(str(path))
                    logger.debug("Added env file", path=str(path))

    # Add default env files
    if env_files:
        for env_file in env_files:
            manager.add_env_file(env_file)
    else:
        # Default env files
        default_env_files = [
            ".env",
            "config/.env",
        ]

        logger.debug("Checking default env files", files=default_env_files)
        for env_file in default_env_files:
            if Path(env_file).exists():
                manager.add_env_file(env_file)
                logger.debug("Added env file", path=env_file)

    logger.debug("Environment files to load", files=manager._env_files)

    # Load environment files into os.environ
    for env_file in manager._env_files:
        if Path(env_file).exists():
            logger.info("Loading environment file", path=env_file)
            load_dotenv(env_file, override=True)

            # Log which environment variables were loaded (without sensitive values)
            env_vars_loaded = []
            for key in ['ROBINHOOD_API_KEY', 'ROBINHOOD_PRIVATE_KEY', 'ROBINHOOD_PUBLIC_KEY', 'ROBINHOOD_SANDBOX']:
                if os.getenv(key):
                    env_vars_loaded.append(key)
            logger.debug("Environment variables loaded", variables=env_vars_loaded)
        else:
            logger.warning("Environment file not found", path=env_file)

    logger.info("Loading configuration from all sources")
    return manager.load_configuration()


def get_settings() -> Settings:
    """Get the current application settings.

    Returns:
        Current Settings object

    Raises:
        ConfigurationError: If configuration not initialized.
    """
    manager = get_config_manager()

    if manager._settings is None:
        raise ConfigurationError(
            "Configuration not initialized. Call initialize_config() first or "
            "use get_config_manager().load_configuration() directly."
        )

    return manager._settings


def reload_config() -> Settings:
    """Reload configuration from all sources.

    Returns:
        Updated Settings object
    """
    return get_config_manager().reload_configuration()