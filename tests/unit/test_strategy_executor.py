"""
Comprehensive unit tests for StrategyExecutor core trading logic.

Tests cover strategy execution, signal processing, market data handling,
and lifecycle management for the core trading engine.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal
from datetime import datetime

from core.engine.strategy_executor import StrategyExecutor, StrategyExecutionError
from core.websocket.market_data import MarketDataClient
from strategies.registry import StrategyRegistry
from strategies.base.strategy import BaseStrategy, StrategyConfig, SignalDirection, TradingSignal
from tests.utils.base_test import UnitTestCase


class TestStrategyExecutor(UnitTestCase):
    """Test suite for StrategyExecutor class."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.mock_market_data_client = self.create_async_mock("market_data_client", spec=MarketDataClient)
        self.mock_strategy_registry = self.create_mock("strategy_registry", spec=StrategyRegistry)
        self.mock_strategy = self.create_async_mock("strategy")

        self.executor = StrategyExecutor(
            market_data_client=self.mock_market_data_client,
            strategy_registry=self.mock_strategy_registry
        )

    @pytest.mark.asyncio
    async def test_execute_strategy_cycle_success(self):
        """Test successful strategy cycle execution."""
        # Setup
        self.mock_strategy.name = "test_strategy"
        self.mock_strategy.symbols = ["BTC"]
        self.executor.active_strategies = {"test_strategy": self.mock_strategy}

        mock_ticker_data = {"price": 50000.0, "volume": 1000}
        self.mock_market_data_client.get_ticker.return_value = mock_ticker_data

        mock_signals = [
            {
                "symbol": "BTC",
                "side": "buy",
                "type": "entry",
                "quantity": 0.1
            }
        ]
        self.mock_strategy.generate_signals = AsyncMock(return_value=mock_signals)

        # Execute
        await self.executor._execute_strategy_cycle()

        # Verify
        self.mock_strategy.generate_signals.assert_called_once()
        self.mock_market_data_client.get_ticker.assert_called_with("BTC")
        assert self.executor.execution_stats['cycles_completed'] == 1

    @pytest.mark.asyncio
    async def test_execute_strategy_cycle_no_enabled_strategies(self):
        """Test strategy cycle with no enabled strategies."""
        # Setup
        self.executor.active_strategies = {}

        # Execute
        await self.executor._execute_strategy_cycle()

        # Verify
        assert self.executor.execution_stats['cycles_completed'] == 1
        # Should not attempt to process any strategies

    @pytest.mark.asyncio
    async def test_execute_strategy_single_strategy(self):
        """Test execution with single strategy."""
        # Setup
        self.mock_strategy.name = "single_strategy"
        self.mock_strategy.symbols = ["ETH"]
        self.executor.active_strategies = {"single_strategy": self.mock_strategy}

        mock_market_data = {
            "ETH": {
                "ticker": {"price": 3000.0},
                "orderbook": {"bids": [], "asks": []},
                "recent_trades": []
            }
        }

        with patch.object(self.executor, '_get_strategy_market_data', return_value=mock_market_data):
            self.mock_strategy.generate_signals = AsyncMock(return_value=[])

            # Execute
            await self.executor._execute_strategy(self.mock_strategy)

        # Verify
        self.mock_strategy.generate_signals.assert_called_once_with(mock_market_data)

    @pytest.mark.asyncio
    async def test_execute_strategy_multiple_strategies(self):
        """Test execution with multiple strategies."""
        # Setup
        strategies = {}
        for i in range(3):
            strategy = self.create_async_mock(f"strategy_{i}")
            strategy.name = f"strategy_{i}"
            strategy.symbols = ["BTC"]
            strategy.generate_signals = AsyncMock(return_value=[])
            strategies[f"strategy_{i}"] = strategy

        self.executor.active_strategies = strategies

        mock_market_data = {
            "BTC": {
                "ticker": {"price": 50000.0},
                "orderbook": {"bids": [], "asks": []},
                "recent_trades": []
            }
        }

        with patch.object(self.executor, '_get_strategy_market_data', return_value=mock_market_data):
            # Execute
            await self.executor._execute_strategy_cycle()

        # Verify
        assert self.executor.execution_stats['cycles_completed'] == 1

    @pytest.mark.asyncio
    async def test_process_signal_entry_signal(self):
        """Test entry signal processing."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        entry_signal = {
            "symbol": "BTC",
            "side": "buy",
            "type": "entry",
            "quantity": 0.1,
            "price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 51000.0
        }

        # Execute
        await self.executor._process_signal(self.mock_strategy, entry_signal)

        # Verify
        assert self.executor.execution_stats['signals_generated'] == 1
        assert self.executor.execution_stats['orders_placed'] == 1

    @pytest.mark.asyncio
    async def test_process_signal_exit_signal(self):
        """Test exit signal processing."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        exit_signal = {
            "symbol": "BTC",
            "side": "sell",
            "type": "exit",
            "quantity": 0.05
        }

        # Execute
        await self.executor._process_signal(self.mock_strategy, exit_signal)

        # Verify
        assert self.executor.execution_stats['signals_generated'] == 1
        assert self.executor.execution_stats['orders_placed'] == 1

    @pytest.mark.asyncio
    async def test_process_signal_modify_signal(self):
        """Test modify signal processing."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        modify_signal = {
            "symbol": "BTC",
            "side": "buy",
            "type": "modify",
            "modifications": {
                "stop_loss": 49500.0,
                "take_profit": 50500.0
            }
        }

        # Execute
        await self.executor._process_signal(self.mock_strategy, modify_signal)

        # Verify
        assert self.executor.execution_stats['signals_generated'] == 1

    def test_validate_signal_valid_format(self):
        """Test valid signal validation."""
        valid_signal = {
            "symbol": "BTC",
            "side": "buy"
        }

        result = self.executor._validate_signal(valid_signal)
        assert result is True

    def test_validate_signal_invalid_format(self):
        """Test invalid signal validation."""
        invalid_signal = {
            "symbol": "BTC"
            # Missing 'side' field
        }

        result = self.executor._validate_signal(invalid_signal)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_entry_signal_long_position(self):
        """Test long entry signal handling."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        signal = {
            "symbol": "BTC",
            "side": "buy",
            "quantity": 0.1,
            "price": 50000.0
        }

        # Execute
        await self.executor._handle_entry_signal(self.mock_strategy, signal)

        # Verify
        assert self.executor.execution_stats['orders_placed'] == 1

    @pytest.mark.asyncio
    async def test_handle_entry_signal_short_position(self):
        """Test short entry signal handling."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        signal = {
            "symbol": "BTC",
            "side": "sell",
            "quantity": 0.05,
            "price": 50000.0
        }

        # Execute
        await self.executor._handle_entry_signal(self.mock_strategy, signal)

        # Verify
        assert self.executor.execution_stats['orders_placed'] == 1

    @pytest.mark.asyncio
    async def test_handle_exit_signal_close_position(self):
        """Test position exit signal handling."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        signal = {
            "symbol": "BTC",
            "quantity": 0.1
        }

        # Execute
        await self.executor._handle_exit_signal(self.mock_strategy, signal)

        # Verify
        assert self.executor.execution_stats['orders_placed'] == 1

    @pytest.mark.asyncio
    async def test_handle_exit_signal_partial_close(self):
        """Test partial position exit."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        signal = {
            "symbol": "BTC",
            "quantity": 0.05  # Partial close
        }

        # Execute
        await self.executor._handle_exit_signal(self.mock_strategy, signal)

        # Verify
        assert self.executor.execution_stats['orders_placed'] == 1

    @pytest.mark.asyncio
    async def test_handle_modify_signal_stop_loss_update(self):
        """Test stop loss modification."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        signal = {
            "symbol": "BTC",
            "modifications": {
                "stop_loss": 49500.0
            }
        }

        # Execute
        await self.executor._handle_modify_signal(self.mock_strategy, signal)

        # Verify
        # Should not increment orders_placed for modify signals

    @pytest.mark.asyncio
    async def test_handle_modify_signal_take_profit_update(self):
        """Test take profit modification."""
        # Setup
        self.mock_strategy.name = "test_strategy"

        signal = {
            "symbol": "BTC",
            "modifications": {
                "take_profit": 50500.0
            }
        }

        # Execute
        await self.executor._handle_modify_signal(self.mock_strategy, signal)

        # Verify
        # Should not increment orders_placed for modify signals

    def test_get_strategy_market_data_success(self):
        """Test market data retrieval for strategy."""
        # Setup
        self.mock_strategy.symbols = ["BTC", "ETH"]

        mock_ticker_btc = {"price": 50000.0, "volume": 1000}
        mock_ticker_eth = {"price": 3000.0, "volume": 500}

        self.mock_market_data_client.get_ticker.side_effect = lambda symbol: {
            "BTC": mock_ticker_btc,
            "ETH": mock_ticker_eth
        }.get(symbol)

        self.mock_market_data_client.get_orderbook.return_value = {"bids": [], "asks": []}
        self.mock_market_data_client.get_recent_trades.return_value = []

        # Execute
        result = self.executor._get_strategy_market_data(self.mock_strategy)

        # Verify
        assert "BTC" in result
        assert "ETH" in result
        assert result["BTC"]["ticker"] == mock_ticker_btc
        assert result["ETH"]["ticker"] == mock_ticker_eth

    def test_get_strategy_market_data_missing_symbol(self):
        """Test market data retrieval with missing symbol."""
        # Setup
        self.mock_strategy.symbols = ["INVALID"]

        self.mock_market_data_client.get_ticker.return_value = None

        # Execute
        result = self.executor._get_strategy_market_data(self.mock_strategy)

        # Verify
        assert result == {}

    def test_load_strategies_from_config(self):
        """Test strategy loading from configuration."""
        # Setup
        mock_strategy_instance = self.create_async_mock("strategy_instance")
        mock_strategy_instance.name = "test_strategy"

        self.mock_strategy_registry.get_strategy.return_value = mock_strategy_instance

        with patch.object(self.executor, '_get_enabled_strategies', return_value=["test_strategy"]):
            # Execute
            self.executor._load_strategies()

        # Verify
        self.mock_strategy_registry.get_strategy.assert_called_with("test_strategy")
        assert "test_strategy" in self.executor.active_strategies

    def test_get_enabled_strategies_filtered(self):
        """Test enabled strategies filtering."""
        # Setup - Mock settings
        mock_settings = Mock()
        mock_settings.strategies.market_making.enabled = True
        self.executor.settings = mock_settings

        # Execute
        result = self.executor._get_enabled_strategies()

        # Verify
        assert "market_making" in result

    def test_setup_data_callbacks_registration(self):
        """Test data callback registration."""
        # Setup
        self.mock_market_data_client.add_ticker_callback = Mock()
        self.mock_market_data_client.add_orderbook_callback = Mock()
        self.mock_market_data_client.add_trade_callback = Mock()

        # Execute
        self.executor._setup_data_callbacks()

        # Verify
        self.mock_market_data_client.add_ticker_callback.assert_called_once()
        self.mock_market_data_client.add_orderbook_callback.assert_called_once()
        self.mock_market_data_client.add_trade_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_execution_loop_error_handling(self):
        """Test execution loop error handling."""
        # Setup
        self.executor.active_strategies = {"test_strategy": self.mock_strategy}
        self.mock_strategy.generate_signals = AsyncMock(side_effect=Exception("Test error"))

        with patch.object(self.executor, '_execute_strategy_cycle', side_effect=Exception("Cycle error")):
            # Execute
            await self.executor._execution_loop()

        # Verify
        assert self.executor.execution_stats['errors'] >= 1

    @pytest.mark.asyncio
    async def test_shutdown_graceful(self):
        """Test graceful shutdown handling."""
        # Setup
        self.executor.is_running = True
        self.executor._shutdown_event.clear()
        self.executor._execution_task = AsyncMock()
        self.executor.active_strategies = {"test_strategy": self.mock_strategy}

        self.mock_strategy.cleanup = AsyncMock()

        # Execute
        await self.executor.shutdown()

        # Verify
        assert not self.executor.is_running
        assert self.executor.active_strategies == {}
        self.mock_strategy.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization."""
        # Setup
        self.mock_market_data_client.initialize_subscriptions = AsyncMock()
        self.mock_strategy_registry.get_strategy = Mock(return_value=self.mock_strategy)
        self.mock_strategy.initialize = AsyncMock()

        with patch.object(self.executor, '_get_enabled_strategies', return_value=["test_strategy"]):
            # Execute
            await self.executor.initialize()

        # Verify
        self.mock_market_data_client.initialize_subscriptions.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test successful start."""
        # Setup
        self.executor.is_running = False
        self.mock_market_data_client.start = AsyncMock()

        with patch('asyncio.create_task') as mock_create_task:
            # Execute
            await self.executor.start()

        # Verify
        assert self.executor.is_running
        self.mock_market_data_client.start.assert_called_once()
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_success(self):
        """Test successful stop."""
        # Setup
        self.executor.is_running = True
        self.executor._shutdown_event.clear()
        self.executor._execution_task = AsyncMock()
        self.mock_market_data_client.stop = AsyncMock()

        # Execute
        await self.executor.stop()

        # Verify
        assert not self.executor.is_running
        self.mock_market_data_client.stop.assert_called_once()

    def test_get_execution_summary(self):
        """Test execution summary generation."""
        # Setup
        self.executor.is_running = True
        self.executor.active_strategies = {"strategy1": self.mock_strategy}
        self.executor.execution_stats = {
            'cycles_completed': 10,
            'signals_generated': 5,
            'orders_placed': 3,
            'errors': 1,
            'last_execution_time': asyncio.get_event_loop().time()
        }
        self.mock_market_data_client.is_connected = True
        self.mock_market_data_client.get_stats = Mock(return_value={"test": "stats"})

        # Execute
        summary = self.executor.get_execution_summary()

        # Verify
        assert summary['is_running'] is True
        assert 'strategy1' in summary['active_strategies']
        assert summary['execution_stats']['cycles_completed'] == 10
        assert summary['market_data_connected'] is True
        assert 'uptime_seconds' in summary


