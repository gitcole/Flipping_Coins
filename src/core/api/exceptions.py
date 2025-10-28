"""Custom API exceptions for the crypto trading bot."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import aiohttp


class APIError(Exception):
    """Base exception for all API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_info: Optional[Dict[str, Any]] = None,
    ):
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data from the API
            request_info: Information about the request that failed
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.request_info = request_info or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [self.args[0]]
        if self.status_code:
            parts.append(f"(Status: {self.status_code})")
        return " ".join(parts)


class APIConnectionError(APIError):
    """Raised when there's a connection error."""
    pass


class APITimeoutError(APIError):
    """Raised when an API request times out."""
    pass


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        """Initialize authentication error."""
        super().__init__(message, **kwargs)


class APIAuthorizationError(APIError):
    """Raised when API authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        **kwargs
    ):
        """Initialize authorization error."""
        super().__init__(message, **kwargs)


class APIInvalidRequestError(APIError):
    """Raised when the API request is invalid."""

    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize invalid request error.

        Args:
            message: Error message
            validation_errors: List of validation error messages
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []


class APINotFoundError(APIError):
    """Raised when the requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize not found error.

        Args:
            message: Error message
            resource_id: ID of the resource that wasn't found
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.resource_id = resource_id


class APIInsufficientFundsError(APIError):
    """Raised when there are insufficient funds for the operation."""

    def __init__(
        self,
        message: str = "Insufficient funds",
        required_amount: Optional[float] = None,
        available_amount: Optional[float] = None,
        **kwargs
    ):
        """Initialize insufficient funds error.

        Args:
            message: Error message
            required_amount: Required amount for the operation
            available_amount: Available amount in the account
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.required_amount = required_amount
        self.available_amount = available_amount


class APIOrderError(APIError):
    """Raised when there's an error with order operations."""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        order_status: Optional[str] = None,
        **kwargs
    ):
        """Initialize order error.

        Args:
            message: Error message
            order_id: ID of the order that caused the error
            order_status: Current status of the order
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.order_status = order_status


class APISymbolError(APIError):
    """Raised when there's an error with trading symbols."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        available_symbols: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize symbol error.

        Args:
            message: Error message
            symbol: Trading symbol that caused the error
            available_symbols: List of available symbols
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.symbol = symbol
        self.available_symbols = available_symbols or []


class APIExchangeError(APIError):
    """Raised when there's a general exchange API error."""

    def __init__(
        self,
        message: str,
        exchange_code: Optional[str] = None,
        **kwargs
    ):
        """Initialize exchange error.

        Args:
            message: Error message
            exchange_code: Exchange-specific error code
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.exchange_code = exchange_code


class APIWebSocketError(APIError):
    """Raised when there's a WebSocket connection error."""

    def __init__(
        self,
        message: str,
        connection_url: Optional[str] = None,
        **kwargs
    ):
        """Initialize WebSocket error.

        Args:
            message: Error message
            connection_url: WebSocket connection URL
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.connection_url = connection_url


class APIResponseError(APIError):
    """Raised when API response cannot be parsed or is invalid."""

    def __init__(
        self,
        message: str,
        response_text: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs
    ):
        """Initialize response error.

        Args:
            message: Error message
            response_text: Raw response text
            content_type: Response content type
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.response_text = response_text
        self.content_type = content_type


