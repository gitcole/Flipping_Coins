"""Structured logging configuration for the crypto trading bot."""

from __future__ import annotations

import logging
import logging.config
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pythonjsonlogger import jsonlogger

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import get_settings


class TradingBotLogFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for trading bot logs."""

    def __init__(self, *args, **kwargs):
        """Initialize the formatter with custom field names."""
        # Map standard fields to more readable names
        kwargs.setdefault('rename_fields', {
            'levelname': 'level',
            'name': 'logger',
            'asctime': 'timestamp',
        })
        super().__init__(*args, **kwargs)

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log records."""
        super().add_fields(log_record, record, message_dict)

        # Add trading bot specific fields
        log_record['bot_version'] = getattr(record, 'bot_version', '1.0.0')
        log_record['environment'] = getattr(record, 'environment', 'development')
        log_record['service'] = 'crypto-trading-bot'

        # Add request/trading context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'trade_id'):
            log_record['trade_id'] = record.trade_id
        if hasattr(record, 'symbol'):
            log_record['symbol'] = record.symbol
        if hasattr(record, 'strategy'):
            log_record['strategy'] = record.strategy

        # Add performance metrics if available
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms
        if hasattr(record, 'memory_usage_mb'):
            log_record['memory_usage_mb'] = record.memory_usage_mb
        if hasattr(record, 'cpu_usage_percent'):
            log_record['cpu_usage_percent'] = record.cpu_usage_percent


class TradingBotLogFilter(logging.Filter):
    """Custom filter for trading bot logs."""

    def __init__(self, environment: str = "development", service: str = "crypto-trading-bot"):
        """Initialize the filter.

        Args:
            environment: Environment name
            service: Service name
        """
        super().__init__()
        self.environment = environment
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records."""
        # Add environment and service info to all records
        record.environment = self.environment
        record.service = self.service

        return True


class LogContext:
    """Context manager for adding contextual information to logs."""

    def __init__(self, logger: logging.Logger, **context):
        """Initialize log context.

        Args:
            logger: Logger instance
            **context: Context key-value pairs to add to log records
        """
        self.logger = logger
        self.context = context
        self.old_factory = logging.getLogRecordFactory()

    def __enter__(self) -> logging.Logger:
        """Enter the context."""
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        logging.setLogRecordFactory(self.old_factory)


def setup_logging(
    config: Optional[Dict[str, Any]] = None,
    log_level: Optional[str] = None,
    log_to_file: bool = False,
    log_file_path: Optional[Union[str, Path]] = None,
    enable_json: bool = True,
) -> None:
    """Setup logging configuration for the trading bot.

    Args:
        config: Logging configuration dictionary (uses settings if not provided)
        log_level: Override log level (uses settings if not provided)
        log_to_file: Enable file logging (uses settings if not provided)
        log_file_path: Log file path (uses settings if not provided)
        enable_json: Enable JSON formatting (uses settings if not provided)
    """
    try:
        # Get settings for default values
        settings = get_settings()

        if config is None:
            config = settings.get_log_config()

        # Override with provided parameters
        if log_level:
            config['loggers']['crypto_trading_bot']['level'] = log_level.upper()

        # Configure file logging if enabled
        if log_to_file or settings.logging.log_to_file:
            log_path = log_file_path or settings.logging.log_file_path
            max_bytes = settings.logging.log_max_file_size
            backup_count = settings.logging.log_backup_count

            # Ensure log directory exists
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)

            # Add file handler to config
            config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'json' if enable_json or settings.logging.enable_json_logging else 'standard',
                'filename': log_path,
                'maxBytes': max_bytes,
                'backupCount': backup_count,
            }

            # Add file handler to logger
            if 'file' not in config['loggers']['crypto_trading_bot']['handlers']:
                config['loggers']['crypto_trading_bot']['handlers'].append('file')

        # Apply configuration
        logging.config.dictConfig(config)

        # Add custom filter
        logger = logging.getLogger('crypto_trading_bot')
        filter = TradingBotLogFilter(
            environment=settings.app.environment,
            service=settings.app.name
        )
        logger.addFilter(filter)

    except Exception as e:
        # Fallback to basic configuration if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
        logging.error(f"Failed to setup logging: {e}")


def get_logger(name: str, **context) -> logging.Logger:
    """Get a logger instance with optional context.

    Args:
        name: Logger name
        **context: Additional context to include in log records

    Returns:
        Logger instance
    """
    logger = logging.getLogger(f"crypto_trading_bot.{name}")

    # Add context attributes to logger for use in LogContext
    for key, value in context.items():
        setattr(logger, f'_{key}', value)

    return logger


def log_function_call(logger: logging.Logger, func_name: str, args: tuple = None, kwargs: dict = None):
    """Decorator to log function calls with performance metrics.

    Args:
        logger: Logger instance
        func_name: Name of the function being called
        args: Function arguments
        kwargs: Function keyword arguments
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            import functools

            start_time = time.time()

            try:
                logger.debug(
                    f"Calling {func_name}",
                    extra={
                        'function': func_name,
                        'args_count': len(args) if args else 0,
                        'kwargs_keys': list(kwargs.keys()) if kwargs else [],
                    }
                )

                result = func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                logger.debug(
                    f"Completed {func_name}",
                    extra={
                        'function': func_name,
                        'duration_ms': duration_ms,
                        'success': True,
                    }
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"Failed {func_name}: {str(e)}",
                    extra={
                        'function': func_name,
                        'duration_ms': duration_ms,
                        'success': False,
                        'error': str(e),
                    }
                )
                raise

        return wrapper
    return decorator