class TestStrategyExecutorErrorHandling(UnitTestCase):
    """Test error handling scenarios for StrategyExecutor."""

    def setup_method(self):
        """Setup for error handling tests."""
        super().setup_method()
        self.mock_market_data_client = self.create_async_mock("market_data_client", spec=MarketDataClient)
        self.mock_strategy_registry = self.create_mock("strategy_registry", spec=StrategyRegistry)

        self.executor = StrategyExecutor(
            market_data_client=self.mock_market_data_client,
            strategy_registry=self.mock_strategy_registry
        )

    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test initialization failure handling."""
        self.mock_market_data_client.initialize_subscriptions = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with pytest.raises(Exception):
            await self.executor.initialize()

    @pytest.mark.asyncio
    async def test_strategy_loading_error(self):
        """Test strategy loading error handling."""
        self.mock_strategy_registry.get_strategy = Mock(
            side_effect=Exception("Strategy not found")
        )

        with patch.object(self.executor, '_get_enabled_strategies', return_value=["invalid_strategy"]):
            # Should not raise exception, but log error
            await self.executor.initialize()

    @pytest.mark.asyncio
    async def test_signal_processing_error(self):
        """Test signal processing error handling."""
        self.mock_strategy.name = "test_strategy"

        invalid_signal = {
            "symbol": "BTC",
            "side": "buy"
            # Missing required fields for processing
        }

        # Should not raise exception
        await self.executor._process_signal(self.mock_strategy, invalid_signal)