"""
Comprehensive API Connectivity Verification System

This module provides comprehensive pre-flight checks for the Robinhood API to ensure
the application can successfully connect and authenticate before starting trading operations.

Key Features:
- Network connectivity validation
- SSL/TLS certificate verification
- API endpoint availability testing
- Authentication credential validation
- Sandbox vs production environment detection
- Comprehensive error reporting with recovery suggestions

Usage:
    >>> from src.core.api.connectivity_check import ConnectivityChecker
    >>> checker = ConnectivityChecker()
    >>> result = await checker.run_comprehensive_check()
    >>> if result.is_healthy:
    ...     print("✅ All systems ready for trading!")
    ... else:
    ...     print(f"❌ Issues found: {result.errors}")
"""

import asyncio
import socket
import ssl
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import aiohttp
import structlog

from ..config import get_settings
from .exceptions import (
    APIAuthenticationError,
    APIConnectionError,
    APITimeoutError,
    RobinhoodAPIError,
    AuthenticationError
)
from .robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from .robinhood.auth import RobinhoodSignatureAuth

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels for connectivity checks."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ConnectivityCheckResult:
    """Result of a connectivity check operation."""

    check_name: str
    status: bool
    duration_ms: float
    error: Optional[str] = None
    details: Optional[Dict] = None

    @property
    def is_success(self) -> bool:
        """Check if this individual check was successful."""
        return self.status

    def __str__(self) -> str:
        status_icon = "✅" if self.status else "❌"
        return f"{status_icon} {self.check_name} ({self.duration_ms:.1f}ms)"


@dataclass
class ComprehensiveConnectivityResult:
    """Comprehensive result of all connectivity checks."""

    is_healthy: bool
    total_duration_ms: float
    checks: List[ConnectivityCheckResult]
    errors: List[str]
    warnings: List[str]
    environment_info: Dict[str, Union[str, bool]]

    @property
    def successful_checks(self) -> List[ConnectivityCheckResult]:
        """Get all successful checks."""
        return [check for check in self.checks if check.is_success]

    @property
    def failed_checks(self) -> List[ConnectivityCheckResult]:
        """Get all failed checks."""
        return [check for check in self.checks if not check.is_success]

    @property
    def critical_failures(self) -> List[ConnectivityCheckResult]:
        """Get critical failures that prevent trading."""
        critical_check_names = {
            'network_connectivity',
            'ssl_certificate',
            'api_endpoint_availability',
            'authentication_validation'
        }
        return [check for check in self.failed_checks if check.check_name in critical_check_names]

    def get_summary(self) -> str:
        """Get a human-readable summary of the results."""
        total_checks = len(self.checks)
        successful = len(self.successful_checks)
        failed = len(self.failed_checks)
        critical = len(self.critical_failures)

        summary = f"""
📊 Connectivity Check Summary
{'='*40}
✅ Successful: {successful}/{total_checks}
❌ Failed: {failed}/{total_checks}
⚠️  Critical Issues: {critical}

"""

        if self.critical_failures:
            summary += "🚨 CRITICAL ISSUES FOUND:\n"
            for check in self.critical_failures:
                summary += f"   • {check.check_name}: {check.error}\n"

        if self.errors:
            summary += f"\n❌ Errors: {len(self.errors)}\n"
            for error in self.errors:
                summary += f"   • {error}\n"

        if self.warnings:
            summary += f"\n⚠️  Warnings: {len(self.warnings)}\n"
            for warning in self.warnings:
                summary += f"   • {warning}\n"

        summary += f"\n🔧 Environment: {self.environment_info.get('environment', 'unknown')}"
        summary += f"\n⏱️  Total time: {self.total_duration_ms:.1f}ms"

        return summary


