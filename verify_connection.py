#!/usr/bin/env python3
"""
Standalone Robinhood API Connection Verification Script

This script provides a comprehensive standalone tool for testing Robinhood API connectivity,
authentication, and configuration without starting the full trading application.

Usage:
    python verify_connection.py                    # Run comprehensive check
    python verify_connection.py --quick           # Quick connectivity test only
    python verify_connection.py --sandbox         # Test sandbox environment
    python verify_connection.py --help            # Show help

Features:
- Network connectivity testing
- SSL/TLS certificate validation
- Configuration validation
- Authentication credential verification
- API endpoint availability testing
- Performance metrics
- Detailed troubleshooting guidance

Exit codes:
- 0: All checks passed successfully
- 1: Critical connectivity issues detected
- 2: Configuration or authentication issues
- 3: Unexpected errors during testing
"""

import argparse
import asyncio
import sys
import time
from typing import Optional

from src.core.api.connectivity_check import (
    ConnectivityChecker,
    ComprehensiveConnectivityResult,
    print_connectivity_status
)
from src.core.api.health_check import print_health_status
from src.core.config import initialize_config
from src.utils.logging import setup_logging


def print_banner():
    """Print the verification script banner."""
    print("🔍 Robinhood Crypto Bot - Connection Verification")
    print("=" * 55)
    print("   Comprehensive API connectivity and authentication testing")
    print("   Run this script before starting the trading bot")
    print()


def print_usage_examples():
    """Print usage examples."""
    print("📋 Usage Examples:")
    print("   python verify_connection.py              # Full comprehensive check")
    print("   python verify_connection.py --quick      # Quick connectivity test")
    print("   python verify_connection.py --sandbox    # Test sandbox environment")
    print("   python verify_connection.py --verbose    # Detailed output")
    print("   python verify_connection.py --help       # Show this help")
    print()


