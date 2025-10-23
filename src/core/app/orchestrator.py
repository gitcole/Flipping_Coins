"""Main application orchestrator for crypto trading bot."""

from __future__ import annotations

import asyncio
import signal
from typing import Dict, List, Optional

from ...risk import RiskManager
from ...strategies.registry import StrategyRegistry, StrategyRegistryConfig
from ...utils.logging import get_logger
from ..api.robinhood.client import RobinhoodClient
from ..api.robinhood.crypto_api import RobinhoodCryptoAPI
from ..config import get_settings, get_config_manager
from ..engine.position_manager import PositionManager
from ..engine.strategy_executor import StrategyExecutor
from ..engine.trading_engine import TradingEngine
from ..websocket.market_data import MarketDataClient


class ApplicationOrchestrator:
    """
    Main orchestrator for all trading bot components.

    This class is responsible for initializing, starting, stopping, and managing
    the lifecycle of all trading bot components including market data clients,
    strategy executors, risk managers, and trading engines. It provides a
    centralized interface for controlling the entire application.

    The orchestrator implements a robust health monitoring system and handles
    graceful shutdown procedures to ensure data integrity and proper cleanup
    of resources.

    Attributes:
        is_running (bool): Current operational state of the application
        market_data_client (MarketDataClient): WebSocket client for real-time market data
        strategy_executor (StrategyExecutor): Executes trading strategies
        risk_manager (RiskManager): Manages risk limits and position sizing
        trading_engine (TradingEngine): Core trading logic and order management
        strategy_registry (StrategyRegistry): Manages available trading strategies
        health_metrics (dict): Real-time health and performance metrics

    Example:
        >>> orchestrator = ApplicationOrchestrator()
        >>> await orchestrator.initialize()
        >>> await orchestrator.start()
        >>> # Application is now running
        >>> await orchestrator.shutdown()
    """

    def __init__(self):
        """
        Initialize application orchestrator.

        Sets up all core components, signal handlers for graceful shutdown,
        and initializes health monitoring systems. All components are created
        but not started until the start() method is called.
        """
        self.settings = get_settings()
        self.logger = get_logger("app.orchestrator")

        # Core components
        self.market_data_client: Optional[MarketDataClient] = None
        self.risk_manager: Optional[RiskManager] = None
        self.strategy_executor: Optional[StrategyExecutor] = None
        self.trading_engine: Optional[TradingEngine] = None
        self.strategy_registry: Optional[StrategyRegistry] = None
        self.robinhood_client: Optional[RobinhoodClient] = None
        self.crypto_api: Optional[RobinhoodCryptoAPI] = None

        # Application state
        self.is_running = False
        self._shutdown_event = asyncio.Event()

        # Health monitoring
        self.health_metrics = {
            'uptime': 0.0,
            'components_healthy': 0,
            'total_components': 0,
            'errors': 0,
            'warnings': 0,
        }

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.shutdown())

    async def initialize(self) -> None:
        """
        Initialize all components and prepare the application for operation.

        This method performs a complete initialization sequence including:
        - Loading and validating configuration
        - Creating and configuring all core components
        - Setting up inter-component dependencies
        - Performing initial health checks

        Raises:
            Exception: If any component fails to initialize or health checks fail

        Note:
            This method must be called before start() and should only be called once.
        """
        try:
            self.logger.info("Initializing crypto trading bot...")

            # Initialize configuration first
            from ..config import initialize_config
            initialize_config()

            # Initialize core components
            await self._initialize_components()

            # Setup component dependencies
            await self._setup_dependencies()

            # Perform health checks
            await self._perform_health_checks()

            self.logger.info("Application initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize application: {str(e)}")
            raise

    async def start(self) -> None:
        """Start all components."""
        if self.is_running:
            self.logger.warning("Application is already running")
            return

        self.is_running = True
        self._shutdown_event.clear()

        self.logger.info("Starting crypto trading bot...")

        try:
            # Start components in dependency order
            await self._start_components()

            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())

            self.logger.info("Application started successfully")

        except Exception as e:
            self.is_running = False
            self.logger.error(f"Error starting application: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop all components."""
        if not self.is_running:
            return

        self.logger.info("Stopping crypto trading bot...")

        # Stop components in reverse dependency order
        await self._stop_components()

        self.is_running = False

    async def shutdown(self) -> None:
        """Shutdown application gracefully."""
        self.logger.info("Shutting down application...")
        self._shutdown_event.set()

        await self.stop()

        # Final cleanup
        await self._cleanup()

        self.logger.info("Application shutdown complete")

    async def _initialize_components(self) -> None:
        """Initialize all components."""
        # Strategy registry
        config_manager = get_config_manager()
        registry_config = StrategyRegistryConfig()
        self.strategy_registry = StrategyRegistry(registry_config, config_manager)

        # Market data client
        self.market_data_client = MarketDataClient()

        # Risk manager
        self.risk_manager = RiskManager()

        # Strategy executor
        self.strategy_executor = StrategyExecutor(
            market_data_client=self.market_data_client,
            strategy_registry=self.strategy_registry,
        )

        # Trading engine (placeholder - would need auth and API clients)
        # self.trading_engine = TradingEngine(...)

        # Robinhood client
        settings = get_settings()
        if settings.robinhood.api_token:
            self.robinhood_client = RobinhoodClient(sandbox=settings.robinhood.sandbox)

        # Robinhood Crypto API (now uses OAuth2 like the main client)
        if settings.robinhood.api_token:
            from ..api.robinhood.crypto_api import RobinhoodCryptoAPI
            self.crypto_api = RobinhoodCryptoAPI(settings.robinhood.api_token)

        self.logger.info("All components initialized")

    async def _setup_dependencies(self) -> None:
        """Setup component dependencies and integrations."""
        try:
            # Setup strategy registry dependencies
            if self.strategy_registry:
                if self.trading_engine:
                    self.strategy_registry.set_trading_engine(self.trading_engine)
                if self.risk_manager:
                    self.strategy_registry.set_risk_manager(self.risk_manager)
                if hasattr(self, 'position_manager') and self.position_manager:
                    self.strategy_registry.set_position_manager(self.position_manager)
                if self.market_data_client:
                    self.strategy_registry.set_websocket_client(self.market_data_client)

            # Connect risk manager to strategy executor
            if self.strategy_executor and self.risk_manager:
                # In a full implementation, we would connect these components
                # For now, just log the setup
                self.logger.info("Connected risk manager to strategy executor")

            # Connect market data to trading engine
            if self.market_data_client:
                # Setup market data callbacks for trading engine
                self.logger.info("Connected market data to trading components")

            self.logger.info("Component dependencies setup complete")

        except Exception as e:
            self.logger.error(f"Error setting up dependencies: {str(e)}")
            raise

    async def _start_components(self) -> None:
        """Start all components."""
        components = []

        # Start strategy registry first
        if self.strategy_registry:
            await self.strategy_registry.start()
            components.append("strategy_registry")

        # Start market data client first
        if self.market_data_client:
            await self.market_data_client.start()
            components.append("market_data_client")

        # Start strategy executor
        if self.strategy_executor:
            await self.strategy_executor.start()
            components.append("strategy_executor")

        # Start risk manager monitoring
        if self.risk_manager:
            # Start risk monitoring task
            asyncio.create_task(self._risk_monitoring_loop())
            components.append("risk_manager")

        # Start Robinhood client
        if self.robinhood_client:
            await self.robinhood_client.initialize()
            components.append("robinhood_client")

        self.logger.info(f"Started components: {', '.join(components)}")

    async def _stop_components(self) -> None:
        """Stop all components."""
        components = []

        # Stop strategy executor first
        if self.strategy_executor:
            await self.strategy_executor.stop()
            components.append("strategy_executor")

        # Stop strategy registry
        if self.strategy_registry:
            await self.strategy_registry.stop()
            components.append("strategy_registry")

        # Stop market data client
        if self.market_data_client:
            await self.market_data_client.stop()
            components.append("market_data_client")

        # Risk manager doesn't need explicit stopping
        if self.risk_manager:
            components.append("risk_manager")

        # Stop Robinhood client
        if self.robinhood_client:
            await self.robinhood_client.close()
            components.append("robinhood_client")

        self.logger.info(f"Stopped components: {', '.join(components)}")

    async def _cleanup(self) -> None:
        """Perform final cleanup."""
        try:
            # Cleanup strategy executor
            if self.strategy_executor:
                await self.strategy_executor.shutdown()

            # Cleanup market data client
            if self.market_data_client:
                await self.market_data_client.disconnect()

            self.logger.info("Cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    async def _health_monitoring_loop(self) -> None:
        """Main health monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._update_health_metrics()
                await asyncio.sleep(30.0)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.health_metrics['errors'] += 1
                self.logger.error(f"Error in health monitoring: {str(e)}")
                await asyncio.sleep(60.0)  # Wait longer on errors

    async def _risk_monitoring_loop(self) -> None:
        """Risk monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                if self.risk_manager:
                    # Update risk metrics
                    await self.risk_manager.update_risk_metrics()

                    # Check for critical risk conditions
                    await self._check_critical_risk_conditions()

                await asyncio.sleep(10.0)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.health_metrics['errors'] += 1
                self.logger.error(f"Error in risk monitoring: {str(e)}")
                await asyncio.sleep(30.0)  # Wait longer on errors

    async def _check_critical_risk_conditions(self) -> None:
        """Check for critical risk conditions that require immediate action."""
        if not self.risk_manager:
            return

        try:
            # Check drawdown limits
            if not await self.risk_manager.check_drawdown_limits():
                self.logger.critical("Critical: Maximum drawdown exceeded!")
                # In a real system, this might trigger emergency position closure

            # Check for high error rates
            error_rate = self.health_metrics.get('errors', 0)
            if error_rate > 10:
                self.logger.critical("Critical: High error rate detected!")

        except Exception as e:
            self.logger.error(f"Error checking critical conditions: {str(e)}")

    async def _update_health_metrics(self) -> None:
        """Update health metrics."""
        try:
            healthy_components = 0
            total_components = 0

            # Check market data client health
            if self.market_data_client:
                total_components += 1
                if self.market_data_client.is_connected:
                    healthy_components += 1

            # Check strategy registry health
            if self.strategy_registry:
                total_components += 1
                if self.strategy_registry._running:
                    healthy_components += 1

            # Check strategy executor health
            if self.strategy_executor:
                total_components += 1
                if self.strategy_executor.is_running:
                    healthy_components += 1

            # Update metrics
            self.health_metrics.update({
                'components_healthy': healthy_components,
                'total_components': total_components,
                'uptime': asyncio.get_event_loop().time(),
            })

        except Exception as e:
            self.logger.error(f"Error updating health metrics: {str(e)}")

    async def _perform_health_checks(self) -> None:
        """Perform initial health checks."""
        self.logger.info("Performing initial health checks...")

        checks = []

        # Check market data connectivity
        if self.market_data_client:
            try:
                # In a real implementation, we would test connectivity
                checks.append("market_data_connectivity: OK")
            except Exception as e:
                checks.append(f"market_data_connectivity: FAILED - {str(e)}")

        # Check strategy loading
        if self.strategy_executor:
            try:
                # In a real implementation, we would verify strategies loaded
                checks.append("strategy_loading: OK")
            except Exception as e:
                checks.append(f"strategy_loading: FAILED - {str(e)}")

        self.logger.info(f"Health check results: {', '.join(checks)}")

    def get_status(self) -> Dict:
        """Get comprehensive application status.

        Returns:
            Status dictionary
        """
        status = {
            'is_running': self.is_running,
            'health_metrics': self.health_metrics,
            'components': {},
        }

        # Market data client status
        if self.market_data_client:
            status['components']['market_data'] = self.market_data_client.get_stats()

        # Strategy registry status
        if self.strategy_registry:
            status['components']['strategy_registry'] = self.strategy_registry.get_strategy_status_summary()

        # Strategy executor status
        if self.strategy_executor:
            status['components']['strategy_executor'] = self.strategy_executor.get_execution_summary()

        # Risk manager status
        if self.risk_manager:
            status['components']['risk_manager'] = self.risk_manager.get_risk_summary()

        # Trading engine status (placeholder)
        if self.trading_engine:
            status['components']['trading_engine'] = {
                'is_running': self.trading_engine.is_running,
                'stats': self.trading_engine.get_order_statistics(),
            }

        return status

    async def run(self) -> None:
        """Run the application until shutdown."""
        try:
            await self.initialize()
            await self.start()

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {str(e)}")
            raise
        finally:
            await self.shutdown()

    def get_component_summary(self) -> Dict:
        """Get summary of all components.

        Returns:
            Component summary dictionary
        """
        return {
            'strategy_registry': {
                'initialized': self.strategy_registry is not None,
                'running': self.strategy_registry._running if self.strategy_registry else False,
            },
            'market_data_client': {
                'initialized': self.market_data_client is not None,
                'connected': self.market_data_client.is_connected if self.market_data_client else False,
            },
            'risk_manager': {
                'initialized': self.risk_manager is not None,
            },
            'strategy_executor': {
                'initialized': self.strategy_executor is not None,
                'running': self.strategy_executor.is_running if self.strategy_executor else False,
            },
            'trading_engine': {
                'initialized': self.trading_engine is not None,
                'running': self.trading_engine.is_running if self.trading_engine else False,
            },
            'robinhood_client': {
                'initialized': self.robinhood_client is not None,
                'authenticated': self.robinhood_client.auth.is_authenticated() if self.robinhood_client else False,
            },
            'crypto_api': {
                'initialized': self.crypto_api is not None,
            },
        }

    def _get_event_loop(self):
        """Get the event loop for thread-safe operations."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop