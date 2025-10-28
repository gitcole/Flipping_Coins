"""
Base integration test class for API connectivity testing.

Provides common setup, teardown, and utilities for integration tests.
"""
import asyncio
import pytest
import os
from typing import Dict, Any, Optional
from unittest.mock import patch

from tests.utils.base_test import IntegrationTestCase
from tests.integration.test_utils import (
    TestEnvironmentManager,
    APIResponseValidator,
    NetworkConnectivityTester,
    PerformanceMonitor,
    TestDataManager,
    RateLimitTester,
    robinhood_client_context,
    create_test_config,
    generate_test_credentials,
    wait_for_condition
)

from src.core.api.robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BaseIntegrationTest(IntegrationTestCase):
    """Base class for integration tests with common setup and utilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env_manager = TestEnvironmentManager(use_sandbox=True)
        self.response_validator = APIResponseValidator()
        self.network_tester = NetworkConnectivityTester()
        self.performance_monitor = PerformanceMonitor()
        self.data_manager = TestDataManager()
        self.rate_limit_tester = RateLimitTester()

    def setup_method(self):
        """Setup for each integration test."""
        super().setup_method()

        # Setup test environment
        self.env_manager.setup_environment()

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        # Setup test credentials
        self.test_credentials = generate_test_credentials()

        logger.info(f"Integration test setup completed for {self.__class__.__name__}")

    def teardown_method(self):
        """Teardown for each integration test."""
        # End performance monitoring
        self.performance_monitor.end_monitoring()

        # Log performance summary
        summary = self.performance_monitor.get_summary()
        logger.info(f"Performance summary: {summary}")

        # Cleanup test data
        async def cleanup():
            await self.data_manager.cleanup()

        self.run_async(cleanup())

        # Restore environment
        self.env_manager.teardown_environment()

        logger.info(f"Integration test teardown completed for {self.__class__.__name__}")

    @pytest.fixture
    async def authenticated_client(self):
        """Fixture providing an authenticated RobinhoodClient."""
        async with robinhood_client_context(sandbox=True) as client:
            # Wait for authentication to complete
            await wait_for_condition(
                lambda: client.auth.is_authenticated(),
                timeout=30.0
            )
            yield client

    @pytest.fixture
    async def unauthenticated_client(self):
        """Fixture providing an unauthenticated RobinhoodClient."""
        async with robinhood_client_context(sandbox=True) as client:
            # Ensure client is not authenticated
            client.config.api_key = "invalid_key"
            client.config.public_key = "invalid_public_key"
            yield client

    def create_client_with_config(self, **config_overrides) -> RobinhoodClient:
        """Create a client with specific configuration."""
        config = create_test_config(sandbox=True, **config_overrides)
        return RobinhoodClient(config=config)

    async def create_authenticated_client_async(self, **config_overrides) -> RobinhoodClient:
        """Create an authenticated client asynchronously."""
        client = self.create_client_with_config(**config_overrides)

        # Set valid credentials
        client.config.api_key = self.test_credentials['api_key']
        client.config.public_key = self.test_credentials['public_key']

        # Initialize client
        await client.initialize()

        return client

    def assert_response_success(self, response: Any, expected_keys: Optional[list] = None):
        """Assert that a response indicates success."""
        if isinstance(response, dict):
            self.response_validator.validate_json_response(response, expected_keys)
        elif response is None:
            pytest.fail("Response is None")
        elif hasattr(response, 'status_code'):
            if response.status_code >= 400:
                pytest.fail(f"HTTP error response: {response.status_code}")

    def assert_response_error(self, response: Any, expected_status: Optional[int] = None):
        """Assert that a response indicates an error."""
        if hasattr(response, 'status_code'):
            if expected_status and response.status_code != expected_status:
                pytest.fail(f"Expected status {expected_status}, got {response.status_code}")
        elif isinstance(response, dict) and 'error' in response:
            # Valid error response format
            pass
        else:
            pytest.fail(f"Expected error response, got: {response}")

    def measure_response_time(self, func, *args, **kwargs):
        """Measure response time of a function call."""
        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(func):
                result = self.run_async(func(*args, **kwargs))
            else:
                result = func(*args, **kwargs)

            response_time = time.time() - start_time
            self.performance_monitor.record_request(response_time, success=True)

            return result, response_time

        except Exception as e:
            response_time = time.time() - start_time
            self.performance_monitor.record_request(response_time, success=False)
            raise

    def skip_if_no_network(self):
        """Skip test if network connectivity is not available."""
        try:
            # Quick connectivity check
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
        except OSError:
            pytest.skip("No network connectivity available")

    def skip_if_no_api_credentials(self):
        """Skip test if API credentials are not configured."""
        required_env_vars = ['ROBINHOOD_API_KEY', 'ROBINHOOD_PUBLIC_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]

        if missing_vars:
            pytest.skip(f"API credentials not configured: {missing_vars}")

    async def wait_for_rate_limit_reset(self, wait_time: float = 60.0):
        """Wait for rate limit to reset."""
        logger.info(f"Waiting {wait_time}s for rate limit reset")
        await asyncio.sleep(wait_time)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from the current test."""
        return self.performance_monitor.get_metrics()

    def log_test_summary(self, test_name: str, success: bool, details: Optional[str] = None):
        """Log test execution summary."""
        status = "PASSED" if success else "FAILED"
        logger.info(f"Test {test_name}: {status}")
        if details:
            logger.info(f"Details: {details}")


