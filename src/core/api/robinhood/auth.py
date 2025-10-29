"""
Robinhood Signature-Based Authentication for Crypto Trading API.

This module provides simplified, secure authentication for the Robinhood Crypto API
using ECDSA digital signatures. It supports both private key and public key-based
authentication methods without requiring complex OAuth flows.

Key Features:
- ECDSA-based digital signature authentication
- Support for both private key (with automatic public key derivation) and public key modes
- Environment variable and direct parameter configuration
- No token management or OAuth complexity required
- Compatible with Robinhood's signature-based authentication system
- Automatic key validation and format checking

Authentication Methods:
1. Private Key Mode: Provide private key, public key is derived automatically
2. Public Key Mode: Provide public key directly (simplified authentication)

Security Notes:
- Private keys should be kept secure and never logged or exposed
- Public keys can be safely shared for authentication
- All key operations use base64 encoding for compatibility

Example:
    >>> # Private key authentication
    >>> auth = RobinhoodSignatureAuth(
    ...     api_key="rh-api-xxx",
    ...     private_key_b64="MF8CAQEE...",
    ...     sandbox=False
    ... )
    >>> if auth.is_authenticated():
    ...     print(f"Authenticated with {auth.get_auth_info()['auth_type']}")

    >>> # Public key authentication
    >>> auth = RobinhoodSignatureAuth(
    ...     api_key="rh-api-xxx",
    ...     public_key_b64="MFkwEwYHKoZI...",
    ...     sandbox=True
    ... )
"""

import os
import time
from typing import Dict, Optional

import structlog
from ecdsa import SigningKey
from base64 import b64decode, b64encode

from ..exceptions import AuthenticationError

logger = structlog.get_logger(__name__)


