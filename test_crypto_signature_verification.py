#!/usr/bin/env python3
"""
Crypto API Signature Verification Test

This script tests the signature generation for Robinhood Crypto API
using the exact format: api_key + timestamp + path + method + body (JSON)

Usage:
    python test_crypto_signature_verification.py

Requirements:
    - Set ROBINHOOD_API_KEY and ROBINHOOD_PRIVATE_KEY in config/.env
    - Or provide them as arguments
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from ecdsa import SigningKey
from base64 import b64decode, b64encode

from src.core.api.robinhood.crypto_api import RobinhoodCryptoAPI
from src.utils.logging import get_logger
from src.core.config import initialize_config

load_dotenv('config/.env')

# Initialize configuration
initialize_config()

logger = get_logger(__name__)


def generate_signature(api_key: str, private_key_b64: str, timestamp: int, endpoint: str, method: str, body: str) -> str:
    """Generate signature using the exact format from the crypto API."""
    message = f"{api_key}{timestamp}{endpoint}{method}{body}"
    logger.info(f"🔍 DEBUG: Signature message: {message}")

    private_key_der = b64decode(private_key_b64)
    signing_key = SigningKey.from_der(private_key_der)
    signature = signing_key.sign(message.encode('utf-8'))
    signature_b64 = b64encode(signature).decode('utf-8')

    return signature_b64


async def test_signature_generation():
    """Test signature generation with various scenarios."""
    print("🔐 CRYPTO API SIGNATURE VERIFICATION TEST")
    print("="*60)

    # Load credentials
    api_key = os.getenv("ROBINHOOD_API_KEY")
    private_key_b64 = os.getenv("ROBINHOOD_PRIVATE_KEY")

    # Generate test credentials if not available
    if not api_key:
        api_key = "rh-test-api-key-12345"
        print("⚠️ Using test API key (not real)")
    else:
        print(f"✅ API Key loaded: {api_key[:20]}...")

    if not private_key_b64:
        print("🔑 Generating test private key for signature verification...")
        from ecdsa import SigningKey
        from base64 import b64encode

        sk = SigningKey.generate()
        private_key_b64 = b64encode(sk.to_der()).decode('utf-8')
        print("✅ Test private key generated")
    else:
        print(f"✅ Private Key loaded: {private_key_b64[:30]}...")

    # Test cases
    test_cases = [
        {
            "name": "GET request without body",
            "endpoint": "/api/v1/crypto/trading/accounts/",
            "method": "GET",
            "data": None
        },
        {
            "name": "POST request with body",
            "endpoint": "/api/v1/crypto/trading/orders/",
            "method": "POST",
            "data": {
                "client_order_id": "test_order_123",
                "side": "buy",
                "type": "market",
                "symbol": "BTC",
                "quantity": "0.1",
                "time_in_force": "gtc"
            }
        },
        {
            "name": "GET request with params",
            "endpoint": "/api/v1/crypto/marketdata/best_bid_ask/",
            "method": "GET",
            "data": None,
            "params": {"symbol": "BTC,ETH"}
        }
    ]

    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print("-" * 40)

        # Prepare body
        if test_case['data']:
            body = json.dumps(test_case['data'], separators=(',', ':'))
        else:
            body = ""

        # Generate timestamp
        timestamp = int(datetime.now(tz=timezone.utc).timestamp())

        # Generate signature manually
        manual_signature = generate_signature(api_key, private_key_b64, timestamp, test_case['endpoint'], test_case['method'], body)

        print(f"   Timestamp: {timestamp}")
        print(f"   Endpoint: {test_case['endpoint']}")
        print(f"   Method: {test_case['method']}")
        print(f"   Body: {body[:100] if body else 'empty'}")
        print(f"   Manual Signature: {manual_signature[:50]}...")

        # Generate signature using the API client simulation
        try:
            # Simulate the exact signature generation from the API client
            message = f"{api_key}{timestamp}{test_case['endpoint']}{test_case['method']}{body}"
            signing_key = SigningKey(b64decode(private_key_b64))
            signature = signing_key.sign(message.encode('utf-8'))
            api_signature_b64 = b64encode(signature).decode('utf-8')

            print(f"   API Signature: {api_signature_b64[:50]}...")

            # Compare signatures
            if manual_signature == api_signature_b64:
                print("   ✅ Signatures match!")
            else:
                print("   ❌ Signatures do NOT match!")
                print(f"   Difference at: {next((i for i, (a,b) in enumerate(zip(manual_signature, api_signature_b64)) if a != b), 'None')}")

        except Exception as e:
            print(f"   ❌ Error generating API signature: {e}")

        print(f"   Full message: {message}")
        print(f"   Message length: {len(message)}")


async def test_api_request():
    """Test actual API request with signature (requires valid credentials)."""
    print("\n🌐 TESTING ACTUAL API REQUEST")
    print("="*60)

    api_key = os.getenv("ROBINHOOD_API_KEY")
    private_key_b64 = os.getenv("ROBINHOOD_PRIVATE_KEY")

    # Generate test credentials if not available
    if not api_key:
        api_key = "rh-test-api-key-12345"

    if not private_key_b64:
        from ecdsa import SigningKey
        from base64 import b64encode
        sk = SigningKey.generate()
        private_key_b64 = b64encode(sk.to_der()).decode('utf-8')

    print(f"⚠️ Using test credentials for API test (will fail but test signature)")

    try:
        async with RobinhoodCryptoAPI(access_token=api_key) as api:
            # Try a simple GET request
            print("   Making test request to /api/v1/crypto/trading/accounts/")
            result = await api.get_account()
            print(f"   ✅ API request successful: {result.id}")

    except Exception as e:
        print(f"   ❌ API request failed: {e}")
        logger.error(f"API request error: {e}")


if __name__ == "__main__":
    asyncio.run(test_signature_generation())
    asyncio.run(test_api_request())