"""
Market Making Strategy Implementation.

This module provides a sophisticated market making strategy with dynamic spread
calculation, inventory management, and high-frequency quoting capabilities.
"""

import asyncio
import math
import statistics
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from pydantic import BaseModel, Field, validator

from ..base import BaseStrategy, StrategyConfig, TradingSignal, SignalDirection
from ....utils.logging import get_logger


@dataclass
class OrderBookSnapshot:
    """Snapshot of order book data."""
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    bid_volume: Decimal
    ask_volume: Decimal
    spread: Decimal
    mid_price: Decimal
    timestamp: datetime
    volatility: float = 0.0


@dataclass
class InventoryState:
    """Current inventory state for a symbol."""
    symbol: str
    current_position: Decimal
    target_position: Decimal
    position_deviation: Decimal
    last_rebalance: datetime
    rebalance_count: int = 0


@dataclass
class QuoteOrder:
    """Active quote order information."""
    order_id: str
    symbol: str
    side: str  # 'bid' or 'ask'
    price: Decimal
    quantity: Decimal
    timestamp: datetime
    status: str = 'active'


class MarketMakerConfig(StrategyConfig):
    """Configuration specific to market making strategy."""

    # Spread configuration
    base_spread_percentage: Decimal = Field(Decimal('0.001'), description="Base spread as percentage")
    min_spread_percentage: Decimal = Field(Decimal('0.0005'), description="Minimum spread percentage")
    max_spread_percentage: Decimal = Field(Decimal('0.01'), description="Maximum spread percentage")

    # Inventory management
    inventory_target: Decimal = Field(Decimal('0'), description="Target inventory position")
    inventory_range: Decimal = Field(Decimal('0.1'), description="Allowable inventory deviation")
    rebalance_threshold: Decimal = Field(Decimal('0.05'), description="Rebalance trigger threshold")

    # Order management
    order_refresh_time: int = Field(30, description="Order refresh interval in seconds")
    quote_quantity: Decimal = Field(Decimal('0.1'), description="Quote order quantity")
    max_order_age: int = Field(60, description="Maximum order age before refresh")

    # Risk management
    max_inventory_value: Decimal = Field(Decimal('1000'), description="Maximum inventory value")
    max_position_size: Decimal = Field(Decimal('1.0'), description="Maximum position size")
    drawdown_limit: Decimal = Field(Decimal('0.1'), description="Maximum drawdown limit")

    # Volatility adjustment
    volatility_window: int = Field(20, description="Volatility calculation window")
    volatility_adjustment_factor: Decimal = Field(Decimal('2.0'), description="Volatility adjustment multiplier")

    # Performance optimization
    max_quotes_per_symbol: int = Field(10, description="Maximum concurrent quotes per symbol")
    order_book_depth: int = Field(10, description="Order book depth to analyze")

    @validator('base_spread_percentage', 'min_spread_percentage', 'max_spread_percentage')
    def validate_spreads(cls, v):
        if v <= 0:
            raise ValueError("Spread percentages must be positive")
        return v


