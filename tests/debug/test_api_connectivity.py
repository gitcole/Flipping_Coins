"""
API Endpoint Connectivity Tests for Robinhood API

Comprehensive tests for validating API endpoint connectivity including:
- HTTP request/response handling
- Different endpoint testing (sandbox vs production)
- Response validation and error handling
- Network connectivity and timeout testing
- Rate limiting and retry logic testing

Usage:
    python tests/debug/test_api_connectivity.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import structlog
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.api.exceptions import APIError, RobinhoodAPIError
from src.core.api.robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from src.core.config import initialize_config, get_settings
from src.utils.logging import get_logger

logger = structlog.get_logger(__name__)
test_logger = get_logger("connectivity_debug")


class APIConnectivityTestSuite:
    """Comprehensive API connectivity test suite."""

    def __init__(self):
        """Initialize the API connectivity test suite."""
        self.test_results = []
        self.issues_found = []
        self.client = None
        self.sandbox_client = None
        self.production_client = None

    def log_test_result(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result and track issues."""
        status = "✅ PASS" if success else "❌ FAIL"
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

        print(f"\n{status} {test_name}")
        print(f"   Message: {message}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")

    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*80)
        print("🌐 ROBINHOOD API CONNECTIVITY TEST SUMMARY")
        print("="*80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")

        if self.issues_found:
            print(f"\n🚨 CONNECTIVITY ISSUES FOUND ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue['test']}: {issue['message']}")
                if issue['details']:
                    for key, value in issue['details'].items():
                        print(f"      {key}: {value}")
        else:
            print("\n🎉 All connectivity tests passed!")

        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")


def test_client_creation(connectivity_suite: APIConnectivityTestSuite):
    """Test 1: Client creation for both environments."""
    print("\n🧪 TEST 1: Client Creation")

    details = {}
    success = True

    try:
        # Test 1: Sandbox client creation
        print("   Creating sandbox client...")
        try:
            sandbox_client = RobinhoodClient(sandbox=True)
            connectivity_suite.sandbox_client = sandbox_client
            details["sandbox_client_created"] = True
            details["sandbox_base_url"] = sandbox_client.config.base_url
            details["sandbox_timeout"] = sandbox_client.config.timeout
            details["sandbox_retries"] = sandbox_client.config.retries
        except Exception as e:
            details["sandbox_client_created"] = False
            details["sandbox_error"] = str(e)
            success = False

        # Test 2: Production client creation
        print("   Creating production client...")
        try:
            production_client = RobinhoodClient(sandbox=False)
            connectivity_suite.production_client = production_client
            details["production_client_created"] = True
            details["production_base_url"] = production_client.config.base_url
            details["production_timeout"] = production_client.config.timeout
            details["production_retries"] = production_client.config.retries
        except Exception as e:
            details["production_client_created"] = False
            details["production_error"] = str(e)
            success = False

        # Test 3: Client with proper authentication
        print("   Creating authenticated client...")

        # Ensure environment variables are loaded
        load_dotenv('config/.env', override=True)
        logger.info("Loaded environment variables from config/.env")

        api_key = os.getenv("ROBINHOOD_API_KEY")
        private_key = os.getenv("ROBINHOOD_PRIVATE_KEY")
        public_key = os.getenv("ROBINHOOD_PUBLIC_KEY")

        logger.debug("Environment check",
                     api_key_present=bool(api_key),
                     private_key_present=bool(private_key),
                     public_key_present=bool(public_key))

        if api_key and (private_key or public_key):
            try:
                # Load environment variables
                load_dotenv('config/.env', override=True)

                # Create properly authenticated client
                client = RobinhoodClient(sandbox=True)  # Use sandbox for safety
                connectivity_suite.client = client

                details["authenticated_client_created"] = True
                details["authenticated_sandbox"] = client.config.sandbox
                details["authenticated_base_url"] = client.config.base_url
                details["authenticated_api_key"] = client.config.api_key[:20] + "..." if client.config.api_key else "None"
                details["authenticated_private_key"] = client.config.private_key[:20] + "..." if client.config.private_key else "None"
                details["authenticated_public_key"] = client.config.public_key[:20] + "..." if client.config.public_key else "None"
                details["authenticated_is_authenticated"] = client.auth.is_authenticated()
                details["authenticated_auth_type"] = client.auth.get_auth_info().get('auth_type', 'unknown')

            except Exception as e:
                details["authenticated_client_created"] = False
                details["authenticated_error"] = str(e)
                success = False
        else:
            details["authenticated_client_created"] = False
            if not api_key:
                details["authenticated_error"] = "Missing ROBINHOOD_API_KEY"
            elif not private_key and not public_key:
                details["authenticated_error"] = "Missing authentication key (need either ROBINHOOD_PRIVATE_KEY or ROBINHOOD_PUBLIC_KEY)"
            else:
                details["authenticated_error"] = "Unknown authentication issue"
            success = False

        message = "Client creation tested"

    except Exception as e:
        success = False
        message = f"Client creation failed: {e}"

    connectivity_suite.log_test_result("Client Creation", success, message, details)
    return success


async def test_basic_connectivity(connectivity_suite: APIConnectivityTestSuite):
    """Test 2: Basic HTTP connectivity and response handling."""
    print("\n🧪 TEST 2: Basic Connectivity")

    details = {}
    success = True

    if not connectivity_suite.client:
        connectivity_suite.log_test_result("Basic Connectivity", False, "No authenticated client available")
        return False

    try:
        # Test 1: Health check
        print("   Testing health check...")
        try:
            start_time = time.time()
            health = await connectivity_suite.client.health_check()
            response_time = time.time() - start_time

            details["health_check_success"] = True
            details["health_check_status"] = health.get("status", "unknown")
            details["health_check_authenticated"] = health.get("authenticated", False)
            details["health_check_sandbox"] = health.get("sandbox", False)
            details["health_check_response_time"] = f"{response_time:.2f}s"
            details["health_check_timestamp"] = health.get("timestamp", 0)

        except Exception as e:
            details["health_check_success"] = False
            details["health_check_error"] = str(e)
            success = False

        # Test 2: Simple GET request (instruments endpoint)
        print("   Testing instruments endpoint...")
        try:
            start_time = time.time()
            response = await connectivity_suite.client.get_instruments()
            response_time = time.time() - start_time

            details["instruments_success"] = True
            details["instruments_response_time"] = f"{response_time:.2f}s"
            details["instruments_count"] = len(response.get("results", [])) if isinstance(response, dict) else 0
            details["instruments_has_results"] = "results" in response if isinstance(response, dict) else False

        except Exception as e:
            details["instruments_success"] = False
            details["instruments_error"] = str(e)
            success = False

        # Test 3: Market data endpoint
        print("   Testing market data endpoint...")
        try:
            start_time = time.time()
            # Try with common crypto symbols
            symbols = ["BTC-USD", "ETH-USD"]
            quotes = await connectivity_suite.client.get_quotes(symbols)
            response_time = time.time() - start_time

            details["quotes_success"] = True
            details["quotes_response_time"] = f"{response_time:.2f}s"
            details["quotes_symbols_returned"] = len(quotes.get("results", {})) if isinstance(quotes, dict) else 0

        except Exception as e:
            details["quotes_success"] = False
            details["quotes_error"] = str(e)
            success = False

        # Test 4: Test with different HTTP methods
        print("   Testing different HTTP methods...")
        try:
            # Test HEAD request (if supported)
            try:
                response = await connectivity_suite.client.request("HEAD", "/instruments/")
                details["head_request_success"] = True
                details["head_response_status"] = response.status if hasattr(response, 'status') else "unknown"
            except Exception:
                details["head_request_success"] = False

        except Exception as e:
            details["http_methods_error"] = str(e)

        message = "Basic connectivity tested"

    except Exception as e:
        success = False
        message = f"Basic connectivity testing failed: {e}"

    connectivity_suite.log_test_result("Basic Connectivity", success, message, details)
    return success


async def test_endpoint_coverage(connectivity_suite: APIConnectivityTestSuite):
    """Test 3: Comprehensive endpoint coverage testing."""
    print("\n🧪 TEST 3: Endpoint Coverage")

    details = {}
    success = True

    if not connectivity_suite.client:
        connectivity_suite.log_test_result("Endpoint Coverage", False, "No authenticated client available")
        return False

    endpoints_to_test = [
        ("GET", "/instruments/", "List instruments"),
        ("GET", "/markets/", "Market information"),
        ("GET", "/user/", "User information"),
        ("GET", "/accounts/", "Account information"),
        ("GET", "/portfolios/", "Portfolio information"),
        ("GET", "/positions/", "Positions information"),
        ("GET", "/watchlists/", "Watchlists"),
    ]

    tested_endpoints = {}
    failed_endpoints = {}

    for method, endpoint, description in endpoints_to_test:
        print(f"   Testing {method} {endpoint} ({description})...")
        try:
            start_time = time.time()
            response = await connectivity_suite.client.request(method, endpoint)
            response_time = time.time() - start_time

            tested_endpoints[endpoint] = {
                "success": True,
                "response_time": f"{response_time:.2f}s",
                "status": response.status if hasattr(response, 'status') else "unknown",
                "description": description
            }

        except Exception as e:
            tested_endpoints[endpoint] = {
                "success": False,
                "error": str(e),
                "description": description
            }
            failed_endpoints[endpoint] = str(e)
            success = False

    details["tested_endpoints"] = len(tested_endpoints)
    details["successful_endpoints"] = len([e for e in tested_endpoints.values() if e.get("success", False)])
    details["failed_endpoints"] = len(failed_endpoints)

    if failed_endpoints:
        details["failed_endpoints_list"] = list(failed_endpoints.keys())
        details["failure_reasons"] = failed_endpoints

    # Test specific crypto-related endpoints
    print("   Testing crypto-specific endpoints...")
    crypto_endpoints = [
        ("GET", "/midlands/currency_pairs/", "Currency pairs"),
        ("GET", "/marketdata/quotes/", "Market data quotes"),
        ("GET", "/marketdata/historicals/", "Historical data"),
    ]

    for method, endpoint, description in crypto_endpoints:
        print(f"   Testing crypto: {method} {endpoint} ({description})...")
        try:
            if "quotes" in endpoint:
                response = await connectivity_suite.client.request(method, endpoint, params={"symbols": "BTC-USD"})
            elif "historicals" in endpoint:
                response = await connectivity_suite.client.request(method, endpoint, params={
                    "symbol": "BTC-USD",
                    "interval": "day",
                    "span": "week"
                })
            else:
                response = await connectivity_suite.client.request(method, endpoint)

            tested_endpoints[f"crypto_{endpoint}"] = {
                "success": True,
                "status": response.status if hasattr(response, 'status') else "unknown",
                "description": description
            }

        except Exception as e:
            tested_endpoints[f"crypto_{endpoint}"] = {
                "success": False,
                "error": str(e),
                "description": description
            }
            success = False

    message = "Endpoint coverage tested"

    connectivity_suite.log_test_result("Endpoint Coverage", success, message, details)
    return success


async def test_error_handling(connectivity_suite: APIConnectivityTestSuite):
    """Test 4: Error handling for various scenarios."""
    print("\n🧪 TEST 4: Error Handling")

    details = {}
    success = True

    if not connectivity_suite.client:
        connectivity_suite.log_test_result("Error Handling", False, "No authenticated client available")
        return False

    try:
        # Test 1: Invalid endpoint
        print("   Testing invalid endpoint handling...")
        try:
            await connectivity_suite.client.get("/invalid/endpoint/path/")
            details["invalid_endpoint_handled"] = False
        except (APIError, RobinhoodAPIError):
            details["invalid_endpoint_handled"] = True
        except Exception as e:
            details["invalid_endpoint_handled"] = False
            details["invalid_endpoint_unexpected"] = str(e)

        # Test 2: Network timeout (if possible)
        print("   Testing timeout handling...")
        try:
            # Create client with very short timeout for testing
            config = RobinhoodAPIConfig(timeout=1, retries=0)
            timeout_client = RobinhoodClient(config=config)

            start_time = time.time()
            try:
                await timeout_client.get("/instruments/")
                details["timeout_handled"] = False
            except Exception:
                response_time = time.time() - start_time
                details["timeout_handled"] = True
                details["timeout_response_time"] = f"{response_time:.2f}s"

        except Exception as e:
            details["timeout_test_error"] = str(e)

        # Test 3: Invalid parameters
        print("   Testing invalid parameters handling...")
        try:
            await connectivity_suite.client.get_quotes("invalid-symbol-format")
            details["invalid_params_handled"] = False
        except (APIError, RobinhoodAPIError, ValueError):
            details["invalid_params_handled"] = True
        except Exception as e:
            details["invalid_params_handled"] = False
            details["invalid_params_unexpected"] = str(e)

        # Test 4: Rate limiting (if applicable)
        print("   Testing rate limiting...")
        try:
            # Make multiple rapid requests
            start_time = time.time()
            responses = []

            for i in range(3):
                try:
                    response = await connectivity_suite.client.get("/instruments/")
                    responses.append(response)
                except Exception as e:
                    responses.append(f"error: {e}")

            total_time = time.time() - start_time
            details["rate_limiting_tested"] = True
            details["rapid_requests_count"] = len(responses)
            details["rapid_requests_time"] = f"{total_time:.2f}s"
            details["rate_limiting_detected"] = any("rate" in str(r).lower() or "limit" in str(r).lower() for r in responses)

        except Exception as e:
            details["rate_limiting_error"] = str(e)

        # Test 5: Authentication errors
        print("   Testing authentication error handling...")
        try:
            # Create client with invalid credentials
            invalid_auth = RobinhoodSignatureAuth(
                api_key="invalid_key_12345",
                private_key_b64="invalid_private_key_12345",
                sandbox=True
            )

            if not invalid_auth.is_authenticated():
                details["invalid_auth_detected"] = True
            else:
                details["invalid_auth_detected"] = False

        except Exception as e:
            details["invalid_auth_error"] = str(e)

        message = "Error handling tested"

    except Exception as e:
        success = False
        message = f"Error handling testing failed: {e}"

    connectivity_suite.log_test_result("Error Handling", success, message, details)
    return success


async def test_response_validation(connectivity_suite: APIConnectivityTestSuite):
    """Test 5: Response validation and parsing."""
    print("\n🧪 TEST 5: Response Validation")

    details = {}
    success = True

    if not connectivity_suite.client:
        connectivity_suite.log_test_result("Response Validation", False, "No authenticated client available")
        return False

    try:
        # Test 1: Response format validation
        print("   Testing response format validation...")
        try:
            response = await connectivity_suite.client.get_instruments()

            if isinstance(response, dict):
                details["response_is_dict"] = True
                details["response_keys"] = list(response.keys()) if hasattr(response, 'keys') else []

                # Check for expected fields
                expected_fields = ["results", "next", "previous"]
                details["expected_fields_present"] = all(field in response for field in expected_fields)

                # Check results structure
                if "results" in response and isinstance(response["results"], list):
                    details["results_is_list"] = True
                    details["results_count"] = len(response["results"])

                    if response["results"]:
                        details["first_result_keys"] = list(response["results"][0].keys()) if isinstance(response["results"][0], dict) else []
                else:
                    details["results_is_list"] = False
            else:
                details["response_is_dict"] = False
                details["response_type"] = type(response).__name__

        except Exception as e:
            details["response_validation_error"] = str(e)
            success = False

        # Test 2: Response status codes
        print("   Testing response status codes...")
        try:
            # This should work and return proper status
            response = await connectivity_suite.client.request("GET", "/instruments/")

            if hasattr(response, 'status'):
                details["response_status_code"] = response.status
                details["response_status_success"] = 200 <= response.status < 300
            else:
                details["response_status_unknown"] = True

        except Exception as e:
            details["status_code_error"] = str(e)

        # Test 3: Response headers
        print("   Testing response headers...")
        try:
            response = await connectivity_suite.client.request("GET", "/instruments/")

            if hasattr(response, 'headers'):
                details["response_headers_present"] = True
                headers = dict(response.headers) if hasattr(response.headers, 'items') else {}
                details["response_headers_count"] = len(headers)
                details["response_content_type"] = headers.get('content-type', 'unknown')
                details["response_server"] = headers.get('server', 'unknown')
            else:
                details["response_headers_present"] = False

        except Exception as e:
            details["headers_error"] = str(e)

        # Test 4: JSON parsing validation
        print("   Testing JSON parsing...")
        try:
            # Test various endpoints for proper JSON response
            endpoints = ["/instruments/", "/markets/"]

            for endpoint in endpoints:
                try:
                    response = await connectivity_suite.client.request("GET", endpoint)
                    details[f"json_parse_{endpoint}"] = True
                except Exception as e:
                    details[f"json_parse_{endpoint}"] = False
                    details[f"json_parse_error_{endpoint}"] = str(e)

        except Exception as e:
            details["json_validation_error"] = str(e)

        message = "Response validation tested"

    except Exception as e:
        success = False
        message = f"Response validation testing failed: {e}"

    connectivity_suite.log_test_result("Response Validation", success, message, details)
    return success


async def test_sandbox_vs_production(connectivity_suite: APIConnectivityTestSuite):
    """Test 6: Sandbox vs Production environment differences."""
    print("\n🧪 TEST 6: Sandbox vs Production Comparison")

    details = {}
    success = True

    try:
        # Test 1: Base URL differences
        print("   Comparing base URLs...")
        details["sandbox_base_url"] = connectivity_suite.sandbox_client.config.base_url if connectivity_suite.sandbox_client else "None"
        details["production_base_url"] = connectivity_suite.production_client.config.base_url if connectivity_suite.production_client else "None"

        if connectivity_suite.sandbox_client and connectivity_suite.production_client:
            details["urls_different"] = (
                connectivity_suite.sandbox_client.config.base_url !=
                connectivity_suite.production_client.config.base_url
            )
        else:
            details["urls_different"] = False

        # Test 2: Authentication differences
        print("   Comparing authentication...")
        if connectivity_suite.sandbox_client and connectivity_suite.production_client:
            sandbox_auth = connectivity_suite.sandbox_client.auth.get_auth_info()
            production_auth = connectivity_suite.production_client.auth.get_auth_info()

            details["sandbox_auth_type"] = sandbox_auth.get("auth_type", "unknown")
            details["production_auth_type"] = production_auth.get("auth_type", "unknown")
            details["auth_types_match"] = sandbox_auth.get("auth_type") == production_auth.get("auth_type")

        # Test 3: Response differences
        print("   Comparing responses between environments...")
        if connectivity_suite.sandbox_client:
            try:
                sandbox_response = await connectivity_suite.sandbox_client.get_instruments()
                details["sandbox_response_success"] = True
                details["sandbox_response_type"] = type(sandbox_response).__name__

                if isinstance(sandbox_response, dict) and "results" in sandbox_response:
                    details["sandbox_results_count"] = len(sandbox_response["results"])
            except Exception as e:
                details["sandbox_response_success"] = False
                details["sandbox_response_error"] = str(e)

        if connectivity_suite.production_client:
            try:
                production_response = await connectivity_suite.production_client.get_instruments()
                details["production_response_success"] = True
                details["production_response_type"] = type(production_response).__name__

                if isinstance(production_response, dict) and "results" in production_response:
                    details["production_results_count"] = len(production_response["results"])
            except Exception as e:
                details["production_response_success"] = False
                details["production_response_error"] = str(e)

        # Test 4: Rate limiting differences
        print("   Testing rate limiting differences...")
        try:
            # Test rapid requests in both environments
            if connectivity_suite.sandbox_client:
                start_time = time.time()
                for i in range(3):
                    await connectivity_suite.sandbox_client.get("/instruments/")
                sandbox_time = time.time() - start_time
                details["sandbox_rate_limit_time"] = f"{sandbox_time:.2f}s"

            if connectivity_suite.production_client:
                start_time = time.time()
                for i in range(3):
                    await connectivity_suite.production_client.get("/instruments/")
                production_time = time.time() - start_time
                details["production_rate_limit_time"] = f"{production_time:.2f}s"

        except Exception as e:
            details["rate_limit_comparison_error"] = str(e)

        message = "Sandbox vs Production comparison tested"

    except Exception as e:
        success = False
        message = f"Sandbox vs Production comparison failed: {e}"

    connectivity_suite.log_test_result("Sandbox vs Production Comparison", success, message, details)
    return success


async def run_api_connectivity_tests():
    """Run all API connectivity tests."""
    print("🌐 Starting Robinhood API Connectivity Tests")
    print("="*80)

    connectivity_suite = APIConnectivityTestSuite()

    # Run all tests
    test_client_creation(connectivity_suite)
    await test_basic_connectivity(connectivity_suite)
    await test_endpoint_coverage(connectivity_suite)
    await test_error_handling(connectivity_suite)
    await test_response_validation(connectivity_suite)
    await test_sandbox_vs_production(connectivity_suite)

    # Print comprehensive summary
    connectivity_suite.print_summary()

    # Provide specific recommendations
    print("\n💡 CONNECTIVITY RECOMMENDATIONS:")
    print("-" * 50)

    # Check for specific connectivity issues
    network_issues = False
    auth_issues = False
    endpoint_issues = False

    for issue in connectivity_suite.issues_found:
        if "Basic Connectivity" in issue["test"] or "Endpoint" in issue["test"]:
            network_issues = True
        if "Authentication" in issue["test"]:
            auth_issues = True
        if "Error Handling" in issue["test"]:
            endpoint_issues = True

    if network_issues:
        print("🌐 Fix network connectivity issues:")
        print("   1. Verify internet connection and firewall settings")
        print("   2. Check Robinhood API status and service availability")
        print("   3. Test both sandbox and production endpoints")
        print("   4. Verify DNS resolution for api.robinhood.com")

    if auth_issues:
        print("🔐 Fix authentication connectivity issues:")
        print("   1. Ensure API credentials are valid and not expired")
        print("   2. Verify sandbox vs production credential differences")
        print("   3. Check that authentication tokens are properly formatted")
        print("   4. Test with both private and public key methods")

    if endpoint_issues:
        print("📍 Fix endpoint and error handling issues:")
        print("   1. Verify endpoint URLs and HTTP methods")
        print("   2. Check response format expectations")
        print("   3. Implement proper timeout and retry logic")
        print("   4. Add comprehensive error logging")

    print("\n📋 Next Steps:")
    print("   1. Review and fix any identified network issues")
    print("   2. Validate authentication in both environments")
    print("   3. Test with real trading scenarios")
    print("   4. Monitor API usage and rate limits")

    return connectivity_suite


if __name__ == "__main__":
    """Run API connectivity tests when script is executed directly."""
    asyncio.run(run_api_connectivity_tests())