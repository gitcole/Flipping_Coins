#!/usr/bin/env python3
"""
Debug API Connectivity Test

This script tests the API connectivity with enhanced logging to help diagnose issues.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.api.robinhood.crypto_api import RobinhoodCryptoAPI
from src.core.config import initialize_config
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def test_api_connectivity():
    """Test API connectivity with detailed logging."""
    print("🔍 API CONNECTIVITY DEBUG TEST")
    print("="*50)

    # Initialize configuration
    print("📋 Initializing configuration...")
    initialize_config()

    print("🚀 Creating API client...")
    try:
        async with RobinhoodCryptoAPI() as api:
            print("✅ API client created successfully")

            print("🔍 Running health check...")
            health_result = await api.health_check()
            print(f"🏥 Health check result: {health_result}")

    except Exception as e:
        print(f"❌ API connectivity test failed: {e}")
        logger.error(f"API connectivity error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_api_connectivity())