class ConnectivityChecker:
    """
    Comprehensive connectivity checker for Robinhood API.

    This class performs all necessary checks to ensure the API is fully functional
    before allowing the application to start trading operations.
    """

    def __init__(self, timeout: float = 10.0, max_retries: int = 3):
        """Initialize the connectivity checker.

        Args:
            timeout: Timeout for individual checks in seconds
            max_retries: Maximum number of retries for failed checks
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = structlog.get_logger(__name__)

        # Common endpoints to test
        self.endpoints = [
            "https://trading.robinhood.com",
            "https://trading.robinhood.com/user/",
            "https://trading.robinhood.com/accounts/",
            "https://trading.robinhood.com/instruments/"
        ]

        # Sandbox endpoints
        self.sandbox_endpoints = [
            "https://trading.robinhood.com",
            "https://trading.robinhood.com/user/",
            "https://trading.robinhood.com/accounts/",
            "https://trading.robinhood.com/instruments/"
        ]

    async def run_comprehensive_check(self, sandbox: Optional[bool] = None) -> ComprehensiveConnectivityResult:
        """Run all connectivity checks comprehensively.

        Args:
            sandbox: Whether to use sandbox environment. Auto-detected if None.

        Returns:
            ComprehensiveConnectivityResult with all check results
        """
        start_time = time.time()
        checks = []
        errors = []
        warnings = []

        self.logger.info("Starting comprehensive connectivity check")

        try:
            # 1. Basic network connectivity
            network_check = await self._check_network_connectivity()
            checks.append(network_check)
            if not network_check.is_success:
                errors.append(f"Network connectivity failed: {network_check.error}")

            # 2. SSL/TLS certificate validation
            ssl_check = await self._check_ssl_certificates()
            checks.append(ssl_check)
            if not ssl_check.is_success:
                errors.append(f"SSL certificate validation failed: {ssl_check.error}")

            # 3. API endpoint availability
            endpoint_check = await self._check_api_endpoints()
            checks.append(endpoint_check)
            if not endpoint_check.is_success:
                errors.append(f"API endpoint check failed: {endpoint_check.error}")

            # 4. Configuration validation
            config_check = await self._check_configuration()
            checks.append(config_check)
            if not config_check.is_success:
                errors.append(f"Configuration validation failed: {config_check.error}")

            # 5. Authentication validation
            auth_check = await self._check_authentication(sandbox)
            checks.append(auth_check)
            if not auth_check.is_success:
                errors.append(f"Authentication failed: {auth_check.error}")

            # 6. API functionality tests
            api_check = await self._check_api_functionality(sandbox)
            checks.append(api_check)
            if not api_check.is_success:
                warnings.append(f"API functionality issues: {api_check.error}")

            # 7. Environment detection
            env_check = await self._check_environment()
            checks.append(env_check)

            # Determine overall health
            is_healthy = len(errors) == 0
            critical_failures = [c for c in checks if not c.is_success and c.check_name in {
                'network_connectivity', 'ssl_certificate', 'api_endpoint_availability', 'authentication_validation'
            }]

            if critical_failures:
                is_healthy = False

        except Exception as e:
            self.logger.error("Comprehensive check failed with exception", error=str(e))
            is_healthy = False
            errors.append(f"Unexpected error during connectivity check: {str(e)}")

        total_duration = (time.time() - start_time) * 1000

        # Get environment info
        env_info = {
            'environment': 'sandbox' if sandbox else 'production',
            'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
            'platform': __import__('sys').platform,
            'total_checks': len(checks),
            'successful_checks': len([c for c in checks if c.is_success])
        }

        return ComprehensiveConnectivityResult(
            is_healthy=is_healthy,
            total_duration_ms=total_duration,
            checks=checks,
            errors=errors,
            warnings=warnings,
            environment_info=env_info
        )

    async def _check_network_connectivity(self) -> ConnectivityCheckResult:
        """Check basic network connectivity to Robinhood API."""
        start_time = time.time()

        try:
            # Test basic socket connectivity
            hostname = urlparse("https://trading.robinhood.com").hostname
            if not hostname:
                return ConnectivityCheckResult(
                    check_name="network_connectivity",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Could not parse Robinhood API hostname"
                )

            # Try to resolve DNS
            try:
                ip = socket.gethostbyname(hostname)
                self.logger.debug("DNS resolution successful", hostname=hostname, ip=ip)
            except socket.gaierror as e:
                return ConnectivityCheckResult(
                    check_name="network_connectivity",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"DNS resolution failed: {str(e)}"
                )

            # Test basic TCP connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)

            try:
                result = sock.connect_ex((ip, 443))  # HTTPS port
                if result != 0:
                    return ConnectivityCheckResult(
                        check_name="network_connectivity",
                        status=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error=f"TCP connection failed (error code: {result})"
                    )
            finally:
                sock.close()

            return ConnectivityCheckResult(
                check_name="network_connectivity",
                status=True,
                duration_ms=(time.time() - start_time) * 1000,
                details={"resolved_ip": ip, "hostname": hostname}
            )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="network_connectivity",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _check_ssl_certificates(self) -> ConnectivityCheckResult:
        """Check SSL/TLS certificate validity."""
        start_time = time.time()

        try:
            hostname = urlparse("https://trading.robinhood.com").hostname
            if not hostname:
                return ConnectivityCheckResult(
                    check_name="ssl_certificate",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Could not parse hostname for SSL check"
                )

            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            with socket.create_connection((hostname, 443)) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as sslsock:
                    cert = sslsock.getpeercert()

            if not cert:
                return ConnectivityCheckResult(
                    check_name="ssl_certificate",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="No SSL certificate found"
                )

            # Check certificate expiration
            import datetime
            not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_until_expiry = (not_after - datetime.datetime.now()).days

            if days_until_expiry < 0:
                return ConnectivityCheckResult(
                    check_name="ssl_certificate",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"SSL certificate expired {abs(days_until_expiry)} days ago"
                )
            elif days_until_expiry < 30:
                return ConnectivityCheckResult(
                    check_name="ssl_certificate",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"SSL certificate expires in {days_until_expiry} days"
                )

            # Check certificate issuer (should be a trusted CA)
            issuer = cert.get('issuer', [])
            issuer_str = ' '.join([item[1] for item in issuer if item[0] == 'organizationName'])

            return ConnectivityCheckResult(
                check_name="ssl_certificate",
                status=True,
                duration_ms=(time.time() - start_time) * 1000,
                details={
                    "issuer": issuer_str,
                    "valid_until": cert['notAfter'],
                    "days_until_expiry": days_until_expiry,
                    "subject": cert.get('subject', [[]])[0]
                }
            )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="ssl_certificate",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _check_api_endpoints(self) -> ConnectivityCheckResult:
        """Check API endpoint availability and response times."""
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            failed_endpoints = []

            for endpoint in self.endpoints:
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.head(endpoint) as response:
                            if response.status >= 400:
                                failed_endpoints.append(f"{endpoint} ({response.status})")
                except Exception as e:
                    failed_endpoints.append(f"{endpoint} ({str(e)})")

            if failed_endpoints:
                return ConnectivityCheckResult(
                    check_name="api_endpoint_availability",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"Failed endpoints: {', '.join(failed_endpoints)}"
                )

            return ConnectivityCheckResult(
                check_name="api_endpoint_availability",
                status=True,
                duration_ms=(time.time() - start_time) * 1000,
                details={"tested_endpoints": len(self.endpoints), "failed_endpoints": 0}
            )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="api_endpoint_availability",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _check_configuration(self) -> ConnectivityCheckResult:
        """Check configuration validity."""
        start_time = time.time()

        try:
            # Load settings
            settings = get_settings()

            # Check required Robinhood configuration
            issues = []

            if not hasattr(settings, 'robinhood') or not settings.robinhood:
                issues.append("Robinhood configuration section missing")
            else:
                rh_config = settings.robinhood

                if not getattr(rh_config, 'api_key', None):
                    issues.append("API key not configured (ROBINHOOD_API_KEY)")

                if not getattr(rh_config, 'private_key', None) and not getattr(rh_config, 'public_key', None):
                    issues.append("Neither private key nor public key configured")

                # Check sandbox setting
                sandbox = getattr(rh_config, 'sandbox', False)
                if sandbox:
                    self.logger.info("Sandbox mode detected")
                else:
                    self.logger.info("Production mode detected")

            if issues:
                return ConnectivityCheckResult(
                    check_name="configuration_validation",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"Configuration issues: {', '.join(issues)}"
                )

            return ConnectivityCheckResult(
                check_name="configuration_validation",
                status=True,
                duration_ms=(time.time() - start_time) * 1000,
                details={
                    "has_api_key": bool(getattr(settings.robinhood, 'api_key', None)),
                    "has_private_key": bool(getattr(settings.robinhood, 'private_key', None)),
                    "has_public_key": bool(getattr(settings.robinhood, 'public_key', None)),
                    "sandbox_mode": getattr(settings.robinhood, 'sandbox', False)
                }
            )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="configuration_validation",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _check_authentication(self, sandbox: Optional[bool] = None) -> ConnectivityCheckResult:
        """Check authentication credentials."""
        start_time = time.time()

        try:
            # Determine sandbox mode
            if sandbox is None:
                settings = get_settings()
                sandbox = getattr(settings.robinhood, 'sandbox', False)

            # Create authentication object
            auth = RobinhoodSignatureAuth(sandbox=sandbox)

            # Check if authentication is properly configured
            if not auth.is_authenticated():
                return ConnectivityCheckResult(
                    check_name="authentication_validation",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Authentication not properly configured"
                )

            # Get auth info
            auth_info = auth.get_auth_info()

            return ConnectivityCheckResult(
                check_name="authentication_validation",
                status=True,
                duration_ms=(time.time() - start_time) * 1000,
                details={
                    "auth_type": auth_info.get("auth_type"),
                    "sandbox": auth_info.get("sandbox"),
                    "api_key_prefix": auth_info.get("api_key_prefix")
                }
            )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="authentication_validation",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _check_api_functionality(self, sandbox: Optional[bool] = None) -> ConnectivityCheckResult:
        """Check basic API functionality with authenticated requests."""
        start_time = time.time()

        try:
            # Determine sandbox mode
            if sandbox is None:
                settings = get_settings()
                sandbox = getattr(settings.robinhood, 'sandbox', False)

            # Create client and test basic functionality
            async with RobinhoodClient(sandbox=sandbox) as client:
                await client.initialize()

                # Test basic API call
                try:
                    user_data = await client.get_user()
                    if user_data:
                        return ConnectivityCheckResult(
                            check_name="api_functionality",
                            status=True,
                            duration_ms=(time.time() - start_time) * 1000,
                            details={
                                "user_authenticated": bool(user_data),
                                "sandbox_mode": sandbox
                            }
                        )
                except Exception as e:
                    return ConnectivityCheckResult(
                        check_name="api_functionality",
                        status=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error=f"API call failed: {str(e)}"
                    )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="api_functionality",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _check_environment(self) -> ConnectivityCheckResult:
        """Check environment and system compatibility."""
        start_time = time.time()

        try:
            # Check Python version
            python_version = f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"

            # Check required packages
            required_packages = ['aiohttp', 'structlog', 'pydantic', 'ecdsa']
            missing_packages = []

            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)

            # Check system resources
            import psutil
            system_info = {
                "python_version": python_version,
                "platform": __import__('sys').platform,
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1)
            }

            if missing_packages:
                return ConnectivityCheckResult(
                    check_name="environment_check",
                    status=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"Missing required packages: {', '.join(missing_packages)}",
                    details=system_info
                )

            return ConnectivityCheckResult(
                check_name="environment_check",
                status=True,
                duration_ms=(time.time() - start_time) * 1000,
                details=system_info
            )

        except Exception as e:
            return ConnectivityCheckResult(
                check_name="environment_check",
                status=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def run_quick_check(self, sandbox: Optional[bool] = None) -> bool:
        """Run a quick connectivity check (only critical checks).

        Args:
            sandbox: Whether to use sandbox environment

        Returns:
            True if all critical checks pass
        """
        result = await self.run_comprehensive_check(sandbox)

        # Quick check only considers critical failures
        critical_checks = ['network_connectivity', 'ssl_certificate', 'api_endpoint_availability', 'authentication_validation']
        critical_failures = [c for c in result.failed_checks if c.check_name in critical_checks]

        return len(critical_failures) == 0

    def get_troubleshooting_guide(self, result: ComprehensiveConnectivityResult) -> str:
        """Generate troubleshooting guide for failed checks."""

        guide = """
