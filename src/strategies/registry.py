"""
Strategy registry system for dynamic loading and management.

This module provides centralized strategy management with hot-swapping,
health monitoring, and failover capabilities for trading strategies.
"""

import asyncio
import importlib
import inspect
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from ..core.config import ConfigurationManager
from ..utils.logging import get_logger
from .base import BaseStrategy, StrategyConfig, StrategyStatus, TradingSignal


class StrategyHealth(Enum):
    """Strategy health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


class DependencyStatus(Enum):
    """Strategy dependency status enumeration."""
    AVAILABLE = "available"
    MISSING = "missing"
    ERROR = "error"


@dataclass
class StrategyDependency:
    """Represents a strategy dependency."""
    name: str
    type: str  # "component", "data_source", "config"
    required: bool = True
    status: DependencyStatus = DependencyStatus.MISSING
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class StrategyInfo:
    """Information about a registered strategy."""
    name: str
    class_type: Type[BaseStrategy]
    config: StrategyConfig
    instance: Optional[BaseStrategy] = None
    status: StrategyStatus = StrategyStatus.STOPPED
    health: StrategyHealth = StrategyHealth.UNHEALTHY
    dependencies: List[StrategyDependency] = field(default_factory=list)
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    warning_count: int = 0
    start_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class StrategyRegistryConfig(BaseModel):
    """Configuration for the strategy registry."""

    health_check_interval: int = Field(30, description="Health check interval in seconds")
    max_consecutive_failures: int = Field(5, description="Max consecutive failures before marking unhealthy")
    dependency_timeout: int = Field(10, description="Timeout for dependency checks in seconds")
    enable_hot_swap: bool = Field(True, description="Enable hot-swapping of strategies")
    max_strategy_instances: int = Field(10, description="Maximum number of strategy instances")


class StrategyRegistry:
    """
    Centralized registry for managing trading strategies.

    Provides dynamic loading, health monitoring, hot-swapping, and failover
    capabilities for all trading strategies in the system.
    """

    def __init__(self, config: StrategyRegistryConfig, config_manager: ConfigurationManager):
        """Initialize the strategy registry.

        Args:
            config: Registry configuration
            config_manager: Global configuration manager
        """
        self.config = config
        self.config_manager = config_manager

        # Registry state
        self._strategies: Dict[str, StrategyInfo] = {}
        self._strategy_classes: Dict[str, Type[BaseStrategy]] = {}
        self._running = False
        self._health_check_task = None
        self._dependency_check_task = None

        # Core components (to be injected)
        self._trading_engine = None
        self._risk_manager = None
        self._position_manager = None
        self._websocket_client = None

        # Logging
        self.logger = get_logger("strategy.registry")

        # Performance tracking
        self._registry_stats = {
            "total_registrations": 0,
            "total_failures": 0,
            "total_health_checks": 0,
            "last_health_check": None
        }

    def set_trading_engine(self, trading_engine):
        """Set the trading engine reference."""
        self._trading_engine = trading_engine

    def set_risk_manager(self, risk_manager):
        """Set the risk manager reference."""
        self._risk_manager = risk_manager

    def set_position_manager(self, position_manager):
        """Set the position manager reference."""
        self._position_manager = position_manager

    def set_websocket_client(self, websocket_client):
        """Set the websocket client reference."""
        self._websocket_client = websocket_client

    async def start(self) -> bool:
        """
        Start the strategy registry.

        Returns:
            True if started successfully
        """
        try:
            self.logger.info("Starting strategy registry")

            self._running = True

            # Start background tasks
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._dependency_check_task = asyncio.create_task(self._dependency_check_loop())

            # Load strategies from configuration
            await self._load_strategies_from_config()

            self.logger.info("Strategy registry started successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to start strategy registry", error=str(e))
            return False

    async def stop(self) -> bool:
        """
        Stop the strategy registry.

        Returns:
            True if stopped successfully
        """
        try:
            self.logger.info("Stopping strategy registry")

            self._running = False

            # Stop all running strategies
            await self.stop_all_strategies()

            # Cancel background tasks
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            if self._dependency_check_task and not self._dependency_check_task.done():
                self._dependency_check_task.cancel()
                try:
                    await self._dependency_check_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Strategy registry stopped successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to stop strategy registry", error=str(e))
            return False

    def register_strategy_class(self, name: str, strategy_class: Type[BaseStrategy]) -> bool:
        """
        Register a strategy class.

        Args:
            name: Strategy name
            strategy_class: Strategy class type

        Returns:
            True if registered successfully
        """
        try:
            # Validate strategy class
            if not self._validate_strategy_class(strategy_class):
                self.logger.error("Invalid strategy class", strategy_name=name)
                return False

            self._strategy_classes[name] = strategy_class
            self._registry_stats["total_registrations"] += 1

            self.logger.info(f"Strategy class registered successfully, strategy_name={name}, class_name={strategy_class.__name__}")

            return True

        except Exception as e:
            self.logger.error("Failed to register strategy class",
                            strategy_name=name, error=str(e))
            return False

    async def create_strategy(self, name: str, config: StrategyConfig) -> bool:
        """
        Create and register a strategy instance.

        Args:
            name: Strategy name
            config: Strategy configuration

        Returns:
            True if created successfully
        """
        try:
            # Check if strategy class is registered
            if name not in self._strategy_classes:
                self.logger.error("Strategy class not registered", strategy_name=name)
                return False

            # Check if strategy already exists
            if name in self._strategies:
                self.logger.error("Strategy already exists", strategy_name=name)
                return False

            strategy_class = self._strategy_classes[name]

            # Create strategy instance
            strategy_instance = strategy_class(config, self.config_manager)

            # Set component references
            if self._trading_engine:
                strategy_instance.set_trading_engine(self._trading_engine)
            if self._risk_manager:
                strategy_instance.set_risk_manager(self._risk_manager)
            if self._position_manager:
                strategy_instance.set_position_manager(self._position_manager)
            if self._websocket_client:
                strategy_instance.set_websocket_client(self._websocket_client)

            # Create strategy info
            strategy_info = StrategyInfo(
                name=name,
                class_type=strategy_class,
                config=config,
                instance=strategy_instance,
                status=StrategyStatus.INITIALIZING
            )

            # Check dependencies
            await self._check_strategy_dependencies(strategy_info)

            self._strategies[name] = strategy_info

            self.logger.info(f"Strategy instance created successfully, strategy_name={name}, status={strategy_info.status.value}")

            return True

        except Exception as e:
            self.logger.error("Failed to create strategy instance",
                           strategy_name=name, error=str(e))
            return False

    async def start_strategy(self, name: str) -> bool:
        """
        Start a specific strategy.

        Args:
            name: Strategy name

        Returns:
            True if started successfully
        """
        try:
            if name not in self._strategies:
                self.logger.error("Strategy not found", strategy_name=name)
                return False

            strategy_info = self._strategies[name]

            if strategy_info.instance is None:
                self.logger.error("Strategy instance is None", strategy_name=name)
                return False

            # Check dependencies before starting
            dependency_healthy = await self._check_strategy_dependencies(strategy_info)
            if not dependency_healthy:
                self.logger.warning(f"Strategy dependencies not healthy, but attempting to start, strategy_name={name}")

            # Initialize strategy
            if not await strategy_info.instance.initialize():
                self.logger.error("Strategy initialization failed", strategy_name=name)
                return False

            # Start strategy
            if not await strategy_info.instance.start():
                self.logger.error("Strategy start failed", strategy_name=name)
                return False

            strategy_info.status = StrategyStatus.RUNNING
            strategy_info.start_count += 1
            strategy_info.updated_at = datetime.now()

            self.logger.info("Strategy started successfully", strategy_name=name)
            return True

        except Exception as e:
            self.logger.error("Failed to start strategy", strategy_name=name, error=str(e))
            return False

    async def stop_strategy(self, name: str) -> bool:
        """
        Stop a specific strategy.

        Args:
            name: Strategy name

        Returns:
            True if stopped successfully
        """
        try:
            if name not in self._strategies:
                self.logger.error("Strategy not found", strategy_name=name)
                return False

            strategy_info = self._strategies[name]

            if strategy_info.instance is None:
                self.logger.error("Strategy instance is None", strategy_name=name)
                return False

            # Stop strategy
            if not await strategy_info.instance.stop():
                self.logger.error("Strategy stop failed", strategy_name=name)

            strategy_info.status = StrategyStatus.STOPPED
            strategy_info.updated_at = datetime.now()

            self.logger.info("Strategy stopped successfully", strategy_name=name)
            return True

        except Exception as e:
            self.logger.error("Failed to stop strategy", strategy_name=name, error=str(e))
            return False

    async def hot_swap_strategy(self, name: str, new_config: StrategyConfig) -> bool:
        """
        Hot-swap a strategy with new configuration.

        Args:
            name: Strategy name
            new_config: New strategy configuration

        Returns:
            True if swapped successfully
        """
        try:
            if not self.config.enable_hot_swap:
                self.logger.error("Hot-swapping is disabled")
                return False

            if name not in self._strategies:
                self.logger.error("Strategy not found", strategy_name=name)
                return False

            strategy_info = self._strategies[name]

            if strategy_info.instance is None:
                self.logger.error("Strategy instance is None", strategy_name=name)
                return False

            self.logger.info(f"Starting hot-swap of strategy, strategy_name={name}")

            # Pause strategy
            await strategy_info.instance.pause()

            # Update configuration
            old_config = strategy_info.config
            strategy_info.config = new_config
            strategy_info.instance.config = new_config

            # Validate new configuration
            await strategy_info.instance._validate_configuration()

            # Resume strategy
            await strategy_info.instance.resume()

            strategy_info.updated_at = datetime.now()

            self.logger.info(f"Strategy hot-swapped successfully, strategy_name={name}, old_config={old_config.name}, new_config={new_config.name}")

            return True

        except Exception as e:
            self.logger.error("Failed to hot-swap strategy",
                           strategy_name=name, error=str(e))
            return False

    async def remove_strategy(self, name: str) -> bool:
        """
        Remove a strategy from the registry.

        Args:
            name: Strategy name

        Returns:
            True if removed successfully
        """
        try:
            if name not in self._strategies:
                self.logger.error("Strategy not found", strategy_name=name)
                return False

            strategy_info = self._strategies[name]

            # Stop strategy if running
            if strategy_info.status == StrategyStatus.RUNNING:
                await self.stop_strategy(name)

            # Remove from registry
            del self._strategies[name]

            self.logger.info("Strategy removed successfully", strategy_name=name)
            return True

        except Exception as e:
            self.logger.error("Failed to remove strategy", strategy_name=name, error=str(e))
            return False

    async def start_all_strategies(self) -> int:
        """
        Start all registered strategies.

        Returns:
            Number of strategies started successfully
        """
        started_count = 0

        for name in self._strategies.keys():
            if await self.start_strategy(name):
                started_count += 1

        self.logger.info(f"Started all strategies, total_started={started_count}")
        return started_count

    async def stop_all_strategies(self) -> int:
        """
        Stop all running strategies.

        Returns:
            Number of strategies stopped successfully
        """
        stopped_count = 0

        for name in self._strategies.keys():
            if await self.stop_strategy(name):
                stopped_count += 1

        self.logger.info(f"Stopped all strategies, total_stopped={stopped_count}")
        return stopped_count

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """
        Get a strategy instance by name.

        Args:
            name: Strategy name

        Returns:
            Strategy instance or None if not found
        """
        if name not in self._strategies:
            return None

        return self._strategies[name].instance

    def get_strategy_info(self, name: str) -> Optional[StrategyInfo]:
        """
        Get strategy information by name.

        Args:
            name: Strategy name

        Returns:
            Strategy info or None if not found
        """
        return self._strategies.get(name)

    def get_all_strategies(self) -> Dict[str, StrategyInfo]:
        """
        Get all registered strategies.

        Returns:
            Dictionary of strategy name to strategy info
        """
        return self._strategies.copy()

    def get_running_strategies(self) -> Dict[str, StrategyInfo]:
        """
        Get all running strategies.

        Returns:
            Dictionary of running strategy name to strategy info
        """
        return {
            name: info for name, info in self._strategies.items()
            if info.status == StrategyStatus.RUNNING and info.instance and info.instance.is_running
        }

    def get_strategy_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all strategy statuses.

        Returns:
            Dictionary containing strategy status summary
        """
        total = len(self._strategies)
        running = len(self.get_running_strategies())
        stopped = len([s for s in self._strategies.values() if s.status == StrategyStatus.STOPPED])
        error = len([s for s in self._strategies.values() if s.status == StrategyStatus.ERROR])

        return {
            "total_strategies": total,
            "running_strategies": running,
            "stopped_strategies": stopped,
            "error_strategies": error,
            "registry_stats": self._registry_stats.copy()
        }

    async def _health_check_loop(self):
        """Background task for health checking all strategies."""
        self.logger.info("Starting strategy health check loop")

        while self._running:
            try:
                await self._perform_health_checks()
                self._registry_stats["total_health_checks"] += 1
                self._registry_stats["last_health_check"] = datetime.now()

                await asyncio.sleep(self.config.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in health check loop", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry

        self.logger.info("Strategy health check loop stopped")

    async def _dependency_check_loop(self):
        """Background task for checking strategy dependencies."""
        self.logger.info("Starting dependency check loop")

        while self._running:
            try:
                for strategy_info in self._strategies.values():
                    await self._check_strategy_dependencies(strategy_info)

                await asyncio.sleep(self.config.dependency_timeout)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in dependency check loop", error=str(e))
                await asyncio.sleep(5)

        self.logger.info("Dependency check loop stopped")

    async def _perform_health_checks(self):
        """Perform health checks on all strategies."""
        for name, strategy_info in self._strategies.items():
            if strategy_info.instance is None:
                continue

            try:
                # Check strategy status
                if not strategy_info.instance.is_running:
                    strategy_info.health = StrategyHealth.UNHEALTHY
                    strategy_info.error_count += 1
                    continue

                # Check for recent activity (signals generated)
                metrics = strategy_info.instance.metrics
                current_time = datetime.now()

                # If strategy has been running but no recent signals, it might be degraded
                if (strategy_info.start_count > 0 and
                    strategy_info.instance._last_signal_time > 0 and
                    (current_time - strategy_info.instance._last_signal_time).seconds > 300):  # 5 minutes
                    strategy_info.health = StrategyHealth.DEGRADED
                    strategy_info.warning_count += 1
                else:
                    strategy_info.health = StrategyHealth.HEALTHY

                # Check error rate
                if strategy_info.error_count > self.config.max_consecutive_failures:
                    strategy_info.health = StrategyHealth.FAILED

                strategy_info.last_health_check = current_time
                strategy_info.updated_at = current_time

            except Exception as e:
                self.logger.error(f"Health check failed for strategy, strategy_name={name}, error={str(e)}")
                strategy_info.health = StrategyHealth.UNHEALTHY
                strategy_info.error_count += 1

    async def _check_strategy_dependencies(self, strategy_info: StrategyInfo) -> bool:
        """
        Check dependencies for a strategy.

        Args:
            strategy_info: Strategy information

        Returns:
            True if all dependencies are healthy
        """
        all_healthy = True

        # Check core components
        dependencies = [
            StrategyDependency("trading_engine", "component",
                             required=True, status=self._check_component_dependency("trading_engine")),
            StrategyDependency("risk_manager", "component",
                             required=True, status=self._check_component_dependency("risk_manager")),
            StrategyDependency("position_manager", "component",
                             required=True, status=self._check_component_dependency("position_manager")),
            StrategyDependency("websocket_client", "component",
                             required=False, status=self._check_component_dependency("websocket_client")),
        ]

        strategy_info.dependencies = dependencies

        for dep in dependencies:
            if dep.required and dep.status != DependencyStatus.AVAILABLE:
                all_healthy = False
                break

        return all_healthy

    def _check_component_dependency(self, component_name: str) -> DependencyStatus:
        """Check if a component dependency is available."""
        component_map = {
            "trading_engine": self._trading_engine,
            "risk_manager": self._risk_manager,
            "position_manager": self._position_manager,
            "websocket_client": self._websocket_client,
        }

        component = component_map.get(component_name)
        if component is not None:
            return DependencyStatus.AVAILABLE
        else:
            return DependencyStatus.MISSING

    def _validate_strategy_class(self, strategy_class: Type[BaseStrategy]) -> bool:
        """
        Validate that a class is a proper strategy implementation.

        Args:
            strategy_class: Class to validate

        Returns:
            True if valid strategy class
        """
        try:
            # Check if it's a class
            if not inspect.isclass(strategy_class):
                return False

            # Check if it inherits from BaseStrategy
            if not issubclass(strategy_class, BaseStrategy):
                return False

            # Check if it implements required abstract methods
            required_methods = ['generate_signal', 'calculate_position_size', 'validate_signal']
            for method_name in required_methods:
                if not hasattr(strategy_class, method_name):
                    return False
                method = getattr(strategy_class, method_name)
                if getattr(method, '__isabstractmethod__', False):
                    return False

            return True

        except Exception:
            return False

    async def _load_strategies_from_config(self):
        """Load strategies from configuration."""
        try:
            # This would load strategy configurations from the config manager
            # For now, we'll implement a basic version
            self.logger.info("Loading strategies from configuration")

            # Example: Load market making strategy if enabled
            # This would be expanded based on the actual configuration structure

        except Exception as e:
            self.logger.error(f"Failed to load strategies from configuration, error={str(e)}")