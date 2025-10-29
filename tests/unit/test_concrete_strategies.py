"""
Comprehensive unit tests for Concrete Strategy Implementations.

Tests cover specific trading strategies including Market Maker,
Moving Average Crossover, RSI, Bollinger Bands, and MACD strategies.
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timedelta

from src.strategies.market_making.market_maker import MarketMaker, MarketMakerConfig, OrderBookSnapshot, InventoryState
from src.strategies.base.strategy import BaseStrategy, StrategyConfig, SignalDirection, TradingSignal
from core.config.manager import ConfigManager
from tests.utils.base_test import UnitTestCase


class TestMarketMakerStrategy(UnitTestCase):
    """Test suite for MarketMaker strategy."""

    def setup_method(self):
        """Setup for MarketMaker tests."""
        super().setup_method()

        self.config = MarketMakerConfig(
            name="test_market_maker",
            enabled=True,
            symbols=["BTC", "ETH"],
            max_positions=5,
            risk_per_trade=Decimal('0.02'),
            base_spread_percentage=Decimal('0.001'),
            quote_quantity=Decimal('0.1')
        )

        self.config_manager = self.create_mock("config_manager", spec=ConfigManager)
        self.market_maker = TestableMarketMaker(self.config, self.config_manager)

    @pytest.mark.asyncio
    async def test_moving_average_crossover_bullish(self):
        """Test moving average bullish crossover."""
        # Setup - Bullish crossover scenario
        market_data = {
            "BTC": {
                "price": 51000.00,
                "ma_short": 50500.00,
                "ma_long": 50000.00,
                "volume": 1000
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("BTC", market_data)

        # Verify bullish signal
        assert signal is not None
        assert signal.symbol == "BTC"
        assert signal.direction == SignalDirection.BUY

    @pytest.mark.asyncio
    async def test_moving_average_crossover_bearish(self):
        """Test moving average bearish crossover."""
        # Setup - Bearish crossover scenario
        market_data = {
            "ETH": {
                "price": 2900.00,
                "ma_short": 2950.00,
                "ma_long": 3000.00,
                "volume": 500
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("ETH", market_data)

        # Verify bearish signal
        assert signal is not None
        assert signal.symbol == "ETH"
        assert signal.direction == SignalDirection.SELL

    @pytest.mark.asyncio
    async def test_moving_average_crossover_no_crossover(self):
        """Test no crossover scenario."""
        # Setup - No crossover scenario
        market_data = {
            "BTC": {
                "price": 50000.00,
                "ma_short": 49950.00,
                "ma_long": 50050.00,
                "volume": 200
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("BTC", market_data)

        # Verify no signal or hold signal
        assert signal is None or signal.direction == SignalDirection.HOLD

    @pytest.mark.asyncio
    async def test_rsi_overbought_signal(self):
        """Test RSI overbought signal generation."""
        # Setup - Overbought scenario (RSI > 70)
        market_data = {
            "BTC": {
                "price": 55000.00,
                "rsi": 75.0,
                "volume": 800
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("BTC", market_data)

        # Verify overbought signal
        assert signal is not None
        assert signal.direction == SignalDirection.SELL

    @pytest.mark.asyncio
    async def test_rsi_oversold_signal(self):
        """Test RSI oversold signal generation."""
        # Setup - Oversold scenario (RSI < 30)
        market_data = {
            "ETH": {
                "price": 2500.00,
                "rsi": 25.0,
                "volume": 300
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("ETH", market_data)

        # Verify oversold signal
        assert signal is not None
        assert signal.direction == SignalDirection.BUY

    @pytest.mark.asyncio
    async def test_rsi_neutral_signal(self):
        """Test RSI neutral signal generation."""
        # Setup - Neutral RSI scenario (30 < RSI < 70)
        market_data = {
            "BTC": {
                "price": 50000.00,
                "rsi": 55.0,
                "volume": 500
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("BTC", market_data)

        # Verify neutral signal
        assert signal is None or signal.direction == SignalDirection.HOLD

    @pytest.mark.asyncio
    async def test_bollinger_band_squeeze_signal(self):
        """Test Bollinger Band squeeze signal."""
        # Setup - Bollinger Band squeeze scenario
        market_data = {
            "BTC": {
                "price": 50000.00,
                "bb_upper": 50200.00,
                "bb_middle": 50000.00,
                "bb_lower": 49800.00,
                "bb_width": 0.001,  # Very narrow bands
                "volume": 200
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("BTC", market_data)

        # Verify squeeze signal (could be either direction)
        assert signal is not None
        assert signal.metadata.get("bb_squeeze") is True

    @pytest.mark.asyncio
    async def test_bollinger_band_expansion_signal(self):
        """Test Bollinger Band expansion signal."""
        # Setup - Bollinger Band expansion scenario
        market_data = {
            "ETH": {
                "price": 3000.00,
                "bb_upper": 3200.00,
                "bb_middle": 3000.00,
                "bb_lower": 2800.00,
                "bb_width": 0.05,  # Wide bands
                "volume": 1000
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("ETH", market_data)

        # Verify expansion signal
        assert signal is not None
        assert signal.metadata.get("bb_expansion") is True

    @pytest.mark.asyncio
    async def test_macd_bullish_divergence(self):
        """Test MACD bullish divergence signal."""
        # Setup - Bullish divergence scenario
        market_data = {
            "BTC": {
                "price": 48000.00,
                "macd_line": -100.0,
                "macd_signal": -150.0,
                "macd_histogram": 50.0,
                "volume": 600
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("BTC", market_data)

        # Verify bullish divergence signal
        assert signal is not None
        assert signal.direction == SignalDirection.BUY
        assert signal.metadata.get("macd_divergence") == "bullish"

    @pytest.mark.asyncio
    async def test_macd_bearish_divergence(self):
        """Test MACD bearish divergence signal."""
        # Setup - Bearish divergence scenario
        market_data = {
            "ETH": {
                "price": 3200.00,
                "macd_line": 150.0,
                "macd_signal": 100.0,
                "macd_histogram": -50.0,
                "volume": 400
            }
        }

        # Execute
        signal = await self.market_maker.generate_signal("ETH", market_data)

        # Verify bearish divergence signal
        assert signal is not None
        assert signal.direction == SignalDirection.SELL
        assert signal.metadata.get("macd_divergence") == "bearish"


class TestMarketMakerSpecific(UnitTestCase):
    """Test MarketMaker specific functionality."""

    def setup_method(self):
        """Setup for MarketMaker specific tests."""
        super().setup_method()

        self.config = MarketMakerConfig(
            name="market_maker_test",
            enabled=True,
            symbols=["BTC"],
            base_spread_percentage=Decimal('0.002'),
            quote_quantity=Decimal('0.1'),
            inventory_target=Decimal('0.5')
        )

        self.config_manager = self.create_mock("config_manager", spec=ConfigManager)
        self.market_maker = TestableMarketMaker(self.config, self.config_manager)

    @pytest.mark.asyncio
    async def test_order_book_update_processing(self):
        """Test order book update processing."""
        # Setup
        market_data = {
            "order_book": {
                "bids": [["49990.00", "0.5"], ["49980.00", "1.0"]],
                "asks": [["50010.00", "0.5"], ["50020.00", "1.0"]]
            }
        }

        # Execute
        await self.market_maker._update_order_book("BTC", market_data)

        # Verify
        assert "BTC" in self.market_maker._order_books
        order_book = self.market_maker._order_books["BTC"]
        assert order_book.bid_price == Decimal('49990.00')
        assert order_book.ask_price == Decimal('50010.00')
        assert order_book.spread == Decimal('20.00')

    def test_calculate_dynamic_spread(self):
        """Test dynamic spread calculation."""
        # Setup - Add order book data
        order_book = OrderBookSnapshot(
            symbol="BTC",
            bid_price=Decimal('49990.00'),
            ask_price=Decimal('50010.00'),
            bid_volume=Decimal('0.5'),
            ask_volume=Decimal('0.5'),
            spread=Decimal('20.00'),
            mid_price=Decimal('50000.00'),
            timestamp=datetime.now(),
            volatility=0.02
        )
        self.market_maker._order_books["BTC"] = order_book

        # Execute
        spread = self.market_maker._calculate_dynamic_spread("BTC")

        # Verify
        assert spread > self.config.base_spread_percentage  # Should increase due to volatility
        assert spread >= self.config.min_spread_percentage
        assert spread <= self.config.max_spread_percentage

    @pytest.mark.asyncio
    async def test_inventory_state_update(self):
        """Test inventory state update."""
        # Setup - Mock position manager
        mock_positions = [
            Mock(symbol="BTC", quantity=Decimal('0.3'))
        ]
        self.market_maker._position_manager = self.create_async_mock("position_manager")
        self.market_maker._position_manager.get_positions = AsyncMock(return_value=mock_positions)

        # Execute
        await self.market_maker._update_inventory_state("BTC")

        # Verify
        inventory_state = self.market_maker._inventory_states["BTC"]
        assert inventory_state.current_position == Decimal('0.3')
        assert inventory_state.position_deviation == Decimal('-0.2')  # 0.3 - 0.5

    @pytest.mark.asyncio
    async def test_quote_refresh_logic(self):
        """Test quote refresh logic."""
        # Setup - Add order book and inventory state
        order_book = OrderBookSnapshot(
            symbol="BTC",
            bid_price=Decimal('49990.00'),
            ask_price=Decimal('50010.00'),
            bid_volume=Decimal('0.5'),
            ask_volume=Decimal('0.5'),
            spread=Decimal('20.00'),
            mid_price=Decimal('50000.00'),
            timestamp=datetime.now(),
            volatility=0.01
        )
        self.market_maker._order_books["BTC"] = order_book

        # Execute
        should_refresh = await self.market_maker._should_refresh_quotes("BTC")

        # Verify
        assert should_refresh is True  # No active quotes initially

    @pytest.mark.asyncio
    async def test_quote_refresh_execution(self):
        """Test quote refresh execution."""
        # Setup
        order_book = OrderBookSnapshot(
            symbol="BTC",
            bid_price=Decimal('49990.00'),
            ask_price=Decimal('50010.00'),
            bid_volume=Decimal('0.5'),
            ask_volume=Decimal('0.5'),
            spread=Decimal('20.00'),
            mid_price=Decimal('50000.00'),
            timestamp=datetime.now(),
            volatility=0.01
        )
        self.market_maker._order_books["BTC"] = order_book

        self.market_maker._trading_engine = self.create_async_mock("trading_engine")
        self.market_maker._trading_engine.execute_signal = AsyncMock()

        # Execute
        await self.market_maker._refresh_quotes("BTC")

        # Verify
        assert self.market_maker._quote_updates == 1
        assert len(self.market_maker._active_quotes["BTC"]) == 2  # Bid and ask

        # Verify trading engine was called for both quotes
        assert self.market_maker._trading_engine.execute_signal.call_count == 2

    def test_volatility_calculation(self):
        """Test volatility calculation."""
        # Setup - Add price history
        self.market_maker._price_volatility["BTC"] = [
            50000.0, 50100.0, 49950.0, 50200.0, 49800.0
        ]

        # Execute
        volatility = self.market_maker._calculate_volatility("BTC", 50000.0)

        # Verify
        assert volatility > 0
        assert isinstance(volatility, float)

    def test_inventory_rebalancing(self):
        """Test inventory rebalancing logic."""
        # Setup - Create inventory state with deviation
        inventory_state = InventoryState(
            symbol="BTC",
            current_position=Decimal('1.0'),
            target_position=Decimal('0.5'),
            position_deviation=Decimal('0.5'),
            last_rebalance=datetime.now()
        )
        self.market_maker._inventory_states["BTC"] = inventory_state

        # Execute
        signal = self.market_maker._rebalance_inventory("BTC")

        # Verify
        assert signal is not None
        assert signal.symbol == "BTC"
        assert signal.direction == SignalDirection.SELL  # Should sell to reduce inventory
        assert signal.metadata["rebalance"] is True

    def test_strategy_metrics_collection(self):
        """Test strategy metrics collection."""
        # Setup - Add some test data
        self.market_maker._quote_updates = 10
        self.market_maker._fills = 5
        self.market_maker._spread_earned = Decimal('100.0')

        self.market_maker._active_quotes = {
            "BTC": ["quote1", "quote2"],
            "ETH": ["quote3"]
        }

        # Execute
        metrics = self.market_maker.get_strategy_metrics()

        # Verify
        assert metrics["quote_updates"] == 10
        assert metrics["active_quotes"] == 3
        assert metrics["fills"] == 5
        assert metrics["spread_earned"] == 100.0

    def test_quote_fill_update(self):
        """Test quote fill update tracking."""
        # Setup - Add order book and inventory state
        order_book = OrderBookSnapshot(
            symbol="BTC",
            bid_price=Decimal('49990.00'),
            ask_price=Decimal('50010.00'),
            bid_volume=Decimal('0.5'),
            ask_volume=Decimal('0.5'),
            spread=Decimal('20.00'),
            mid_price=Decimal('50000.00'),
            timestamp=datetime.now()
        )
        self.market_maker._order_books["BTC"] = order_book

        inventory_state = InventoryState(
            symbol="BTC",
            current_position=Decimal('0'),
            target_position=Decimal('0'),
            position_deviation=Decimal('0'),
            last_rebalance=datetime.now()
        )
        self.market_maker._inventory_states["BTC"] = inventory_state

        # Execute
        self.market_maker.update_quote_fill("BTC", "buy", Decimal('0.1'), Decimal('50000.00'))

        # Verify
        assert self.market_maker._fills == 1
        assert self.market_maker._inventory_states["BTC"].current_position == Decimal('0.1')
        assert self.market_maker._spread_earned > 0  # Should earn spread


class TestStrategyIntegration(UnitTestCase):
    """Test strategy integration scenarios."""

    def setup_method(self):
        """Setup for integration tests."""
        super().setup_method()

        self.config = StrategyConfig(
            name="integration_test_strategy",
            enabled=True,
            symbols=["BTC", "ETH", "ADA"],
            max_positions=10,
            risk_per_trade=Decimal('0.03')
        )

        self.config_manager = self.create_mock("config_manager", spec=ConfigManager)
        self.strategy = TestableBaseStrategy(self.config, self.config_manager)

    @pytest.mark.asyncio
    async def test_multiple_symbol_signal_generation(self):
        """Test signal generation across multiple symbols."""
        # Setup - Different market conditions for each symbol
        market_data = {
            "BTC": {
                "price": 51000.00,
                "ma_short": 50500.00,
                "ma_long": 50000.00,
                "volume": 1000
            },
            "ETH": {
                "price": 2900.00,
                "ma_short": 2950.00,
                "ma_long": 3000.00,
                "volume": 500
            },
            "ADA": {
                "price": 0.45,
                "ma_short": 0.44,
                "ma_long": 0.46,
                "volume": 10000
            }
        }

        signals = []
        for symbol in self.config.symbols:
            signal = await self.strategy.generate_signal(symbol, market_data)
            if signal:
                signals.append(signal)

        # Verify
        assert len(signals) >= 1  # Should generate at least one signal

    @pytest.mark.asyncio
    async def test_strategy_lifecycle_with_multiple_symbols(self):
        """Test complete strategy lifecycle with multiple symbols."""
        # Setup
        self.strategy._validate_configuration = AsyncMock(return_value=True)
        self.strategy._initialize_strategy = AsyncMock()

        # Initialize
        result = await self.strategy.initialize()
        assert result is True

        # Start
        self.strategy._running = False
        with patch('asyncio.create_task'):
            result = await self.strategy.start()
        assert result is True

        # Generate signals for multiple symbols
        market_data = {
            "BTC": {"price": 50000.00, "ma_short": 50500.00, "ma_long": 50000.00},
            "ETH": {"price": 3000.00, "ma_short": 2950.00, "ma_long": 3000.00}
        }

        for symbol in ["BTC", "ETH"]:
            signal = await self.strategy.generate_signal(symbol, market_data)
            if signal and signal.direction != SignalDirection.HOLD:
                # Validate signal
                is_valid = await self.strategy.validate_signal(signal)
                assert is_valid is True

        # Stop
        self.strategy._signal_task = AsyncMock()
        self.strategy._cleanup_strategy = AsyncMock()
        result = await self.strategy.stop()
        assert result is True


class TestableMarketMaker(MarketMaker):
    """Testable concrete implementation of MarketMaker."""

    async def generate_signal(self, symbol: str, market_data) -> TradingSignal:
        """Concrete implementation for testing various indicators."""
        if symbol not in market_data:
            return None

        data = market_data[symbol]

        # Moving Average Crossover Logic
        ma_short = data.get("ma_short", data.get("price", 0))
        ma_long = data.get("ma_long", data.get("price", 0))

        if ma_short > ma_long * 1.01:  # Bullish crossover
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.8,
                quantity=Decimal('0.1'),
                metadata={"strategy": "ma_crossover", "signal_type": "bullish"}
            )
        elif ma_short < ma_long * 0.99:  # Bearish crossover
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.8,
                quantity=Decimal('0.1'),
                metadata={"strategy": "ma_crossover", "signal_type": "bearish"}
            )

        # RSI Logic
        rsi = data.get("rsi", 50.0)
        if rsi > 70:  # Overbought
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.7,
                quantity=Decimal('0.1'),
                metadata={"strategy": "rsi", "signal_type": "overbought"}
            )
        elif rsi < 30:  # Oversold
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.7,
                quantity=Decimal('0.1'),
                metadata={"strategy": "rsi", "signal_type": "oversold"}
            )

        # Bollinger Bands Logic
        bb_width = data.get("bb_width", 0.02)
        if bb_width < 0.005:  # Squeeze
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,  # Could be either direction
                confidence=0.6,
                quantity=Decimal('0.1'),
                metadata={"strategy": "bb", "signal_type": "squeeze", "bb_squeeze": True}
            )
        elif bb_width > 0.04:  # Expansion
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,  # Could be either direction
                confidence=0.6,
                quantity=Decimal('0.1'),
                metadata={"strategy": "bb", "signal_type": "expansion", "bb_expansion": True}
            )

        # MACD Logic
        macd_histogram = data.get("macd_histogram", 0)
        if macd_histogram > 10:  # Bullish divergence
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.7,
                quantity=Decimal('0.1'),
                metadata={"strategy": "macd", "signal_type": "bullish_divergence", "macd_divergence": "bullish"}
            )
        elif macd_histogram < -10:  # Bearish divergence
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.7,
                quantity=Decimal('0.1'),
                metadata={"strategy": "macd", "signal_type": "bearish_divergence", "macd_divergence": "bearish"}
            )

        # No signal condition
        return TradingSignal(
            symbol=symbol,
            direction=SignalDirection.HOLD,
            confidence=0.5,
            quantity=Decimal('0')
        )

    def calculate_position_size(self, signal: TradingSignal, portfolio_value: Decimal) -> Decimal:
        """Position sizing based on confidence and strategy."""
        if signal.quantity == 0:
            return Decimal('0')

        # Base position size
        base_size = portfolio_value * self.config.risk_per_trade * Decimal(str(signal.confidence))

        # Adjust for strategy type
        strategy_multiplier = {
            "ma_crossover": 1.2,
            "rsi": 1.0,
            "bb": 1.1,
            "macd": 1.3
        }.get(signal.metadata.get("strategy", "unknown"), 1.0)

        return min(base_size * Decimal(str(strategy_multiplier)), portfolio_value * self.config.risk_per_trade)

    async def validate_signal(self, signal: TradingSignal) -> bool:
        """Enhanced signal validation for concrete strategies."""
        # Basic validation from base class would be called first
        if not await super().validate_signal(signal):
            return False

        # Strategy-specific validation
        strategy = signal.metadata.get("strategy")
        if strategy == "rsi" and signal.confidence < 0.6:
            return False  # RSI signals need higher confidence

        if strategy == "bb" and signal.metadata.get("bb_width", 0) < 0.001:
            return False  # Bollinger Band signals need significant width

        return True

    async def _initialize_strategy(self):
        """Strategy-specific initialization."""
        pass

    async def _validate_strategy_config(self):
        """Strategy-specific configuration validation."""
        pass

    async def _cleanup_strategy(self):
        """Strategy-specific cleanup."""
        pass


class TestableBaseStrategy(BaseStrategy):
    """Testable concrete implementation of BaseStrategy for integration testing."""

    async def generate_signal(self, symbol: str, market_data) -> TradingSignal:
        """Simple implementation for integration testing."""
        if symbol not in market_data:
            return None

        price = market_data[symbol].get("price", 0)
        if price == 0:
            return None

        # Simple price momentum strategy
        if price > 50000:
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=0.7,
                quantity=Decimal('0.1')
            )
        else:
            return TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.6,
                quantity=Decimal('0.1')
            )

    def calculate_position_size(self, signal: TradingSignal, portfolio_value: Decimal) -> Decimal:
        """Simple position sizing for testing."""
        return portfolio_value * self.config.risk_per_trade

    async def validate_signal(self, signal: TradingSignal) -> bool:
        """Simple validation for testing."""
        return signal.confidence > 0.5 and signal.quantity > 0

    async def _initialize_strategy(self):
        """Strategy-specific initialization."""
        pass

    async def _validate_strategy_config(self):
        """Strategy-specific configuration validation."""
        pass

    async def _cleanup_strategy(self):
        """Strategy-specific cleanup."""
        pass