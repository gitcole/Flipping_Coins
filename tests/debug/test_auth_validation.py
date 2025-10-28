"""
Authentication Validation Tests for Robinhood API

Comprehensive tests for validating authentication methods including:
- Private key authentication validation
- Public key authentication validation  
- Key format and conversion validation
- Authentication error handling
- Environment-based authentication testing

Usage:
    python tests/debug/test_auth_validation.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import structlog
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.api.exceptions import AuthenticationError
from src.core.api.robinhood.auth import RobinhoodSignatureAuth
from src.core.config import initialize_config, get_settings
from src.utils.logging import get_logger

logger = structlog.get_logger(__name__)
test_logger = get_logger("auth_debug")


class AuthValidationTestSuite:
    """Comprehensive authentication validation test suite."""

    def __init__(self):
        """Initialize the authentication test suite."""
        self.test_results = []
        self.issues_found = []

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
        print("🔐 ROBINHOOD AUTHENTICATION VALIDATION SUMMARY")
        print("="*80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")

        if self.issues_found:
            print(f"\n🚨 AUTHENTICATION ISSUES FOUND ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue['test']}: {issue['message']}")
                if issue['details']:
                    for key, value in issue['details'].items():
                        print(f"      {key}: {value}")
        else:
            print("\n🎉 All authentication tests passed!")

        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")


def test_environment_auth_loading(auth_suite: AuthValidationTestSuite):
    """Test 1: Authentication credential loading from environment."""
    print("\n🧪 TEST 1: Environment Authentication Loading")

    details = {}
    success = True

    try:
        # Test 1: Check environment variables
        print("   Checking environment variables...")
        api_key = os.getenv("ROBINHOOD_API_KEY")
        private_key = os.getenv("ROBINHOOD_PRIVATE_KEY")
        public_key = os.getenv("ROBINHOOD_PUBLIC_KEY")
        sandbox = os.getenv("ROBINHOOD_SANDBOX", "false").lower() == "true"

        details["env_api_key"] = api_key[:30] + "..." if api_key and len(api_key) > 30 else api_key or "None"
        details["env_private_key"] = private_key[:30] + "..." if private_key and len(private_key) > 30 else private_key or "None"
        details["env_public_key"] = public_key[:30] + "..." if public_key and len(public_key) > 30 else public_key or "None"
        details["env_sandbox"] = sandbox

        # Test 2: Load .env files and recheck
        print("   Loading .env files...")
        load_dotenv('config/.env', override=True)
        load_dotenv('.env', override=True)

        api_key = os.getenv("ROBINHOOD_API_KEY")
        private_key = os.getenv("ROBINHOOD_PRIVATE_KEY")
        public_key = os.getenv("ROBINHOOD_PUBLIC_KEY")

        details["env_after_load_api_key"] = api_key[:30] + "..." if api_key and len(api_key) > 30 else api_key or "None"
        details["env_after_load_private_key"] = private_key[:30] + "..." if private_key and len(private_key) > 30 else private_key or "None"
        details["env_after_load_public_key"] = public_key[:30] + "..." if public_key and len(public_key) > 30 else public_key or "None"

        # Test 3: Try configuration loading
        print("   Testing configuration loading...")
        try:
            settings = initialize_config()
            details["config_loaded"] = True
            details["config_api_key"] = settings.robinhood.api_key[:30] + "..." if settings.robinhood.api_key else "None"
            details["config_private_key"] = settings.robinhood.private_key[:30] + "..." if settings.robinhood.private_key else "None"
            details["config_public_key"] = settings.robinhood.public_key[:30] + "..." if settings.robinhood.public_key else "None"
            details["config_sandbox"] = settings.robinhood.sandbox
        except Exception as e:
            details["config_loaded"] = False
            details["config_error"] = str(e)
            success = False

        message = "Environment authentication loading tested"

    except Exception as e:
        success = False
        message = f"Environment authentication loading failed: {e}"

    auth_suite.log_test_result("Environment Authentication Loading", success, message, details)
    return success


def test_private_key_auth_validation(auth_suite: AuthValidationTestSuite):
    """Test 2: Private key authentication validation."""
    print("\n🧪 TEST 2: Private Key Authentication Validation")

    details = {}
    success = True

    try:
        # Test 1: Valid private key from environment
        print("   Testing valid private key from environment...")
        api_key = os.getenv("ROBINHOOD_API_KEY")
        private_key = os.getenv("ROBINHOOD_PRIVATE_KEY")

        if api_key and private_key:
            try:
                auth = RobinhoodSignatureAuth(
                    api_key=api_key,
                    private_key_b64=private_key,
                    sandbox=True
                )
                details["env_private_key_valid"] = auth.is_authenticated()
                details["env_private_key_type"] = auth.get_auth_info().get("auth_type", "unknown")
                details["env_private_key_api_key"] = auth.get_api_key()[:20] + "..."
                details["env_private_key_public"] = auth.get_public_key()[:30] + "..."
            except Exception as e:
                details["env_private_key_valid"] = False
                details["env_private_key_error"] = str(e)
                success = False
        else:
            details["env_private_key_valid"] = False
            details["env_private_key_error"] = "Missing API key or private key"
            success = False

        # Test 2: Generated test private key
        print("   Testing generated test private key...")
        try:
            from ecdsa import SigningKey
            from base64 import b64encode

            sk = SigningKey.generate()
            test_private_key = b64encode(sk.to_der()).decode('utf-8')
            test_public_key = b64encode(sk.verifying_key.to_der()).decode('utf-8')

            auth = RobinhoodSignatureAuth(
                api_key="test_api_key_12345",
                private_key_b64=test_private_key,
                sandbox=True
            )

            details["test_private_key_valid"] = auth.is_authenticated()
            details["test_private_key_type"] = auth.get_auth_info().get("auth_type", "unknown")
            details["test_private_key_api_key"] = auth.get_api_key()
            details["test_private_key_public"] = auth.get_public_key()[:30] + "..."
            details["test_public_key_derived"] = test_public_key[:30] + "..."

        except Exception as e:
            details["test_private_key_valid"] = False
            details["test_private_key_error"] = str(e)
            success = False

        # Test 3: Invalid private key formats
        print("   Testing invalid private key formats...")
        invalid_keys = [
            "invalid_key",
            "MF8CAQEE",  # too short
            "MF8CAQEEGO+yeKLB0dCppmnu++31Pa/H51py22zmd6AKBggqhkjOPQMBAaE0AzIABHIfySeMpGsEoEsg7Wp6tgCcJgpPaA5WMkT+1y55auVDkNqw/gG6ecI9zh/s40GxAg==extra",  # too long
        ]

        for i, invalid_key in enumerate(invalid_keys):
            try:
                auth = RobinhoodSignatureAuth(
                    api_key="test_api_key",
                    private_key_b64=invalid_key,
                    sandbox=True
                )
                details[f"invalid_key_{i}_accepted"] = auth.is_authenticated()
            except Exception:
                details[f"invalid_key_{i}_accepted"] = False

        message = "Private key authentication validation tested"

    except Exception as e:
        success = False
        message = f"Private key authentication validation failed: {e}"

    auth_suite.log_test_result("Private Key Authentication Validation", success, message, details)
    return success


def test_public_key_auth_validation(auth_suite: AuthValidationTestSuite):
    """Test 3: Public key authentication validation."""
    print("\n🧪 TEST 3: Public Key Authentication Validation")

    details = {}
    success = True

    try:
        # Test 1: Valid public key from environment
        print("   Testing valid public key from environment...")
        api_key = os.getenv("ROBINHOOD_API_KEY")
        public_key = os.getenv("ROBINHOOD_PUBLIC_KEY")

        if api_key and public_key:
            try:
                auth = RobinhoodSignatureAuth(
                    api_key=api_key,
                    public_key_b64=public_key,
                    sandbox=True
                )
                details["env_public_key_valid"] = auth.is_authenticated()
                details["env_public_key_type"] = auth.get_auth_info().get("auth_type", "unknown")
                details["env_public_key_api_key"] = auth.get_api_key()[:20] + "..."
                details["env_public_key_length"] = len(public_key)
            except Exception as e:
                details["env_public_key_valid"] = False
                details["env_public_key_error"] = str(e)
                success = False
        else:
            details["env_public_key_valid"] = False
            details["env_public_key_error"] = "Missing API key or public key"
            success = False

        # Test 2: Generated test public key
        print("   Testing generated test public key...")
        try:
            from ecdsa import SigningKey
            from base64 import b64encode

            sk = SigningKey.generate()
            test_public_key = b64encode(sk.verifying_key.to_der()).decode('utf-8')

            auth = RobinhoodSignatureAuth(
                api_key="test_api_key_12345",
                public_key_b64=test_public_key,
                sandbox=True
            )

            details["test_public_key_valid"] = auth.is_authenticated()
            details["test_public_key_type"] = auth.get_auth_info().get("auth_type", "unknown")
            details["test_public_key_api_key"] = auth.get_api_key()
            details["test_public_key_length"] = len(test_public_key)

        except Exception as e:
            details["test_public_key_valid"] = False
            details["test_public_key_error"] = str(e)
            success = False

        # Test 3: Invalid public key formats
        print("   Testing invalid public key formats...")
        invalid_keys = [
            "invalid_key",
            "MFkwEwYHKoZI",  # too short
            "MFkwEwYHKoZIjv6gYgMFkwEwYHKoZIjv6gYgMFkwEwYHKoZIjv6gYgextra",  # too long
        ]

        for i, invalid_key in enumerate(invalid_keys):
            try:
                auth = RobinhoodSignatureAuth(
                    api_key="test_api_key",
                    public_key_b64=invalid_key,
                    sandbox=True
                )
                details[f"invalid_public_key_{i}_accepted"] = auth.is_authenticated()
            except Exception:
                details[f"invalid_public_key_{i}_accepted"] = False

        message = "Public key authentication validation tested"

    except Exception as e:
        success = False
        message = f"Public key authentication validation failed: {e}"

    auth_suite.log_test_result("Public Key Authentication Validation", success, message, details)
    return success


def test_key_conversion_validation(auth_suite: AuthValidationTestSuite):
    """Test 4: Key conversion and validation between formats."""
    print("\n🧪 TEST 4: Key Conversion Validation")

    details = {}
    success = True

    try:
        # Test 1: Private key to public key conversion
        print("   Testing private to public key conversion...")
        try:
            from ecdsa import SigningKey
            from base64 import b64encode, b64decode

            # Use environment private key or generate test one
            private_key_b64 = os.getenv("ROBINHOOD_PRIVATE_KEY")
            if not private_key_b64:
                sk = SigningKey.generate()
                private_key_b64 = b64encode(sk.to_der()).decode('utf-8')

            # Convert private key to public key
            private_key_der = b64decode(private_key_b64)
            signing_key = SigningKey.from_der(private_key_der)
            public_key_der = signing_key.verifying_key.to_der()
            converted_public_key = b64encode(public_key_der).decode('utf-8')

            details["conversion_success"] = True
            details["original_private_key"] = private_key_b64[:30] + "..."
            details["converted_public_key"] = converted_public_key[:30] + "..."

            # Test that public key auth works with converted key
            api_key = os.getenv("ROBINHOOD_API_KEY") or "test_api_key"
            auth = RobinhoodSignatureAuth(
                api_key=api_key,
                public_key_b64=converted_public_key,
                sandbox=True
            )
            details["converted_key_auth"] = auth.is_authenticated()

        except Exception as e:
            details["conversion_success"] = False
            details["conversion_error"] = str(e)
            success = False

        # Test 2: Validate key lengths and formats
        print("   Testing key format validation...")
        try:
            # Test private key format
            if private_key_b64:
                private_key_der = b64decode(private_key_b64)
                details["private_key_der_length"] = len(private_key_der)
                details["private_key_format_valid"] = len(private_key_der) > 0

            # Test public key format
            public_key_b64 = os.getenv("ROBINHOOD_PUBLIC_KEY")
            if public_key_b64:
                public_key_der = b64decode(public_key_b64)
                details["public_key_der_length"] = len(public_key_der)
                details["public_key_format_valid"] = len(public_key_der) > 0

        except Exception as e:
            details["format_validation_success"] = False
            details["format_validation_error"] = str(e)
            success = False
        else:
            details["format_validation_success"] = True

        message = "Key conversion validation tested"

    except Exception as e:
        success = False
        message = f"Key conversion validation failed: {e}"

    auth_suite.log_test_result("Key Conversion Validation", success, message, details)
    return success


def test_auth_error_handling(auth_suite: AuthValidationTestSuite):
    """Test 5: Authentication error handling."""
    print("\n🧪 TEST 5: Authentication Error Handling")

    details = {}
    success = True

    try:
        # Test 1: Missing API key
        print("   Testing missing API key handling...")
        try:
            auth = RobinhoodSignatureAuth(
                api_key=None,
                private_key_b64="MF8CAQEEGO+yeKLB0dCppmnu++31Pa/H51py22zmd6AKBggqhkjOPQMBAaE0AzIABHIfySeMpGsEoEsg7Wp6tgCcJgpPaA5WMkT+1y55auVDkNqw/gG6ecI9zh/s40GxAg==",
                sandbox=True
            )
            details["missing_api_key_handled"] = False
        except AuthenticationError:
            details["missing_api_key_handled"] = True
        except Exception as e:
            details["missing_api_key_handled"] = False
            details["missing_api_key_unexpected"] = str(e)

        # Test 2: Missing keys (both private and public)
        print("   Testing missing keys handling...")
        try:
            auth = RobinhoodSignatureAuth(
                api_key="test_api_key",
                private_key_b64=None,
                public_key_b64=None,
                sandbox=True
            )
            details["missing_keys_handled"] = False
        except AuthenticationError:
            details["missing_keys_handled"] = True
        except Exception as e:
            details["missing_keys_handled"] = False
            details["missing_keys_unexpected"] = str(e)

        # Test 3: Invalid key data
        print("   Testing invalid key data handling...")
        try:
            auth = RobinhoodSignatureAuth(
                api_key="test_api_key",
                private_key_b64="clearly_invalid_key_data",
                sandbox=True
            )
            details["invalid_key_handled"] = False
        except (AuthenticationError, Exception):
            details["invalid_key_handled"] = True

        # Test 4: Access methods without authentication
        print("   Testing access method protection...")
        try:
            auth = RobinhoodSignatureAuth(
                api_key="test_api_key",
                private_key_b64="MF8CAQEEGO+yeKLB0dCppmnu++31Pa/H51py22zmd6AKBggqhkjOPQMBAaE0AzIABHIfySeMpGsEoEsg7Wp6tgCcJgpPaA5WMkT+1y55auVDkNqw/gG6ecI9zh/s40GxAg==",
                sandbox=True
            )

            # These should work if authenticated
            if auth.is_authenticated():
                try:
                    api_key = auth.get_api_key()
                    details["get_api_key_works"] = True
                except Exception:
                    details["get_api_key_works"] = False

                try:
                    private_key = auth.get_private_key()
                    details["get_private_key_works"] = True
                except Exception:
                    details["get_private_key_works"] = False

                try:
                    public_key = auth.get_public_key()
                    details["get_public_key_works"] = True
                except Exception:
                    details["get_public_key_works"] = False
            else:
                details["auth_not_authenticated"] = True

        except Exception as e:
            details["access_method_error"] = str(e)

        message = "Authentication error handling tested"

    except Exception as e:
        success = False
        message = f"Authentication error handling testing failed: {e}"

    auth_suite.log_test_result("Authentication Error Handling", success, message, details)
    return success


def test_sandbox_vs_production_auth(auth_suite: AuthValidationTestSuite):
    """Test 6: Sandbox vs Production authentication differences."""
    print("\n🧪 TEST 6: Sandbox vs Production Authentication")

    details = {}
    success = True

    try:
        api_key = os.getenv("ROBINHOOD_API_KEY")
        private_key = os.getenv("ROBINHOOD_PRIVATE_KEY")

        if not api_key or not private_key:
            auth_suite.log_test_result("Sandbox vs Production Authentication", False, "Missing credentials for testing")
            return False

        # Test 1: Sandbox authentication
        print("   Testing sandbox authentication...")
        try:
            auth_sandbox = RobinhoodSignatureAuth(
                api_key=api_key,
                private_key_b64=private_key,
                sandbox=True
            )
            details["sandbox_auth_success"] = auth_sandbox.is_authenticated()
            details["sandbox_auth_type"] = auth_sandbox.get_auth_info().get("auth_type", "unknown")
            details["sandbox_base_url"] = auth_sandbox.get_auth_info().get("base_url", "unknown")
        except Exception as e:
            details["sandbox_auth_success"] = False
            details["sandbox_auth_error"] = str(e)
            success = False

        # Test 2: Production authentication
        print("   Testing production authentication...")
        try:
            auth_production = RobinhoodSignatureAuth(
                api_key=api_key,
                private_key_b64=private_key,
                sandbox=False
            )
            details["production_auth_success"] = auth_production.is_authenticated()
            details["production_auth_type"] = auth_production.get_auth_info().get("auth_type", "unknown")
            details["production_base_url"] = auth_production.get_auth_info().get("base_url", "unknown")
        except Exception as e:
            details["production_auth_success"] = False
            details["production_auth_error"] = str(e)
            success = False

        # Test 3: Compare authentication info
        print("   Comparing authentication configurations...")
        if details.get("sandbox_auth_success") and details.get("production_auth_success"):
            details["auth_consistency"] = (
                details.get("sandbox_auth_type") == details.get("production_auth_type")
            )
            details["base_url_consistency"] = (
                details.get("sandbox_base_url") == details.get("production_base_url")
            )
        else:
            details["auth_consistency"] = False
            details["base_url_consistency"] = False

        message = "Sandbox vs Production authentication tested"

    except Exception as e:
        success = False
        message = f"Sandbox vs Production authentication testing failed: {e}"

    auth_suite.log_test_result("Sandbox vs Production Authentication", success, message, details)
    return success


async def run_auth_validation_tests():
    """Run all authentication validation tests."""
    print("🔐 Starting Robinhood Authentication Validation Tests")
    print("="*80)

    auth_suite = AuthValidationTestSuite()

    # Run all tests
    test_environment_auth_loading(auth_suite)
    test_private_key_auth_validation(auth_suite)
    test_public_key_auth_validation(auth_suite)
    test_key_conversion_validation(auth_suite)
    test_auth_error_handling(auth_suite)
    test_sandbox_vs_production_auth(auth_suite)

    # Print comprehensive summary
    auth_suite.print_summary()

    # Provide specific recommendations
    print("\n💡 AUTHENTICATION RECOMMENDATIONS:")
    print("-" * 50)

    # Check for specific issues and provide recommendations
    env_missing = False
    auth_failing = False

    for issue in auth_suite.issues_found:
        if "Environment" in issue["test"]:
            env_missing = True
        if "Authentication" in issue["test"]:
            auth_failing = True

    if env_missing:
        print("🔧 Fix environment credential issues:")
        print("   1. Ensure config/.env file exists with proper credentials")
        print("   2. Set ROBINHOOD_API_KEY (should start with 'rh-')")
        print("   3. Set either ROBINHOOD_PRIVATE_KEY or ROBINHOOD_PUBLIC_KEY")
        print("   4. Verify keys are base64-encoded ECDSA keys")

    if auth_failing:
        print("🔐 Fix authentication issues:")
        print("   1. Verify API key format and validity")
        print("   2. Check that private/public keys are valid ECDSA keys")
        print("   3. Test both authentication methods (private and public key)")
        print("   4. Ensure keys are properly base64-encoded")

    print("\n📋 Next Steps:")
    print("   1. Run the API connectivity tests to verify end-to-end functionality")
    print("   2. Test with both sandbox and production environments")
    print("   3. Validate request signing and response handling")

    return auth_suite


if __name__ == "__main__":
    """Run authentication validation tests when script is executed directly."""
    asyncio.run(run_auth_validation_tests())