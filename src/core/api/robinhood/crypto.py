"""
Robinhood Crypto Trading

Handles cryptocurrency trading operations including placing orders,
canceling orders, and managing crypto positions on Robinhood.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union, TYPE_CHECKING

import structlog
from pydantic import BaseModel, Field, validator

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

    @validator('side')
    def validate_side(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError('Side must be "buy" or "sell"')
        return v.lower()

    @validator('order_type')
    def validate_order_type(cls, v):
        if v.lower() not in ['market', 'limit', 'stop', 'stop_limit']:
            raise ValueError('Order type must be market, limit, stop, or stop_limit')
        return v.lower()

    @validator('time_in_force')
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
            client: Robinhood API client instance
        """
        self.client = client
        self.logger = structlog.get_logger("robinhood.crypto")

        # Initialize the new crypto API client with proper token from main client
        # Get token from main client auth or use None if not authenticated yet
        access_token = None
        self.logger.info("🔍 DEBUG: Initializing crypto API")
        if hasattr(client, 'auth') and client.auth.is_authenticated():
            try:
                access_token = client.auth.get_access_token()
                self.logger.info(f"🔍 DEBUG: Got access token from main client: {access_token[:20]}...")
            except Exception as e:
                self.logger.warning("🔍 DEBUG: Could not get access token from main client", error=str(e))
        else:
            self.logger.warning("🔍 DEBUG: Main client auth not available or not authenticated")

        self.logger.info(f"🔍 DEBUG: Passing access_token to RobinhoodCryptoAPI: {access_token is not None}")
        self.crypto_api = RobinhoodCryptoAPI(access_token=access_token)

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
            raise RobinhoodAPIError(f"Failed to get quote for {symbol}: {e}")

    async def get_crypto_quotes(self, symbols: List[str]) -> List[CryptoQuote]:
        """Get quotes for multiple cryptocurrencies.

        Args:
            symbols: List of crypto symbols

        Returns:
            List of quote information
        """
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
            The /portfolios/crypto/ endpoint may be deprecated.
            Consider using get_crypto_positions() for current positions instead.
        """
        try:
            response = await self.client.get("/portfolios/crypto/")
            return response.data
        except Exception as e:
            self.logger.warning(
                "Failed to get crypto portfolio from deprecated endpoint",
                error=str(e),
                message="Consider using get_crypto_positions() instead"
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
        try:
            response = await self.client.get("/watchlists/crypto/")
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