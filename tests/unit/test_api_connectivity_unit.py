"""
Comprehensive unit tests for API connectivity with enhanced mocking.

This module provides comprehensive unit tests that complement the integration tests,
focusing on edge cases, error scenarios, and detailed mocking of API behaviors.

Tests include:
- Enhanced error scenario mocking
- Network condition simulation
- Rate limiting and retry logic
- Response format validation
- Performance characteristic testing
"""
import asyncio
import json
import pytest
import socket
import ssl
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from base64 import b64encode
from ecdsa import SigningKey

from tests.utils.base_test import UnitTestCase
from tests.mocks.api_mocks import (
    RobinhoodApiMock,
    EnhancedApiMock,
    MockScenarioBuilder,
    ScenarioMock
)
from tests.integration.test_utils import (
    TestEnvironmentManager,
    APIResponseValidator,
    NetworkConnectivityTester,
    PerformanceMonitor,
    RateLimitTester
)

from src.core.api.robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from src.core.api.exceptions import (
    AuthenticationError,
    RateLimitError,
    NetworkError,
    APIError
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TestEnhancedMockingScenarios(UnitTestCase):
    """Test enhanced mocking scenarios for comprehensive API testing."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.mock_api = EnhancedApiMock()
        self.performance_monitor = PerformanceMonitor()
        self.rate_limiter = RateLimitTester()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_mock_error_patterns(self):
        """Test that mock API can simulate different error patterns."""
        # Setup error pattern for specific endpoint
        self.mock_api.set_error_pattern("/api/quotes", "timeout", frequency=1.0)

        # Mock the request method to use our enhanced API
        with patch('src.core.api.robinhood.client.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "success"}
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            # Test that error pattern is applied
            should_error = self.mock_api.should_error_for_endpoint("/api/quotes")
            assert should_error, "Should error for configured endpoint"

            error_type = self.mock_api.get_error_for_endpoint("/api/quotes")
            assert error_type == "timeout", "Should return configured error type"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_mock_network_conditions(self):
        """Test network condition simulation."""
        # Setup network condition
        self.mock_api.set_network_condition("high_latency", duration=1.0)

        # Test that network condition affects response time
        start_time = time.time()
        await self.mock_api._simulate_enhanced_delay(0.1)
        actual_time = time.time() - start_time

        # Should have additional latency
        assert actual_time > 0.1, "Network condition should add latency"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_mock_rate_limiting_simulation(self):
        """Test rate limiting simulation."""
        # Test rate limit exceeded scenario
        with pytest.raises(Exception):  # Should raise RateLimitError
            await self.mock_api.simulate_rate_limit_exceeded()

        # Check rate limit history
        history = self.mock_api.get_rate_limit_history()
        assert len(history) > 0, "Should record rate limit events"
        assert history[-1]['event'] == 'rate_limit_exceeded', "Should record correct event type"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_mock_malformed_response_simulation(self):
        """Test malformed response simulation."""
        # Test malformed JSON
        malformed_response = await self.mock_api.simulate_malformed_response()
        assert malformed_response == 'invalid json response {', "Should return malformed JSON"

        # Test empty response
        empty_response = await self.mock_api.simulate_empty_response()
        assert empty_response == "", "Should return empty response"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_mock_large_response_simulation(self):
        """Test large response simulation."""
        # Test large response (1MB)
        large_response = await self.mock_api.simulate_large_response(1.0)
        response_size = len(json.dumps(large_response))

        assert response_size > 1024 * 1024, "Should generate large response"
        assert "data" in large_response, "Should have expected structure"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_mock_scenario_builder(self):
        """Test scenario builder functionality."""
        builder = MockScenarioBuilder()

        scenario = (builder
                   .add_delay_step(0.5)
                   .add_error_step("timeout", "/api/test")
                   .add_rate_limit_step(5)
                   .build_scenario())

        assert len(scenario.steps) == 3, "Should have 3 steps"
        assert scenario.steps[0]['type'] == 'delay', "First step should be delay"
        assert scenario.steps[1]['type'] == 'error', "Second step should be error"
        assert scenario.steps[2]['type'] == 'rate_limit', "Third step should be rate limit"


class TestClientErrorHandling(UnitTestCase):
    """Test client error handling with comprehensive mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.mock_api = EnhancedApiMock()

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_client_timeout_handling(self):
        """Test client timeout handling."""
        client = RobinhoodClient(sandbox=True)
        client.config.timeout = 0.1  # Very short timeout

        # Mock slow response
        async def slow_request(*args, **kwargs):
            await asyncio.sleep(1.0)  # Longer than timeout
            return {"data": "success"}

        client.request = slow_request

        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await client.get_user()

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_client_retry_logic(self):
        """Test client retry logic."""
        client = RobinhoodClient(sandbox=True)
        client.config.max_retries = 2
        client.config.retry_delay = 0.1

        # Mock failing requests that eventually succeed
        call_count = 0

        async def failing_then_successful_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:
                raise Exception("Temporary failure")
            return {"data": "success"}

        client.request = failing_then_successful_request

        # Should succeed after retries
        result = await client.get_user()
        assert result["data"] == "success"
        assert call_count == 3, "Should have made 3 attempts (initial + 2 retries)"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_client_rate_limit_handling(self):
        """Test client rate limit handling."""
        client = RobinhoodClient(sandbox=True)
        client.config.rate_limit_per_second = 2

        # Mock rate limit response
        call_count = 0

        async def rate_limited_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:
                # Simulate rate limit error
                from src.core.api.exceptions import RateLimitError
                raise RateLimitError("Rate limit exceeded", retry_after=1)
            return {"data": "success"}

        client.request = rate_limited_request

        # Should handle rate limiting
        result = await client.get_user()
        assert result["data"] == "success"
        assert call_count == 3, "Should have made multiple attempts with rate limit handling"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_client_authentication_error_handling(self):
        """Test client authentication error handling."""
        client = RobinhoodClient(sandbox=True)
        client.config.api_key = "invalid_key"

        # Mock authentication failure
        async def auth_failure_request(*args, **kwargs):
            from src.core.api.exceptions import AuthenticationError
            raise AuthenticationError("Invalid API key")

        client.request = auth_failure_request

        # Should handle authentication error
        with pytest.raises(AuthenticationError):
            await client.get_user()

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_client_malformed_response_handling(self):
        """Test client handling of malformed responses."""
        client = RobinhoodClient(sandbox=True)

        # Mock malformed JSON response
        async def malformed_response_request(*args, **kwargs):
            return "invalid json response {"

        client.request = malformed_response_request

        # Should handle malformed response gracefully
        result = await client.get_user()
        # Client should handle this gracefully or return None/error
        assert result is not None  # Client should attempt to handle malformed responses


class TestNetworkConnectivityMocking(UnitTestCase):
    """Test network connectivity scenarios with mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    @pytest.mark.unit
    @pytest.mark.mock
    @pytest.mark.network
    def test_dns_resolution_mock(self):
        """Test DNS resolution with mocked responses."""
        with patch('socket.gethostbyname') as mock_gethostbyname:
            # Test successful DNS resolution
            mock_gethostbyname.return_value = "192.168.1.1"

            tester = NetworkConnectivityTester()
            result = asyncio.run(tester.test_dns_resolution("api.robinhood.com"))
            assert result is True, "DNS resolution should succeed"

            mock_gethostbyname.assert_called_once_with("api.robinhood.com")

            # Test DNS failure
            mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")

            result = asyncio.run(tester.test_dns_resolution("invalid-host.example"))
            assert result is False, "DNS resolution should fail for invalid host"

    @pytest.mark.unit
    @pytest.mark.mock
    @pytest.mark.network
    def test_tcp_connection_mock(self):
        """Test TCP connection with mocked responses."""
        with patch('asyncio.open_connection') as mock_open_connection:
            # Test successful connection
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open_connection.return_value = (mock_reader, mock_writer)

            tester = NetworkConnectivityTester()
            result = asyncio.run(tester.test_tcp_connection("api.robinhood.com", 443))
            assert result is True, "TCP connection should succeed"

            # Test connection failure
            mock_open_connection.side_effect = OSError("Connection refused")

            result = asyncio.run(tester.test_tcp_connection("127.0.0.1", 99999))
            assert result is False, "TCP connection should fail for invalid port"

    @pytest.mark.unit
    @pytest.mark.mock
    @pytest.mark.network
    def test_ssl_certificate_mock(self):
        """Test SSL certificate validation with mocked responses."""
        with patch('ssl.create_default_context') as mock_ssl_context:
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context

            with patch('socket.socket') as mock_socket:
                mock_sock = MagicMock()
                mock_socket.return_value = mock_sock

                # Mock successful certificate validation
                mock_sock.getpeercert.return_value = {
                    'subject': ((('commonName', 'api.robinhood.com'),),),
                    'issuer': ((('organizationName', 'DigiCert Inc'),),),
                    'notBefore': 'Jan 01 00:00:00 2023 GMT',
                    'notAfter': 'Jan 01 00:00:00 2025 GMT',
                    'serialNumber': '123456789'
                }

                tester = NetworkConnectivityTester()
                result = asyncio.run(tester.test_ssl_certificate("api.robinhood.com"))

                assert result['valid'] is True, "SSL certificate should be valid"
                assert 'subject' in result, "Should have certificate subject"
                assert 'not_after' in result, "Should have expiration date"


class TestPerformanceMocking(UnitTestCase):
    """Test performance scenarios with mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.performance_monitor = PerformanceMonitor()

    @pytest.mark.unit
    @pytest.mark.mock
    @pytest.mark.performance
    async def test_response_time_measurement(self):
        """Test response time measurement accuracy."""
        client = RobinhoodClient(sandbox=True)

        # Mock request with known delay
        async def mock_request_with_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {"data": "test"}

        client.request = mock_request_with_delay

        # Measure response time
        start_time = time.time()
        result = await client.get_user()
        actual_time = time.time() - start_time

        # Should be close to expected delay
        assert 0.09 < actual_time < 0.15, f"Response time should be ~100ms, got {actual_time:.3f}s"
        assert result["data"] == "test", "Should return expected data"

    @pytest.mark.unit
    @pytest.mark.mock
    @pytest.mark.performance
    async def test_concurrent_request_performance(self):
        """Test performance under concurrent load."""
        client = RobinhoodClient(sandbox=True)

        async def mock_concurrent_request(i: int):
            await asyncio.sleep(0.01 * i)  # Stagger requests
            return await client.get_instruments()

        # Mock the request method
        async def mock_request(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms per request
            return {"results": [{"id": "test", "symbol": "BTC"}]}

        client.request = mock_request

        # Make concurrent requests
        num_requests = 5
        start_time = time.time()

        tasks = [mock_concurrent_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Should complete all requests
        assert len(results) == num_requests, "Should complete all concurrent requests"

        # Should complete within reasonable time (allowing for staggering)
        expected_min_time = 0.05 * num_requests  # If perfectly parallel
        expected_max_time = 0.05 + 0.01 * (num_requests - 1)  # With staggering

        assert expected_min_time <= total_time <= expected_max_time * 1.5, \
            f"Concurrent requests took {total_time:.3f}s, expected ~{expected_max_time:.3f}s"


class TestEdgeCaseScenarios(UnitTestCase):
    """Test edge cases and unusual scenarios."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_empty_response_handling(self):
        """Test handling of empty responses."""
        with patch('src.core.api.robinhood.client.httpx.AsyncClient') as mock_client:
            # Mock empty response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_response.json.side_effect = json.JSONDecodeError("Empty response", "", 0)
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            # Client should handle empty response gracefully
            client = RobinhoodClient(sandbox=True)

            async def test_empty_response():
                return await client.get_user()

            result = self.run_async(test_empty_response())
            # Should handle empty response without crashing
            assert result is not None

    @pytest.mark.unit
    @pytest.mark.mock
    def test_unicode_response_handling(self):
        """Test handling of Unicode responses."""
        with patch('src.core.api.robinhood.client.httpx.AsyncClient') as mock_client:
            # Mock response with Unicode characters
            unicode_data = {"message": "Test with émojis 🚀 and ñoñó characters"}
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = unicode_data
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            client = RobinhoodClient(sandbox=True)

            async def test_unicode_response():
                return await client.get_user()

            result = self.run_async(test_unicode_response())
            assert result == unicode_data, "Should handle Unicode response correctly"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_very_large_response_handling(self):
        """Test handling of very large responses."""
        with patch('src.core.api.robinhood.client.httpx.AsyncClient') as mock_client:
            # Mock very large response (5MB)
            large_data = {"data": "x" * (5 * 1024 * 1024)}
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = large_data
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            client = RobinhoodClient(sandbox=True)

            async def test_large_response():
                return await client.get_user()

            # Should handle large response without memory issues
            result = self.run_async(test_large_response())
            assert "data" in result, "Should handle large response"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_response_with_null_values(self):
        """Test handling of responses with null values."""
        with patch('src.core.api.robinhood.client.httpx.AsyncClient') as mock_client:
            # Mock response with null values
            null_data = {
                "id": None,
                "name": "test",
                "data": null,
                "active": False
            }
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = null_data
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            client = RobinhoodClient(sandbox=True)

            async def test_null_response():
                return await client.get_user()

            result = self.run_async(test_null_response())
            assert result == null_data, "Should handle null values correctly"


class TestRateLimitMocking(UnitTestCase):
    """Test rate limiting scenarios with comprehensive mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.rate_limiter = RateLimitTester(max_requests=5, time_window=1.0)

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_rate_limit_enforcement(self):
        """Test rate limit enforcement."""
        # Make requests up to the limit
        for i in range(5):
            can_request = await self.rate_limiter.make_request()
            assert can_request, f"Request {i+1} should be allowed"

        # Next request should be rate limited
        can_request = await self.rate_limiter.make_request()
        assert not can_request, "Should be rate limited after reaching limit"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_rate_limit_window_reset(self):
        """Test rate limit window reset."""
        # Fill up rate limit
        for i in range(5):
            await self.rate_limiter.make_request()

        assert self.rate_limiter.is_rate_limited(), "Should be rate limited"

        # Wait for window to reset
        await asyncio.sleep(1.1)  # Slightly longer than window

        # Should be able to make requests again
        can_request = await self.rate_limiter.make_request()
        assert can_request, "Should be able to make requests after window reset"

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_rate_limit_with_delays(self):
        """Test rate limiting with request delays."""
        # Make requests with delays
        for i in range(3):
            can_request = await self.rate_limiter.make_request(delay=0.1)
            assert can_request, f"Request {i+1} should be allowed"

        # Check current count
        current_count = self.rate_limiter.get_request_count()
        assert current_count == 3, "Should have made 3 requests"

        # Should not be rate limited yet
        assert not self.rate_limiter.is_rate_limited(), "Should not be rate limited"


class TestAuthenticationEdgeCases(UnitTestCase):
    """Test authentication edge cases with comprehensive mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_auth_with_expired_keys(self):
        """Test authentication with expired or invalid keys."""
        # Test with obviously invalid key format
        with pytest.raises(Exception):  # Should raise AuthenticationError
            auth = RobinhoodSignatureAuth(
                api_key="expired_key",
                public_key_b64="invalid_key_format"
            )

    @pytest.mark.unit
    @pytest.mark.mock
    def test_auth_key_derivation_edge_cases(self):
        """Test key derivation edge cases."""
        # Test that public key derivation is deterministic
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        # Create multiple auth instances
        auth1 = RobinhoodSignatureAuth(api_key="test1", private_key_b64=private_key_b64)
        auth2 = RobinhoodSignatureAuth(api_key="test2", private_key_b64=private_key_b64)

        # Should derive same public key
        assert auth1.get_public_key() == auth2.get_public_key(), "Key derivation should be deterministic"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_auth_info_completeness_edge_cases(self):
        """Test auth info completeness in edge cases."""
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')

        # Test with minimal configuration
        auth = RobinhoodSignatureAuth(
            api_key="test",
            private_key_b64=private_key_b64
        )

        auth_info = auth.get_auth_info()

        # Should have all required fields even with minimal config
        required_fields = ['authenticated', 'api_key_prefix', 'auth_type', 'sandbox']
        for field in required_fields:
            assert field in auth_info, f"Missing required field: {field}"


class TestClientConfigurationMocking(UnitTestCase):
    """Test client configuration scenarios with mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_client_config_validation(self):
        """Test client configuration validation."""
        # Test with invalid configuration
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):  # Should raise ConfigurationError
                client = RobinhoodClient()
                # Client should attempt to load config and fail

    @pytest.mark.unit
    @pytest.mark.mock
    def test_client_initialization_with_mocked_config(self):
        """Test client initialization with mocked configuration."""
        with patch('src.core.api.robinhood.client.get_settings') as mock_get_settings:
            # Mock settings
            mock_settings = Mock()
            mock_settings.robinhood.api_key = "mock_api_key"
            mock_settings.robinhood.public_key = "mock_public_key"
            mock_settings.robinhood.sandbox = True
            mock_get_settings.return_value = mock_settings

            client = RobinhoodClient(sandbox=True)

            assert client.config.api_key == "mock_api_key"
            assert client.config.public_key == "mock_public_key"
            assert client.config.sandbox is True


class TestResponseValidationMocking(UnitTestCase):
    """Test response validation with comprehensive mocking."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.validator = APIResponseValidator()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_json_response_validation(self):
        """Test JSON response validation."""
        # Test valid response
        valid_response = {"id": "test", "name": "Test Item"}
        result = self.validator.validate_json_response(valid_response, ["id", "name"])
        assert result == valid_response, "Should return valid response"

        # Test missing required keys
        with pytest.raises(AssertionError, match="Missing expected keys"):
            self.validator.validate_json_response({"id": "test"}, ["id", "name"])

    @pytest.mark.unit
    @pytest.mark.mock
    def test_response_time_validation(self):
        """Test response time validation."""
        # Test acceptable response time
        self.validator.validate_response_time(0.5, max_time=1.0)  # Should not raise

        # Test excessive response time
        with pytest.raises(AssertionError, match="exceeds maximum"):
            self.validator.validate_response_time(2.0, max_time=1.0)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_schema_compliance_validation(self):
        """Test schema compliance validation."""
        # Test valid schema compliance
        data = {"name": "test", "count": 5}
        schema = {
            "name": {"type": "string", "required": True},
            "count": {"type": "number", "required": False}
        }

        self.validator.validate_schema_compliance(data, schema)  # Should not raise

        # Test schema violation
        invalid_data = {"name": 123}  # name should be string
        invalid_schema = {"name": {"type": "string", "required": True}}

        with pytest.raises(AssertionError, match="expected string"):
            self.validator.validate_schema_compliance(invalid_data, invalid_schema)


class TestErrorPropagationMocking(UnitTestCase):
    """Test error propagation through the system."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_error_chain_propagation(self):
        """Test that errors propagate correctly through the call chain."""
        client = RobinhoodClient(sandbox=True)

        # Create a chain of failing operations
        async def failing_operation_1():
            raise NetworkError("Network connection failed")

        async def failing_operation_2():
            try:
                await failing_operation_1()
            except NetworkError as e:
                raise APIError(f"API operation failed: {e}")

        async def failing_operation_3():
            try:
                await failing_operation_2()
            except APIError as e:
                raise Exception(f"Client operation failed: {e}")

        client.request = failing_operation_3

        # Should propagate the original error through the chain
        with pytest.raises(Exception, match="Client operation failed"):
            await client.get_user()

    @pytest.mark.unit
    @pytest.mark.mock
    async def test_error_context_preservation(self):
        """Test that error context is preserved."""
        client = RobinhoodClient(sandbox=True)

        # Mock request that provides context
        async def contextual_error_request(*args, **kwargs):
            error = APIError("API rate limit exceeded")
            error.endpoint = "/api/quotes"
            error.retry_after = 60
            raise error

        client.request = contextual_error_request

        # Should preserve error context
        with pytest.raises(APIError) as exc_info:
            await client.get_quotes(["BTC"])

        error = exc_info.value
        assert hasattr(error, 'endpoint'), "Should preserve endpoint context"
        assert hasattr(error, 'retry_after'), "Should preserve retry_after context"


class TestMockIntegrationWithRealComponents(UnitTestCase):
    """Test integration of mocks with real components."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_mock_integration_with_auth_component(self):
        """Test that mocks integrate properly with authentication components."""
        # Generate real test keys
        private_key = SigningKey.generate()
        private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
        public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

        # Test with real auth component and mock API
        auth = RobinhoodSignatureAuth(
            api_key="test_integration_key",
            private_key_b64=private_key_b64
        )

        assert auth.is_authenticated(), "Auth should work with real keys"
        assert auth.get_auth_info()['auth_type'] == 'private_key', "Should use private key auth"

        # Mock API should work with real auth
        mock_api = RobinhoodApiMock()
        # In real implementation, auth would be used with mock API
        # This tests the integration boundary

    @pytest.mark.unit
    @pytest.mark.mock
    def test_mock_configuration_integration(self):
        """Test mock integration with configuration system."""
        with patch('src.core.api.robinhood.client.get_settings') as mock_get_settings:
            # Mock configuration
            mock_settings = Mock()
            mock_settings.robinhood.api_key = "config_test_key"
            mock_settings.robinhood.public_key = "config_test_public_key"
            mock_settings.robinhood.sandbox = False
            mock_get_settings.return_value = mock_settings

            # Client should use mocked configuration
            client = RobinhoodClient(sandbox=False)

            assert client.config.api_key == "config_test_key"
            assert client.config.public_key == "config_test_public_key"
            assert client.config.sandbox is False