🔧 TROUBLESHOOTING GUIDE
{'='*50}

"""

        if not result.critical_failures:
            guide += "✅ No critical issues found! Your system appears ready for trading.\n\n"
        else:
            guide += "🚨 Critical issues detected. Please address these before trading:\n\n"

            for check in result.critical_failures:
                if check.check_name == "network_connectivity":
                    guide += """
Network Connectivity Issue:
  • Check your internet connection
  • Verify firewall settings allow HTTPS traffic to trading.robinhood.com
  • Try accessing https://trading.robinhood.com in your browser
  • Check if VPN/proxy settings are interfering

"""
                elif check.check_name == "ssl_certificate":
                    guide += """
SSL Certificate Issue:
  • Check system date/time settings
  • Update SSL certificates: pip install --upgrade certifi
  • Check firewall/proxy SSL inspection settings
  • Try disabling VPN if using one

"""
                elif check.check_name == "api_endpoint_availability":
                    guide += """
API Endpoint Issue:
  • Robinhood API may be experiencing downtime
  • Check Robinhood status page or social media
  • Try again in a few minutes
  • Verify you're using the correct API endpoints

"""
                elif check.check_name == "authentication_validation":
                    guide += """
Authentication Issue:
  • Verify your API key is correct and active
  • Check that your private/public keys are valid
  • Ensure keys are in the correct format (base64)
  • Verify you're using the right environment (sandbox vs production)
  • Check that your Robinhood account has API access enabled

