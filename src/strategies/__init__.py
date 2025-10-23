"""
Strategy management system exports.

This module provides the complete strategy framework including base classes,
registry system, and strategy implementations for building sophisticated
trading strategies with lifecycle management and monitoring.
"""

from .base import (
    BaseStrategy,
    StrategyConfig,
    StrategyStatus,
    SignalDirection,
    TradingSignal,
    StrategyMetrics,
)

from .registry import (
    StrategyRegistry,
    StrategyRegistryConfig,
    StrategyHealth,
    DependencyStatus,
    StrategyInfo,
    StrategyDependency,
)

__all__ = [
    # Base strategy framework
    "BaseStrategy",
    "StrategyConfig",
    "StrategyStatus",
    "SignalDirection",
    "TradingSignal",
    "StrategyMetrics",

    # Strategy registry system
    "StrategyRegistry",
    "StrategyRegistryConfig",
    "StrategyHealth",
    "DependencyStatus",
    "StrategyInfo",
    "StrategyDependency",
]