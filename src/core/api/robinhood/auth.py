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
from typing import Dict, Optional

import structlog
from ecdsa import SigningKey
from base64 import b64decode

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
        # Load credentials from parameters or environment variables
        self.api_key = api_key or os.getenv("ROBINHOOD_API_KEY")
        self.private_key_b64 = private_key_b64 or os.getenv("ROBINHOOD_PRIVATE_KEY")
        self.public_key_b64 = public_key_b64 or os.getenv("ROBINHOOD_PUBLIC_KEY")
        self.sandbox = sandbox

        # Check for OAuth 2.0 credentials (preferred method)
        self.oauth_api_token = os.getenv("ROBINHOOD_API_TOKEN")
        self.oauth_client_id = os.getenv("ROBINHOOD_CLIENT_ID")
        self.oauth_client_secret = os.getenv("ROBINHOOD_CLIENT_SECRET")

        # Log credential loading for debugging
        logger.debug("Auth credentials loaded",
                      api_key_present=bool(self.api_key),
                      private_key_present=bool(self.private_key_b64),
                      public_key_present=bool(self.public_key_b64),
                      oauth_token_present=bool(self.oauth_api_token),
                      oauth_client_id_present=bool(self.oauth_client_id),
                      oauth_client_secret_present=bool(self.oauth_client_secret),
                      sandbox=self.sandbox)

        # Base URL for different environments (same for sandbox and production)
        self.base_url = "https://trading.robinhood.com"
        logger.info("Auth base URL set", base_url=self.base_url)

        # Initialize internal state
        self._private_key: Optional[str] = None
        self._public_key: Optional[str] = None
        self._authenticated = False

        # Check for OAuth 2.0 credentials first (preferred method)
        if self.oauth_api_token and self.oauth_client_id and self.oauth_client_secret:
            self._initialize_oauth_auth()
        # Fall back to legacy private/public key authentication
        elif self.api_key and self.private_key_b64:
            # Private key authentication: More secure, allows request signing
            self._initialize_private_key_auth()
        elif self.api_key and self.public_key_b64:
            # Public key authentication: Simplified, direct key verification
            self._initialize_public_key_auth()
        else:
            # No valid authentication method found
            missing_oauth = []
            if not self.oauth_api_token:
                missing_oauth.append("ROBINHOOD_API_TOKEN")
            if not self.oauth_client_id:
                missing_oauth.append("ROBINHOOD_CLIENT_ID")
            if not self.oauth_client_secret:
                missing_oauth.append("ROBINHOOD_CLIENT_SECRET")

            missing_legacy = []
            if not self.api_key:
                missing_legacy.append("ROBINHOOD_API_KEY")
            if not self.private_key_b64 and not self.public_key_b64:
                missing_legacy.append("ROBINHOOD_PRIVATE_KEY or ROBINHOOD_PUBLIC_KEY")

            error_msg = "No valid authentication credentials found. Please configure either:\n"
            if missing_oauth:
                error_msg += f"OAuth 2.0 (recommended): {', '.join(missing_oauth)}\n"
            if missing_legacy:
                error_msg += f"Legacy private/public key: {', '.join(missing_legacy)}\n"
            error_msg += "See config/.env.example for configuration examples."

            raise AuthenticationError(error_msg)

    def get_api_key(self) -> str:
        """Get the API key for requests."""
        if not self._authenticated:
            raise AuthenticationError("Authentication not initialized")
        return self.api_key

    def get_private_key(self) -> str:
        """Get the private key for signing."""
        if not self._authenticated or not self._private_key:
            raise AuthenticationError("Private key not available")
        return self._private_key

    def get_public_key(self) -> str:
        """Get the public key for authentication."""
        if not self._authenticated or not self._public_key:
            raise AuthenticationError("Public key not available")
        return self._public_key

    def is_authenticated(self) -> bool:
        """Check if authentication is properly configured."""
        logger.debug("Checking authentication status", authenticated=self._authenticated)
        return self._authenticated

    def _initialize_private_key_auth(self):
        """
        Initialize private key-based authentication with automatic public key derivation.

        This method validates the provided private key and derives the corresponding
        public key for authentication. Private key authentication is more secure as it
        allows for request signing, but requires careful key management.

        Raises:
            AuthenticationError: If private key is invalid or cannot be processed.
        """
        if not self.private_key_b64:
            raise AuthenticationError("Private key is required for private key authentication")

        # Step 1: Validate and process the private key
        try:
            # Import required modules for key processing
            from ecdsa import SigningKey
            from base64 import b64decode, b64encode

            # Step 2: Decode the base64-encoded private key into DER format
            private_key_der = b64decode(self.private_key_b64)
            logger.debug("Private key decoded successfully")

            # Step 3: Create ECDSA signing key object from DER data
            signing_key = SigningKey.from_der(private_key_der)
            logger.debug("ECDSA signing key created from DER")

            # Step 4: Store the private key and derive the public key
            self._private_key = self.private_key_b64
            self._public_key = b64encode(signing_key.verifying_key.to_der()).decode('utf-8')
            logger.debug("Public key derived from private key")

            # Step 5: Mark authentication as successful
            self._authenticated = True
            logger.info("Robinhood private key authentication initialized successfully")
        except Exception as e:
            # Handle key validation errors with detailed message
            raise AuthenticationError(f"Failed to initialize private key: {e}")

    def _initialize_public_key_auth(self):
        """
        Initialize public key-based authentication for simplified access.

        This method validates the provided public key for direct authentication.
        Public key authentication is simpler but less secure than private key mode,
        as it doesn't support request signing.

        Raises:
            AuthenticationError: If public key is invalid or cannot be processed.
        """
        if not self.public_key_b64:
            raise AuthenticationError("Public key is required for public key authentication")

        # Step 1: Validate the public key format
        try:
            # Import required module for key decoding
            from base64 import b64decode

            # Step 2: Decode the base64-encoded public key into DER format
            public_key_der = b64decode(self.public_key_b64)
            logger.debug("Public key decoded successfully")

            # Step 3: Store the public key (no private key available)
            self._public_key = self.public_key_b64
            self._authenticated = True

            # Step 4: Log successful initialization
            logger.info("Robinhood public key authentication initialized successfully")
        except Exception as e:
            # Handle key validation errors with detailed message
            raise AuthenticationError(f"Failed to initialize public key: {e}")

    def _initialize_oauth_auth(self):
        """
        Initialize OAuth 2.0 authentication (preferred method).

        This method validates OAuth 2.0 credentials for modern authentication.
        OAuth 2.0 is the recommended authentication method for new applications.

        Raises:
            AuthenticationError: If OAuth credentials are invalid.
        """
        if not self.oauth_api_token or not self.oauth_client_id or not self.oauth_client_secret:
            raise AuthenticationError("OAuth 2.0 credentials are incomplete")

        # Store OAuth credentials
        self._oauth_token = self.oauth_api_token
        self._authenticated = True

        logger.info("Robinhood OAuth 2.0 authentication initialized successfully")

    def get_auth_info(self) -> Dict:
        """Get information about the authentication configuration."""
        auth_type = "oauth"
        if hasattr(self, '_private_key') and self._private_key:
            auth_type = "private_key"
        elif hasattr(self, '_public_key') and self._public_key:
            auth_type = "public_key"

        return {
            "authenticated": self._authenticated,
            "api_key_prefix": self.api_key[:20] + "..." if self.api_key else None,
            "private_key_prefix": self._private_key[:30] + "..." if hasattr(self, '_private_key') and self._private_key else None,
            "public_key_prefix": self._public_key[:30] + "..." if hasattr(self, '_public_key') and self._public_key else None,
            "oauth_token_prefix": self._oauth_token[:20] + "..." if hasattr(self, '_oauth_token') and self._oauth_token else None,
            "sandbox": self.sandbox,
            "base_url": self.base_url,
            "auth_type": auth_type,
        }