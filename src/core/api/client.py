"""
Base HTTP client with retry logic and rate limiting for API requests.

This module provides a comprehensive HTTP client framework for interacting with cryptocurrency
exchange APIs. It includes features such as automatic retry on failures, rate limiting to
prevent API bans, and robust error handling.

Key Features:
- Asynchronous HTTP requests with aiohttp
- Configurable retry logic with exponential backoff
- Token bucket rate limiting per endpoint type
- Automatic session management and cleanup
- Detailed logging and metrics collection
- Support for both authenticated and unauthenticated requests

Classes:
    APIResponse: Wrapper for HTTP response data with timing and metadata
    BaseAPIClient: Core HTTP client with retry and rate limiting
    ExchangeAPIClient: Specialized client for exchange APIs with authentication
    APIClientFactory: Factory pattern for creating API client instances

Example:
    >>> async with BaseAPIClient(base_url="https://api.example.com") as client:
    ...     response = await client.get("/data")
    ...     print(response.status, response.data)
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import aiohttp
from aiohttp import TCPConnector

from ..config import get_settings
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.logging import get_logger, log_api_call
from .exceptions import APIError, handle_http_error
from .rate_limiter import get_api_rate_limiter


class APIResponse:
    """
    Wrapper for API response data with metadata.

    This class encapsulates the response from an HTTP request, including status code,
    response data, headers, timing information, and request URL. It provides a
    convenient interface for accessing response details and includes string
    representation for logging and debugging.

    Attributes:
        status (int): HTTP status code (e.g., 200, 404, 500)
        data (Any): Parsed response data (JSON dict, text, or raw bytes)
        headers (Dict[str, str]): Response headers as a dictionary
        request_time (float): Total time taken for the request in seconds
        url (str): The full URL that was requested

    Example:
        >>> response = APIResponse(200, {"price": 50000}, {"Content-Type": "application/json"}, 0.5, "https://api.example.com/ticker")
        >>> print(response)  # APIResponse(status=200, data={'price': 50000}, time=0.500s)
    """

    def __init__(
        self,
        status: int,
        data: Any,
        headers: Dict[str, str],
        request_time: float,
        url: str,
    ):
        """Initialize API response.

        Args:
            status: HTTP status code
            data: Response data (parsed JSON or raw text)
            headers: Response headers
            request_time: Time taken for the request in seconds
            url: Request URL
        """
        self.status = status
        self.data = data
        self.headers = headers
        self.request_time = request_time
        self.url = url

    def __str__(self) -> str:
        """String representation of the response."""
        return f"APIResponse(status={self.status}, data={self.data}, time={self.request_time:.3f}s)"


class BaseAPIClient:
    """
    Base HTTP client with retry logic, rate limiting, and error handling.

    This class provides a robust foundation for making HTTP requests to APIs. It includes
    automatic retry on failures, rate limiting to prevent API bans, and comprehensive
    error handling. The client uses aiohttp for asynchronous requests and supports
    connection pooling, custom headers, and various rate limiting strategies.

    Key Features:
    - Asynchronous HTTP requests with retry logic and exponential backoff
    - Token bucket rate limiting per endpoint type (global, trading, market data, etc.)
    - Automatic session management and cleanup
    - Configurable timeouts, retries, and user agents
    - Detailed logging of API calls and performance metrics
    - Support for custom headers and proxy settings

    Attributes:
        base_url (str): Base URL for all API requests
        timeout (int): Request timeout in seconds
        retries (int): Number of retry attempts for failed requests
        rate_limit_type (str): Type of rate limiting (e.g., "global", "trading")
        headers (Dict[str, str]): Default headers sent with every request
        session (aiohttp.ClientSession): Shared HTTP session for requests
        rate_limiter (Optional[RateLimiter]): Rate limiter instance for request throttling

    Example:
        >>> async with BaseAPIClient(base_url="https://api.example.com") as client:
        ...     response = await client.get("/data")
        ...     print(f"Status: {response.status}, Data: {response.data}")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        rate_limit_type: str = "global",
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """
        Initialize the API client with configuration and session setup.

        Args:
            base_url: Base URL for API requests. Falls back to settings if None.
            timeout: Request timeout in seconds. Falls back to settings if None.
            retries: Number of retry attempts. Falls back to settings if None.
            rate_limit_type: Type of rate limiting to use (e.g., "global", "trading").
            user_agent: User agent string. Falls back to settings if None.
            headers: Additional headers to send with requests. Merged with defaults.
            session: Shared aiohttp session. If None, a new session is created.

        Raises:
            ValueError: If base_url is not provided and not in settings.
        """
        self.settings = get_settings()
        self.logger = get_logger("api.client")

        # Use provided values or fall back to settings
        self.base_url = base_url or self.settings.api.base_url
        self.timeout = timeout or self.settings.api.timeout
        self.retries = retries or self.settings.api.retries
        self.rate_limit_type = rate_limit_type
        self.user_agent = user_agent or self.settings.api.user_agent

        # Default headers
        self.headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # Add custom headers
        if headers:
            self.headers.update(headers)

        # Session management: Create a new session if none provided
        self._owned_session = session is None
        if session is None:
            # Configure TCP connector for connection pooling and performance
            connector = TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=10,  # Max connections per host
                enable_cleanup_closed=True,  # Clean up closed connections
                keepalive_timeout=30,  # Keep-alive timeout
                ttl_dns_cache=300,  # DNS cache TTL
            )

            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.headers.copy(),
                connector=connector,
                trust_env=True,  # Use system proxy settings if available
            )
        else:
            self.session = session

        # Rate limiting: Initialized lazily to avoid overhead
        self.rate_limiter = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP session and connector."""
        if self._owned_session and not self.session.closed:
            await self.session.close()
            # Close the connector if it exists
            if hasattr(self.session, 'connector') and self.session.connector:
                await self.session.connector.close()

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint.

        Args:
            endpoint: API endpoint (can be absolute or relative)

        Returns:
            Full URL
        """
        if endpoint.startswith('http://') or endpoint.startswith('https://'):
            return endpoint
        return urljoin(self.base_url, endpoint)

    def _get_rate_limit_tokens(self, method: str, endpoint: str) -> int:
        """Determine number of tokens to consume for rate limiting.

        Args:
            method: HTTP method
            endpoint: API endpoint

        Returns:
            Number of tokens to consume
        """
        # Different endpoints may consume different numbers of tokens
        if 'orders' in endpoint.lower():
            return 2  # Order operations are more expensive
        elif any(word in endpoint.lower() for word in ['balance', 'account', 'position']):
            return 3  # Account operations are most expensive
        else:
            return 1  # Standard operations

    async def _rate_limit_request(self, method: str, endpoint: str) -> float:
        """Apply rate limiting to request.

        Args:
            method: HTTP method
            endpoint: API endpoint

        Returns:
            Time waited for rate limiting
        """
        if not self.rate_limiter:
            self.rate_limiter = await get_api_rate_limiter()

        tokens = self._get_rate_limit_tokens(method, endpoint)
        wait_time = 0.0

        if self.rate_limit_type == "global":
            wait_time = await self.rate_limiter.wait_for_global(tokens)
        elif self.rate_limit_type == "trading":
            wait_time = await self.rate_limiter.wait_for_trading(tokens)
        elif self.rate_limit_type == "market_data":
            wait_time = await self.rate_limiter.wait_for_market_data(tokens)
        elif self.rate_limit_type == "orders":
            wait_time = await self.rate_limiter.wait_for_orders(tokens)
        elif self.rate_limit_type == "account":
            wait_time = await self.rate_limiter.wait_for_account(tokens)

        return wait_time

    async def _retry_request(
        self,
        method: str,
        url: str,
        retry_count: int = 0,
        **kwargs
    ) -> APIResponse:
        """
        Make HTTP request with retry logic and comprehensive error handling.

        This method implements the core request logic with automatic retries on failures,
        rate limiting enforcement, and detailed logging. It handles various error scenarios
        including network issues, API rate limits, and malformed responses.

        Args:
            method: HTTP method (e.g., 'GET', 'POST')
            url: Full request URL
            retry_count: Current retry attempt number (starts at 0)
            **kwargs: Additional arguments passed to aiohttp.request()

        Returns:
            APIResponse: Parsed response object with status, data, headers, and timing

        Raises:
            APIError: If all retry attempts are exhausted or non-retryable error occurs
        """
        start_time = time.time()

        try:
            # Step 1: Apply rate limiting before making the request
            # This ensures we don't exceed API rate limits and wait if necessary
            rate_limit_wait = await self._rate_limit_request(method, url)
            if rate_limit_wait > 0:
                self.logger.debug(f"Rate limited for {rate_limit_wait:.3f}s before {method} {url}")

            # Step 2: Execute the HTTP request using aiohttp
            async with self.session.request(method, url, **kwargs) as response:
                request_time = time.time() - start_time

                # Step 3: Log the API call for monitoring and debugging
                # Includes method, URL, status, response time, and rate limit wait time
                log_api_call(
                    self.logger,
                    method,
                    url,
                    response.status,
                    request_time * 1000,  # Convert to milliseconds
                    rate_limit_wait_ms=rate_limit_wait * 1000
                )

                # Step 4: Handle rate limiting response (HTTP 429)
                if response.status == 429:  # Rate limited by server
                    # Extract Retry-After header if provided
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except ValueError:
                            retry_after = None

                    # Create specific rate limit error
                    from .exceptions import APIRateLimitError
                    error = APIRateLimitError(
                        f"Rate limit exceeded for {method} {url}",
                        retry_after=retry_after,
                        status_code=429,
                        request_info={'method': method, 'url': url}
                    )

                    # Check if we should retry based on retry count
                    if retry_count < self.retries:
                        # Calculate exponential backoff delay
                        from .exceptions import get_retry_delay
                        delay = get_retry_delay(error, retry_count + 1)
                        self.logger.warning(
                            f"Rate limited, retrying in {delay:.2f}s (attempt {retry_count + 1}/{self.retries})"
                        )
                        await asyncio.sleep(delay)
                        # Recursive retry with incremented count
                        return await self._retry_request(method, url, retry_count + 1, **kwargs)

                    # If no more retries, raise the error
                    raise error

                # Step 5: Parse response body (JSON or text)
                try:
                    if response.content_type == 'application/json':
                        data = await response.json()
                    else:
                        data = await response.text()
                except Exception as e:
                    # Handle parsing errors by creating a response error
                    from .exceptions import APIResponseError
                    raise APIResponseError(
                        f"Failed to parse response: {str(e)}",
                        response_text=await response.text(),
                        content_type=response.content_type,
                        request_info={'method': method, 'url': url}
                    )

                # Step 6: Handle other HTTP error status codes (4xx, 5xx)
                if response.status >= 400:
                    error = handle_http_error(response, data)
                    raise error

                # Step 7: Success - return parsed APIResponse object
                return APIResponse(
                    status=response.status,
                    data=data,
                    headers=dict(response.headers),
                    request_time=request_time,
                    url=url,
                )

        except aiohttp.ClientError as e:
            # Step 8: Handle client-side errors (network, timeout, etc.)
            from .exceptions import APIErrorHandler
            error = APIErrorHandler.handle_aiohttp_error(e, {'method': method, 'url': url})

            # Check if error is retryable and we have retries left
            if retry_count < self.retries:
                from .exceptions import is_retryable_error, get_retry_delay
                if is_retryable_error(error):
                    delay = get_retry_delay(error, retry_count + 1)
                    self.logger.warning(
                        f"Request failed, retrying in {delay:.2f}s: {str(error)} (attempt {retry_count + 1}/{self.retries})"
                    )
                    await asyncio.sleep(delay)
                    # Recursive retry for client errors
                    return await self._retry_request(method, url, retry_count + 1, **kwargs)

            # If not retryable or no retries left, raise the error
            raise error

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """Make HTTP request to API endpoint.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Request body data
            headers: Additional headers
            **kwargs: Additional arguments for aiohttp request

        Returns:
            API response

        Raises:
            APIError: If request fails
        """
        url = self._build_url(endpoint)

        # Merge headers
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)

        # Prepare request arguments
        request_kwargs = {
            'params': params,
            'headers': request_headers,
            **kwargs
        }

        # Handle request data
        if data is not None:
            if isinstance(data, dict):
                request_kwargs['json'] = data
            else:
                request_kwargs['data'] = data

        return await self._retry_request(method, url, **request_kwargs)

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            API response
        """
        return await self.request('GET', endpoint, params=params, headers=headers, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """Make POST request.

        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            API response
        """
        return await self.request('POST', endpoint, params=params, data=data, headers=headers, **kwargs)

    async def put(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """Make PUT request.

        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            API response
        """
        return await self.request('PUT', endpoint, params=params, data=data, headers=headers, **kwargs)

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """Make DELETE request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            API response
        """
        return await self.request('DELETE', endpoint, params=params, headers=headers, **kwargs)

    async def patch(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> APIResponse:
        """Make PATCH request.

        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            API response
        """
        return await self.request('PATCH', endpoint, params=params, data=data, headers=headers, **kwargs)


class ExchangeAPIClient(BaseAPIClient):
    """
    Base client for cryptocurrency exchange APIs with authentication and signing.

    This class extends BaseAPIClient to provide exchange-specific functionality,
    including API key authentication, request signing, and common exchange operations
    like getting server time, account info, and placing orders. Subclasses should
    override the _sign_request method to implement exchange-specific signature algorithms.

    Key Features:
    - Automatic API key authentication via headers
    - Request signing for secure authenticated endpoints
    - Sandbox environment support
    - Common exchange operations (time, info, symbols, trading)

    Attributes:
        api_key (Optional[str]): Exchange API key for authentication
        secret_key (Optional[str]): Exchange secret key for request signing
        sandbox (bool): Whether to use sandbox/test environment

    Example:
        >>> client = ExchangeAPIClient(
        ...     api_key="your_api_key",
        ...     secret_key="your_secret_key",
        ...     sandbox=True
        ... )
        >>> async with client:
        ...     time_response = await client.get_server_time()
        ...     print(f"Server time: {time_response.data}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        sandbox: bool = False,
        **kwargs
    ):
        """
        Initialize the exchange API client with authentication credentials.

        Args:
            api_key: Exchange API key. Falls back to settings if None.
            secret_key: Exchange secret key for signing requests. Falls back to settings if None.
            sandbox: Use sandbox environment for testing. Falls back to settings if False.
            **kwargs: Additional arguments passed to BaseAPIClient (e.g., base_url, timeout).

        Raises:
            ValueError: If required credentials are missing and not in settings.
        """
        super().__init__(**kwargs)

        # Load credentials from parameters or settings
        self.api_key = api_key or self.settings.exchange.api_key
        self.secret_key = secret_key or self.settings.exchange.secret_key
        self.sandbox = sandbox or self.settings.exchange.sandbox

        # Add authentication headers if API key is available
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key

        # Override base URL for sandbox environment if configured
        if self.sandbox and hasattr(self.settings, 'sandbox_base_url'):
            self.base_url = self.settings.sandbox_base_url

    def _sign_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Sign request with API credentials.

        This is a base implementation. Subclasses should override this
        method to implement exchange-specific signing.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data

        Returns:
            Dictionary of signature headers
        """
        return {}

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        signed: bool = False,
        **kwargs
    ) -> APIResponse:
        """Make authenticated request to exchange API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            signed: Whether to sign the request
            **kwargs: Additional arguments

        Returns:
            API response
        """
        # Add signature if required
        if signed and self.secret_key:
            signature_headers = self._sign_request(method, endpoint, data)
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers'].update(signature_headers)

        return await super().request(method, endpoint, params=params, data=data, **kwargs)

    async def get_server_time(self) -> APIResponse:
        """Get server time from exchange.

        Returns:
            API response with server time
        """
        return await self.get('/time')

    async def get_exchange_info(self) -> APIResponse:
        """Get exchange information.

        Returns:
            API response with exchange info
        """
        return await self.get('/exchangeInfo')

    async def get_symbols(self) -> APIResponse:
        """Get available trading symbols.

        Returns:
            API response with symbol information
        """
        return await self.get('/symbols')

    async def get_ticker(self, symbol: str) -> APIResponse:
        """Get ticker information for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            API response with ticker data
        """
        return await self.get(f'/ticker/price', params={'symbol': symbol})

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> APIResponse:
        """Get kline/candlestick data.

        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 1h, etc.)
            limit: Number of klines to retrieve
            start_time: Start time in milliseconds
            end_time: End time in milliseconds

        Returns:
            API response with kline data
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit,
        }

        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        return await self.get('/klines', params=params)

    async def get_order_book(self, symbol: str, limit: int = 100) -> APIResponse:
        """Get order book for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of entries to retrieve

        Returns:
            API response with order book data
        """
        return await self.get('/depth', params={'symbol': symbol, 'limit': limit})

    async def get_account_info(self) -> APIResponse:
        """Get account information.

        Returns:
            API response with account data
        """
        return await self.request('GET', '/account', signed=True)

    async def get_balances(self) -> APIResponse:
        """Get account balances.

        Returns:
            API response with balance data
        """
        return await self.request('GET', '/balances', signed=True)

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = 'GTC',
        **kwargs
    ) -> APIResponse:
        """Place a trading order.

        Args:
            symbol: Trading symbol
            side: Order side (BUY or SELL)
            order_type: Order type (MARKET, LIMIT, etc.)
            quantity: Order quantity
            price: Order price (required for limit orders)
            time_in_force: Time in force policy
            **kwargs: Additional order parameters

        Returns:
            API response with order data
        """
        order_data = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'timeInForce': time_in_force,
            **kwargs
        }

        if price is not None:
            order_data['price'] = price

        return await self.request('POST', '/order', data=order_data, signed=True)

    async def cancel_order(self, symbol: str, order_id: str) -> APIResponse:
        """Cancel an order.

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            API response with cancellation result
        """
        return await self.request(
            'DELETE',
            '/order',
            data={'symbol': symbol, 'orderId': order_id},
            signed=True
        )

    async def get_order_status(self, symbol: str, order_id: str) -> APIResponse:
        """Get order status.

        Args:
            symbol: Trading symbol
            order_id: Order ID

        Returns:
            API response with order status
        """
        return await self.request(
            'GET',
            '/order',
            params={'symbol': symbol, 'orderId': order_id},
            signed=True
        )

    async def get_open_orders(self, symbol: Optional[str] = None) -> APIResponse:
        """Get open orders.

        Args:
            symbol: Trading symbol (optional, returns all if not provided)

        Returns:
            API response with open orders
        """
        params = {}
        if symbol:
            params['symbol'] = symbol

        return await self.request('GET', '/openOrders', params=params, signed=True)


