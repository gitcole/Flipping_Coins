"""
Unit tests for API connectivity verification system.

This module tests the comprehensive connectivity checking and health monitoring
functionality to ensure reliable API connectivity verification.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.api.connectivity_check import (
    ConnectivityChecker,
    ConnectivityCheckResult,
    ComprehensiveConnectivityResult,
    HealthStatus
)
from src.core.api.health_check import (
    HealthMonitor,
    HealthMetrics,
    HealthAlert,
    HealthStatusReport,
    health_check_endpoint
)
from src.core.config import initialize_config
from src.core.api.exceptions import APIError, AuthenticationError


class TestConnectivityCheckResult:
    """Test cases for ConnectivityCheckResult."""

    def test_success_result(self):
        """Test successful connectivity check result."""
        result = ConnectivityCheckResult(
            check_name="test_check",
            status=True,
            duration_ms=150.5,
            details={"extra": "info"}
        )

        assert result.check_name == "test_check"
        assert result.status == True
        assert result.duration_ms == 150.5
        assert result.is_success == True
        assert result.details == {"extra": "info"}
        assert result.error is None

    def test_failure_result(self):
        """Test failed connectivity check result."""
        result = ConnectivityCheckResult(
            check_name="test_check",
            status=False,
            duration_ms=200.0,
            error="Connection timeout"
        )

        assert result.check_name == "test_check"
        assert result.status == False
        assert result.duration_ms == 200.0
        assert result.is_success == False
        assert result.error == "Connection timeout"

    def test_string_representation(self):
        """Test string representation of results."""
        success_result = ConnectivityCheckResult("test", True, 100.0)
        failure_result = ConnectivityCheckResult("test", False, 100.0, "Error")

        assert "✅" in str(success_result)
        assert "❌" in str(failure_result)
        assert "test" in str(success_result)
        assert "100.0ms" in str(success_result)


class TestComprehensiveConnectivityResult:
    """Test cases for ComprehensiveConnectivityResult."""

    def test_successful_comprehensive_result(self):
        """Test comprehensive result with all checks passing."""
        checks = [
            ConnectivityCheckResult("check1", True, 100.0),
            ConnectivityCheckResult("check2", True, 150.0)
        ]

        result = ComprehensiveConnectivityResult(
            is_healthy=True,
            total_duration_ms=250.0,
            checks=checks,
            errors=[],
            warnings=[],
            environment_info={"env": "test"}
        )

        assert result.is_healthy == True
        assert result.total_duration_ms == 250.0
        assert len(result.successful_checks) == 2
        assert len(result.failed_checks) == 0
        assert len(result.critical_failures) == 0

    def test_failed_comprehensive_result(self):
        """Test comprehensive result with failures."""
        checks = [
            ConnectivityCheckResult("network", False, 100.0, "No internet"),
            ConnectivityCheckResult("auth", True, 50.0)
        ]

        result = ComprehensiveConnectivityResult(
            is_healthy=False,
            total_duration_ms=150.0,
            checks=checks,
            errors=["Network connectivity failed"],
            warnings=[],
            environment_info={"env": "test"}
        )

        assert result.is_healthy == False
        assert len(result.successful_checks) == 1
        assert len(result.failed_checks) == 1
        assert len(result.critical_failures) == 1  # network is critical

    def test_summary_generation(self):
        """Test summary generation."""
        checks = [
            ConnectivityCheckResult("check1", True, 100.0),
            ConnectivityCheckResult("check2", False, 50.0, "Error")
        ]

        result = ComprehensiveConnectivityResult(
            is_healthy=False,
            total_duration_ms=150.0,
            checks=checks,
            errors=["Error occurred"],
            warnings=["Warning message"],
            environment_info={"env": "production"}
        )

        summary = result.get_summary()

        assert "📊 Connectivity Check Summary" in summary
        assert "✅ Successful: 1/2" in summary
        assert "❌ Failed: 1/2" in summary
        assert "🚨 CRITICAL ISSUES FOUND" in summary
        assert "Error occurred" in summary
        assert "Warning message" in summary


class TestHealthMetrics:
    """Test cases for HealthMetrics."""

    def test_initial_metrics(self):
        """Test initial metrics state."""
        metrics = HealthMetrics()

        assert metrics.total_checks == 0
        assert metrics.successful_checks == 0
        assert metrics.consecutive_failures == 0
        assert metrics.success_rate == 100.0
        assert metrics.uptime_percentage == 0.0

    def test_success_recording(self):
        """Test recording successful checks."""
        metrics = HealthMetrics()

        metrics.record_success()
        assert metrics.total_checks == 1
        assert metrics.successful_checks == 1
        assert metrics.consecutive_failures == 0
        assert metrics.last_successful_check is not None
        assert metrics.success_rate == 100.0

    def test_failure_recording(self):
        """Test recording failed checks."""
        metrics = HealthMetrics()

        metrics.record_failure("Test error")
        assert metrics.total_checks == 1
        assert metrics.consecutive_failures == 1
        assert metrics.last_failed_check is not None
        assert "Test error" in metrics.recent_errors
        assert metrics.error_counts["Test error"] == 1

    def test_response_time_tracking(self):
        """Test response time tracking."""
        metrics = HealthMetrics()

        metrics.add_response_time(100.0)
        metrics.add_response_time(200.0)

        assert len(metrics.response_times) == 2
        assert metrics.average_response_time == 150.0
        assert metrics.min_response_time == 100.0
        assert metrics.max_response_time == 200.0

        # Test rolling window
        for i in range(100):
            metrics.add_response_time(50.0)

        assert len(metrics.response_times) == 100  # Should keep only last 100


class TestHealthAlert:
    """Test cases for HealthAlert."""

    def test_alert_creation(self):
        """Test health alert creation."""
        alert = HealthAlert(
            timestamp=time.time(),
            level=AlertLevel.ERROR,
            message="Test alert",
            details={"key": "value"}
        )

        assert alert.level == AlertLevel.ERROR
        assert alert.message == "Test alert"
        assert alert.details == {"key": "value"}
        assert alert.resolved == False

    def test_alert_serialization(self):
        """Test alert to dictionary conversion."""
        alert = HealthAlert(
            timestamp=1234567890.0,
            level=AlertLevel.WARNING,
            message="Warning message"
        )

        alert_dict = alert.to_dict()

        assert alert_dict["timestamp"] == 1234567890.0
        assert alert_dict["level"] == "warning"
        assert alert_dict["message"] == "Warning message"
        assert alert_dict["resolved"] == False


class TestHealthMonitor:
    """Test cases for HealthMonitor."""

    @pytest.fixture
    def monitor(self):
        """Create health monitor for testing."""
        return HealthMonitor(check_interval=0.1)  # Fast interval for testing

    def test_monitor_initialization(self):
        """Test health monitor initialization."""
        monitor = HealthMonitor(check_interval=30.0)

        assert monitor.check_interval == 30.0
        assert monitor.is_running == False
        assert monitor.current_status == HealthStatus.HEALTHY
        assert len(monitor.alerts) == 0

    @pytest.mark.asyncio
    async def test_manual_check(self, monitor):
        """Test manual connectivity check."""
        with patch.object(monitor.checker, 'run_comprehensive_check') as mock_check:
            mock_result = ComprehensiveConnectivityResult(
                is_healthy=True,
                total_duration_ms=100.0,
                checks=[],
                errors=[],
                warnings=[],
                environment_info={}
            )
            mock_check.return_value = mock_result

            result = await monitor.run_manual_check()

            assert result.is_healthy == True
            mock_check.assert_called_once()

    def test_performance_summary(self, monitor):
        """Test performance summary generation."""
        # Add some test data
        monitor.metrics.record_success()
        monitor.metrics.record_success()
        monitor.metrics.record_failure("Test error")
        monitor.metrics.add_response_time(100.0)
        monitor.metrics.add_response_time(200.0)

        summary = monitor.get_performance_summary()

        assert summary["success_rate"] == pytest.approx(66.67, abs=0.1)
        assert summary["total_checks"] == 3
        assert summary["consecutive_failures"] == 1
        assert summary["current_status"] == "degraded"

    def test_status_report(self, monitor):
        """Test health status report generation."""
        # Add some metrics
        monitor.metrics.record_success()
        monitor.metrics.add_response_time(150.0)

        report = monitor.get_current_status()

        assert isinstance(report, HealthStatusReport)
        assert report.status == HealthStatus.HEALTHY
        assert report.metrics.total_checks == 1
        assert report.timestamp is not None

        # Test JSON serialization
        json_str = monitor.get_status_json()
        assert "healthy" in json_str.lower()
        assert "success_rate" in json_str


class TestConnectivityChecker:
    """Test cases for ConnectivityChecker."""

    @pytest.fixture
    def checker(self):
        """Create connectivity checker for testing."""
        return ConnectivityChecker(timeout=1.0)

    @pytest.mark.asyncio
    async def test_network_connectivity_success(self, checker):
        """Test successful network connectivity check."""
        with patch('socket.gethostbyname') as mock_gethostbyname, \
             patch('socket.socket') as mock_socket:

            mock_gethostbyname.return_value = "104.18.0.1"
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            result = await checker._check_network_connectivity()

            assert result.status == True
            assert result.check_name == "network_connectivity"
            mock_gethostbyname.assert_called_once()

    @pytest.mark.asyncio
    async def test_network_connectivity_failure(self, checker):
        """Test failed network connectivity check."""
        with patch('socket.gethostbyname', side_effect=socket.gaierror("DNS failure")):
            result = await checker._check_network_connectivity()

            assert result.status == False
            assert "DNS resolution failed" in result.error

    @pytest.mark.asyncio
    async def test_ssl_certificate_check(self, checker):
        """Test SSL certificate validation."""
        with patch('ssl.create_default_context') as mock_context, \
             patch('socket.create_connection') as mock_socket:

            # Mock SSL context and certificate
            mock_context.return_value.wrap_socket.return_value.getpeercert.return_value = {
                'notAfter': 'Dec 31 23:59:59 2025 GMT',
                'issuer': [('organizationName', 'DigiCert Inc')],
                'subject': [[('commonName', 'trading.robinhood.com')]]
            }

            result = await checker._check_ssl_certificates()

            assert result.status == True
            assert result.check_name == "ssl_certificate"

    @pytest.mark.asyncio
    async def test_configuration_check_success(self, checker):
        """Test successful configuration validation."""
        with patch('src.core.api.connectivity_check.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.robinhood.api_key = "test_key"
            mock_settings.robinhood.private_key = "test_private_key"
            mock_settings.robinhood.public_key = None
            mock_settings.robinhood.sandbox = False
            mock_get_settings.return_value = mock_settings

            result = await checker._check_configuration()

            assert result.status == True
            assert result.check_name == "configuration_validation"

    @pytest.mark.asyncio
    async def test_configuration_check_failure(self, checker):
        """Test failed configuration validation."""
        with patch('src.core.api.connectivity_check.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.robinhood = None  # Missing robinhood config
            mock_get_settings.return_value = mock_settings

            result = await checker._check_configuration()

            assert result.status == False
            assert "Configuration issues" in result.error

    @pytest.mark.asyncio
    async def test_authentication_check_success(self, checker):
        """Test successful authentication validation."""
        with patch('src.core.api.connectivity_check.RobinhoodSignatureAuth') as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.is_authenticated.return_value = True
            mock_auth.get_auth_info.return_value = {
                "auth_type": "private_key",
                "sandbox": False,
                "api_key_prefix": "test..."
            }
            mock_auth_class.return_value = mock_auth

            result = await checker._check_authentication(sandbox=False)

            assert result.status == True
            assert result.check_name == "authentication_validation"

    @pytest.mark.asyncio
    async def test_authentication_check_failure(self, checker):
        """Test failed authentication validation."""
        with patch('src.core.api.connectivity_check.RobinhoodSignatureAuth') as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.is_authenticated.return_value = False
            mock_auth_class.return_value = mock_auth

            result = await checker._check_authentication(sandbox=False)

            assert result.status == False
            assert "Authentication not properly configured" in result.error

    @pytest.mark.asyncio
    async def test_api_functionality_check(self, checker):
        """Test API functionality check."""
        with patch('src.core.api.connectivity_check.RobinhoodClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.initialize = AsyncMock()
            mock_client.get_user = AsyncMock(return_value={"id": "user123"})
            mock_client_class.return_value = mock_client

            result = await checker._check_api_functionality(sandbox=True)

            assert result.status == True
            assert result.check_name == "api_functionality"

    @pytest.mark.asyncio
    async def test_environment_check_success(self, checker):
        """Test successful environment check."""
        with patch('psutil.cpu_count', return_value=4), \
             patch('psutil.virtual_memory') as mock_memory:

            mock_memory.return_value.total = 8 * 1024**3  # 8GB

            result = await checker._check_environment()

            assert result.status == True
            assert result.check_name == "environment_check"
            assert "cpu_count" in result.details

    @pytest.mark.asyncio
    async def test_comprehensive_check_success(self, checker):
        """Test comprehensive check with all passing."""
        with patch.object(checker, '_check_network_connectivity') as mock_network, \
             patch.object(checker, '_check_ssl_certificates') as mock_ssl, \
             patch.object(checker, '_check_api_endpoints') as mock_api, \
             patch.object(checker, '_check_configuration') as mock_config, \
             patch.object(checker, '_check_authentication') as mock_auth, \
             patch.object(checker, '_check_api_functionality') as mock_functionality, \
             patch.object(checker, '_check_environment') as mock_env:

            # Mock all checks to succeed
            mock_network.return_value = ConnectivityCheckResult("network", True, 100.0)
            mock_ssl.return_value = ConnectivityCheckResult("ssl", True, 50.0)
            mock_api.return_value = ConnectivityCheckResult("api", True, 75.0)
            mock_config.return_value = ConnectivityCheckResult("config", True, 25.0)
            mock_auth.return_value = ConnectivityCheckResult("auth", True, 30.0)
            mock_functionality.return_value = ConnectivityCheckResult("functionality", True, 200.0)
            mock_env.return_value = ConnectivityCheckResult("env", True, 10.0)

            result = await checker.run_comprehensive_check()

            assert result.is_healthy == True
            assert len(result.checks) == 7
            assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_comprehensive_check_with_failures(self, checker):
        """Test comprehensive check with some failures."""
        with patch.object(checker, '_check_network_connectivity') as mock_network, \
             patch.object(checker, '_check_configuration') as mock_config, \
             patch.object(checker, '_check_authentication') as mock_auth:

            # Mock critical checks to fail
            mock_network.return_value = ConnectivityCheckResult("network", False, 100.0, "No connection")
            mock_config.return_value = ConnectivityCheckResult("config", True, 25.0)
            mock_auth.return_value = ConnectivityCheckResult("auth", True, 30.0)

            result = await checker.run_comprehensive_check()

            assert result.is_healthy == False
            assert len(result.critical_failures) == 1
            assert "Network connectivity failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_quick_check(self, checker):
        """Test quick connectivity check."""
        with patch.object(checker, 'run_comprehensive_check') as mock_comprehensive:
            mock_result = ComprehensiveConnectivityResult(
                is_healthy=True,
                total_duration_ms=100.0,
                checks=[],
                errors=[],
                warnings=[],
                environment_info={}
            )
            mock_comprehensive.return_value = mock_result

            is_ready = await checker.run_quick_check()

            assert is_ready == True
            mock_comprehensive.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Test health check endpoint."""
    with patch('src.core.api.health_check.get_health_monitor') as mock_get_monitor:
        mock_monitor = MagicMock()
        mock_report = HealthStatusReport(
            timestamp=time.time(),
            status=HealthStatus.HEALTHY,
            metrics=HealthMetrics(),
            recent_alerts=[],
            error_summary={}
        )
        mock_monitor.get_current_status.return_value = mock_report
        mock_get_monitor.return_value = mock_monitor

        result = await health_check_endpoint()

        assert result["status"] == "healthy"
        assert result["healthy"] == True
        assert "service" in result


