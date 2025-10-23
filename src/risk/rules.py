"""Risk rules and validation logic for trading bot."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Protocol

from ..core.config import get_settings
from ..utils.logging import get_logger


class RiskRule(Protocol):
    """Protocol for risk rules."""

    async def validate(self, context: Dict) -> bool:
        """Validate rule against context.

        Args:
            context: Validation context

        Returns:
            True if rule passes
        """
        ...

    def get_description(self) -> str:
        """Get rule description.

        Returns:
            Rule description
        """
        ...


class PositionLimitRule:
    """Rule to check position limits."""

    def __init__(self, max_positions: int = 10):
        """Initialize position limit rule.

        Args:
            max_positions: Maximum number of positions
        """
        self.max_positions = max_positions
        self.description = f"Maximum {max_positions} positions allowed"

    async def validate(self, context: Dict) -> bool:
        """Validate position limits.

        Args:
            context: Must contain 'current_positions' key

        Returns:
            True if within limits
        """
        current_positions = context.get('current_positions', 0)
        return current_positions < self.max_positions

    def get_description(self) -> str:
        return self.description


class PortfolioRiskRule:
    """Rule to check portfolio risk limits."""

    def __init__(self, max_risk: float = 0.1):
        """Initialize portfolio risk rule.

        Args:
            max_risk: Maximum portfolio risk (0.1 = 10%)
        """
        self.max_risk = max_risk
        self.description = f"Maximum portfolio risk: {max_risk:.1%}"

    async def validate(self, context: Dict) -> bool:
        """Validate portfolio risk.

        Args:
            context: Must contain 'portfolio_risk' and 'trade_risk' keys

        Returns:
            True if within limits
        """
        portfolio_risk = context.get('portfolio_risk', 0.0)
        trade_risk = context.get('trade_risk', 0.0)

        return (portfolio_risk + trade_risk) <= self.max_risk

    def get_description(self) -> str:
        return self.description


class PositionRiskRule:
    """Rule to check individual position risk."""

    def __init__(self, max_position_risk: float = 0.02):
        """Initialize position risk rule.

        Args:
            max_position_risk: Maximum risk per position (0.02 = 2%)
        """
        self.max_position_risk = max_position_risk
        self.description = f"Maximum position risk: {max_position_risk:.1%}"

    async def validate(self, context: Dict) -> bool:
        """Validate position risk.

        Args:
            context: Must contain 'position_value' and 'portfolio_value' keys

        Returns:
            True if within limits
        """
        position_value = context.get('position_value', 0.0)
        portfolio_value = context.get('portfolio_value', 1.0)

        if portfolio_value == 0:
            return True

        position_risk = position_value / portfolio_value
        return position_risk <= self.max_position_risk

    def get_description(self) -> str:
        return self.description


class CorrelationRule:
    """Rule to check asset correlation limits."""

    def __init__(self, max_correlation: float = 0.7):
        """Initialize correlation rule.

        Args:
            max_correlation: Maximum allowed correlation
        """
        self.max_correlation = max_correlation
        self.description = f"Maximum correlation: {max_correlation}"

    async def validate(self, context: Dict) -> bool:
        """Validate correlation limits.

        Args:
            context: Must contain 'asset_correlation' key

        Returns:
            True if within limits
        """
        asset_correlation = context.get('asset_correlation', 0.0)
        return asset_correlation <= self.max_correlation

    def get_description(self) -> str:
        return self.description


class DrawdownRule:
    """Rule to check drawdown limits."""

    def __init__(self, max_drawdown: float = 0.2):
        """Initialize drawdown rule.

        Args:
            max_drawdown: Maximum allowed drawdown (0.2 = 20%)
        """
        self.max_drawdown = max_drawdown
        self.description = f"Maximum drawdown: {max_drawdown:.1%}"

    async def validate(self, context: Dict) -> bool:
        """Validate drawdown limits.

        Args:
            context: Must contain 'current_drawdown' key

        Returns:
            True if within limits
        """
        current_drawdown = context.get('current_drawdown', 0.0)
        return current_drawdown <= self.max_drawdown

    def get_description(self) -> str:
        return self.description


class MinimumOrderSizeRule:
    """Rule to check minimum order size."""

    def __init__(self, min_order_size: float = 10.0):
        """Initialize minimum order size rule.

        Args:
            min_order_size: Minimum order size in base currency
        """
        self.min_order_size = min_order_size
        self.description = f"Minimum order size: ${min_order_size}"

    async def validate(self, context: Dict) -> bool:
        """Validate minimum order size.

        Args:
            context: Must contain 'order_value' key

        Returns:
            True if meets minimum size
        """
        order_value = context.get('order_value', 0.0)
        return order_value >= self.min_order_size

    def get_description(self) -> str:
        return self.description


class RiskRuleEngine:
    """Engine for managing and executing risk rules."""

    def __init__(self):
        """Initialize risk rule engine."""
        self.settings = get_settings()
        self.logger = get_logger("risk.rules")

        self.rules: List[RiskRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize default risk rules."""
        # Position limit rule
        self.add_rule(PositionLimitRule(self.settings.trading.max_positions))

        # Portfolio risk rule
        self.add_rule(PortfolioRiskRule(self.settings.risk.max_portfolio_risk))

        # Position risk rule
        self.add_rule(PositionRiskRule(self.settings.trading.default_risk_per_trade))

        # Correlation rule
        self.add_rule(CorrelationRule(self.settings.risk.max_correlation))

        # Drawdown rule
        self.add_rule(DrawdownRule(self.settings.risk.max_drawdown))

        # Minimum order size rule
        self.add_rule(MinimumOrderSizeRule(self.settings.trading.min_order_size))

    def add_rule(self, rule: RiskRule) -> None:
        """Add risk rule.

        Args:
            rule: Risk rule to add
        """
        self.rules.append(rule)
        self.logger.debug(f"Added risk rule: {rule.get_description()}")

    def remove_rule(self, rule: RiskRule) -> None:
        """Remove risk rule.

        Args:
            rule: Risk rule to remove
        """
        try:
            self.rules.remove(rule)
            self.logger.debug(f"Removed risk rule: {rule.get_description()}")
        except ValueError:
            self.logger.warning("Risk rule not found")

    async def validate_trade(self, context: Dict) -> List[str]:
        """Validate trade against all rules.

        Args:
            context: Validation context

        Returns:
            List of validation failure messages
        """
        failures = []

        for rule in self.rules:
            try:
                if not await rule.validate(context):
                    failures.append(rule.get_description())
            except Exception as e:
                self.logger.error(f"Error validating rule {rule.get_description()}: {str(e)}")
                failures.append(f"Rule validation error: {str(e)}")

        return failures

    async def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        portfolio_value: Optional[float] = None,
        current_positions: Optional[int] = None,
        **context
    ) -> List[str]:
        """Validate order against risk rules.

        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            price: Order price
            portfolio_value: Current portfolio value
            current_positions: Current number of positions
            **context: Additional context

        Returns:
            List of validation failure messages
        """
        # Build validation context
        validation_context = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'order_value': quantity * (price or 0),
            'portfolio_value': portfolio_value or 10000,
            'current_positions': current_positions or 0,
            **context
        }

        return await self.validate_trade(validation_context)

    def get_rule_descriptions(self) -> List[str]:
        """Get descriptions of all rules.

        Returns:
            List of rule descriptions
        """
        return [rule.get_description() for rule in self.rules]

    def get_rules_count(self) -> int:
        """Get number of active rules.

        Returns:
            Number of rules
        """
        return len(self.rules)