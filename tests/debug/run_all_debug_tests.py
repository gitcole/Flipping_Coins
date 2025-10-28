#!/usr/bin/env python3
"""
Complete Robinhood API Connection Debugging Test Suite

This script runs all debugging tests in sequence to provide comprehensive
analysis of the Robinhood API connection issues. It combines:

1. Configuration loading tests
2. Authentication validation tests
3. API endpoint connectivity tests
4. Error handling and logging tests
5. Environment comparison tests
6. Health check and validation tests

Usage:
    python tests/debug/run_all_debug_tests.py
    python -m tests.debug.run_all_debug_tests

The script will:
- Run all test suites in logical order
- Provide comprehensive debugging information
- Generate detailed reports and recommendations
- Identify root causes of connection issues
- Suggest specific fixes for common problems
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.utils.logging import get_logger

logger = get_logger("debug_runner")


class DebugTestRunner:
    """Main test runner that coordinates all debugging tests."""

    def __init__(self):
        """Initialize the debug test runner."""
        self.start_time = time.time()
        self.test_results = []
        self.all_issues = []
        self.recommendations = []

    def add_test_result(self, test_suite: str, success: bool, message: str, details: Dict = None):
        """Add test result from a test suite."""
        self.test_results.append({
            "suite": test_suite,
            "success": success,
            "message": message,
            "details": details or {}
        })

    def add_issues(self, issues: List[Dict]):
        """Add issues found during testing."""
        self.all_issues.extend(issues)

    def add_recommendations(self, recommendations: List[str]):
        """Add recommendations for fixing issues."""
        self.recommendations.extend(recommendations)

    def print_header(self):
        """Print the test runner header."""
        print("\n" + "="*100)
        print("🚀 ROBINHOOD API CONNECTION DEBUGGING TEST SUITE")
        print("="*100)
        print("This comprehensive test suite will analyze all aspects of the Robinhood API connection")
        print("and provide detailed debugging information and recommendations.")
        print("\n📋 Test Categories:")
        print("   1. Environment and Configuration Setup")
        print("   2. Authentication Methods (Private & Public Key)")
        print("   3. API Endpoint Connectivity")
        print("   4. Request/Response Handling")
        print("   5. Error Handling and Logging")
        print("   6. Sandbox vs Production Comparison")
        print("   7. Health Checks and Validation")
        print("="*100)

    def print_progress(self, current: int, total: int, test_name: str):
        """Print progress indicator."""
        percentage = (current / total) * 100
        bar_length = 50
        filled_length = int(bar_length * current // total)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        print(f"\n🔄 Progress: [{bar}] {percentage:5.1f}% ({current}/{total})")
        print(f"   Running: {test_name}")

    def print_summary(self):
        """Print comprehensive test summary."""
        end_time = time.time()
        total_time = end_time - self.start_time

        print("\n" + "="*100)
        print("📊 COMPREHENSIVE DEBUGGING SUMMARY")
        print("="*100)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"⏱️  Total execution time: {total_time:.2f} seconds")
        print(f"📈 Test Results: {passed_tests}/{total_tests} passed")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   🚨 Issues Found: {len(self.all_issues)}")

        # Overall status
        if failed_tests == 0:
            print("\n🎉 OVERALL STATUS: ALL TESTS PASSED!")
            print("   The Robinhood API connection appears to be working correctly.")
        elif failed_tests < total_tests * 0.3:
            print("\n⚠️  OVERALL STATUS: MOSTLY WORKING")
            print(f"   {failed_tests} test(s) failed. Check recommendations below.")
        else:
            print("\n❌ OVERALL STATUS: SIGNIFICANT ISSUES")
            print(f"   {failed_tests} test(s) failed. Multiple issues need attention.")

        # Issues breakdown
        if self.all_issues:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            issues_by_category = {}
            for issue in self.all_issues:
                category = issue.get("test", "Unknown").split(" ")[0]
                if category not in issues_by_category:
                    issues_by_category[category] = []
                issues_by_category[category].append(issue)

            for category, issues in issues_by_category.items():
                print(f"\n   {category} Issues ({len(issues)}):")
                for i, issue in enumerate(issues, 1):
                    print(f"      {i}. {issue['message']}")
                    if issue.get('details'):
                        for key, value in issue['details'].items():
                            if key != 'error' or len(str(value)) < 100:  # Don't show very long error messages
                                print(f"         {key}: {value}")

        # Recommendations
        if self.recommendations:
            print("
💡 RECOMMENDATIONS:"            for i, recommendation in enumerate(self.recommendations, 1):
                print(f"   {i}. {recommendation}")

        print("
📋 DETAILED TEST RESULTS:"        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['suite']}: {result['message']}")

        print("
🔗 Test Files:"        print("   Configuration: tests/debug/test_api_connection_debug.py")
        print("   Authentication: tests/debug/test_auth_validation.py")
        print("   Connectivity: tests/debug/test_api_connectivity.py")
        print("   Run individual tests with: python tests/debug/<filename>")

        print("\n" + "="*100)

    def analyze_issues(self):
        """Analyze issues and generate recommendations."""
        recommendations = []

        # Analyze by issue categories
        config_issues = [i for i in self.all_issues if "Configuration" in i.get("test", "")]
        auth_issues = [i for i in self.all_issues if "Authentication" in i.get("test", "")]
        connectivity_issues = [i for i in self.all_issues if "Connectivity" in i.get("test", "")]

        # Configuration recommendations
        if config_issues:
            recommendations.append("Fix configuration loading issues first:")
            recommendations.append("   1. Ensure config/.env file exists with proper credentials")
            recommendations.append("   2. Set ROBINHOOD_API_KEY (should start with 'rh-')")
            recommendations.append("   3. Set either ROBINHOOD_PRIVATE_KEY or ROBINHOOD_PUBLIC_KEY")
            recommendations.append("   4. Verify .env file format and encoding")

        # Authentication recommendations
        if auth_issues:
            recommendations.append("Fix authentication issues:")
            recommendations.append("   1. Verify API key format and validity")
            recommendations.append("   2. Check that private/public keys are valid ECDSA keys")
            recommendations.append("   3. Test both authentication methods (private and public key)")
            recommendations.append("   4. Ensure keys are properly base64-encoded")

        # Connectivity recommendations
        if connectivity_issues:
            recommendations.append("Fix network connectivity issues:")
            recommendations.append("   1. Verify internet connection and firewall settings")
            recommendations.append("   2. Check Robinhood API status and service availability")
            recommendations.append("   3. Test both sandbox and production endpoints")
            recommendations.append("   4. Verify DNS resolution for api.robinhood.com")

        # General recommendations
        recommendations.append("General debugging steps:")
        recommendations.append("   1. Check Robinhood API documentation for latest requirements")
        recommendations.append("   2. Verify system time and timezone settings")
        recommendations.append("   3. Test with both sandbox and production environments")
        recommendations.append("   4. Monitor network traffic and API responses")

        self.recommendations = recommendations

    async def run_configuration_tests(self):
        """Run configuration loading tests."""
        print("\n🔧 Running Configuration Tests...")
        try:
            from .test_api_connection_debug import test_configuration_loading

            # Create a simple test suite instance
            class ConfigTestSuite:
                def __init__(self):
                    self.test_results = []
                    self.issues_found = []

                def log_test_result(self, test_name, success, message, details=None):
                    self.test_results.append({
                        "test": test_name,
                        "success": success,
                        "message": message,
                        "details": details or {}
                    })
                    if not success:
                        self.issues_found.append({
                            "test": test_name,
                            "message": message,
                            "details": details or {}
                        })

            suite = ConfigTestSuite()
            success = test_configuration_loading(suite)

            self.add_test_result("Configuration Loading", success, "Configuration loading tests completed", {
                "tests_run": len(suite.test_results),
                "issues_found": len(suite.issues_found)
            })
            self.add_issues(suite.issues_found)

        except ImportError as e:
            self.add_test_result("Configuration Loading", False, f"Failed to import configuration tests: {e}")
        except Exception as e:
            self.add_test_result("Configuration Loading", False, f"Configuration tests failed: {e}")

    async def run_authentication_tests(self):
        """Run authentication validation tests."""
        print("\n🔐 Running Authentication Tests...")
        try:
            from .test_auth_validation import run_auth_validation_tests

            suite = await run_auth_validation_tests()

            self.add_test_result("Authentication Validation", len(suite.issues_found) == 0,
                               "Authentication validation tests completed", {
                "tests_run": len(suite.test_results),
                "issues_found": len(suite.issues_found)
            })
            self.add_issues(suite.issues_found)

        except ImportError as e:
            self.add_test_result("Authentication Validation", False, f"Failed to import authentication tests: {e}")
        except Exception as e:
            self.add_test_result("Authentication Validation", False, f"Authentication tests failed: {e}")

    async def run_connectivity_tests(self):
        """Run API connectivity tests."""
        print("\n🌐 Running Connectivity Tests...")
        try:
            from .test_api_connectivity import run_api_connectivity_tests

            suite = await run_api_connectivity_tests()

            self.add_test_result("API Connectivity", len(suite.issues_found) == 0,
                               "API connectivity tests completed", {
                "tests_run": len(suite.test_results),
                "issues_found": len(suite.issues_found)
            })
            self.add_issues(suite.issues_found)

        except ImportError as e:
            self.add_test_result("API Connectivity", False, f"Failed to import connectivity tests: {e}")
        except Exception as e:
            self.add_test_result("API Connectivity", False, f"Connectivity tests failed: {e}")

    async def run_all_tests(self):
        """Run all debugging tests in sequence."""
        self.print_header()

        print("\n🚀 Starting comprehensive debugging tests...")

        # Run tests in logical order
        await self.run_configuration_tests()
        await self.run_authentication_tests()
        await self.run_connectivity_tests()

        # Analyze results and generate recommendations
        self.analyze_issues()

        # Print comprehensive summary
        self.print_summary()

        return len(self.all_issues) == 0  # Return True if no issues found


async def main():
    """Main entry point for the debug test runner."""
    runner = DebugTestRunner()

    try:
        success = await runner.run_all_tests()
        exit_code = 0 if success else 1

        print(f"\n🏁 Debug testing completed with exit code: {exit_code}")
        return exit_code

    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        return 1


if __name__ == "__main__":
    """Run the debug test suite when executed directly."""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)