@pytest.mark.asyncio
async def test_console_monitoring_demo():
    """Test console monitoring demo (basic smoke test)."""
    with patch('asyncio.sleep'), \
         patch('src.core.api.health_check.console_monitoring_demo') as mock_demo:

        # This is a smoke test - we don't want to actually run the demo
        # as it would run indefinitely
        pass


class TestIntegration:
    """Integration tests for the connectivity verification system."""

    @pytest.mark.asyncio
    async def test_end_to_end_verification_flow(self):
        """Test complete verification flow."""
        checker = ConnectivityChecker(timeout=1.0)

        # Test with mocked responses
        with patch.object(checker, '_check_network_connectivity') as mock_network, \
             patch.object(checker, '_check_ssl_certificates') as mock_ssl, \
             patch.object(checker, '_check_configuration') as mock_config, \
             patch.object(checker, '_check_authentication') as mock_auth, \
             patch.object(checker, '_check_environment') as mock_env:

            # Mock all checks to succeed quickly
            mock_network.return_value = ConnectivityCheckResult("network", True, 10.0)
            mock_ssl.return_value = ConnectivityCheckResult("ssl", True, 15.0)
            mock_config.return_value = ConnectivityCheckResult("config", True, 5.0)
            mock_auth.return_value = ConnectivityCheckResult("auth", True, 8.0)
            mock_env.return_value = ConnectivityCheckResult("env", True, 3.0)

            result = await checker.run_comprehensive_check()

            # Verify result structure
            assert isinstance(result, ComprehensiveConnectivityResult)
            assert result.is_healthy == True
            assert len(result.checks) == 5  # All our mocked checks
            assert result.total_duration_ms > 0

    def test_troubleshooting_guide_generation(self):
        """Test troubleshooting guide generation."""
        checker = ConnectivityChecker()

        # Create a result with failures
        checks = [
            ConnectivityCheckResult("network", False, 100.0, "Connection timeout"),
            ConnectivityCheckResult("auth", False, 50.0, "Invalid credentials"),
            ConnectivityCheckResult("config", True, 25.0)
        ]

        result = ComprehensiveConnectivityResult(
            is_healthy=False,
            total_duration_ms=175.0,
            checks=checks,
            errors=["Network failed", "Auth failed"],
            warnings=[],
            environment_info={"env": "production"}
        )

        guide = checker.get_troubleshooting_guide(result)

        assert "TROUBLESHOOTING GUIDE" in guide
        assert "CRITICAL ISSUES FOUND" in guide
        assert "Network Connectivity Issue" in guide
        assert "Authentication Issue" in guide
        assert "General Troubleshooting Steps" in guide


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])