class RobinhoodAPIError(APIError):
    """Raised when there's a Robinhood-specific API error."""

    def __init__(
        self,
        message: str,
        **kwargs
    ):
        """Initialize Robinhood API error.

        Args:
            message: Error message
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)


class CryptoTradingError(APIError):
    """Raised when there's a crypto trading specific error."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        order_type: Optional[str] = None,
        **kwargs
    ):
        """Initialize crypto trading error.

        Args:
            message: Error message
            symbol: Trading symbol involved
            order_type: Type of order that caused the error
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.symbol = symbol
        self.order_type = order_type


class CryptoMarketDataError(APIError):
    """Raised when there's an error retrieving crypto market data."""

    def __init__(
        self,
        message: str,
        symbols: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize crypto market data error.

        Args:
            message: Error message
            symbols: List of symbols that caused the error
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.symbols = symbols or []


class CryptoInsufficientLiquidityError(APIError):
    """Raised when there's insufficient liquidity for a crypto trade."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        available_liquidity: Optional[float] = None,
        **kwargs
    ):
        """Initialize insufficient liquidity error.

        Args:
            message: Error message
            symbol: Trading symbol
            available_liquidity: Available liquidity amount
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.symbol = symbol
        self.available_liquidity = available_liquidity


def handle_http_error(response: aiohttp.ClientResponse, response_data: Optional[Dict[str, Any]] = None) -> APIError:
    """Handle HTTP errors and return appropriate exception.

    Args:
        response: aiohttp response object
        response_data: Parsed response data

    Returns:
        Appropriate APIError subclass

    Raises:
        APIError: The appropriate error based on status code
    """
    status_code = response.status
    response_data = response_data or {}

    # Extract error message from response
    message = response_data.get('message', response_data.get('error', f'HTTP {status_code}'))

    # Add request info
    request_info = {
        'method': response.method,
        'url': str(response.url),
        'headers': dict(response.headers),
    }

    # Handle specific status codes
    if status_code == 400:
        return APIInvalidRequestError(message, response_data=response_data, request_info=request_info)
    elif status_code == 401:
        return APIAuthenticationError(message, response_data=response_data, request_info=request_info)
    elif status_code == 403:
        return APIAuthorizationError(message, response_data=response_data, request_info=request_info)
    elif status_code == 404:
        return APINotFoundError(message, response_data=response_data, request_info=request_info)
    elif status_code == 429:
        # Extract retry-after header if available
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                retry_after = int(retry_after)
            except ValueError:
                retry_after = None

        return APIRateLimitError(
            message,
            retry_after=retry_after,
            response_data=response_data,
            request_info=request_info
        )
    elif 500 <= status_code < 600:
        return APIExchangeError(
            f"Server error: {message}",
            exchange_code=response_data.get('code'),
            status_code=status_code,
            response_data=response_data,
            request_info=request_info
        )
    else:
        return APIError(
            message,
            status_code=status_code,
            response_data=response_data,
            request_info=request_info
        )


def parse_api_error(response_data: Dict[str, Any], default_message: str = "API Error") -> APIError:
    """Parse API error from response data.

    Args:
        response_data: Response data from API
        default_message: Default error message if none found in response

    Returns:
        Appropriate APIError instance
    """
    # Extract error information
    message = (
        response_data.get('message') or
        response_data.get('error') or
        response_data.get('msg') or
        default_message
    )

    error_code = response_data.get('code')
    error_type = response_data.get('type')

    # Determine error type based on code or message content
    if error_code == 'INSUFFICIENT_FUNDS' or 'insufficient funds' in message.lower():
        return APIInsufficientFundsError(message)
    elif error_code == 'INVALID_SYMBOL' or 'symbol' in message.lower() and 'not found' in message.lower():
        return APISymbolError(message)
    elif error_code == 'INVALID_ORDER' or 'order' in message.lower() and 'invalid' in message.lower():
        return APIOrderError(message)
    elif error_type == 'authentication' or 'auth' in message.lower():
        return APIAuthenticationError(message)
    elif error_type == 'authorization' or 'permission' in message.lower():
        return APIAuthorizationError(message)
    elif error_code == 'INSUFFICIENT_LIQUIDITY' or 'insufficient liquidity' in message.lower():
        return CryptoInsufficientLiquidityError(message)
    elif 'crypto' in message.lower() or 'trading' in message.lower():
        return CryptoTradingError(message)
    elif 'market data' in message.lower() or 'quote' in message.lower():
        return CryptoMarketDataError(message)
    else:
        return APIError(message, response_data=response_data)


def is_retryable_error(error: APIError) -> bool:
    """Check if an API error is retryable.

    Args:
        error: API error instance

    Returns:
        True if the error can be retried
    """
    # Connection errors are usually retryable
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return True

    # Rate limit errors are retryable
    if isinstance(error, APIRateLimitError):
        return True

    # Server errors (5xx) are retryable
    if isinstance(error, APIExchangeError) and error.status_code and 500 <= error.status_code < 600:
        return True

    # Authentication/authorization errors are not retryable
    if isinstance(error, (APIAuthenticationError, APIAuthorizationError)):
        return False

    # Invalid requests are not retryable
    if isinstance(error, APIInvalidRequestError):
        return False

    # Not found errors are not retryable
    if isinstance(error, APINotFoundError):
        return False

    # Insufficient funds might be retryable if it's a temporary condition
    if isinstance(error, APIInsufficientFundsError):
        return True

    # Default to retryable for unknown errors
    return True


def get_retry_delay(error: APIError, attempt: int) -> float:
    """Calculate retry delay for an API error.

    Args:
        error: API error instance
        attempt: Current attempt number (1-based)

    Returns:
        Delay in seconds before retrying
    """
    base_delay = 1.0

    # Use retry-after header if available
    if isinstance(error, APIRateLimitError) and error.retry_after:
        return float(error.retry_after)

    # Exponential backoff for retryable errors
    if is_retryable_error(error):
        # Cap at 30 seconds max delay
        return min(base_delay * (2 ** (attempt - 1)), 30.0)

    return 0.0


class APIErrorHandler:
    """Handler for processing and converting various errors to API errors."""

    @staticmethod
    def handle_aiohttp_error(error: Exception, request_info: Optional[Dict[str, Any]] = None) -> APIError:
        """Handle aiohttp-specific errors.

        Args:
            error: Exception from aiohttp
            request_info: Information about the request

        Returns:
            Appropriate APIError instance
        """
        request_info = request_info or {}

        if isinstance(error, aiohttp.ClientConnectionError):
            return APIConnectionError(
                f"Connection error: {str(error)}",
                request_info=request_info
            )
        elif isinstance(error, aiohttp.ClientTimeout):
            return APITimeoutError(
                f"Request timeout: {str(error)}",
                request_info=request_info
            )
        elif isinstance(error, aiohttp.ClientError):
            return APIError(
                f"HTTP client error: {str(error)}",
                request_info=request_info
            )
        else:
            return APIError(
                f"Unexpected error: {str(error)}",
                request_info=request_info
            )

    @staticmethod
    def handle_json_decode_error(error: Exception, response_text: str, request_info: Optional[Dict[str, Any]] = None) -> APIError:
        """Handle JSON decoding errors.

        Args:
            error: JSON decode exception
            response_text: Raw response text
            request_info: Information about the request

        Returns:
            APIResponseError instance
        """
        return APIResponseError(
            f"Failed to parse JSON response: {str(error)}",
            response_text=response_text,
            content_type="application/json",
            request_info=request_info or {}
        )

    @staticmethod
    def handle_validation_error(error: Exception, field_errors: Optional[Dict[str, Any]] = None) -> APIInvalidRequestError:
        """Handle validation errors.

        Args:
            error: Validation exception
            field_errors: Field-specific validation errors

        Returns:
            APIInvalidRequestError instance
        """
        message = f"Validation error: {str(error)}"

        validation_errors = []
        if field_errors:
            for field, errors in field_errors.items():
                if isinstance(errors, list):
                    for err in errors:
                        validation_errors.append(f"{field}: {err}")
                else:
                    validation_errors.append(f"{field}: {errors}")

        return APIInvalidRequestError(
            message,
            validation_errors=validation_errors
        )


# Aliases for backward compatibility
AuthenticationError = APIAuthenticationError
RateLimitError = APIRateLimitError
NetworkError = APIConnectionError