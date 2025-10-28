"""
Comprehensive API Connection Debugging Tests for Robinhood API

This module provides systematic debugging tests to identify and resolve
issues with the Robinhood API connection. Tests cover:

1. Configuration loading and validation
2. Authentication setup and validation
3. API endpoint connectivity
4. Request/response handling
5. Error handling and logging
6. Both sandbox and production environments
7. Both private key and public key authentication methods

Usage:
    python -m pytest tests/debug/test_api_connection_debug.py -v -s
    or
    python tests/debug/test_api_connection_debug.py
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

from src.core.api.exceptions import APIError, AuthenticationError, RobinhoodAPIError
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from src.core.api.robinhood.client import RobinhoodClient, RobinhoodAPIConfig
from src.core.config import initialize_config, get_settings
from src.core.config.manager import ConfigurationManager
from src.utils.logging import get_logger

logger = structlog.get_logger(__name__)
test_logger = get_logger("api_debug")


class APIDebugTestSuite:
    """Comprehensive test suite for debugging Robinhood API connection issues."""

    def __init__(self):
        """Initialize the debug test suite."""
        self.test_results = []
        self.issues_found = []
        self.config = None
        self.client = None

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
        print("🔍 ROBINHOOD API CONNECTION DEBUG SUMMARY")
        print("="*80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")

        if self.issues_found:
            print(f"\n🚨 ISSUES FOUND ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue['test']}: {issue['message']}")
                if issue['details']:
                    for key, value in issue['details'].items():
                        print(f"      {key}: {value}")
        else:
            print("\n🎉 No critical issues found!")

        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")


def test_environment_setup(debug_suite: APIDebugTestSuite):
    """Test 1: Environment and path setup."""
    print("\n🧪 TEST 1: Environment Setup")

    details = {}

    try:
        # Check current working directory
        cwd = os.getcwd()
        details["current_directory"] = cwd

        # Check Python path
        src_path = str(Path(__file__).parent.parent.parent / "src")
        if src_path in sys.path:
            details["src_in_path"] = True
        else:
            details["src_in_path"] = False
            sys.path.insert(0, src_path)

        # Check if config directory exists
        config_dir = Path("config")
        details["config_dir_exists"] = config_dir.exists()

        if config_dir.exists():
            env_example = config_dir / ".env.example"
            env_file = config_dir / ".env"
            details["env_example_exists"] = env_example.exists()
            details["env_file_exists"] = env_file.exists()

        success = True
        message = "Environment setup completed"

    except Exception as e:
        success = False
        message = f"Environment setup failed: {e}"

    debug_suite.log_test_result("Environment Setup", success, message, details)
    return success


def test_configuration_loading(debug_suite: APIDebugTestSuite):
    """Test 2: Configuration loading from multiple sources."""
    print("\n🧪 TEST 2: Configuration Loading")

    details = {}
    success = True

    try:
        # Test 1: Check environment variables directly
        print("   Checking environment variables...")
        env_vars = ['ROBINHOOD_API_KEY', 'ROBINHOOD_PRIVATE_KEY', 'ROBINHOOD_PUBLIC_KEY', 'ROBINHOOD_SANDBOX']
        for var in env_vars:
            value = os.getenv(var)
            details[f"env_{var.lower()}"] = value[:30] + "..." if value and len(value) > 30 else value or "None"

        # Test 2: Load .env files manually
        print("   Loading .env files...")
        load_dotenv('config/.env', override=True)
        load_dotenv('.env', override=True)

        # Check again after loading
        for var in env_vars:
            value = os.getenv(var)
            details[f"env_after_load_{var.lower()}"] = value[:30] + "..." if value and len(value) > 30 else value or "None"

        # Test 3: Try configuration manager
        print("   Testing configuration manager...")
        try:
            manager = ConfigurationManager()
            manager.add_env_file('config/.env')
            manager.add_env_file('.env')

            # Load environment files into os.environ
            load_dotenv('config/.env')
            load_dotenv('.env')

            config = manager.load_configuration()
            debug_suite.config = config

            details["config_loaded"] = True
            details["robinhood_api_key"] = config.robinhood.api_key[:30] + "..." if config.robinhood.api_key else "None"
            details["robinhood_private_key"] = config.robinhood.private_key[:30] + "..." if config.robinhood.private_key else "None"
            details["robinhood_public_key"] = config.robinhood.public_key[:30] + "..." if config.robinhood.public_key else "None"
            details["robinhood_sandbox"] = config.robinhood.sandbox

        except Exception as e:
            details["config_loaded"] = False
            details["config_error"] = str(e)
            success = False

        # Test 4: Try initialize_config function
        print("   Testing initialize_config function...")
        try:
            settings = initialize_config()
            details["initialize_config_success"] = True
        except Exception as e:
            details["initialize_config_success"] = False
            details["initialize_config_error"] = str(e)
            success = False

        message = "Configuration loading completed"

    except Exception as e:
        success = False
        message = f"Configuration loading failed: {e}"

    debug_suite.log_test_result("Configuration Loading", success, message, details)
    return success


def test_authentication_methods(debug_suite: APIDebugTestSuite):
    """Test 3: Authentication methods (both private and public key)."""
    print("\n🧪 TEST 3: Authentication Methods")

    details = {}
    success = True

    try:
        # Test 1: Private key authentication
        print("   Testing private key authentication...")
        try:
            api_key = os.getenv("ROBINHOOD_API_KEY")
            private_key = os.getenv("ROBINHOOD_PRIVATE_KEY")

            if api_key and private_key:
                auth = RobinhoodSignatureAuth(
                    api_key=api_key,
                    private_key_b64=private_key,
                    sandbox=os.getenv("ROBINHOOD_SANDBOX", "false").lower() == "true"
                )
                details["private_key_auth"] = auth.is_authenticated()
                details["private_key_type"] = auth.get_auth_info().get("auth_type", "unknown")
                details["private_key_api_key"] = auth.get_api_key()[:20] + "..." if auth.get_api_key() else "None"
            else:
                details["private_key_auth"] = False
                details["private_key_error"] = "Missing API key or private key"
                success = False

        except Exception as e:
            details["private_key_auth"] = False
            details["private_key_error"] = str(e)
            success = False

        # Test 2: Public key authentication
        print("   Testing public key authentication...")
        try:
            api_key = os.getenv("ROBINHOOD_API_KEY")
            public_key = os.getenv("ROBINHOOD_PUBLIC_KEY")

            if api_key and public_key:
                auth = RobinhoodSignatureAuth(
                    api_key=api_key,
                    public_key_b64=public_key,
                    sandbox=os.getenv("ROBINHOOD_SANDBOX", "false").lower() == "true"
                )
                details["public_key_auth"] = auth.is_authenticated()
                details["public_key_type"] = auth.get_auth_info().get("auth_type", "unknown")
                details["public_key_api_key"] = auth.get_api_key()[:20] + "..." if auth.get_api_key() else "None"
            else:
                details["public_key_auth"] = False
                details["public_key_error"] = "Missing API key or public key"
                success = False

        except Exception as e:
            details["public_key_auth"] = False
            details["public_key_error"] = str(e)
            success = False

        message = "Authentication methods tested"

    except Exception as e:
        success = False
        message = f"Authentication testing failed: {e}"

    debug_suite.log_test_result("Authentication Methods", success, message, details)
    return success


def test_client_initialization(debug_suite: APIDebugTestSuite):
    """Test 4: Client initialization with different configurations."""
    print("\n🧪 TEST 4: Client Initialization")

    details = {}
    success = True

    try:
        # Test 1: Client with sandbox=True
        print("   Testing client with sandbox=True...")
        try:
            client = RobinhoodClient(sandbox=True)
            details["sandbox_client_created"] = True
            details["sandbox_config_sandbox"] = client.config.sandbox
            details["sandbox_base_url"] = client.config.base_url
            details["sandbox_authenticated"] = client.auth.is_authenticated()
        except Exception as e:
            details["sandbox_client_created"] = False
            details["sandbox_error"] = str(e)
            success = False

        # Test 2: Client with sandbox=False
        print("   Testing client with sandbox=False...")
        try:
            client = RobinhoodClient(sandbox=False)
            details["production_client_created"] = True
            details["production_config_sandbox"] = client.config.sandbox
            details["production_base_url"] = client.config.base_url
            details["production_authenticated"] = client.auth.is_authenticated()
        except Exception as e:
            details["production_client_created"] = False
            details["production_error"] = str(e)
            success = False

        # Test 3: Client without parameters (should auto-initialize)
        print("   Testing client auto-initialization...")
        try:
            client = RobinhoodClient()
            debug_suite.client = client
            details["auto_client_created"] = True
            details["auto_config_sandbox"] = client.config.sandbox
            details["auto_base_url"] = client.config.base_url
            details["auto_authenticated"] = client.auth.is_authenticated()
            details["auto_api_key"] = client.config.api_key[:20] + "..." if client.config.api_key else "None"
            details["auto_private_key"] = client.config.private_key[:20] + "..." if client.config.private_key else "None"
            details["auto_public_key"] = client.config.public_key[:20] + "..." if client.config.public_key else "None"
        except Exception as e:
            details["auto_client_created"] = False
            details["auto_error"] = str(e)
            success = False

        # Test 4: Client with explicit config
        print("   Testing client with explicit config...")
        try:
            config = RobinhoodAPIConfig(sandbox=True)
            client = RobinhoodClient(config=config)
            details["explicit_config_client_created"] = True
            details["explicit_config_sandbox"] = client.config.sandbox
        except Exception as e:
            details["explicit_config_client_created"] = False
            details["explicit_config_error"] = str(e)
            success = False

        message = "Client initialization tested"

    except Exception as e:
        success = False
        message = f"Client initialization failed: {e}"

    debug_suite.log_test_result("Client Initialization", success, message, details)
    return success


async def test_api_connectivity(debug_suite: APIDebugTestSuite):
    """Test 5: API endpoint connectivity and basic requests."""
    print("\n🧪 TEST 5: API Connectivity")

    details = {}
    success = True

    if not debug_suite.client:
        debug_suite.log_test_result("API Connectivity", False, "No client available for testing")
        return False

    try:
        # Test 1: Health check
        print("   Testing health check...")
        try:
            health = await debug_suite.client.health_check()
            details["health_check"] = health.get("status", "unknown")
            details["health_authenticated"] = health.get("authenticated", False)
            details["health_sandbox"] = health.get("sandbox", False)
            details["health_error"] = health.get("error", "")
        except Exception as e:
            details["health_check"] = False
            details["health_error"] = str(e)
            success = False

        # Test 2: Basic endpoint access (instruments)
        print("   Testing basic endpoint access...")
        try:
            instruments = await debug_suite.client.get_instruments()
            details["instruments_success"] = True
            details["instruments_count"] = len(instruments.get("results", [])) if isinstance(instruments, dict) else 0
        except Exception as e:
            details["instruments_success"] = False
            details["instruments_error"] = str(e)
            success = False

        # Test 3: Market data access
        print("   Testing market data access...")
        try:
            # Try to get popular symbols
            symbols = ["BTC-USD", "ETH-USD"]  # Common crypto symbols
            quotes = await debug_suite.client.get_quotes(symbols)
            details["quotes_success"] = True
            details["quotes_symbols"] = len(quotes.get("results", {})) if isinstance(quotes, dict) else 0
        except Exception as e:
            details["quotes_success"] = False
            details["quotes_error"] = str(e)
            success = False

        message = "API connectivity tested"

    except Exception as e:
        success = False
        message = f"API connectivity testing failed: {e}"

    debug_suite.log_test_result("API Connectivity", success, message, details)
    return success


async def test_error_handling(debug_suite: APIDebugTestSuite):
    """Test 6: Error handling and logging."""
    print("\n🧪 TEST 6: Error Handling")

    details = {}
    success = True

    try:
        # Test 1: Invalid credentials
        print("   Testing invalid credentials handling...")
        try:
            auth = RobinhoodSignatureAuth(
                api_key="invalid_key",
                private_key_b64="invalid_private_key",
                sandbox=True
            )
            details["invalid_creds_handled"] = not auth.is_authenticated()
        except Exception as e:
            details["invalid_creds_handled"] = True
            details["invalid_creds_error"] = str(e)

        # Test 2: Missing configuration
        print("   Testing missing configuration handling...")
        try:
            client = RobinhoodClient()
            if not client.config.api_key:
                details["missing_config_handled"] = True
            else:
                details["missing_config_handled"] = False
        except Exception as e:
            details["missing_config_handled"] = True
            details["missing_config_error"] = str(e)

        # Test 3: Network error simulation
        print("   Testing network error handling...")
        try:
            # This should fail with invalid endpoint
            await debug_suite.client.get("/invalid/endpoint/")
            details["network_error_handled"] = False
        except (APIError, RobinhoodAPIError):
            details["network_error_handled"] = True
        except Exception as e:
            details["network_error_handled"] = False
            details["network_error_unexpected"] = str(e)

        message = "Error handling tested"

    except Exception as e:
        success = False
        message = f"Error handling testing failed: {e}"

    debug_suite.log_test_result("Error Handling", success, message, details)
    return success


def test_signature_validation(debug_suite: APIDebugTestSuite):
    """Test 7: Signature validation and key conversion."""
    print("\n🧪 TEST 7: Signature Validation")

    details = {}
    success = True

    try:
        # Test 1: Private key to public key conversion
        print("   Testing private to public key conversion...")
        try:
            from ecdsa import SigningKey
            from base64 import b64encode, b64decode

            # Use existing private key or generate test one
            private_key_b64 = os.getenv("ROBINHOOD_PRIVATE_KEY")
            if not private_key_b64:
                # Generate a test key for validation
                sk = SigningKey.generate()
                private_key_b64 = b64encode(sk.to_der()).decode('utf-8')

            # Decode and recreate signing key
            private_key_der = b64decode(private_key_b64)
            signing_key = SigningKey.from_der(private_key_der)

            # Generate public key
            public_key_der = signing_key.verifying_key.to_der()
            public_key_b64 = b64encode(public_key_der).decode('utf-8')

            details["key_conversion_success"] = True
            details["generated_public_key"] = public_key_b64[:30] + "..."

            # Test that public key authentication works with derived key
            api_key = os.getenv("ROBINHOOD_API_KEY")
            if api_key:
                auth = RobinhoodSignatureAuth(
                    api_key=api_key,
                    public_key_b64=public_key_b64,
                    sandbox=True
                )
                details["derived_key_auth"] = auth.is_authenticated()
            else:
                details["derived_key_auth"] = False
                details["missing_api_key"] = True

        except Exception as e:
            details["key_conversion_success"] = False
            details["key_conversion_error"] = str(e)
            success = False

        # Test 2: Public key validation
        print("   Testing public key validation...")
        try:
            public_key_b64 = os.getenv("ROBINHOOD_PUBLIC_KEY")
            if public_key_b64:
                from base64 import b64decode
                public_key_der = b64decode(public_key_b64)
                details["public_key_valid"] = True
                details["public_key_length"] = len(public_key_der)
            else:
                details["public_key_valid"] = False
                details["no_public_key"] = True
        except Exception as e:
            details["public_key_valid"] = False
            details["public_key_error"] = str(e)
            success = False

        message = "Signature validation tested"

    except Exception as e:
        success = False
        message = f"Signature validation testing failed: {e}"

    debug_suite.log_test_result("Signature Validation", success, message, details)
    return success


async def test_environment_modes(debug_suite: APIDebugTestSuite):
    """Test 8: Sandbox vs Production environment handling."""
    print("\n🧪 TEST 8: Environment Modes")

    details = {}
    success = True

    try:
        # Test 1: Sandbox mode
        print("   Testing sandbox mode...")
        try:
            sandbox_client = RobinhoodClient(sandbox=True)
            details["sandbox_mode"] = sandbox_client.is_sandbox()
            details["sandbox_base_url"] = sandbox_client.config.base_url
            details["sandbox_auth_type"] = sandbox_client.auth.get_auth_info().get("auth_type", "unknown")
        except Exception as e:
            details["sandbox_mode"] = False
            details["sandbox_error"] = str(e)
            success = False

        # Test 2: Production mode
        print("   Testing production mode...")
        try:
            prod_client = RobinhoodClient(sandbox=False)
            details["production_mode"] = not prod_client.is_sandbox()
            details["production_base_url"] = prod_client.config.base_url
            details["production_auth_type"] = prod_client.auth.get_auth_info().get("auth_type", "unknown")
        except Exception as e:
            details["production_mode"] = False
            details["production_error"] = str(e)
            success = False

        # Test 3: Environment-specific endpoints
        print("   Testing environment-specific endpoints...")
        try:
            # Test sandbox endpoints
            sandbox_response = await sandbox_client.get("/instruments/")
            details["sandbox_endpoints"] = True
        except Exception as e:
            details["sandbox_endpoints"] = False
            details["sandbox_endpoints_error"] = str(e)

        message = "Environment modes tested"

    except Exception as e:
        success = False
        message = f"Environment modes testing failed: {e}"

    debug_suite.log_test_result("Environment Modes", success, message, details)
    return success


async def run_debug_tests():
    """Run all debugging tests and provide comprehensive analysis."""
    print("🚀 Starting Robinhood API Connection Debug Tests")
    print("="*80)

    debug_suite = APIDebugTestSuite()

    # Run all tests
    test_environment_setup(debug_suite)
    test_configuration_loading(debug_suite)
    test_authentication_methods(debug_suite)
    test_client_initialization(debug_suite)
    await test_api_connectivity(debug_suite)
    await test_error_handling(debug_suite)
    test_signature_validation(debug_suite)
    await test_environment_modes(debug_suite)

    # Print comprehensive summary
    debug_suite.print_summary()

    # Provide recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 40)

    if not any(r["success"] for r in debug_suite.test_results if "Configuration" in r["test"]):
        print("🔧 Fix configuration loading first:")
        print("   1. Ensure config/.env file exists with proper credentials")
        print("   2. Check that ROBINHOOD_API_KEY and either ROBINHOOD_PRIVATE_KEY or ROBINHOOD_PUBLIC_KEY are set")
        print("   3. Verify .env file format and encoding")

    if not any(r["success"] for r in debug_suite.test_results if "Authentication" in r["test"]):
        print("🔐 Fix authentication issues:")
        print("   1. Verify API key format (should start with 'rh-')")
        print("   2. Check private/public key base64 encoding")
        print("   3. Ensure keys are valid ECDSA keys")

    if not any(r["success"] for r in debug_suite.test_results if "Client" in r["test"]):
        print("🏗️ Fix client initialization:")
        print("   1. Call initialize_config() before creating RobinhoodClient")
        print("   2. Or provide credentials directly to RobinhoodClient")
        print("   3. Check that required environment variables are loaded")

    if debug_suite.client and not debug_suite.client.auth.is_authenticated():
        print("🔑 Authentication failed - check credentials:")
        print("   1. Verify API key is correct")
        print("   2. Check that private/public keys are valid")
        print("   3. Try both authentication methods")

    return debug_suite


if __name__ == "__main__":
    """Run debugging tests when script is executed directly."""
    asyncio.run(run_debug_tests())