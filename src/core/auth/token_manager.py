"""Token management for OAuth authentication."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, Optional, Union
from pathlib import Path

import aiohttp

from ..config import get_settings
from ...utils.logging import get_logger


class TokenError(Exception):
    """Raised when there's an error with token operations."""
    pass


class TokenExpiredError(TokenError):
    """Raised when an access token has expired."""
    pass


class TokenInvalidError(TokenError):
    """Raised when a token is invalid or malformed."""
    pass


class Token:
    """Represents an OAuth token."""

    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        expires_in: Optional[int] = None,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None,
        obtained_at: Optional[float] = None,
    ):
        """Initialize token.

        Args:
            access_token: The access token string
            token_type: Type of token (usually "Bearer")
            expires_in: Token lifetime in seconds
            refresh_token: Refresh token for renewing access
            scope: Token scope/permissions
            obtained_at: Timestamp when token was obtained
        """
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.scope = scope
        self.obtained_at = obtained_at or time.time()

    @property
    def expires_at(self) -> Optional[float]:
        """Get token expiration timestamp."""
        if self.expires_in:
            return self.obtained_at + self.expires_in
        return None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False  # No expiration set
        return time.time() >= self.expires_at

    @property
    def time_until_expiry(self) -> Optional[float]:
        """Get time until token expires in seconds."""
        if not self.expires_at:
            return None
        return max(0, self.expires_at - time.time())

    def to_dict(self) -> Dict[str, Union[str, int, float, None]]:
        """Convert token to dictionary."""
        return {
            'access_token': self.access_token,
            'token_type': self.token_type,
            'expires_in': self.expires_in,
            'refresh_token': self.refresh_token,
            'scope': self.scope,
            'obtained_at': self.obtained_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int, float, None]]) -> Token:
        """Create token from dictionary."""
        return cls(
            access_token=str(data['access_token']),
            token_type=str(data.get('token_type', 'Bearer')),
            expires_in=int(data['expires_in']) if data.get('expires_in') else None,
            refresh_token=str(data['refresh_token']) if data.get('refresh_token') else None,
            scope=str(data['scope']) if data.get('scope') else None,
            obtained_at=float(data['obtained_at']) if data.get('obtained_at') else None,
        )

    def __str__(self) -> str:
        """String representation of token."""
        return f"Token(type={self.token_type}, expires_in={self.expires_in})"


class TokenStorage:
    """Abstract base class for token storage."""

    async def save_token(self, name: str, token: Token) -> None:
        """Save token.

        Args:
            name: Token identifier
            token: Token to save
        """
        raise NotImplementedError

    async def load_token(self, name: str) -> Optional[Token]:
        """Load token.

        Args:
            name: Token identifier

        Returns:
            Token if found, None otherwise
        """
        raise NotImplementedError

    async def delete_token(self, name: str) -> None:
        """Delete token.

        Args:
            name: Token identifier
        """
        raise NotImplementedError

    async def list_tokens(self) -> Dict[str, Token]:
        """List all stored tokens.

        Returns:
            Dictionary of token names and tokens
        """
        raise NotImplementedError


class MemoryTokenStorage(TokenStorage):
    """In-memory token storage."""

    def __init__(self):
        """Initialize memory storage."""
        self._tokens: Dict[str, Token] = {}

    async def save_token(self, name: str, token: Token) -> None:
        """Save token to memory."""
        self._tokens[name] = token

    async def load_token(self, name: str) -> Optional[Token]:
        """Load token from memory."""
        return self._tokens.get(name)

    async def delete_token(self, name: str) -> None:
        """Delete token from memory."""
        self._tokens.pop(name, None)

    async def list_tokens(self) -> Dict[str, Token]:
        """List all tokens in memory."""
        return self._tokens.copy()


