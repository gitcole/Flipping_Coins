"""
Robinhood Crypto Trading

Handles cryptocurrency trading operations including placing orders,
canceling orders, and managing crypto positions on Robinhood.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union, TYPE_CHECKING

import structlog
from pydantic import BaseModel, Field, field_validator

from ..exceptions import RobinhoodAPIError
from .crypto_api import RobinhoodCryptoAPI, CryptoOrderRequest

if TYPE_CHECKING:
    from .client import RobinhoodClient

logger = structlog.get_logger(__name__)


class CryptoOrder(BaseModel):
    """Crypto order model."""

    symbol: str = Field(..., description="Crypto symbol (e.g., BTC, ETH)")
    quantity: Union[float, str] = Field(..., description="Order quantity")
    side: str = Field(..., description="Order side (buy or sell)")
    order_type: str = Field(..., description="Order type (market, limit)")
    time_in_force: str = Field(default="gtc", description="Time in force")
    price: Optional[Union[float, str]] = Field(None, description="Limit price")
    stop_price: Optional[Union[float, str]] = Field(None, description="Stop price")
    extended_hours: bool = Field(default=False, description="Allow extended hours")

    @field_validator('side')
    @classmethod
    def validate_side(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError('Side must be "buy" or "sell"')
        return v.lower()

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        if v.lower() not in ['market', 'limit', 'stop', 'stop_limit']:
            raise ValueError('Order type must be market, limit, stop, or stop_limit')
        return v.lower()

    @field_validator('time_in_force')
    @classmethod
    def validate_time_in_force(cls, v):
        valid_tif = ['gtc', 'gtd', 'ioc', 'fok']
        if v.lower() not in valid_tif:
            raise ValueError(f'Time in force must be one of: {valid_tif}')
        return v.lower()


class CryptoPosition(BaseModel):
    """Crypto position model."""

    symbol: str = Field(..., description="Crypto symbol")
    quantity: float = Field(..., description="Position quantity")
    average_buy_price: float = Field(..., description="Average buy price")
    current_price: float = Field(..., description="Current price")
    market_value: float = Field(..., description="Market value")
    cost_basis: float = Field(..., description="Cost basis")
    unrealized_pl: float = Field(..., description="Unrealized P&L")
    unrealized_pl_percent: float = Field(..., description="Unrealized P&L percentage")


class CryptoQuote(BaseModel):
    """Crypto quote model."""

    symbol: str = Field(..., description="Crypto symbol")
    bid_price: float = Field(..., description="Bid price")
    ask_price: float = Field(..., description="Ask price")
    last_trade_price: float = Field(..., description="Last trade price")
    volume: float = Field(..., description="24h volume")
    high_24h: float = Field(..., description="24h high")
    low_24h: float = Field(..., description="24h low")


class RobinhoodCrypto:
    """
    Handles cryptocurrency trading operations for Robinhood.

    Features:
    - Place crypto orders (market, limit, stop)
    - Cancel orders
    - Get order status and history
    - Manage crypto positions
    - Get real-time quotes
    - Historical price data
    """

    def __init__(self, client: RobinhoodClient):
        """Initialize crypto trading module.

        Args:
            client: Robinhood API client instance (legacy compatibility)
        """
        self.client = client
        self.logger = structlog.get_logger("robinhood.crypto")

        # Initialize enhanced crypto API directly from .env file
        # This bypasses the old OAuth authentication system
        self.logger.info("🔍 DEBUG: Initializing enhanced crypto API from .env file")
        try:
            from ...app.orchestrator import EnhancedRobinhoodCryptoAPI
            self.crypto_api = EnhancedRobinhoodCryptoAPI(config_path=".env")
            self.logger.info("✅ Enhanced crypto API initialized successfully")
        except Exception as e:
            self.logger.warning(f"⚠️  Enhanced crypto API initialization failed: {str(e)}")
            # Fallback to standard API with signature auth
            try:
                from ...config import get_settings
                settings = get_settings()
                if settings.robinhood.api_key and settings.robinhood.private_key:
                    self.crypto_api = RobinhoodCryptoAPI(settings.robinhood.api_key)
                    self.logger.info("✅ Standard crypto API initialized with signature auth")
                else:
                    self.logger.error("❌ No API credentials available for crypto API")
                    self.crypto_api = None
            except Exception as fallback_e:
                self.logger.error(f"❌ Fallback crypto API initialization failed: {str(fallback_e)}")
                self.crypto_api = None

    async def get_crypto_currencies(self) -> List[Dict]:
        """Get list of supported cryptocurrencies.

        Returns:
            List of crypto currency information
        """
        try:
            # Use new crypto API to get supported assets
            # This method now returns a simplified list for backward compatibility
            return []  # Placeholder - new API doesn't have a direct equivalent
        except Exception as e:
            self.logger.error("Failed to get cryptocurrencies", error=str(e))
            raise RobinhoodAPIError(f"Failed to get cryptocurrencies: {e}")

    async def get_crypto_info(self, symbol: str) -> Dict:
        """Get detailed information about a cryptocurrency.

        Args:
            symbol: Crypto symbol (e.g., BTC, ETH)

        Returns:
            Crypto currency information
        """
        try:
            # Use new crypto API - this method returns basic info for backward compatibility
            # The new API doesn't have a direct equivalent for detailed crypto info
            return {
                "symbol": symbol.upper(),
                "name": symbol.upper(),
                "type": "cryptocurrency",
                "min_order_size": "0.00000001",
                "max_order_size": "999999999",
            }
        except Exception as e:
            self.logger.error("Failed to get crypto info", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get crypto info for {symbol}: {e}")

    async def get_crypto_quote(self, symbol: str) -> CryptoQuote:
        """Get real-time quote for a cryptocurrency.

        Args:
            symbol: Crypto symbol

        Returns:
            Current quote information
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get quote for {symbol}: crypto API not initialized")

        try:
            # Use new crypto API
            quote = await self.crypto_api.get_quote(symbol.upper())

            return CryptoQuote(
                symbol=quote.symbol,
                bid_price=float(quote.bid_price),
                ask_price=float(quote.ask_price),
                last_trade_price=float(quote.last_trade_price),
                volume=float(quote.volume_24h),
                high_24h=float(quote.high_24h),
                low_24h=float(quote.low_24h),
            )
        except Exception as e:
            self.logger.error("Failed to get crypto quote", symbol=symbol, error=str(e))
            if self.crypto_api is None:
                self.logger.error("Crypto API is not initialized - cannot get quote")
                raise RobinhoodAPIError(f"Failed to get quote for {symbol}: crypto API not initialized")
            raise RobinhoodAPIError(f"Failed to get quote for {symbol}: {e}")

    async def get_crypto_quotes(self, symbols: List[str]) -> List[CryptoQuote]:
        """Get quotes for multiple cryptocurrencies.

        Args:
            symbols: List of crypto symbols

        Returns:
            List of quote information
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get quotes for {symbols}: crypto API not initialized")

        try:
            # Use new crypto API
            quotes_data = await self.crypto_api.get_quotes([s.upper() for s in symbols])

            quotes = []
            for quote in quotes_data:
                quotes.append(CryptoQuote(
                    symbol=quote.symbol,
                    bid_price=float(quote.bid_price),
                    ask_price=float(quote.ask_price),
                    last_trade_price=float(quote.last_trade_price),
                    volume=float(quote.volume_24h),
                    high_24h=float(quote.high_24h),
                    low_24h=float(quote.low_24h),
                ))

            return quotes
        except Exception as e:
            self.logger.error("Failed to get crypto quotes", symbols=symbols, error=str(e))
            raise RobinhoodAPIError(f"Failed to get quotes for {symbols}: {e}")

    async def get_crypto_historicals(
        self,
        symbol: str,
        interval: str = "hour",
        span: str = "day",
        bounds: str = "24_7"
    ) -> List[Dict]:
        """Get historical price data for a cryptocurrency.

        Args:
            symbol: Crypto symbol
            interval: Time interval (15second, 5minute, 10minute, hour, day, week)
            span: Time span (hour, day, week, month, 3month, year, 5year)
            bounds: Trading bounds (24_7, regular, extended)

        Returns:
            Historical price data

        Note:
            Historical crypto data is no longer supported by the current API.
            This method is deprecated and returns empty data.
        """
        self.logger.warning(
            "Historical crypto data not supported",
            symbol=symbol,
            message="The crypto API no longer provides historical data"
        )

        # Return empty list for backward compatibility
        return []

    async def place_crypto_order(self, order: CryptoOrder) -> Dict:
        """Place a crypto trading order.

        Args:
            order: Crypto order to place

        Returns:
            Order confirmation data
        """
        # Validate order
        if order.order_type in ['limit', 'stop_limit'] and not order.price:
            raise ValueError("Price is required for limit orders")

        if order.order_type in ['stop', 'stop_limit'] and not order.stop_price:
            raise ValueError("Stop price is required for stop orders")

        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to place order for {order.symbol}: crypto API not initialized")

        try:
            # Use new crypto API
            order_request = CryptoOrderRequest(
                side=order.side,
                order_type=order.order_type,
                symbol=order.symbol.upper(),
                quantity=str(order.quantity),
                time_in_force=order.time_in_force,
                price=str(order.price) if order.price else None,
                stop_price=str(order.stop_price) if order.stop_price else None,
            )

            order_response = await self.crypto_api.place_order(order_request)

            self.logger.info("Placed crypto order",
                           symbol=order.symbol,
                           side=order.side,
                           quantity=order.quantity,
                           order_type=order.order_type,
                           client_order_id=order_response.client_order_id)

            # Return response in legacy format for backward compatibility
            return {
                "id": order_response.id,
                "client_order_id": order_response.client_order_id,
                "side": order_response.side,
                "order_type": order_response.order_type,
                "symbol": order_response.symbol,
                "quantity": order_response.quantity,
                "status": order_response.status,
                "created_at": order_response.created_at,
                "updated_at": order_response.updated_at,
            }
        except Exception as e:
            self.logger.error("Failed to place crypto order",
                            symbol=order.symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to place order for {order.symbol}: {e}")

    async def place_market_buy_order(self, symbol: str, quantity: Union[float, str]) -> Dict:
        """Place a market buy order.

        Args:
            symbol: Crypto symbol
            quantity: Order quantity

        Returns:
            Order confirmation
        """
        order = CryptoOrder(
            symbol=symbol,
            quantity=quantity,
            side="buy",
            order_type="market"
        )
        return await self.place_crypto_order(order)

    async def place_market_sell_order(self, symbol: str, quantity: Union[float, str]) -> Dict:
        """Place a market sell order.

        Args:
            symbol: Crypto symbol
            quantity: Order quantity

        Returns:
            Order confirmation
        """
        order = CryptoOrder(
            symbol=symbol,
            quantity=quantity,
            side="sell",
            order_type="market"
        )
        return await self.place_crypto_order(order)

    async def place_limit_buy_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        price: Union[float, str]
    ) -> Dict:
        """Place a limit buy order.

        Args:
            symbol: Crypto symbol
            quantity: Order quantity
            price: Limit price

        Returns:
            Order confirmation
        """
        order = CryptoOrder(
            symbol=symbol,
            quantity=quantity,
            side="buy",
            order_type="limit",
            price=price
        )
        return await self.place_crypto_order(order)

    async def place_limit_sell_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        price: Union[float, str]
    ) -> Dict:
        """Place a limit sell order.

        Args:
            symbol: Crypto symbol
            quantity: Order quantity
            price: Limit price

        Returns:
            Order confirmation
        """
        order = CryptoOrder(
            symbol=symbol,
            quantity=quantity,
            side="sell",
            order_type="limit",
            price=price
        )
        return await self.place_crypto_order(order)

    async def get_crypto_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get crypto orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of crypto orders
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get crypto orders: crypto API not initialized")

        try:
            orders = await self.crypto_api.get_orders(symbol.upper() if symbol else None)
            # Return in legacy format for backward compatibility
            return orders
        except Exception as e:
            self.logger.error("Failed to get crypto orders", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get crypto orders: {e}")

    async def get_crypto_order(self, order_id: str) -> Dict:
        """Get specific crypto order.

        Args:
            order_id: Order ID

        Returns:
            Order information
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get order {order_id}: crypto API not initialized")

        try:
            order = await self.crypto_api.get_order(order_id)
            return order
        except Exception as e:
            self.logger.error("Failed to get crypto order", order_id=order_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get order {order_id}: {e}")

    async def cancel_crypto_order(self, order_id: str) -> Dict:
        """Cancel a crypto order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation confirmation
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to cancel order {order_id}: crypto API not initialized")

        try:
            result = await self.crypto_api.cancel_order(order_id)
            self.logger.info("Cancelled crypto order", order_id=order_id)
            return result
        except Exception as e:
            self.logger.error("Failed to cancel crypto order", order_id=order_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to cancel order {order_id}: {e}")

    async def get_crypto_positions(self) -> List[CryptoPosition]:
        """Get crypto positions.

        Returns:
            List of crypto positions
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get crypto positions: crypto API not initialized")

        try:
            # Use new crypto API
            positions_data = await self.crypto_api.get_positions()
            positions = []

            for pos in positions_data:
                positions.append(CryptoPosition(
                    symbol=pos.asset_code,  # Use asset_code as symbol for backward compatibility
                    quantity=float(pos.quantity),
                    average_buy_price=float(pos.average_cost),
                    current_price=float(pos.current_price),
                    market_value=float(pos.market_value),
                    cost_basis=float(pos.market_value) - float(pos.unrealized_pnl),  # Calculate cost basis
                    unrealized_pl=float(pos.unrealized_pnl),
                    unrealized_pl_percent=float(pos.unrealized_pnl_percent),
                ))

            return positions
        except Exception as e:
            self.logger.error("Failed to get crypto positions", error=str(e))
            raise RobinhoodAPIError(f"Failed to get crypto positions: {e}")

    async def get_crypto_position(self, symbol: str) -> Optional[CryptoPosition]:
        """Get specific crypto position.

        Args:
            symbol: Crypto symbol

        Returns:
            Position information or None if not found
        """
        positions = await self.get_crypto_positions()
        for position in positions:
            if position.symbol.upper() == symbol.upper():
                return position
        return None

    async def get_crypto_account_info(self) -> Dict:
        """Get crypto account information.

        Returns:
            Crypto account information
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get crypto account info: crypto API not initialized")

        try:
            # Use new crypto API
            account = await self.crypto_api.get_account()

            # Return in legacy format for backward compatibility
            return {
                "id": account.id,
                "account_number": account.account_number,
                "status": account.status,
                "buying_power": account.buying_power,
                "cash_balance": account.cash_balance,
                "currency": account.currency,
                "type": "cryptocurrency",
                "crypto_trading_enabled": account.status == "active",
            }
        except Exception as e:
            self.logger.error("Failed to get crypto account info", error=str(e))
            raise RobinhoodAPIError(f"Failed to get crypto account info: {e}")

    async def get_crypto_portfolio(self) -> Dict:
        """Get crypto portfolio information.

        Returns:
            Portfolio information

        Note:
            Updated to use crypto API positions instead of deprecated /portfolios/crypto/ endpoint.
        """
        self.logger.info("🔍 DEBUG: Getting crypto portfolio using crypto API positions")
        try:
            positions = await self.get_crypto_positions()
            total_market_value = sum(float(pos.market_value) for pos in positions)
            total_cost_basis = sum(float(pos.cost_basis) for pos in positions)
            total_unrealized_pl = sum(float(pos.unrealized_pl) for pos in positions)

            portfolio = {
                "equity": str(total_market_value),
                "extended_hours_equity": str(total_market_value),  # Assuming same for crypto
                "market_value": str(total_market_value),
                "adjusted_equity_previous_close": "0.00",  # Not available from positions
                "equity_previous_close": "0.00"
            }
            self.logger.info("🔍 DEBUG: Crypto portfolio computed from positions", total_value=total_market_value)
            return portfolio
        except Exception as e:
            self.logger.warning(
                "Failed to get crypto portfolio from positions",
                error=str(e),
                message="Falling back to empty portfolio"
            )
            # Return empty portfolio structure for backward compatibility
            return {
                "equity": "0.00",
                "extended_hours_equity": "0.00",
                "market_value": "0.00",
                "adjusted_equity_previous_close": "0.00",
                "equity_previous_close": "0.00"
            }

    async def _get_crypto_account_id(self) -> str:
        """Get the crypto trading account ID.

        Returns:
            Account ID for crypto trading

        Raises:
            RobinhoodAPIError: If no crypto account found
        """
        if self.crypto_api is None:
            raise RobinhoodAPIError(f"Failed to get crypto account ID: crypto API not initialized")

        try:
            # Use new crypto API to get account
            account = await self.crypto_api.get_account()
            return account.id
        except Exception as e:
            self.logger.error("Failed to get crypto account ID", error=str(e))
            raise RobinhoodAPIError(f"Failed to get crypto account ID: {e}")

    async def is_crypto_trading_enabled(self) -> bool:
        """Check if crypto trading is enabled for the account.

        Returns:
            True if crypto trading is enabled
        """
        try:
            account_info = await self.get_crypto_account_info()
            return account_info.get("crypto_trading_enabled", False)
        except Exception:
            return False

    async def get_minimum_order_size(self, symbol: str) -> float:
        """Get minimum order size for a crypto symbol.

        Args:
            symbol: Crypto symbol

        Returns:
            Minimum order size
        """
        try:
            crypto_info = await self.get_crypto_info(symbol)
            return float(crypto_info.get("min_order_size", 0))
        except Exception as e:
            self.logger.warning("Failed to get minimum order size", symbol=symbol, error=str(e))
            return 0.0

    async def get_trading_hours(self, symbol: str) -> Dict:
        """Get trading hours for a crypto symbol.

        Args:
            symbol: Crypto symbol

        Returns:
            Trading hours information
        """
        try:
            crypto_info = await self.get_crypto_info(symbol)
            return crypto_info.get("trading_hours", {})
        except Exception as e:
            self.logger.error("Failed to get trading hours", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get trading hours for {symbol}: {e}")

    async def get_crypto_watchlists(self) -> List[Dict]:
        """Get crypto watchlists.

        Returns:
            List of crypto watchlists
        """
        self.logger.info("🔍 DEBUG: Attempting to get crypto watchlists using main client")
        try:
            response = await self.client.get("/watchlists/crypto/")
            self.logger.info("🔍 DEBUG: Crypto watchlists retrieved successfully", count=len(response.data.get("results", [])))
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get crypto watchlists", error=str(e))
            raise RobinhoodAPIError(f"Failed to get crypto watchlists: {e}")

    async def add_to_crypto_watchlist(self, symbol: str) -> Dict:
        """Add a crypto symbol to watchlist.

        Args:
            symbol: Crypto symbol to add

        Returns:
            Watchlist addition confirmation
        """
        try:
            # Get default crypto watchlist
            watchlists = await self.get_crypto_watchlists()
            if not watchlists:
                raise RobinhoodAPIError("No crypto watchlist found")

            watchlist_id = watchlists[0]["id"]

            data = {
                "currency": {"code": symbol.upper()}
            }

            response = await self.client.post(f"/watchlists/{watchlist_id}/", data=data)
            self.logger.info("Added crypto to watchlist", symbol=symbol)
            return response.data
        except Exception as e:
            self.logger.error("Failed to add crypto to watchlist", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to add {symbol} to watchlist: {e}")

    async def remove_from_crypto_watchlist(self, symbol: str) -> bool:
        """Remove a crypto symbol from watchlist.

        Args:
            symbol: Crypto symbol to remove

        Returns:
            True if removal successful
        """
        try:
            # This would require getting the specific watchlist item ID first
            # For now, return False as this is a more complex operation
            self.logger.warning("Remove from watchlist not fully implemented", symbol=symbol)
            return False
        except Exception as e:
            self.logger.error("Failed to remove crypto from watchlist", symbol=symbol, error=str(e))
            return False