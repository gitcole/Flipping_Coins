"""
Runtime Health Check and Monitoring System

This module provides continuous runtime monitoring of API connectivity, performance,
and system health. It includes periodic health checks, alerting, and degradation
detection to ensure the trading bot remains operational.

Key Features:
- Periodic connectivity monitoring
- Performance metrics tracking
- Alert system for connectivity degradation
- Health status endpoint for external monitoring
- Automatic recovery detection
- Configurable check intervals and thresholds

Usage:
    >>> from src.core.api.health_check import HealthMonitor
    >>> monitor = HealthMonitor()
    >>> await monitor.start()
    >>> # Monitor runs in background
    >>> status = monitor.get_current_status()
    >>> await monitor.stop()
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import json

import structlog

from ..config import get_settings
from .connectivity_check import ConnectivityChecker, ComprehensiveConnectivityResult
from .exceptions import RobinhoodAPIError

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetrics:
    """Health and performance metrics."""

    # Connectivity metrics
    last_successful_check: Optional[float] = None
    last_failed_check: Optional[float] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    successful_checks: int = 0

    # Performance metrics
    average_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)

    # Error tracking
    recent_errors: List[str] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_checks == 0:
            return 100.0
        return (self.successful_checks / self.total_checks) * 100.0

    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage since first check."""
        if self.last_successful_check is None:
            return 0.0
        total_time = time.time() - self.last_successful_check
        if total_time <= 0:
            return 100.0
        return self.success_rate

    def add_response_time(self, response_time: float) -> None:
        """Add a response time measurement."""
        self.response_times.append(response_time)

        # Update statistics
        self.average_response_time = sum(self.response_times[-100:]) / min(len(self.response_times), 100)
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)

        # Keep only last 100 measurements
        if len(self.response_times) > 100:
            self.response_times.pop(0)

    def record_success(self) -> None:
        """Record a successful check."""
        self.last_successful_check = time.time()
        self.total_checks += 1
        self.successful_checks += 1
        self.consecutive_failures = 0

    def record_failure(self, error: str) -> None:
        """Record a failed check."""
        self.last_failed_check = time.time()
        self.total_checks += 1
        self.consecutive_failures += 1

        # Track error
        self.recent_errors.append(error)
        if len(self.recent_errors) > 10:
            self.recent_errors.pop(0)

        self.error_counts[error] = self.error_counts.get(error, 0) + 1


@dataclass
class HealthAlert:
    """Health alert information."""

    timestamp: float
    level: AlertLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'level': self.level.value,
            'message': self.message,
            'details': self.details,
            'resolved': self.resolved
        }


