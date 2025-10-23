"""
Comprehensive Priority 3 test cases for ApplicationOrchestrator - Infrastructure Components.
Tests focus on application lifecycle, component management, and core orchestration functions.
"""
import asyncio
import pytest
import signal
import time
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from core.application.orchestrator import ApplicationOrchestrator
from core.config.settings import Settings


class TestApplicationOrchestrator(UnitTestCase):
    """Test cases for ApplicationOrchestrator infrastructure functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.settings = Mock(spec=Settings)
        self.settings.component_configs = {
            'test_component': {
                'enabled': True,
                'timeout': 30,
                'retry_attempts': 3
            }
        }

        self.orchestrator = ApplicationOrchestrator(self.settings)
        self.orchestrator.components = {}
        self.orchestrator.health_metrics = {}
        self.orchestrator.risk_metrics = {}

    def test_initialize_success(self):
        """Test successful component initialization."""
        # Arrange
        mock_component = self.create_async_mock('test_component')
        mock_component.initialize = AsyncMock(return_value=True)
        self.orchestrator.components = {'test_component': mock_component}

        # Act
        async def run_test():
            return await self.orchestrator.initialize()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        mock_component.initialize.assert_called_once()

    def test_initialize_component_failure(self):
        """Test component initialization failure handling."""
        # Arrange
        mock_component = self.create_async_mock('failing_component')
        mock_component.initialize = AsyncMock(side_effect=Exception("Init failed"))
        self.orchestrator.components = {'failing_component': mock_component}

        # Act
        async def run_test():
            return await self.orchestrator.initialize()

        result = self.run_async(run_test())

        # Assert
        assert result is False
        assert len(self.orchestrator.components) == 1

    def test_initialize_dependency_setup(self):
        """Test dependency setup and injection."""
        # Arrange
        mock_component = self.create_async_mock('dependent_component')
        mock_component.dependencies = ['database', 'cache']
        mock_component.initialize = AsyncMock(return_value=True)

        self.orchestrator.components = {
            'database': self.create_async_mock('database', {'initialize': AsyncMock(return_value=True)}),
            'cache': self.create_async_mock('cache', {'initialize': AsyncMock(return_value=True)}),
            'dependent_component': mock_component
        }

        # Act
        async def run_test():
            return await self.orchestrator.initialize()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        # Verify dependency order - database and cache should initialize first
        database_mock = self.orchestrator.components['database'].initialize
        cache_mock = self.orchestrator.components['cache'].initialize
        assert database_mock.called
        assert cache_mock.called

    def test_start_all_components(self):
        """Test successful component startup sequence."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            component.start = AsyncMock(return_value=True)
            component.is_healthy = AsyncMock(return_value=True)
            components[f'component_{i}'] = component

        self.orchestrator.components = components

        # Act
        async def run_test():
            return await self.orchestrator.start_all_components()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        for component in self.orchestrator.components.values():
            component.start.assert_called_once()

    def test_start_partial_failure(self):
        """Test partial startup failure recovery."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            if i == 1:  # Make middle component fail
                component.start = AsyncMock(side_effect=Exception("Start failed"))
            else:
                component.start = AsyncMock(return_value=True)
            components[f'component_{i}'] = component

        self.orchestrator.components = components

        # Act
        async def run_test():
            return await self.orchestrator.start_all_components()

        result = self.run_async(run_test())

        # Assert
        assert result is False
        # First component should have started, second should have failed, third should not have been attempted
        components['component_0'].start.assert_called_once()
        components['component_1'].start.assert_called_once()
        components['component_2'].start.assert_not_called()

    def test_stop_graceful_shutdown(self):
        """Test graceful component shutdown."""
        # Arrange
        mock_component = self.create_async_mock('test_component')
        mock_component.stop = AsyncMock(return_value=True)
        mock_component.cleanup = AsyncMock(return_value=True)
        self.orchestrator.components = {'test_component': mock_component}

        # Act
        async def run_test():
            return await self.orchestrator.stop_graceful_shutdown()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        mock_component.stop.assert_called_once()
        mock_component.cleanup.assert_called_once()

    def test_stop_forced_shutdown(self):
        """Test forced shutdown handling."""
        # Arrange
        mock_component = self.create_async_mock('hung_component')
        mock_component.stop = AsyncMock(side_effect=asyncio.TimeoutError("Hung"))
        mock_component.force_stop = AsyncMock(return_value=True)
        self.orchestrator.components = {'hung_component': mock_component}

        # Act
        async def run_test():
            return await self.orchestrator.stop_forced_shutdown(timeout=1.0)

        result = self.run_async(run_test())

        # Assert
        assert result is True
        mock_component.force_stop.assert_called_once()

    def test_shutdown_complete_cleanup(self):
        """Test complete shutdown and cleanup."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            component.stop = AsyncMock(return_value=True)
            component.cleanup = AsyncMock(return_value=True)
            components[f'component_{i}'] = component

        self.orchestrator.components = components

        # Act
        async def run_test():
            return await self.orchestrator.shutdown_complete_cleanup()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        for component in self.orchestrator.components.values():
            component.stop.assert_called_once()
            component.cleanup.assert_called_once()

    def test_health_monitoring_loop_success(self):
        """Test health monitoring loop execution."""
        # Arrange
        mock_component = self.create_async_mock('healthy_component')
        mock_component.is_healthy = AsyncMock(return_value=True)
        self.orchestrator.components = {'healthy_component': mock_component}

        # Act
        async def run_test():
            await self.orchestrator.health_monitoring_loop(interval=0.1, duration=0.3)

        self.run_async(run_test())

        # Assert
        # Should have checked health multiple times
        assert mock_component.is_healthy.call_count >= 2

    def test_health_monitoring_loop_component_failure(self):
        """Test component failure detection."""
        # Arrange
        mock_component = self.create_async_mock('failing_component')
        mock_component.is_healthy = AsyncMock(side_effect=[True, False, Exception("Failed")])
        self.orchestrator.components = {'failing_component': mock_component}

        # Act
        async def run_test():
            await self.orchestrator.health_monitoring_loop(interval=0.1, duration=0.4)

        self.run_async(run_test())

        # Assert
        # Should have detected the failure and created alert
        assert len(self.orchestrator.health_alerts) > 0

    def test_risk_monitoring_loop_success(self):
        """Test risk monitoring loop execution."""
        # Arrange
        self.orchestrator.risk_metrics = {
            'portfolio_risk': 0.05,
            'max_risk': 0.10,
            'component_risks': {}
        }

        # Act
        async def run_test():
            await self.orchestrator.risk_monitoring_loop(interval=0.1, duration=0.3)

        self.run_async(run_test())

        # Assert
        # Should have completed without issues
        assert self.orchestrator.risk_metrics['portfolio_risk'] == 0.05

    def test_risk_monitoring_loop_critical_risk(self):
        """Test critical risk condition handling."""
        # Arrange
        self.orchestrator.risk_metrics = {
            'portfolio_risk': 0.15,  # Above threshold
            'max_risk': 0.10,
            'component_risks': {}
        }

        # Act
        async def run_test():
            await self.orchestrator.risk_monitoring_loop(interval=0.1, duration=0.3)

        self.run_async(run_test())

        # Assert
        # Should have detected critical risk and triggered shutdown
        assert len(self.orchestrator.critical_risk_alerts) > 0

    def test_check_critical_risk_conditions_normal(self):
        """Test normal risk condition checking."""
        # Arrange
        self.orchestrator.risk_metrics = {
            'portfolio_risk': 0.05,
            'max_risk': 0.10,
            'component_risks': {}
        }

        # Act
        async def run_test():
            return await self.orchestrator.check_critical_risk_conditions()

        result = self.run_async(run_test())

        # Assert
        assert result is False  # No critical conditions

    def test_check_critical_risk_conditions_critical(self):
        """Test critical risk condition detection."""
        # Arrange
        self.orchestrator.risk_metrics = {
            'portfolio_risk': 0.15,  # Above threshold
            'max_risk': 0.10,
            'component_risks': {}
        }

        # Act
        async def run_test():
            return await self.orchestrator.check_critical_risk_conditions()

        result = self.run_async(run_test())

        # Assert
        assert result is True  # Critical conditions detected

    def test_update_health_metrics_comprehensive(self):
        """Test health metrics update."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            component.get_health_status = AsyncMock(return_value={
                'status': 'healthy' if i != 1 else 'unhealthy',
                'uptime': 100 + i,
                'memory_usage': 50 + i * 10
            })
            components[f'component_{i}'] = component

        self.orchestrator.components = components

        # Act
        async def run_test():
            await self.orchestrator.update_health_metrics()

        self.run_async(run_test())

        # Assert
        assert 'overall_health' in self.orchestrator.health_metrics
        assert 'component_health' in self.orchestrator.health_metrics
        assert len(self.orchestrator.health_metrics['component_health']) == 3

    def test_perform_health_checks_initial(self):
        """Test initial health checks."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            component.perform_health_check = AsyncMock(return_value=True)
            components[f'component_{i}'] = component

        self.orchestrator.components = components

        # Act
        async def run_test():
            return await self.orchestrator.perform_health_checks()

        result = self.run_async(run_test())

        # Assert
        assert result is True
        for component in self.orchestrator.components.values():
            component.perform_health_check.assert_called_once()

    def test_perform_health_checks_ongoing(self):
        """Test ongoing health checks."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            component.perform_health_check = AsyncMock(return_value=True)
            components[f'component_{i}'] = component

        self.orchestrator.components = components
        self.orchestrator.last_health_check = time.time() - 3600  # 1 hour ago

        # Act
        async def run_test():
            return await self.orchestrator.perform_health_checks()

        result = self.run_async(run_test())

        # Assert
        assert result is True

    def test_get_status_comprehensive(self):
        """Test comprehensive status retrieval."""
        # Arrange
        self.orchestrator.health_metrics = {
            'overall_health': 'healthy',
            'uptime': 3600,
            'component_count': 3
        }
        self.orchestrator.risk_metrics = {
            'portfolio_risk': 0.05,
            'max_risk': 0.10
        }

        # Act
        status = self.orchestrator.get_status()

        # Assert
        assert status['health'] == 'healthy'
        assert status['uptime'] == 3600
        assert status['risk_level'] == 0.05
        assert 'components' in status

    def test_get_component_summary_detailed(self):
        """Test detailed component summary."""
        # Arrange
        components = {}
        for i in range(3):
            component = self.create_async_mock(f'component_{i}')
            component.get_summary = AsyncMock(return_value={
                'name': f'component_{i}',
                'status': 'running',
                'version': f'1.{i}.0',
                'uptime': 100 + i
            })
            components[f'component_{i}'] = component

        self.orchestrator.components = components

        # Act
        async def run_test():
            return await self.orchestrator.get_component_summary()

        summary = self.run_async(run_test())

        # Assert
        assert len(summary) == 3
        for component_summary in summary:
            assert 'name' in component_summary
            assert 'status' in component_summary

    def test_run_until_shutdown(self):
        """Test main run loop until shutdown."""
        # Arrange
        self.orchestrator.should_shutdown = False

        # Mock the monitoring loops to complete quickly
        with patch.object(self.orchestrator, 'health_monitoring_loop', new_callable=AsyncMock) as mock_health, \
             patch.object(self.orchestrator, 'risk_monitoring_loop', new_callable=AsyncMock) as mock_risk:

            mock_health.side_effect = asyncio.CancelledError("Shutdown")
            mock_risk.return_value = None

            # Act & Assert
            async def run_test():
                try:
                    await self.orchestrator.run_until_shutdown()
                except asyncio.CancelledError:
                    pass  # Expected shutdown

            self.run_async(run_test())

            # Should have started monitoring loops
            mock_health.assert_called()
            mock_risk.assert_called()

    def test_signal_handler_graceful(self):
        """Test signal handler graceful shutdown."""
        # Arrange
        self.orchestrator.should_shutdown = False

        # Act
        async def run_test():
            await self.orchestrator.signal_handler_graceful(signal.SIGTERM)

        self.run_async(run_test())

        # Assert
        assert self.orchestrator.should_shutdown is True
        assert self.orchestrator.shutdown_mode == 'graceful'

    def test_signal_handler_forced(self):
        """Test signal handler forced shutdown."""
        # Arrange
        self.orchestrator.should_shutdown = False

        # Act
        async def run_test():
            await self.orchestrator.signal_handler_forced(signal.SIGKILL)

        self.run_async(run_test())

        # Assert
        assert self.orchestrator.should_shutdown is True
        assert self.orchestrator.shutdown_mode == 'forced'