def log_async_function_call(logger: logging.Logger, func_name: str):
    """Decorator to log async function calls with performance metrics.

    Args:
        logger: Logger instance
        func_name: Name of the async function being called
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            import functools

            start_time = time.time()

            try:
                logger.debug(
                    f"Calling async {func_name}",
                    extra={
                        'function': func_name,
                        'async': True,
                        'args_count': len(args) if args else 0,
                        'kwargs_keys': list(kwargs.keys()) if kwargs else [],
                    }
                )

                result = await func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                logger.debug(
                    f"Completed async {func_name}",
                    extra={
                        'function': func_name,
                        'async': True,
                        'duration_ms': duration_ms,
                        'success': True,
                    }
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                logger.error(
                    f"Failed async {func_name}: {str(e)}",
                    extra={
                        'function': func_name,
                        'async': True,
                        'duration_ms': duration_ms,
                        'success': False,
                        'error': str(e),
                    }
                )
                raise

        return wrapper
    return decorator


class PerformanceLogger:
    """Context manager for logging performance metrics."""

    def __init__(self, logger: logging.Logger, operation: str, extra_context: Optional[Dict[str, Any]] = None):
        """Initialize performance logger.

        Args:
            logger: Logger instance
            operation: Operation name
            extra_context: Additional context to log
        """
        self.logger = logger
        self.operation = operation
        self.extra_context = extra_context or {}
        self.start_time = None

    def __enter__(self):
        """Start timing the operation."""
        import time
        self.start_time = time.time()

        self.logger.debug(
            f"Starting {self.operation}",
            extra={'operation': self.operation, 'phase': 'start', **self.extra_context}
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log the operation."""
        import time

        if self.start_time is None:
            return

        duration_ms = (time.time() - self.start_time) * 1000

        extra = {
            'operation': self.operation,
            'phase': 'complete',
            'duration_ms': duration_ms,
            **self.extra_context
        }

        if exc_type is not None:
            extra['success'] = False
            extra['error'] = str(exc_val)
            self.logger.error(
                f"Failed {self.operation}",
                extra=extra
            )
        else:
            extra['success'] = True
            self.logger.info(
                f"Completed {self.operation}",
                extra=extra
            )