async def run_comprehensive_verification(sandbox: Optional[bool] = None, verbose: bool = False) -> int:
    """Run comprehensive connectivity verification.

    Args:
        sandbox: Whether to test sandbox environment
        verbose: Whether to show detailed output

    Returns:
        Exit code (0 for success, non-zero for issues)
    """
    print("🚀 Starting comprehensive connectivity verification...")
    print(f"   Environment: {'Sandbox' if sandbox else 'Production'}")
    print(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print()

    try:
        # Initialize configuration
        print("⚙️  Initializing configuration...")
        initialize_config()
        setup_logging()
        print("   ✅ Configuration loaded successfully")
        print()

        # Run connectivity check
        checker = ConnectivityChecker()
        result = await checker.run_comprehensive_check(sandbox)

        # Display results
        print_connectivity_status(result)

        if verbose:
            print("\n📊 Detailed Performance Metrics:")
            print(f"   Total execution time: {result.total_duration_ms:.1f}ms")
            successful_checks = len(result.successful_checks)
            failed_checks = len(result.failed_checks)
            print(f"   Check results: {successful_checks} passed, {failed_checks} failed")

            if result.successful_checks:
                print("   ✅ Successful checks:")
                for check in result.successful_checks:
                    print(f"      • {check.check_name} ({check.duration_ms:.1f}ms)")
            if result.failed_checks:
                print("   ❌ Failed checks:")
                for check in result.failed_checks:
                    print(f"      • {check.check_name}: {check.error}")

        # Determine exit code
        if not result.is_healthy:
            print("\n❌ VERIFICATION FAILED")
            print("=" * 30)
            print("Critical connectivity issues were detected.")
            print("Please address these issues before starting the trading bot.")

            if result.critical_failures:
                print("\n🚨 Critical failures that prevent trading:")
                for failure in result.critical_failures:
                    print(f"   • {failure.check_name}: {failure.error}")

            print("\n🔧 Troubleshooting steps:")
            print("   1. Check your internet connection")
            print("   2. Verify API credentials in config/.env")
            print("   3. Check if Robinhood API is operational")
            print("   4. Review the detailed error messages above")
            print("   5. Try running: python verify_connection.py --quick")

            # Critical issues = exit code 1
            if result.critical_failures:
                return 1
            # Non-critical issues = exit code 2
            else:
                return 2

        print("\n" + "="*50)
        print("✅ VERIFICATION SUCCESSFUL")
        print("="*50)
        print("All connectivity checks passed! Your system is ready for trading.")
        print("\n🚀 You can now safely start the trading bot:")
        print("   python -m src")
        print("\n💡 Tips:")
        print("   • Run this verification script regularly")
        print("   • Check connectivity before market hours")
        print("   • Monitor for any degradation warnings")

        return 0

    except KeyboardInterrupt:
        print("\n⏹️  Verification cancelled by user")
        return 3
    except Exception as e:
        print(f"\n❌ Unexpected error during verification: {str(e)}")
        print("   This may indicate a configuration or environment issue")
        print("\n🔧 Troubleshooting:")
        print("   1. Check that config/.env file exists")
        print("   2. Verify all required dependencies are installed")
        print("   3. Check file permissions")
        print("   4. Try: pip install -r requirements.txt")
        return 3


async def run_quick_verification(sandbox: Optional[bool] = None) -> int:
    """Run quick connectivity verification.

    Args:
        sandbox: Whether to test sandbox environment

    Returns:
        Exit code (0 for success, non-zero for issues)
    """
    print("⚡ Running quick connectivity check...")
    print(f"   Environment: {'Sandbox' if sandbox else 'Production'}")
    print()

    try:
        checker = ConnectivityChecker()
        is_ready = await checker.run_quick_check(sandbox)

        if is_ready:
            print("✅ Quick check passed! System is ready for trading.")
            print("\n🚀 You can start the trading bot:")
            print("   python -m src")
            return 0
        else:
            print("❌ Quick check failed! Connectivity issues detected.")
            print("\n🔧 Run comprehensive check for detailed diagnostics:")
            print("   python verify_connection.py")
            return 1

    except Exception as e:
        print(f"❌ Error during quick check: {str(e)}")
        return 3


async def run_health_monitoring_demo(sandbox: Optional[bool] = None) -> int:
    """Run health monitoring demo."""
    print("📊 Starting health monitoring demo...")
    print("   This will run continuous monitoring for 60 seconds")
    print("   Press Ctrl+C to stop early")
    print()

    try:
        from src.core.api.health_check import console_monitoring_demo
        await console_monitoring_demo()
        print("\n✅ Health monitoring demo completed")
        return 0
    except KeyboardInterrupt:
        print("\n⏹️  Demo stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Error during health monitoring demo: {str(e)}")
        return 3


def main():
    """Main entry point for the verification script."""
    parser = argparse.ArgumentParser(
        description="Robinhood API Connection Verification Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_connection.py              # Run comprehensive check
  python verify_connection.py --quick      # Quick connectivity test
  python verify_connection.py --sandbox    # Test sandbox environment
  python verify_connection.py --monitor    # Health monitoring demo
  python verify_connection.py --verbose    # Detailed output
        """
    )

    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Run quick connectivity test only'
    )

    parser.add_argument(
        '--sandbox', '-s',
        action='store_true',
        help='Test sandbox environment instead of production'
    )

    parser.add_argument(
        '--monitor', '-m',
        action='store_true',
        help='Run health monitoring demo'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output and performance metrics'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )

    args = parser.parse_args()

    # Determine which verification mode to run
    if args.monitor:
        mode = "monitoring_demo"
    elif args.quick:
        mode = "quick_check"
    else:
        mode = "comprehensive_check"

    print_banner()

    # Run the appropriate verification
    if mode == "quick_check":
        exit_code = asyncio.run(run_quick_verification(args.sandbox))
    elif mode == "monitoring_demo":
        exit_code = asyncio.run(run_health_monitoring_demo(args.sandbox))
    else:
        exit_code = asyncio.run(run_comprehensive_verification(args.sandbox, args.verbose))

    # Handle JSON output
    if args.json and mode == "comprehensive_check":
        try:
            from src.core.api.connectivity_check import comprehensive_connectivity_check
            result = asyncio.run(comprehensive_connectivity_check(args.sandbox))
            import json
            print(json.dumps({
                'exit_code': exit_code,
                'healthy': result.is_healthy,
                'total_duration_ms': result.total_duration_ms,
                'environment': result.environment_info.get('environment', 'unknown'),
                'timestamp': time.time()
            }, indent=2))
        except Exception as e:
            print(f"Error generating JSON output: {e}")

    print_usage_examples()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()