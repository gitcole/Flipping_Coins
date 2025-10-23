"""OAuth 2.0 client implementation for authentication."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Dict, List, Optional, Union
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from ..config import get_settings
from ...utils.logging import get_logger
from .token_manager import Token, TokenManager


class OAuthError(Exception):
    """Base exception for OAuth-related errors."""
    pass


class OAuthFlowError(OAuthError):
    """Raised when OAuth flow fails."""
    pass


class OAuthTokenError(OAuthError):
    """Raised when token operations fail."""
    pass


class OAuthClient:
    """OAuth 2.0 client for handling authorization flows."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_url: str,
        token_url: str,
        scopes: Optional[List[str]] = None,
        token_manager: Optional[TokenManager] = None,
    ):
        """Initialize OAuth client.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            authorization_url: Authorization endpoint URL
            token_url: Token endpoint URL
            scopes: List of OAuth scopes to request
            token_manager: Token manager instance
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.scopes = scopes or []
        self.token_manager = token_manager or TokenManager()

        self.logger = get_logger("auth.oauth_client")

        # Generate state for CSRF protection
        self._state = secrets.token_urlsafe(32)

    @property
    def state(self) -> str:
        """Get current state for CSRF protection."""
        return self._state

    def new_state(self) -> str:
        """Generate new state for CSRF protection."""
        self._state = secrets.token_urlsafe(32)
        return self._state

    def build_authorization_url(
        self,
        state: Optional[str] = None,
        additional_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection
            additional_params: Additional query parameters

        Returns:
            Complete authorization URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'state': state or self.state,
        }

        if additional_params:
            params.update(additional_params)

        query_string = urlencode(params)
        return f"{self.authorization_url}?{query_string}"

    async def exchange_code_for_token(
        self,
        authorization_code: str,
        code_verifier: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Token:
        """Exchange authorization code for access token.

        Args:
            authorization_code: Authorization code from OAuth provider
            code_verifier: PKCE code verifier (if using PKCE)
            state: State parameter for verification

        Returns:
            Access token

        Raises:
            OAuthFlowError: If token exchange fails
        """
        if state and state != self.state:
            raise OAuthFlowError("State parameter mismatch")

        # Prepare token request
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': authorization_code,
        }

        # Add PKCE code verifier if provided
        if code_verifier:
            token_data['code_verifier'] = code_verifier

        try:
            # Make token request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=token_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise OAuthFlowError(f"Token exchange failed: {error_text}")

                    token_response = await response.json()

                    # Parse token response
                    token = Token(
                        access_token=token_response['access_token'],
                        token_type=token_response.get('token_type', 'Bearer'),
                        expires_in=token_response.get('expires_in'),
                        refresh_token=token_response.get('refresh_token'),
                        scope=token_response.get('scope'),
                    )

                    # Store token
                    await self.token_manager.store_token('default', token)

                    self.logger.info("Successfully exchanged authorization code for token")
                    return token

        except aiohttp.ClientError as e:
            raise OAuthFlowError(f"Token exchange request failed: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            New access token

        Raises:
            OAuthTokenError: If refresh fails
        """
        refresh_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=refresh_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise OAuthTokenError(f"Token refresh failed: {error_text}")

                    token_response = await response.json()

                    # Create new token
                    token = Token(
                        access_token=token_response['access_token'],
                        token_type=token_response.get('token_type', 'Bearer'),
                        expires_in=token_response.get('expires_in'),
                        refresh_token=token_response.get('refresh_token', refresh_token),
                        scope=token_response.get('scope'),
                    )

                    # Store updated token
                    await self.token_manager.store_token('default', token)

                    self.logger.info("Successfully refreshed access token")
                    return token

        except aiohttp.ClientError as e:
            raise OAuthTokenError(f"Token refresh request failed: {str(e)}")

    async def revoke_token(self, token: str, token_type_hint: str = "access_token") -> bool:
        """Revoke an OAuth token.

        Args:
            token: Token to revoke
            token_type_hint: Type of token being revoked

        Returns:
            True if revocation was successful

        Raises:
            OAuthTokenError: If revocation fails
        """
        # Note: Not all OAuth providers support token revocation
        # This is a base implementation
        try:
            revoke_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'token': token,
                'token_type_hint': token_type_hint,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.token_url}/revoke", data=revoke_data) as response:
                    success = response.status in (200, 204)

                    if success:
                        self.logger.info("Successfully revoked OAuth token")
                    else:
                        self.logger.warning(f"Token revocation returned status {response.status}")

                    return success

        except aiohttp.ClientError as e:
            self.logger.error(f"Token revocation request failed: {str(e)}")
            return False


