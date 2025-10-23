"""Main trading engine for the crypto trading bot."""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Dict, List, Optional, Set, Union

from ..api.client import ExchangeAPIClient
from ..auth import ExchangeAuthenticator
from ..config import get_settings
from ...utils.logging import get_logger, log_error_with_context
from .position_manager import Position, PositionManager


class TradingEngineError(Exception):
    """Base exception for trading engine errors."""
    pass


class InsufficientFundsError(TradingEngineError):
    """Raised when there are insufficient funds for a trade."""
    pass


class InvalidOrderError(TradingEngineError):
    """Raised when an order is invalid."""
    pass


class RiskLimitExceededError(TradingEngineError):
    """Raised when risk limits are exceeded."""
    pass


class Order:
    """Represents a trading order."""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        status: str = "PENDING",
        timestamp: Optional[float] = None,
        filled_quantity: float = 0.0,
        remaining_quantity: Optional[float] = None,
        fee: float = 0.0,
        strategy: Optional[str] = None,
    ):
        """Initialize order.

        Args:
            order_id: Unique order identifier
            symbol: Trading symbol
            side: Order side (BUY or SELL)
            order_type: Order type (MARKET, LIMIT, etc.)
            quantity: Order quantity
            price: Order price (for limit orders)
            status: Order status
            timestamp: Order creation timestamp
            filled_quantity: Quantity that has been filled
            remaining_quantity: Remaining quantity to be filled
            fee: Transaction fee
            strategy: Strategy that created the order
        """
        self.order_id = order_id
        self.symbol = symbol
        self.side = side.upper()
        self.order_type = order_type.upper()
        self.quantity = quantity
        self.price = price
        self.status = status
        self.timestamp = timestamp or time.time()
        self.filled_quantity = filled_quantity
        self.remaining_quantity = remaining_quantity or (quantity - filled_quantity)
        self.fee = fee
        self.strategy = strategy

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "FILLED"

    @property
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in ("PENDING", "PARTIAL_FILLED")

    @property
    def is_cancelled(self) -> bool:
        """Check if order is cancelled."""
        return self.status == "CANCELLED"

    @property
    def progress_percentage(self) -> float:
        """Get order fill progress as percentage."""
        if self.quantity == 0:
            return 100.0
        return (self.filled_quantity / self.quantity) * 100.0

    def update_from_api_response(self, api_data: Dict) -> None:
        """Update order from API response data.

        Args:
            api_data: API response data
        """
        self.status = api_data.get('status', self.status)
        self.filled_quantity = float(api_data.get('executedQty', self.filled_quantity))
        self.remaining_quantity = float(api_data.get('origQty', self.quantity)) - self.filled_quantity
        self.fee = float(api_data.get('fee', self.fee))

    def to_dict(self) -> Dict:
        """Convert order to dictionary."""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status,
            'timestamp': self.timestamp,
            'filled_quantity': self.filled_quantity,
            'remaining_quantity': self.remaining_quantity,
            'fee': self.fee,
            'strategy': self.strategy,
            'progress_percentage': self.progress_percentage,
        }

    def __str__(self) -> str:
        """String representation of order."""
        return f"Order({self.order_id}, {self.side} {self.quantity} {self.symbol} @ {self.price})"


