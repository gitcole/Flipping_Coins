"""Token bucket rate limiter for API requests."""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional, Tuple

from ..config import get_settings


class TokenBucket:
    """Token bucket rate limiter implementation."""

    def __init__(
        self,
        rate_per_second: float,
        capacity: int,
        initial_tokens: Optional[int] = None
    ):
        """Initialize token bucket.

        Args:
            rate_per_second: Rate of token replenishment per second
            capacity: Maximum number of tokens the bucket can hold
            initial_tokens: Initial number of tokens (defaults to capacity)
        """
        self.rate_per_second = rate_per_second
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if bucket is empty
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate_per_second
            )
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_tokens(self, tokens: int = 1) -> float:
        """Wait until enough tokens are available.

        Args:
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        start_time = time.time()

        while True:
            if await self.acquire(tokens):
                return time.time() - start_time

            # Calculate wait time for next token
            async with self._lock:
                now = time.time()
                elapsed = now - self.last_update

                # Add tokens based on elapsed time
                current_tokens = min(
                    self.capacity,
                    self.tokens + elapsed * self.rate_per_second
                )

                if current_tokens >= tokens:
                    # Should have acquired tokens
                    continue

                # Calculate time needed for required tokens
                tokens_needed = tokens - current_tokens
                wait_time = tokens_needed / self.rate_per_second

                # Update state for next iteration
                self.tokens = current_tokens
                self.last_update = now

            # Wait for the calculated time
            await asyncio.sleep(wait_time)

    def get_tokens(self) -> float:
        """Get current number of tokens (non-blocking).

        Returns:
            Current token count
        """
        now = time.time()
        elapsed = now - self.last_update
        return min(self.capacity, self.tokens + elapsed * self.rate_per_second)

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get estimated wait time for tokens without acquiring them.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        current_tokens = self.get_tokens()

        if current_tokens >= tokens:
            return 0.0

        tokens_needed = tokens - current_tokens
        return tokens_needed / self.rate_per_second


class RateLimiter:
    """Multi-bucket rate limiter for different API endpoints."""

    def __init__(self):
        """Initialize rate limiter."""
        self.buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    def add_bucket(
        self,
        name: str,
        rate_per_second: float,
        capacity: Optional[int] = None,
        initial_tokens: Optional[int] = None
    ) -> None:
        """Add a token bucket for a specific rate limit.

        Args:
            name: Bucket identifier
            rate_per_second: Rate of token replenishment per second
            capacity: Maximum bucket capacity (defaults to rate_per_second * 60)
            initial_tokens: Initial tokens (defaults to capacity)
        """
        if capacity is None:
            capacity = int(rate_per_second * 60)  # 1 minute worth of tokens

        self.buckets[name] = TokenBucket(
            rate_per_second=rate_per_second,
            capacity=capacity,
            initial_tokens=initial_tokens
        )

    async def acquire(self, bucket_name: str, tokens: int = 1) -> bool:
        """Acquire tokens from a specific bucket.

        Args:
            bucket_name: Name of the bucket
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        if bucket_name not in self.buckets:
            return True  # No rate limit configured

        return await self.buckets[bucket_name].acquire(tokens)

    async def wait_for_tokens(self, bucket_name: str, tokens: int = 1) -> float:
        """Wait for tokens in a specific bucket.

        Args:
            bucket_name: Name of the bucket
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        if bucket_name not in self.buckets:
            return 0.0  # No rate limit configured

        return await self.buckets[bucket_name].wait_for_tokens(tokens)

    def get_wait_time(self, bucket_name: str, tokens: int = 1) -> float:
        """Get estimated wait time for a bucket.

        Args:
            bucket_name: Name of the bucket
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        if bucket_name not in self.buckets:
            return 0.0  # No rate limit configured

        return self.buckets[bucket_name].get_wait_time(tokens)

    def get_bucket_info(self, bucket_name: str) -> Optional[Dict[str, float]]:
        """Get information about a specific bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Bucket information or None if bucket doesn't exist
        """
        if bucket_name not in self.buckets:
            return None

        bucket = self.buckets[bucket_name]
        return {
            'current_tokens': bucket.get_tokens(),
            'capacity': bucket.capacity,
            'rate_per_second': bucket.rate_per_second,
            'wait_time_for_1_token': bucket.get_wait_time(1),
        }

    def list_buckets(self) -> Dict[str, Dict[str, float]]:
        """List all configured buckets with their info.

        Returns:
            Dictionary of bucket information
        """
        return {
            name: self.get_bucket_info(name)
            for name in self.buckets.keys()
        }


