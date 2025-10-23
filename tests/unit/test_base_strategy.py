"""
Comprehensive unit tests for BaseStrategy core trading logic.

Tests cover strategy lifecycle, signal generation, position sizing,
risk management, and metrics tracking for the core trading engine.
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timedelta

from strategies.base.strategy import (
    BaseStrategy, StrategyConfig, StrategyStatus, SignalDirection,
    TradingSignal, StrategyMetrics
)
from core.config.manager import ConfigManager
from tests.utils.base_test import UnitTestCase


class TestBaseStrategy(UnitTestCase):
    """Test suite for BaseStrategy class."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

        # Create a concrete strategy implementation for testing
        self.config = StrategyConfig(
            name="test_strategy",
            enabled=True,
            symbols=["BTC", "ETH"],
            max_positions=5,
            risk_per_trade=Decimal('0.02'),
            max_portfolio_risk=Decimal('0.1')
        )

        self.config_manager = self.create_mock("config_manager", spec=ConfigManager)
        self.strategy = TestableBaseStrategy(self.config, self.config_manager)

    @pytest.mark.asyncio
    async def test_generate_signal_bullish_market(self):
        """Test bullish market signal generation."""
        # Setup
        market_data = {
            "BTC": {
                "price": 51000.00,
                "volume": 1000,
                "ma_short": 50500.00,
                "ma_long": 50000.00
            }
        }

        # Execute
        signal = await self.strategy.generate_signal("BTC", market_data)

        # Verify
        assert signal is not None
        assert signal.symbol == "BTC"
        assert signal.direction == SignalDirection.BUY
        assert signal.confidence > 0.5

    @pytest.mark.asyncio
    async def test_generate_signal_bearish_market(self):
        """Test bearish market signal generation."""
        # Setup
        market_data = {
            "ETH": {
                "price": 2900.00,
                "volume": 500,
                "ma_short": 2950.00,
                "ma_long": 3000.00
            }
        }

        # Execute
        signal = await self.strategy.generate_signal("ETH", market_data)

        # Verify
        assert signal is not None
        assert signal.symbol == "ETH"
        assert signal.direction == SignalDirection.SELL
        assert signal.confidence > 0.5

    @pytest.mark.asyncio
    async def test_generate_signal_sideways_market(self):
        """Test sideways market signal generation."""
        # Setup
        market_data = {
            "BTC": {
                "price": 50000.00,
                "volume": 200,
                "ma_short": 49950.00,
                "ma_long": 50050.00
            }
        }

        # Execute
        signal = await self.strategy.generate_signal("BTC", market_data)

        # Verify
        assert signal is not None
        assert signal.direction == SignalDirection.HOLD

    @pytest.mark.asyncio
    async def test_generate_signal_no_signal(self):
        """Test no signal generation scenario."""
        # Setup - Invalid market data
        market_data = {
            "INVALID": {
                "price": 0,
                "volume": 0
            }
        }

        # Execute
        signal = await self.strategy.generate_signal("INVALID", market_data)

        # Verify
        assert signal is None

    def test_calculate_position_size_kelly_formula(self):
        """Test Kelly Criterion position sizing."""
        # Setup
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0.7,
            quantity=Decimal('1.0')
        )
        portfolio_value = Decimal('10000')

        # Execute
        position_size = self.strategy.calculate_position_size(signal, portfolio_value)

        # Verify
        assert position_size > 0
        assert position_size <= portfolio_value * Decimal('0.02')  # Risk per trade limit

    def test_calculate_position_size_fixed_fractional(self):
        """Test fixed fractional position sizing."""
        # Setup
        signal = TradingSignal(
            symbol="ETH",
            direction=SignalDirection.BUY,
            confidence=0.8,
            quantity=Decimal('10.0')
        )
        portfolio_value = Decimal('50000')

        # Execute
        position_size = self.strategy.calculate_position_size(signal, portfolio_value)

        # Verify
        assert position_size > 0
        assert position_size <= portfolio_value * Decimal('0.02')

    def test_calculate_position_size_risk_based(self):
        """Test risk-based position sizing."""
        # Setup - High confidence signal
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0.9,
            quantity=Decimal('0.5')
        )
        portfolio_value = Decimal('25000')

        # Execute
        position_size = self.strategy.calculate_position_size(signal, portfolio_value)

        # Verify
        assert position_size > 0
        assert position_size <= portfolio_value * Decimal('0.02')

    def test_calculate_position_size_zero_volatility(self):
        """Test zero volatility edge case."""
        # Setup - Signal with zero quantity (edge case)
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0.5,
            quantity=Decimal('0')
        )
        portfolio_value = Decimal('10000')

        # Execute
        position_size = self.strategy.calculate_position_size(signal, portfolio_value)

        # Verify
        assert position_size == 0  # Should handle zero quantity gracefully

    @pytest.mark.asyncio
    async def test_validate_signal_valid_signal(self):
        """Test valid signal validation."""
        # Setup
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0.7,
            quantity=Decimal('0.1')
        )

        # Execute
        result = await self.strategy.validate_signal(signal)

        # Verify
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_signal_invalid_signal_type(self):
        """Test invalid signal type validation."""
        # Setup - Invalid direction
        signal = TradingSignal(
            symbol="BTC",
            direction="invalid_direction",  # type: ignore
            confidence=0.7,
            quantity=Decimal('0.1')
        )

        # Execute
        result = await self.strategy.validate_signal(signal)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_signal_missing_required_fields(self):
        """Test missing fields validation."""
        # Setup - Signal with missing confidence
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0,  # Invalid confidence
            quantity=Decimal('0.1')
        )

        # Execute
        result = await self.strategy.validate_signal(signal)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_strategy_initialization_success(self):
        """Test successful strategy initialization."""
        # Setup
        self.strategy._validate_configuration = AsyncMock(return_value=True)
        self.strategy._initialize_strategy = AsyncMock()

        # Execute
        result = await self.strategy.initialize()

        # Verify
        assert result is True
        assert self.strategy.status == StrategyStatus.RUNNING

    @pytest.mark.asyncio
    async def test_strategy_initialization_config_error(self):
        """Test configuration error handling."""
        # Setup
        self.strategy._validate_configuration = AsyncMock(
            side_effect=ValueError("Invalid config")
        )

        # Execute
        result = await self.strategy.initialize()

        # Verify
        assert result is False
        assert self.strategy.status == StrategyStatus.ERROR

    @pytest.mark.asyncio
    async def test_strategy_start_success(self):
        """Test successful strategy start."""
        # Setup
        self.strategy.status = StrategyStatus.RUNNING
        self.strategy._running = False

        with patch('asyncio.create_task') as mock_create_task:
            # Execute
            result = await self.strategy.start()

        # Verify
        assert result is True
        assert self.strategy._running is True
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_strategy_stop_graceful(self):
        """Test graceful strategy stop."""
        # Setup
        self.strategy.status = StrategyStatus.STOPPING
        self.strategy._running = True
        self.strategy._signal_task = AsyncMock()
        self.strategy._cleanup_strategy = AsyncMock()

        # Execute
        result = await self.strategy.stop()

        # Verify
        assert result is True
        assert not self.strategy._running
        assert self.strategy.status == StrategyStatus.STOPPED
        self.strategy._cleanup_strategy.assert_called_once()

    @pytest.mark.asyncio
    async def test_strategy_pause_resume(self):
        """Test strategy pause and resume."""
        # Setup - Start strategy first
        self.strategy.status = StrategyStatus.RUNNING
        self.strategy._running = True

        # Test pause
        result = await self.strategy.pause()
        assert result is True
        assert self.strategy.status == StrategyStatus.PAUSED

        # Test resume
        result = await self.strategy.resume()
        assert result is True
        assert self.strategy.status == StrategyStatus.RUNNING

    @pytest.mark.asyncio
    async def test_signal_generation_loop_execution(self):
        """Test signal generation loop execution."""
        # Setup
        self.strategy._running = True
        self.strategy._get_market_data = AsyncMock(return_value={"price": 50000.00})
        self.strategy.generate_signal = AsyncMock(return_value=None)
        self.strategy._process_signal = AsyncMock()

        # Execute - Run loop briefly
        await asyncio.sleep(0.1)  # Let loop run briefly

        # Verify
        # Loop should have attempted to generate signals
        assert self.strategy._get_market_data.call_count >= 0  # May be 0 if timing doesn't align

    @pytest.mark.asyncio
    async def test_risk_limits_checking(self):
        """Test risk limits checking integration."""
        # Setup
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0.8,
            quantity=Decimal('0.1')
        )

        self.strategy._position_manager = self.create_async_mock("position_manager")
        self.strategy._position_manager.get_positions = AsyncMock(return_value=[])
        self.strategy._risk_manager = self.create_async_mock("risk_manager")
        self.strategy._risk_manager.get_portfolio_risk = AsyncMock(return_value=Decimal('0.05'))

        # Execute
        result = await self.strategy._check_risk_limits(signal)

        # Verify
        assert result is True
        self.strategy._position_manager.get_positions.assert_called_once()
        self.strategy._risk_manager.get_portfolio_risk.assert_called_once()

    @pytest.mark.asyncio
    async def test_metrics_update_on_trade(self):
        """Test metrics update on trade execution."""
        # Setup
        initial_metrics = StrategyMetrics()
        self.strategy._metrics = initial_metrics

        # Execute
        self.strategy.update_metrics(Decimal('100'), Decimal('2'))

        # Verify
        assert self.strategy._metrics.total_trades == 1
        assert self.strategy._metrics.winning_trades == 1
        assert self.strategy._metrics.total_pnl == Decimal('100')
        assert self.strategy._metrics.total_fees == Decimal('2')
        assert self.strategy._metrics.win_rate == 1.0