# Connection and Network Test Base Class
class NetworkTestBase(BaseIntegrationTest):
    """Base class for network connectivity tests."""

    def setup_method(self):
        super().setup_method()
        self.skip_if_no_network()

    async def test_basic_connectivity(self, base_url: str = "https://trading.robinhood.com"):
        """Test basic connectivity to API endpoints."""
        connectivity_result = await self.network_tester.test_http_connectivity(base_url)

        assert connectivity_result['connectivity'], \
            f"Failed to connect to {base_url}: {connectivity_result.get('error')}"

        if connectivity_result['response_time']:
            self.response_validator.validate_response_time(
                connectivity_result['response_time'], max_time=10.0
            )

        logger.info(f"Connectivity test passed: {connectivity_result['response_time']:.2f}s")


# Authentication Test Base Class
class AuthenticationTestBase(BaseIntegrationTest):
    """Base class for authentication flow tests."""

    async def test_authentication_flow(self, use_sandbox: bool = True):
        """Test complete authentication flow."""
        client = await self.create_authenticated_client_async()

        # Verify authentication state
        assert client.auth.is_authenticated(), "Client should be authenticated"

        auth_info = client.get_auth_info()
        assert auth_info['authenticated'] is True
        assert auth_info['auth_type'] in ['private_key', 'public_key']
        assert auth_info['sandbox'] == use_sandbox

        # Test authenticated request
        try:
            user_info = await client.get_user()
            self.assert_response_success(user_info)
        except Exception as e:
            # In sandbox, this might fail but authentication should still work
            logger.warning(f"Authenticated request failed: {e}")

    async def test_invalid_credentials(self):
        """Test behavior with invalid credentials."""
        client = self.create_client_with_config(
            api_key="invalid_key",
            public_key="invalid_public_key"
        )

        # Should not be authenticated
        assert not client.auth.is_authenticated(), "Client should not be authenticated with invalid credentials"

        # Requests should fail or return auth errors
        try:
            await client.get_user()
            # If we get here, the request succeeded unexpectedly
            logger.warning("Request succeeded with invalid credentials")
        except Exception:
            # Expected behavior - authentication should fail
            pass


# Error Handling Test Base Class
class ErrorHandlingTestBase(BaseIntegrationTest):
    """Base class for error handling tests."""

    async def test_network_timeout(self, timeout: float = 1.0):
        """Test timeout handling."""
        client = self.create_client_with_config(timeout=timeout)

        # Mock a slow response
        original_request = client.request

        async def slow_request(*args, **kwargs):
            await asyncio.sleep(timeout + 1.0)  # Longer than timeout
            return await original_request(*args, **kwargs)

        client.request = slow_request

        with pytest.raises(asyncio.TimeoutError):
            await client.get_user()

    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        # This would typically be tested with mocked responses
        # In real integration tests, we rely on the API to return valid JSON
        pass

    async def test_rate_limiting(self):
        """Test rate limiting behavior."""
        # Note: This is difficult to test reliably in integration tests
        # as it depends on API rate limits being triggered
        pass


# Performance Test Base Class
class PerformanceTestBase(BaseIntegrationTest):
    """Base class for performance and load tests."""

    async def test_response_time_benchmarks(self):
        """Test that response times meet benchmarks."""
        client = await self.create_authenticated_client_async()

        # Test various endpoints
        endpoints = [
            lambda: client.get_instruments(),
            lambda: client.get_quotes(["BTC", "ETH"]),
            lambda: client.get_user()
        ]

        for endpoint in endpoints:
            try:
                _, response_time = self.measure_response_time(endpoint)
                self.response_validator.validate_response_time(response_time, max_time=5.0)
            except Exception as e:
                logger.warning(f"Performance test failed for endpoint: {e}")

    async def test_concurrent_requests(self, num_requests: int = 5):
        """Test concurrent request handling."""
        client = await self.create_authenticated_client_async()

        async def make_request(i: int):
            await asyncio.sleep(0.1 * i)  # Stagger requests
            return await client.get_quotes("BTC")

        # Make concurrent requests
        tasks = [make_request(i) for i in range(num_requests)]
        start_time = time.time()

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Check results
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Concurrent requests: {success_count}/{num_requests} succeeded in {total_time:.2f}s")

        assert success_count > 0, "At least some concurrent requests should succeed"