class APIClientFactory:
    """
    Factory for creating and managing API client instances.

    This class implements the Factory pattern to register and create API client
    instances dynamically. It allows registering client classes by name and
    instantiating them with custom parameters, promoting modularity and
    extensibility for different exchange APIs.

    Attributes:
        _clients (Dict[str, type]): Registry of client names to client classes

    Example:
        >>> # Register a custom client
        >>> APIClientFactory.register_client("binance", BinanceClient)
        >>>
        >>> # Create an instance
        >>> client = APIClientFactory.create_client("binance", api_key="key", sandbox=True)
        >>>
        >>> # List all registered clients
        >>> clients = APIClientFactory.list_clients()
        >>> print(clients.keys())  # dict_keys(['binance'])
    """

    _clients: Dict[str, type] = {}

    @classmethod
    def register_client(cls, name: str, client_class: type) -> None:
        """
        Register an API client class for later instantiation.

        Args:
            name: Unique name to register the client under
            client_class: The API client class (must inherit from BaseAPIClient)

        Raises:
            TypeError: If client_class is not a subclass of BaseAPIClient
        """
        if not issubclass(client_class, BaseAPIClient):
            raise TypeError(f"Client class must inherit from BaseAPIClient, got {client_class}")
        cls._clients[name] = client_class

    @classmethod
    def create_client(cls, name: str, **kwargs) -> BaseAPIClient:
        """
        Create an instance of a registered API client.

        Args:
            name: Name of the registered client
            **kwargs: Arguments to pass to the client constructor

        Returns:
            BaseAPIClient: Instance of the requested client class

        Raises:
            ValueError: If the client name is not registered
            TypeError: If instantiation fails due to invalid arguments
        """
        if name not in cls._clients:
            raise ValueError(f"Unknown API client: {name}. Available clients: {list(cls._clients.keys())}")

        try:
            return cls._clients[name](**kwargs)
        except Exception as e:
            raise TypeError(f"Failed to create client '{name}': {str(e)}") from e

    @classmethod
    def list_clients(cls) -> Dict[str, type]:
        """
        List all currently registered API client classes.

        Returns:
            Dict[str, type]: Dictionary mapping client names to client classes
        """
        return cls._clients.copy()