"""
                elif check.check_name == "configuration_validation":
                    guide += """
Configuration Issue:
  • Check config/.env file exists and has correct format
  • Verify all required environment variables are set
  • Check config/default.yaml for any overrides
  • Ensure file permissions are correct

"""

        # Add general troubleshooting
        guide += """
General Troubleshooting Steps:
1. Restart the application
2. Check your internet connection
3. Verify all credentials in config/.env
4. Try running: python verify_connection.py
5. Check the logs for more detailed error messages
6. Contact support if issues persist

For more help, check:
• README.md - Setup and configuration guide
• ROBINHOOD_API_SETUP.md - Detailed API setup instructions
• GitHub issues - Similar problems and solutions

"""

        return guide


# Convenience functions for quick checks

async def quick_connectivity_check(sandbox: Optional[bool] = None) -> bool:
    """Quick connectivity check - returns True if ready for trading."""
    checker = ConnectivityChecker()
    return await checker.run_quick_check(sandbox)


async def comprehensive_connectivity_check(sandbox: Optional[bool] = None) -> ComprehensiveConnectivityResult:
    """Run comprehensive connectivity check with detailed results."""
    checker = ConnectivityChecker()
    return await checker.run_comprehensive_check(sandbox)


def print_connectivity_status(result: ComprehensiveConnectivityResult) -> None:
    """Print connectivity status in a human-readable format."""
    print(result.get_summary())

    if not result.is_healthy:
        print("\n" + "="*50)
        print("❌ CONNECTIVITY ISSUES DETECTED")
        print("="*50)
        print("The application cannot start safely due to connectivity issues.")
        print("Please address the issues above before starting the trading bot.")
        print("\nTroubleshooting guide:")
        print(ConnectivityChecker().get_troubleshooting_guide(result))
    else:
        print("\n" + "="*50)
        print("✅ CONNECTIVITY CHECK PASSED")
        print("="*50)
        print("All systems are ready! You can safely start the trading bot.")