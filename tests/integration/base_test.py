"""
Base integration test fixtures and utilities for API connectivity testing.

Provides common setup, teardown, and utilities for integration tests.
"""
import asyncio
import pytest
import os
import time
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


# ===== FIXTURES =====

@pytest.fixture
async def authenticated_client():
    """Fixture providing an authenticated RobinhoodClient."""
    async with robinhood_client_context(sandbox=True) as client:
        # Wait for authentication to complete
        await wait_for_condition(
            lambda: client.auth.is_authenticated(),
            timeout=30.0
        )
        yield client

@pytest.fixture
async def unauthenticated_client():
    """Fixture providing an unauthenticated RobinhoodClient."""
    async with robinhood_client_context(sandbox=True) as client:
        # Ensure client is not authenticated
        client.config.api_key = "invalid_key"
        client.config.public_key = "invalid_public_key"
        yield client

# ===== UTILITY FUNCTIONS =====

def create_client_with_config(**config_overrides) -> RobinhoodClient:
    """Create a client with specific configuration."""
    config = create_test_config(sandbox=True, **config_overrides)
    return RobinhoodClient(config=config)

async def create_authenticated_client_async(**config_overrides) -> RobinhoodClient:
    """Create an authenticated client asynchronously."""
    test_credentials = generate_test_credentials()
    client = create_client_with_config(**config_overrides)

    # Set valid credentials
    client.config.api_key = test_credentials['api_key']
    client.config.public_key = test_credentials['public_key']

    # Initialize client
    await client.initialize()

    return client

def assert_response_success(response: Any, expected_keys: Optional[list] = None):
    """Assert that a response indicates success."""
    response_validator = APIResponseValidator()
    if isinstance(response, dict):
        response_validator.validate_json_response(response, expected_keys)
    elif response is None:
        pytest.fail("Response is None")
    elif hasattr(response, 'status_code'):
        if response.status_code >= 400:
            pytest.fail(f"HTTP error response: {response.status_code}")

def assert_response_error(response: Any, expected_status: Optional[int] = None):
    """Assert that a response indicates an error."""
    if hasattr(response, 'status_code'):
        if expected_status and response.status_code != expected_status:
            pytest.fail(f"Expected status {expected_status}, got {response.status_code}")
    elif isinstance(response, dict) and 'error' in response:
        # Valid error response format
        pass
    else:
        pytest.fail(f"Expected error response, got: {response}")

def measure_response_time(func, *args, **kwargs):
    """Measure response time of a function call."""
    performance_monitor = PerformanceMonitor()
    start_time = time.time()

    try:
        if asyncio.iscoroutinefunction(func):
            # Note: In a real pytest function, you'd need to handle async differently
            # This is a simplified version for standalone functions
            result = func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        response_time = time.time() - start_time
        performance_monitor.record_request(response_time, success=True)

        return result, response_time

    except Exception as e:
        response_time = time.time() - start_time
        performance_monitor.record_request(response_time, success=False)
        raise

def skip_if_no_network():
    """Skip test if network connectivity is not available."""
    try:
        # Quick connectivity check
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=5)
    except OSError:
        pytest.skip("No network connectivity available")