@dataclass
class HealthStatusReport:
    """Comprehensive health status report."""

    timestamp: float
    status: HealthStatus
    metrics: HealthMetrics
    recent_alerts: List[HealthAlert]
    connectivity_details: Optional[ComprehensiveConnectivityResult] = None
    error_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert status report to dictionary."""
        return {
            'timestamp': self.timestamp,
            'status': self.status.value,
            'metrics': {
                'success_rate': self.metrics.success_rate,
                'uptime_percentage': self.metrics.uptime_percentage,
                'average_response_time': self.metrics.average_response_time,
                'consecutive_failures': self.metrics.consecutive_failures,
                'total_checks': self.metrics.total_checks
            },
            'recent_alerts': [alert.to_dict() for alert in self.recent_alerts],
            'connectivity_details': self.connectivity_details.get_summary() if self.connectivity_details else None,
            'error_summary': self.error_summary
        }


class HealthMonitor:
    """
    Runtime health monitor for continuous API connectivity monitoring.

    This class provides continuous monitoring of API health, performance metrics,
    and automatic alerting when issues are detected.
    """

    def __init__(
        self,
        check_interval: float = 30.0,
        alert_callback: Optional[Callable[[HealthAlert], None]] = None,
        max_alerts: int = 100,
        degradation_threshold: int = 3,
        critical_threshold: int = 5
    ):
        """Initialize health monitor.

        Args:
            check_interval: Time between health checks in seconds
            alert_callback: Function to call when alerts are generated
            max_alerts: Maximum number of alerts to keep in memory
            degradation_threshold: Consecutive failures before degraded status
            critical_threshold: Consecutive failures before critical status
        """
        self.check_interval = check_interval
        self.alert_callback = alert_callback
        self.max_alerts = max_alerts
        self.degradation_threshold = degradation_threshold
        self.critical_threshold = critical_threshold

        self.metrics = HealthMetrics()
        self.alerts: List[HealthAlert] = []
        self.current_status = HealthStatus.HEALTHY
        self.is_running = False
        self.check_task: Optional[asyncio.Task] = None
        self.checker = ConnectivityChecker()

        self.logger = structlog.get_logger(__name__)

    async def start(self) -> None:
        """Start the health monitoring."""
        if self.is_running:
            self.logger.warning("Health monitor already running")
            return

        self.is_running = True
        self.logger.info("Starting health monitor", check_interval=self.check_interval)

        # Run initial check
        await self._run_health_check()

        # Start periodic monitoring
        self.check_task = asyncio.create_task(self._monitoring_loop())

    async def stop(self) -> None:
        """Stop the health monitoring."""
        if not self.is_running:
            return

        self.is_running = False
        self.logger.info("Stopping health monitor")

        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        try:
            while self.is_running:
                await asyncio.sleep(self.check_interval)
                await self._run_health_check()
        except asyncio.CancelledError:
            self.logger.info("Health monitoring loop cancelled")
        except Exception as e:
            self.logger.error("Health monitoring loop error", error=str(e))

    async def _run_health_check(self) -> None:
        """Run a single health check."""
        start_time = time.time()

        try:
            # Run connectivity check
            result = await self.checker.run_comprehensive_check()

            if result.is_healthy:
                self.metrics.record_success()
                self.metrics.add_response_time(result.total_duration_ms)

                # Update status based on consecutive failures
                if self.metrics.consecutive_failures == 0:
                    self.current_status = HealthStatus.HEALTHY
                elif self.metrics.consecutive_failures < self.degradation_threshold:
                    self.current_status = HealthStatus.DEGRADED
                else:
                    self.current_status = HealthStatus.HEALTHY  # Recovered

                self.logger.debug("Health check successful", duration_ms=result.total_duration_ms)

            else:
                error_msg = "; ".join(result.errors)
                self.metrics.record_failure(error_msg)
                self.metrics.add_response_time(result.total_duration_ms)

                # Update status based on failure severity
                if self.metrics.consecutive_failures >= self.critical_threshold:
                    self.current_status = HealthStatus.CRITICAL
                    await self._generate_alert(
                        AlertLevel.CRITICAL,
                        f"Critical connectivity issues detected: {error_msg}",
                        {"consecutive_failures": self.metrics.consecutive_failures}
                    )
                elif self.metrics.consecutive_failures >= self.degradation_threshold:
                    self.current_status = HealthStatus.UNHEALTHY
                    await self._generate_alert(
                        AlertLevel.ERROR,
                        f"Connectivity degraded: {error_msg}",
                        {"consecutive_failures": self.metrics.consecutive_failures}
                    )
                else:
                    self.current_status = HealthStatus.DEGRADED
                    await self._generate_alert(
                        AlertLevel.WARNING,
                        f"Connectivity issues detected: {error_msg}",
                        {"consecutive_failures": self.metrics.consecutive_failures}
                    )

                self.logger.warning("Health check failed", error=error_msg, consecutive_failures=self.metrics.consecutive_failures)

        except Exception as e:
            error_msg = str(e)
            self.metrics.record_failure(error_msg)

            # Update status for unexpected errors
            if self.metrics.consecutive_failures >= self.critical_threshold:
                self.current_status = HealthStatus.CRITICAL
            elif self.metrics.consecutive_failures >= self.degradation_threshold:
                self.current_status = HealthStatus.UNHEALTHY
            else:
                self.current_status = HealthStatus.DEGRADED

            await self._generate_alert(
                AlertLevel.ERROR,
                f"Health check error: {error_msg}",
                {"error_type": type(e).__name__}
            )

            self.logger.error("Health check exception", error=str(e))

    async def _generate_alert(self, level: AlertLevel, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Generate and store an alert."""
        alert = HealthAlert(
            timestamp=time.time(),
            level=level,
            message=message,
            details=details
        )

        self.alerts.append(alert)

        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)

        # Call alert callback if provided
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                self.logger.error("Alert callback error", error=str(e))

        self.logger.info("Health alert generated", level=level.value, message=message)

    def get_current_status(self) -> HealthStatusReport:
        """Get current health status report."""
        # Calculate error summary
        error_summary = {}
        for error in self.metrics.recent_errors:
            error_summary[error] = self.metrics.error_counts.get(error, 0)

        return HealthStatusReport(
            timestamp=time.time(),
            status=self.current_status,
            metrics=self.metrics,
            recent_alerts=self.alerts[-10:],  # Last 10 alerts
            error_summary=error_summary
        )

    def get_status_json(self) -> str:
        """Get current status as JSON string."""
        report = self.get_current_status()
        return json.dumps(report.to_dict(), indent=2)

    async def run_manual_check(self) -> ComprehensiveConnectivityResult:
        """Run a manual connectivity check."""
        self.logger.info("Running manual connectivity check")
        return await self.checker.run_comprehensive_check()

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            'success_rate': self.metrics.success_rate,
            'uptime_percentage': self.metrics.uptime_percentage,
            'average_response_time': self.metrics.average_response_time,
            'min_response_time': self.metrics.min_response_time if self.metrics.min_response_time != float('inf') else 0,
            'max_response_time': self.metrics.max_response_time,
            'consecutive_failures': self.metrics.consecutive_failures,
            'total_checks': self.metrics.total_checks,
            'current_status': self.current_status.value
        }


