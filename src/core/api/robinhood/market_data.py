"""
Robinhood Market Data

Handles market data operations including quotes, historical data,
and market information for all instruments on Robinhood.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

from pydantic import BaseModel, Field, validator

from ..exceptions import RobinhoodAPIError
from ....utils.logging import get_logger

logger = get_logger(__name__)


class Quote(BaseModel):
    """Market quote model."""

    symbol: str = Field(..., description="Instrument symbol")
    ask_price: float = Field(..., description="Ask price")
    ask_size: int = Field(..., description="Ask size")
    bid_price: float = Field(..., description="Bid price")
    bid_size: int = Field(..., description="Bid size")
    last_trade_price: float = Field(..., description="Last trade price")
    last_extended_hours_trade_price: Optional[float] = Field(None, description="Last extended hours price")
    previous_close: float = Field(..., description="Previous close price")
    adjusted_previous_close: float = Field(..., description="Adjusted previous close")
    previous_close_date: str = Field(..., description="Previous close date")
    symbol_name: str = Field(..., description="Symbol name")
    trading_halted: bool = Field(default=False, description="Trading halted flag")
    has_traded: bool = Field(default=True, description="Has traded flag")
    updated_at: str = Field(..., description="Last update timestamp")


class HistoricalQuote(BaseModel):
    """Historical quote data point."""

    symbol: str = Field(..., description="Instrument symbol")
    timestamp: str = Field(..., description="Quote timestamp")
    open_price: float = Field(..., description="Open price")
    close_price: float = Field(..., description="Close price")
    high_price: float = Field(..., description="High price")
    low_price: float = Field(..., description="Low price")
    volume: int = Field(..., description="Volume")
    session: str = Field(..., description="Trading session")
    interpolated: bool = Field(default=False, description="Interpolated data flag")


class MarketHours(BaseModel):
    """Market hours information."""

    date: str = Field(..., description="Date")
    is_open: bool = Field(..., description="Is market open")
    opens_at: Optional[str] = Field(None, description="Market open time")
    closes_at: Optional[str] = Field(None, description="Market close time")
    extended_opens_at: Optional[str] = Field(None, description="Extended hours open")
    extended_closes_at: Optional[str] = Field(None, description="Extended hours close")
    previous_open_days: List[str] = Field(default_factory=list, description="Previous open days")
    next_open_days: List[str] = Field(default_factory=list, description="Next open days")


class MarketData:
    """Market data information."""

    instruments: List[str] = Field(default_factory=list, description="Available instruments")
    quotes: List[Quote] = Field(default_factory=list, description="Market quotes")
    historical_quotes: List[HistoricalQuote] = Field(default_factory=list, description="Historical quotes")
    market_hours: Optional[MarketHours] = Field(None, description="Market hours")


class RobinhoodMarketData:
    """
    Comprehensive market data operations for Robinhood trading platform.

    This class provides a complete interface for retrieving market data from Robinhood,
    including real-time quotes, historical data, market hours, and various financial
    metrics. It supports stocks, options, ETFs, and other instruments available on
    the platform.

    Key Features:
    - Real-time quotes for stocks, options, crypto, and other instruments
    - Historical price data with customizable intervals and spans
    - Market hours and trading session information
    - Option chains and derivatives data
    - Corporate earnings and dividend information
    - News, analyst ratings, and company profiles
    - ETF holdings and fund performance data
    - Market movers and popular instruments
    - Comprehensive batch data retrieval

    Data Models:
    - Quote: Real-time price and volume information
    - HistoricalQuote: Historical price data points
    - MarketHours: Trading session schedules
    - MarketData: Aggregated market information

    Attributes:
        client (RobinhoodClient): The authenticated Robinhood API client instance
        logger (structlog.BoundLogger): Logger for market data operations

    Example:
        >>> market_data = RobinhoodMarketData(client)
        >>> quote = await market_data.get_quote("AAPL")
        >>> print(f"AAPL: ${quote.last_trade_price}")
        >>>
        >>> historicals = await market_data.get_historicals("AAPL", span="year")
        >>> print(f"52-week high: ${max(h.close_price for h in historicals)}")
        >>>
        >>> batch_data = await market_data.get_market_data_batch(["AAPL", "GOOGL", "MSFT"])
        >>> print(f"Market open: {batch_data.market_hours.is_open}")
    """

    def __init__(self, client: RobinhoodClient):
        """Initialize market data module.

        Args:
            client: Robinhood API client instance
        """
        self.client = client
        self.logger = get_logger("robinhood.market_data")

        # Performance optimization: Cache for frequently requested quotes
        self._quote_cache = {}
        self._cache_expiry = 10  # seconds

    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached quote is still valid."""
        if symbol not in self._quote_cache:
            return False
        cache_time, _ = self._quote_cache[symbol]
        return (time.time() - cache_time) < self._cache_expiry

    def _get_cached_quote(self, symbol: str) -> Optional[Quote]:
        """Get cached quote if valid."""
        if self._is_cache_valid(symbol):
            _, quote = self._quote_cache[symbol]
            self.logger.debug(f"Returning cached quote for {symbol}")
            return quote
        return None

    def _cache_quote(self, symbol: str, quote: Quote):
        """Cache a quote with timestamp."""
        self._quote_cache[symbol] = (time.time(), quote)
        # Limit cache size to prevent memory growth
        if len(self._quote_cache) > 100:
            oldest_symbol = min(self._quote_cache.keys(),
                               key=lambda s: self._quote_cache[s][0])
            del self._quote_cache[oldest_symbol]
            self.logger.debug(f"Removed oldest cache entry for {oldest_symbol}")

    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for an instrument with caching.

        Args:
            symbol: Instrument symbol

        Returns:
            Current quote information
        """
        try:
            # Check cache first
            cached_quote = self._get_cached_quote(symbol)
            if cached_quote:
                return cached_quote

            # Fetch from API
            response = await self.client.get(f"/marketdata/quotes/{symbol}/")
            quote_data = response.data

            quote = Quote(
                symbol=quote_data.get("symbol", symbol),
                ask_price=float(quote_data.get("ask_price", 0)),
                ask_size=int(quote_data.get("ask_size", 0)),
                bid_price=float(quote_data.get("bid_price", 0)),
                bid_size=int(quote_data.get("bid_size", 0)),
                last_trade_price=float(quote_data.get("last_trade_price", 0)),
                last_extended_hours_trade_price=quote_data.get("last_extended_hours_trade_price"),
                previous_close=float(quote_data.get("previous_close", 0)),
                adjusted_previous_close=float(quote_data.get("adjusted_previous_close", 0)),
                previous_close_date=quote_data.get("previous_close_date", ""),
                symbol_name=quote_data.get("name", ""),
                trading_halted=quote_data.get("trading_halted", False),
                has_traded=quote_data.get("has_traded", True),
                updated_at=quote_data.get("updated_at", ""),
            )

            # Cache the quote
            self._cache_quote(symbol, quote)
            return quote

        except Exception as e:
            self.logger.error("Failed to get quote", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get quote for {symbol}: {e}")

    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get quotes for multiple instruments.

        Args:
            symbols: List of instrument symbols

        Returns:
            List of quote information
        """
        quotes = []

        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except Exception as e:
                self.logger.warning("Failed to get quote for symbol", symbol=symbol, error=str(e))

        return quotes

    async def get_historicals(
        self,
        symbol: str,
        interval: str = "day",
        span: str = "year",
        bounds: str = "regular"
    ) -> List[HistoricalQuote]:
        """Get historical data for an instrument.

        Args:
            symbol: Instrument symbol
            interval: Time interval (5minute, 10minute, hour, day, week, month)
            span: Time span (day, week, month, 3month, year, 5year, all)
            bounds: Price bounds (regular, extended, trading)

        Returns:
            Historical data points
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "span": span,
            "bounds": bounds,
        }

        try:
            response = await self.client.get("/marketdata/historicals/", params=params)
            historicals_data = response.data.get("historicals", [])
            historicals = []

            for hist_data in historicals_data:
                historicals.append(HistoricalQuote(
                    symbol=hist_data.get("symbol", symbol),
                    timestamp=hist_data.get("begins_at", ""),
                    open_price=float(hist_data.get("open_price", 0)),
                    close_price=float(hist_data.get("close_price", 0)),
                    high_price=float(hist_data.get("high_price", 0)),
                    low_price=float(hist_data.get("low_price", 0)),
                    volume=int(hist_data.get("volume", 0)),
                    session=hist_data.get("session", ""),
                    interpolated=hist_data.get("interpolated", False),
                ))

            return historicals
        except Exception as e:
            self.logger.error("Failed to get historicals",
                           symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get historicals for {symbol}: {e}")

    async def get_option_chains(self, symbol: str, expiration_dates: Optional[List[str]] = None) -> Dict:
        """Get option chains for a symbol.

        Args:
            symbol: Underlying symbol
            expiration_dates: Optional list of expiration dates

        Returns:
            Option chains data
        """
        params = {}
        if expiration_dates:
            params["expiration_dates"] = ",".join(expiration_dates)

        try:
            response = await self.client.get(f"/marketdata/options/chains/{symbol}/", params=params)
            return response.data
        except Exception as e:
            self.logger.error("Failed to get option chains", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get option chains for {symbol}: {e}")

    async def get_market_hours(
        self,
        date: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> MarketHours:
        """Get market hours for a specific date.

        Args:
            date: Date in YYYY-MM-DD format (default: today)
            symbol: Optional symbol for specific market hours

        Returns:
            Market hours information
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        endpoint = f"/marketdata/hours/{date}/"
        if symbol:
            endpoint = f"/marketdata/instruments/{symbol}/hours/{date}/"

        try:
            response = await self.client.get(endpoint)
            hours_data = response.data

            return MarketHours(
                date=hours_data.get("date", date),
                is_open=hours_data.get("is_open", False),
                opens_at=hours_data.get("opens_at"),
                closes_at=hours_data.get("closes_at"),
                extended_opens_at=hours_data.get("extended_opens_at"),
                extended_closes_at=hours_data.get("extended_closes_at"),
                previous_open_days=hours_data.get("previous_open_days", []),
                next_open_days=hours_data.get("next_open_days", []),
            )
        except Exception as e:
            self.logger.error("Failed to get market hours", date=date, symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get market hours: {e}")

    async def get_splits(self, symbol: str) -> Dict:
        """Get stock splits for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Splits data
        """
        try:
            response = await self.client.get(f"/instruments/{symbol}/splits/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get splits", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get splits for {symbol}: {e}")

    async def get_dividends(self, symbol: str) -> Dict:
        """Get dividends for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dividends data
        """
        try:
            response = await self.client.get(f"/instruments/{symbol}/dividends/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get dividends", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get dividends for {symbol}: {e}")

    async def get_earnings(self, symbol: str) -> Dict:
        """Get earnings data for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Earnings data
        """
        try:
            response = await self.client.get(f"/marketdata/earnings/{symbol}/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get earnings", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get earnings for {symbol}: {e}")

    async def get_news(self, symbol: Optional[str] = None, limit: int = 10) -> Dict:
        """Get news articles.

        Args:
            symbol: Optional symbol filter
            limit: Number of articles to retrieve

        Returns:
            News data
        """
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol

        try:
            response = await self.client.get("/midlands/news/", params=params)
            return response.data
        except Exception as e:
            self.logger.error("Failed to get news", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get news: {e}")

    async def get_popular_stocks(self) -> List[Dict]:
        """Get popular stocks on Robinhood.

        Returns:
            List of popular stocks
        """
        try:
            response = await self.client.get("/midlands/tags/tag/popular-stocks/")
            return response.data.get("instruments", [])
        except Exception as e:
            self.logger.error("Failed to get popular stocks", error=str(e))
            raise RobinhoodAPIError(f"Failed to get popular stocks: {e}")

    async def get_top_movers(self, direction: str = "up") -> List[Dict]:
        """Get top moving stocks.

        Args:
            direction: Direction of movement (up or down)

        Returns:
            List of top movers
        """
        try:
            response = await self.client.get(f"/midlands/movers/{direction}/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get top movers", direction=direction, error=str(e))
            raise RobinhoodAPIError(f"Failed to get top movers: {e}")

    async def get_etf_holdings(self, symbol: str) -> Dict:
        """Get ETF holdings for a symbol.

        Args:
            symbol: ETF symbol

        Returns:
            ETF holdings data
        """
        try:
            response = await self.client.get(f"/etps/{symbol}/holdings/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get ETF holdings", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get ETF holdings for {symbol}: {e}")

    async def get_analyst_ratings(self, symbol: str) -> Dict:
        """Get analyst ratings for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Analyst ratings data
        """
        try:
            response = await self.client.get(f"/instruments/{symbol}/ratings/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get analyst ratings", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get analyst ratings for {symbol}: {e}")

    async def get_company_profile(self, symbol: str) -> Dict:
        """Get company profile information.

        Args:
            symbol: Stock symbol

        Returns:
            Company profile data
        """
        try:
            response = await self.client.get(f"/instruments/{symbol}/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get company profile", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get company profile for {symbol}: {e}")

    async def get_key_statistics(self, symbol: str) -> Dict:
        """Get key statistics for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Key statistics data
        """
        try:
            response = await self.client.get(f"/instruments/{symbol}/stats/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get key statistics", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get key statistics for {symbol}: {e}")

    async def search_instruments(self, query: str) -> List[Dict]:
        """Search for instruments.

        Args:
            query: Search query

        Returns:
            List of matching instruments
        """
        try:
            response = await self.client.get("/instruments/", params={"query": query})
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to search instruments", query=query, error=str(e))
            raise RobinhoodAPIError(f"Failed to search instruments: {e}")

    async def get_market_data_batch(self, symbols: List[str]) -> MarketData:
        """Get comprehensive market data for multiple symbols.

        Args:
            symbols: List of symbols to get data for

        Returns:
            Comprehensive market data
        """
        market_data = MarketData()

        try:
            # Get quotes for all symbols
            market_data.quotes = await self.get_quotes(symbols)
            market_data.instruments = symbols

            # Get market hours for today
            market_data.market_hours = await self.get_market_hours()

            # Get historical data for each symbol (last 30 days)
            for symbol in symbols:
                try:
                    historicals = await self.get_historicals(symbol, span="month")
                    market_data.historical_quotes.extend(historicals)
                except Exception as e:
                    self.logger.warning("Failed to get historicals for symbol",
                                      symbol=symbol, error=str(e))

            return market_data

        except Exception as e:
            self.logger.error("Failed to get market data batch", symbols=symbols, error=str(e))
            raise RobinhoodAPIError(f"Failed to get market data batch: {e}")

    async def get_real_time_price(self, symbol: str) -> float:
        """Get real-time price for a symbol.

        Args:
            symbol: Instrument symbol

        Returns:
            Current price
        """
        quote = await self.get_quote(symbol)
        return quote.last_trade_price

    async def get_price_change(self, symbol: str, days: int = 1) -> Dict:
        """Get price change information for a symbol.

        Args:
            symbol: Instrument symbol
            days: Number of days to look back

        Returns:
            Price change information
        """
        try:
            # Get current quote and historical data
            quote = await self.get_quote(symbol)
            historicals = await self.get_historicals(symbol, span=f"{days}day", interval="day")

            if historicals:
                old_price = historicals[0].close_price
                current_price = quote.last_trade_price
                change = current_price - old_price
                change_percent = (change / old_price) * 100 if old_price > 0 else 0

                return {
                    "symbol": symbol,
                    "current_price": current_price,
                    "old_price": old_price,
                    "change": change,
                    "change_percent": change_percent,
                    "days": days,
                }
            else:
                return {
                    "symbol": symbol,
                    "current_price": quote.last_trade_price,
                    "error": "No historical data available",
                }
        except Exception as e:
            self.logger.error("Failed to get price change", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get price change for {symbol}: {e}")

    async def is_market_open(self, symbol: Optional[str] = None) -> bool:
        """Check if market is currently open.

        Args:
            symbol: Optional symbol for specific market

        Returns:
            True if market is open
        """
        try:
            market_hours = await self.get_market_hours(symbol=symbol)
            return market_hours.is_open
        except Exception:
            return False

    async def get_next_market_open(self) -> Optional[datetime]:
        """Get next market open time.

        Returns:
            Next market open datetime or None if always open
        """
        try:
            market_hours = await self.get_market_hours()
            if market_hours.opens_at:
                return datetime.fromisoformat(market_hours.opens_at.replace('Z', '+00:00'))
            return None
        except Exception:
            return None

    async def get_next_market_close(self) -> Optional[datetime]:
        """Get next market close time.

        Returns:
            Next market close datetime or None if always open
        """
        try:
            market_hours = await self.get_market_hours()
            if market_hours.closes_at:
                return datetime.fromisoformat(market_hours.closes_at.replace('Z', '+00:00'))
            return None
        except Exception:
            return None

    async def get_trading_days(
        self,
        start_date: str,
        end_date: str,
        symbol: Optional[str] = None
    ) -> List[str]:
        """Get trading days between two dates.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            symbol: Optional symbol for specific market

        Returns:
            List of trading days
        """
        try:
            market_hours = await self.get_market_hours(symbol=symbol)
            return market_hours.previous_open_days + market_hours.next_open_days
        except Exception as e:
            self.logger.error("Failed to get trading days",
                            start_date=start_date, end_date=end_date, error=str(e))
            raise RobinhoodAPIError(f"Failed to get trading days: {e}")