class FileTokenStorage(TokenStorage):
    """File-based token storage."""

    def __init__(self, storage_path: Union[str, Path]):
        """Initialize file storage.

        Args:
            storage_path: Directory to store token files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_token_file(self, name: str) -> Path:
        """Get token file path."""
        return self.storage_path / f"{name}.json"

    async def save_token(self, name: str, token: Token) -> None:
        """Save token to file."""
        file_path = self._get_token_file(name)
        token_data = token.to_dict()

        # Write atomically
        temp_file = file_path.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2)
            temp_file.replace(file_path)
        except Exception:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise

    async def load_token(self, name: str) -> Optional[Token]:
        """Load token from file."""
        file_path = self._get_token_file(name)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            return Token.from_dict(token_data)
        except Exception:
            # If file is corrupted, delete it
            file_path.unlink(missing_ok=True)
            return None

    async def delete_token(self, name: str) -> None:
        """Delete token file."""
        file_path = self._get_token_file(name)
        file_path.unlink(missing_ok=True)

    async def list_tokens(self) -> Dict[str, Token]:
        """List all token files."""
        tokens = {}

        for token_file in self.storage_path.glob("*.json"):
            try:
                name = token_file.stem
                token = await self.load_token(name)
                if token:
                    tokens[name] = token
            except Exception:
                continue

        return tokens


class RedisTokenStorage(TokenStorage):
    """Redis-based token storage."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis storage.

        Args:
            redis_url: Redis connection URL
        """
        import aioredis

        self.redis_url = redis_url or get_settings().get_redis_url()
        self.redis = None

    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            import aioredis
            self.redis = aioredis.from_url(self.redis_url)
        return self.redis

    async def save_token(self, name: str, token: Token) -> None:
        """Save token to Redis."""
        redis = await self._get_redis()
        token_data = json.dumps(token.to_dict())
        await redis.set(f"token:{name}", token_data)

    async def load_token(self, name: str) -> Optional[Token]:
        """Load token from Redis."""
        redis = await self._get_redis()
        token_data = await redis.get(f"token:{name}")

        if not token_data:
            return None

        try:
            data = json.loads(token_data)
            return Token.from_dict(data)
        except Exception:
            # Delete corrupted token
            await redis.delete(f"token:{name}")
            return None

    async def delete_token(self, name: str) -> None:
        """Delete token from Redis."""
        redis = await self._get_redis()
        await redis.delete(f"token:{name}")

    async def list_tokens(self) -> Dict[str, Token]:
        """List all tokens in Redis."""
        redis = await self._get_redis()
        pattern = "token:*"

        tokens = {}
        async for key in redis.scan_iter(pattern):
            name = key.decode().removeprefix("token:")
            token = await self.load_token(name)
            if token:
                tokens[name] = token

        return tokens


class TokenManager:
    """Manages OAuth tokens with automatic refresh."""

    def __init__(
        self,
        storage: Optional[TokenStorage] = None,
        auto_refresh: bool = True,
        refresh_threshold: int = 300,  # 5 minutes
    ):
        """Initialize token manager.

        Args:
            storage: Token storage backend
            auto_refresh: Enable automatic token refresh
            refresh_threshold: Refresh tokens when they expire within this many seconds
        """
        self.logger = get_logger("auth.token_manager")
        self.storage = storage or MemoryTokenStorage()
        self.auto_refresh = auto_refresh
        self.refresh_threshold = refresh_threshold
        self._refresh_tasks: Dict[str, asyncio.Task] = {}

    async def store_token(self, name: str, token: Token) -> None:
        """Store a token.

        Args:
            name: Token identifier
            token: Token to store
        """
        await self.storage.save_token(name, token)
        self.logger.info(f"Stored token: {name}")

        # Start refresh task if auto-refresh is enabled
        if self.auto_refresh and token.refresh_token:
            await self._schedule_token_refresh(name, token)

    async def get_token(self, name: str) -> Optional[Token]:
        """Get a token.

        Args:
            name: Token identifier

        Returns:
            Token if found and valid, None otherwise
        """
        token = await self.storage.load_token(name)

        if not token:
            return None

        # Check if token is expired
        if token.is_expired:
            self.logger.warning(f"Token {name} has expired")
            await self._cleanup_token(name)
            return None

        return token

    async def get_valid_token(self, name: str) -> Optional[Token]:
        """Get a valid token, refreshing if necessary.

        Args:
            name: Token identifier

        Returns:
            Valid token or None if not available
        """
        token = await self.get_token(name)

        if not token:
            return None

        # Check if token needs refresh
        if self.auto_refresh and token.refresh_token and token.time_until_expiry:
            if token.time_until_expiry <= self.refresh_threshold:
                # Try to refresh token
                refreshed_token = await self._refresh_token(name, token)
                if refreshed_token:
                    return refreshed_token

        return token

    async def delete_token(self, name: str) -> None:
        """Delete a token.

        Args:
            name: Token identifier
        """
        await self.storage.delete_token(name)
        await self._cleanup_token(name)
        self.logger.info(f"Deleted token: {name}")

    async def list_tokens(self) -> Dict[str, Token]:
        """List all tokens.

        Returns:
            Dictionary of token names and tokens
        """
        return await self.storage.list_tokens()

    async def _refresh_token(self, name: str, token: Token) -> Optional[Token]:
        """Refresh an expired token.

        Args:
            name: Token identifier
            token: Token to refresh

        Returns:
            New token if refresh successful, None otherwise
        """
        if not token.refresh_token:
            self.logger.warning(f"No refresh token available for {name}")
            return None

        try:
            # Cancel existing refresh task
            await self._cancel_refresh_task(name)

            self.logger.info(f"Refreshing token: {name}")

            # This would typically call an OAuth refresh endpoint
            # For now, we'll implement a generic refresh mechanism
            new_token = await self._perform_token_refresh(token)

            if new_token:
                await self.store_token(name, new_token)
                self.logger.info(f"Successfully refreshed token: {name}")
                return new_token
            else:
                self.logger.error(f"Failed to refresh token: {name}")
                await self._cleanup_token(name)
                return None

        except Exception as e:
            self.logger.error(f"Error refreshing token {name}: {str(e)}")
            await self._cleanup_token(name)
            return None

    async def _perform_token_refresh(self, token: Token) -> Optional[Token]:
        """Perform the actual token refresh operation.

        This is a base implementation. Subclasses should override this
        method to implement exchange-specific refresh logic.

        Args:
            token: Token to refresh

        Returns:
            New token if refresh successful
        """
        # This would typically make an HTTP request to the OAuth refresh endpoint
        # For now, we'll return None to indicate refresh is not implemented
        self.logger.warning("Token refresh not implemented - using base implementation")
        return None

    async def _schedule_token_refresh(self, name: str, token: Token) -> None:
        """Schedule automatic token refresh.

        Args:
            name: Token identifier
            token: Token to schedule refresh for
        """
        # Cancel existing refresh task
        await self._cancel_refresh_task(name)

        if not token.refresh_token or not token.time_until_expiry:
            return

        # Schedule refresh before token expires
        refresh_delay = max(0, token.time_until_expiry - self.refresh_threshold)

        async def refresh_task():
            await asyncio.sleep(refresh_delay)
            await self._refresh_token(name, token)

        task = asyncio.create_task(refresh_task())
        self._refresh_tasks[name] = task

        self.logger.debug(f"Scheduled token refresh for {name} in {refresh_delay:.0f} seconds")

    async def _cancel_refresh_task(self, name: str) -> None:
        """Cancel refresh task for a token.

        Args:
            name: Token identifier
        """
        task = self._refresh_tasks.pop(name, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _cleanup_token(self, name: str) -> None:
        """Clean up resources for a token.

        Args:
            name: Token identifier
        """
        await self._cancel_refresh_task(name)

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cancel all refresh tasks
        for name in list(self._refresh_tasks.keys()):
            await self._cancel_refresh_task(name)

        self.logger.info("Token manager cleanup completed")


class ExchangeTokenManager(TokenManager):
    """Token manager for cryptocurrency exchanges."""

    def __init__(
        self,
        exchange_name: str,
        refresh_url: Optional[str] = None,
        **kwargs
    ):
        """Initialize exchange token manager.

        Args:
            exchange_name: Name of the exchange
            refresh_url: Token refresh endpoint URL
            **kwargs: Additional arguments for TokenManager
        """
        super().__init__(**kwargs)
        self.exchange_name = exchange_name
        self.refresh_url = refresh_url

        # Use file storage for exchange tokens by default
        if not self.storage or isinstance(self.storage, MemoryTokenStorage):
            storage_path = Path(f"tokens/{exchange_name}")
            self.storage = FileTokenStorage(storage_path)

    async def _perform_token_refresh(self, token: Token) -> Optional[Token]:
        """Perform exchange-specific token refresh.

        Args:
            token: Token to refresh

        Returns:
            New token if refresh successful
        """
        if not self.refresh_url:
            self.logger.error(f"No refresh URL configured for {self.exchange_name}")
            return None

        try:
            # Prepare refresh request
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': token.refresh_token,
            }

            # Add client credentials if available
            settings = get_settings()
            if settings.exchange.api_key and settings.exchange.secret_key:
                refresh_data.update({
                    'client_id': settings.exchange.api_key,
                    'client_secret': settings.exchange.secret_key,
                })

            # Make refresh request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.refresh_url, data=refresh_data) as response:
                    if response.status != 200:
                        self.logger.error(f"Token refresh failed: HTTP {response.status}")
                        return None

                    data = await response.json()

                    # Parse new token
                    return Token(
                        access_token=data['access_token'],
                        token_type=data.get('token_type', 'Bearer'),
                        expires_in=data.get('expires_in'),
                        refresh_token=data.get('refresh_token', token.refresh_token),
                        scope=data.get('scope'),
                    )

        except Exception as e:
            self.logger.error(f"Error during token refresh: {str(e)}")
            return None


# Global token manager instance
_token_manager: Optional[TokenManager] = None
_token_manager_lock = asyncio.Lock()


async def get_token_manager() -> TokenManager:
    """Get the global token manager instance.

    Returns:
        Global TokenManager instance
    """
    global _token_manager

    async with _token_manager_lock:
        if _token_manager is None:
            _token_manager = TokenManager()

    return _token_manager


# Convenience functions
async def store_token(name: str, token: Token) -> None:
    """Store a token.

    Args:
        name: Token identifier
        token: Token to store
    """
    manager = await get_token_manager()
    await manager.store_token(name, token)


async def get_token(name: str) -> Optional[Token]:
    """Get a token.

    Args:
        name: Token identifier

    Returns:
        Token if found and valid
    """
    manager = await get_token_manager()
    return await manager.get_valid_token(name)


async def delete_token(name: str) -> None:
    """Delete a token.

    Args:
        name: Token identifier
    """
    manager = await get_token_manager()
    await manager.delete_token(name)


async def list_tokens() -> Dict[str, Token]:
    """List all tokens.

    Returns:
        Dictionary of token names and tokens
    """
    manager = await get_token_manager()
    return await manager.list_tokens()