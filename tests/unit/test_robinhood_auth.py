"""
Unit tests for Robinhood Signature-Based Authentication.

Tests cover signature authentication with both private and public keys,
key validation, error handling, and integration with Robinhood API client.
"""
import os
import pytest
from unittest.mock import Mock, patch
from base64 import b64encode, b64decode
from ecdsa import SigningKey

from tests.utils.base_test import UnitTestCase
from src.core.api.robinhood.auth import (
    RobinhoodSignatureAuth,
    AuthenticationError
)


class TestRobinhoodSignatureAuth(UnitTestCase):
    """Test cases for RobinhoodSignatureAuth class."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    def test_private_key_auth_initialization(self):
        """Test initialization with private key."""
        # Generate a test private key
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_api_key",
            private_key_b64=private_key_b64,
            sandbox=False
        )

        assert auth.is_authenticated() is True
        assert auth.api_key == "test_api_key"
        assert auth.get_api_key() == "test_api_key"
        assert auth.get_private_key() == private_key_b64
        assert auth.get_public_key() is not None
        assert auth.get_public_key() != private_key_b64

        # Check auth info
        auth_info = auth.get_auth_info()
        assert auth_info["authenticated"] is True
        assert auth_info["api_key_prefix"] == "test_api_key"
        assert auth_info["private_key_prefix"] is not None
        assert auth_info["public_key_prefix"] is not None
        assert auth_info["sandbox"] is False
        assert auth_info["auth_type"] == "private_key"

    def test_public_key_auth_initialization(self):
        """Test initialization with public key."""
        # Generate a test private key and derive public key
        private_key = SigningKey.generate()
        public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_api_key",
            public_key_b64=public_key_b64,
            sandbox=True
        )

        assert auth.is_authenticated() is True
        assert auth.api_key == "test_api_key"
        assert auth.get_api_key() == "test_api_key"
        assert auth.get_public_key() == public_key_b64

        # Check auth info
        auth_info = auth.get_auth_info()
        assert auth_info["authenticated"] is True
        assert auth_info["api_key_prefix"] == "test_api_key"
        assert auth_info["public_key_prefix"] is not None
        assert auth_info["private_key_prefix"] is None
        assert auth_info["sandbox"] is True
        assert auth_info["auth_type"] == "public_key"

    def test_initialization_from_environment(self):
        """Test initialization from environment variables."""
        with patch.dict(os.environ, {
            "ROBINHOOD_API_KEY": "env_api_key",
            "ROBINHOOD_PUBLIC_KEY": "env_public_key",
            "ROBINHOOD_SANDBOX": "true"
        }, clear=True):
            auth = RobinhoodSignatureAuth()

            assert auth.is_authenticated() is True
            assert auth.api_key == "env_api_key"
            assert auth.get_public_key() == "env_public_key"
            assert auth.sandbox is True

    def test_initialization_no_api_key(self):
        """Test initialization without API key."""
        with pytest.raises(AuthenticationError, match="API key is required"):
            RobinhoodSignatureAuth()

    def test_initialization_no_keys(self):
        """Test initialization without any keys."""
        with pytest.raises(AuthenticationError, match="Either private key or public key is required"):
            RobinhoodSignatureAuth(api_key="test_key")

    def test_initialization_invalid_private_key(self):
        """Test initialization with invalid private key."""
        with pytest.raises(AuthenticationError, match="Failed to initialize private key"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                private_key_b64="invalid_key"
            )

    def test_initialization_invalid_public_key(self):
        """Test initialization with invalid public key."""
        with pytest.raises(AuthenticationError, match="Failed to initialize public key"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                public_key_b64="invalid_key"
            )

    def test_get_api_key_not_authenticated(self):
        """Test getting API key when not authenticated."""
        # Create auth instance without proper initialization
        auth = RobinhoodSignatureAuth.__new__(RobinhoodSignatureAuth)
        auth._authenticated = False

        with pytest.raises(AuthenticationError, match="Authentication not initialized"):
            auth.get_api_key()

    def test_get_private_key_not_available(self):
        """Test getting private key when not available."""
        # Generate public key only
        private_key = SigningKey.generate()
        public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_key",
            public_key_b64=public_key_b64
        )

        with pytest.raises(AuthenticationError, match="Private key not available"):
            auth.get_private_key()

    def test_get_public_key_not_available(self):
        """Test getting public key when not available."""
        # Generate private key only
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_key",
            private_key_b64=private_key_b64
        )

        with pytest.raises(AuthenticationError, match="Public key not available"):
            # Try to get public key when only private key is available
            # This should work since public key is derived from private key
            public_key = auth.get_public_key()
            assert public_key is not None

    def test_private_key_derivation(self):
        """Test that public key is correctly derived from private key."""
        # Generate a known private key
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
        expected_public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_key",
            private_key_b64=private_key_b64
        )

        actual_public_key_b64 = auth.get_public_key()

        # The public key should match what we expect
        assert actual_public_key_b64 == expected_public_key_b64

    def test_both_keys_provided(self):
        """Test initialization when both keys are provided (should use private key)."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
        public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_key",
            private_key_b64=private_key_b64,
            public_key_b64=public_key_b64
        )

        # Should use private key authentication
        auth_info = auth.get_auth_info()
        assert auth_info["auth_type"] == "private_key"
        assert auth.get_private_key() == private_key_b64

    def test_base_url_configuration(self):
        """Test base URL configuration for different environments."""
        # Test production (default)
        auth_prod = RobinhoodSignatureAuth(
            api_key="test_key",
            public_key_b64="test_public_key"
        )
        assert auth_prod.base_url == "https://api.robinhood.com"

        # Test sandbox
        auth_sandbox = RobinhoodSignatureAuth(
            api_key="test_key",
            public_key_b64="test_public_key",
            sandbox=True
        )
        assert auth_sandbox.base_url == "https://api.robinhood.com"  # Same as production