class APIRateLimiter:
    """High-level API rate limiter with predefined buckets for common scenarios."""

    def __init__(self):
        """Initialize API rate limiter."""
        self.rate_limiter = RateLimiter()
        self._setup_default_buckets()

    def _setup_default_buckets(self) -> None:
        """Setup default rate limit buckets."""
        settings = get_settings()

        # Global API rate limit
        rate_per_minute = settings.api.rate_limit_per_minute
        rate_per_second = rate_per_minute / 60.0

        self.rate_limiter.add_bucket(
            name="global",
            rate_per_second=rate_per_second,
            capacity=rate_per_minute  # 1 minute capacity
        )

        # Trading-specific rate limits (usually lower)
        trading_rate_per_minute = min(rate_per_minute // 2, 30)  # Max 30 requests per minute for trading
        trading_rate_per_second = trading_rate_per_minute / 60.0

        self.rate_limiter.add_bucket(
            name="trading",
            rate_per_second=trading_rate_per_second,
            capacity=trading_rate_per_minute
        )

        # Market data rate limits (usually higher)
        market_data_rate_per_minute = min(rate_per_minute * 2, 200)  # Max 200 requests per minute for market data
        market_data_rate_per_second = market_data_rate_per_minute / 60.0

        self.rate_limiter.add_bucket(
            name="market_data",
            rate_per_second=market_data_rate_per_second,
            capacity=market_data_rate_per_minute
        )

        # Order management rate limits
        order_rate_per_minute = min(rate_per_minute, 60)  # Max 60 requests per minute for orders
        order_rate_per_second = order_rate_per_minute / 60.0

        self.rate_limiter.add_bucket(
            name="orders",
            rate_per_second=order_rate_per_second,
            capacity=order_rate_per_minute
        )

        # Account/balance rate limits (usually low)
        account_rate_per_minute = min(rate_per_minute // 4, 20)  # Max 20 requests per minute for account
        account_rate_per_second = account_rate_per_minute / 60.0

        self.rate_limiter.add_bucket(
            name="account",
            rate_per_second=account_rate_per_second,
            capacity=account_rate_per_minute
        )

    async def acquire_global(self, tokens: int = 1) -> bool:
        """Acquire global API rate limit tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        return await self.rate_limiter.acquire("global", tokens)

    async def wait_for_global(self, tokens: int = 1) -> float:
        """Wait for global API rate limit tokens.

        Args:
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        return await self.rate_limiter.wait_for_tokens("global", tokens)

    async def acquire_trading(self, tokens: int = 1) -> bool:
        """Acquire trading-specific rate limit tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        return await self.rate_limiter.acquire("trading", tokens)

    async def wait_for_trading(self, tokens: int = 1) -> float:
        """Wait for trading-specific rate limit tokens.

        Args:
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        return await self.rate_limiter.wait_for_tokens("trading", tokens)

    async def acquire_market_data(self, tokens: int = 1) -> bool:
        """Acquire market data rate limit tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        return await self.rate_limiter.acquire("market_data", tokens)

    async def wait_for_market_data(self, tokens: int = 1) -> float:
        """Wait for market data rate limit tokens.

        Args:
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        return await self.rate_limiter.wait_for_tokens("market_data", tokens)

    async def acquire_orders(self, tokens: int = 1) -> bool:
        """Acquire order management rate limit tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        return await self.rate_limiter.acquire("orders", tokens)

    async def wait_for_orders(self, tokens: int = 1) -> float:
        """Wait for order management rate limit tokens.

        Args:
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        return await self.rate_limiter.wait_for_tokens("orders", tokens)

    async def acquire_account(self, tokens: int = 1) -> bool:
        """Acquire account/balance rate limit tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        return await self.rate_limiter.acquire("account", tokens)

    async def wait_for_account(self, tokens: int = 1) -> float:
        """Wait for account/balance rate limit tokens.

        Args:
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        return await self.rate_limiter.wait_for_tokens("account", tokens)

    async def acquire_custom(self, bucket_name: str, tokens: int = 1) -> bool:
        """Acquire tokens from a custom bucket.

        Args:
            bucket_name: Name of the custom bucket
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired
        """
        return await self.rate_limiter.acquire(bucket_name, tokens)

    async def wait_for_custom(self, bucket_name: str, tokens: int = 1) -> float:
        """Wait for tokens from a custom bucket.

        Args:
            bucket_name: Name of the custom bucket
            tokens: Number of tokens to wait for

        Returns:
            Time waited in seconds
        """
        return await self.rate_limiter.wait_for_tokens(bucket_name, tokens)

    def get_wait_time_global(self, tokens: int = 1) -> float:
        """Get estimated wait time for global rate limit.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        return self.rate_limiter.get_wait_time("global", tokens)

    def get_wait_time_trading(self, tokens: int = 1) -> float:
        """Get estimated wait time for trading rate limit.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        return self.rate_limiter.get_wait_time("trading", tokens)

    def get_wait_time_market_data(self, tokens: int = 1) -> float:
        """Get estimated wait time for market data rate limit.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        return self.rate_limiter.get_wait_time("market_data", tokens)

    def get_wait_time_orders(self, tokens: int = 1) -> float:
        """Get estimated wait time for orders rate limit.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        return self.rate_limiter.get_wait_time("orders", tokens)

    def get_wait_time_account(self, tokens: int = 1) -> float:
        """Get estimated wait time for account rate limit.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        return self.rate_limiter.get_wait_time("account", tokens)

    def get_wait_time_custom(self, bucket_name: str, tokens: int = 1) -> float:
        """Get estimated wait time for custom rate limit.

        Args:
            bucket_name: Name of the custom bucket
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        return self.rate_limiter.get_wait_time(bucket_name, tokens)

    def get_bucket_info(self, bucket_name: str) -> Optional[Dict[str, float]]:
        """Get information about a specific bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Bucket information or None if bucket doesn't exist
        """
        return self.rate_limiter.get_bucket_info(bucket_name)

    def list_buckets(self) -> Dict[str, Dict[str, float]]:
        """List all configured buckets with their info.

        Returns:
            Dictionary of bucket information
        """
        return self.rate_limiter.list_buckets()

    def add_custom_bucket(
        self,
        name: str,
        rate_per_second: float,
        capacity: Optional[int] = None
    ) -> None:
        """Add a custom rate limit bucket.

        Args:
            name: Bucket identifier
            rate_per_second: Rate of token replenishment per second
            capacity: Maximum bucket capacity (defaults to rate_per_second * 60)
        """
        self.rate_limiter.add_bucket(name, rate_per_second, capacity)


# Global rate limiter instance
_api_rate_limiter: Optional[APIRateLimiter] = None
_rate_limiter_lock = asyncio.Lock()


async def get_api_rate_limiter() -> APIRateLimiter:
    """Get the global API rate limiter instance.

    Returns:
        Global APIRateLimiter instance
    """
    global _api_rate_limiter

    async with _rate_limiter_lock:
        if _api_rate_limiter is None:
            _api_rate_limiter = APIRateLimiter()

    return _api_rate_limiter


# Convenience functions for common use cases
async def rate_limit_api_call(call_type: str = "global", tokens: int = 1) -> float:
    """Rate limit an API call and return wait time.

    Args:
        call_type: Type of API call ("global", "trading", "market_data", "orders", "account")
        tokens: Number of tokens to consume

    Returns:
        Time waited in seconds
    """
    rate_limiter = await get_api_rate_limiter()

    if call_type == "trading":
        return await rate_limiter.wait_for_trading(tokens)
    elif call_type == "market_data":
        return await rate_limiter.wait_for_market_data(tokens)
    elif call_type == "orders":
        return await rate_limiter.wait_for_orders(tokens)
    elif call_type == "account":
        return await rate_limiter.wait_for_account(tokens)
    else:
        return await rate_limiter.wait_for_global(tokens)


def get_estimated_wait_time(call_type: str = "global", tokens: int = 1) -> float:
    """Get estimated wait time for an API call without consuming tokens.

    Args:
        call_type: Type of API call
        tokens: Number of tokens needed

    Returns:
        Estimated wait time in seconds
    """
    import asyncio

    # Get or create event loop for sync access
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, we need to handle this differently
            return 1.0  # Default fallback
    except RuntimeError:
        # No event loop, create a new one for this operation
        return asyncio.run(_get_estimated_wait_time_async(call_type, tokens))

    return asyncio.run(_get_estimated_wait_time_async(call_type, tokens))


async def _get_estimated_wait_time_async(call_type: str = "global", tokens: int = 1) -> float:
    """Async helper to get estimated wait time."""
    rate_limiter = await get_api_rate_limiter()

    if call_type == "trading":
        return rate_limiter.get_wait_time_trading(tokens)
    elif call_type == "market_data":
        return rate_limiter.get_wait_time_market_data(tokens)
    elif call_type == "orders":
        return rate_limiter.get_wait_time_orders(tokens)
    elif call_type == "account":
        return rate_limiter.get_wait_time_account(tokens)
    else:
        return rate_limiter.get_wait_time_global(tokens)


class RateLimitContext:
    """Context manager for automatic rate limiting."""

    def __init__(self, call_type: str = "global", tokens: int = 1):
        """Initialize rate limit context.

        Args:
            call_type: Type of API call to rate limit
            tokens: Number of tokens to consume
        """
        self.call_type = call_type
        self.tokens = tokens
        self.wait_time = 0.0

    async def __aenter__(self) -> RateLimitContext:
        """Enter the rate limit context and wait for tokens."""
        self.wait_time = await rate_limit_api_call(self.call_type, self.tokens)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the rate limit context."""
        pass


# Decorator for automatic rate limiting
def rate_limited(call_type: str = "global", tokens: int = 1):
    """Decorator to automatically rate limit function calls.

    Args:
        call_type: Type of API call
        tokens: Number of tokens to consume per call
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            async with RateLimitContext(call_type, tokens):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, need to create a task
                    return asyncio.create_task(async_wrapper(*args, **kwargs))
                else:
                    return loop.run_until_complete(async_wrapper(*args, **kwargs))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator