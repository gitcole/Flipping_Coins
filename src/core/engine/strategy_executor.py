"""Strategy execution engine for continuous automated trading."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from ...strategies.registry import StrategyRegistry
from ...utils.logging import get_logger
from ..config import get_settings
from ..websocket.market_data import MarketDataClient


class StrategyExecutionError(Exception):
    """Base exception for strategy execution errors."""
    pass


class StrategyExecutor:
    """Orchestrates strategy execution with continuous operation."""

    def __init__(
        self,
        market_data_client: Optional[MarketDataClient] = None,
        strategy_registry: Optional[StrategyRegistry] = None,
    ):
        """Initialize strategy executor.

        Args:
            market_data_client: Market data WebSocket client
            strategy_registry: Strategy registry instance
        """
        self.settings = get_settings()
        self.logger = get_logger("strategy.executor")

        self.market_data_client = market_data_client or MarketDataClient()
        self.strategy_registry = strategy_registry or StrategyRegistry()

        # Execution state
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._execution_task: Optional[asyncio.Task] = None

        # Strategy instances
        self.active_strategies: Dict[str, Any] = {}

        # Execution statistics
        self.execution_stats = {
            'cycles_completed': 0,
            'signals_generated': 0,
            'orders_placed': 0,
            'errors': 0,
            'last_execution_time': None,
        }

        # Execution configuration
        self.execution_interval = 1.0  # seconds
        self.max_strategies_per_cycle = 5

    async def initialize(self) -> None:
        """Initialize strategy executor."""
        try:
            self.logger.info("Initializing strategy executor...")

            # Initialize market data client
            await self.market_data_client.initialize_subscriptions()

            # Load and initialize strategies
            await self._load_strategies()

            # Setup market data callbacks
            self._setup_data_callbacks()

            self.logger.info("Strategy executor initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize strategy executor: {str(e)}")
            raise

    async def start(self) -> None:
        """Start strategy execution."""
        if self.is_running:
            self.logger.warning("Strategy executor is already running")
            return

        self.is_running = True
        self._shutdown_event.clear()

        self.logger.info("Starting strategy executor...")

        try:
            # Start market data client
            await self.market_data_client.start()

            # Start execution loop
            self._execution_task = asyncio.create_task(self._execution_loop())

        except Exception as e:
            self.is_running = False
            self.logger.error(f"Error starting strategy executor: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop strategy execution."""
        if not self.is_running:
            return

        self.logger.info("Stopping strategy executor...")
        self._shutdown_event.set()

        # Stop execution task
        if self._execution_task:
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass

        # Stop market data client
        await self.market_data_client.stop()

        self.is_running = False

    async def _execution_loop(self) -> None:
        """Main strategy execution loop."""
        self.logger.info("Starting strategy execution loop...")

        consecutive_errors = 0
        max_consecutive_errors = 5

        while not self._shutdown_event.is_set():
            try:
                # Execute strategy cycle
                await self._execute_strategy_cycle()

                # Update statistics
                self.execution_stats['cycles_completed'] += 1
                self.execution_stats['last_execution_time'] = asyncio.get_event_loop().time()

                # Reset error counter on successful execution
                consecutive_errors = 0

                # Wait for next cycle
                await asyncio.sleep(self.execution_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                self.execution_stats['errors'] += 1
                self.logger.error(f"Error in execution loop: {str(e)}")

                # If too many consecutive errors, take a longer break
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.warning(f"Too many consecutive errors ({consecutive_errors}), taking longer break")
                    await asyncio.sleep(30.0)  # 30 second break
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(5.0)  # Wait before retrying

    async def _execute_strategy_cycle(self) -> None:
        """Execute one cycle of strategy processing."""
        try:
            # Get active strategies
            active_strategies = list(self.active_strategies.values())

            if not active_strategies:
                return

            # Limit number of strategies per cycle for performance
            strategies_to_process = active_strategies[:self.max_strategies_per_cycle]

            # Execute strategies concurrently with timeout
            tasks = []
            for strategy in strategies_to_process:
                task = asyncio.create_task(self._execute_strategy_with_timeout(strategy))
                tasks.append(task)

            # Wait for all strategies to complete with overall timeout
            if tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=30.0  # 30 second timeout for entire cycle
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Strategy execution cycle timed out")
                    # Cancel all running tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()

        except Exception as e:
            self.logger.error(f"Error in strategy cycle: {str(e)}")

    async def _execute_strategy(self, strategy) -> None:
        """Execute a single strategy.

        Args:
            strategy: Strategy instance to execute
        """
        try:
            # Get current market data for strategy symbols with timeout
            try:
                market_data = await asyncio.wait_for(
                    self._get_strategy_market_data_async(strategy),
                    timeout=5.0  # 5 second timeout for market data
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"Market data timeout for strategy {strategy.name}")
                return

            if not market_data:
                return

            # Execute strategy logic with timeout
            try:
                signals = await asyncio.wait_for(
                    strategy.generate_signals(market_data),
                    timeout=10.0  # 10 second timeout for strategy execution
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"Strategy execution timeout: {strategy.name}")
                return

            if signals:
                self.execution_stats['signals_generated'] += len(signals)

                # Process trading signals with timeout for each
                for signal in signals:
                    try:
                        await asyncio.wait_for(
                            self._process_signal(strategy, signal),
                            timeout=5.0  # 5 second timeout per signal
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Signal processing timeout for {strategy.name}")
                        continue

        except Exception as e:
            self.logger.error(f"Error executing strategy {strategy.name}: {str(e)}")

    async def _execute_strategy_with_timeout(self, strategy) -> None:
        """Execute a single strategy with overall timeout.

        Args:
            strategy: Strategy instance to execute
        """
        try:
            await asyncio.wait_for(
                self._execute_strategy(strategy),
                timeout=15.0  # 15 second overall timeout per strategy
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Strategy {strategy.name} timed out completely")
        except Exception as e:
            self.logger.error(f"Error in strategy with timeout {strategy.name}: {str(e)}")

    def _get_strategy_market_data(self, strategy) -> Dict:
        """Get market data for strategy symbols (synchronous version).

        Args:
            strategy: Strategy instance

        Returns:
            Market data dictionary
        """
        market_data = {}

        for symbol in strategy.symbols:
            # Get ticker data
            ticker = self.market_data_client.get_ticker(symbol)
            if ticker:
                market_data[symbol] = {
                    'ticker': ticker,
                    'orderbook': self.market_data_client.get_orderbook(symbol),
                    'recent_trades': self.market_data_client.get_recent_trades(symbol, 10),
                }

        return market_data

    async def _get_strategy_market_data_async(self, strategy) -> Dict:
        """Get market data for strategy symbols (asynchronous version).

        Args:
            strategy: Strategy instance

        Returns:
            Market data dictionary
        """
        market_data = {}

        for symbol in strategy.symbols:
            try:
                # Get ticker data
                ticker = self.market_data_client.get_ticker(symbol)
                if ticker:
                    market_data[symbol] = {
                        'ticker': ticker,
                        'orderbook': self.market_data_client.get_orderbook(symbol),
                        'recent_trades': self.market_data_client.get_recent_trades(symbol, 10),
                    }
                else:
                    self.logger.debug(f"No ticker data available for {symbol}")
            except Exception as e:
                self.logger.warning(f"Error getting market data for {symbol}: {str(e)}")
                continue

        # Log if no market data is available for any symbols
        if not market_data and strategy.symbols:
            self.logger.info(f"No market data available for strategy {strategy.name} symbols: {strategy.symbols}")

        return market_data

    async def _process_signal(self, strategy, signal) -> None:
        """Process a trading signal from a strategy.

        Args:
            strategy: Strategy that generated the signal
            signal: Trading signal
        """
        try:
            # Validate signal format
            if not self._validate_signal(signal):
                self.logger.warning(f"Invalid signal format: {signal}")
                return

            # Extract signal data
            symbol = signal.get('symbol')
            side = signal.get('side')
            signal_type = signal.get('type', 'entry')

            if not symbol or not side:
                self.logger.warning(f"Missing symbol or side in signal: {signal}")
                return

            # Handle different signal types
            if signal_type == 'entry':
                await self._handle_entry_signal(strategy, signal)
            elif signal_type == 'exit':
                await self._handle_exit_signal(strategy, signal)
            elif signal_type == 'modify':
                await self._handle_modify_signal(strategy, signal)
            else:
                self.logger.warning(f"Unknown signal type: {signal_type}")

        except Exception as e:
            self.logger.error(f"Error processing signal: {str(e)}")

    async def _handle_entry_signal(self, strategy, signal) -> None:
        """Handle entry signal from strategy.

        Args:
            strategy: Strategy that generated the signal
            signal: Entry signal
        """
        try:
            symbol = signal['symbol']
            side = signal['side']
            quantity = signal.get('quantity', 0)
            price = signal.get('price')
            stop_loss = signal.get('stop_loss')
            take_profit = signal.get('take_profit')

            if quantity <= 0:
                self.logger.warning(f"Invalid quantity in entry signal: {quantity}")
                return

            # Here we would integrate with the trading engine to place orders
            # For now, just log the signal
            self.logger.info(
                f"Entry signal: {strategy.name} -> {side} {quantity} {symbol} "
                f"@ {price} (SL: {stop_loss}, TP: {take_profit})"
            )

            self.execution_stats['orders_placed'] += 1

        except Exception as e:
            self.logger.error(f"Error handling entry signal: {str(e)}")

    async def _handle_exit_signal(self, strategy, signal) -> None:
        """Handle exit signal from strategy.

        Args:
            strategy: Strategy that generated the signal
            signal: Exit signal
        """
        try:
            symbol = signal['symbol']
            quantity = signal.get('quantity', 0)

            # Here we would integrate with the trading engine to close positions
            self.logger.info(
                f"Exit signal: {strategy.name} -> Close {quantity} {symbol}"
            )

            self.execution_stats['orders_placed'] += 1

        except Exception as e:
            self.logger.error(f"Error handling exit signal: {str(e)}")

    async def _handle_modify_signal(self, strategy, signal) -> None:
        """Handle position modification signal from strategy.

        Args:
            strategy: Strategy that generated the signal
            signal: Modify signal
        """
        try:
            symbol = signal['symbol']
            modifications = signal.get('modifications', {})

            # Here we would integrate with the trading engine to modify positions
            self.logger.info(
                f"Modify signal: {strategy.name} -> Modify {symbol}: {modifications}"
            )

        except Exception as e:
            self.logger.error(f"Error handling modify signal: {str(e)}")

    def _validate_signal(self, signal: Dict) -> bool:
        """Validate trading signal format.

        Args:
            signal: Trading signal to validate

        Returns:
            True if signal is valid
        """
        required_fields = ['symbol', 'side']
        return all(field in signal for field in required_fields)

    async def _load_strategies(self) -> None:
        """Load and initialize trading strategies."""
        try:
            # Get enabled strategies from configuration
            enabled_strategies = self._get_enabled_strategies()

            for strategy_name in enabled_strategies:
                try:
                    # Get strategy instance
                    strategy = self.strategy_registry.get_strategy(strategy_name)
                    if strategy:
                        # Initialize strategy
                        await strategy.initialize()
                        self.active_strategies[strategy_name] = strategy

                        self.logger.info(f"Loaded strategy: {strategy_name}")

                except Exception as e:
                    self.logger.error(f"Error loading strategy {strategy_name}: {str(e)}")

            self.logger.info(f"Loaded {len(self.active_strategies)} strategies")

        except Exception as e:
            self.logger.error(f"Error loading strategies: {str(e)}")

    def _get_enabled_strategies(self) -> List[str]:
        """Get list of enabled strategies from configuration.

        Returns:
            List of enabled strategy names
        """
        enabled_strategies = []

        # Check market making strategy
        if self.settings.strategies.market_making.enabled:
            enabled_strategies.append('market_making')

        # Add other strategy checks here as more strategies are implemented

        return enabled_strategies

    def _setup_data_callbacks(self) -> None:
        """Setup market data callbacks for strategies."""
        # Ticker data callback
        def on_ticker_data(symbol: str, ticker_data: Dict):
            """Handle ticker data updates."""
            # Notify relevant strategies about ticker updates
            for strategy in self.active_strategies.values():
                if symbol in strategy.symbols:
                    # In a real implementation, strategies would be notified
                    # For now, just log
                    pass

        # Orderbook data callback
        def on_orderbook_data(symbol: str, orderbook_data: Dict):
            """Handle orderbook data updates."""
            for strategy in self.active_strategies.values():
                if symbol in strategy.symbols:
                    pass

        # Trade data callback
        def on_trade_data(symbol: str, trade_data: Dict):
            """Handle trade data updates."""
            for strategy in self.active_strategies.values():
                if symbol in strategy.symbols:
                    pass

        # Register callbacks
        self.market_data_client.add_ticker_callback(on_ticker_data)
        self.market_data_client.add_orderbook_callback(on_orderbook_data)
        self.market_data_client.add_trade_callback(on_trade_data)

    def get_execution_summary(self) -> Dict:
        """Get execution summary.

        Returns:
            Execution summary dictionary
        """
        uptime = None
        if self.execution_stats['last_execution_time']:
            uptime = asyncio.get_event_loop().time() - self.execution_stats['last_execution_time']

        return {
            'is_running': self.is_running,
            'active_strategies': list(self.active_strategies.keys()),
            'execution_stats': self.execution_stats,
            'market_data_connected': self.market_data_client.is_connected,
            'market_data_stats': self.market_data_client.get_stats(),
            'uptime_seconds': uptime,
        }

    async def shutdown(self) -> None:
        """Shutdown strategy executor gracefully."""
        self.logger.info("Shutting down strategy executor...")

        await self.stop()

        # Cleanup strategies
        for strategy in self.active_strategies.values():
            try:
                await strategy.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up strategy {strategy.name}: {str(e)}")

        self.active_strategies.clear()
        self.logger.info("Strategy executor shutdown complete")