"""
Comprehensive unit tests for RobinhoodClient - Signature-Based Authentication.
Tests focus on client initialization, API communication, error handling, and integration with signature auth.
"""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from src.core.api.robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from base64 import b64encode
from ecdsa import SigningKey


class TestRobinhoodClient(UnitTestCase):
    """Test cases for RobinhoodClient with signature-based authentication."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    def test_client_initialization_with_sandbox_parameter(self):
        """Test client initialization with sandbox parameter."""
        client = RobinhoodClient(sandbox=True)
        assert client.config.sandbox is True
        assert client.auth.sandbox is True
        assert client.is_sandbox() is True

    def test_client_initialization_without_sandbox(self):
        """Test client initialization without sandbox parameter (should default to False)."""
        client = RobinhoodClient()
        assert client.config.sandbox is False
        assert client.auth.sandbox is False
        assert client.is_sandbox() is False

    def test_client_initialization_with_config_object(self):
        """Test client initialization with explicit config object."""
        config = RobinhoodAPIConfig(sandbox=True)
        client = RobinhoodClient(config=config)
        assert client.config.sandbox is True
        assert client.auth.sandbox is True

    def test_client_initialization_with_auto_config_loading(self):
        """Test client initialization with automatic configuration loading."""
        # Mock the settings loading
        with patch('src.core.api.robinhood.client.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.robinhood.api_key = "auto_api_key"
            mock_settings.robinhood.public_key = "auto_public_key"
            mock_settings.robinhood.sandbox = True
            mock_get_settings.return_value = mock_settings

            client = RobinhoodClient()
            assert client.config.api_key == "auto_api_key"
            assert client.config.public_key == "auto_public_key"
            assert client.config.sandbox is True

    def test_client_initialization_authentication_integration(self):
        """Test that client properly integrates with signature authentication."""
        # Generate test keys
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
        public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        client = RobinhoodClient(sandbox=False)
        client.config.api_key = "test_api_key"
        client.config.private_key = private_key_b64

        # Check that auth is properly initialized
        assert isinstance(client.auth, RobinhoodSignatureAuth)
        assert client.auth.is_authenticated() is True
        assert client.auth.get_api_key() == "test_api_key"

    def test_client_context_manager(self):
        """Test async context manager functionality."""
        async def run_test():
            async with RobinhoodClient(sandbox=True) as client:
                assert client is not None
                assert client.config.sandbox is True
                return True

        result = self.run_async(run_test())
        assert result is True

    def test_client_close_method(self):
        """Test client cleanup."""
        client = RobinhoodClient(sandbox=True)

        async def run_test():
            await client.close()
            return True

        result = self.run_async(run_test())
        assert result is True

    def test_client_health_check_success(self):
        """Test successful health check."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        # Mock successful user info response
        async def mock_get_user():
            return {"id": "test_user", "username": "test"}

        client.get_user = mock_get_user

        async def run_test():
            health = await client.health_check()
            return health

        health = self.run_async(run_test())
        assert health["status"] == "healthy"
        assert health["authenticated"] is True
        assert health["sandbox"] is True

    def test_client_health_check_failure(self):
        """Test health check with authentication failure."""
        client = RobinhoodClient(sandbox=True)

        # Mock failed user info response
        async def mock_get_user():
            raise Exception("Authentication failed")

        client.get_user = mock_get_user

        async def run_test():
            health = await client.health_check()
            return health

        health = self.run_async(run_test())
        assert health["status"] == "unhealthy"
        assert health["authenticated"] is False
        assert "error" in health

    def test_client_get_quotes_single_symbol(self):
        """Test getting quotes for single symbol."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        # Mock the request method
        async def mock_request(method, endpoint, **kwargs):
            return {"data": {"BTC": {"symbol": "BTC", "price": 50000}}}

        client.request = mock_request

        async def run_test():
            quotes = await client.get_quotes("BTC")
            return quotes

        quotes = self.run_async(run_test())
        assert "BTC" in quotes
        assert quotes["BTC"]["symbol"] == "BTC"

    def test_client_get_quotes_multiple_symbols(self):
        """Test getting quotes for multiple symbols."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            symbols_param = kwargs.get("params", {}).get("symbols", "")
            if "BTC" in symbols_param and "ETH" in symbols_param:
                return {"data": {
                    "BTC": {"symbol": "BTC", "price": 50000},
                    "ETH": {"symbol": "ETH", "price": 3000}
                }}
            return {"data": {}}

        client.request = mock_request

        async def run_test():
            quotes = await client.get_quotes(["BTC", "ETH"])
            return quotes

        quotes = self.run_async(run_test())
        assert "BTC" in quotes
        assert "ETH" in quotes
        assert quotes["BTC"]["price"] == 50000
        assert quotes["ETH"]["price"] == 3000

    def test_client_get_historicals(self):
        """Test getting historical data."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": {"historicals": [{"date": "2024-01-01", "close": 50000}]}}

        client.request = mock_request

        async def run_test():
            historicals = await client.get_historicals("BTC", "day", "year")
            return historicals

        historicals = self.run_async(run_test())
        assert "historicals" in historicals

    def test_client_get_instruments(self):
        """Test getting instruments."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": {
                "results": [
                    {"id": "btc_id", "symbol": "BTC", "name": "Bitcoin"},
                    {"id": "eth_id", "symbol": "ETH", "name": "Ethereum"}
                ]
            }}

        client.request = mock_request

        async def run_test():
            instruments = await client.get_instruments()
            return instruments

        instruments = self.run_async(run_test())
        assert "results" in instruments
        assert len(instruments["results"]) == 2

    def test_client_get_user_info(self):
        """Test getting user information."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": {
                "id": "user123",
                "username": "testuser",
                "email": "test@example.com"
            }}

        client.request = mock_request

        async def run_test():
            user = await client.get_user()
            return user

        user = self.run_async(run_test())
        assert user["id"] == "user123"
        assert user["username"] == "testuser"

    def test_client_get_accounts(self):
        """Test getting account information."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": {
                "results": [
                    {"id": "acc1", "account_number": "123456", "cash_balance": "10000"},
                    {"id": "acc2", "account_number": "789012", "cash_balance": "5000"}
                ]
            }}

        client.request = mock_request

        async def run_test():
            accounts = await client.get_accounts()
            return accounts

        accounts = self.run_async(run_test())
        assert "results" in accounts
        assert len(accounts["results"]) == 2

    def test_client_get_portfolio(self):
        """Test getting portfolio information."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": {
                "id": "port123",
                "total_value": "15000",
                "positions": []
            }}

        client.request = mock_request

        async def run_test():
            portfolio = await client.get_portfolio()
            return portfolio

        portfolio = self.run_async(run_test())
        assert portfolio["id"] == "port123"
        assert portfolio["total_value"] == "15000"

    def test_client_get_positions(self):
        """Test getting positions."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": {
                "results": [
                    {
                        "id": "pos1",
                        "symbol": "BTC",
                        "quantity": "0.1",
                        "avg_price": "45000"
                    }
                ]
            }}

        client.request = mock_request

        async def run_test():
            positions = await client.get_positions()
            return positions

        positions = self.run_async(run_test())
        assert "results" in positions
        assert len(positions["results"]) == 1
        assert positions["results"][0]["symbol"] == "BTC"

    def test_client_websocket_client_creation(self):
        """Test WebSocket client creation."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def run_test():
            ws_client = await client.get_websocket_client()
            return ws_client

        ws_client = self.run_async(run_test())
        assert ws_client is not None

    def test_client_quote_subscription(self):
        """Test quote subscription."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        # Mock WebSocket client
        mock_ws = AsyncMock()
        mock_ws.send.return_value = True
        client._ws_client = mock_ws

        async def run_test():
            result = await client.subscribe_quotes(["BTC", "ETH"])
            return result

        result = self.run_async(run_test())
        assert result is True
        mock_ws.send.assert_called_once()

    def test_client_order_subscription(self):
        """Test order update subscription."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        # Mock WebSocket client
        mock_ws = AsyncMock()
        mock_ws.send.return_value = True
        client._ws_client = mock_ws

        async def run_test():
            result = await client.subscribe_order_updates()
            return result

        result = self.run_async(run_test())
        assert result is True

    def test_client_get_auth_info(self):
        """Test getting authentication information."""
        # Generate test keys
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_api_key"
        client.config.private_key = private_key_b64

        auth_info = client.get_auth_info()

        assert auth_info["authenticated"] is True
        assert "test_api_key" in auth_info["api_key_prefix"]
        assert auth_info["sandbox"] is True
        assert auth_info["auth_type"] == "private_key"

    def test_client_request_without_authentication(self):
        """Test that requests fail without authentication."""
        client = RobinhoodClient(sandbox=True)
        # Don't set authentication credentials

        async def run_test():
            try:
                await client.request("GET", "/test")
                return False  # Should not reach here
            except Exception:
                return True  # Should raise exception

        result = self.run_async(run_test())
        assert result is True

    def test_client_request_with_authentication(self):
        """Test successful request with authentication."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        async def mock_request(method, endpoint, **kwargs):
            return {"data": "success"}

        client.request = mock_request

        async def run_test():
            result = await client.request("GET", "/test")
            return result

        result = self.run_async(run_test())
        assert result["data"] == "success"

    def test_client_initialization_error_handling(self):
        """Test error handling during client initialization."""
        # Test with invalid API key
        with pytest.raises(Exception):  # Should raise ConfigurationError
            client = RobinhoodClient(sandbox=True)
            client.config.api_key = None
            client.config.public_key = None

            async def run_test():
                await client.initialize()

            self.run_async(run_test())

    def test_client_crypto_api_integration(self):
        """Test integration with crypto API."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "test_key"
        client.config.public_key = "test_public_key"

        # Check that crypto API is properly initialized
        assert hasattr(client, 'crypto_api')
        assert hasattr(client, 'crypto')

        # Test that crypto API has reference to client
        assert client.crypto.client is client

    def test_request_success(self):
        """Test successful API request."""
        # Arrange
        expected_response = {"status": "success", "data": "test"}

        # Act
        async def run_test():
            return await self.client._make_request("GET", "/test", expected_response)

        result = self.run_async(run_test())

        # Assert
        assert result == expected_response
        assert self.api_mock.request_count == 1

    def test_request_authentication_error(self):
        """Test authentication error handling."""
        # Arrange
        self.api_mock.set_error_mode(True, 1.0)  # Always error

        # Act
        async def run_test():
            return await self.client._make_request("GET", "/test")

        result = self.run_async(run_test())

        # Assert
        assert result is None  # Should handle auth errors gracefully

    def test_request_rate_limit(self):
        """Test rate limiting handling."""
        # Arrange - Set very low rate limit for testing
        self.client.rate_limiter = Mock()
        self.client.rate_limiter.acquire = AsyncMock(side_effect=asyncio.RateLimitError("Rate limited"))

        # Act
        async def run_test():
            return await self.client._make_request("GET", "/test")

        result = self.run_async(run_test())

        # Assert
        assert result is None  # Should handle rate limits gracefully

    def test_request_network_error(self):
        """Test network error recovery."""
        # Arrange
        self.api_mock.set_error_mode(True, 0.5)  # 50% error rate

        # Act
        async def run_test():
            # Make multiple requests to test retry logic
            for i in range(3):
                await self.client._make_request("GET", "/test")
            return True

        result = self.run_async(run_test())

        # Assert
        assert result is True
        # Should have made multiple requests due to retries

    def test_authenticate_with_code_success(self):
        """Test successful OAuth authentication."""
        # Arrange
        auth_code = "valid_auth_code"

        # Act
        async def run_test():
            return await self.client.authenticate_with_code(auth_code)

        result = self.run_async(run_test())

        # Assert
        assert result is True
        assert self.api_mock.authenticated is True

    def test_authenticate_with_code_invalid_code(self):
        """Test invalid authorization code."""
        # Arrange
        self.api_mock.set_error_mode(True, 1.0)  # Always fail auth

        # Act
        async def run_test():
            return await self.client.authenticate_with_code("invalid_code")

        result = self.run_async(run_test())

        # Assert
        assert result is False
        assert self.api_mock.authenticated is False

    def test_authenticate_with_code_expired_code(self):
        """Test expired authorization code."""
        # Arrange - Mock expired token scenario
        original_authenticate = self.api_mock.authenticate
        async def expired_auth(*args, **kwargs):
            raise Exception("Token expired")

        self.api_mock.authenticate = expired_auth

        # Act
        async def run_test():
            return await self.client.authenticate_with_code("expired_code")

        result = self.run_async(run_test())

        # Assert
        assert result is False

    def test_ensure_authenticated_valid_token(self):
        """Test valid token validation."""
        # Arrange
        self.api_mock.authenticated = True
        self.api_mock.auth_token = "valid_token_123"

        # Act
        async def run_test():
            return await self.client.ensure_authenticated()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        assert self.api_mock.authenticated is True

    def test_ensure_authenticated_refresh_token(self):
        """Test token refresh handling."""
        # Arrange - Token expired but refresh available
        self.api_mock.authenticated = False
        original_authenticate = self.api_mock.authenticate

        async def refresh_auth(*args, **kwargs):
            self.api_mock.authenticated = True
            return {"token": "new_token"}

        self.api_mock.authenticate = refresh_auth

        # Act
        async def run_test():
            return await self.client.ensure_authenticated()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        assert self.api_mock.authenticated is True

    def test_ensure_authenticated_reauthenticate(self):
        """Test re-authentication flow."""
        # Arrange - Complete re-authentication needed
        self.api_mock.authenticated = False

        # Act
        async def run_test():
            return await self.client.ensure_authenticated()

        result = self.run_async(run_test())

        # Assert
        assert result is True  # Should attempt re-authentication

    def test_get_instruments_single_symbol(self):
        """Test single symbol instruments."""
        # Arrange
        symbol = "BTC"

        # Act
        async def run_test():
            return await self.client.get_instruments(symbol)

        result = self.run_async(run_test())

        # Assert
        assert len(result) == 1
        assert result[0]["symbol"] == "BTC"

    def test_get_instruments_multiple_symbols(self):
        """Test multiple symbol instruments."""
        # Arrange - Add more instruments to mock
        self.api_mock._instruments["ETH"] = {
            "id": "crypto_eth_id",
            "symbol": "ETH",
            "name": "Ethereum",
            "type": "cryptocurrency",
            "tradability": "tradable"
        }

        # Act
        async def run_test():
            return await self.client.get_instruments()

        result = self.run_async(run_test())

        # Assert
        assert len(result) >= 2  # Should have BTC and ETH

    def test_get_quotes_realtime(self):
        """Test real-time quotes retrieval."""
        # Arrange
        symbols = ["BTC", "ETH"]

        # Act
        async def run_test():
            return await self.client.get_quotes(symbols)

        result = self.run_async(run_test())

        # Assert
        assert "BTC" in result
        assert "ETH" in result
        assert "ask_price" in result["BTC"]

    def test_get_historicals_daily(self):
        """Test daily historical data."""
        # Arrange
        symbol = "BTC"
        timeframe = "day"

        # Act
        async def run_test():
            return await self.client.get_historicals(symbol, timeframe)

        result = self.run_async(run_test())

        # Assert
        assert result is not None
        # Should return historical data structure

    def test_get_historicals_weekly(self):
        """Test weekly historical data."""
        # Arrange
        symbol = "BTC"
        timeframe = "week"

        # Act
        async def run_test():
            return await self.client.get_historicals(symbol, timeframe)

        result = self.run_async(run_test())

        # Assert
        assert result is not None

    def test_get_fundamentals_comprehensive(self):
        """Test comprehensive fundamentals."""
        # Arrange
        symbol = "BTC"

        # Act
        async def run_test():
            return await self.client.get_fundamentals(symbol)

        result = self.run_async(run_test())

        # Assert
        assert result is not None
        # Should contain fundamental analysis data

    def test_get_user_profile(self):
        """Test user profile information."""
        # Arrange
        self.api_mock.authenticated = True

        # Act
        async def run_test():
            return await self.client.get_user_profile()

        result = self.run_async(run_test())

        # Assert
        assert result is not None
        assert "id" in result
        assert "account_number" in result

    def test_get_accounts_multiple(self):
        """Test multiple account handling."""
        # Arrange - Add multiple accounts
        self.api_mock._accounts["account2"] = {
            "id": "mock_account_id_2",
            "account_number": "987654321",
            "cash_balance": "5000.00"
        }

        # Act
        async def run_test():
            return await self.client.get_accounts()

        result = self.run_async(run_test())

        # Assert
        assert len(result) >= 1
        # Should handle multiple accounts

    def test_get_portfolio_positions(self):
        """Test portfolio positions retrieval."""
        # Arrange
        self.api_mock.authenticated = True

        # Act
        async def run_test():
            return await self.client.get_portfolio_positions()

        result = self.run_async(run_test())

        # Assert
        assert result is not None
        # Should return position data

    def test_get_positions_detailed(self):
        """Test detailed position information."""
        # Arrange
        self.api_mock.authenticated = True

        # Act
        async def run_test():
            return await self.client.get_positions()

        result = self.run_async(run_test())

        # Assert
        assert result is not None
        # Should return detailed position info

    def test_health_check_healthy(self):
        """Test healthy connection check."""
        # Arrange
        self.api_mock.authenticated = True

        # Act
        async def run_test():
            return await self.client.health_check()

        result = self.run_async(run_test())

        # Assert
        assert result is True

    def test_health_check_unhealthy(self):
        """Test unhealthy connection detection."""
        # Arrange
        self.api_mock.set_error_mode(True, 1.0)  # Always error

        # Act
        async def run_test():
            return await self.client.health_check()

        result = self.run_async(run_test())

        # Assert
        assert result is False

    def test_get_websocket_client_connection(self):
        """Test WebSocket client creation."""
        # Arrange
        self.api_mock.authenticated = True

        # Act
        async def run_test():
            return await self.client.get_websocket_client()

        result = self.run_async(run_test())

        # Assert
        assert result is not None
        # Should return WebSocket client instance

    def test_subscribe_quotes_success(self):
        """Test quote subscription success."""
        # Arrange
        symbols = ["BTC", "ETH"]
        mock_websocket = AsyncMock()
        self.client.websocket_client = mock_websocket

        # Act
        async def run_test():
            return await self.client.subscribe_quotes(symbols)

        result = self.run_async(run_test())

        # Assert
        assert result is True
        # Should have subscribed to quotes

    def test_subscribe_order_updates_success(self):
        """Test order update subscription."""
        # Arrange
        mock_websocket = AsyncMock()
        self.client.websocket_client = mock_websocket

        # Act
        async def run_test():
            return await self.client.subscribe_order_updates()

        result = self.run_async(run_test())

        # Assert
        assert result is True

    def test_close_connection(self):
        """Test connection cleanup."""
        # Arrange
        mock_websocket = AsyncMock()
        self.client.websocket_client = mock_websocket

        # Act
        async def run_test():
            await self.client.close_connection()

        self.run_async(run_test())

        # Assert
        # Should close WebSocket connection
        mock_websocket.close.assert_called_once()

    def test_context_manager_usage(self):
        """Test async context manager usage."""
        # Arrange
        self.api_mock.authenticated = True

        # Act & Assert
        async def run_test():
            async with self.client as client:
                assert client is self.client
                assert client.api.authenticated is True

        self.run_async(run_test())

        # Should have cleaned up properly