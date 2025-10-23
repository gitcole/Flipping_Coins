"""
Market Making Strategy exports.

This module provides the market making strategy implementation with
sophisticated spread calculation, inventory management, and high-frequency
quoting capabilities for cryptocurrency markets.
"""

from .market_maker import (
    MarketMaker,
    MarketMakerConfig,
    OrderBookSnapshot,
    InventoryState,
    QuoteOrder,
)

__all__ = [
    # Main strategy implementation
    "MarketMaker",
    "MarketMakerConfig",

    # Data models
    "OrderBookSnapshot",
    "InventoryState",
    "QuoteOrder",
]