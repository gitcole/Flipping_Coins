"""
Integration test utilities for API connectivity testing.

This module provides utilities for:
- API response validation
- Environment setup and configuration
- Test data management and cleanup
- Performance monitoring
- Rate limiting and retry logic testing
"""
import asyncio
import json
import os
import socket
import ssl
import time
import tempfile
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, Any, Optional, List, Union
from unittest.mock import Mock, patch
import pytest
from datetime import datetime, timedelta

from src.core.api.robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from src.core.config import initialize_config, get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TestEnvironmentManager:
    """Manages test environment setup and teardown."""

    def __init__(self, use_sandbox: bool = True):
        self.use_sandbox = use_sandbox
        self.original_env = {}
        self.temp_files = []

    def setup_environment(self):
        """Setup test environment variables."""
        # Store original environment
        env_keys = ['ROBINHOOD_API_KEY', 'ROBINHOOD_PRIVATE_KEY', 'ROBINHOOD_PUBLIC_KEY', 'ROBINHOOD_SANDBOX']
        for key in env_keys:
            self.original_env[key] = os.getenv(key)

        # Set test environment
        os.environ['ROBINHOOD_API_KEY'] = 'test_api_key_integration'
        os.environ['ROBINHOOD_PUBLIC_KEY'] = 'test_public_key_integration'
        os.environ['ROBINHOOD_SANDBOX'] = 'true' if self.use_sandbox else 'false'

        # Initialize configuration
        initialize_config()

        logger.info(f"Test environment setup for {'sandbox' if self.use_sandbox else 'production'}")

    def teardown_environment(self):
        """Restore original environment."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Clean up temporary files
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except OSError:
                pass

        self.temp_files.clear()
        logger.info("Test environment restored")

    @contextmanager
    def environment_context(self):
        """Context manager for test environment."""
        self.setup_environment()
        try:
            yield
        finally:
            self.teardown_environment()


class APIResponseValidator:
    """Validates API responses for integration tests."""

    @staticmethod
    def validate_json_response(response: Any, expected_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate JSON response structure."""
        if not isinstance(response, dict):
            raise AssertionError(f"Expected dict response, got {type(response)}")

        if expected_keys:
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                raise AssertionError(f"Missing expected keys: {missing_keys}")

        return response

    @staticmethod
    def validate_http_status_code(status_code: int, expected_codes: Union[int, List[int]]) -> None:
        """Validate HTTP status code."""
        if isinstance(expected_codes, int):
            expected_codes = [expected_codes]

        if status_code not in expected_codes:
            raise AssertionError(f"Expected status code {expected_codes}, got {status_code}")

    @staticmethod
    def validate_response_time(response_time: float, max_time: float = 5.0) -> None:
        """Validate response time is within acceptable limits."""
        if response_time > max_time:
            raise AssertionError(f"Response time {response_time:.2f}s exceeds maximum {max_time:.2f}s")

    @staticmethod
    def validate_schema_compliance(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate data complies with expected schema."""
        for field, field_schema in schema.items():
            if field not in data:
                if field_schema.get('required', False):
                    raise AssertionError(f"Required field '{field}' missing from response")
                continue

            expected_type = field_schema.get('type')
            actual_value = data[field]

            if expected_type == 'string' and not isinstance(actual_value, str):
                raise AssertionError(f"Field '{field}' expected string, got {type(actual_value)}")
            elif expected_type == 'number' and not isinstance(actual_value, (int, float)):
                raise AssertionError(f"Field '{field}' expected number, got {type(actual_value)}")
            elif expected_type == 'array' and not isinstance(actual_value, list):
                raise AssertionError(f"Field '{field}' expected array, got {type(actual_value)}")


class NetworkConnectivityTester:
    """Tests network connectivity and SSL/TLS validation."""

    @staticmethod
    async def test_dns_resolution(hostname: str) -> bool:
        """Test DNS resolution for a hostname."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, socket.gethostbyname, hostname
            )
            return True
        except socket.gaierror:
            return False

    @staticmethod
    async def test_tcp_connection(host: str, port: int, timeout: float = 5.0) -> bool:
        """Test TCP connection to a host and port."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, OSError):
            return False

    @staticmethod
    async def test_ssl_certificate(host: str, port: int = 443) -> Dict[str, Any]:
        """Test SSL certificate validity."""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            reader, writer = await asyncio.open_connection(host, port)

            try:
                ssl_socket = context.wrap_socket(
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                    server_hostname=host
                )
                ssl_socket.connect((host, port))

                cert = ssl_socket.getpeercert()
                ssl_socket.close()

                return {
                    'valid': True,
                    'subject': dict(x[0] for x in cert.get('subject', [])),
                    'issuer': dict(x[0] for x in cert.get('issuer', [])),
                    'not_before': cert.get('notBefore'),
                    'not_after': cert.get('notAfter'),
                    'serial_number': cert.get('serialNumber')
                }
            finally:
                writer.close()
                await writer.wait_closed()

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    @staticmethod
    async def test_http_connectivity(base_url: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Test HTTP connectivity to API endpoints."""
        import aiohttp

        results = {
            'connectivity': False,
            'response_time': None,
            'status_code': None,
            'error': None
        }

        start_time = time.time()

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(base_url, allow_redirects=False) as response:
                    results['connectivity'] = response.status < 500  # Any response indicates connectivity
                    results['status_code'] = response.status
                    results['response_time'] = time.time() - start_time

        except asyncio.TimeoutError:
            results['error'] = f"Connection timeout after {timeout}s"
        except Exception as e:
            results['error'] = str(e)

        return results