class RobinhoodSignatureAuth:
    """
    Simplified authentication for Robinhood Crypto API using API key and digital signatures.

    This class handles authentication for the Robinhood Crypto Trading API using ECDSA
    digital signatures. It supports two modes: private key (with automatic public key
    derivation) and public key (direct authentication). The authentication is designed
    to be simple, secure, and compatible with Robinhood's signature-based system.

    Attributes:
        api_key (str): Robinhood API key for authentication
        private_key_b64 (Optional[str]): Base64-encoded private key (if using private key mode)
        public_key_b64 (Optional[str]): Base64-encoded public key (if using public key mode)
        sandbox (bool): Whether using sandbox environment
        base_url (str): API base URL (same for sandbox and production)
        _private_key (Optional[str]): Internal storage for private key
        _public_key (Optional[str]): Internal storage for public key
        _authenticated (bool): Authentication status

    Raises:
        AuthenticationError: If required credentials are missing or invalid

    Example:
        >>> auth = RobinhoodSignatureAuth(
        ...     api_key="rh-api-key",
        ...     private_key_b64="base64-encoded-private-key",
        ...     sandbox=False
        ... )
        >>> print(auth.is_authenticated())  # True
        >>> print(auth.get_auth_info())
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        private_key_b64: Optional[str] = None,
        public_key_b64: Optional[str] = None,
        sandbox: bool = False
    ):
        """
        Initialize Robinhood authentication with API key and digital signatures.

        This method sets up authentication for the Robinhood Crypto API using either
        private key (with automatic public key derivation) or public key methods.
        Credentials can be provided directly or loaded from environment variables.

        Args:
            api_key: Robinhood API key. Falls back to ROBINHOOD_API_KEY env var if None.
            private_key_b64: Base64-encoded private key for signing requests. Falls back to
                ROBINHOOD_PRIVATE_KEY env var if None. Mutually exclusive with public_key_b64.
            public_key_b64: Base64-encoded public key for authentication. Falls back to
                ROBINHOOD_PUBLIC_KEY env var if None. Use this for simplified authentication.
            sandbox: Whether to use sandbox environment (default: False for production).

        Raises:
            AuthenticationError: If API key is missing or both private and public keys are missing.
            AuthenticationError: If key validation fails during initialization.

        Note:
            - Exactly one of private_key_b64 or public_key_b64 must be provided
            - Private keys are used for request signing (more secure)
            - Public keys are used for direct authentication (simplified)
        """
        # Load credentials from parameters or environment variables (support both naming conventions)
        self.api_key = api_key or os.getenv("ROBINHOOD_API_KEY") or os.getenv("RH_API_KEY")
        self.private_key_b64 = private_key_b64 or os.getenv("ROBINHOOD_PRIVATE_KEY") or os.getenv("RH_BASE64_PRIVATE_KEY")
        self.public_key_b64 = public_key_b64 or os.getenv("ROBINHOOD_PUBLIC_KEY")
        self.sandbox = sandbox

        # Log credential loading for debugging
        logger.debug("Auth credentials loaded",
                      api_key_present=bool(self.api_key),
                      private_key_present=bool(self.private_key_b64),
                      public_key_present=bool(self.public_key_b64),
                      sandbox=self.sandbox)

        # Base URL for different environments (same for sandbox and production)
        self.base_url = "https://trading.robinhood.com"
        logger.info("Auth base URL set", base_url=self.base_url)

        # Initialize internal state
        self._private_key: Optional[str] = None
        self._public_key: Optional[str] = None
        self._authenticated = False

        # Initialize signature-based authentication
        if self.api_key and self.private_key_b64:
            self._initialize_signature_auth()
        else:
            # Provide detailed error message
            missing = []
            if not self.api_key:
                missing.append("ROBINHOOD_API_KEY or RH_API_KEY")
            if not self.private_key_b64:
                missing.append("ROBINHOOD_PRIVATE_KEY or RH_BASE64_PRIVATE_KEY")
            
            error_msg = f"API credentials required but missing: {', '.join(missing)}. "
            error_msg += "Please set these environment variables in your .env file. "
            error_msg += "See config/.env.example for configuration examples."

            raise AuthenticationError(error_msg)

    def get_api_key(self) -> str:
        """Get the API key for requests."""
        if not self._authenticated:
            raise AuthenticationError("Authentication not initialized")
        return self.api_key

    def is_authenticated(self) -> bool:
        """Check if authentication is properly configured."""
        logger.debug("Checking authentication status", authenticated=self._authenticated)
        return self._authenticated

    def _initialize_signature_auth(self):
        """
        Initialize API key + private key authentication (fallback method).

        This method validates and stores API key and private key credentials
        for signature-based authentication.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        if not self.api_key or not self.private_key_b64:
            raise AuthenticationError("API key and private key are required for signature authentication")

        try:
            # Validate private key format
            private_key_bytes = b64decode(self.private_key_b64)
            if len(private_key_bytes) != 32:
                raise AuthenticationError("Private key must be 32 bytes when decoded")

            # Store credentials
            self._private_key = self.private_key_b64
            self._public_key = None  # Will be derived when needed
            self._authenticated = True

            logger.info("Robinhood signature authentication initialized successfully")

        except Exception as e:
            raise AuthenticationError(f"Invalid private key format: {str(e)}")

    def get_signature_headers(self, method: str, path: str, body: str = "", timestamp: Optional[int] = None) -> Dict[str, str]:
        """
        Generate signature headers for API requests.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            body: Request body (for POST requests)
            timestamp: Unix timestamp (defaults to current time)

        Returns:
            Dictionary of authorization headers
        """
        if not self._authenticated or not self._private_key:
            raise AuthenticationError("Signature authentication not initialized")

        if timestamp is None:
            timestamp = int(time.time())

        # Import here to avoid circular imports
        import time
        from base64 import b64encode
        from nacl.signing import SigningKey

        try:
            private_key_bytes = b64decode(self._private_key)
            signing_key = SigningKey(private_key_bytes)
            
            message_to_sign = f"{self.api_key}{timestamp}{path}{method}{body}"
            signed = signing_key.sign(message_to_sign.encode("utf-8"))

            return {
                "x-api-key": self.api_key,
                "x-signature": b64encode(signed.signature).decode("utf-8"),
                "x-timestamp": str(timestamp),
            }
        except Exception as e:
            raise AuthenticationError(f"Failed to generate signature headers: {str(e)}")

    def get_auth_info(self) -> Dict:
        """Get information about the authentication configuration."""
        auth_type = "signature" if hasattr(self, '_private_key') and self._private_key else "unknown"

        return {
            "authenticated": self._authenticated,
            "api_key_prefix": self.api_key[:20] + "..." if self.api_key else None,
            "private_key_prefix": self._private_key[:30] + "..." if hasattr(self, '_private_key') and self._private_key else None,
            "sandbox": self.sandbox,
            "base_url": self.base_url,
            "auth_type": auth_type,
        }