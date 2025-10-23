"""
Integration tests for crypto API with mocks.

Tests demonstrate how the mock API responses work with the actual crypto API
implementation, ensuring proper integration and realistic test scenarios.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from tests.mocks.api_mocks import RobinhoodApiMock
from core.api.robinhood.crypto_api import RobinhoodCryptoAPI, CryptoOrderRequest
from core.api.robinhood.crypto import RobinhoodCrypto
from core.api.exceptions import RobinhoodAPIError


class TestCryptoApiWithMocks(UnitTestCase):
    """Test crypto API integration with mocks."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.api_mock = RobinhoodApiMock()
        self.crypto_api = RobinhoodCryptoAPI(access_token="test_token")

    async def test_crypto_api_with_mock_responses(self):
        """Test crypto API using mock responses."""
        # Replace the internal session with our mock
        await self.crypto_api.initialize()

        # Mock the _make_request method to use our API mock
        with patch.object(self.crypto_api, '_make_request') as mock_make_request:
            # Configure mock responses
            async def mock_request_response(*args, **kwargs):
                endpoint = args[1] if len(args) > 1 else ""

                if endpoint == "/api/v1/crypto/trading/accounts/":
                    return {"results": [self.api_mock._crypto_accounts["default"]]}
                elif endpoint == "/api/v1/crypto/trading/holdings/":
                    return {"results": list(self.api_mock._crypto_positions.values())}
                elif "/api/v1/crypto/marketdata/best_bid_ask/" in endpoint:
                    symbols = kwargs.get('params', {}).get('symbol', '').split(',')
                    results = []
                    for symbol in symbols:
                        if symbol in self.api_mock._crypto_quotes:
                            results.append(self.api_mock._crypto_quotes[symbol])
                    return {"results": results}
                elif "/api/v1/crypto/trading/orders/" in endpoint:
                    if kwargs.get('params'):  # GET request
                        return {"results": list(self.api_mock._crypto_orders.values())}
                    else:  # POST request
                        order_data = args[2] if len(args) > 2 else {}
                        order_response = await self.api_mock.place_crypto_order(**order_data)
                        return order_response
                else:
                    return {"error": "Unknown endpoint"}

            mock_make_request.side_effect = mock_request_response

            # Test account retrieval
            account = await self.crypto_api.get_account()
            assert account.id == "crypto_account_id"
            assert account.status == "active"

            # Test positions retrieval
            positions = await self.crypto_api.get_positions()
            assert len(positions) == 2  # BTC and ETH
            assert positions[0].asset_code == "BTC"
            assert positions[1].asset_code == "ETH"

            # Test quotes retrieval
            quotes = await self.crypto_api.get_quotes(["BTC", "ETH"])
            assert len(quotes) == 2
            assert quotes[0].symbol == "BTC"
            assert quotes[1].symbol == "ETH"

            # Test order placement
            order_request = CryptoOrderRequest(
                side="buy",
                order_type="market",
                symbol="BTC",
                quantity="0.1"
            )

            with patch.object(self.crypto_api, '_generate_client_order_id', return_value="test_client_id"):
                order_response = await self.crypto_api.place_order(order_request)
                assert order_response.side == "buy"
                assert order_response.symbol == "BTC"
                assert order_response.quantity == "0.1"

    async def test_crypto_wrapper_with_mock_responses(self):
        """Test crypto wrapper using mock responses."""
        # Mock the main client
        mock_client = AsyncMock()
        mock_client.auth = AsyncMock()
        mock_client.auth.is_authenticated.return_value = True
        mock_client.auth.get_access_token.return_value = "test_token"

        # Create crypto wrapper
        crypto_wrapper = RobinhoodCrypto(mock_client)

        # Mock the crypto API methods
        with patch.object(crypto_wrapper.crypto_api, 'get_quote') as mock_get_quote:
            mock_get_quote.return_value = type('MockQuote', (), {
                'symbol': 'BTC',
                'bid_price': '49990.00',
                'ask_price': '50010.00',
                'last_trade_price': '50000.00',
                'volume_24h': '1000000.00',
                'high_24h': '51000.00',
                'low_24h': '49000.00'
            })()

            # Test quote retrieval
            quote = await crypto_wrapper.get_crypto_quote("BTC")
            assert quote.symbol == "BTC"
            assert quote.bid_price == 49990.0
            assert quote.ask_price == 50010.0

    async def test_mock_error_scenarios(self):
        """Test various error scenarios with mocks."""
        await self.crypto_api.initialize()

        # Test rate limit error
        with patch.object(self.crypto_api, '_make_request') as mock_make_request:
            from core.api.exceptions import APIRateLimitError

            async def mock_rate_limit(*args, **kwargs):
                raise APIRateLimitError("Rate limited", retry_after=60)

            mock_make_request.side_effect = mock_rate_limit

            with pytest.raises(APIRateLimitError):
                await self.crypto_api.get_account()

        # Test authentication error
        with patch.object(self.crypto_api, '_make_request') as mock_make_request:
            from core.api.exceptions import APIAuthenticationError

            async def mock_auth_error(*args, **kwargs):
                raise APIAuthenticationError("Authentication failed")

            mock_make_request.side_effect = mock_auth_error

            with pytest.raises(APIAuthenticationError):
                await self.crypto_api.get_positions()

    async def test_mock_dynamic_data_updates(self):
        """Test dynamic updates to mock data."""
        await self.crypto_api.initialize()

        # Start with default data
        with patch.object(self.crypto_api, '_make_request') as mock_make_request:
            async def mock_response(*args, **kwargs):
                return {"results": list(self.api_mock._crypto_positions.values())}

            mock_make_request.side_effect = mock_response

            positions = await self.crypto_api.get_positions()
            initial_count = len(positions)

            # Add new position via mock
            self.api_mock.add_crypto_position("ADA", "100.0", "1.50")

            positions = await self.crypto_api.get_positions()
            assert len(positions) == initial_count + 1

            # Update quote price
            self.api_mock.set_crypto_quote_price("BTC", 55000.0)

            # Verify quote was updated in mock
            assert self.api_mock._crypto_quotes["BTC"]["last_trade_price"] == "55000.0"

    async def test_mock_order_lifecycle(self):
        """Test complete order lifecycle with mocks."""
        await self.crypto_api.initialize()

        # Mock order operations
        with patch.object(self.crypto_api, '_make_request') as mock_make_request:
            # Track call count and responses
            call_count = 0
            placed_order = None

            async def mock_order_operations(*args, **kwargs):
                nonlocal call_count, placed_order
                call_count += 1

                if call_count == 1:  # Place order
                    order_data = args[2] if len(args) > 2 else {}
                    placed_order = {
                        "id": "test_order_123",
                        "client_order_id": order_data.get("client_order_id", "unknown"),
                        "side": order_data.get("side"),
                        "order_type": order_data.get("type"),
                        "symbol": order_data.get("symbol"),
                        "quantity": order_data.get("quantity"),
                        "status": "pending",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    }
                    return placed_order
                elif call_count == 2:  # Get orders
                    return {"results": [placed_order] if placed_order else []}
                elif call_count == 3:  # Cancel order
                    if placed_order:
                        placed_order["status"] = "cancelled"
                    return {"id": "test_order_123", "status": "cancelled"}
                else:
                    return {"results": []}

            mock_make_request.side_effect = mock_order_operations

            # Place order
            order_request = CryptoOrderRequest(
                side="buy",
                order_type="market",
                symbol="BTC",
                quantity="0.1"
            )

            with patch.object(self.crypto_api, '_generate_client_order_id', return_value="client_123"):
                order_response = await self.crypto_api.place_order(order_request)
                assert order_response.id == "test_order_123"
                assert order_response.status == "pending"

            # Get orders
            orders = await self.crypto_api.get_orders()
            assert len(orders) == 1
            assert orders[0]["id"] == "test_order_123"

            # Cancel order
            cancel_result = await self.crypto_api.cancel_order("test_order_123")
            assert cancel_result["status"] == "cancelled"

    def test_mock_configuration_methods(self):
        """Test mock configuration and utility methods."""
        # Test initial state
        assert self.api_mock.authenticated is False
        assert self.api_mock.request_count == 0

        # Test authentication setup
        self.api_mock.authenticated = True
        assert self.api_mock.authenticated is True

        # Test quote price updates
        original_price = self.api_mock._crypto_quotes["BTC"]["last_trade_price"]
        self.api_mock.set_crypto_quote_price("BTC", 55000.0)

        assert self.api_mock._crypto_quotes["BTC"]["last_trade_price"] == "55000.0"
        assert self.api_mock._crypto_quotes["BTC"]["bid_price"] == "54989.0"  # 55000 * 0.9998
        assert self.api_mock._crypto_quotes["BTC"]["ask_price"] == "55110.0"  # 55000 * 1.0002

        # Test position management
        initial_positions = len(self.api_mock._crypto_positions)
        self.api_mock.add_crypto_position("ADA", "100.0", "1.50")

        assert len(self.api_mock._crypto_positions) == initial_positions + 1
        assert "ADA" in self.api_mock._crypto_positions

        # Test clearing positions
        self.api_mock.clear_crypto_positions()
        assert len(self.api_mock._crypto_positions) == 0

        # Test clearing orders
        self.api_mock._crypto_orders["test_order"] = {"id": "test_order"}
        assert len(self.api_mock._crypto_orders) == 1

        self.api_mock.clear_crypto_orders()
        assert len(self.api_mock._crypto_orders) == 0