class MarketMaker(BaseStrategy):
    """
    High-frequency market making strategy.

    Implements sophisticated spread calculation, inventory management,
    and order lifecycle management for providing liquidity in crypto markets.
    """

    def __init__(self, config: MarketMakerConfig, config_manager):
        """Initialize the market maker strategy."""
        super().__init__(config, config_manager)

        # Market making specific state
        self._order_books: Dict[str, OrderBookSnapshot] = {}
        self._inventory_states: Dict[str, InventoryState] = {}
        self._active_quotes: Dict[str, List[QuoteOrder]] = {}
        self._quote_refresh_task = None
        self._price_volatility: Dict[str, List[float]] = {}

        # Performance tracking
        self._quote_updates = 0
        self._fills = 0
        self._spread_earned = Decimal('0')

        # Logging with strategy-specific context
        self.logger = get_logger("strategy.market_maker")

    async def generate_signal(self, symbol: str, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate market making signals based on order book analysis.

        For market making, we continuously maintain quotes rather than
        generating discrete signals.
        """
        try:
            # Update order book data
            await self._update_order_book(symbol, market_data)

            # Check if we need to refresh quotes
            if await self._should_refresh_quotes(symbol):
                await self._refresh_quotes(symbol)

            # Return None as market making doesn't generate discrete signals
            return None

        except Exception as e:
            self.logger.error("Error generating market making signal",
                            symbol=symbol, error=str(e))
            return None

    def calculate_position_size(self, signal: TradingSignal, portfolio_value: Decimal) -> Decimal:
        """
        Calculate position size for market making orders.

        Args:
            signal: Trading signal (not used in market making)
            portfolio_value: Current portfolio value

        Returns:
            Position size based on inventory management
        """
        # For market making, position size is determined by quote quantity configuration
        # and inventory management logic
        return self.config.quote_quantity

    async def validate_signal(self, signal: TradingSignal) -> bool:
        """
        Validate market making signals.

        Args:
            signal: Trading signal to validate

        Returns:
            True if signal is valid for market making
        """
        try:
            # Check inventory limits
            inventory_state = self._inventory_states.get(signal.symbol)
            if inventory_state:
                if abs(inventory_state.position_deviation) > self.config.inventory_range:
                    self.logger.debug("Inventory deviation too high",
                                    symbol=signal.symbol,
                                    deviation=float(inventory_state.position_deviation))
                    return False

            # Check position value limits
            position_value = abs(signal.quantity) * signal.price if signal.price else Decimal('0')
            if position_value > self.config.max_inventory_value:
                self.logger.debug("Position value exceeds limit",
                                symbol=signal.symbol,
                                position_value=float(position_value),
                                limit=float(self.config.max_inventory_value))
                return False

            return True

        except Exception as e:
            self.logger.error("Error validating market making signal",
                            symbol=signal.symbol, error=str(e))
            return False

    async def _initialize_strategy(self):
        """Initialize market making specific components."""
        try:
            self.logger.info("Initializing market making strategy")

            # Initialize inventory states for all symbols
            for symbol in self.config.symbols:
                self._inventory_states[symbol] = InventoryState(
                    symbol=symbol,
                    current_position=Decimal('0'),
                    target_position=self.config.inventory_target,
                    position_deviation=Decimal('0'),
                    last_rebalance=datetime.now()
                )

                self._active_quotes[symbol] = []
                self._price_volatility[symbol] = []

            # Start quote refresh task
            if not self._quote_refresh_task:
                self._quote_refresh_task = asyncio.create_task(self._quote_refresh_loop())

            self.logger.info("Market making strategy initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize market making strategy", error=str(e))
            raise

    async def _cleanup_strategy(self):
        """Cleanup market making specific components."""
        try:
            self.logger.info("Cleaning up market making strategy")

            # Cancel all active quotes
            await self._cancel_all_quotes()

            # Stop quote refresh task
            if self._quote_refresh_task and not self._quote_refresh_task.done():
                self._quote_refresh_task.cancel()
                try:
                    await self._quote_refresh_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Market making strategy cleanup completed")

        except Exception as e:
            self.logger.error("Error during market making cleanup", error=str(e))

    async def _update_order_book(self, symbol: str, market_data: Dict[str, Any]):
        """Update order book data for a symbol."""
        try:
            # Extract order book data
            order_book = market_data.get('order_book', {})
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])

            if not bids or not asks:
                return

            # Calculate best bid/ask
            bid_price = Decimal(str(bids[0][0]))
            ask_price = Decimal(str(asks[0][0]))
            bid_volume = Decimal(str(bids[0][1]))
            ask_volume = Decimal(str(asks[0][1]))

            # Calculate spread and mid price
            spread = ask_price - bid_price
            mid_price = (bid_price + ask_price) / 2

            # Calculate volatility if we have price history
            current_price = float(mid_price)
            if symbol in self._price_volatility:
                volatility = self._calculate_volatility(symbol, current_price)
            else:
                volatility = 0.0

            # Create order book snapshot
            snapshot = OrderBookSnapshot(
                symbol=symbol,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                spread=spread,
                mid_price=mid_price,
                timestamp=datetime.now(),
                volatility=volatility
            )

            self._order_books[symbol] = snapshot

            # Update inventory state
            await self._update_inventory_state(symbol)

        except Exception as e:
            self.logger.error("Error updating order book",
                            symbol=symbol, error=str(e))

    async def _update_inventory_state(self, symbol: str):
        """Update inventory state for a symbol."""
        try:
            if symbol not in self._inventory_states:
                return

            # Get current position from position manager
            if self._position_manager:
                positions = await self._position_manager.get_positions(self.name)
                symbol_positions = [p for p in positions if p.symbol == symbol]

                current_position = Decimal('0')
                for pos in symbol_positions:
                    current_position += pos.quantity

                inventory_state = self._inventory_states[symbol]
                inventory_state.current_position = current_position
                inventory_state.position_deviation = current_position - inventory_state.target_position

        except Exception as e:
            self.logger.error("Error updating inventory state",
                            symbol=symbol, error=str(e))

    def _calculate_volatility(self, symbol: str, current_price: float) -> float:
        """Calculate price volatility for spread adjustment."""
        try:
            price_history = self._price_volatility[symbol]

            # Add current price to history
            price_history.append(current_price)

            # Maintain window size
            if len(price_history) > self.config.volatility_window:
                price_history.pop(0)

            # Calculate volatility if we have enough data
            if len(price_history) >= 5:
                returns = [
                    (price_history[i] - price_history[i-1]) / price_history[i-1]
                    for i in range(1, len(price_history))
                ]
                return statistics.stdev(returns) if len(returns) > 1 else 0.0

            return 0.0

        except Exception:
            return 0.0

    def _calculate_dynamic_spread(self, symbol: str) -> Decimal:
        """
        Calculate dynamic spread based on market conditions.

        Args:
            symbol: Trading symbol

        Returns:
            Dynamic spread as decimal
        """
        try:
            if symbol not in self._order_books:
                return self.config.base_spread_percentage

            order_book = self._order_books[symbol]

            # Base spread
            spread = self.config.base_spread_percentage

            # Adjust for volatility
            if order_book.volatility > 0:
                volatility_adjustment = order_book.volatility * float(self.config.volatility_adjustment_factor)
                spread += Decimal(str(volatility_adjustment))

            # Adjust for inventory imbalance
            if symbol in self._inventory_states:
                inventory_state = self._inventory_states[symbol]
                inventory_factor = abs(inventory_state.position_deviation) / max(
                    abs(inventory_state.target_position), Decimal('0.1')
                )
                spread *= (1 + float(inventory_factor))

            # Apply min/max bounds
            spread = max(spread, self.config.min_spread_percentage)
            spread = min(spread, self.config.max_spread_percentage)

            return spread

        except Exception as e:
            self.logger.error("Error calculating dynamic spread",
                           symbol=symbol, error=str(e))
            return self.config.base_spread_percentage

    async def _should_refresh_quotes(self, symbol: str) -> bool:
        """Check if quotes should be refreshed for a symbol."""
        try:
            if symbol not in self._active_quotes:
                return True

            active_quotes = self._active_quotes[symbol]

            # Check if we have too few quotes
            if len(active_quotes) < 2:  # Need at least bid and ask
                return True

            # Check quote age
            current_time = datetime.now()
            for quote in active_quotes:
                age = (current_time - quote.timestamp).seconds
                if age > self.config.max_order_age:
                    return True

            # Check if spread has changed significantly
            if symbol in self._order_books:
                current_spread = self._calculate_dynamic_spread(symbol)
                order_book = self._order_books[symbol]

                # Refresh if spread changed by more than 10%
                spread_change = abs(current_spread - order_book.spread) / order_book.spread
                if spread_change > Decimal('0.1'):
                    return True

            return False

        except Exception as e:
            self.logger.error("Error checking quote refresh condition",
                           symbol=symbol, error=str(e))
            return True

    async def _refresh_quotes(self, symbol: str):
        """Refresh quotes for a symbol."""
        try:
            if symbol not in self._order_books:
                return

            order_book = self._order_books[symbol]
            dynamic_spread = self._calculate_dynamic_spread(symbol)

            # Cancel existing quotes
            await self._cancel_symbol_quotes(symbol)

            # Calculate new quote prices
            half_spread = (order_book.mid_price * dynamic_spread) / 2

            bid_price = order_book.mid_price - half_spread
            ask_price = order_book.mid_price + half_spread

            # Create new quotes
            bid_signal = TradingSignal(
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=1.0,
                quantity=self.config.quote_quantity,
                price=bid_price,
                timestamp=datetime.now(),
                metadata={'quote_type': 'bid', 'strategy': 'market_making'}
            )

            ask_signal = TradingSignal(
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=1.0,
                quantity=self.config.quote_quantity,
                price=ask_price,
                timestamp=datetime.now(),
                metadata={'quote_type': 'ask', 'strategy': 'market_making'}
            )

            # Execute quotes through trading engine
            if self._trading_engine:
                await self._trading_engine.execute_signal(bid_signal, self)
                await self._trading_engine.execute_signal(ask_signal, self)

            # Track active quotes
            self._active_quotes[symbol] = [
                QuoteOrder(
                    order_id=f"{symbol}_bid_{int(time.time())}",
                    symbol=symbol,
                    side='bid',
                    price=bid_price,
                    quantity=self.config.quote_quantity,
                    timestamp=datetime.now()
                ),
                QuoteOrder(
                    order_id=f"{symbol}_ask_{int(time.time())}",
                    symbol=symbol,
                    side='ask',
                    price=ask_price,
                    quantity=self.config.quote_quantity,
                    timestamp=datetime.now()
                )
            ]

            self._quote_updates += 1

            self.logger.debug("Quotes refreshed",
                            symbol=symbol,
                            bid_price=float(bid_price),
                            ask_price=float(ask_price),
                            spread=float(dynamic_spread))

        except Exception as e:
            self.logger.error("Error refreshing quotes",
                           symbol=symbol, error=str(e))

    async def _cancel_symbol_quotes(self, symbol: str):
        """Cancel all active quotes for a symbol."""
        try:
            if symbol not in self._active_quotes:
                return

            # Cancel orders through trading engine
            if self._trading_engine:
                for quote in self._active_quotes[symbol]:
                    await self._trading_engine.cancel_order(quote.order_id, self.name)

            # Clear active quotes
            self._active_quotes[symbol] = []

        except Exception as e:
            self.logger.error("Error canceling symbol quotes",
                           symbol=symbol, error=str(e))

    async def _cancel_all_quotes(self):
        """Cancel all active quotes."""
        for symbol in self.config.symbols:
            await self._cancel_symbol_quotes(symbol)

    async def _quote_refresh_loop(self):
        """Background task for refreshing quotes."""
        self.logger.info("Starting quote refresh loop")

        while self._running:
            try:
                # Refresh quotes for all symbols
                for symbol in self.config.symbols:
                    if not self._running:
                        break

                    try:
                        if await self._should_refresh_quotes(symbol):
                            await self._refresh_quotes(symbol)
                    except Exception as e:
                        self.logger.error("Error refreshing quotes for symbol",
                                        symbol=symbol, error=str(e))

                # Wait for next refresh cycle
                await asyncio.sleep(self.config.order_refresh_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in quote refresh loop", error=str(e))
                await asyncio.sleep(1)

        self.logger.info("Quote refresh loop stopped")

    def _rebalance_inventory(self, symbol: str):
        """Rebalance inventory position for a symbol."""
        try:
            if symbol not in self._inventory_states:
                return

            inventory_state = self._inventory_states[symbol]

            # Check if rebalancing is needed
            if abs(inventory_state.position_deviation) < self.config.rebalance_threshold:
                return

            self.logger.info("Rebalancing inventory",
                           symbol=symbol,
                           current_position=float(inventory_state.current_position),
                           target_position=float(inventory_state.target_position),
                           deviation=float(inventory_state.position_deviation))

            # Create rebalancing signal
            if inventory_state.position_deviation > 0:
                # Too much inventory, sell to reduce
                rebalance_signal = TradingSignal(
                    symbol=symbol,
                    direction=SignalDirection.SELL,
                    confidence=0.8,
                    quantity=min(inventory_state.position_deviation, self.config.quote_quantity),
                    timestamp=datetime.now(),
                    metadata={'rebalance': True, 'strategy': 'market_making'}
                )
            else:
                # Too little inventory, buy to increase
                rebalance_signal = TradingSignal(
                    symbol=symbol,
                    direction=SignalDirection.BUY,
                    confidence=0.8,
                    quantity=min(abs(inventory_state.position_deviation), self.config.quote_quantity),
                    timestamp=datetime.now(),
                    metadata={'rebalance': True, 'strategy': 'market_making'}
                )

            inventory_state.rebalance_count += 1
            inventory_state.last_rebalance = datetime.now()

            return rebalance_signal

        except Exception as e:
            self.logger.error("Error rebalancing inventory",
                           symbol=symbol, error=str(e))
            return None

    def get_strategy_metrics(self) -> Dict[str, Any]:
        """Get market making specific metrics."""
        try:
            total_quotes = sum(len(quotes) for quotes in self._active_quotes.values())
            total_inventory = sum(abs(state.position_deviation) for state in self._inventory_states.values())

            return {
                "quote_updates": self._quote_updates,
                "active_quotes": total_quotes,
                "fills": self._fills,
                "spread_earned": float(self._spread_earned),
                "total_inventory_deviation": float(total_inventory),
                "average_volatility": {
                    symbol: sum(volatility_history) / len(volatility_history)
                    if volatility_history else 0.0
                    for symbol, volatility_history in self._price_volatility.items()
                }
            }

        except Exception as e:
            self.logger.error("Error getting strategy metrics", error=str(e))
            return {}

    def update_quote_fill(self, symbol: str, side: str, quantity: Decimal, price: Decimal):
        """Update tracking when a quote is filled."""
        try:
            self._fills += 1

            # Update inventory state
            if symbol in self._inventory_states:
                inventory_state = self._inventory_states[symbol]

                if side.lower() == 'buy':
                    inventory_state.current_position += quantity
                else:
                    inventory_state.current_position -= quantity

                inventory_state.position_deviation = (
                    inventory_state.current_position - inventory_state.target_position
                )

            # Calculate spread earned
            if symbol in self._order_books:
                mid_price = self._order_books[symbol].mid_price
                spread_earned = abs(price - mid_price) * quantity
                self._spread_earned += spread_earned

            self.logger.debug("Quote filled",
                            symbol=symbol,
                            side=side,
                            quantity=float(quantity),
                            price=float(price))

        except Exception as e:
            self.logger.error("Error updating quote fill",
                           symbol=symbol, error=str(e))