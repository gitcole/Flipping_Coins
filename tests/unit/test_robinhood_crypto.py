"""
Unit tests for RobinhoodCrypto wrapper class.

Tests cover the high-level crypto trading interface, backward compatibility,
order placement, position management, and account operations.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from core.api.robinhood.crypto import RobinhoodCrypto, CryptoOrder, CryptoPosition, CryptoQuote
from core.api.robinhood.crypto_api import CryptoOrderRequest, CryptoOrderResponse
from core.api.exceptions import RobinhoodAPIError


class TestRobinhoodCrypto(UnitTestCase):
    """Test cases for RobinhoodCrypto wrapper."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

        # Mock the main client
        self.mock_client = AsyncMock()
        self.mock_client.auth = AsyncMock()
        self.mock_client.auth.is_authenticated.return_value = True
        self.mock_client.auth.get_access_token.return_value = "test_access_token"

        # Create the crypto wrapper
        self.crypto = RobinhoodCrypto(self.mock_client)

    def test_initialization_with_authenticated_client(self):
        """Test initialization with authenticated client."""
        assert self.crypto.client == self.mock_client
        assert hasattr(self.crypto, 'crypto_api')
        assert self.crypto.crypto_api.access_token == "test_access_token"

    def test_initialization_with_unauthenticated_client(self):
        """Test initialization with unauthenticated client."""
        self.mock_client.auth.is_authenticated.return_value = False

        crypto = RobinhoodCrypto(self.mock_client)

        assert crypto.crypto_api.access_token is None

    def test_initialization_token_retrieval_failure(self):
        """Test initialization when token retrieval fails."""
        self.mock_client.auth.get_access_token.side_effect = Exception("Token error")

        with patch('structlog.get_logger') as mock_logger:
            crypto = RobinhoodCrypto(self.mock_client)

            # Should still create crypto_api but with None token
            assert crypto.crypto_api.access_token is None
            mock_logger.return_value.warning.assert_called()

    async def test_get_crypto_currencies(self):
        """Test getting supported cryptocurrencies."""
        # This method returns empty list for backward compatibility
        result = await self.crypto.get_crypto_currencies()

        assert result == []
        # No API calls should be made
        self.mock_client.get.assert_not_called()

    async def test_get_crypto_info(self):
        """Test getting crypto information."""
        result = await self.crypto.get_crypto_info("BTC")

        assert result["symbol"] == "BTC"
        assert result["name"] == "BTC"
        assert result["type"] == "cryptocurrency"
        assert result["min_order_size"] == "0.00000001"
        assert result["max_order_size"] == "999999999"

    async def test_get_crypto_quote(self):
        """Test getting crypto quote."""
        # Mock the crypto API response
        mock_quote = MagicMock()
        mock_quote.symbol = "BTC"
        mock_quote.bid_price = "49990.00"
        mock_quote.ask_price = "50010.00"
        mock_quote.last_trade_price = "50000.00"
        mock_quote.volume_24h = "1000000.00"
        mock_quote.high_24h = "51000.00"
        mock_quote.low_24h = "49000.00"

        with patch.object(self.crypto.crypto_api, 'get_quote', return_value=mock_quote):
            result = await self.crypto.get_crypto_quote("BTC")

            assert isinstance(result, CryptoQuote)
            assert result.symbol == "BTC"
            assert result.bid_price == 49990.0
            assert result.ask_price == 50010.0
            assert result.last_trade_price == 50000.0
            assert result.volume == 1000000.0
            assert result.high_24h == 51000.0
            assert result.low_24h == 49000.0

    async def test_get_crypto_quote_error(self):
        """Test crypto quote retrieval error handling."""
        with patch.object(self.crypto.crypto_api, 'get_quote', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get quote for BTC"):
                await self.crypto.get_crypto_quote("BTC")

    async def test_get_crypto_quotes_multiple(self):
        """Test getting quotes for multiple cryptocurrencies."""
        # Mock multiple quotes
        mock_quotes = [
            MagicMock(symbol="BTC", bid_price="49990.00", ask_price="50010.00",
                     last_trade_price="50000.00", volume_24h="1000000.00",
                     high_24h="51000.00", low_24h="49000.00"),
            MagicMock(symbol="ETH", bid_price="2990.00", ask_price="3010.00",
                     last_trade_price="3000.00", volume_24h="500000.00",
                     high_24h="3100.00", low_24h="2900.00")
        ]

        with patch.object(self.crypto.crypto_api, 'get_quotes', return_value=mock_quotes):
            result = await self.crypto.get_crypto_quotes(["BTC", "ETH"])

            assert len(result) == 2
            assert result[0].symbol == "BTC"
            assert result[1].symbol == "ETH"

            # Check conversion to CryptoQuote
            assert isinstance(result[0], CryptoQuote)
            assert result[0].bid_price == 49990.0

    async def test_get_crypto_quotes_error(self):
        """Test multiple quotes retrieval error handling."""
        with patch.object(self.crypto.crypto_api, 'get_quotes', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get quotes for"):
                await self.crypto.get_crypto_quotes(["BTC", "ETH"])

    async def test_get_crypto_historicals_deprecated(self):
        """Test historical data method (deprecated)."""
        result = await self.crypto.get_crypto_historicals("BTC")

        assert result == []
        # Should log warning about deprecation
        # Note: We can't easily test the logging without more complex setup

    async def test_place_crypto_order_market(self):
        """Test placing market order."""
        order = CryptoOrder(
            symbol="BTC",
            quantity=0.1,
            side="buy",
            order_type="market"
        )

        # Mock order response
        mock_response = MagicMock()
        mock_response.id = "test_order_id"
        mock_response.client_order_id = "test_client_id"
        mock_response.side = "buy"
        mock_response.order_type = "market"
        mock_response.symbol = "BTC"
        mock_response.quantity = "0.1"
        mock_response.status = "pending"
        mock_response.created_at = "2024-01-01T00:00:00Z"
        mock_response.updated_at = "2024-01-01T00:00:00Z"

        with patch.object(self.crypto.crypto_api, 'place_order', return_value=mock_response):
            result = await self.crypto.place_crypto_order(order)

            # Check legacy format response
            assert result["id"] == "test_order_id"
            assert result["client_order_id"] == "test_client_id"
            assert result["side"] == "buy"
            assert result["order_type"] == "market"
            assert result["symbol"] == "BTC"
            assert result["quantity"] == "0.1"
            assert result["status"] == "pending"

    async def test_place_crypto_order_limit(self):
        """Test placing limit order."""
        order = CryptoOrder(
            symbol="ETH",
            quantity=1.0,
            side="sell",
            order_type="limit",
            price=3000.00
        )

        mock_response = MagicMock()
        mock_response.id = "test_order_id"
        mock_response.client_order_id = "test_client_id"
        mock_response.side = "sell"
        mock_response.order_type = "limit"
        mock_response.symbol = "ETH"
        mock_response.quantity = "1.0"
        mock_response.status = "pending"
        mock_response.created_at = "2024-01-01T00:00:00Z"
        mock_response.updated_at = "2024-01-01T00:00:00Z"

        with patch.object(self.crypto.crypto_api, 'place_order', return_value=mock_response):
            result = await self.crypto.place_crypto_order(order)

            assert result["order_type"] == "limit"
            assert "price" not in result  # Legacy format doesn't include price

    async def test_place_crypto_order_limit_missing_price(self):
        """Test placing limit order without price raises error."""
        order = CryptoOrder(
            symbol="BTC",
            quantity=0.1,
            side="buy",
            order_type="limit"
            # Missing price
        )

        with pytest.raises(ValueError, match="Price is required for limit orders"):
            await self.crypto.place_crypto_order(order)

    async def test_place_crypto_order_stop_missing_stop_price(self):
        """Test placing stop order without stop price raises error."""
        order = CryptoOrder(
            symbol="ETH",
            quantity=1.0,
            side="sell",
            order_type="stop"
            # Missing stop_price
        )

        with pytest.raises(ValueError, match="Stop price is required for stop orders"):
            await self.crypto.place_crypto_order(order)

    async def test_place_crypto_order_api_error(self):
        """Test order placement API error handling."""
        order = CryptoOrder(
            symbol="BTC",
            quantity=0.1,
            side="buy",
            order_type="market"
        )

        with patch.object(self.crypto.crypto_api, 'place_order', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to place order for BTC"):
                await self.crypto.place_crypto_order(order)

    async def test_place_market_buy_order_convenience(self):
        """Test convenience method for market buy."""
        order_response = {
            "id": "test_order_id",
            "client_order_id": "test_client_id",
            "side": "buy",
            "order_type": "market",
            "symbol": "BTC",
            "quantity": "0.1",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

        with patch.object(self.crypto, 'place_crypto_order', return_value=order_response) as mock_place:
            result = await self.crypto.place_market_buy_order("BTC", 0.1)

            assert result == order_response

            # Check that correct order was created
            mock_place.assert_called_once()
            call_args = mock_place.call_args[0][0]
            assert call_args.symbol == "BTC"
            assert call_args.quantity == 0.1
            assert call_args.side == "buy"
            assert call_args.order_type == "market"

    async def test_place_limit_sell_order_convenience(self):
        """Test convenience method for limit sell."""
        order_response = {
            "id": "test_order_id",
            "client_order_id": "test_client_id",
            "side": "sell",
            "order_type": "limit",
            "symbol": "ETH",
            "quantity": "1.0",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

        with patch.object(self.crypto, 'place_crypto_order', return_value=order_response) as mock_place:
            result = await self.crypto.place_limit_sell_order("ETH", 1.0, 3000.00)

            assert result == order_response

            # Check that correct order was created
            mock_place.assert_called_once()
            call_args = mock_place.call_args[0][0]
            assert call_args.symbol == "ETH"
            assert call_args.quantity == 1.0
            assert call_args.side == "sell"
            assert call_args.order_type == "limit"
            assert call_args.price == 3000.00

    async def test_get_crypto_orders(self):
        """Test getting crypto orders."""
        orders_data = [
            {
                "id": "order1",
                "symbol": "BTC",
                "side": "buy",
                "type": "market",
                "status": "filled"
            }
        ]

        with patch.object(self.crypto.crypto_api, 'get_orders', return_value=orders_data):
            result = await self.crypto.get_crypto_orders()

            assert result == orders_data

    async def test_get_crypto_orders_with_symbol(self):
        """Test getting crypto orders with symbol filter."""
        orders_data = [
            {
                "id": "order1",
                "symbol": "BTC",
                "side": "buy",
                "type": "market",
                "status": "filled"
            }
        ]

        with patch.object(self.crypto.crypto_api, 'get_orders', return_value=orders_data) as mock_get_orders:
            result = await self.crypto.get_crypto_orders("BTC")

            assert result == orders_data
            mock_get_orders.assert_called_with("BTC")

    async def test_get_crypto_order_specific(self):
        """Test getting specific order."""
        order_data = {
            "id": "test_order_id",
            "symbol": "BTC",
            "side": "buy",
            "status": "filled"
        }

        with patch.object(self.crypto.crypto_api, 'get_order', return_value=order_data):
            result = await self.crypto.get_crypto_order("test_order_id")

            assert result == order_data

    async def test_cancel_crypto_order(self):
        """Test canceling crypto order."""
        cancel_data = {"id": "test_order_id", "status": "cancelled"}

        with patch.object(self.crypto.crypto_api, 'cancel_order', return_value=cancel_data):
            result = await self.crypto.cancel_crypto_order("test_order_id")

            assert result == cancel_data

    async def test_get_crypto_positions(self):
        """Test getting crypto positions."""
        # Mock API response
        positions_data = [
            MagicMock(
                asset_code="BTC",
                quantity="0.1",
                average_cost="50000.00",
                current_price="51000.00",
                market_value="5100.00",
                unrealized_pnl="100.00",
                unrealized_pnl_percent="2.00"
            )
        ]

        with patch.object(self.crypto.crypto_api, 'get_positions', return_value=positions_data):
            result = await self.crypto.get_crypto_positions()

            assert len(result) == 1
            assert isinstance(result[0], CryptoPosition)
            assert result[0].symbol == "BTC"
            assert result[0].quantity == 0.1
            assert result[0].average_buy_price == 50000.0
            assert result[0].current_price == 51000.0
            assert result[0].market_value == 5100.0
            assert result[0].unrealized_pl == 100.0
            assert result[0].unrealized_pl_percent == 2.0

    async def test_get_crypto_position_specific(self):
        """Test getting specific crypto position."""
        positions = [
            CryptoPosition(
                symbol="BTC",
                quantity=0.1,
                average_buy_price=50000.0,
                current_price=51000.0,
                market_value=5100.0,
                cost_basis=5000.0,
                unrealized_pl=100.0,
                unrealized_pl_percent=2.0
            ),
            CryptoPosition(
                symbol="ETH",
                quantity=1.0,
                average_buy_price=3000.0,
                current_price=3100.0,
                market_value=3100.0,
                cost_basis=3000.0,
                unrealized_pl=100.0,
                unrealized_pl_percent=3.33
            )
        ]

        with patch.object(self.crypto, 'get_crypto_positions', return_value=positions):
            result = await self.crypto.get_crypto_position("BTC")

            assert result is not None
            assert result.symbol == "BTC"

    async def test_get_crypto_position_not_found(self):
        """Test getting position that doesn't exist."""
        positions = [
            CryptoPosition(
                symbol="ETH",
                quantity=1.0,
                average_buy_price=3000.0,
                current_price=3100.0,
                market_value=3100.0,
                cost_basis=3000.0,
                unrealized_pl=100.0,
                unrealized_pl_percent=3.33
            )
        ]

        with patch.object(self.crypto, 'get_crypto_positions', return_value=positions):
            result = await self.crypto.get_crypto_position("BTC")

            assert result is None

    async def test_get_crypto_account_info(self):
        """Test getting crypto account information."""
        # Mock API response
        mock_account = MagicMock()
        mock_account.id = "test_account_id"
        mock_account.account_number = "123456789"
        mock_account.status = "active"
        mock_account.buying_power = "10000.00"
        mock_account.cash_balance = "5000.00"
        mock_account.currency = "USD"

        with patch.object(self.crypto.crypto_api, 'get_account', return_value=mock_account):
            result = await self.crypto.get_crypto_account_info()

            # Check legacy format
            assert result["id"] == "test_account_id"
            assert result["account_number"] == "123456789"
            assert result["status"] == "active"
            assert result["buying_power"] == "10000.00"
            assert result["cash_balance"] == "5000.00"
            assert result["currency"] == "USD"
            assert result["type"] == "cryptocurrency"
            assert result["crypto_trading_enabled"] is True

    async def test_get_crypto_account_info_inactive(self):
        """Test account info for inactive account."""
        mock_account = MagicMock()
        mock_account.id = "test_account_id"
        mock_account.account_number = "123456789"
        mock_account.status = "inactive"
        mock_account.buying_power = "10000.00"
        mock_account.cash_balance = "5000.00"
        mock_account.currency = "USD"

        with patch.object(self.crypto.crypto_api, 'get_account', return_value=mock_account):
            result = await self.crypto.get_crypto_account_info()

            assert result["crypto_trading_enabled"] is False

    async def test_get_crypto_portfolio_deprecated_endpoint(self):
        """Test crypto portfolio using deprecated endpoint."""
        portfolio_data = {
            "equity": "10000.00",
            "extended_hours_equity": "10000.00",
            "market_value": "10000.00",
            "adjusted_equity_previous_close": "9500.00",
            "equity_previous_close": "9500.00"
        }

        self.mock_client.get.return_value.data = portfolio_data

        result = await self.crypto.get_crypto_portfolio()

        assert result == portfolio_data
        self.mock_client.get.assert_called_with("/portfolios/crypto/")

    async def test_get_crypto_portfolio_error_fallback(self):
        """Test portfolio fallback when deprecated endpoint fails."""
        self.mock_client.get.side_effect = Exception("API Error")

        result = await self.crypto.get_crypto_portfolio()

        # Should return default empty structure
        assert result["equity"] == "0.00"
        assert result["market_value"] == "0.00"

    async def test_get_crypto_account_id(self):
        """Test getting crypto account ID."""
        mock_account = MagicMock()
        mock_account.id = "test_account_id"

        with patch.object(self.crypto.crypto_api, 'get_account', return_value=mock_account):
            result = await self.crypto._get_crypto_account_id()

            assert result == "test_account_id"

    async def test_is_crypto_trading_enabled_true(self):
        """Test checking if crypto trading is enabled (true)."""
        account_info = {"crypto_trading_enabled": True}

        with patch.object(self.crypto, 'get_crypto_account_info', return_value=account_info):
            result = await self.crypto.is_crypto_trading_enabled()

            assert result is True

    async def test_is_crypto_trading_enabled_false(self):
        """Test checking if crypto trading is enabled (false)."""
        account_info = {"crypto_trading_enabled": False}

        with patch.object(self.crypto, 'get_crypto_account_info', return_value=account_info):
            result = await self.crypto.is_crypto_trading_enabled()

            assert result is False

    async def test_get_minimum_order_size(self):
        """Test getting minimum order size."""
        crypto_info = {"min_order_size": "0.00000001"}

        with patch.object(self.crypto, 'get_crypto_info', return_value=crypto_info):
            result = await self.crypto.get_minimum_order_size("BTC")

            assert result == 0.00000001

    async def test_get_minimum_order_size_error(self):
        """Test minimum order size with error fallback."""
        with patch.object(self.crypto, 'get_crypto_info', side_effect=Exception("API Error")):
            result = await self.crypto.get_minimum_order_size("BTC")

            assert result == 0.0

    async def test_get_trading_hours(self):
        """Test getting trading hours."""
        crypto_info = {"trading_hours": {"open": "00:00", "close": "23:59"}}

        with patch.object(self.crypto, 'get_crypto_info', return_value=crypto_info):
            result = await self.crypto.get_trading_hours("BTC")

            assert result == {"open": "00:00", "close": "23:59"}

    async def test_get_trading_hours_error(self):
        """Test trading hours with error."""
        with patch.object(self.crypto, 'get_crypto_info', side_effect=Exception("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get trading hours for BTC"):
                await self.crypto.get_trading_hours("BTC")

    async def test_get_crypto_watchlists(self):
        """Test getting crypto watchlists."""
        watchlists_data = {"results": [{"id": "watchlist1", "name": "Crypto Watchlist"}]}

        self.mock_client.get.return_value.data = watchlists_data

        result = await self.crypto.get_crypto_watchlists()

        assert result == [{"id": "watchlist1", "name": "Crypto Watchlist"}]
        self.mock_client.get.assert_called_with("/watchlists/crypto/")

    async def test_add_to_crypto_watchlist(self):
        """Test adding symbol to crypto watchlist."""
        # Mock watchlists
        watchlists_data = {"results": [{"id": "watchlist1"}]}
        self.mock_client.get.return_value.data = watchlists_data

        # Mock add to watchlist
        add_response = {"success": True}
        self.mock_client.post.return_value.data = add_response

        result = await self.crypto.add_to_crypto_watchlist("BTC")

        assert result == add_response
        self.mock_client.get.assert_called_with("/watchlists/crypto/")
        self.mock_client.post.assert_called_with("/watchlists/watchlist1/", data={"currency": {"code": "BTC"}})

    async def test_add_to_crypto_watchlist_no_watchlist(self):
        """Test adding to watchlist when no watchlist exists."""
        self.mock_client.get.return_value.data = {"results": []}

        with pytest.raises(RobinhoodAPIError, match="No crypto watchlist found"):
            await self.crypto.add_to_crypto_watchlist("BTC")

    async def test_remove_from_crypto_watchlist_not_implemented(self):
        """Test removing from watchlist (not fully implemented)."""
        result = await self.crypto.remove_from_crypto_watchlist("BTC")

        assert result is False