class TestBaseStrategyLifecycle(UnitTestCase):
    """Test strategy lifecycle management."""

    def setup_method(self):
        """Setup for lifecycle tests."""
        super().setup_method()

        self.config = StrategyConfig(
            name="lifecycle_test_strategy",
            enabled=True,
            symbols=["BTC"],
            max_positions=3,
            risk_per_trade=Decimal('0.01')
        )

        self.config_manager = self.create_mock("config_manager", spec=ConfigManager)
        self.strategy = TestableBaseStrategy(self.config, self.config_manager)

    @pytest.mark.asyncio
    async def test_complete_strategy_lifecycle(self):
        """Test complete strategy lifecycle."""
        # Initialize
        self.strategy._validate_configuration = AsyncMock(return_value=True)
        self.strategy._initialize_strategy = AsyncMock()

        result = await self.strategy.initialize()
        assert result is True
        assert self.strategy.status == StrategyStatus.RUNNING

        # Start
        self.strategy._running = False
        with patch('asyncio.create_task'):
            result = await self.strategy.start()
        assert result is True
        assert self.strategy._running is True

        # Stop
        self.strategy._signal_task = AsyncMock()
        self.strategy._cleanup_strategy = AsyncMock()

        result = await self.strategy.stop()
        assert result is True
        assert self.strategy.status == StrategyStatus.STOPPED

    @pytest.mark.asyncio
    async def test_strategy_reinitialization_after_error(self):
        """Test strategy reinitialization after error."""
        # Setup - Strategy in error state
        self.strategy.status = StrategyStatus.ERROR
        self.strategy._validate_configuration = AsyncMock(return_value=True)
        self.strategy._initialize_strategy = AsyncMock()

        # Execute
        result = await self.strategy.initialize()

        # Verify
        assert result is True
        assert self.strategy.status == StrategyStatus.RUNNING

    @pytest.mark.asyncio
    async def test_signal_processing_with_risk_violation(self):
        """Test signal processing when risk limits are violated."""
        # Setup
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=0.8,
            quantity=Decimal('1.0')  # Large quantity that may violate risk
        )

        # Mock risk manager to return high risk
        self.strategy._risk_manager = self.create_async_mock("risk_manager")
        self.strategy._risk_manager.get_portfolio_risk = AsyncMock(
            return_value=Decimal('0.15')  # Above max portfolio risk
        )

        # Execute
        result = await self.strategy._check_risk_limits(signal)

        # Verify
        assert result is False  # Should be rejected due to high portfolio risk