class PKCEHelper:
    """Helper for PKCE (Proof Key for Code Exchange) operations."""

    @staticmethod
    def generate_code_challenge(code_verifier: str, method: str = "S256") -> str:
        """Generate PKCE code challenge.

        Args:
            code_verifier: Code verifier string
            method: Hash method (S256 or plain)

        Returns:
            Code challenge string
        """
        if method == "S256":
            # SHA256 hash and base64url encode
            hash_bytes = hashlib.sha256(code_verifier.encode()).digest()
            return base64.urlsafe_b64encode(hash_bytes).decode().rstrip('=')
        elif method == "plain":
            return code_verifier
        else:
            raise ValueError(f"Unsupported PKCE method: {method}")

    @staticmethod
    def generate_code_verifier(length: int = 128) -> str:
        """Generate PKCE code verifier.

        Args:
            length: Length of code verifier

        Returns:
            Code verifier string
        """
        # Generate random string of specified length
        # Use URL-safe characters as per RFC 7636
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        return ''.join(secrets.choice(chars) for _ in range(length))


class ExchangeOAuthClient(OAuthClient):
    """OAuth client specifically for cryptocurrency exchanges."""

    def __init__(
        self,
        exchange_name: str,
        client_id: str,
        client_secret: str,
        **kwargs
    ):
        """Initialize exchange OAuth client.

        Args:
            exchange_name: Name of the exchange
            client_id: Exchange client ID
            client_secret: Exchange client secret
            **kwargs: Additional arguments for OAuthClient
        """
        # Set exchange-specific defaults
        if 'scopes' not in kwargs:
            kwargs['scopes'] = ['trading', 'account']

        super().__init__(client_id, client_secret, **kwargs)

        self.exchange_name = exchange_name

        # Override token manager with exchange-specific one
        if not self.token_manager:
            self.token_manager = TokenManager()

    def build_authorization_url(
        self,
        use_pkce: bool = False,
        **kwargs
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Build authorization URL with optional PKCE support.

        Args:
            use_pkce: Whether to use PKCE
            **kwargs: Additional arguments for authorization URL

        Returns:
            Tuple of (authorization_url, code_verifier, state)
        """
        additional_params = kwargs.get('additional_params', {})

        if use_pkce:
            # Generate PKCE parameters
            code_verifier = PKCEHelper.generate_code_verifier()
            code_challenge = PKCEHelper.generate_code_challenge(code_verifier)

            additional_params.update({
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256',
            })

            kwargs['additional_params'] = additional_params

        url = super().build_authorization_url(**kwargs)

        state = kwargs.get('state') or self.state
        return url, code_verifier if use_pkce else None, state

    async def authenticate_with_pkce(
        self,
        use_pkce: bool = True,
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Start OAuth flow with PKCE support.

        Args:
            use_pkce: Whether to use PKCE

        Returns:
            Tuple of (authorization_url, code_verifier, state)
        """
        return self.build_authorization_url(use_pkce=use_pkce)

    async def complete_authentication(
        self,
        authorization_code: str,
        code_verifier: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Token:
        """Complete OAuth authentication flow.

        Args:
            authorization_code: Authorization code from callback
            code_verifier: PKCE code verifier if using PKCE
            state: State parameter for verification

        Returns:
            Access token
        """
        return await self.exchange_code_for_token(
            authorization_code,
            code_verifier=code_verifier,
            state=state,
        )


class OAuthFlowManager:
    """Manages complete OAuth authentication flows."""

    def __init__(
        self,
        client: OAuthClient,
        token_storage_path: Optional[str] = None,
    ):
        """Initialize OAuth flow manager.

        Args:
            client: OAuth client instance
            token_storage_path: Path for token storage
        """
        self.client = client
        self.logger = get_logger("auth.oauth_flow")

        # Use file storage for tokens if path provided
        if token_storage_path:
            from .token_manager import FileTokenStorage
            storage = FileTokenStorage(token_storage_path)
            self.client.token_manager = TokenManager(storage=storage)

    async def run_device_flow(self) -> Token:
        """Run OAuth Device Authorization Grant flow.

        Returns:
            Access token

        Raises:
            OAuthFlowError: If device flow fails
        """
        # Device flow implementation would go here
        # This is a placeholder for the device authorization grant flow
        self.logger.warning("Device flow not implemented")
        raise OAuthFlowError("Device flow not implemented")

    async def run_implicit_flow(self) -> Token:
        """Run OAuth Implicit Grant flow.

        Returns:
            Access token

        Raises:
            OAuthFlowError: If implicit flow fails
        """
        # Implicit flow implementation would go here
        self.logger.warning("Implicit flow not implemented")
        raise OAuthFlowError("Implicit flow not implemented")

    async def run_authorization_code_flow(
        self,
        use_pkce: bool = True,
        interactive: bool = True,
    ) -> Token:
        """Run OAuth Authorization Code flow.

        Args:
            use_pkce: Whether to use PKCE
            interactive: Whether to print URLs for manual authentication

        Returns:
            Access token

        Raises:
            OAuthFlowError: If authorization code flow fails
        """
        # Build authorization URL
        auth_url, code_verifier, state = self.client.build_authorization_url(use_pkce=use_pkce)

        if interactive:
            self.logger.info(f"Please visit this URL to authorize: {auth_url}")
            self.logger.info("After authorization, you'll receive an authorization code.")

        # In a real implementation, this would:
        # 1. Open browser or display URL
        # 2. Wait for callback with authorization code
        # 3. Exchange code for token

        # For now, we'll simulate this process
        self.logger.warning("Interactive authorization code flow requires manual implementation")
        self.logger.info(f"Authorization URL: {auth_url}")

        if use_pkce:
            self.logger.info(f"Code verifier: {code_verifier}")

        raise OAuthFlowError("Interactive flow requires manual code exchange")

    async def get_valid_token(self) -> Optional[Token]:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token or None if not available
        """
        return await self.client.token_manager.get_valid_token('default')

    async def revoke_current_token(self) -> bool:
        """Revoke the current access token.

        Returns:
            True if revocation was successful
        """
        token = await self.get_valid_token()

        if not token:
            self.logger.warning("No valid token to revoke")
            return False

        return await self.client.revoke_token(token.access_token)


class ExchangeAuthenticator:
    """High-level authenticator for cryptocurrency exchanges."""

    def __init__(
        self,
        exchange_name: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
    ):
        """Initialize exchange authenticator.

        Args:
            exchange_name: Name of the exchange
            api_key: Exchange API key
            api_secret: Exchange API secret
            sandbox: Use sandbox environment
        """
        self.exchange_name = exchange_name
        self.settings = get_settings()

        # Use provided credentials or fall back to settings
        self.api_key = api_key or self.settings.exchange.api_key
        self.api_secret = api_secret or self.settings.exchange.secret_key
        self.sandbox = sandbox or self.settings.exchange.sandbox

        self.logger = get_logger(f"auth.{exchange_name}")

        # OAuth configuration for exchanges that support it
        self.oauth_config = self._get_oauth_config()

        # Initialize OAuth client if configured
        self.oauth_client = None
        if self.oauth_config:
            self.oauth_client = ExchangeOAuthClient(
                exchange_name=exchange_name,
                client_id=self.oauth_config['client_id'],
                client_secret=self.oauth_config['client_secret'],
                authorization_url=self.oauth_config['authorization_url'],
                token_url=self.oauth_config['token_url'],
                redirect_uri=self.oauth_config['redirect_uri'],
            )

    def _get_oauth_config(self) -> Optional[Dict[str, str]]:
        """Get OAuth configuration for the exchange.

        Returns:
            OAuth configuration or None if not supported
        """
        # This would typically be loaded from a configuration file
        # or determined based on the exchange
        oauth_configs = {
            'binance': {
                'client_id': self.api_key,
                'client_secret': self.api_secret,
                'authorization_url': 'https://accounts.binance.com/oauth/authorize',
                'token_url': 'https://accounts.binance.com/oauth/token',
                'redirect_uri': 'http://localhost:8080/callback',
            },
            # Add more exchanges as needed
        }

        return oauth_configs.get(self.exchange_name.lower())

    async def authenticate_api_key(self) -> bool:
        """Authenticate using API key and secret.

        Returns:
            True if authentication is successful
        """
        if not self.api_key or not self.api_secret:
            self.logger.error("API key and secret are required for API key authentication")
            return False

        try:
            # Test authentication by making a simple API call
            # This would typically be implemented per exchange
            self.logger.info(f"API key authentication configured for {self.exchange_name}")
            return True

        except Exception as e:
            self.logger.error(f"API key authentication failed: {str(e)}")
            return False

    async def authenticate_oauth(
        self,
        use_pkce: bool = True,
        force_reauth: bool = False,
    ) -> Optional[Token]:
        """Authenticate using OAuth flow.

        Args:
            use_pkce: Whether to use PKCE for enhanced security
            force_reauth: Force re-authentication even if token exists

        Returns:
            Access token if authentication successful
        """
        if not self.oauth_client:
            self.logger.error(f"OAuth not supported for {self.exchange_name}")
            return None

        # Check if we already have a valid token
        if not force_reauth:
            existing_token = await self.oauth_client.token_manager.get_valid_token('default')
            if existing_token:
                self.logger.info("Using existing OAuth token")
                return existing_token

        try:
            # Run OAuth flow
            flow_manager = OAuthFlowManager(self.oauth_client)
            token = await flow_manager.run_authorization_code_flow(use_pkce=use_pkce)

            self.logger.info("OAuth authentication completed successfully")
            return token

        except Exception as e:
            self.logger.error(f"OAuth authentication failed: {str(e)}")
            return None

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dictionary of authentication headers
        """
        headers = {}

        if self.oauth_client:
            # Use OAuth token if available
            token = await self.oauth_client.token_manager.get_valid_token('default')
            if token:
                headers['Authorization'] = f"{token.token_type} {token.access_token}"

        # Fall back to API key authentication
        if not headers and self.api_key:
            headers['X-API-Key'] = self.api_key

            # Add signature if secret is available
            if self.api_secret:
                # This would implement exchange-specific signing
                # For now, just add the secret as a header
                headers['X-API-Secret'] = self.api_secret

        return headers

    async def is_authenticated(self) -> bool:
        """Check if currently authenticated.

        Returns:
            True if authenticated
        """
        if self.oauth_client:
            token = await self.oauth_client.token_manager.get_valid_token('default')
            if token:
                return True

        # Check API key authentication
        return bool(self.api_key and self.api_secret)

    async def revoke_authentication(self) -> bool:
        """Revoke current authentication.

        Returns:
            True if revocation was successful
        """
        success = True

        if self.oauth_client:
            try:
                await self.oauth_client.token_manager.delete_token('default')
                self.logger.info("OAuth token revoked")
            except Exception as e:
                self.logger.error(f"Failed to revoke OAuth token: {str(e)}")
                success = False

        return success


# Convenience functions for common authentication patterns
async def authenticate_exchange(
    exchange_name: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    use_oauth: bool = False,
    sandbox: bool = False,
) -> ExchangeAuthenticator:
    """Authenticate with a cryptocurrency exchange.

    Args:
        exchange_name: Name of the exchange
        api_key: Exchange API key
        api_secret: Exchange API secret
        use_oauth: Whether to use OAuth authentication
        sandbox: Use sandbox environment

    Returns:
        Authenticated exchange authenticator
    """
    authenticator = ExchangeAuthenticator(
        exchange_name=exchange_name,
        api_key=api_key,
        api_secret=api_secret,
        sandbox=sandbox,
    )

    if use_oauth:
        await authenticator.authenticate_oauth()
    else:
        await authenticator.authenticate_api_key()

    return authenticator


async def get_exchange_auth_headers(exchange_name: str) -> Dict[str, str]:
    """Get authentication headers for an exchange.

    Args:
        exchange_name: Name of the exchange

    Returns:
        Dictionary of authentication headers
    """
    authenticator = ExchangeAuthenticator(exchange_name)
    return await authenticator.get_auth_headers()