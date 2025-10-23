"""
Utilities for async testing.
"""
import asyncio
import functools
import time
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import dataclass
from datetime import datetime, timedelta

T = TypeVar('T')


@dataclass
class AsyncTestResult:
    """Result of an async test operation."""
    success: bool
    data: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0


class AsyncTestUtils:
    """Utilities for testing async code."""

    @staticmethod
    def run_async(coro, timeout: Optional[float] = None) -> Any:
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if timeout:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        else:
            return loop.run_until_complete(coro)

    @staticmethod
    def create_task(coro) -> asyncio.Task:
        """Create and schedule a task."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.create_task(coro)

    @staticmethod
    def run_multiple_async(coroutines: List[Any], timeout: Optional[float] = None) -> List[Any]:
        """Run multiple async coroutines concurrently."""
        async def run_all():
            tasks = [asyncio.create_task(coro) for coro in coroutines]
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
            else:
                results = await asyncio.gather(*tasks, return_exceptions=True)

            return results

        return AsyncTestUtils.run_async(run_all())

    @staticmethod
    def async_test(timeout: Optional[float] = None):
        """Decorator to run async test functions."""
        def decorator(func):
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    return AsyncTestUtils.run_async(func(*args, **kwargs), timeout)
                return wrapper
            else:
                return func
        return decorator

    @staticmethod
    def wait_for_condition(condition_func, timeout: float = 5.0,
                          check_interval: float = 0.01) -> bool:
        """Wait for an async condition to be true."""
        async def wait():
            start_time = time.time()
            while time.time() - start_time < timeout:
                if await condition_func():
                    return True
                await asyncio.sleep(check_interval)
            return False

        return AsyncTestUtils.run_async(wait())


class AsyncContextManager:
    """Async context manager utilities."""

    @staticmethod
    @asynccontextmanager
    async def managed_resource(resource_factory, cleanup_func=None):
        """Context manager for async resources."""
        resource = await resource_factory() if asyncio.iscoroutinefunction(resource_factory) else resource_factory()
        try:
            yield resource
        finally:
            if cleanup_func:
                await cleanup_func(resource) if asyncio.iscoroutinefunction(cleanup_func) else cleanup_func(resource)
            else:
                if hasattr(resource, 'close') and asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                elif hasattr(resource, 'close'):
                    resource.close()

    @staticmethod
    @asynccontextmanager
    async def temporary_connection(connect_func, disconnect_func):
        """Context manager for temporary connections."""
        connection = await connect_func() if asyncio.iscoroutinefunction(connect_func) else connect_func()
        try:
            yield connection
        finally:
            await disconnect_func(connection) if asyncio.iscoroutinefunction(disconnect_func) else disconnect_func(connection)


class AsyncMockUtils:
    """Utilities for working with async mocks."""

    @staticmethod
    def create_async_mock_response(data: Any, delay: float = 0.0) -> AsyncMock:
        """Create an async mock that returns data after delay."""
        async def mock_response(*args, **kwargs):
            if delay > 0:
                await asyncio.sleep(delay)
            return data

        mock = AsyncMock(side_effect=mock_response)
        return mock

    @staticmethod
    def create_sequential_responses(responses: List[Any], delays: Optional[List[float]] = None) -> AsyncMock:
        """Create an async mock that returns responses sequentially."""
        if delays is None:
            delays = [0.0] * len(responses)

        call_count = 0

        async def sequential_response(*args, **kwargs):
            nonlocal call_count
            if call_count < len(responses):
                response = responses[call_count]
                delay = delays[call_count]
                call_count += 1

                if delay > 0:
                    await asyncio.sleep(delay)

                return response
            else:
                raise StopAsyncIteration("No more responses")

        mock = AsyncMock(side_effect=sequential_response)
        return mock

    @staticmethod
    def create_failing_mock(exception: Exception, after_calls: int = 1) -> AsyncMock:
        """Create an async mock that fails after specified calls."""
        call_count = 0

        async def failing_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count >= after_calls:
                raise exception
            else:
                return None

        mock = AsyncMock(side_effect=failing_response)
        return mock


class TestTimer:
    """Timer for measuring test execution time."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.laps = []

    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        return self

    def stop(self):
        """Stop the timer."""
        self.end_time = time.time()
        return self

    def lap(self, name: str = "lap"):
        """Record a lap time."""
        current_time = time.time()
        if self.start_time:
            lap_time = current_time - (self.laps[-1][1] if self.laps else self.start_time)
            self.laps.append((name, current_time, lap_time))

    def total_time(self) -> float:
        """Get total elapsed time."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        else:
            return 0.0

    def get_laps(self) -> List[tuple]:
        """Get all lap records."""
        return self.laps.copy()


class AsyncTestCaseMixin:
    """Mixin providing async testing utilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = TestTimer()
        self.tasks = []

    def setUp(self):
        """Setup async test case."""
        self.timer = TestTimer()
        self.tasks = []

    def tearDown(self):
        """Cleanup async test case."""
        # Cancel any running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to be cancelled
        if self.tasks:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(*self.tasks, return_exceptions=True))

    def run_async_test(self, coro, timeout: Optional[float] = None):
        """Run an async test method."""
        self.timer.start()
        try:
            result = AsyncTestUtils.run_async(coro, timeout)
            self.timer.stop()
            return result
        except Exception as e:
            self.timer.stop()
            raise e

    def create_background_task(self, coro) -> asyncio.Task:
        """Create a background task for the test."""
        task = AsyncTestUtils.create_task(coro)
        self.tasks.append(task)
        return task

    def wait_for_task_completion(self, task: asyncio.Task, timeout: float = 5.0):
        """Wait for a background task to complete."""
        return AsyncTestUtils.run_async(
            asyncio.wait_for(task, timeout=timeout)
        )


