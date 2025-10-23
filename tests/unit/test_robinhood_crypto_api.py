"""
Unit tests for RobinhoodCryptoAPI class.

Tests cover async functionality, OAuth2 authentication, rate limiting,
error handling, and all core API methods including trading, market data,
and account management.
"""
import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal
from typing import Dict, Any

import aiohttp
from tests.utils.base_test import UnitTestCase
from core.api.robinhood.crypto_api import RobinhoodCryptoAPI, CryptoOrderRequest, CryptoOrderResponse
from core.api.exceptions import (
    RobinhoodAPIError, APIRateLimitError, APIConnectionError,
    APIAuthenticationError, APIAuthorizationError, APINotFoundError,
    APIInvalidRequestError, APIExchangeError
)
from core.config import get_settings


class TestRobinhoodCryptoAPI(UnitTestCase):
    """Test cases for RobinhoodCryptoAPI."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.access_token = "test_access_token_12345"
        self.base_url = "https://trading.robinhood.com"
        self.timeout = 30
        self.max_retries = 3

        # Mock settings
        with patch('core.api.robinhood.crypto_api.get_settings') as mock_settings:
            mock_settings.return_value.robinhood.api_token = self.access_token
            self.api = RobinhoodCryptoAPI(
                access_token=self.access_token,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries
            )

    def test_initialization_with_token(self):
        """Test initialization with access token."""
        assert self.api.access_token == self.access_token
        assert self.api.base_url == self.base_url.rstrip("/")
        assert self.api.timeout.total == self.timeout
        assert self.api.max_retries == self.max_retries
        assert self.api._session is None
        assert self.api._rate_limiter is None
        assert self.api._client_order_ids == set()
        assert self.api._request_count == 0
        assert self.api._error_count == 0

    def test_initialization_without_token(self):
        """Test initialization without access token."""
        with patch('core.api.robinhood.crypto_api.get_settings') as mock_settings:
            mock_settings.return_value.robinhood.api_token = None
            api = RobinhoodCryptoAPI()

            assert api.access_token is None
            assert api.base_url == "https://trading.robinhood.com"

    def test_initialization_from_settings(self):
        """Test initialization using settings token."""
        with patch('core.api.robinhood.crypto_api.get_settings') as mock_settings:
            mock_settings.return_value.robinhood.api_token = "settings_token"
            api = RobinhoodCryptoAPI()

            assert api.access_token == "settings_token"

    def test_generate_client_order_id_uniqueness(self):
        """Test client order ID generation ensures uniqueness."""
        ids = set()
        for _ in range(100):
            client_id = self.api._generate_client_order_id()
            assert client_id not in ids
            ids.add(client_id)
            assert isinstance(client_id, str)
            assert len(client_id) == 36  # UUID length

    def test_generate_client_order_id_memory_management(self):
        """Test that old client order IDs are removed when limit reached."""
        # Fill up the set
        for i in range(1000):
            self.api._client_order_ids.add(f"test_id_{i}")

        # Generate one more
        new_id = self.api._generate_client_order_id()

        # Should have removed oldest and added new one
        assert len(self.api._client_order_ids) == 1000
        assert new_id not in [f"test_id_{i}" for i in range(999)]  # Oldest should be gone

    async def test_initialize_session(self):
        """Test session initialization."""
        await self.api.initialize()

        assert self.api._session is not None
        assert self.api._rate_limiter is not None

        # Check session headers
        headers = self.api._session._default_headers
        assert headers["Authorization"] == f"Bearer {self.access_token}"
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "crypto-trading-bot/1.0.0"

    async def test_close_session(self):
        """Test session cleanup."""
        await self.api.initialize()
        await self.api.close()

        assert self.api._session is None

    async def test_context_manager(self):
        """Test async context manager."""
        async with RobinhoodCryptoAPI(access_token=self.access_token) as api:
            assert api._session is not None
            assert api._rate_limiter is not None

        # Should be closed after context
        assert api._session is None

    async def test_make_request_success(self):
        """Test successful API request."""
        await self.api.initialize()

        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True, "data": "test"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            result = await self.api._make_request("GET", "/test")

            assert result == {"success": True, "data": "test"}
            assert self.api._request_count == 1
            assert self.api._error_count == 0

    async def test_make_request_rate_limit(self):
        """Test rate limiting in API requests."""
        await self.api.initialize()

        # Mock rate limiter
        self.api._rate_limiter = AsyncMock()
        self.api._rate_limiter.wait_for_custom = AsyncMock(return_value=0.1)

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            result = await self.api._make_request("GET", "/test")

            assert result == {"success": True}
            self.api._rate_limiter.wait_for_custom.assert_called_with("trading", 1)

    async def test_make_request_rate_limit_error(self):
        """Test handling of rate limit errors."""
        await self.api.initialize()

        # Mock rate limit error
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={"error": "Rate limited"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APIRateLimitError("Rate limited", retry_after=60)

                with pytest.raises(APIRateLimitError):
                    await self.api._make_request("GET", "/test", retry_on_rate_limit=False)

    async def test_make_request_retry_on_error(self):
        """Test retry logic on network errors."""
        await self.api.initialize()

        # Mock connection error, then success
        call_count = 0
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("Connection timeout")
            else:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"success": True})
                return AsyncMock(__aenter__=AsyncMock(return_value=mock_response))

        with patch.object(self.api._session, 'request', side_effect=mock_request):
            result = await self.api._make_request("GET", "/test")

            assert result == {"success": True}
            assert call_count == 2  # Should retry once

    async def test_make_request_max_retries_exceeded(self):
        """Test behavior when max retries exceeded."""
        await self.api.initialize()

        # Always fail
        with patch.object(self.api._session, 'request', side_effect=asyncio.TimeoutError("Connection timeout")):
            with pytest.raises(APIConnectionError):
                await self.api._make_request("GET", "/test")

            assert self.api._error_count == 1

    async def test_get_account_success(self):
        """Test successful account retrieval."""
        await self.api.initialize()

        account_data = {
            "id": "test_account_id",
            "account_number": "123456789",
            "status": "active",
            "buying_power": "10000.00",
            "cash_balance": "5000.00",
            "currency": "USD"
        }

        with patch.object(self.api, '_make_request', return_value={"results": [account_data]}) as mock_request:
            result = await self.api.get_account()

            assert result.id == "test_account_id"
            assert result.account_number == "123456789"
            assert result.status == "active"
            mock_request.assert_called_with("GET", "/api/v1/crypto/trading/accounts/")

    async def test_get_account_no_account(self):
        """Test account retrieval when no account exists."""
        await self.api.initialize()

        with patch.object(self.api, '_make_request', return_value={"results": []}):
            with pytest.raises(RobinhoodAPIError, match="No crypto account found"):
                await self.api.get_account()

    async def test_get_positions_with_filters(self):
        """Test positions retrieval with asset code filters."""
        await self.api.initialize()

        positions_data = [
            {
                "asset_code": "BTC",
                "quantity": "0.1",
                "average_cost": "50000.00",
                "current_price": "51000.00",
                "market_value": "5100.00",
                "unrealized_pnl": "100.00",
                "unrealized_pnl_percent": "2.00"
            }
        ]

        with patch.object(self.api, '_make_request', return_value={"results": positions_data}) as mock_request:
            result = await self.api.get_positions(["BTC"])

            assert len(result) == 1
            assert result[0].asset_code == "BTC"
            mock_request.assert_called_with("GET", "/api/v1/crypto/trading/holdings/", params={"asset_code": "BTC"})

    async def test_get_positions_without_filters(self):
        """Test positions retrieval without filters."""
        await self.api.initialize()

        positions_data = [
            {
                "asset_code": "BTC",
                "quantity": "0.1",
                "average_cost": "50000.00",
                "current_price": "51000.00",
                "market_value": "5100.00",
                "unrealized_pnl": "100.00",
                "unrealized_pnl_percent": "2.00"
            }
        ]

        with patch.object(self.api, '_make_request', return_value={"results": positions_data}) as mock_request:
            result = await self.api.get_positions()

            assert len(result) == 1
            mock_request.assert_called_with("GET", "/api/v1/crypto/trading/holdings/", params={})

    async def test_get_quotes_multiple_symbols(self):
        """Test quotes retrieval for multiple symbols."""
        await self.api.initialize()

        quotes_data = {
            "results": [
                {
                    "symbol": "BTC",
                    "bid_price": "49990.00",
                    "ask_price": "50010.00",
                    "last_trade_price": "50000.00",
                    "volume_24h": "1000000.00",
                    "high_24h": "51000.00",
                    "low_24h": "49000.00"
                },
                {
                    "symbol": "ETH",
                    "bid_price": "2990.00",
                    "ask_price": "3010.00",
                    "last_trade_price": "3000.00",
                    "volume_24h": "500000.00",
                    "high_24h": "3100.00",
                    "low_24h": "2900.00"
                }
            ]
        }

        with patch.object(self.api, '_make_request', return_value=quotes_data) as mock_request:
            result = await self.api.get_quotes(["BTC", "ETH"])

            assert len(result) == 2
            assert result[0].symbol == "BTC"
            assert result[1].symbol == "ETH"
            mock_request.assert_called_with(
                "GET",
                "/api/v1/crypto/marketdata/best_bid_ask/",
                params={"symbol": "BTC,ETH"},
                rate_limit_type="market_data"
            )

    async def test_get_quote_single_symbol(self):
        """Test single symbol quote retrieval."""
        await self.api.initialize()

        quotes_data = {
            "results": [
                {
                    "symbol": "BTC",
                    "bid_price": "49990.00",
                    "ask_price": "50010.00",
                    "last_trade_price": "50000.00",
                    "volume_24h": "1000000.00",
                    "high_24h": "51000.00",
                    "low_24h": "49000.00"
                }
            ]
        }

        with patch.object(self.api, 'get_quotes', return_value=quotes_data["results"]) as mock_get_quotes:
            result = await self.api.get_quote("BTC")

            assert result.symbol == "BTC"
            assert result.bid_price == "49990.00"
            mock_get_quotes.assert_called_with(["BTC"])

    async def test_get_quote_no_result(self):
        """Test single quote retrieval when no quotes found."""
        await self.api.initialize()

        with patch.object(self.api, 'get_quotes', return_value=[]):
            with pytest.raises(RobinhoodAPIError, match="No quote found for symbol: BTC"):
                await self.api.get_quote("BTC")

    async def test_get_estimated_price(self):
        """Test estimated price retrieval."""
        await self.api.initialize()

        estimated_data = {
            "symbol": "BTC",
            "side": "buy",
            "quantity": "0.1",
            "estimated_price": "50000.00",
            "estimated_fees": "5.00"
        }

        with patch.object(self.api, '_make_request', return_value=estimated_data) as mock_request:
            result = await self.api.get_estimated_price("BTC", "buy", "0.1")

            assert result == estimated_data
            mock_request.assert_called_with(
                "GET",
                "/api/v1/crypto/marketdata/estimated_price/",
                params={"symbol": "BTC", "side": "buy", "quantity": "0.1"},
                rate_limit_type="market_data"
            )

    async def test_place_order_market_buy(self):
        """Test placing a market buy order."""
        await self.api.initialize()

        order_request = CryptoOrderRequest(
            side="buy",
            order_type="market",
            symbol="BTC",
            quantity=Decimal("0.1")
        )

        order_response_data = {
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

        with patch.object(self.api, '_make_request', return_value=order_response_data) as mock_request:
            with patch.object(self.api, '_generate_client_order_id', return_value="test_client_id"):
                result = await self.api.place_order(order_request)

                assert result.id == "test_order_id"
                assert result.client_order_id == "test_client_id"
                assert result.side == "buy"

                expected_data = {
                    "client_order_id": "test_client_id",
                    "side": "buy",
                    "type": "market",
                    "symbol": "BTC",
                    "quantity": "0.1",
                    "time_in_force": "gtc"
                }

                mock_request.assert_called_with(
                    "POST",
                    "/api/v1/crypto/trading/orders/",
                    data=expected_data,
                    rate_limit_type="orders"
                )

    async def test_place_order_limit_with_price(self):
        """Test placing a limit order with price."""
        await self.api.initialize()

        order_request = CryptoOrderRequest(
            side="sell",
            order_type="limit",
            symbol="ETH",
            quantity=Decimal("1.0"),
            price=Decimal("3000.00")
        )

        order_response_data = {
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

        with patch.object(self.api, '_make_request', return_value=order_response_data) as mock_request:
            with patch.object(self.api, '_generate_client_order_id', return_value="test_client_id"):
                result = await self.api.place_order(order_request)

                expected_data = {
                    "client_order_id": "test_client_id",
                    "side": "sell",
                    "type": "limit",
                    "symbol": "ETH",
                    "quantity": "1.0",
                    "time_in_force": "gtc",
                    "price": "3000.0"
                }

                mock_request.assert_called_with(
                    "POST",
                    "/api/v1/crypto/trading/orders/",
                    data=expected_data,
                    rate_limit_type="orders"
                )

    async def test_place_order_limit_missing_price(self):
        """Test placing limit order without price raises error."""
        await self.api.initialize()

        order_request = CryptoOrderRequest(
            side="buy",
            order_type="limit",
            symbol="BTC",
            quantity=Decimal("0.1")
            # Missing price
        )

        with pytest.raises(RobinhoodAPIError, match="Price is required for limit orders"):
            await self.api.place_order(order_request)

    async def test_place_order_stop_missing_stop_price(self):
        """Test placing stop order without stop price raises error."""
        await self.api.initialize()

        order_request = CryptoOrderRequest(
            side="sell",
            order_type="stop",
            symbol="ETH",
            quantity=Decimal("1.0")
            # Missing stop_price
        )

        with pytest.raises(RobinhoodAPIError, match="Stop price is required for stop orders"):
            await self.api.place_order(order_request)

    async def test_get_orders_with_symbol_filter(self):
        """Test getting orders with symbol filter."""
        await self.api.initialize()

        orders_data = {
            "results": [
                {
                    "id": "order1",
                    "symbol": "BTC",
                    "side": "buy",
                    "type": "market",
                    "status": "filled"
                }
            ]
        }

        with patch.object(self.api, '_make_request', return_value=orders_data) as mock_request:
            result = await self.api.get_orders("BTC")

            assert len(result) == 1
            assert result[0]["symbol"] == "BTC"
            mock_request.assert_called_with("GET", "/api/v1/crypto/trading/orders/", params={"symbol": "BTC"})

    async def test_get_orders_without_filter(self):
        """Test getting all orders."""
        await self.api.initialize()

        orders_data = {"results": []}

        with patch.object(self.api, '_make_request', return_value=orders_data) as mock_request:
            result = await self.api.get_orders()

            assert result == []
            mock_request.assert_called_with("GET", "/api/v1/crypto/trading/orders/", params={})

    async def test_get_order_specific(self):
        """Test getting specific order details."""
        await self.api.initialize()

        order_data = {
            "id": "test_order_id",
            "symbol": "BTC",
            "side": "buy",
            "status": "filled"
        }

        with patch.object(self.api, '_make_request', return_value=order_data) as mock_request:
            result = await self.api.get_order("test_order_id")

            assert result == order_data
            mock_request.assert_called_with("GET", "/api/v1/crypto/trading/orders/test_order_id/")

    async def test_cancel_order(self):
        """Test canceling an order."""
        await self.api.initialize()

        cancel_data = {"id": "test_order_id", "status": "cancelled"}

        with patch.object(self.api, '_make_request', return_value=cancel_data) as mock_request:
            result = await self.api.cancel_order("test_order_id")

            assert result == cancel_data
            mock_request.assert_called_with(
                "POST",
                "/api/v1/crypto/trading/orders/test_order_id/cancel/",
                rate_limit_type="orders"
            )

    async def test_place_market_buy_order_convenience(self):
        """Test convenience method for market buy order."""
        await self.api.initialize()

        order_response = CryptoOrderResponse(
            id="test_id",
            client_order_id="test_client_id",
            side="buy",
            order_type="market",
            symbol="BTC",
            quantity="0.1",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        with patch.object(self.api, 'place_order', return_value=order_response) as mock_place_order:
            result = await self.api.place_market_buy_order("BTC", Decimal("0.1"))

            assert result == order_response

            # Check that place_order was called with correct request
            mock_place_order.assert_called_once()
            call_args = mock_place_order.call_args[0][0]
            assert call_args.side == "buy"
            assert call_args.order_type == "market"
            assert call_args.symbol == "BTC"
            assert call_args.quantity == Decimal("0.1")

    async def test_place_limit_sell_order_convenience(self):
        """Test convenience method for limit sell order."""
        await self.api.initialize()

        order_response = CryptoOrderResponse(
            id="test_id",
            client_order_id="test_client_id",
            side="sell",
            order_type="limit",
            symbol="ETH",
            quantity="1.0",
            status="pending",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        with patch.object(self.api, 'place_order', return_value=order_response) as mock_place_order:
            result = await self.api.place_limit_sell_order("ETH", Decimal("1.0"), Decimal("3000.00"))

            assert result == order_response

            # Check that place_order was called with correct request
            mock_place_order.assert_called_once()
            call_args = mock_place_order.call_args[0][0]
            assert call_args.side == "sell"
            assert call_args.order_type == "limit"
            assert call_args.symbol == "ETH"
            assert call_args.quantity == Decimal("1.0")
            assert call_args.price == Decimal("3000.00")

    async def test_get_stats(self):
        """Test getting API client statistics."""
        await self.api.initialize()

        # Simulate some requests and errors
        self.api._request_count = 10
        self.api._error_count = 2
        self.api._last_request_time = 1234567890.0
        self.api._client_order_ids = {"id1", "id2", "id3"}

        stats = self.api.get_stats()

        assert stats["request_count"] == 10
        assert stats["error_count"] == 2
        assert stats["error_rate"] == 0.2  # 2/10
        assert stats["last_request_time"] == 1234567890.0
        assert stats["client_order_ids_tracked"] == 3

    async def test_health_check_healthy(self):
        """Test health check when API is healthy."""
        await self.api.initialize()

        account_data = {
            "id": "test_account_id",
            "account_number": "123456789",
            "status": "active",
            "buying_power": "10000.00",
            "cash_balance": "5000.00",
            "currency": "USD"
        }

        with patch.object(self.api, 'get_account', return_value=MagicMock(**account_data)):
            result = await self.api.health_check()

            assert result["status"] == "healthy"
            assert result["authenticated"] is True
            assert "timestamp" in result
            assert "stats" in result

    async def test_health_check_unhealthy(self):
        """Test health check when API is unhealthy."""
        await self.api.initialize()

        with patch.object(self.api, 'get_account', side_effect=RobinhoodAPIError("API Error")):
            result = await self.api.health_check()

            assert result["status"] == "unhealthy"
            assert result["authenticated"] is False
            assert result["error"] == "API Error"
            assert "timestamp" in result
            assert "stats" in result

    def test_request_stats_tracking(self):
        """Test that request statistics are properly tracked."""
        # Initially zero
        assert self.api._request_count == 0
        assert self.api._error_count == 0

        # Simulate request
        self.api._request_count += 1
        self.api._last_request_time = time.time()

        # Check updated stats
        stats = self.api.get_stats()
        assert stats["request_count"] == 1
        assert stats["error_rate"] == 0.0

        # Simulate error
        self.api._error_count += 1

        # Check updated error stats
        stats = self.api.get_stats()
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 1.0  # 1/1

    # Error Handling Tests

    async def test_make_request_400_bad_request(self):
        """Test handling of 400 Bad Request errors."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": "Invalid request"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APIInvalidRequestError("Invalid request")

                with pytest.raises(APIInvalidRequestError):
                    await self.api._make_request("POST", "/test", data={"invalid": "data"})

    async def test_make_request_401_unauthorized(self):
        """Test handling of 401 Unauthorized errors."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={"error": "Unauthorized"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APIAuthenticationError("Unauthorized")

                with pytest.raises(APIAuthenticationError):
                    await self.api._make_request("GET", "/test")

    async def test_make_request_403_forbidden(self):
        """Test handling of 403 Forbidden errors."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.json = AsyncMock(return_value={"error": "Forbidden"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APIAuthorizationError("Forbidden")

                with pytest.raises(APIAuthorizationError):
                    await self.api._make_request("GET", "/test")

    async def test_make_request_404_not_found(self):
        """Test handling of 404 Not Found errors."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={"error": "Not found"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APINotFoundError("Not found")

                with pytest.raises(APINotFoundError):
                    await self.api._make_request("GET", "/test")

    async def test_make_request_429_rate_limit_with_retry_after(self):
        """Test handling of 429 Rate Limit with retry-after header."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json = AsyncMock(return_value={"error": "Rate limited"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APIRateLimitError("Rate limited", retry_after=60)

                with pytest.raises(APIRateLimitError) as exc_info:
                    await self.api._make_request("GET", "/test", retry_on_rate_limit=False)

                assert exc_info.value.retry_after == 60

    async def test_make_request_500_server_error(self):
        """Test handling of 500 Server Error."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={"error": "Internal server error"})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                mock_handle.return_value = APIExchangeError("Server error: Internal server error")

                with pytest.raises(APIExchangeError):
                    await self.api._make_request("GET", "/test")

    async def test_make_request_connection_error(self):
        """Test handling of connection errors."""
        await self.api.initialize()

        with patch.object(self.api._session, 'request', side_effect=aiohttp.ClientConnectionError("Connection refused")):
            with pytest.raises(APIConnectionError):
                await self.api._make_request("GET", "/test")

    async def test_make_request_timeout_error(self):
        """Test handling of timeout errors."""
        await self.api.initialize()

        with patch.object(self.api._session, 'request', side_effect=asyncio.TimeoutError("Request timeout")):
            with pytest.raises(APIConnectionError):  # Should be wrapped in APIConnectionError
                await self.api._make_request("GET", "/test")

    async def test_make_request_json_decode_error(self):
        """Test handling of JSON decode errors."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch('core.api.exceptions.handle_http_error') as mock_handle:
                # Should handle as successful but with error fallback
                result = await self.api._make_request("GET", "/test")

                assert result == {"error": ""}  # Should contain error text

    async def test_make_request_empty_response(self):
        """Test handling of empty responses."""
        await self.api.initialize()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(None, None))
        mock_response.text = AsyncMock(return_value="")

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            result = await self.api._make_request("GET", "/test")

            assert result == {"error": ""}

    async def test_get_account_api_error(self):
        """Test account retrieval API error."""
        await self.api.initialize()

        with patch.object(self.api, '_make_request', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get crypto account"):
                await self.api.get_account()

    async def test_get_positions_api_error(self):
        """Test positions retrieval API error."""
        await self.api.initialize()

        with patch.object(self.api, '_make_request', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get crypto positions"):
                await self.api.get_positions()

    async def test_get_quotes_api_error(self):
        """Test quotes retrieval API error."""
        await self.api.initialize()

        with patch.object(self.api, '_make_request', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get crypto quotes"):
                await self.api.get_quotes(["BTC"])

    async def test_get_estimated_price_api_error(self):
        """Test estimated price API error."""
        await self.api.initialize()

        with patch.object(self.api, '_make_request', side_effect=RobinhoodAPIError("API Error")):
            with pytest.raises(RobinhoodAPIError, match="Failed to get estimated price"):
                await self.api.get_estimated_price("BTC", "buy", "0.1")

    async def test_place_order_api_error(self):
        """Test order placement API error."""
        await self.api.initialize()

        order_request = CryptoOrderRequest(
            side="buy",
            order_type="market",
            symbol="BTC",
            quantity=Decimal("0.1")
        )

        with patch.object(self.api, '_make_request', side_effect=RobinhoodAPIError("Order failed")):
            with pytest.raises(RobinhoodAPIError, match="Failed to place order"):
                await self.api.place_order(order_request)

    async def test_cancel_order_api_error(self):
        """Test order cancellation API error."""
        await self.api.initialize()

        with patch.object(self.api, '_make_request', side_effect=RobinhoodAPIError("Cancel failed")):
            with pytest.raises(RobinhoodAPIError, match="Failed to cancel order"):
                await self.api.cancel_order("test_order_id")

    async def test_health_check_api_error(self):
        """Test health check with API error."""
        await self.api.initialize()

        with patch.object(self.api, 'get_account', side_effect=RobinhoodAPIError("API Error")):
            result = await self.api.health_check()

            assert result["status"] == "unhealthy"
            assert result["authenticated"] is False
            assert result["error"] == "API Error"

    # Rate Limiting Tests

    async def test_rate_limiter_integration(self):
        """Test integration with rate limiter."""
        await self.api.initialize()

        # Mock rate limiter returning wait time
        self.api._rate_limiter.wait_for_custom = AsyncMock(return_value=0.5)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            result = await self.api._make_request("GET", "/test")

            assert result == {"success": True}
            self.api._rate_limiter.wait_for_custom.assert_called_with("trading", 1)

    async def test_rate_limiter_market_data(self):
        """Test rate limiter for market data requests."""
        await self.api.initialize()

        self.api._rate_limiter.wait_for_custom = AsyncMock(return_value=0.1)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"results": []})

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            await self.api.get_quotes(["BTC"])

            self.api._rate_limiter.wait_for_custom.assert_called_with("market_data", 1)

    async def test_rate_limiter_orders(self):
        """Test rate limiter for order requests."""
        await self.api.initialize()

        self.api._rate_limiter.wait_for_custom = AsyncMock(return_value=0.2)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": "order_id",
            "client_order_id": "client_id",
            "side": "buy",
            "order_type": "market",
            "symbol": "BTC",
            "quantity": "0.1",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        })

        order_request = CryptoOrderRequest(
            side="buy",
            order_type="market",
            symbol="BTC",
            quantity=Decimal("0.1")
        )

        with patch.object(self.api._session, 'request', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
            with patch.object(self.api, '_generate_client_order_id', return_value="client_id"):
                await self.api.place_order(order_request)

                self.api._rate_limiter.wait_for_custom.assert_called_with("orders", 1)

    # Backward Compatibility Tests

    async def test_convenience_methods_backward_compatibility(self):
        """Test that convenience methods work with existing code."""
        await self.api.initialize()

        # Mock successful responses
        with patch.object(self.api, 'place_order') as mock_place_order:
            mock_response = CryptoOrderResponse(
                id="test_id",
                client_order_id="test_client_id",
                side="buy",
                order_type="market",
                symbol="BTC",
                quantity="0.1",
                status="pending",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z"
            )
            mock_place_order.return_value = mock_response

            # Test market buy
            result = await self.api.place_market_buy_order("BTC", Decimal("0.1"))
            assert result == mock_response

            # Test market sell
            result = await self.api.place_market_sell_order("BTC", Decimal("0.1"))
            assert result == mock_response

            # Test limit buy
            result = await self.api.place_limit_buy_order("BTC", Decimal("0.1"), Decimal("50000"))
            assert result == mock_response

            # Test limit sell
            result = await self.api.place_limit_sell_order("BTC", Decimal("0.1"), Decimal("50000"))
            assert result == mock_response

            # Should have called place_order 4 times
            assert mock_place_order.call_count == 4

    async def test_crypto_order_request_validation(self):
        """Test CryptoOrderRequest validation."""
        # Valid order
        order = CryptoOrderRequest(
            side="buy",
            order_type="market",
            symbol="BTC",
            quantity=Decimal("0.1")
        )
        assert order.side == "buy"
        assert order.order_type == "market"

        # Test validators
        from pydantic import ValidationError

        # Invalid side
        with pytest.raises(ValidationError):
            CryptoOrderRequest(
                side="invalid",
                order_type="market",
                symbol="BTC",
                quantity=Decimal("0.1")
            )

        # Invalid order type
        with pytest.raises(ValidationError):
            CryptoOrderRequest(
                side="buy",
                order_type="invalid",
                symbol="BTC",
                quantity=Decimal("0.1")
            )