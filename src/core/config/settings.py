"""Configuration settings for the crypto trading bot."""

from __future__ import annotations

import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class AppSettings(BaseModel):
    """Application-level settings."""

    name: str = Field(default="crypto-trading-bot", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment (development, staging, production)")

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()


class APISettings(BaseModel):
    """API configuration settings."""

    base_url: str = Field(default="https://api.example.com", description="Base API URL")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    retries: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    rate_limit_per_minute: int = Field(default=100, ge=1, le=1000, description="Rate limit per minute")
    user_agent: str = Field(default="crypto-trading-bot/1.0.0", description="User agent string")


class WebSocketSettings(BaseModel):
    """WebSocket configuration settings."""

    uri: str = Field(default="", description="WebSocket server URI (leave empty to disable WebSocket)")
    ping_interval: int = Field(default=20, ge=5, le=300, description="Ping interval in seconds")
    timeout: int = Field(default=10, ge=5, le=60, description="Connection timeout in seconds")
    max_reconnects: int = Field(default=5, ge=1, le=20, description="Maximum reconnection attempts")
    reconnect_delay: int = Field(default=5, ge=1, le=60, description="Reconnection delay in seconds")


class TradingSettings(BaseModel):
    """Trading configuration settings."""

    enabled: bool = Field(default=True, description="Enable trading")
    max_positions: int = Field(default=10, ge=1, le=100, description="Maximum number of positions")
    default_risk_per_trade: float = Field(default=0.02, ge=0.001, le=0.1, description="Default risk per trade (0.001-0.1)")
    min_order_size: float = Field(default=10.0, ge=0.01, description="Minimum order size")
    supported_symbols: List[str] = Field(
        default=["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT"],
        description="Supported trading symbols"
    )
    max_order_value: float = Field(default=10000.0, ge=1.0, description="Maximum order value")
    order_timeout: int = Field(default=30, ge=5, le=300, description="Order timeout in seconds")

    @validator("supported_symbols")
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Validate trading symbols format."""
        if not v:
            raise ValueError("At least one symbol must be specified")

        for symbol in v:
            if not symbol or "/" not in symbol:
                raise ValueError(f"Invalid symbol format: {symbol}. Expected format: BASE/QUOTE")

        return v


class RiskSettings(BaseModel):
    """Risk management settings."""

    max_portfolio_risk: float = Field(default=0.1, ge=0.01, le=0.5, description="Maximum portfolio risk (0.01-0.5)")
    max_correlation: float = Field(default=0.7, ge=0.1, le=1.0, description="Maximum asset correlation")
    stop_loss_default: float = Field(default=0.05, ge=0.01, le=0.3, description="Default stop loss (0.01-0.3)")
    take_profit_default: float = Field(default=0.15, ge=0.01, le=1.0, description="Default take profit (0.01-1.0)")
    max_drawdown: float = Field(default=0.2, ge=0.05, le=0.5, description="Maximum drawdown (0.05-0.5)")
    max_positions_per_symbol: int = Field(default=3, ge=1, le=10, description="Maximum positions per symbol")
    daily_loss_limit: float = Field(default=0.05, ge=0.01, le=0.2, description="Daily loss limit (0.01-0.2)")
    max_open_orders: int = Field(default=20, ge=1, le=100, description="Maximum open orders")


class DatabaseSettings(BaseModel):
    """Database configuration settings."""

    class RedisSettings(BaseModel):
        """Redis-specific settings."""
        host: str = Field(default="localhost", description="Redis host")
        port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
        db: int = Field(default=0, ge=0, le=15, description="Redis database number")
        password: Optional[str] = Field(default=None, description="Redis password")
        decode_responses: bool = Field(default=True, description="Decode responses as strings")
        socket_timeout: int = Field(default=5, ge=1, le=30, description="Socket timeout in seconds")
        socket_connect_timeout: int = Field(default=5, ge=1, le=30, description="Socket connect timeout in seconds")
        retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
        max_connections: int = Field(default=20, ge=1, le=100, description="Maximum connections")

    redis: RedisSettings = Field(default_factory=RedisSettings, description="Redis configuration")


class StrategySettings(BaseModel):
    """Strategy-specific settings."""

    class MarketMakingSettings(BaseModel):
        """Market making strategy settings."""
        enabled: bool = Field(default=True, description="Enable market making strategy")
        spread_percentage: float = Field(default=0.001, ge=0.0001, le=0.01, description="Spread percentage")
        order_refresh_time: int = Field(default=30, ge=10, le=300, description="Order refresh time in seconds")
        inventory_range: float = Field(default=0.1, ge=0.01, le=0.5, description="Inventory range")
        min_order_size: float = Field(default=0.001, ge=0.0001, description="Minimum order size for market making")
        max_order_size: float = Field(default=1.0, ge=0.001, description="Maximum order size for market making")
        max_inventory_value: float = Field(default=1000.0, ge=1.0, description="Maximum inventory value")

    market_making: MarketMakingSettings = Field(default_factory=MarketMakingSettings, description="Market making strategy configuration")


class NotificationSettings(BaseModel):
    """Notification settings."""

    telegram_bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID")
    email_smtp_server: Optional[str] = Field(default=None, description="SMTP server")
    email_smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP port")
    email_username: Optional[str] = Field(default=None, description="Email username")
    email_password: Optional[str] = Field(default=None, description="Email password")
    email_recipients: List[str] = Field(default_factory=list, description="Email recipients")

    @validator("email_recipients")
    def validate_email_recipients(cls, v: List[str]) -> List[str]:
        """Validate email format."""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for email in v:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email format: {email}")

        return v


class LoggingSettings(BaseModel):
    """Logging configuration settings."""

    log_to_file: bool = Field(default=False, description="Enable file logging")
    log_file_path: str = Field(default="logs/crypto_trading_bot.log", description="Log file path")
    log_max_file_size: int = Field(default=10485760, ge=1024, description="Max log file size in bytes")
    log_backup_count: int = Field(default=5, ge=1, le=50, description="Number of log backups to keep")
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    enable_json_logging: bool = Field(default=False, description="Enable JSON formatted logging")


class RobinhoodSettings(BaseModel):
    """Robinhood-specific settings."""

    api_token: Optional[str] = Field(default=None, alias="ROBINHOOD_API_TOKEN", description="Robinhood API token")
    client_id: Optional[str] = Field(default=None, alias="ROBINHOOD_CLIENT_ID", description="Robinhood OAuth client ID")
    client_secret: Optional[str] = Field(default=None, alias="ROBINHOOD_CLIENT_SECRET", description="Robinhood OAuth client secret")
    api_key: Optional[str] = Field(default=None, alias="ROBINHOOD_API_KEY", description="Robinhood Crypto API key")
    private_key: Optional[str] = Field(default=None, alias="ROBINHOOD_PRIVATE_KEY", description="Robinhood Crypto private key (base64)")
    public_key: Optional[str] = Field(default=None, alias="ROBINHOOD_PUBLIC_KEY", description="Robinhood Crypto public key (base64)")
    sandbox: bool = Field(default=False, alias="ROBINHOOD_SANDBOX", description="Use sandbox/testnet environment")

    class Config:
        """Pydantic configuration for Robinhood settings."""
        validate_by_name = True


class ExchangeSettings(BaseModel):
    """Exchange-specific settings."""

    api_key: Optional[str] = Field(default=None, description="Exchange API key")
    secret_key: Optional[str] = Field(default=None, description="Exchange secret key")
    sandbox: bool = Field(default=False, description="Use sandbox/testnet environment")
    testnet: bool = Field(default=True, description="Use testnet for development")
    passphrase: Optional[str] = Field(default=None, description="Exchange passphrase (if required)")


class Settings(BaseModel):
    """Main application settings."""

    app: AppSettings = Field(default_factory=AppSettings, description="Application settings")
    api: APISettings = Field(default_factory=APISettings, description="API settings")
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings, description="WebSocket settings")
    trading: TradingSettings = Field(default_factory=TradingSettings, description="Trading settings")
    risk: RiskSettings = Field(default_factory=RiskSettings, description="Risk management settings")
    database: DatabaseSettings = Field(default_factory=DatabaseSettings, description="Database settings")
    strategies: StrategySettings = Field(default_factory=StrategySettings, description="Strategy settings")
    notifications: NotificationSettings = Field(default_factory=NotificationSettings, description="Notification settings")
    logging: LoggingSettings = Field(default_factory=LoggingSettings, description="Logging settings")
    exchange: ExchangeSettings = Field(default_factory=ExchangeSettings, description="Exchange settings")
    robinhood: RobinhoodSettings = Field(default_factory=RobinhoodSettings, description="Robinhood settings")

    class Config:
        """Pydantic configuration."""
        env_file = None  # Disable Pydantic's env loading since we handle it manually
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True
        validate_by_name = True

    def __init__(self, **data):
        """Initialize settings with environment variable overrides."""
        # Merge os.environ with provided data (os.environ already loaded from .env by manager)
        data = {**os.environ, **data}

        super().__init__(**data)

    @classmethod
    def from_env_files(cls, *env_files: str) -> Settings:
        """Create settings from multiple .env files."""
        # Load the specified env files into os.environ
        for env_file in env_files:
            if os.path.exists(env_file):
                load_dotenv(env_file)

        # Then use os.environ
        return cls(**os.environ)

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return self.dict()

    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        redis_config = self.database.redis
        auth = f":{redis_config.password}@" if redis_config.password else ""
        return f"redis://{auth}{redis_config.host}:{redis_config.port}/{redis_config.db}"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == "development"

    def should_enable_trading(self) -> bool:
        """Check if trading should be enabled."""
        return self.trading.enabled and not self.app.debug

    def get_log_config(self) -> dict:
        """Get logging configuration for Python logging module."""

        # Human-readable formatter
        readable_format = "%(asctime)s - %(levelname)s - %(message)s"

        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "readable": {
                    "format": readable_format,
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": self.logging.log_format,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "readable",  # Use human-readable format
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "crypto_trading_bot": {
                    "level": self.app.log_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }

        if self.logging.log_to_file:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json" if self.logging.enable_json_logging else "standard",
                "filename": self.logging.log_file_path,
                "maxBytes": self.logging.log_max_file_size,
                "backupCount": self.logging.log_backup_count,
            }
            config["loggers"]["crypto_trading_bot"]["handlers"].append("file")

        return config