class TradingLogger:
    """Specialized logger for trading operations."""

    def __init__(self, name: str = "trading"):
        """Initialize trading logger.

        Args:
            name: Logger name
        """
        self.logger = get_logger(name)
        self._trade_context = {}

    def set_trade_context(self, **context):
        """Set trading context for subsequent log messages.

        Args:
            **context: Trading context (trade_id, symbol, strategy, etc.)
        """
        self._trade_context.update(context)

    def clear_trade_context(self):
        """Clear trading context."""
        self._trade_context.clear()

    def log_order_placed(self, order_id: str, symbol: str, side: str, quantity: float, price: float, **kwargs):
        """Log order placement.

        Args:
            order_id: Order ID
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            price: Order price
            **kwargs: Additional order details
        """
        self.logger.info(
            f"Order placed: {side.upper()} {quantity} {symbol} @ {price}",
            extra={
                'event': 'order_placed',
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'order_value': quantity * price,
                **self._trade_context,
                **kwargs
            }
        )

    def log_order_filled(self, order_id: str, symbol: str, side: str, quantity: float, price: float, fee: float = 0.0, **kwargs):
        """Log order fill.

        Args:
            order_id: Order ID
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Filled quantity
            price: Fill price
            fee: Transaction fee
            **kwargs: Additional fill details
        """
        self.logger.info(
            f"Order filled: {side.upper()} {quantity} {symbol} @ {price}",
            extra={
                'event': 'order_filled',
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'fee': fee,
                'order_value': quantity * price,
                **self._trade_context,
                **kwargs
            }
        )

    def log_position_opened(self, symbol: str, quantity: float, avg_price: float, **kwargs):
        """Log position opening.

        Args:
            symbol: Trading symbol
            quantity: Position quantity
            avg_price: Average entry price
            **kwargs: Additional position details
        """
        self.logger.info(
            f"Position opened: {quantity} {symbol} @ {avg_price}",
            extra={
                'event': 'position_opened',
                'symbol': symbol,
                'quantity': quantity,
                'avg_price': avg_price,
                'position_value': quantity * avg_price,
                **self._trade_context,
                **kwargs
            }
        )

    def log_position_closed(self, symbol: str, quantity: float, entry_price: float, exit_price: float, pnl: float, **kwargs):
        """Log position closing.

        Args:
            symbol: Trading symbol
            quantity: Position quantity
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/loss amount
            **kwargs: Additional position details
        """
        pnl_percentage = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

        self.logger.info(
            f"Position closed: {quantity} {symbol} | Entry: {entry_price} | Exit: {exit_price} | PnL: {pnl} ({pnl_percentage:.2f}%)",
            extra={
                'event': 'position_closed',
                'symbol': symbol,
                'quantity': quantity,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'position_value': quantity * exit_price,
                **self._trade_context,
                **kwargs
            }
        )

    def log_risk_check(self, symbol: str, risk_level: float, threshold: float, passed: bool, **kwargs):
        """Log risk management check.

        Args:
            symbol: Trading symbol
            risk_level: Current risk level
            threshold: Risk threshold
            passed: Whether risk check passed
            **kwargs: Additional risk details
        """
        self.logger.warning(
            f"Risk check {'PASSED' if passed else 'FAILED'}: {symbol} risk {risk_level:.2f} vs threshold {threshold:.2f}",
            extra={
                'event': 'risk_check',
                'symbol': symbol,
                'risk_level': risk_level,
                'threshold': threshold,
                'passed': passed,
                **self._trade_context,
                **kwargs
            }
        ) if not passed else self.logger.debug(
            f"Risk check passed: {symbol} risk {risk_level:.2f} vs threshold {threshold:.2f}",
            extra={
                'event': 'risk_check',
                'symbol': symbol,
                'risk_level': risk_level,
                'threshold': threshold,
                'passed': passed,
                **self._trade_context,
                **kwargs
            }
        )


# Convenience functions for common logging patterns
def log_api_call(logger: logging.Logger, method: str, url: str, status_code: Optional[int] = None, duration_ms: Optional[float] = None, **kwargs):
    """Log API call details.

    Args:
        logger: Logger instance
        method: HTTP method
        url: API URL
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional request details
    """
    extra = {
        'event': 'api_call',
        'http_method': method,
        'url': url,
        **kwargs
    }

    if status_code is not None:
        extra['status_code'] = status_code

    if duration_ms is not None:
        extra['duration_ms'] = duration_ms

    if status_code and status_code >= 400:
        logger.error(f"API call failed: {method} {url}", extra=extra)
    else:
        logger.info(f"API call: {method} {url}", extra=extra)


def log_websocket_event(logger: logging.Logger, event: str, symbol: Optional[str] = None, **kwargs):
    """Log WebSocket event.

    Args:
        logger: Logger instance
        event: WebSocket event type
        symbol: Trading symbol (if applicable)
        **kwargs: Additional event details
    """
    extra = {
        'event': 'websocket',
        'ws_event': event,
        **kwargs
    }

    if symbol:
        extra['symbol'] = symbol

    logger.info(f"WebSocket event: {event}", extra=extra)


def log_error_with_context(logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None, **kwargs):
    """Log error with additional context.

    Args:
        logger: Logger instance
        error: Exception instance
        context: Additional context
        **kwargs: Additional error details
    """
    extra = {
        'event': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        **kwargs
    }

    if context:
        extra.update(context)

    logger.error(f"Error: {type(error).__name__}: {str(error)}", extra=extra)


def log_strategy_signal(logger: logging.Logger, strategy: str, symbol: str, signal: str, confidence: float, **kwargs):
    """Log trading strategy signal.

    Args:
        logger: Logger instance
        strategy: Strategy name
        symbol: Trading symbol
        signal: Trading signal (buy/sell/hold)
        confidence: Signal confidence (0-1)
        **kwargs: Additional signal details
    """
    logger.info(
        f"Strategy signal: {strategy} -> {signal.upper()} {symbol} (confidence: {confidence:.2f})",
        extra={
            'event': 'strategy_signal',
            'strategy': strategy,
            'symbol': symbol,
            'signal': signal,
            'confidence': confidence,
            **kwargs
        }
    )


# Initialize logging when module is imported
def initialize_logging() -> None:
    """Initialize logging with default settings."""
    try:
        settings = get_settings()
        setup_logging()
    except Exception:
        # Fallback configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )


# Auto-initialize logging if settings are available
try:
    initialize_logging()
except Exception:
    # If settings aren't available yet, use basic config
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )