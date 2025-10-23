"""Risk management system for crypto trading bot."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from ..core.config import get_settings
from ..core.engine.position_manager import Position, PositionManager
from ..utils.logging import get_logger


class RiskLimitExceededError(Exception):
    """Raised when risk limits are exceeded."""
    pass


class RiskValidationError(Exception):
    """Raised when risk validation fails."""
    pass


class RiskManager:
    """Central risk management and position sizing system."""

    def __init__(self, position_manager: Optional[PositionManager] = None):
        """Initialize risk manager.

        Args:
            position_manager: Position manager instance
        """
        self.settings = get_settings()
        self.logger = get_logger("risk.manager")

        self.position_manager = position_manager or PositionManager()

        # Risk state
        self.risk_metrics = {
            'total_portfolio_risk': 0.0,
            'max_position_risk': 0.0,
            'current_drawdown': 0.0,
            'correlation_risk': 0.0,
            'concentration_risk': 0.0,
        }

        # Risk tracking
        self.risk_history: List[Dict] = []
        self.alerts: List[Dict] = []

        # Risk rules
        self.max_portfolio_risk = self.settings.risk.max_portfolio_risk  # 10%
        self.max_position_risk = self.settings.trading.default_risk_per_trade  # 2%
        self.max_correlation = self.settings.risk.max_correlation  # 0.7
        self.max_drawdown = self.settings.risk.max_drawdown  # 20%
        self.max_positions = self.settings.trading.max_positions

    async def validate_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        strategy: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Validate trade against risk limits.

        Args:
            symbol: Trading symbol
            side: Trade side (BUY/SELL)
            quantity: Trade quantity
            price: Trade price
            strategy: Strategy name

        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Check position limits
            if not await self._check_position_limits(symbol, side, quantity):
                return False, f"Position limits exceeded for {symbol}"

            # Check portfolio risk
            if not await self._check_portfolio_risk(symbol, side, quantity, price):
                return False, f"Portfolio risk limits exceeded for {symbol}"

            # Check correlation risk
            if not await self._check_correlation_risk(symbol, side, quantity, price):
                return False, f"Correlation risk too high for {symbol}"

            # Check concentration risk
            if not await self._check_concentration_risk(symbol, quantity, price):
                return False, f"Concentration risk too high for {symbol}"

            # Check strategy-specific limits
            if strategy and not await self._check_strategy_limits(strategy, symbol, quantity, price):
                return False, f"Strategy limits exceeded for {strategy}"

            return True, "Trade approved"

        except Exception as e:
            self.logger.error(f"Error validating trade: {str(e)}")
            return False, f"Validation error: {str(e)}"

    async def _check_position_limits(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> bool:
        """Check position limits.

        Args:
            symbol: Trading symbol
            side: Trade side
            quantity: Trade quantity

        Returns:
            True if within limits
        """
        # Check maximum positions
        current_positions = len(self.position_manager.positions)
        if current_positions >= self.max_positions:
            self.logger.warning(f"Maximum positions ({self.max_positions}) reached")
            return False

        # Check if adding this position would exceed limits
        if side.upper() == "BUY":
            # For new positions, check if we can add one more
            if symbol not in self.position_manager.positions:
                if current_positions + 1 > self.max_positions:
                    return False

        return True

    async def _check_portfolio_risk(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> bool:
        """Check portfolio risk limits.

        Args:
            symbol: Trading symbol
            side: Trade side
            quantity: Trade quantity
            price: Trade price

        Returns:
            True if within limits
        """
        if not price:
            # Can't check risk without price
            return True

        # Calculate trade value
        trade_value = quantity * price

        # Calculate current portfolio risk
        current_risk = self._calculate_portfolio_risk()

        # Calculate new portfolio risk if trade is executed
        new_risk = self._calculate_trade_portfolio_risk(symbol, side, quantity, price, current_risk)

        # Check against maximum portfolio risk
        if new_risk > self.max_portfolio_risk:
            self.logger.warning(
                f"Portfolio risk {new_risk:.2%} would exceed limit {self.max_portfolio_risk:.2%}"
            )
            return False

        return True

    async def _check_correlation_risk(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> bool:
        """Check correlation risk limits.

        Args:
            symbol: Trading symbol
            side: Trade side
            quantity: Trade quantity
            price: Trade price

        Returns:
            True if within limits
        """
        if not price:
            return True

        # Calculate correlation with existing positions
        correlation_risk = self._calculate_correlation_risk(symbol, quantity * price)

        if correlation_risk > self.max_correlation:
            self.logger.warning(
                f"Correlation risk {correlation_risk:.2f} exceeds limit {self.max_correlation}"
            )
            return False

        return True

    async def _check_concentration_risk(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> bool:
        """Check concentration risk limits.

        Args:
            symbol: Trading symbol
            side: Trade side
            quantity: Trade quantity
            price: Trade price

        Returns:
            True if within limits
        """
        if not price:
            return True

        trade_value = quantity * price
        portfolio_value = self.position_manager.portfolio_value or 1.0

        # Calculate concentration percentage
        concentration = trade_value / portfolio_value

        # Check if this would create too much concentration
        if concentration > self.max_position_risk:
            self.logger.warning(
                f"Position concentration {concentration:.2%} exceeds limit {self.max_position_risk:.2%}"
            )
            return False

        return True

    async def _check_strategy_limits(
        self,
        strategy: str,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> bool:
        """Check strategy-specific limits.

        Args:
            strategy: Strategy name
            symbol: Trading symbol
            quantity: Trade quantity
            price: Trade price

        Returns:
            True if within limits
        """
        # Strategy-specific risk checks would go here
        # For now, just return True
        return True

    def _calculate_portfolio_risk(self) -> float:
        """Calculate current portfolio risk.

        Returns:
            Portfolio risk as percentage
        """
        if not self.position_manager.portfolio_value:
            return 0.0

        total_risk = sum(
            abs(pos.unrealized_pnl) for pos in self.position_manager.positions.values()
        )

        return total_risk / self.position_manager.portfolio_value

    def _calculate_trade_portfolio_risk(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        current_risk: float,
    ) -> float:
        """Calculate portfolio risk after trade.

        Args:
            symbol: Trading symbol
            side: Trade side
            quantity: Trade quantity
            price: Trade price
            current_risk: Current portfolio risk

        Returns:
            New portfolio risk
        """
        # Simplified calculation - in reality this would be more complex
        trade_value = quantity * price

        if side.upper() == "BUY":
            # Buying increases exposure
            return current_risk + (trade_value / self.position_manager.portfolio_value * 0.01)
        else:
            # Selling decreases exposure
            return max(0, current_risk - (trade_value / self.position_manager.portfolio_value * 0.01))

    def _calculate_correlation_risk(self, symbol: str, trade_value: float) -> float:
        """Calculate correlation risk.

        Args:
            symbol: Trading symbol
            trade_value: Trade value

        Returns:
            Correlation risk score
        """
        # Simplified correlation calculation
        # In a real system, this would use historical price data
        if not self.position_manager.positions:
            return 0.0

        # Assume average correlation of 0.3 for crypto assets
        avg_correlation = 0.3
        position_count = len(self.position_manager.positions)

        return avg_correlation * position_count

    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: Optional[float] = None,
        strategy: Optional[str] = None,
    ) -> float:
        """Calculate optimal position size based on risk.

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            strategy: Strategy name

        Returns:
            Optimal position size
        """
        portfolio_value = self.position_manager.portfolio_value or 10000  # Default if unknown

        # Base risk amount per trade
        risk_per_trade = portfolio_value * self.max_position_risk

        # If stop loss is provided, use it to calculate position size
        if stop_loss:
            if symbol.upper().endswith('USD'):
                # Crypto to USD pair
                price_diff = abs(entry_price - stop_loss)
                position_size = risk_per_trade / price_diff
            else:
                # Crypto to crypto pair (simplified)
                position_size = risk_per_trade / entry_price * 10  # Assume $10 per unit risk
        else:
            # Use percentage-based sizing
            position_size = (portfolio_value * self.max_position_risk) / entry_price

        # Apply minimum order size constraint
        min_order_size = self.settings.trading.min_order_size
        position_size = max(position_size, min_order_size)

        self.logger.info(
            f"Calculated position size for {symbol}: {position_size} "
            f"(portfolio: ${portfolio_value:,.0f}, risk: ${risk_per_trade:.2f})"
        )

        return position_size

    async def check_drawdown_limits(self) -> bool:
        """Check if current drawdown exceeds limits.

        Returns:
            True if within limits
        """
        if not self.position_manager.positions:
            return True

        # Calculate current drawdown
        total_unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.position_manager.positions.values()
        )

        if self.position_manager.portfolio_value > 0:
            current_drawdown = abs(total_unrealized_pnl) / self.position_manager.portfolio_value

            if current_drawdown > self.max_drawdown:
                self.logger.warning(
                    f"Drawdown {current_drawdown:.2%} exceeds limit {self.max_drawdown:.2%}"
                )

                # Create alert
                await self._create_alert(
                    "DRAWDOWN_EXCEEDED",
                    f"Portfolio drawdown {current_drawdown:.2%} exceeds limit {self.max_drawdown:.2%}",
                    "HIGH"
                )

                return False

        return True

    async def update_risk_metrics(self) -> None:
        """Update risk metrics."""
        try:
            # Update portfolio risk
            self.risk_metrics['total_portfolio_risk'] = self._calculate_portfolio_risk()

            # Update position risk
            if self.position_manager.positions:
                position_risks = [
                    abs(pos.unrealized_pnl) / max(pos.quantity * pos.avg_entry_price, 1)
                    for pos in self.position_manager.positions.values()
                ]
                self.risk_metrics['max_position_risk'] = max(position_risks) if position_risks else 0.0

            # Update drawdown
            await self.check_drawdown_limits()
            self.risk_metrics['current_drawdown'] = self.risk_metrics.get('current_drawdown', 0.0)

            # Update correlation risk
            self.risk_metrics['correlation_risk'] = self._calculate_correlation_risk('dummy', 0)

            # Update concentration risk
            self.risk_metrics['concentration_risk'] = self._calculate_concentration_risk()

            # Store in history
            self.risk_history.append(self.risk_metrics.copy())

            # Keep only recent history
            if len(self.risk_history) > 1000:
                self.risk_history = self.risk_history[-1000:]

        except Exception as e:
            self.logger.error(f"Error updating risk metrics: {str(e)}")

    def _calculate_concentration_risk(self) -> float:
        """Calculate concentration risk.

        Returns:
            Concentration risk score
        """
        if not self.position_manager.positions or not self.position_manager.portfolio_value:
            return 0.0

        # Calculate largest position as percentage of portfolio
        largest_position = 0.0
        for position in self.position_manager.positions.values():
            position_value = position.quantity * position.avg_entry_price
            position_pct = position_value / self.position_manager.portfolio_value
            largest_position = max(largest_position, position_pct)

        return largest_position

    async def _create_alert(self, alert_type: str, message: str, severity: str) -> None:
        """Create risk alert.

        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (LOW, MEDIUM, HIGH, CRITICAL)
        """
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': asyncio.get_event_loop().time(),
        }

        self.alerts.append(alert)
        self.logger.warning(f"Risk Alert [{severity}]: {message}")

        # Keep only recent alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

    def get_risk_summary(self) -> Dict:
        """Get risk management summary.

        Returns:
            Risk summary dictionary
        """
        return {
            'risk_metrics': self.risk_metrics,
            'limits': {
                'max_portfolio_risk': self.max_portfolio_risk,
                'max_position_risk': self.max_position_risk,
                'max_correlation': self.max_correlation,
                'max_drawdown': self.max_drawdown,
                'max_positions': self.max_positions,
            },
            'current_positions': len(self.position_manager.positions),
            'portfolio_value': self.position_manager.portfolio_value,
            'recent_alerts': self.alerts[-10:],  # Last 10 alerts
            'risk_history_length': len(self.risk_history),
        }

    def get_position_risk(self, symbol: str) -> Optional[Dict]:
        """Get risk information for a position.

        Args:
            symbol: Trading symbol

        Returns:
            Position risk information or None if not found
        """
        position = self.position_manager.positions.get(symbol)
        if not position:
            return None

        position_value = position.quantity * position.avg_entry_price
        portfolio_value = self.position_manager.portfolio_value or 1.0

        return {
            'symbol': symbol,
            'position_value': position_value,
            'portfolio_percentage': position_value / portfolio_value,
            'unrealized_pnl': position.unrealized_pnl,
            'risk_amount': abs(position.unrealized_pnl),
            'strategy': position.strategy,
        }