"""
Comprehensive unit tests for MarketDataClient core trading logic.

Tests cover WebSocket message handling, market data processing,
callback execution, and data retrieval for the core trading engine.
"""
import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from core.websocket.market_data import MarketDataClient
from core.websocket.client import WebSocketClientError
from tests.utils.base_test import UnitTestCase


class TestMarketDataClient(UnitTestCase):
    """Test suite for MarketDataClient class."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.client = MarketDataClient(symbols=["BTC", "ETH"])

    @pytest.mark.asyncio
    async def test_handle_message_ticker_data(self):
        """Test ticker message processing."""
        # Setup
        ticker_message = {
            "stream": "ticker:btc",
            "symbol": "BTC",
            "price": "50000.00",
            "volume": "1000.00",
            "timestamp": "1640995200000"
        }

        # Execute
        await self.client._handle_message(json.dumps(ticker_message))

        # Verify
        ticker_data = self.client.get_ticker("BTC")
        assert ticker_data is not None
        assert ticker_data["symbol"] == "BTC"
        assert ticker_data["price"] == 50000.00

    @pytest.mark.asyncio
    async def test_handle_message_orderbook_data(self):
        """Test orderbook message processing."""
        # Setup
        orderbook_message = {
            "stream": "orderbook:btc",
            "symbol": "BTC",
            "bids": [["49990.00", "0.1"], ["49980.00", "0.2"]],
            "asks": [["50010.00", "0.1"], ["50020.00", "0.2"]],
            "timestamp": "1640995200000"
        }

        # Execute
        await self.client._handle_message(json.dumps(orderbook_message))

        # Verify
        orderbook_data = self.client.get_orderbook("BTC")
        assert orderbook_data is not None
        assert orderbook_data["symbol"] == "BTC"
        assert len(orderbook_data["bids"]) == 2
        assert len(orderbook_data["asks"]) == 2

    @pytest.mark.asyncio
    async def test_handle_message_trade_data(self):
        """Test trade message processing."""
        # Setup
        trade_message = {
            "stream": "trades:btc",
            "symbol": "BTC",
            "price": "50000.00",
            "quantity": "0.1",
            "side": "buy",
            "timestamp": "1640995200000"
        }

        # Execute
        await self.client._handle_message(json.dumps(trade_message))

        # Verify
        recent_trades = self.client.get_recent_trades("BTC")
        assert len(recent_trades) == 1
        assert recent_trades[0]["symbol"] == "BTC"
        assert recent_trades[0]["price"] == 50000.00
        assert recent_trades[0]["quantity"] == 0.1

    @pytest.mark.asyncio
    async def test_handle_message_invalid_format(self):
        """Test invalid message format handling."""
        # Setup
        invalid_message = {
            "invalid": "message",
            "format": True
        }

        # Execute (should not raise exception)
        await self.client._handle_message(json.dumps(invalid_message))

        # Verify no data was stored
        assert self.client.get_ticker("INVALID") is None

    def test_extract_channel_from_message(self):
        """Test channel extraction from messages."""
        # Test different message formats
        message1 = {"stream": "ticker:btc"}
        message2 = {"channel": "orderbook", "symbol": "eth"}
        message3 = {"topic": "trades", "symbol": "btc"}
        message4 = {"type": "market_data"}

        assert self.client._extract_channel(message1) == "ticker:btc"
        assert self.client._extract_channel(message2) == "orderbook:eth"
        assert self.client._extract_channel(message3) == "trades:btc"
        assert self.client._extract_channel(message4) == "market_data"

    @pytest.mark.asyncio
    async def test_handle_ticker_data_update(self):
        """Test ticker data update processing."""
        # Setup
        ticker_data = {
            "symbol": "BTC",
            "price": 51000.00,
            "bid": 50990.00,
            "ask": 51010.00,
            "volume": 1500.00,
            "timestamp": 1640995200000
        }

        # Execute
        await self.client._handle_ticker_data(ticker_data)

        # Verify
        stored_data = self.client.get_ticker("BTC")
        assert stored_data["price"] == 51000.00
        assert stored_data["bid"] == 50990.00
        assert stored_data["ask"] == 51010.00

    @pytest.mark.asyncio
    async def test_handle_orderbook_data_snapshot(self):
        """Test orderbook snapshot processing."""
        # Setup
        orderbook_data = {
            "symbol": "ETH",
            "bids": [["2990.00", "1.0"], ["2980.00", "2.0"]],
            "asks": [["3010.00", "1.0"], ["3020.00", "2.0"]],
            "timestamp": 1640995200000
        }

        # Execute
        await self.client._handle_orderbook_data(orderbook_data)

        # Verify
        stored_data = self.client.get_orderbook("ETH")
        assert len(stored_data["bids"]) == 2
        assert len(stored_data["asks"]) == 2
        assert stored_data["bids"][0][0] == "2990.00"

    @pytest.mark.asyncio
    async def test_handle_orderbook_data_update(self):
        """Test orderbook update processing."""
        # Setup - First add some initial data
        initial_data = {
            "symbol": "BTC",
            "bids": [["49990.00", "0.1"]],
            "asks": [["50010.00", "0.1"]],
            "timestamp": 1640995200000
        }
        await self.client._handle_orderbook_data(initial_data)

        # Update data
        update_data = {
            "symbol": "BTC",
            "bids": [["49995.00", "0.2"]],  # Updated bid
            "asks": [["50005.00", "0.2"]],  # Updated ask
            "timestamp": 1640995260000
        }

        # Execute
        await self.client._handle_orderbook_data(update_data)

        # Verify
        stored_data = self.client.get_orderbook("BTC")
        assert len(stored_data["bids"]) == 1
        assert stored_data["bids"][0][0] == "49995.00"

    @pytest.mark.asyncio
    async def test_handle_trade_data_new_trade(self):
        """Test new trade data processing."""
        # Setup
        trade_data = {
            "symbol": "BTC",
            "id": "trade_123",
            "price": 50000.00,
            "quantity": 0.1,
            "side": "buy",
            "timestamp": 1640995200000
        }

        # Execute
        await self.client._handle_trade_data(trade_data)

        # Verify
        trades = self.client.get_recent_trades("BTC")
        assert len(trades) == 1
        assert trades[0]["id"] == "trade_123"
        assert trades[0]["side"] == "buy"

    def test_get_ticker_available_symbol(self):
        """Test available ticker retrieval."""
        # Setup
        ticker_data = {
            "symbol": "BTC",
            "price": 50000.00,
            "volume": 1000,
            "timestamp": 1640995200000
        }
        self.client.ticker_data["BTC"] = ticker_data

        # Execute
        result = self.client.get_ticker("BTC")

        # Verify
        assert result is not None
        assert result["symbol"] == "BTC"
        assert result["price"] == 50000.00

    def test_get_ticker_unavailable_symbol(self):
        """Test unavailable ticker retrieval."""
        # Execute
        result = self.client.get_ticker("INVALID")

        # Verify
        assert result is None

    def test_get_orderbook_available_symbol(self):
        """Test available orderbook retrieval."""
        # Setup
        orderbook_data = {
            "symbol": "ETH",
            "bids": [["2990.00", "1.0"]],
            "asks": [["3010.00", "1.0"]],
            "timestamp": 1640995200000
        }
        self.client.orderbook_data["ETH"] = orderbook_data

        # Execute
        result = self.client.get_orderbook("ETH")

        # Verify
        assert result is not None
        assert result["symbol"] == "ETH"
        assert len(result["bids"]) == 1

    def test_get_orderbook_unavailable_symbol(self):
        """Test unavailable orderbook retrieval."""
        # Execute
        result = self.client.get_orderbook("INVALID")

        # Verify
        assert result is None

    def test_get_recent_trades_with_limit(self):
        """Test recent trades with limit."""
        # Setup - Add multiple trades
        for i in range(5):
            trade_data = {
                "symbol": "BTC",
                "id": f"trade_{i}",
                "price": 50000.00 + i,
                "quantity": 0.1,
                "side": "buy",
                "timestamp": 1640995200000 + i * 1000
            }
            self.client.trade_data["BTC"] = self.client.trade_data.get("BTC", [])
            self.client.trade_data["BTC"].append(trade_data)

        # Execute
        result = self.client.get_recent_trades("BTC", limit=3)

        # Verify
        assert len(result) == 3
        assert result[-1]["id"] == "trade_4"  # Most recent

    def test_get_recent_trades_without_limit(self):
        """Test recent trades without limit."""
        # Setup - Add trades
        for i in range(3):
            trade_data = {
                "symbol": "ETH",
                "id": f"trade_{i}",
                "price": 3000.00 + i,
                "quantity": 0.1,
                "side": "sell",
                "timestamp": 1640995200000 + i * 1000
            }
            self.client.trade_data["ETH"] = self.client.trade_data.get("ETH", [])
            self.client.trade_data["ETH"].append(trade_data)

        # Execute
        result = self.client.get_recent_trades("ETH")  # No limit specified

        # Verify
        assert len(result) == 3

    def test_add_ticker_callback_registration(self):
        """Test ticker callback registration."""
        # Setup
        def test_callback(symbol, data):
            pass

        # Execute
        self.client.add_ticker_callback(test_callback)

        # Verify
        assert test_callback in self.client.ticker_callbacks

    def test_add_orderbook_callback_registration(self):
        """Test orderbook callback registration."""
        # Setup
        def test_callback(symbol, data):
            pass

        # Execute
        self.client.add_orderbook_callback(test_callback)

        # Verify
        assert test_callback in self.client.orderbook_callbacks

    def test_add_trade_callback_registration(self):
        """Test trade callback registration."""
        # Setup
        def test_callback(symbol, data):
            pass

        # Execute
        self.client.add_trade_callback(test_callback)

        # Verify
        assert test_callback in self.client.trade_callbacks

    @pytest.mark.asyncio
    async def test_callback_execution_on_data(self):
        """Test callback execution on data receipt."""
        # Setup
        callback_results = []

        async def ticker_callback(symbol, data):
            callback_results.append(("ticker", symbol, data))

        async def orderbook_callback(symbol, data):
            callback_results.append(("orderbook", symbol, data))

        async def trade_callback(symbol, data):
            callback_results.append(("trade", symbol, data))

        self.client.add_ticker_callback(ticker_callback)
        self.client.add_orderbook_callback(orderbook_callback)
        self.client.add_trade_callback(trade_callback)

        # Execute - Send data that triggers callbacks
        ticker_data = {
            "symbol": "BTC",
            "price": 50000.00,
            "timestamp": 1640995200000
        }
        await self.client._handle_ticker_data(ticker_data)

        orderbook_data = {
            "symbol": "BTC",
            "bids": [["49990.00", "0.1"]],
            "asks": [["50010.00", "0.1"]],
            "timestamp": 1640995200000
        }
        await self.client._handle_orderbook_data(orderbook_data)

        trade_data = {
            "symbol": "BTC",
            "id": "trade_123",
            "price": 50000.00,
            "quantity": 0.1,
            "side": "buy",
            "timestamp": 1640995200000
        }
        await self.client._handle_trade_data(trade_data)

        # Verify
        assert len(callback_results) == 3
        assert ("ticker", "BTC", ticker_data) in callback_results
        assert ("orderbook", "BTC", orderbook_data) in callback_results
        assert ("trade", "BTC", trade_data) in callback_results

    @pytest.mark.asyncio
    async def test_subscription_initialization(self):
        """Test WebSocket subscription initialization."""
        # Setup
        expected_channels = [
            "ticker:btc", "orderbook:btc", "trades:btc",
            "ticker:eth", "orderbook:eth", "trades:eth"
        ]

        # Execute
        await self.client.initialize_subscriptions()

        # Verify
        assert set(self.client.subscriptions) == set(expected_channels)
        assert set(self.client.ticker_channels) == {"ticker:btc", "ticker:eth"}
        assert set(self.client.orderbook_channels) == {"orderbook:btc", "orderbook:eth"}
        assert set(self.client.trade_channels) == {"trades:btc", "trades:eth"}

    def test_market_data_summary_generation(self):
        """Test market data summary generation."""
        # Setup - Add some test data
        self.client.ticker_data = {
            "BTC": {"price": 50000.00},
            "ETH": {"price": 3000.00}
        }
        self.client.orderbook_data = {
            "BTC": {"bids": [], "asks": []}
        }
        self.client.trade_data = {
            "BTC": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "ETH": [{"id": "4"}]
        }

        # Execute
        summary = self.client.get_market_data_summary()

        # Verify
        assert summary["symbols_tracked"] == 2
        assert set(summary["tickers_available"]) == {"BTC", "ETH"}
        assert set(summary["orderbooks_available"]) == {"BTC"}
        assert summary["recent_trade_counts"]["BTC"] == 3
        assert summary["recent_trade_counts"]["ETH"] == 1
        assert summary["subscription_counts"]["tickers"] == 0  # Not initialized yet


class TestMarketDataClientErrorHandling(UnitTestCase):
    """Test error handling scenarios for MarketDataClient."""

    def setup_method(self):
        """Setup for error handling tests."""
        super().setup_method()
        self.client = MarketDataClient(symbols=["BTC"])

    @pytest.mark.asyncio
    async def test_handle_invalid_json_message(self):
        """Test handling of invalid JSON messages."""
        # Execute (should not raise exception)
        await self.client._handle_message("invalid json")

        # Verify no data was stored and no errors in logs (would be handled by logger)

    @pytest.mark.asyncio
    async def test_handle_ticker_data_missing_symbol(self):
        """Test ticker data handling with missing symbol."""
        # Setup
        ticker_data = {
            "price": 50000.00,
            "timestamp": 1640995200000
            # Missing symbol
        }

        # Execute (should not raise exception)
        await self.client._handle_ticker_data(ticker_data)

        # Verify no data was stored
        assert self.client.get_ticker("BTC") is None

    @pytest.mark.asyncio
    async def test_handle_orderbook_data_missing_symbol(self):
        """Test orderbook data handling with missing symbol."""
        # Setup
        orderbook_data = {
            "bids": [["49990.00", "0.1"]],
            "asks": [["50010.00", "0.1"]],
            "timestamp": 1640995200000
            # Missing symbol
        }

        # Execute (should not raise exception)
        await self.client._handle_orderbook_data(orderbook_data)

        # Verify no data was stored
        assert self.client.get_orderbook("BTC") is None

    @pytest.mark.asyncio
    async def test_handle_trade_data_missing_symbol(self):
        """Test trade data handling with missing symbol."""
        # Setup
        trade_data = {
            "price": 50000.00,
            "quantity": 0.1,
            "timestamp": 1640995200000
            # Missing symbol
        }

        # Execute (should not raise exception)
        await self.client._handle_trade_data(trade_data)

        # Verify no data was stored
        assert self.client.get_recent_trades("BTC") == []

    @pytest.mark.asyncio
    async def test_callback_exception_handling(self):
        """Test callback exception handling."""
        # Setup
        callback_errors = []

        async def failing_callback(symbol, data):
            callback_errors.append(f"Error in callback for {symbol}")
            raise Exception("Callback error")

        async def working_callback(symbol, data):
            callback_errors.append(f"Success for {symbol}")

        self.client.add_ticker_callback(failing_callback)
        self.client.add_ticker_callback(working_callback)

        # Execute
        ticker_data = {
            "symbol": "BTC",
            "price": 50000.00,
            "timestamp": 1640995200000
        }
        await self.client._handle_ticker_data(ticker_data)

        # Verify both callbacks were attempted
        assert len(callback_errors) == 2
        assert "Error in callback for BTC" in callback_errors
        assert "Success for BTC" in callback_errors

    @pytest.mark.asyncio
    async def test_trade_data_limit_handling(self):
        """Test trade data limit handling."""
        # Setup - Add more than 100 trades
        for i in range(105):
            trade_data = {
                "symbol": "BTC",
                "id": f"trade_{i}",
                "price": 50000.00,
                "quantity": 0.1,
                "side": "buy",
                "timestamp": 1640995200000 + i
            }
            if "BTC" not in self.client.trade_data:
                self.client.trade_data["BTC"] = []
            self.client.trade_data["BTC"].append(trade_data)

        # Execute - This should trigger the limit logic
        new_trade = {
            "symbol": "BTC",
            "id": "trade_105",
            "price": 50000.00,
            "quantity": 0.1,
            "side": "buy",
            "timestamp": 1640995200105
        }
        await self.client._handle_trade_data(new_trade)

        # Verify only last 100 trades are kept
        trades = self.client.get_recent_trades("BTC")
        assert len(trades) == 100
        # Should contain the new trade
        assert any(trade["id"] == "trade_105" for trade in trades)
        # Should not contain the first 5 trades
        assert not any(trade["id"] == "trade_0" for trade in trades)


class TestMarketDataClientDataProcessing(UnitTestCase):
    """Test data processing scenarios for MarketDataClient."""

    def setup_method(self):
        """Setup for data processing tests."""
        super().setup_method()
        self.client = MarketDataClient(symbols=["BTC", "ETH", "ADA"])

    @pytest.mark.asyncio
    async def test_multiple_symbol_data_handling(self):
        """Test handling data for multiple symbols."""
        # Setup - Send data for different symbols
        btc_ticker = {
            "symbol": "BTC",
            "price": 50000.00,
            "timestamp": 1640995200000
        }
        eth_ticker = {
            "symbol": "ETH",
            "price": 3000.00,
            "timestamp": 1640995200000
        }

        # Execute
        await self.client._handle_ticker_data(btc_ticker)
        await self.client._handle_ticker_data(eth_ticker)

        # Verify
        btc_data = self.client.get_ticker("BTC")
        eth_data = self.client.get_ticker("ETH")
        ada_data = self.client.get_ticker("ADA")  # Should be None

        assert btc_data is not None
        assert eth_data is not None
        assert ada_data is None

    @pytest.mark.asyncio
    async def test_data_normalization_different_formats(self):
        """Test data normalization from different exchange formats."""
        # Test Binance-style format
        binance_ticker = {
            "s": "BTC",  # symbol
            "c": "50000.00",  # price
            "v": "1000.00",  # volume
            "E": 1640995200000  # timestamp
        }

        # Test alternative format
        alt_ticker = {
            "symbol": "ETH",
            "price": 3000.00,
            "bestBid": 2995.00,
            "bestAsk": 3005.00,
            "timestamp": 1640995200000
        }

        # Execute
        await self.client._handle_ticker_data(binance_ticker)
        await self.client._handle_ticker_data(alt_ticker)

        # Verify normalization worked
        btc_data = self.client.get_ticker("BTC")
        eth_data = self.client.get_ticker("ETH")

        assert btc_data["symbol"] == "BTC"
        assert btc_data["price"] == 50000.00

        assert eth_data["symbol"] == "ETH"
        assert eth_data["price"] == 3000.00
        assert eth_data["bid"] == 2995.00
        assert eth_data["ask"] == 3005.00

    @pytest.mark.asyncio
    async def test_real_time_data_updates(self):
        """Test real-time data update scenarios."""
        # Setup - Initial data
        initial_data = {
            "symbol": "BTC",
            "price": 50000.00,
            "timestamp": 1640995200000
        }
        await self.client._handle_ticker_data(initial_data)

        # Update with new data
        update_data = {
            "symbol": "BTC",
            "price": 50100.00,
            "timestamp": 1640995260000
        }
        await self.client._handle_ticker_data(update_data)

        # Verify update
        current_data = self.client.get_ticker("BTC")
        assert current_data["price"] == 50100.00
        # Should preserve other fields from original format
        assert current_data["symbol"] == "BTC"