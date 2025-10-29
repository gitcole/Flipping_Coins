"""
Robinhood Crypto API Client

Updated implementation using OAuth2 authentication and async/await pattern.
Provides comprehensive access to Robinhood's Crypto Trading API with rate limiting,
enhanced error handling, and proper asset code management.
"""

import asyncio
import json
import time
import uuid
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import aiohttp
from aiohttp import TCPConnector
from pydantic import BaseModel, Field
from ecdsa import SigningKey
from base64 import b64decode, b64encode

from ...config import get_settings
from ..exceptions import (
    APIConnectionError,
    APIRateLimitError,
    RobinhoodAPIError,
    CryptoTradingError,
    CryptoMarketDataError,
    CryptoInsufficientLiquidityError,
    handle_http_error,
)
from ..rate_limiter import get_api_rate_limiter
from ....utils.logging import get_logger

logger = get_logger(__name__)


class CryptoOrderRequest(BaseModel):
    """Crypto order request model."""

    side: str = Field(..., description="Order side (buy/sell)")
    order_type: str = Field(..., description="Order type (market/limit/stop)")
    symbol: str = Field(..., description="Trading symbol (e.g., BTC, ETH)")
    quantity: Union[str, float, Decimal] = Field(..., description="Order quantity")
    time_in_force: str = Field(default="gtc", description="Time in force")
    price: Optional[Union[str, float, Decimal]] = Field(None, description="Limit price")
    stop_price: Optional[Union[str, float, Decimal]] = Field(None, description="Stop price")


class CryptoOrderResponse(BaseModel):
    """Crypto order response model."""

    id: str
    client_order_id: str
    side: str
    order_type: str
    symbol: str
    quantity: str
    status: str
    created_at: str
    updated_at: str


class CryptoAccount(BaseModel):
    """Crypto account information."""

    id: str
    account_number: str
    status: str
    buying_power: str
    cash_balance: str
    currency: str


class CryptoPosition(BaseModel):
    """Crypto position information."""

    asset_code: str
    quantity: str
    average_cost: str
    current_price: str
    market_value: str
    unrealized_pnl: str
    unrealized_pnl_percent: str


class CryptoQuote(BaseModel):
    """Crypto market quote."""

    symbol: str
    bid_price: str
    ask_price: str
    last_trade_price: str
    volume_24h: str
    high_24h: str
    low_24h: str