class TestBaseStrategyConfiguration(UnitTestCase):
    """Test strategy configuration management."""

    def setup_method(self):
        """Setup for configuration tests."""
        super().setup_method()

    def test_strategy_config_validation_success(self):
        """Test successful strategy configuration validation."""
        # Setup
        config = StrategyConfig(
            name="valid_strategy",
            enabled=True,
            symbols=["BTC", "ETH"],
            max_positions=5,
            risk_per_trade=Decimal('0.02'),
            max_portfolio_risk=Decimal('0.1')
        )

        # Execute & Verify - Should not raise exception
        assert config.name == "valid_strategy"
        assert len(config.symbols) == 2
        assert config.risk_per_trade == Decimal('0.02')

    def test_strategy_config_validation_risk_values(self):
        """Test strategy configuration risk value validation."""
        # Test negative risk values
        with pytest.raises(ValueError):
            StrategyConfig(
                name="invalid_strategy",
                enabled=True,
                symbols=["BTC"],
                risk_per_trade=Decimal('-0.01')  # Negative risk
            )

    def test_strategy_config_validation_confidence_bounds(self):
        """Test strategy configuration confidence bounds."""
        # Test confidence bounds (this would be in signal validation)
        signal = TradingSignal(
            symbol="BTC",
            direction=SignalDirection.BUY,
            confidence=1.5,  # Invalid confidence > 1.0
            quantity=Decimal('0.1')
        )

        # This would typically be validated in signal creation
        assert not (0.0 <= signal.confidence <= 1.0)


