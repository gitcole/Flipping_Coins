"""Market data WebSocket client for real-time trading data."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.core.websocket.client import WebSocketClient, WebSocketClientError
from src.core.config import get_settings
from src.utils.logging import get_logger


class RobinhoodMarketDataClient:
    """Robinhood-specific market data client using REST API instead of WebSocket."""

    def __init__(self, robinhood_client=None):
        """Initialize Robinhood market data client.

        Args:
            robinhood_client: Authenticated Robinhood client instance
        """
        self.settings = get_settings()
        self.logger = get_logger("robinhood.market_data")

        self.robinhood_client = robinhood_client
        self.robinhood_crypto = None
        self.is_connected = False

        # Market data storage
        self.ticker_data: Dict[str, Dict[str, Any]] = {}
        self.positions_data: List[Dict[str, Any]] = []

        # Initialize Robinhood crypto client if client provided
        if robinhood_client:
            self._initialize_robinhood_crypto()

    def _initialize_robinhood_crypto(self):
        """Initialize Robinhood crypto client."""
        try:
            from ...api.robinhood.crypto import RobinhoodCrypto
            self.robinhood_crypto = RobinhoodCrypto(self.robinhood_client)
            self.is_connected = True
            self.logger.info("Robinhood market data client initialized")
        except ImportError as e:
            self.logger.error(f"Failed to import Robinhood crypto module: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Robinhood crypto client: {e}")

    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for a symbol using Robinhood API.

        Args:
            symbol: Trading symbol (e.g., BTC, ETH)

        Returns:
            Ticker data or None if not available
        """
        if not self.robinhood_crypto:
            self.logger.warning("Robinhood crypto client not initialized")
            return None

        try:
            # Remove /USD suffix for Robinhood API
            clean_symbol = symbol.replace("/USD", "").upper()

            # Get quote from Robinhood API
            quote = await self.robinhood_crypto.get_crypto_quote(clean_symbol)

            # Convert to expected format
            ticker_data = {
                'symbol': f"{quote.symbol}/USD",
                'price': quote.last_trade_price,
                'bid': quote.bid_price,
                'ask': quote.ask_price,
                'volume': quote.volume,
                'price_change': 0.0,  # Robinhood doesn't provide this directly
                'price_change_percent': 0.0,  # Would need historical data to calculate
                'timestamp': asyncio.get_event_loop().time() * 1000,
            }

            # Cache the data
            self.ticker_data[symbol] = ticker_data

            return ticker_data

        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            return None

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get quotes for multiple symbols in batch.

        Args:
            symbols: List of trading symbols

        Returns:
            Dictionary of ticker data by symbol
        """
        if not self.robinhood_crypto:
            self.logger.warning("Robinhood crypto client not initialized")
            return {}

        try:
            # Clean symbols for Robinhood API
            clean_symbols = [s.replace("/USD", "").upper() for s in symbols]

            # Get quotes from Robinhood API
            quotes = await self.robinhood_crypto.get_crypto_quotes(clean_symbols)

            # Convert to expected format
            ticker_data = {}
            for quote in quotes:
                original_symbol = f"{quote.symbol}/USD"
                ticker_data[original_symbol] = {
                    'symbol': original_symbol,
                    'price': quote.last_trade_price,
                    'bid': quote.bid_price,
                    'ask': quote.ask_price,
                    'volume': quote.volume,
                    'price_change': 0.0,
                    'price_change_percent': 0.0,
                    'timestamp': asyncio.get_event_loop().time() * 1000,
                }

                # Cache individual ticker data
                self.ticker_data[original_symbol] = ticker_data[original_symbol]

            return ticker_data

        except Exception as e:
            self.logger.error(f"Error getting quotes batch for {symbols}: {str(e)}")
            return {}

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current crypto positions from Robinhood.

        Returns:
            List of position data
        """
        if not self.robinhood_crypto:
            self.logger.warning("Robinhood crypto client not initialized")
            return []

        try:
            positions = await self.robinhood_crypto.get_crypto_positions()

            # Convert to expected format
            positions_data = []
            for pos in positions:
                position_data = {
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'average_buy_price': pos.average_buy_price,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'cost_basis': pos.cost_basis,
                    'unrealized_pl': pos.unrealized_pl,
                    'unrealized_pl_percent': pos.unrealized_pl_percent,
                }
                positions_data.append(position_data)

            self.positions_data = positions_data
            return positions_data

        except Exception as e:
            self.logger.error(f"Error getting positions: {str(e)}")
            return []

    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get orderbook data (not available from Robinhood REST API).

        Args:
            symbol: Trading symbol

        Returns:
            Orderbook data or None
        """
        # Robinhood doesn't provide orderbook data via REST API
        return None

    def get_recent_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades (not available from Robinhood REST API).

        Args:
            symbol: Trading symbol
            limit: Number of trades to return

        Returns:
            List of recent trades
        """
        # Robinhood doesn't provide recent trades via REST API
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Dictionary with client statistics
        """
        return {
            'is_connected': self.is_connected,
            'ticker_data_count': len(self.ticker_data),
            'positions_count': len(self.positions_data),
            'supported_symbols': len(self.settings.trading.supported_symbols) if self.settings else 0,
        }


class MarketDataClient(WebSocketClient):
    """WebSocket client specialized for real-time market data."""

    def __init__(self, symbols: Optional[List[str]] = None, **kwargs):
        """Initialize market data client.

        Args:
            symbols: List of trading symbols to subscribe to
            **kwargs: Additional arguments for WebSocketClient
        """
        super().__init__(**kwargs)

        self.settings = get_settings()
        self.logger = get_logger("websocket.market_data")

        self.symbols = symbols or self.settings.trading.supported_symbols

        # Market data storage
        self.ticker_data: Dict[str, Dict[str, Any]] = {}
        self.orderbook_data: Dict[str, Dict[str, Any]] = {}
        self.trade_data: Dict[str, List[Dict[str, Any]]] = {}

        # Data callbacks
        self.ticker_callbacks: List[callable] = []
        self.orderbook_callbacks: List[callable] = []
        self.trade_callbacks: List[callable] = []

        # Subscription channels for different data types
        self.ticker_channels: List[str] = []
        self.orderbook_channels: List[str] = []
        self.trade_channels: List[str] = []

        # Robinhood API integration
        self.robinhood_crypto = None

    async def initialize_robinhood_client(self, robinhood_client) -> None:
        """Initialize Robinhood crypto client for market data.

        Args:
            robinhood_client: Authenticated Robinhood client instance
        """
        try:
            from src.core.api.robinhood.crypto import RobinhoodCrypto
            self.robinhood_crypto = RobinhoodCrypto(robinhood_client)
            self.logger.info("Robinhood crypto client initialized for market data")
        except ImportError:
            self.logger.warning("Robinhood crypto module not available")

    async def initialize_subscriptions(self) -> None:
        """Initialize market data subscriptions."""
        # Skip WebSocket subscriptions if no URI is configured
        if not self.websocket.uri or self.websocket.uri.strip() == "":
            self.logger.info("WebSocket not configured - using polling-based market data")
            return

        self.logger.info(f"Initializing market data subscriptions for symbols: {self.symbols}")

        # Create subscription channels for each symbol
        for symbol in self.symbols:
            # Ticker channels
            ticker_channel = f"ticker:{symbol.lower()}"
            self.ticker_channels.append(ticker_channel)
            self.subscriptions.append(ticker_channel)

            # Orderbook channels
            orderbook_channel = f"orderbook:{symbol.lower()}"
            self.orderbook_channels.append(orderbook_channel)
            self.subscriptions.append(orderbook_channel)

            # Trade channels
            trade_channel = f"trades:{symbol.lower()}"
            self.trade_channels.append(trade_channel)
            self.subscriptions.append(trade_channel)

        self.logger.info(f"Created subscriptions for {len(self.subscriptions)} channels")

    def _extract_channel(self, data: Dict[str, Any]) -> str:
        """Extract channel from market data message.

        Args:
            data: Message data

        Returns:
            Channel identifier
        """
        # Handle different exchange message formats
        if 'stream' in data:
            return data['stream']
        elif 'channel' in data:
            return f"{data['channel']}:{data.get('symbol', 'unknown')}"
        elif 'topic' in data:
            return f"{data['topic']}:{data.get('symbol', 'unknown')}"
        elif 'type' in data:
            return data['type']
        else:
            return 'market_data'

    async def _handle_message(self, message: str) -> None:
        """Handle incoming market data message.

        Args:
            message: Raw message string
        """
        try:
            data = json.loads(message)

            # Handle different message types
            if 'ticker' in self._extract_channel(data):
                await self._handle_ticker_data(data)
            elif 'orderbook' in self._extract_channel(data):
                await self._handle_orderbook_data(data)
            elif 'trade' in self._extract_channel(data):
                await self._handle_trade_data(data)
            else:
                self.logger.debug(f"Unhandled message type: {data}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in market data: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error handling market data message: {str(e)}")

    async def _handle_ticker_data(self, data: Dict[str, Any]) -> None:
        """Handle ticker data update.

        Args:
            data: Ticker data
        """
        try:
            # Extract symbol and ticker info
            symbol = data.get('symbol', data.get('s', ''))
            if not symbol:
                return

            # Normalize ticker data structure
            ticker_info = {
                'symbol': symbol,
                'price': float(data.get('price', data.get('c', 0))),
                'bid': float(data.get('bid', data.get('bestBid', 0))),
                'ask': float(data.get('ask', data.get('bestAsk', 0))),
                'volume': float(data.get('volume', data.get('v', 0))),
                'timestamp': data.get('timestamp', data.get('E', asyncio.get_event_loop().time() * 1000)),
                'price_change': float(data.get('price_change', data.get('P', 0))),
                'price_change_percent': float(data.get('price_change_percent', data.get('p', 0))),
            }

            # Store ticker data
            self.ticker_data[symbol] = ticker_info

            # Notify callbacks
            for callback in self.ticker_callbacks:
                try:
                    await callback(symbol, ticker_info)
                except Exception as e:
                    self.logger.error(f"Error in ticker callback: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error handling ticker data: {str(e)}")

    async def _handle_orderbook_data(self, data: Dict[str, Any]) -> None:
        """Handle orderbook data update.

        Args:
            data: Orderbook data
        """
        try:
            symbol = data.get('symbol', data.get('s', ''))
            if not symbol:
                return

            # Normalize orderbook data structure
            orderbook_info = {
                'symbol': symbol,
                'bids': data.get('bids', data.get('b', [])),
                'asks': data.get('asks', data.get('a', [])),
                'timestamp': data.get('timestamp', data.get('E', asyncio.get_event_loop().time() * 1000)),
            }

            # Store orderbook data
            self.orderbook_data[symbol] = orderbook_info

            # Notify callbacks
            for callback in self.orderbook_callbacks:
                try:
                    await callback(symbol, orderbook_info)
                except Exception as e:
                    self.logger.error(f"Error in orderbook callback: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error handling orderbook data: {str(e)}")

    async def _handle_trade_data(self, data: Dict[str, Any]) -> None:
        """Handle trade data update.

        Args:
            data: Trade data
        """
        try:
            symbol = data.get('symbol', data.get('s', ''))
            if not symbol:
                return

            # Normalize trade data
            trade_info = {
                'symbol': symbol,
                'id': data.get('id', data.get('t', '')),
                'price': float(data.get('price', data.get('p', 0))),
                'quantity': float(data.get('quantity', data.get('q', 0))),
                'side': data.get('side', data.get('m', '')),
                'timestamp': data.get('timestamp', data.get('T', asyncio.get_event_loop().time() * 1000)),
            }

            # Store trade data (keep last 100 trades per symbol)
            if symbol not in self.trade_data:
                self.trade_data[symbol] = []
            self.trade_data[symbol].append(trade_info)

            # Keep only recent trades
            if len(self.trade_data[symbol]) > 100:
                self.trade_data[symbol] = self.trade_data[symbol][-100:]

            # Notify callbacks
            for callback in self.trade_callbacks:
                try:
                    await callback(symbol, trade_info)
                except Exception as e:
                    self.logger.error(f"Error in trade callback: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error handling trade data: {str(e)}")

    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest ticker data for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data or None if not available
        """
        return self.ticker_data.get(symbol)

    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest orderbook data for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Orderbook data or None if not available
        """
        return self.orderbook_data.get(symbol)

    def get_recent_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades for symbol.

        Args:
            symbol: Trading symbol
            limit: Number of trades to return

        Returns:
            List of recent trades
        """
        trades = self.trade_data.get(symbol, [])
        return trades[-limit:] if trades else []

    def add_ticker_callback(self, callback: callable) -> None:
        """Add ticker data callback.

        Args:
            callback: Callback function(symbol, ticker_data)
        """
        self.ticker_callbacks.append(callback)

    def add_orderbook_callback(self, callback: callable) -> None:
        """Add orderbook data callback.

        Args:
            callback: Callback function(symbol, orderbook_data)
        """
        self.orderbook_callbacks.append(callback)

    def add_trade_callback(self, callback: callable) -> None:
        """Add trade data callback.

        Args:
            callback: Callback function(symbol, trade_data)
        """
        self.trade_callbacks.append(callback)

    def get_market_data_summary(self) -> Dict[str, Any]:
        """Get summary of current market data.

        Returns:
            Market data summary
        """
        return {
            'symbols_tracked': len(self.ticker_data),
            'tickers_available': list(self.ticker_data.keys()),
            'orderbooks_available': list(self.orderbook_data.keys()),
            'recent_trade_counts': {
                symbol: len(trades) for symbol, trades in self.trade_data.items()
            },
            'subscription_counts': {
                'tickers': len(self.ticker_channels),
                'orderbooks': len(self.orderbook_channels),
                'trades': len(self.trade_channels),
            }
        }