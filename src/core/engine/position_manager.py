"""Portfolio position tracking and management."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Dict, List, Optional, Set

from ..config import get_settings
from ...utils.logging import get_logger


class Position:
    """Represents a trading position."""

    def __init__(
        self,
        symbol: str,
        quantity: float,
        avg_entry_price: float,
        strategy: Optional[str] = None,
        unrealized_pnl: float = 0.0,
        realized_pnl: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        opened_at: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Initialize position.

        Args:
            symbol: Trading symbol
            quantity: Position quantity (positive for long, negative for short)
            avg_entry_price: Average entry price
            strategy: Strategy that opened the position
            unrealized_pnl: Unrealized profit/loss
            realized_pnl: Realized profit/loss
            stop_loss: Stop loss price
            take_profit: Take profit price
            opened_at: Position opening timestamp
            tags: Additional metadata tags
        """
        self.symbol = symbol
        self.quantity = quantity
        self.avg_entry_price = avg_entry_price
        self.strategy = strategy
        self.unrealized_pnl = unrealized_pnl
        self.realized_pnl = realized_pnl
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.opened_at = opened_at or time.time()
        self.tags = tags or {}

        # Track updates
        self.last_update = time.time()
        self.update_count = 0

    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        return abs(self.quantity) * self.avg_entry_price

    @property
    def total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_percentage(self) -> float:
        """Get P&L as percentage of entry value."""
        if self.market_value == 0:
            return 0.0
        return (self.total_pnl / self.market_value) * 100.0

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.quantity < 0

    @property
    def is_profitable(self) -> bool:
        """Check if position is currently profitable."""
        return self.total_pnl > 0

    @property
    def risk_amount(self) -> float:
        """Calculate position risk amount."""
        settings = get_settings()
        return self.market_value * settings.trading.default_risk_per_trade

    def update_unrealized_pnl(self, current_price: float) -> None:
        """Update unrealized P&L based on current market price.

        Args:
            current_price: Current market price
        """
        if self.quantity > 0:  # Long position
            self.unrealized_pnl = (current_price - self.avg_entry_price) * self.quantity
        else:  # Short position
            self.unrealized_pnl = (self.avg_entry_price - current_price) * abs(self.quantity)

        self.last_update = time.time()
        self.update_count += 1

    def should_trigger_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss should be triggered.

        Args:
            current_price: Current market price

        Returns:
            True if stop loss should be triggered
        """
        if not self.stop_loss:
            return False

        if self.quantity > 0:  # Long position
            return current_price <= self.stop_loss
        else:  # Short position
            return current_price >= self.stop_loss

    def should_trigger_take_profit(self, current_price: float) -> bool:
        """Check if take profit should be triggered.

        Args:
            current_price: Current market price

        Returns:
            True if take profit should be triggered
        """
        if not self.take_profit:
            return False

        if self.quantity > 0:  # Long position
            return current_price >= self.take_profit
        else:  # Short position
            return current_price <= self.take_profit

    def set_stop_loss(self, price: float, use_trailing: bool = False) -> None:
        """Set stop loss for the position.

        Args:
            price: Stop loss price
            use_trailing: Whether to use trailing stop loss
        """
        self.stop_loss = price
        if use_trailing:
            self.tags['trailing_stop'] = 'true'

    def set_take_profit(self, price: float) -> None:
        """Set take profit for the position.

        Args:
            price: Take profit price
        """
        self.take_profit = price

    def add_tag(self, key: str, value: str) -> None:
        """Add a metadata tag.

        Args:
            key: Tag key
            value: Tag value
        """
        self.tags[key] = value

    def get_tag(self, key: str, default: str = "") -> str:
        """Get a metadata tag value.

        Args:
            key: Tag key
            default: Default value if tag not found

        Returns:
            Tag value or default
        """
        return self.tags.get(key, default)

    def to_dict(self) -> Dict:
        """Convert position to dictionary."""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_entry_price': self.avg_entry_price,
            'strategy': self.strategy,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'total_pnl': self.total_pnl,
            'pnl_percentage': self.pnl_percentage,
            'market_value': self.market_value,
            'risk_amount': self.risk_amount,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'opened_at': self.opened_at,
            'last_update': self.last_update,
            'update_count': self.update_count,
            'tags': self.tags.copy(),
            'is_long': self.is_long,
            'is_short': self.is_short,
            'is_profitable': self.is_profitable,
        }

    def __str__(self) -> str:
        """String representation of position."""
        side = "LONG" if self.is_long else "SHORT"
        return f"Position({self.symbol}, {side}, {abs(self.quantity)} @ {self.avg_entry_price})"


class PositionManager:
    """Manages portfolio positions."""

    def __init__(self):
        """Initialize position manager."""
        self.settings = get_settings()
        self.logger = get_logger("trading.position_manager")

        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.portfolio_value = 0.0
        self.base_currency = "USDT"  # Default base currency

    def add_position(self, position: Position) -> None:
        """Add a position to the portfolio.

        Args:
            position: Position to add
        """
        if position.symbol in self.positions:
            self.logger.warning(f"Updating existing position for {position.symbol}")
            self._merge_positions(self.positions[position.symbol], position)
        else:
            self.positions[position.symbol] = position
            self.logger.info(f"Added new position: {position}")

        self._update_portfolio_value()

    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a position from the portfolio.

        Args:
            symbol: Symbol to remove

        Returns:
            Removed position or None if not found
        """
        position = self.positions.pop(symbol, None)

        if position:
            # Move to closed positions
            position.closed_at = time.time()
            self.closed_positions.append(position)
            self.logger.info(f"Removed position: {symbol}")
            self._update_portfolio_value()

        return position

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position or None if not found
        """
        return self.positions.get(symbol)

    def get_positions_by_strategy(self, strategy: str) -> List[Position]:
        """Get all positions for a specific strategy.

        Args:
            strategy: Strategy name

        Returns:
            List of positions for the strategy
        """
        return [pos for pos in self.positions.values() if pos.strategy == strategy]

    def get_long_positions(self) -> List[Position]:
        """Get all long positions.

        Returns:
            List of long positions
        """
        return [pos for pos in self.positions.values() if pos.is_long]

    def get_short_positions(self) -> List[Position]:
        """Get all short positions.

        Returns:
            List of short positions
        """
        return [pos for pos in self.positions.values() if pos.is_short]

    def get_profitable_positions(self) -> List[Position]:
        """Get all profitable positions.

        Returns:
            List of profitable positions
        """
        return [pos for pos in self.positions.values() if pos.is_profitable]

    def get_unprofitable_positions(self) -> List[Position]:
        """Get all unprofitable positions.

        Returns:
            List of unprofitable positions
        """
        return [pos for pos in self.positions.values() if not pos.is_profitable]

    def update_position_prices(self, price_data: Dict[str, float]) -> None:
        """Update position prices and P&L.

        Args:
            price_data: Dictionary of symbol -> current price
        """
        for symbol, current_price in price_data.items():
            position = self.positions.get(symbol)
            if position:
                position.update_unrealized_pnl(current_price)

        self._update_portfolio_value()

    def calculate_portfolio_risk(self) -> Dict[str, float]:
        """Calculate portfolio risk metrics.

        Returns:
            Dictionary of risk metrics
        """
        if not self.positions:
            return {
                'total_risk': 0.0,
                'max_position_risk': 0.0,
                'concentration_risk': 0.0,
                'correlation_risk': 0.0,
            }

        total_value = self.portfolio_value
        if total_value == 0:
            return {'total_risk': 0.0, 'max_position_risk': 0.0, 'concentration_risk': 0.0, 'correlation_risk': 0.0}

        # Calculate individual position risks
        position_risks = []
        for position in self.positions.values():
            risk_percentage = (position.risk_amount / total_value) * 100
            position_risks.append(risk_percentage)

        # Total risk (sum of individual risks)
        total_risk = sum(position_risks)

        # Maximum position risk (largest single position risk)
        max_position_risk = max(position_risks) if position_risks else 0.0

        # Concentration risk (Herfindahl-Hirschman Index)
        concentration_risk = sum((risk / total_risk) ** 2 for risk in position_risks) * 100 if total_risk > 0 else 0.0

        # Simple correlation risk (placeholder - would need correlation matrix)
        correlation_risk = min(total_risk * 0.5, 50.0)  # Simplified calculation

        return {
            'total_risk': total_risk,
            'max_position_risk': max_position_risk,
            'concentration_risk': concentration_risk,
            'correlation_risk': correlation_risk,
        }

    def check_position_limits(self) -> Dict[str, bool]:
        """Check if positions are within configured limits.

        Returns:
            Dictionary of limit checks
        """
        settings = get_settings()

        current_positions = len(self.positions)
        max_positions = settings.trading.max_positions

        # Position count limit
        position_count_ok = current_positions < max_positions

        # Risk limit checks
        risk_metrics = self.calculate_portfolio_risk()
        max_portfolio_risk = settings.risk.max_portfolio_risk * 100  # Convert to percentage

        portfolio_risk_ok = risk_metrics['total_risk'] <= max_portfolio_risk

        # Symbol concentration check
        symbols = list(self.positions.keys())
        max_positions_per_symbol = settings.risk.max_positions_per_symbol

        symbol_concentration_ok = True
        for symbol in symbols:
            symbol_positions = [pos for pos in self.positions.values() if pos.symbol == symbol]
            if len(symbol_positions) > max_positions_per_symbol:
                symbol_concentration_ok = False
                break

        return {
            'position_count_ok': position_count_ok,
            'portfolio_risk_ok': portfolio_risk_ok,
            'symbol_concentration_ok': symbol_concentration_ok,
            'max_positions': max_positions,
            'current_positions': current_positions,
            'portfolio_risk': risk_metrics['total_risk'],
            'max_portfolio_risk': max_portfolio_risk,
        }

    def get_positions_summary(self) -> Dict:
        """Get summary of all positions.

        Returns:
            Dictionary with position summary
        """
        if not self.positions:
            return {
                'total_positions': 0,
                'long_positions': 0,
                'short_positions': 0,
                'total_value': 0.0,
                'total_unrealized_pnl': 0.0,
                'total_realized_pnl': 0.0,
                'winning_positions': 0,
                'losing_positions': 0,
            }

        long_positions = self.get_long_positions()
        short_positions = self.get_short_positions()
        profitable_positions = self.get_profitable_positions()
        unprofitable_positions = self.get_unprofitable_positions()

        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())

        return {
            'total_positions': len(self.positions),
            'long_positions': len(long_positions),
            'short_positions': len(short_positions),
            'total_value': self.portfolio_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'winning_positions': len(profitable_positions),
            'losing_positions': len(unprofitable_positions),
            'win_rate': (len(profitable_positions) / len(self.positions)) * 100 if self.positions else 0.0,
            'total_pnl': total_unrealized_pnl + total_realized_pnl,
        }

    def export_positions(self) -> List[Dict]:
        """Export all positions to list of dictionaries.

        Returns:
            List of position dictionaries
        """
        positions_data = []

        for position in self.positions.values():
            position_dict = position.to_dict()
            positions_data.append(position_dict)

        return positions_data

    def import_positions(self, positions_data: List[Dict]) -> None:
        """Import positions from list of dictionaries.

        Args:
            positions_data: List of position dictionaries
        """
        for pos_data in positions_data:
            try:
                position = Position(
                    symbol=pos_data['symbol'],
                    quantity=pos_data['quantity'],
                    avg_entry_price=pos_data['avg_entry_price'],
                    strategy=pos_data.get('strategy'),
                    unrealized_pnl=pos_data.get('unrealized_pnl', 0.0),
                    realized_pnl=pos_data.get('realized_pnl', 0.0),
                    stop_loss=pos_data.get('stop_loss'),
                    take_profit=pos_data.get('take_profit'),
                    opened_at=pos_data.get('opened_at'),
                    tags=pos_data.get('tags', {}),
                )
                self.positions[position.symbol] = position

            except Exception as e:
                self.logger.error(f"Error importing position {pos_data.get('symbol', 'unknown')}: {str(e)}")

        self._update_portfolio_value()
        self.logger.info(f"Imported {len(positions_data)} positions")

    def _merge_positions(self, existing: Position, new: Position) -> None:
        """Merge two positions for the same symbol.

        Args:
            existing: Existing position
            new: New position data
        """
        if existing.symbol != new.symbol:
            raise ValueError("Cannot merge positions for different symbols")

        # Calculate weighted average price
        total_quantity = existing.quantity + new.quantity
        if total_quantity == 0:
            # Position fully closed
            existing.quantity = 0
            existing.avg_entry_price = 0
        else:
            total_cost = (existing.avg_entry_price * existing.quantity) + (new.avg_entry_price * new.quantity)
            existing.avg_entry_price = total_cost / total_quantity
            existing.quantity = total_quantity

        # Merge other attributes
        if new.strategy and not existing.strategy:
            existing.strategy = new.strategy

        if new.stop_loss:
            existing.stop_loss = new.stop_loss

        if new.take_profit:
            existing.take_profit = new.take_profit

        # Merge tags
        existing.tags.update(new.tags)

    def _update_portfolio_value(self) -> None:
        """Update total portfolio value."""
        self.portfolio_value = sum(pos.market_value for pos in self.positions.values())

    def clear_positions(self) -> None:
        """Clear all positions."""
        # Move all positions to closed positions
        for position in self.positions.values():
            position.closed_at = time.time()

        self.closed_positions.extend(self.positions.values())
        self.positions.clear()
        self.portfolio_value = 0.0

        self.logger.info(f"Cleared {len(self.closed_positions)} positions")

    def get_largest_positions(self, limit: int = 5) -> List[Position]:
        """Get positions with largest market value.

        Args:
            limit: Maximum number of positions to return

        Returns:
            List of positions sorted by market value
        """
        sorted_positions = sorted(
            self.positions.values(),
            key=lambda pos: pos.market_value,
            reverse=True
        )
        return sorted_positions[:limit]

    def get_most_profitable_positions(self, limit: int = 5) -> List[Position]:
        """Get most profitable positions.

        Args:
            limit: Maximum number of positions to return

        Returns:
            List of positions sorted by total P&L
        """
        sorted_positions = sorted(
            self.positions.values(),
            key=lambda pos: pos.total_pnl,
            reverse=True
        )
        return sorted_positions[:limit]

    def get_worst_performing_positions(self, limit: int = 5) -> List[Position]:
        """Get worst performing positions.

        Args:
            limit: Maximum number of positions to return

        Returns:
            List of positions sorted by total P&L (ascending)
        """
        sorted_positions = sorted(
            self.positions.values(),
            key=lambda pos: pos.total_pnl
        )
        return sorted_positions[:limit]

    def calculate_drawdown(self) -> Dict[str, float]:
        """Calculate portfolio drawdown metrics.

        Returns:
            Dictionary of drawdown metrics
        """
        if not self.closed_positions:
            return {
                'current_drawdown': 0.0,
                'max_drawdown': 0.0,
                'peak_value': self.portfolio_value,
                'lowest_value': self.portfolio_value,
            }

        # Calculate running portfolio values
        values = []
        current_value = 0.0

        # Add current positions
        for position in self.positions.values():
            current_value += position.market_value
        values.append(current_value)

        # Add closed positions (in reverse chronological order)
        for position in reversed(self.closed_positions):
            if position.closed_at:
                current_value += position.market_value
                values.append(current_value)

        if not values:
            return {'current_drawdown': 0.0, 'max_drawdown': 0.0, 'peak_value': 0.0, 'lowest_value': 0.0}

        # Calculate drawdown
        peak = values[0]
        max_drawdown = 0.0
        current_drawdown = 0.0
        lowest_value = values[0]

        for value in values:
            if value > peak:
                peak = value
            else:
                drawdown = ((peak - value) / peak) * 100
                max_drawdown = max(max_drawdown, drawdown)
                current_drawdown = drawdown

            lowest_value = min(lowest_value, value)

        return {
            'current_drawdown': current_drawdown,
            'max_drawdown': max_drawdown,
            'peak_value': peak,
            'lowest_value': lowest_value,
        }

    def get_rebalance_suggestions(self) -> Dict[str, List[str]]:
        """Get suggestions for portfolio rebalancing.

        Returns:
            Dictionary of rebalancing suggestions
        """
        suggestions = {
            'close_positions': [],
            'reduce_positions': [],
            'increase_positions': [],
        }

        # Check risk limits
        limit_checks = self.check_position_limits()

        if not limit_checks['portfolio_risk_ok']:
            # Suggest reducing high-risk positions
            risk_metrics = self.calculate_portfolio_risk()
            if risk_metrics['total_risk'] > limit_checks['max_portfolio_risk']:
                # Find positions contributing most to risk
                risky_positions = sorted(
                    self.positions.values(),
                    key=lambda pos: pos.risk_amount,
                    reverse=True
                )
                suggestions['reduce_positions'] = [pos.symbol for pos in risky_positions[:3]]

        # Check position count
        if not limit_checks['position_count_ok']:
            # Suggest closing least profitable positions
            unprofitable = self.get_unprofitable_positions()
            if unprofitable:
                suggestions['close_positions'] = [pos.symbol for pos in unprofitable[:2]]

        # Check for concentration
        if not limit_checks['symbol_concentration_ok']:
            # Find over-concentrated symbols
            symbol_counts = {}
            for position in self.positions.values():
                symbol_counts[position.symbol] = symbol_counts.get(position.symbol, 0) + 1

            over_concentrated = [symbol for symbol, count in symbol_counts.items() if count > 2]
            suggestions['reduce_positions'].extend(over_concentrated)

        return suggestions

    def get_daily_pnl(self) -> float:
        """Calculate daily P&L.

        Returns:
            Daily P&L amount
        """
        # This is a simplified calculation
        # In a real implementation, you'd track daily changes
        total_pnl = sum(pos.total_pnl for pos in self.positions.values())

        # Assume this represents today's P&L for now
        return total_pnl

    def get_monthly_pnl(self) -> float:
        """Calculate monthly P&L.

        Returns:
            Monthly P&L amount
        """
        # This is a simplified calculation
        # In a real implementation, you'd aggregate daily P&L
        total_pnl = sum(pos.total_pnl for pos in self.positions.values())

        # Assume this represents this month's P&L for now
        return total_pnl

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get position by symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position or None if not found
        """
        return self.positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            True if position exists
        """
        return symbol in self.positions

    def get_total_exposure(self, symbol: Optional[str] = None) -> float:
        """Get total exposure for symbol or entire portfolio.

        Args:
            symbol: Trading symbol (optional)

        Returns:
            Total exposure amount
        """
        if symbol:
            position = self.positions.get(symbol)
            return position.market_value if position else 0.0
        else:
            return self.portfolio_value

    def get_net_exposure(self) -> Dict[str, float]:
        """Calculate net exposure by asset class.

        Returns:
            Dictionary of asset class exposures
        """
        # This is a simplified implementation
        # In reality, you'd categorize assets by type
        exposures = {
            'crypto': self.portfolio_value,
            'fiat': 0.0,  # Would track fiat balances
        }

        return exposures

    def __len__(self) -> int:
        """Return number of positions."""
        return len(self.positions)

    def __contains__(self, symbol: str) -> bool:
        """Check if symbol has a position."""
        return symbol in self.positions

    def __iter__(self):
        """Iterate over positions."""
        return iter(self.positions.values())