# Decorators for async testing
def async_test(timeout: Optional[float] = None):
    """Decorator for async test methods."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'run_async_test'):
                return self.run_async_test(func(self, *args, **kwargs), timeout)
            else:
                return AsyncTestUtils.run_async(func(self, *args, **kwargs), timeout)
        return wrapper
    return decorator


def retry_async(times: int = 3, exceptions: tuple = (Exception,), delay: float = 0.1):
    """Decorator to retry async functions on failure."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(times):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < times - 1:
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    continue

            raise last_exception

        return wrapper
    return decorator


def measure_time_async(name: Optional[str] = None):
    """Decorator to measure async function execution time."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            timer = TestTimer()
            timer.start()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                timer.stop()
                func_name = name or func.__name__
                print(f"{func_name} took {timer.total_time()".3f"}s")

        return wrapper
    return decorator


def patch_async(target, new=None, **kwargs):
    """Async version of unittest.mock.patch decorator."""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs_inner):
                with patch(target, new, **kwargs) as mock:
                    return await func(*args, **kwargs_inner)
            return wrapper
        else:
            return patch(target, new, **kwargs)(func)
    return decorator


# Utility functions for common async testing patterns
async def wait_for_condition(condition_func, timeout: float = 5.0,
                           check_interval: float = 0.01) -> bool:
    """Wait for an async condition to be true."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(check_interval)
    return False


async def wait_for_event(event: asyncio.Event, timeout: float = 5.0) -> bool:
    """Wait for an asyncio Event to be set."""
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False


async def collect_async_results(async_iter: AsyncGenerator, timeout: float = 5.0) -> List[Any]:
    """Collect results from an async iterator."""
    results = []

    async def collect():
        async for item in async_iter:
            results.append(item)

    try:
        await asyncio.wait_for(collect(), timeout=timeout)
    except asyncio.TimeoutError:
        pass

    return results


def create_async_test_data(size: int = 100) -> List[Dict[str, Any]]:
    """Create test data for async operations."""
    return [
        {
            "id": i,
            "symbol": f"TEST{i % 10}",
            "value": i * 100,
            "timestamp": datetime.now() + timedelta(seconds=i)
        }
        for i in range(size)
    ]


async def simulate_workload(duration: float, cpu_intensive: bool = False):
    """Simulate async workload."""
    if cpu_intensive:
        # CPU intensive work
        end_time = time.time() + duration
        while time.time() < end_time:
            _ = [x*x for x in range(1000)]
    else:
        # I/O bound work
        await asyncio.sleep(duration)


class AsyncTestEnvironment:
    """Environment for running async tests."""

    def __init__(self):
        self.loop = None
        self.tasks = set()
        self.cleanup_callbacks = []

    def __enter__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Run cleanup callbacks
        for cleanup in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(cleanup):
                    self.loop.run_until_complete(cleanup())
                else:
                    cleanup()
            except Exception:
                pass  # Ignore cleanup errors

        # Close loop
        if self.loop:
            self.loop.close()

        return False

    def run(self, coro):
        """Run a coroutine in this environment."""
        if not self.loop:
            raise RuntimeError("Environment not entered")

        return self.loop.run_until_complete(coro)

    def create_task(self, coro) -> asyncio.Task:
        """Create a task in this environment."""
        if not self.loop:
            raise RuntimeError("Environment not entered")

        task = self.loop.create_task(coro)
        self.tasks.add(task)
        return task

    def add_cleanup_callback(self, callback):
        """Add a cleanup callback."""
        self.cleanup_callbacks.append(callback)


# Convenience functions for common patterns
def with_timeout(timeout: float):
    """Create a decorator that adds timeout to async functions."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        return wrapper
    return decorator


def suppress_exceptions(*exceptions):
    """Create a decorator that suppresses specified exceptions."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions:
                return None
        return wrapper
    return decorator


async def eventually(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to eventually become true."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if await condition_func():
                return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    return False