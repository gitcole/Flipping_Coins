"""
Pytest configuration and shared fixtures for API connectivity testing.

This module provides shared fixtures and configuration for both unit and integration tests.
"""
import asyncio
import os
import pytest
import tempfile
from typing import Dict, Any
from unittest.mock import patch

from tests.mocks.api_mocks import RobinhoodApiMock, EnhancedApiMock
from tests.integration.test_utils import TestEnvironmentManager, generate_test_credentials
from tests.utils.base_test import UnitTestCase, IntegrationTestCase

from src.core.config import initialize_config
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ===== SHARED FIXTURES =====

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment for all tests."""
    # Initialize configuration for tests
    initialize_config()

    # Set test-specific environment variables
    os.environ.setdefault('ROBINHOOD_SANDBOX', 'true')
    os.environ.setdefault('LOG_LEVEL', 'DEBUG')

    logger.info("Test environment setup completed")


@pytest.fixture
def temp_config_file():
    """Provide a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write('''
app:
  name: test-bot
  version: "1.0.0"
robinhood:
  api_key: test_api_key
  public_key: test_public_key
  sandbox: true
  timeout: 30
  max_retries: 3
trading:
  enabled: false
  max_positions: 5
''')
        config_path = f.name

    yield config_path

    # Cleanup
    try:
        os.unlink(config_path)
    except OSError:
        pass


@pytest.fixture
def temp_env_file():
    """Provide a temporary environment file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write('''
ROBINHOOD_API_KEY=test_api_key_from_env
ROBINHOOD_PUBLIC_KEY=test_public_key_from_env
ROBINHOOD_SANDBOX=true
LOG_LEVEL=INFO
''')
        env_path = f.name

    yield env_path

    # Cleanup
    try:
        os.unlink(env_path)
    except OSError:
        pass


@pytest.fixture
def mock_api():
    """Provide a mock API for unit testing."""
    return RobinhoodApiMock()


@pytest.fixture
def enhanced_mock_api():
    """Provide an enhanced mock API with advanced features."""
    return EnhancedApiMock()


@pytest.fixture
def test_credentials():
    """Provide test credentials for authentication testing."""
    return generate_test_credentials()


# ===== UNIT TEST FIXTURES =====

@pytest.fixture
def unit_test_client(mock_api):
    """Provide a unit test client with mocked API."""
    from src.core.api.robinhood.client import RobinhoodClient

    client = RobinhoodClient(sandbox=True)
    client.config.api_key = "unit_test_api_key"
    client.config.public_key = "unit_test_public_key"

    # Mock the request method to use our mock API
    async def mock_request(method, endpoint, **kwargs):
        # Simulate API call with mock data
        if "instruments" in endpoint:
            return {"results": [
                {"id": "test_btc", "symbol": "BTC", "name": "Bitcoin"},
                {"id": "test_eth", "symbol": "ETH", "name": "Ethereum"}
            ]}
        elif "quotes" in endpoint:
            return {"BTC": {"symbol": "BTC", "price": "50000"}}
        else:
            return {"data": "mock_response"}

    client.request = mock_request
    return client


# ===== INTEGRATION TEST FIXTURES =====

@pytest.fixture
async def integration_test_client():
    """Provide an integration test client with real API configuration."""
    from src.core.api.robinhood.client import RobinhoodClient

    # Setup test environment
    env_manager = TestEnvironmentManager(use_sandbox=True)
    env_manager.setup_environment()

    try:
        client = RobinhoodClient(sandbox=True)

        # Set test credentials
        credentials = generate_test_credentials()
        client.config.api_key = credentials['api_key']
        client.config.public_key = credentials['public_key']

        # Initialize client
        await client.initialize()

        yield client

    finally:
        await client.close()
        env_manager.teardown_environment()


@pytest.fixture
def performance_monitor():
    """Provide performance monitoring for tests."""
    from tests.integration.test_utils import PerformanceMonitor

    monitor = PerformanceMonitor()
    monitor.start_monitoring()

    yield monitor

    monitor.end_monitoring()


# ===== MARKERS AND CONFIGURATION =====

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests that require real API access"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests that use mocking"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load testing"
    )
    config.addinivalue_line(
        "markers", "network: Network connectivity tests"
    )
    config.addinivalue_line(
        "markers", "auth: Authentication tests"
    )
    config.addinivalue_line(
        "markers", "error: Error handling tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add integration marker for integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add unit marker for unit tests
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add performance marker for performance tests
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)

        # Add network marker for network tests
        if "network" in item.name.lower() or "connectivity" in item.name.lower():
            item.add_marker(pytest.mark.network)

        # Add auth marker for authentication tests
        if "auth" in item.name.lower():
            item.add_marker(pytest.mark.auth)

        # Add error marker for error handling tests
        if "error" in item.name.lower():
            item.add_marker(pytest.mark.error)


# ===== ASYNC TEST UTILITIES =====

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===== MOCKING UTILITIES =====

@pytest.fixture
def mock_network_failure():
    """Mock network failure for testing error handling."""
    def network_failure_side_effect(*args, **kwargs):
        raise Exception("Network connection failed")

    return network_failure_side_effect


@pytest.fixture
def mock_timeout():
    """Mock timeout for testing timeout handling."""
    async def timeout_side_effect(*args, **kwargs):
        await asyncio.sleep(10)  # Long delay to trigger timeout
        return {"data": "should_not_reach_here"}

    return timeout_side_effect


@pytest.fixture
def mock_rate_limit():
    """Mock rate limiting for testing rate limit handling."""
    call_count = 0

    async def rate_limit_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count <= 2:
            from src.core.api.exceptions import RateLimitError
            raise RateLimitError("Rate limit exceeded", retry_after=60)

        return {"data": "success_after_retry"}

    return rate_limit_side_effect


# ===== DEBUG TEST FIXTURES =====

@pytest.fixture
def debug_suite():
    """Provide a debug test suite for comprehensive debugging tests."""
    from tests.debug.test_api_connectivity import APIConnectivityTestSuite
    return APIConnectivityTestSuite()


@pytest.fixture
def connectivity_suite():
    """Provide a connectivity test suite for network connectivity testing."""
    from tests.debug.test_api_connectivity import APIConnectivityTestSuite
    return APIConnectivityTestSuite()


@pytest.fixture
def auth_suite():
    """Provide an authentication test suite for auth-related testing."""
    from tests.debug.test_api_connectivity import APIConnectivityTestSuite
    return APIConnectivityTestSuite()


# ===== TEST DATA FIXTURES =====

@pytest.fixture
def sample_crypto_data():
    """Provide sample cryptocurrency data for testing."""
    return {
        "BTC": {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price": 50000.00,
            "volume": 1000000,
            "change_24h": 2.5
        },
        "ETH": {
            "symbol": "ETH",
            "name": "Ethereum",
            "price": 3000.00,
            "volume": 500000,
            "change_24h": -1.2
        }
    }


@pytest.fixture
def sample_order_data():
    """Provide sample order data for testing."""
    return {
        "symbol": "BTC",
        "side": "buy",
        "type": "limit",
        "quantity": "0.1",
        "price": "50000.00"
    }


@pytest.fixture
def sample_position_data():
    """Provide sample position data for testing."""
    return {
        "symbol": "BTC",
        "quantity": "0.1",
        "average_price": "45000.00",
        "current_price": "50000.00",
        "unrealized_pnl": "500.00"
    }