class TradingEngine:
    """Main trading engine that orchestrates all trading activities."""

    def __init__(
        self,
        authenticator: Optional[ExchangeAuthenticator] = None,
        api_client: Optional[ExchangeAPIClient] = None,
        position_manager: Optional[PositionManager] = None,
        max_positions: Optional[int] = None,
        dry_run: bool = False,
    ):
        """Initialize trading engine.

        Args:
            authenticator: Exchange authenticator
            api_client: Exchange API client
            position_manager: Position manager instance
            max_positions: Maximum number of concurrent positions
            dry_run: Enable dry run mode (no actual trades)
        """
        self.settings = get_settings()
        self.logger = get_logger("trading.engine")
        self.dry_run = dry_run

        # Core components
        self.authenticator = authenticator or ExchangeAuthenticator(
            exchange_name="default",
            api_key=self.settings.exchange.api_key,
            api_secret=self.settings.exchange.secret_key,
            sandbox=self.settings.exchange.sandbox,
        )

        self.api_client = api_client or ExchangeAPIClient(
            api_key=self.settings.exchange.api_key,
            secret_key=self.settings.exchange.secret_key,
            sandbox=self.settings.exchange.sandbox,
        )

        self.position_manager = position_manager or PositionManager()
        self.max_positions = max_positions or self.settings.trading.max_positions

        # Trading state
        self.orders: Dict[str, Order] = {}
        self.active_strategies: Set[str] = set()
        self.is_running = False
        self._shutdown_event = asyncio.Event()

        # Performance tracking
        self.stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'total_pnl': 0.0,
            'start_time': time.time(),
        }

    async def initialize(self) -> None:
        """Initialize the trading engine."""
        try:
            self.logger.info("Initializing trading engine...")

            # Authenticate with exchange
            if not await self.authenticator.is_authenticated():
                self.logger.error("Authentication failed")
                raise TradingEngineError("Authentication failed")

            # Initialize API client
            await self.api_client.close()  # Close default session
            auth_headers = await self.authenticator.get_auth_headers()
            self.api_client = ExchangeAPIClient(
                api_key=self.settings.exchange.api_key,
                secret_key=self.settings.exchange.secret_key,
                sandbox=self.settings.exchange.sandbox,
                headers=auth_headers,
            )

            # Load existing positions
            await self._load_existing_positions()

            # Load existing orders
            await self._load_existing_orders()

            self.logger.info("Trading engine initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize trading engine: {str(e)}")
            raise

    async def start(self) -> None:
        """Start the trading engine."""
        if self.is_running:
            self.logger.warning("Trading engine is already running")
            return

        self.is_running = True
        self._shutdown_event.clear()

        self.logger.info("Starting trading engine...")

        try:
            # Start the main trading loop
            await self._run_trading_loop()

        except asyncio.CancelledError:
            self.logger.info("Trading engine shutdown requested")
        except Exception as e:
            self.logger.error(f"Trading engine error: {str(e)}")
            log_error_with_context(self.logger, e, {'component': 'trading_engine'})
        finally:
            self.is_running = False

    async def stop(self) -> None:
        """Stop the trading engine."""
        if not self.is_running:
            return

        self.logger.info("Stopping trading engine...")
        self._shutdown_event.set()

        # Cancel any pending orders in dry run mode
        if self.dry_run:
            await self._cancel_all_orders()

    async def _run_trading_loop(self) -> None:
        """Main trading loop."""
        while not self._shutdown_event.is_set():
            try:
                # Check risk limits
                await self._check_risk_limits()

                # Update order statuses
                await self._update_order_statuses()

                # Update positions
                await self._update_positions()

                # Process strategies
                await self._process_strategies()

                # Sleep for a short interval
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {str(e)}")
                await asyncio.sleep(5.0)  # Wait before retrying

    async def _check_risk_limits(self) -> None:
        """Check and enforce risk limits."""
        try:
            # Check position limits
            current_positions = len(self.position_manager.positions)
            if current_positions >= self.max_positions:
                self.logger.warning(f"Maximum positions ({self.max_positions}) reached")

            # Check portfolio risk
            total_risk = sum(pos.risk_amount for pos in self.position_manager.positions.values())
            max_risk = self.settings.risk.max_portfolio_risk * self.position_manager.portfolio_value

            if total_risk > max_risk:
                self.logger.warning(f"Portfolio risk limit exceeded: {total_risk} > {max_risk}")
                # In a real implementation, this might trigger position reduction

        except Exception as e:
            self.logger.error(f"Error checking risk limits: {str(e)}")

    async def _update_order_statuses(self) -> None:
        """Update order statuses from exchange."""
        try:
            for order in list(self.orders.values()):
                if order.is_active:
                    try:
                        response = await self.api_client.get_order_status(order.symbol, order.order_id)

                        if response.status == 200:
                            order.update_from_api_response(response.data)

                            # Update position if order is filled
                            if order.is_filled:
                                await self._handle_filled_order(order)

                    except Exception as e:
                        self.logger.error(f"Error updating order {order.order_id}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error updating order statuses: {str(e)}")

    async def _update_positions(self) -> None:
        """Update position information."""
        try:
            # Update position P&L based on current market prices
            for symbol, position in self.position_manager.positions.items():
                try:
                    # Get current market price
                    ticker_response = await self.api_client.get_ticker(symbol)
                    if ticker_response.status == 200:
                        current_price = float(ticker_response.data['price'])
                        position.update_unrealized_pnl(current_price)

                except Exception as e:
                    self.logger.error(f"Error updating position {symbol}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error updating positions: {str(e)}")

    async def _process_strategies(self) -> None:
        """Process active trading strategies."""
        # Strategy processing would be implemented here
        # This is a placeholder for strategy integration
        pass

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        strategy: Optional[str] = None,
        **kwargs
    ) -> Optional[Order]:
        """Place a trading order.

        Args:
            symbol: Trading symbol
            side: Order side (BUY or SELL)
            order_type: Order type (MARKET, LIMIT, etc.)
            quantity: Order quantity
            price: Order price (for limit orders)
            strategy: Strategy name
            **kwargs: Additional order parameters

        Returns:
            Order instance if successful

        Raises:
            TradingEngineError: If order placement fails
        """
        try:
            # Validate order
            await self._validate_order(symbol, side, order_type, quantity, price)

            # Check risk limits
            await self._check_order_risk(symbol, side, quantity, price)

            # Generate order ID
            order_id = f"bot_{int(time.time() * 1000)}_{secrets.token_hex(4)}"

            # Create order object
            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                strategy=strategy,
            )

            if self.dry_run:
                # Simulate order placement in dry run mode
                self.logger.info(f"DRY RUN: Would place order: {order}")
                order.status = "FILLED"  # Simulate immediate fill
                order.filled_quantity = quantity
                order.remaining_quantity = 0.0

                # Simulate position update
                await self._handle_filled_order(order)

            else:
                # Place actual order
                response = await self.api_client.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    **kwargs
                )

                if response.status == 200:
                    order.update_from_api_response(response.data)
                    self.logger.info(f"Placed order: {order}")
                else:
                    raise TradingEngineError(f"Order placement failed: {response.data}")

            # Store order
            self.orders[order_id] = order

            # Update statistics
            self.stats['total_orders'] += 1
            if order.is_filled:
                self.stats['successful_orders'] += 1

            return order

        except Exception as e:
            self.stats['failed_orders'] += 1
            self.logger.error(f"Error placing order: {str(e)}")
            log_error_with_context(
                self.logger,
                e,
                {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'strategy': strategy,
                }
            )
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation was successful
        """
        if order_id not in self.orders:
            self.logger.warning(f"Order {order_id} not found")
            return False

        order = self.orders[order_id]

        if not order.is_active:
            self.logger.warning(f"Order {order_id} is not active")
            return False

        try:
            if self.dry_run:
                # Simulate order cancellation
                self.logger.info(f"DRY RUN: Would cancel order: {order_id}")
                order.status = "CANCELLED"
                return True

            response = await self.api_client.cancel_order(order.symbol, order_id)

            if response.status == 200:
                order.status = "CANCELLED"
                self.logger.info(f"Cancelled order: {order_id}")
                return True
            else:
                self.logger.error(f"Failed to cancel order {order_id}: {response.data}")
                return False

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False

    async def _validate_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> None:
        """Validate order parameters.

        Args:
            symbol: Trading symbol
            side: Order side
            order_type: Order type
            quantity: Order quantity
            price: Order price

        Raises:
            InvalidOrderError: If order is invalid
        """
        # Validate symbol
        if symbol not in self.settings.trading.supported_symbols:
            raise InvalidOrderError(f"Unsupported symbol: {symbol}")

        # Validate side
        if side.upper() not in ("BUY", "SELL"):
            raise InvalidOrderError(f"Invalid order side: {side}")

        # Validate order type
        valid_types = ("MARKET", "LIMIT", "STOP_LOSS", "STOP_LOSS_LIMIT", "TAKE_PROFIT", "TAKE_PROFIT_LIMIT")
        if order_type.upper() not in valid_types:
            raise InvalidOrderError(f"Invalid order type: {order_type}")

        # Validate quantity
        if quantity <= 0:
            raise InvalidOrderError(f"Invalid quantity: {quantity}")

        if quantity < self.settings.trading.min_order_size:
            raise InvalidOrderError(f"Quantity below minimum: {quantity} < {self.settings.trading.min_order_size}")

        # Validate price for limit orders
        if order_type.upper() in ("LIMIT", "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"):
            if price is None or price <= 0:
                raise InvalidOrderError(f"Price required for {order_type} order")

    async def _check_order_risk(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> None:
        """Check if order exceeds risk limits.

        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            price: Order price

        Raises:
            RiskLimitExceededError: If risk limits are exceeded
        """
        # Get current market price if not provided
        if price is None:
            try:
                ticker_response = await self.api_client.get_ticker(symbol)
                if ticker_response.status == 200:
                    price = float(ticker_response.data['price'])
            except Exception:
                # If we can't get price, assume order risk is acceptable
                return

        if not price:
            return

        # Calculate order value
        order_value = quantity * price

        # Check if this would exceed maximum order value
        if order_value > self.settings.trading.max_order_value:
            raise RiskLimitExceededError(f"Order value {order_value} exceeds maximum {self.settings.trading.max_order_value}")

        # Check portfolio risk impact
        current_positions = len(self.position_manager.positions)
        if current_positions >= self.max_positions:
            raise RiskLimitExceededError(f"Maximum positions ({self.max_positions}) reached")

    async def _handle_filled_order(self, order: Order) -> None:
        """Handle a filled order by updating positions.

        Args:
            order: Filled order
        """
        try:
            # Calculate average fill price (simplified)
            fill_price = order.price or 0.0  # Would be calculated from actual fills

            # Update or create position
            current_position = self.position_manager.positions.get(order.symbol)

            if order.side == "BUY":
                if current_position:
                    # Average into existing position
                    total_quantity = current_position.quantity + order.filled_quantity
                    total_cost = (current_position.avg_entry_price * current_position.quantity) + (fill_price * order.filled_quantity)
                    avg_price = total_cost / total_quantity

                    current_position.quantity = total_quantity
                    current_position.avg_entry_price = avg_price
                else:
                    # Create new position
                    position = Position(
                        symbol=order.symbol,
                        quantity=order.filled_quantity,
                        avg_entry_price=fill_price,
                        strategy=order.strategy,
                    )
                    self.position_manager.add_position(position)

            else:  # SELL
                if current_position:
                    # Reduce position
                    current_position.quantity -= order.filled_quantity

                    # Calculate P&L
                    pnl = (fill_price - current_position.avg_entry_price) * order.filled_quantity
                    self.stats['total_pnl'] += pnl

                    # Remove position if fully closed
                    if current_position.quantity <= 0:
                        self.position_manager.remove_position(order.symbol)

            self.logger.info(f"Updated position for {order.symbol} after filled order")

        except Exception as e:
            self.logger.error(f"Error handling filled order {order.order_id}: {str(e)}")

    async def _load_existing_positions(self) -> None:
        """Load existing positions from exchange."""
        try:
            if self.dry_run:
                return

            response = await self.api_client.get_account_info()

            if response.status == 200:
                # Parse positions from API response
                positions_data = response.data.get('positions', [])

                for pos_data in positions_data:
                    if float(pos_data.get('positionAmt', 0)) != 0:
                        position = Position(
                            symbol=pos_data['symbol'],
                            quantity=float(pos_data['positionAmt']),
                            avg_entry_price=float(pos_data.get('entryPrice', 0)),
                        )
                        self.position_manager.add_position(position)

                self.logger.info(f"Loaded {len(positions_data)} existing positions")

        except Exception as e:
            self.logger.error(f"Error loading existing positions: {str(e)}")

    async def _load_existing_orders(self) -> None:
        """Load existing orders from exchange."""
        try:
            if self.dry_run:
                return

            response = await self.api_client.get_open_orders()

            if response.status == 200:
                orders_data = response.data

                for order_data in orders_data:
                    order = Order(
                        order_id=order_data['orderId'],
                        symbol=order_data['symbol'],
                        side=order_data['side'],
                        order_type=order_data['type'],
                        quantity=float(order_data['origQty']),
                        price=float(order_data.get('price', 0)) or None,
                        status=order_data['status'],
                        filled_quantity=float(order_data.get('executedQty', 0)),
                    )
                    self.orders[order.order_id] = order

                self.logger.info(f"Loaded {len(orders_data)} existing orders")

        except Exception as e:
            self.logger.error(f"Error loading existing orders: {str(e)}")

    async def _cancel_all_orders(self) -> None:
        """Cancel all active orders."""
        for order in list(self.orders.values()):
            if order.is_active:
                await self.cancel_order(order.order_id)

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order instance or None if not found
        """
        return self.orders.get(order_id)

    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of orders for the symbol
        """
        return [order for order in self.orders.values() if order.symbol == symbol]

    def get_active_orders(self) -> List[Order]:
        """Get all active orders.

        Returns:
            List of active orders
        """
        return [order for order in self.orders.values() if order.is_active]

    def get_order_statistics(self) -> Dict:
        """Get trading statistics.

        Returns:
            Dictionary of trading statistics
        """
        uptime = time.time() - self.stats['start_time']

        return {
            'uptime_seconds': uptime,
            'total_orders': self.stats['total_orders'],
            'successful_orders': self.stats['successful_orders'],
            'failed_orders': self.stats['failed_orders'],
            'success_rate': (self.stats['successful_orders'] / max(1, self.stats['total_orders'])) * 100,
            'total_pnl': self.stats['total_pnl'],
            'active_orders': len(self.get_active_orders()),
            'total_positions': len(self.position_manager.positions),
            'portfolio_value': self.position_manager.portfolio_value,
        }

    async def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary.

        Returns:
            Dictionary with portfolio information
        """
        return {
            'total_positions': len(self.position_manager.positions),
            'portfolio_value': self.position_manager.portfolio_value,
            'total_unrealized_pnl': sum(pos.unrealized_pnl for pos in self.position_manager.positions.values()),
            'total_realized_pnl': self.stats['total_pnl'],
            'positions': {
                symbol: pos.to_dict() for symbol, pos in self.position_manager.positions.items()
            },
        }

    async def shutdown(self) -> None:
        """Shutdown the trading engine gracefully."""
        self.logger.info("Shutting down trading engine...")

        # Stop the engine
        await self.stop()

        # Cancel all orders
        await self._cancel_all_orders()

        # Close API client
        await self.api_client.close()

        self.logger.info("Trading engine shutdown complete")