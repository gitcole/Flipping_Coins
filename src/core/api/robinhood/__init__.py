"""
Robinhood API Client

A comprehensive Python client for the Robinhood trading API, providing
authentication, trading, market data, and account management functionality.

This module provides:
- OAuth 2.0 authentication with PKCE
- Crypto trading capabilities
- Market data and quotes
- Order management
- Account and portfolio information
- Real-time data through WebSocket integration
"""

from .client import RobinhoodClient
from .auth import RobinhoodSignatureAuth
from .crypto import RobinhoodCrypto
from .crypto_api import RobinhoodCryptoAPI
from .market_data import RobinhoodMarketData
from .orders import RobinhoodOrders
from .account import RobinhoodAccount

__version__ = "1.0.0"
__all__ = [
    "RobinhoodClient",
    "RobinhoodSignatureAuth",
    "RobinhoodCrypto",
    "RobinhoodCryptoAPI",
    "RobinhoodMarketData",
    "RobinhoodOrders",
    "RobinhoodAccount",
]