class RobinhoodCryptoAPI:
    """
    Async Robinhood Crypto API client using OAuth2 authentication with optimized performance.

    Features:
    - OAuth2 authentication with automatic token management
    - Connection pooling and keep-alive for improved performance
    - Automatic rate limiting (300 req/min authenticated, 100 req/min market data)
    - Comprehensive error handling with crypto-specific exceptions
    - Request compression (gzip, deflate) for reduced bandwidth
    - Retry logic with exponential backoff for resilient connections
    - Proper asset code vs symbol handling
    - Full async/await support with production-ready optimizations

    Performance Optimizations:
    - TCP connection pooling (limit: 100 total, 10 per host)
    - DNS caching (300s TTL) to reduce lookup times
    - Keep-alive connections (30s timeout) to reuse connections
    - Request compression to minimize data transfer
    - Exponential backoff for retries (up to 30s max delay)

    Error Handling:
    - CryptoTradingError for trading-related issues
    - CryptoMarketDataError for market data retrieval failures
    - CryptoInsufficientLiquidityError for liquidity issues
    - Automatic retry on transient errors with smart backoff
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        base_url: str = "https://trading.robinhood.com",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """Initialize the crypto API client with optimized settings.

        Args:
            access_token: API key (optional, will use settings if not provided)
            base_url: API base URL (default: https://trading.robinhood.com)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)

        The client automatically configures:
        - Connection pooling for improved performance
        - Request compression and keep-alive settings
        - Comprehensive error handling and retry logic
        """
        logger.info("🔍 DEBUG: Initializing RobinhoodCryptoAPI")
        self.api_key = access_token or get_settings().robinhood.api_key
        self.private_key_b64 = get_settings().robinhood.private_key
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

        # Session and rate limiting
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = None
        self._client_order_ids: set = set()  # Track used client_order_ids

        # Request stats
        self._request_count = 0
        self._error_count = 0
        self._last_request_time = 0

        logger.info(f"🔍 DEBUG: API key set: {self.api_key is not None}")
        logger.info(f"🔍 DEBUG: Private key B64 set: {self.private_key_b64 is not None}")

        # Enhanced logging for credential validation
        if self.api_key:
            logger.info(f"🔍 DEBUG: API key format valid: {self.api_key.startswith('rh-')}")
            logger.info(f"🔍 DEBUG: API key length: {len(self.api_key)}")
        if self.private_key_b64:
            logger.info(f"🔍 DEBUG: Private key B64 length: {len(self.private_key_b64)}")
            logger.info(f"🔍 DEBUG: Private key B64 format appears valid: {len(self.private_key_b64) > 50}")

        # Store public key if available
        self.public_key_b64 = get_settings().robinhood.public_key

        # Decode private key with enhanced error handling
        try:
            if self.private_key_b64:
                self.private_key = SigningKey(b64decode(self.private_key_b64))
                logger.info("🔍 DEBUG: Private key decoded successfully")
                logger.info("🔍 DEBUG: Private key type: %s", type(self.private_key))
            else:
                self.private_key = None
        except Exception as e:
            self.private_key = None
            logger.error("🔍 DEBUG: Failed to decode private key: %s", str(e))
            logger.error("🔍 DEBUG: Private key B64 starts with: %s...", self.private_key_b64[:30] if self.private_key_b64 else "None")

        # Enhanced validation warnings
        if not self.api_key:
            logger.warning("🔍 DEBUG: No API key provided for Robinhood Crypto API")
        if not self.private_key_b64:
            logger.warning("🔍 DEBUG: No private key provided for Robinhood Crypto API")
        if not self.private_key:
            logger.warning("🔍 DEBUG: Private key could not be decoded - signature authentication will fail")

        # Check environment mode
        sandbox_mode = getattr(get_settings().robinhood, 'sandbox', False)
        logger.info(f"🔍 DEBUG: Sandbox mode: {sandbox_mode}")

        # Authentication method detection
        has_signature_auth = self.api_key and self.private_key_b64 and self.private_key

        logger.info("🔍 DEBUG: === SIGNATURE AUTHENTICATION CHECK ===")
        logger.info(f"🔍 DEBUG: Signature auth available: {has_signature_auth}")

        if not has_signature_auth:
            logger.error("🔍 DEBUG: NO VALID SIGNATURE AUTHENTICATION FOUND!")
            logger.error("🔍 DEBUG: This indicates missing or invalid credentials")
            logger.error("🔍 DEBUG: Please configure RH_API_KEY and RH_BASE64_PRIVATE_KEY in your .env file")
        else:
            logger.info("🔍 DEBUG: Signature authentication is properly configured")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize the API client with optimized connection pooling and settings."""
        if self._session is None:
            # Configure TCP connector for connection pooling
            connector = TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=10,  # Max connections per host
                enable_cleanup_closed=True,  # Clean up closed connections
                keepalive_timeout=30,  # Keep-alive timeout
                ttl_dns_cache=300,  # DNS cache TTL
            )

            self._session = aiohttp.ClientSession(
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",  # Enable compression
                    "Content-Type": "application/json",
                    "User-Agent": "crypto-trading-bot/1.0.0",
                    "Connection": "keep-alive",  # Keep connections alive
                },
                timeout=self.timeout,
                connector=connector,
                trust_env=True,  # Use system proxy settings if available
            )

        # Initialize rate limiter
        self._rate_limiter = await get_api_rate_limiter()

        logger.info("Robinhood Crypto API client initialized with connection pooling")

    async def close(self) -> None:
        """Close the API client and cleanup resources."""
        if self._session:
            await self._session.close()
            # Close the connector if it exists
            if hasattr(self._session, 'connector') and self._session.connector:
                await self._session.connector.close()
            self._session = None
        logger.info("Robinhood Crypto API client closed")

    def _generate_client_order_id(self) -> str:
        """Generate a unique client order ID for idempotency."""
        while True:
            client_order_id = str(uuid.uuid4())
            if client_order_id not in self._client_order_ids:
                self._client_order_ids.add(client_order_id)
                # Keep only last 1000 IDs to prevent memory growth
                if len(self._client_order_ids) > 1000:
                    oldest_id = next(iter(self._client_order_ids))
                    self._client_order_ids.remove(oldest_id)
                return client_order_id

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        rate_limit_type: str = "trading",
        retry_on_rate_limit: bool = True
    ) -> Dict[str, Any]:
        """Make an authenticated API request with optimized performance, rate limiting, and retries.

        This method includes:
        - Rate limiting based on request type (trading, market_data, orders, account)
        - Exponential backoff for retries on transient errors
        - Connection pooling and keep-alive for efficient networking
        - Compression handling for reduced bandwidth usage

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            data: Request body data (will be JSON-encoded)
            params: Query parameters
            rate_limit_type: Type of rate limiting ("trading", "market_data", "orders", "account")
            retry_on_rate_limit: Whether to retry on rate limit errors (default: True)

        Returns:
            Response data as dictionary

        Raises:
            CryptoTradingError: If request fails due to trading issues
            CryptoMarketDataError: If request fails due to market data issues
            APIRateLimitError: If rate limit is exceeded and retries exhausted
            APIConnectionError: If connection fails after all retries
        """
        if not self._session:
            await self.initialize()

        url = f"{self.base_url}{endpoint}"
        request_id = str(uuid.uuid4())[:8]

        # Rate limiting
        wait_time = 0
        if self._rate_limiter:
            wait_time = await self._rate_limiter.wait_for_custom(rate_limit_type, 1)

        # Update stats
        self._request_count += 1
        self._last_request_time = time.time()

        logger.info(
            "🔍 DEBUG: Making API request - ID: %s, Method: %s, URL: %s, Endpoint: %s, Base URL: %s, Wait: %s, Count: %s",
            request_id, method, url, endpoint, self.base_url, wait_time, self._request_count
        )

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Prepare body for signing - use compact JSON format
                body = json.dumps(data, separators=(',', ':')) if data else ""

                # Check if we have valid signature authentication credentials
                has_private_key = self.api_key and self.private_key_b64 and self.private_key
                has_public_key = self.api_key and self.public_key_b64 is not None

                # Check authentication method availability
                if not has_private_key and not has_public_key:
                    logger.error("🔍 DEBUG: No valid authentication credentials found")
                    logger.error("🔍 DEBUG: Private key available: %s", has_private_key)
                    logger.error("🔍 DEBUG: Public key available: %s", has_public_key)
                    logger.error("🔍 DEBUG: Please configure authentication credentials in .env file")
                    logger.error("🔍 DEBUG: Required: RH_API_KEY and RH_BASE64_PRIVATE_KEY")
                    logger.error("🔍 DEBUG: Or public key: ROBINHOOD_API_KEY and ROBINHOOD_PUBLIC_KEY")
                    raise RobinhoodAPIError("No authentication credentials configured")

                # Choose authentication method
                logger.info(f"🔍 DEBUG: Authentication method selection - Private: {has_private_key}, Public: {has_public_key}")

                if has_private_key:
                    logger.info("🔍 DEBUG: Using private key authentication")
                    auth_method = "private_key"
                elif has_public_key:
                    logger.info("🔍 DEBUG: Using public key authentication")
                    auth_method = "public_key"
                else:
                    logger.error(f"🔍 DEBUG: No valid auth method - Private: {has_private_key}, Public: {has_public_key}")
                    raise RobinhoodAPIError("No valid authentication method available")

                # Initialize headers with base headers
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }

                # Generate signature for private key method
                if auth_method == "private_key":
                    timestamp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
                    # Updated signature format: api_key + timestamp + path + method + body (JSON)
                    message = f"{self.api_key}{timestamp}{endpoint}{method}{body}"

                    # Enhanced signature logging
                    logger.info(f"🔍 DEBUG: === SIGNATURE GENERATION ===")
                    logger.info(f"🔍 DEBUG: Timestamp: {timestamp}")
                    logger.info(f"🔍 DEBUG: Endpoint: {endpoint}")
                    logger.info(f"🔍 DEBUG: Method: {method}")
                    logger.info(f"🔍 DEBUG: Body length: {len(body)}")
                    logger.info(f"🔍 DEBUG: API key length: {len(self.api_key)}")
                    logger.info(f"🔍 DEBUG: Message length: {len(message)}")
                    logger.info(f"🔍 DEBUG: Message preview: {message[:100]}...")
                    logger.info(f"🔍 DEBUG: Body preview: {body[:100] if body else 'empty'}")

                    logger.info(f"🔍 DEBUG: Private key available for signing: {type(self.private_key)}")

                    try:
                        signature = self.private_key.sign(message.encode('utf-8'))
                        signature_b64 = b64encode(signature.signature).decode('utf-8')
                        logger.info(f"🔍 DEBUG: Signature generated successfully")
                        logger.info(f"🔍 DEBUG: Signature length: {len(signature_b64)}")
                        logger.info(f"🔍 DEBUG: Signature preview: {signature_b64[:50]}...")
                    except Exception as e:
                        logger.error(f"🔍 DEBUG: Failed to generate signature: {e}")
                        logger.error(f"🔍 DEBUG: Message encoding issue: {message.encode('utf-8')}")
                        raise RobinhoodAPIError(f"Signature generation failed: {e}")

                    # Set headers based on authentication method
                    if auth_method == "private_key":
                        headers.update({
                            "x-api-key": self.api_key,
                            "x-signature": signature_b64,
                            "x-timestamp": str(timestamp),
                        })
                    elif auth_method == "public_key":
                        headers.update({
                            "x-api-key": self.api_key,
                        })
        
                        # Enhanced header logging for debugging
                logger.info(f"🔍 DEBUG: === REQUEST HEADERS ===")
                if auth_method == "private_key":
                    logger.info(f"🔍 DEBUG: x-api-key: {self.api_key[:20]}...")
                    logger.info(f"🔍 DEBUG: x-signature: {signature_b64[:50]}...")
                    logger.info(f"🔍 DEBUG: x-timestamp: {timestamp}")
                elif auth_method == "public_key":
                    logger.info(f"🔍 DEBUG: x-api-key: {self.api_key[:20]}...")
                    logger.info(f"🔍 DEBUG: Public key authentication (no signature required)")
                logger.info(f"🔍 DEBUG: Full URL: {url}")
                logger.info(f"🔍 DEBUG: Method: {method}")
                logger.info(f"🔍 DEBUG: Request ID: {request_id}")
                
                async with self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers
                ) as response:
                    response_data = None

                    # Try to parse JSON response
                    try:
                        response_data = await response.json()
                    except (aiohttp.ContentTypeError, json.JSONDecodeError):
                        response_data = {"error": await response.text()}

                    # Handle HTTP errors
                    if response.status >= 400:
                        # Enhanced error logging for authentication issues
                        logger.error(f"🔍 DEBUG: === HTTP ERROR RESPONSE ===")
                        logger.error(f"🔍 DEBUG: Status code: {response.status}")
                        logger.error(f"🔍 DEBUG: Response headers: {dict(response.headers)}")
                        logger.error(f"🔍 DEBUG: Response data: {response_data}")
                        logger.error(f"🔍 DEBUG: Request ID: {request_id}")
                        logger.error(f"🔍 DEBUG: Attempt: {attempt + 1}")

                        # Check for common authentication errors
                        if response.status == 401:
                            logger.error("🔍 DEBUG: 401 Unauthorized - Authentication failed")
                            logger.error("🔍 DEBUG: This indicates signature verification or credential issues")
                        elif response.status == 403:
                            logger.error("🔍 DEBUG: 403 Forbidden - Access denied")
                            logger.error("🔍 DEBUG: This may indicate account or permission issues")

                        error = handle_http_error(response, response_data)
                        if isinstance(error, APIRateLimitError) and retry_on_rate_limit and attempt < self.max_retries:
                            # Wait for rate limit reset and retry
                            retry_delay = getattr(error, 'retry_after', 60) or 60
                            logger.warning(
                                "Rate limited, retrying after delay - ID: %s, Attempt: %s, Delay: %s",
                                request_id, attempt + 1, retry_delay
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            self._error_count += 1
                            raise error

                    logger.debug(
                        "API request successful - ID: %s, Status: %s, Response size: %s",
                        request_id, response.status, len(str(response_data))
                    )

                    return response_data

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    retry_delay = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                    logger.warning(
                        "Request failed, retrying",
                        request_id=request_id,
                        attempt=attempt + 1,
                        error=str(e),
                        retry_delay=retry_delay
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self._error_count += 1
                    raise APIConnectionError(f"Request failed after {self.max_retries} retries: {str(e)}")

        # This should never be reached, but just in case
        if last_error:
            raise APIConnectionError(f"Request failed: {str(last_error)}")
        else:
            raise RobinhoodAPIError("Request failed with unknown error")

    # Trading Account Methods

    async def get_account(self) -> CryptoAccount:
        """Get crypto trading account information.

        Returns:
            Account information

        Raises:
            RobinhoodAPIError: If account retrieval fails
        """
        logger.info("🔍 DEBUG: Retrieving crypto account using endpoint /api/v1/crypto/trading/accounts/")
        try:
            data = await self._make_request("GET", "/api/v1/crypto/trading/accounts/")
            if not data or "results" not in data or not data["results"]:
                logger.error("🔍 DEBUG: No crypto account found in response", response_data=data)
                raise RobinhoodAPIError("No crypto account found")

            account_data = data["results"][0]
            logger.info("🔍 DEBUG: Crypto account retrieved successfully", account_id=account_data.get("id"))
            return CryptoAccount(**account_data)

        except Exception as e:
            logger.error("Failed to get crypto account: %s", str(e))
            raise RobinhoodAPIError(f"Failed to get crypto account: {e}")

    async def get_positions(self, asset_codes: Optional[List[str]] = None) -> List[CryptoPosition]:
        """Get crypto positions.

        Args:
            asset_codes: Optional list of asset codes to filter by

        Returns:
            List of crypto positions

        Raises:
            RobinhoodAPIError: If position retrieval fails
        """
        try:
            params = {}
            if asset_codes:
                params["asset_code"] = ",".join(asset_codes)

            data = await self._make_request("GET", "/api/v1/crypto/trading/holdings/", params=params)

            positions = []
            for position_data in data.get("results", []):
                positions.append(CryptoPosition(**position_data))

            return positions

        except Exception as e:
            logger.error("Failed to get crypto positions: %s", str(e))
            raise RobinhoodAPIError(f"Failed to get crypto positions: {e}")

    # Market Data Methods

    async def get_quotes(self, symbols: List[str]) -> List[CryptoQuote]:
        """Get quotes for multiple cryptocurrencies.

        Args:
            symbols: List of trading symbols

        Returns:
            List of crypto quotes

        Raises:
            RobinhoodAPIError: If quote retrieval fails
        """
        try:
            params = {"symbol": ",".join(symbols)}
            data = await self._make_request(
                "GET",
                "/api/v1/crypto/marketdata/best_bid_ask/",
                params=params,
                rate_limit_type="market_data"
            )

            quotes = []
            for quote_data in data.get("results", []):
                quotes.append(CryptoQuote(**quote_data))

            return quotes

        except Exception as e:
            logger.error("Failed to get crypto quotes for symbols %s: %s", symbols, str(e))
            raise CryptoMarketDataError(f"Failed to get crypto quotes: {e}", symbols=symbols)

    async def get_quote(self, symbol: str) -> CryptoQuote:
        """Get quote for a single cryptocurrency.

        Args:
            symbol: Trading symbol

        Returns:
            Crypto quote

        Raises:
            RobinhoodAPIError: If quote retrieval fails
        """
        quotes = await self.get_quotes([symbol])
        if not quotes:
            raise CryptoMarketDataError(f"No quote found for symbol: {symbol}", symbols=[symbol])
        return quotes[0]

    async def get_estimated_price(self, symbol: str, side: str, quantity: str) -> Dict[str, Any]:
        """Get estimated price for a trade.

        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity

        Returns:
            Estimated price information

        Raises:
            RobinhoodAPIError: If estimation fails
        """
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity)
            }

            return await self._make_request(
                "GET",
                "/api/v1/crypto/marketdata/estimated_price/",
                params=params,
                rate_limit_type="market_data"
            )

        except Exception as e:
            logger.error(
                "Failed to get estimated price for symbol %s, side %s, quantity %s: %s",
                symbol, side, quantity, str(e)
            )
            raise RobinhoodAPIError(f"Failed to get estimated price: {e}")

    # Trading Methods

    async def place_order(self, order: CryptoOrderRequest) -> CryptoOrderResponse:
        """Place a crypto trading order.

        Args:
            order: Order request details

        Returns:
            Order response

        Raises:
            RobinhoodAPIError: If order placement fails
        """
        try:
            # Validate order
            if order.order_type in ["limit", "stop_limit"] and not order.price:
                raise RobinhoodAPIError("Price is required for limit orders")

            if order.order_type in ["stop", "stop_limit"] and not order.stop_price:
                raise RobinhoodAPIError("Stop price is required for stop orders")

            # Prepare order data
            order_data = {
                "client_order_id": self._generate_client_order_id(),
                "side": order.side.lower(),
                "type": order.order_type.lower(),
                "symbol": order.symbol.upper(),
                "quantity": str(order.quantity),
                "time_in_force": order.time_in_force.lower(),
            }

            if order.price:
                order_data["price"] = str(order.price)
            if order.stop_price:
                order_data["stop_price"] = str(order.stop_price)

            data = await self._make_request(
                "POST",
                "/api/v1/crypto/trading/orders/",
                data=order_data,
                rate_limit_type="orders"
            )

            logger.info(
                "Placed crypto order",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                client_order_id=order_data["client_order_id"]
            )

            return CryptoOrderResponse(**data)

        except Exception as e:
            logger.error(
                "Failed to place crypto order",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                error=str(e)
            )
            raise CryptoTradingError(f"Failed to place order: {e}", symbol=order.symbol, order_type=order.order_type)

    async def get_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get crypto orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of orders

        Raises:
            RobinhoodAPIError: If order retrieval fails
        """
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()

            data = await self._make_request("GET", "/api/v1/crypto/trading/orders/", params=params)
            return data.get("results", [])

        except Exception as e:
            logger.error("Failed to get crypto orders for symbol %s: %s", symbol, str(e))
            raise RobinhoodAPIError(f"Failed to get crypto orders: {e}")

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get specific order details.

        Args:
            order_id: Order ID

        Returns:
            Order details

        Raises:
            RobinhoodAPIError: If order retrieval fails
        """
        try:
            return await self._make_request("GET", f"/api/v1/crypto/trading/orders/{order_id}/")

        except Exception as e:
            logger.error("Failed to get crypto order %s: %s", order_id, str(e))
            raise RobinhoodAPIError(f"Failed to get order {order_id}: {e}")

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a crypto order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation result

        Raises:
            RobinhoodAPIError: If cancellation fails
        """
        try:
            data = await self._make_request(
                "POST",
                f"/api/v1/crypto/trading/orders/{order_id}/cancel/",
                rate_limit_type="orders"
            )

            logger.info("Cancelled crypto order", order_id=order_id)
            return data

        except Exception as e:
            logger.error("Failed to cancel crypto order %s: %s", order_id, str(e))
            raise RobinhoodAPIError(f"Failed to cancel order {order_id}: {e}")

    # Convenience Methods

    async def place_market_buy_order(
        self,
        symbol: str,
        quantity: Union[str, float, Decimal]
    ) -> CryptoOrderResponse:
        """Place a market buy order.

        Args:
            symbol: Trading symbol
            quantity: Order quantity

        Returns:
            Order response
        """
        order = CryptoOrderRequest(
            side="buy",
            order_type="market",
            symbol=symbol,
            quantity=quantity
        )
        return await self.place_order(order)

    async def place_market_sell_order(
        self,
        symbol: str,
        quantity: Union[str, float, Decimal]
    ) -> CryptoOrderResponse:
        """Place a market sell order.

        Args:
            symbol: Trading symbol
            quantity: Order quantity

        Returns:
            Order response
        """
        order = CryptoOrderRequest(
            side="sell",
            order_type="market",
            symbol=symbol,
            quantity=quantity
        )
        return await self.place_order(order)

    async def place_limit_buy_order(
        self,
        symbol: str,
        quantity: Union[str, float, Decimal],
        price: Union[str, float, Decimal]
    ) -> CryptoOrderResponse:
        """Place a limit buy order.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price

        Returns:
            Order response
        """
        order = CryptoOrderRequest(
            side="buy",
            order_type="limit",
            symbol=symbol,
            quantity=quantity,
            price=price
        )
        return await self.place_order(order)

    async def place_limit_sell_order(
        self,
        symbol: str,
        quantity: Union[str, float, Decimal],
        price: Union[str, float, Decimal]
    ) -> CryptoOrderResponse:
        """Place a limit sell order.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price

        Returns:
            Order response
        """
        order = CryptoOrderRequest(
            side="sell",
            order_type="limit",
            symbol=symbol,
            quantity=quantity,
            price=price
        )
        return await self.place_order(order)

    # Utility Methods

    def get_stats(self) -> Dict[str, Any]:
        """Get API client statistics.

        Returns:
            Client statistics
        """
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
            "last_request_time": self._last_request_time,
            "client_order_ids_tracked": len(self._client_order_ids),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the API connection.

        Returns:
            Health check results
        """
        try:
            # Try to get account info as a health check
            await self.get_account()
            return {
                "status": "healthy",
                "authenticated": True,
                "timestamp": time.time(),
                "stats": self.get_stats(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "authenticated": False,
                "error": str(e),
                "timestamp": time.time(),
                "stats": self.get_stats(),
            }