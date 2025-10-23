"""
Base test classes for common testing functionality.
"""
import asyncio
import pytest
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import Mock, AsyncMock, MagicMock
import time
import json
import os
from pathlib import Path

from core.config.settings import Settings


class BaseTestCase(ABC):
    """Abstract base class for all tests."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup method that runs before each test."""
        self.start_time = time.time()
        self.test_data = {}

    def teardown_method(self):
        """Cleanup method that runs after each test."""
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"\nTest duration: {duration".3f"}s")

    def assertDictContainsSubset(self, subset: Dict[str, Any],
                               dictionary: Dict[str, Any]):
        """Assert that dictionary contains the subset."""
        for key, value in subset.items():
            assert key in dictionary, f"Key '{key}' not found in dictionary"
            if isinstance(value, dict) and isinstance(dictionary[key], dict):
                self.assertDictContainsSubset(value, dictionary[key])
            else:
                assert dictionary[key] == value, \
                    f"Value for '{key}' mismatch: {dictionary[key]} != {value}"

    def assertAlmostEqualFloat(self, a: float, b: float, delta: float = 0.01):
        """Assert that two floats are almost equal within delta."""
        assert abs(a - b) <= delta, f"{a} != {b} within {delta}"


class AsyncBaseTestCase(BaseTestCase):
    """Base class for async tests."""

    @pytest.fixture(autouse=True)
    def setup_async_method(self, event_loop):
        """Setup async test environment."""
        self.event_loop = event_loop

    async def async_setup(self):
        """Async setup method for subclasses to override."""
        pass

    async def async_teardown(self):
        """Async cleanup method for subclasses to override."""
        pass

    def run_async(self, coro):
        """Run an async coroutine in the test."""
        return self.event_loop.run_until_complete(coro)

    async def wait_for_condition(self, condition_func, timeout: float = 5.0):
        """Wait for a condition to be true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(0.01)
        return False


class UnitTestCase(AsyncBaseTestCase):
    """Base class for unit tests."""

    def setup_method(self):
        """Setup for unit tests."""
        super().setup_method()
        self.mocks = {}
        self.test_isolation_level = "unit"

    def create_mock(self, name: str, spec: Any = None) -> Mock:
        """Create and register a mock."""
        if spec:
            mock_obj = Mock(spec=spec)
        else:
            mock_obj = Mock()

        self.mocks[name] = mock_obj
        return mock_obj

    def create_async_mock(self, name: str, spec: Any = None) -> AsyncMock:
        """Create and register an async mock."""
        if spec:
            mock_obj = AsyncMock(spec=spec)
        else:
            mock_obj = AsyncMock()

        self.mocks[name] = mock_obj
        return mock_obj

    def reset_all_mocks(self):
        """Reset all registered mocks."""
        for mock in self.mocks.values():
            mock.reset_mock()


class IntegrationTestCase(AsyncBaseTestCase):
    """Base class for integration tests."""

    def setup_method(self):
        """Setup for integration tests."""
        super().setup_method()
        self.test_isolation_level = "integration"
        self.integration_components = []

    async def setup_integration_components(self):
        """Setup integration test components."""
        # This should be overridden by subclasses that need specific components
        pass

    async def teardown_integration_components(self):
        """Cleanup integration test components."""
        # This should be overridden by subclasses that need specific cleanup
        pass

    async def wait_for_component_ready(self, component, timeout: float = 10.0):
        """Wait for an integration component to be ready."""
        async def check_ready():
            return getattr(component, 'is_ready', lambda: True)()

        return await self.wait_for_condition(check_ready, timeout)


class E2ETestCase(AsyncBaseTestCase):
    """Base class for end-to-end tests."""

    def setup_method(self):
        """Setup for E2E tests."""
        super().setup_method()
        self.test_isolation_level = "e2e"
        self.e2e_components = []
        self.test_scenario = {}

    def define_test_scenario(self, scenario: Dict[str, Any]):
        """Define the test scenario."""
        self.test_scenario = scenario

    async def setup_e2e_environment(self):
        """Setup complete E2E test environment."""
        # This should be overridden by subclasses
        pass

    async def execute_e2e_scenario(self):
        """Execute the defined E2E scenario."""
        # This should be overridden by subclasses
        pass


class MockBuilder:
    """Builder for creating complex mock objects."""

    def __init__(self):
        self.mock_config = {}

    def with_method(self, name: str, return_value: Any = None,
                   side_effect: Any = None) -> 'MockBuilder':
        """Add a method to the mock."""
        method_config = {}
        if return_value is not None:
            method_config['return_value'] = return_value
        if side_effect is not None:
            method_config['side_effect'] = side_effect

        self.mock_config[name] = method_config
        return self

    def with_async_method(self, name: str, return_value: Any = None,
                         side_effect: Any = None) -> 'MockBuilder':
        """Add an async method to the mock."""
        return self.with_method(name, return_value, side_effect)

    def with_property(self, name: str, value: Any) -> 'MockBuilder':
        """Add a property to the mock."""
        self.mock_config[name] = {'property': True, 'value': value}
        return self

    def build(self, spec: Any = None) -> Mock:
        """Build the configured mock."""
        if spec:
            mock_obj = Mock(spec=spec)
        else:
            mock_obj = Mock()

        for name, config in self.mock_config.items():
            if config.get('property'):
                setattr(type(mock_obj), name, property(lambda self, value=config['value']: value))
            else:
                method = Mock(**config)
                setattr(mock_obj, name, method)

        return mock_obj


class AsyncMockBuilder(MockBuilder):
    """Builder for creating complex async mock objects."""

    def build(self, spec: Any = None) -> AsyncMock:
        """Build the configured async mock."""
        if spec:
            mock_obj = AsyncMock(spec=spec)
        else:
            mock_obj = AsyncMock()

        for name, config in self.mock_config.items():
            if config.get('property'):
                setattr(type(mock_obj), name, property(lambda self, value=config['value']: value))
            else:
                method = AsyncMock(**config)
                setattr(mock_obj, name, method)

        return mock_obj


class TestDataLoader:
    """Utility for loading test data from files."""

    def __init__(self, test_data_dir: str = "tests/fixtures"):
        self.test_data_dir = Path(test_data_dir)

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON test data."""
        file_path = self.test_data_dir / filename
        with open(file_path, 'r') as f:
            return json.load(f)

    def load_text(self, filename: str) -> str:
        """Load text test data."""
        file_path = self.test_data_dir / filename
        with open(file_path, 'r') as f:
            return f.read()

    def save_test_data(self, filename: str, data: Any):
        """Save test data for debugging."""
        os.makedirs(self.test_data_dir, exist_ok=True)
        file_path = self.test_data_dir / filename

        if isinstance(data, (dict, list)):
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            with open(file_path, 'w') as f:
                f.write(str(data))


class PerformanceTestMixin:
    """Mixin for performance testing."""

    def measure_execution_time(self, func, *args, iterations: int = 100, **kwargs):
        """Measure average execution time of a function."""
        times = []

        for _ in range(iterations):
            start_time = time.time()
            if asyncio.iscoroutinefunction(func):
                self.event_loop.run_until_complete(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
            end_time = time.time()
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        return {
            'average': avg_time,
            'min': min_time,
            'max': max_time,
            'iterations': iterations
        }

    def assert_performance_threshold(self, result: Dict[str, float],
                                   max_time: float):
        """Assert that performance meets threshold."""
        assert result['average'] <= max_time, \
            f"Average time {result['average']".4f"}s exceeds threshold {max_time".4f"}s"


# Convenience factory functions
def create_unit_test() -> UnitTestCase:
    """Factory function for unit tests."""
    return UnitTestCase()


def create_integration_test() -> IntegrationTestCase:
    """Factory function for integration tests."""
    return IntegrationTestCase()


def create_e2e_test() -> E2ETestCase:
    """Factory function for E2E tests."""
    return E2ETestCase()