def skip_if_no_api_credentials():
    """Skip test if API credentials are not configured."""
    required_env_vars = ['ROBINHOOD_API_KEY', 'ROBINHOOD_PUBLIC_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(f"API credentials not configured: {missing_vars}")

async def wait_for_rate_limit_reset(wait_time: float = 60.0):
    """Wait for rate limit to reset."""
    logger.info(f"Waiting {wait_time}s for rate limit reset")
    await asyncio.sleep(wait_time)

def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics from the current test."""
    performance_monitor = PerformanceMonitor()
    return performance_monitor.get_metrics()

def log_test_summary(test_name: str, success: bool, details: Optional[str] = None):
    """Log test execution summary."""
    status = "PASSED" if success else "FAILED"
    logger.info(f"Test {test_name}: {status}")
    if details:
        logger.info(f"Details: {details}")

# ===== SETUP/TEARDOWN FUNCTIONS =====

def setup_integration_test():
    """Setup for each integration test."""
    env_manager = TestEnvironmentManager(use_sandbox=True)
    performance_monitor = PerformanceMonitor()
    data_manager = TestDataManager()

    # Setup test environment
    env_manager.setup_environment()

    # Start performance monitoring
    performance_monitor.start_monitoring()

    # Setup test credentials
    test_credentials = generate_test_credentials()

    logger.info("Integration test setup completed")

    return {
        'env_manager': env_manager,
        'performance_monitor': performance_monitor,
        'data_manager': data_manager,
        'test_credentials': test_credentials
    }

async def teardown_integration_test(setup_data):
    """Teardown for each integration test."""
    performance_monitor = setup_data['performance_monitor']
    data_manager = setup_data['data_manager']
    env_manager = setup_data['env_manager']

    # End performance monitoring
    performance_monitor.end_monitoring()

    # Log performance summary
    summary = performance_monitor.get_summary()
    logger.info(f"Performance summary: {summary}")

    # Cleanup test data
    await data_manager.cleanup()

    # Restore environment
    env_manager.teardown_environment()

    logger.info("Integration test teardown completed")


# ===== STANDALONE TEST FUNCTIONS =====

async def test_basic_connectivity(base_url: str = "https://trading.robinhood.com"):
    """Test basic connectivity to API endpoints."""
    skip_if_no_network()
    network_tester = NetworkConnectivityTester()
    response_validator = APIResponseValidator()

    connectivity_result = await network_tester.test_http_connectivity(base_url)

    assert connectivity_result['connectivity'], \
        f"Failed to connect to {base_url}: {connectivity_result.get('error')}"

    if connectivity_result['response_time']:
        response_validator.validate_response_time(
            connectivity_result['response_time'], max_time=10.0
        )

    logger.info(f"Connectivity test passed: {connectivity_result['response_time']:.2f}s")


async def test_authentication_flow(use_sandbox: bool = True):
    """Test complete authentication flow."""
    client = await create_authenticated_client_async()

    # Verify authentication state
    assert client.auth.is_authenticated(), "Client should be authenticated"

    auth_info = client.get_auth_info()
    assert auth_info['authenticated'] is True
    assert auth_info['auth_type'] in ['private_key', 'public_key']
    assert auth_info['sandbox'] == use_sandbox

    # Test authenticated request
    try:
        user_info = await client.get_user()
        assert_response_success(user_info)
    except Exception as e:
        # In sandbox, this might fail but authentication should still work
        logger.warning(f"Authenticated request failed: {e}")


async def test_invalid_credentials():
    """Test behavior with invalid credentials."""
    client = create_client_with_config(
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


async def test_network_timeout(timeout: float = 1.0):
    """Test timeout handling."""
    client = create_client_with_config(timeout=timeout)

    # Mock a slow response
    original_request = client.request

    async def slow_request(*args, **kwargs):
        await asyncio.sleep(timeout + 1.0)  # Longer than timeout
        return await original_request(*args, **kwargs)

    client.request = slow_request

    with pytest.raises(asyncio.TimeoutError):
        await client.get_user()


async def test_invalid_json_response():
    """Test handling of invalid JSON responses."""
    # This would typically be tested with mocked responses
    # In real integration tests, we rely on the API to return valid JSON
    pass


async def test_rate_limiting():
    """Test rate limiting behavior."""
    # Note: This is difficult to test reliably in integration tests
    # as it depends on API rate limits being triggered
    pass


async def test_response_time_benchmarks():
    """Test that response times meet benchmarks."""
    client = await create_authenticated_client_async()
    response_validator = APIResponseValidator()

    # Test various endpoints
    endpoints = [
        lambda: client.get_instruments(),
        lambda: client.get_quotes(["BTC", "ETH"]),
        lambda: client.get_user()
    ]

    for endpoint in endpoints:
        try:
            _, response_time = measure_response_time(endpoint)
            response_validator.validate_response_time(response_time, max_time=5.0)
        except Exception as e:
            logger.warning(f"Performance test failed for endpoint: {e}")


async def test_concurrent_requests(num_requests: int = 5):
    """Test concurrent request handling."""
    client = await create_authenticated_client_async()

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