# Global health monitor instance
_global_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create global health monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = HealthMonitor()
    return _global_monitor


async def start_global_monitor(
    check_interval: float = 30.0,
    alert_callback: Optional[Callable[[HealthAlert], None]] = None
) -> HealthMonitor:
    """Start the global health monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = HealthMonitor(check_interval=check_interval, alert_callback=alert_callback)

    await _global_monitor.start()
    return _global_monitor


async def stop_global_monitor() -> None:
    """Stop the global health monitor."""
    global _global_monitor
    if _global_monitor:
        await _global_monitor.stop()
        _global_monitor = None


def get_health_status() -> HealthStatusReport:
    """Get current health status from global monitor."""
    monitor = get_health_monitor()
    return monitor.get_current_status()


async def health_check_endpoint() -> Dict[str, Any]:
    """Health check endpoint for external monitoring systems."""
    try:
        monitor = get_health_monitor()
        report = monitor.get_current_status()

        # Add additional endpoint-specific information
        return {
            'status': report.status.value,
            'timestamp': report.timestamp,
            'healthy': report.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
            'metrics': report.to_dict()['metrics'],
            'service': 'robinhood-crypto-bot',
            'version': '1.0.0'
        }
    except Exception as e:
        logger.error("Health check endpoint error", error=str(e))
        return {
            'status': 'error',
            'timestamp': time.time(),
            'healthy': False,
            'error': str(e),
            'service': 'robinhood-crypto-bot',
            'version': '1.0.0'
        }


# Convenience functions for quick health checks

async def quick_health_check() -> bool:
    """Quick health check - returns True if system is operational."""
    try:
        monitor = get_health_monitor()
        status = monitor.get_current_status()
        return status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    except Exception:
        return False


async def comprehensive_health_check() -> HealthStatusReport:
    """Run comprehensive health check and return detailed report."""
    monitor = get_health_monitor()
    return monitor.get_current_status()


def print_health_status(report: Optional[HealthStatusReport] = None) -> None:
    """Print health status in human-readable format."""
    if report is None:
        report = get_health_status()

    status_icon = {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.DEGRADED: "⚠️",
        HealthStatus.UNHEALTHY: "❌",
        HealthStatus.CRITICAL: "🚨"
    }.get(report.status, "❓")

    print(f"\n{status_icon} HEALTH STATUS REPORT")
    print("=" * 50)
    print(f"Status: {report.status.value.upper()}")
    print(f"Success Rate: {report.metrics.success_rate:.1f}%")
    print(f"Uptime: {report.metrics.uptime_percentage:.1f}%")
    print(f"Avg Response Time: {report.metrics.average_response_time:.1f}ms")
    print(f"Consecutive Failures: {report.metrics.consecutive_failures}")
    print(f"Total Checks: {report.metrics.total_checks}")

    if report.recent_alerts:
        print(f"\n🚨 Recent Alerts ({len(report.recent_alerts)}):")
        for alert in report.recent_alerts[-5:]:  # Show last 5 alerts
            level_icon = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }.get(alert.level, "❓")
            print(f"   {level_icon} {alert.message}")

    if report.error_summary:
        print("\n❌ Error Summary:")
        for error, count in list(report.error_summary.items())[-5:]:  # Show top 5 errors
            print(f"   • {error} ({count} times)")

    print(f"\n📊 Report generated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.timestamp))}")


# Default alert handlers

def log_alert_handler(alert: HealthAlert) -> None:
    """Default alert handler that logs alerts."""
    logger.info(
        "Health alert",
        level=alert.level.value,
        message=alert.message,
        details=alert.details
    )


def print_alert_handler(alert: HealthAlert) -> None:
    """Alert handler that prints alerts to console."""
    level_icon = {
        AlertLevel.INFO: "ℹ️",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.ERROR: "❌",
        AlertLevel.CRITICAL: "🚨"
    }.get(alert.level, "❓")

    timestamp = time.strftime('%H:%M:%S', time.localtime(alert.timestamp))
    print(f"{level_icon} [{timestamp}] {alert.message}")

    if alert.details:
        print(f"   Details: {alert.details}")


async def console_monitoring_demo() -> None:
    """Demo function showing console monitoring."""
    print("🔍 Starting console health monitoring demo...")
    print("   Press Ctrl+C to stop")

    # Start monitor with console alerts
    monitor = HealthMonitor(
        check_interval=10.0,
        alert_callback=print_alert_handler
    )

    await monitor.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

            # Print status update every 30 seconds
            if int(time.time()) % 30 == 0:
                print_health_status()

    except KeyboardInterrupt:
        print("\n⏹️ Stopping monitoring...")

    await monitor.stop()
    print("✅ Monitoring stopped")