class PerformanceMonitor:
    """Monitors performance metrics during testing."""

    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'total_response_time': 0.0,
            'min_response_time': float('inf'),
            'max_response_time': 0.0,
            'error_count': 0,
            'start_time': None,
            'end_time': None
        }
        self.response_times = []

    def start_monitoring(self):
        """Start performance monitoring."""
        self.metrics['start_time'] = time.time()
        logger.info("Performance monitoring started")

    def end_monitoring(self):
        """End performance monitoring."""
        self.metrics['end_time'] = time.time()

        if self.response_times:
            self.metrics['min_response_time'] = min(self.response_times)
            self.metrics['max_response_time'] = max(self.response_times)
            self.metrics['avg_response_time'] = sum(self.response_times) / len(self.response_times)
            self.metrics['total_response_time'] = sum(self.response_times)

        logger.info(f"Performance monitoring ended. Total requests: {self.metrics['request_count']}")

    def record_request(self, response_time: float, success: bool = True):
        """Record a request with its response time."""
        self.metrics['request_count'] += 1
        self.response_times.append(response_time)

        if not success:
            self.metrics['error_count'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.metrics.copy()

    def get_summary(self) -> str:
        """Get performance summary."""
        if self.metrics['request_count'] == 0:
            return "No requests recorded"

        avg_time = self.metrics.get('avg_response_time', 0)
        error_rate = (self.metrics['error_count'] / self.metrics['request_count']) * 100

        return (
            f"Requests: {self.metrics['request_count']}, "
            f"Avg Time: {avg_time:.2f}s, "
            f"Error Rate: {error_rate:.1f}%"
        )


class TestDataManager:
    """Manages test data creation and cleanup."""

    def __init__(self):
        self.created_data = {
            'orders': [],
            'positions': [],
            'accounts': []
        }
        self.cleanup_callbacks = []

    def add_cleanup_callback(self, callback):
        """Add a cleanup callback."""
        self.cleanup_callbacks.append(callback)

    async def cleanup(self):
        """Clean up all test data."""
        logger.info("Starting test data cleanup")

        # Execute cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")

        # Clear data tracking
        self.created_data.clear()
        self.cleanup_callbacks.clear()

        logger.info("Test data cleanup completed")

    def record_created_order(self, order_data: Dict[str, Any]):
        """Record a created order for cleanup."""
        self.created_data['orders'].append(order_data)

    def record_created_position(self, position_data: Dict[str, Any]):
        """Record a created position for cleanup."""
        self.created_data['positions'].append(position_data)


class RateLimitTester:
    """Tests rate limiting behavior."""

    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = []
        self.rate_limited = False

    async def make_request(self, delay: float = 0.0) -> bool:
        """Make a request and check for rate limiting."""
        current_time = time.time()

        # Clean old requests outside the time window
        self.request_times = [
            req_time for req_time in self.request_times
            if current_time - req_time < self.time_window
        ]

        # Check if we're rate limited
        if len(self.request_times) >= self.max_requests:
            self.rate_limited = True
            return False

        # Record this request
        self.request_times.append(current_time)

        if delay > 0:
            await asyncio.sleep(delay)

        return True

    def get_request_count(self) -> int:
        """Get current request count in time window."""
        current_time = time.time()
        self.request_times = [
            req_time for req_time in self.request_times
            if current_time - req_time < self.time_window
        ]
        return len(self.request_times)

    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        return self.get_request_count() >= self.max_requests


@asynccontextmanager
async def robinhood_client_context(sandbox: bool = True, **client_kwargs):
    """Async context manager for RobinhoodClient with automatic cleanup."""
    client = None
    try:
        # Create client with test configuration
        env_manager = TestEnvironmentManager(use_sandbox=sandbox)
        env_manager.setup_environment()

        client = RobinhoodClient(sandbox=sandbox, **client_kwargs)

        # Initialize client
        await client.initialize()

        yield client

    except Exception as e:
        logger.error(f"Error in client context: {e}")
        raise
    finally:
        if client:
            await client.close()
        env_manager.teardown_environment()


def create_test_config(sandbox: bool = True, **overrides) -> RobinhoodAPIConfig:
    """Create a test configuration."""
    config_data = {
        'sandbox': sandbox,
        'api_key': 'test_api_key',
        'public_key': 'test_public_key',
        'private_key': 'test_private_key',
        'base_url': 'https://trading.robinhood.com',
        'timeout': 30,
        'max_retries': 3,
        'retry_delay': 1.0,
        'rate_limit_per_second': 10
    }
    config_data.update(overrides)

    return RobinhoodAPIConfig(**config_data)


def generate_test_credentials():
    """Generate test credentials for integration testing."""
    from ecdsa import SigningKey
    from base64 import b64encode
    import secrets

    # Generate test API key
    api_key = f"rh-api-{secrets.token_hex(16)}"

    # Generate test key pair
    private_key = SigningKey.generate()
    private_key_b64 = b64encode(private_key.to_der()).decode('utf-8')
    public_key_b64 = b64encode(private_key.verifying_key.to_der()).decode('utf-8')

    return {
        'api_key': api_key,
        'private_key': private_key_b64,
        'public_key': public_key_b64
    }


async def wait_for_condition(condition_func, timeout: float = 10.0, check_interval: float = 0.1):
    """Wait for a condition to be met."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            if await condition_func():
                return True
        except Exception:
            pass

        await asyncio.sleep(check_interval)

    return False