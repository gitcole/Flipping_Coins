"""
Main Robinhood API Client

Central client for interacting with the Robinhood API, integrating authentication,
rate limiting, and all Robinhood-specific functionality.
"""

import asyncio
import time
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin

import structlog
from pydantic import BaseModel

from ...config import get_settings
from ...config.manager import ConfigurationError
from ..client import BaseAPIClient
from ..exceptions import APIError, RobinhoodAPIError
from .auth import RobinhoodSignatureAuth
from .crypto_api import RobinhoodCryptoAPI
from .crypto import RobinhoodCrypto
from .market_data import RobinhoodMarketData
from .orders import RobinhoodOrders
from .account import RobinhoodAccount

logger = structlog.get_logger(__name__)


class RobinhoodAPIConfig(BaseModel):
    """Configuration for Robinhood API client."""

    # Authentication (supports both private and public key)
    api_key: Optional[str] = None
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    sandbox: bool = False

    # API settings
    base_url: str = "https://trading.robinhood.com"
    timeout: int = 30
    retries: int = 3
    rate_limit_per_minute: int = 100

    # WebSocket settings
    ws_ping_interval: int = 20
    ws_timeout: int = 10
    ws_max_reconnects: int = 5


class RobinhoodClient(BaseAPIClient):
    """
    Main Robinhood API client providing complete access to Robinhood's API.

    This client integrates:
    - OAuth 2.0 authentication with PKCE
    - Rate limiting and retry logic
    - Crypto trading functionality
    - Market data access
    - Order management
    - Account information
    - Real-time data through WebSocket integration

    Features:
    - Automatic token refresh
    - Sandbox and production environment support
    - Comprehensive error handling
    - Type-safe request/response handling
    - Integration with trading engine and strategies
    """

    def __init__(
        self,
        config: Optional[RobinhoodAPIConfig] = None,
        sandbox: Optional[bool] = None,
        **kwargs
    ):
        """Initialize Robinhood API client.

        Args:
            config: Robinhood API configuration
            sandbox: Whether to use sandbox environment
            **kwargs: Additional arguments for BaseAPIClient
        """
        # Use provided config or create from environment/settings
        if config is None:
            logger.info("RobinhoodClient: No config provided, attempting to load settings...")
            try:
                settings = get_settings()
                logger.info("RobinhoodClient: Successfully loaded settings", sandbox=sandbox)
            except Exception as e:
                logger.warning("RobinhoodClient: Configuration not initialized, attempting auto-initialization: %s", str(e))
                try:
                    # Auto-initialize configuration if not already loaded
                    from ...config import initialize_config
                    settings = initialize_config()
                    logger.info("RobinhoodClient: Successfully auto-initialized configuration")
                except Exception as init_error:
                    logger.error("RobinhoodClient: Failed to auto-initialize configuration: %s", str(init_error))
                    raise ConfigurationError(
                        "Configuration not initialized and auto-initialization failed. "
                        "Please call initialize_config() before creating RobinhoodClient, "
                        "or ensure config/.env file exists with proper credentials."
                    ) from init_error

            # Try to get Robinhood-specific settings
            rh_settings = getattr(settings, 'robinhood', None)
            if rh_settings:
                config = RobinhoodAPIConfig(
                    api_key=rh_settings.api_key,
                    private_key=rh_settings.private_key,
                    public_key=rh_settings.public_key,
                    sandbox=bool(rh_settings.sandbox) if rh_settings.sandbox else False
                )
            else:
                # Create config from environment variables
                config = RobinhoodAPIConfig(
                    api_key=getattr(settings, 'robinhood', None) and settings.robinhood.api_key or None,
                    private_key=getattr(settings, 'robinhood', None) and settings.robinhood.private_key or None,
                    public_key=getattr(settings, 'robinhood', None) and settings.robinhood.public_key or None,
                    sandbox=bool(getattr(settings, 'robinhood', None) and settings.robinhood.sandbox) if getattr(settings, 'robinhood', None) and settings.robinhood.sandbox else False,
                )

        # Override sandbox setting if explicitly provided
        if sandbox is not None:
            config.sandbox = sandbox

        logger.info("Base URL configured", base_url=config.base_url)

        # Initialize base client
        super().__init__(
            base_url=config.base_url,
            timeout=config.timeout,
            retries=config.retries,
            rate_limit_type="robinhood",
            **kwargs
        )

        # Set up authentication (supports both private and public key)
        self.auth = RobinhoodSignatureAuth(
            api_key=config.api_key,
            private_key_b64=config.private_key,
            public_key_b64=config.public_key,
            sandbox=config.sandbox
        )
        self.config = config
        logger.debug("Authentication set up", auth_type=self.auth.get_auth_info()['auth_type'])

        # Initialize service modules
        self.market_data = RobinhoodMarketData(self)
        self.orders = RobinhoodOrders(self)
        self.account = RobinhoodAccount(self)

        # Initialize crypto API (signature-based auth is handled internally)
        self.crypto_api = RobinhoodCryptoAPI()
        self.crypto = RobinhoodCrypto(self)

        # WebSocket client for real-time data
        self._ws_client = None

        logger.info("Robinhood API client initialized", sandbox=config.sandbox)

    async def initialize(self) -> None:
        """Initialize the Robinhood client and validate configuration.

        This method should be called after creating the client to validate
        that all required configuration is present and authentication is working.

        Raises:
            RobinhoodAPIError: If configuration is invalid or authentication fails
        """
        try:
            # Validate configuration
            if not self.config.api_key:
                raise RobinhoodAPIError("API key is required but not configured")
            if not self.config.private_key and not self.config.public_key:
                raise RobinhoodAPIError("Either private key or public key is required but not configured")

            # Validate authentication
            if not self.auth.is_authenticated():
                auth_type = "private key" if self.config.private_key else "public key"
                logger.error("Authentication validation failed", auth_type=auth_type)
                raise RobinhoodAPIError(f"Authentication failed - check API key and {auth_type}")

            logger.debug("Authentication validated successfully")

            # Test connection with a simple health check
            try:
                health = await self.health_check()
                logger.info("Robinhood client initialized successfully", health_status=health.get('status'))
            except Exception as e:
                logger.warning(f"Health check failed during initialization: {e}")
                # Don't fail initialization for health check issues
                logger.info("Robinhood client initialized (health check skipped)")

        except Exception as e:
            logger.error(f"Failed to initialize Robinhood client: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the client and all connections."""
        # Close WebSocket connection if exists
        if self._ws_client:
            await self._ws_client.close()

        await super().close()


    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """Make authenticated request to Robinhood API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            API response

        Raises:
            RobinhoodAPIError: If not authenticated or request fails
        """
        # Check if we're properly authenticated
        if not self.auth.is_authenticated():
            logger.error("Request attempted without authentication", method=method, endpoint=endpoint)
            raise RobinhoodAPIError("Not authenticated with Robinhood API")

        logger.debug("Making authenticated request", method=method, endpoint=endpoint, params=params)
        try:
            response = await super().request(method, endpoint, params=params, data=data, headers=headers, **kwargs)
            logger.debug("Request successful", method=method, endpoint=endpoint, status=response.status if hasattr(response, 'status') else 'unknown')
            return response
        except Exception as e:
            logger.error("Request failed", method=method, endpoint=endpoint, error=str(e))
            raise

    # Convenience methods for common API endpoints

    async def get_instruments(self, symbol: Optional[str] = None) -> Dict:
        """Get instruments (cryptocurrencies/stocks).

        Args:
            symbol: Optional symbol filter

        Returns:
            Instruments data
        """
        endpoint = "/instruments/"
        if symbol:
            endpoint += f"?symbol={symbol}"

        response = await self.get(endpoint)
        return response.data

    async def get_quotes(self, symbols: Union[str, List[str]]) -> Dict:
        """Get quotes for symbols.

        Args:
            symbols: Symbol or list of symbols

        Returns:
            Quotes data
        """
        if isinstance(symbols, list):
            symbols_str = ",".join(symbols)
        else:
            symbols_str = symbols

        response = await self.get("/marketdata/quotes/", params={"symbols": symbols_str})
        return response.data

    async def get_historicals(
        self,
        symbol: str,
        interval: str = "day",
        span: str = "year",
        bounds: str = "regular"
    ) -> Dict:
        """Get historical data for a symbol.

        Args:
            symbol: Trading symbol
            interval: Time interval (5minute, 10minute, hour, day, week)
            span: Time span (day, week, month, 3month, year, 5year)
            bounds: Price bounds (extended, regular, trading)

        Returns:
            Historical data
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "span": span,
            "bounds": bounds,
        }

        response = await self.get("/marketdata/historicals/", params=params)
        return response.data

    async def get_fundamentals(self, symbol: str) -> Dict:
        """Get fundamental data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Fundamental data
        """
        response = await self.get(f"/fundamentals/{symbol}/")
        return response.data

    async def get_popularity(self, symbol: str) -> Dict:
        """Get popularity data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Popularity data
        """
        response = await self.get(f"/instruments/{symbol}/popularity/")
        return response.data

    async def get_ratings(self, symbol: str) -> Dict:
        """Get analyst ratings for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Ratings data
        """
        response = await self.get(f"/instruments/{symbol}/ratings/")
        return response.data

    async def get_news(self, symbol: Optional[str] = None) -> Dict:
        """Get news articles.

        Args:
            symbol: Optional symbol filter

        Returns:
            News data
        """
        endpoint = "/midlands/news/"
        if symbol:
            endpoint += f"?symbol={symbol}"

        response = await self.get(endpoint)
        return response.data

    async def get_markets(self) -> Dict:
        """Get market information.

        Returns:
            Market data
        """
        response = await self.get("/markets/")
        return response.data

    async def get_currency_pairs(self) -> Dict:
        """Get available currency pairs.

        Returns:
            Currency pairs data
        """
        response = await self.get("/midlands/currency_pairs/")
        return response.data

    # User/Account methods

    async def get_user(self) -> Dict:
        """Get current user information.

        Returns:
            User data
        """
        response = await self.get("/user/")
        return response.data

    async def get_accounts(self) -> Dict:
        """Get user accounts.

        Returns:
            Accounts data
        """
        response = await self.get("/accounts/")
        return response.data

    async def get_portfolio(self, account_id: Optional[str] = None) -> Dict:
        """Get portfolio information.

        Args:
            account_id: Optional account ID

        Returns:
            Portfolio data
        """
        if account_id:
            response = await self.get(f"/portfolios/{account_id}/")
        else:
            response = await self.get("/portfolios/")

        return response.data

    async def get_positions(self, account_id: Optional[str] = None) -> Dict:
        """Get account positions.

        Args:
            account_id: Optional account ID

        Returns:
            Positions data
        """
        if account_id:
            response = await self.get(f"/positions/?account_id={account_id}")
        else:
            response = await self.get("/positions/")

        return response.data

    async def get_watchlists(self) -> Dict:
        """Get user watchlists.

        Returns:
            Watchlists data
        """
        response = await self.get("/watchlists/")
        return response.data

    # Utility methods

    def is_sandbox(self) -> bool:
        """Check if client is using sandbox environment."""
        return self.config.sandbox

    def get_auth_info(self) -> Dict:
        """Get information about current authentication configuration."""
        return self.auth.get_auth_info()

    async def health_check(self) -> Dict:
        """Perform a health check of the API connection.

        Returns:
            Health check results
        """
        logger.debug("Starting health check")
        try:
            # Try to get user info as a simple health check
            await self.get_user()
            logger.debug("Health check passed")
            return {
                "status": "healthy",
                "authenticated": True,
                "sandbox": self.is_sandbox(),
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "authenticated": False,
                "error": str(e),
                "timestamp": time.time(),
            }

    # WebSocket integration for real-time data

    async def get_websocket_client(self):
        """Get WebSocket client for real-time data.

        Returns:
            WebSocket client instance
        """
        if self._ws_client is None:
            from ...websocket.client import WebSocketClient

            self._ws_client = WebSocketClient(
                ping_interval=self.config.ws_ping_interval,
                timeout=self.config.ws_timeout,
                max_reconnects=self.config.ws_max_reconnects,
            )

            # Connect to Robinhood WebSocket endpoints
            await self._ws_client.connect("wss://trading.robinhood.com/ws/")

        return self._ws_client

    async def subscribe_quotes(self, symbols: List[str]) -> bool:
        """Subscribe to real-time quotes for symbols.

        Args:
            symbols: List of symbols to subscribe to

        Returns:
            True if subscription successful
        """
        ws_client = await self.get_websocket_client()

        # Format subscription message for Robinhood
        subscription = {
            "type": "subscription",
            "data": {
                "type": "quotes",
                "symbols": symbols
            }
        }

        return await ws_client.send(subscription)

    async def subscribe_order_updates(self) -> bool:
        """Subscribe to real-time order updates.

        Returns:
            True if subscription successful
        """
        ws_client = await self.get_websocket_client()

        subscription = {
            "type": "subscription",
            "data": {
                "type": "orders"
            }
        }

        return await ws_client.send(subscription)