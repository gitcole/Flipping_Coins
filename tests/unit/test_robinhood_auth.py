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
        assert auth_prod.base_url == "https://trading.robinhood.com"

        # Test sandbox
        auth_sandbox = RobinhoodSignatureAuth(
            api_key="test_key",
            public_key_b64="test_public_key",
            sandbox=True
        )
        assert auth_sandbox.base_url == "https://trading.robinhood.com"  # Same as production

    def test_authentication_edge_cases_empty_keys(self):
        """Test authentication with empty or whitespace-only keys."""
        # Test with empty API key
        with pytest.raises(AuthenticationError, match="API key is required"):
            RobinhoodSignatureAuth(
                api_key="",
                public_key_b64="test_public_key"
            )

        # Test with whitespace-only API key
        with pytest.raises(AuthenticationError, match="API key is required"):
            RobinhoodSignatureAuth(
                api_key="   ",
                public_key_b64="test_public_key"
            )

    def test_authentication_edge_cases_none_values(self):
        """Test authentication with None values."""
        # Test with None API key
        with pytest.raises(AuthenticationError, match="API key is required"):
            RobinhoodSignatureAuth(
                api_key=None,
                public_key_b64="test_public_key"
            )

        # Test with None public key
        with pytest.raises(AuthenticationError, match="Either private key or public key is required"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                public_key_b64=None
            )

    def test_authentication_key_validation_malformed_base64(self):
        """Test authentication with malformed base64 keys."""
        # Test with invalid base64 private key
        with pytest.raises(AuthenticationError, match="Failed to initialize private key"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                private_key_b64="not_valid_base64!@#$%"
            )

        # Test with invalid base64 public key
        with pytest.raises(AuthenticationError, match="Failed to initialize public key"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                public_key_b64="not_valid_base64!@#$%"
            )

    def test_authentication_key_validation_truncated_keys(self):
        """Test authentication with truncated or incomplete keys."""
        # Test with very short private key
        with pytest.raises(AuthenticationError, match="Failed to initialize private key"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                private_key_b64="short"
            )

        # Test with very short public key
        with pytest.raises(AuthenticationError, match="Failed to initialize public key"):
            RobinhoodSignatureAuth(
                api_key="test_key",
                public_key_b64="short"
            )

    def test_authentication_state_transitions(self):
        """Test authentication state transitions."""
        # Start with unauthenticated state
        auth = RobinhoodSignatureAuth.__new__(RobinhoodSignatureAuth)
        auth._authenticated = False

        # Should not be authenticated initially
        assert auth.is_authenticated() is False

        # Initialize properly
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        auth.__init__(
            api_key="test_key",
            private_key_b64=private_key_b64
        )

        # Should now be authenticated
        assert auth.is_authenticated() is True

    def test_authentication_info_completeness(self):
        """Test that auth info contains all expected fields."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
        public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key="test_api_key",
            private_key_b64=private_key_b64,
            sandbox=True
        )

        auth_info = auth.get_auth_info()

        # Check all required fields are present
        required_fields = [
            'authenticated', 'api_key_prefix', 'private_key_prefix',
            'public_key_prefix', 'sandbox', 'auth_type', 'base_url'
        ]

        for field in required_fields:
            assert field in auth_info, f"Missing required field: {field}"

        # Check field types
        assert isinstance(auth_info['authenticated'], bool)
        assert isinstance(auth_info['api_key_prefix'], str)
        assert isinstance(auth_info['sandbox'], bool)
        assert isinstance(auth_info['auth_type'], str)
        assert isinstance(auth_info['base_url'], str)

    def test_authentication_key_derivation_consistency(self):
        """Test that key derivation is consistent across instances."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
        expected_public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        # Create multiple auth instances with same private key
        auth1 = RobinhoodSignatureAuth(api_key="test1", private_key_b64=private_key_b64)
        auth2 = RobinhoodSignatureAuth(api_key="test2", private_key_b64=private_key_b64)

        # Both should derive the same public key
        assert auth1.get_public_key() == auth2.get_public_key()
        assert auth1.get_public_key() == expected_public_key_b64

    def test_authentication_error_message_quality(self):
        """Test that error messages are informative and helpful."""
        # Test missing API key error
        with pytest.raises(AuthenticationError) as exc_info:
            RobinhoodSignatureAuth()

        error_msg = str(exc_info.value)
        assert "API key" in error_msg
        assert "required" in error_msg.lower()

        # Test missing keys error
        with pytest.raises(AuthenticationError) as exc_info:
            RobinhoodSignatureAuth(api_key="test_key")

        error_msg = str(exc_info.value)
        assert "private key" in error_msg.lower() or "public key" in error_msg.lower()

    def test_authentication_configuration_persistence(self):
        """Test that authentication configuration persists correctly."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        original_config = {
            'api_key': 'persistent_test_key',
            'private_key_b64': private_key_b64,
            'sandbox': True
        }

        auth = RobinhoodSignatureAuth(**original_config)

        # Verify initial configuration
        assert auth.api_key == original_config['api_key']
        assert auth.get_private_key() == original_config['private_key_b64']
        assert auth.sandbox == original_config['sandbox']

        # Verify configuration persists through auth info
        auth_info = auth.get_auth_info()
        assert auth_info['api_key_prefix'] == original_config['api_key']
        assert auth_info['sandbox'] == original_config['sandbox']

    def test_authentication_with_special_characters(self):
        """Test authentication with special characters in API keys."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        # Test with special characters in API key
        special_api_key = "test_key_with_special_chars!@#$%^&*()"
        auth = RobinhoodSignatureAuth(
            api_key=special_api_key,
            private_key_b64=private_key_b64
        )

        assert auth.is_authenticated() is True
        assert auth.get_api_key() == special_api_key
        assert auth.get_auth_info()['api_key_prefix'] == special_api_key

    def test_authentication_key_length_validation(self):
        """Test authentication with various key lengths."""
        # Test with very long API key
        long_api_key = "a" * 1000
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        auth = RobinhoodSignatureAuth(
            api_key=long_api_key,
            private_key_b64=private_key_b64
        )

        assert auth.is_authenticated() is True
        assert auth.get_api_key() == long_api_key

    def test_authentication_multiple_initialization_attempts(self):
        """Test multiple initialization attempts."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        # First initialization should work
        auth = RobinhoodSignatureAuth(
            api_key="test_key",
            private_key_b64=private_key_b64
        )

        assert auth.is_authenticated() is True

        # Multiple initializations should not cause issues
        # (In practice, re-initialization would create a new instance)
        auth2 = RobinhoodSignatureAuth(
            api_key="test_key2",
            private_key_b64=private_key_b64
        )

        assert auth2.is_authenticated() is True
        assert auth2.get_api_key() == "test_key2"