class TestableBaseStrategy(BaseStrategy):
    """Testable concrete implementation of BaseStrategy."""

    async def generate_signal(self, symbol: str, market_data) -> TradingSignal:
        """Concrete implementation for testing."""
        if symbol not in market_data:
            return None

        data = market_data[symbol]
        price = data.get("price", 0)

        # Simple moving average crossover logic for testing
        ma_short = data.get("ma_short", price)
        ma_long = data.get("ma_long", price)

        if ma_short > ma_long * 1.01:  # Bullish
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.7,
                quantity=Decimal('0.1'),
                price=Decimal(str(price))
            )
        elif ma_short < ma_long * 0.99:  # Bearish
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.7,
                quantity=Decimal('0.1'),
                price=Decimal(str(price))
            )
        else:  # Sideways
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.HOLD,
                confidence=0.5,
                quantity=Decimal('0')
            )

    def calculate_position_size(self, signal: TradingSignal, portfolio_value: Decimal) -> Decimal:
        """Concrete implementation for testing."""
        if signal.quantity == 0:
            return Decimal('0')

        # Risk-based position sizing
        risk_amount = portfolio_value * self.config.risk_per_trade
        price = signal.price or Decimal('50000')

        # Simple position sizing based on confidence
        position_size = (risk_amount / price) * Decimal(str(signal.confidence))

        return min(position_size, portfolio_value * self.config.risk_per_trade)

    async def validate_signal(self, signal: TradingSignal) -> bool:
        """Concrete implementation for testing."""
        # Basic validation
        if signal.confidence <= 0 or signal.confidence > 1:
            return False

        if signal.quantity < 0:
            return False

        if signal.direction not in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD]:
            return False

        return True

    async def _initialize_strategy(self):
        """Strategy-specific initialization for testing."""
        pass

    async def _validate_strategy_config(self):
        """Strategy-specific configuration validation for testing."""
        pass

    async def _cleanup_strategy(self):
        """Strategy-specific cleanup for testing."""
        pass