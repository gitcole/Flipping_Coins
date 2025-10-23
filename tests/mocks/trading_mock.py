"""
Mock implementations for trading components.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import AsyncMock, Mock
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class MockOrder:
    """Mock order representation."""
    id: str
    symbol: str
    quantity: float
    side: str
    type: str
    price: Optional[float]
    status: str
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0


@dataclass
class MockPosition:
    """Mock position representation."""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    side: str


class TradingEngineMock:
    """Mock trading engine for testing."""

    def __init__(self):
        self.running = False
        self.orders = {}
        self.positions = {}
        self.order_history = []
        self.execution_delay = 0.1
        self.fill_rate = 1.0  # 0.0-1.0

        # Callbacks
        self.order_callbacks = {}
        self.trade_callbacks = {}

        # Statistics
        self.orders_placed = 0
        self.orders_filled = 0
        self.trades_executed = 0

    async def start(self) -> bool:
        """Mock start engine."""
        await self._simulate_delay(0.1)
        self.running = True
        return True

    async def stop(self) -> bool:
        """Mock stop engine."""
        await self._simulate_delay(0.05)
        self.running = False
        return True

    async def place_order(self, symbol: str, quantity: float, side: str,
                         order_type: str = "market", price: Optional[float] = None,
                         stop_price: Optional[float] = None) -> Dict[str, Any]:
        """Mock place order."""
        await self._simulate_delay(self.execution_delay)

        if not self.running:
            raise Exception("Trading engine not running")

        order_id = f"mock_order_{int(time.time() * 1000)}"

        order = MockOrder(
            id=order_id,
            symbol=symbol,
            quantity=quantity,
            side=side,
            type=order_type,
            price=price,
            status="pending",
            created_at=datetime.now()
        )
        order.remaining_quantity = quantity

        self.orders[order_id] = order
        self.orders_placed += 1

        # Simulate order processing
        asyncio.create_task(self._process_order(order))

        # Trigger callbacks
        if "order_placed" in self.order_callbacks:
            for callback in self.order_callbacks["order_placed"]:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(order))
                else:
                    callback(order)

        return {
            "id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "status": "pending"
        }

    async def cancel_order(self, order_id: str) -> bool:
        """Mock cancel order."""
        await self._simulate_delay(0.05)

        if order_id not in self.orders:
            return False

        order = self.orders[order_id]
        if order.status in ["filled", "cancelled"]:
            return False

        order.status = "cancelled"

        # Trigger callbacks
        if "order_cancelled" in self.order_callbacks:
            for callback in self.order_callbacks["order_cancelled"]:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(order))
                else:
                    callback(order)

        return True

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Mock get order."""
        await self._simulate_delay(0.02)

        if order_id not in self.orders:
            return None

        order = self.orders[order_id]
        return {
            "id": order.id,
            "symbol": order.symbol,
            "quantity": order.quantity,
            "side": order.side,
            "type": order.type,
            "price": order.price,
            "status": order.status,
            "filled_quantity": order.filled_quantity,
            "remaining_quantity": order.remaining_quantity,
            "created_at": order.created_at.isoformat()
        }

    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock get orders."""
        await self._simulate_delay(0.03)

        orders = []
        for order in self.orders.values():
            if status is None or order.status == status:
                orders.append({
                    "id": order.id,
                    "symbol": order.symbol,
                    "quantity": order.quantity,
                    "side": order.side,
                    "type": order.type,
                    "price": order.price,
                    "status": order.status,
                    "created_at": order.created_at.isoformat()
                })

        return orders

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Mock get positions."""
        await self._simulate_delay(0.02)

        positions = []
        for position in self.positions.values():
            positions.append({
                "symbol": position.symbol,
                "quantity": position.quantity,
                "avg_price": position.avg_price,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "realized_pnl": position.realized_pnl,
                "side": position.side
            })

        return positions

    async def close_position(self, symbol: str) -> bool:
        """Mock close position."""
        await self._simulate_delay(0.1)

        if symbol not in self.positions:
            return False

        position = self.positions[symbol]

        # Place opposite order to close position
        await self.place_order(
            symbol=symbol,
            quantity=position.quantity,
            side="sell" if position.side == "long" else "buy",
            order_type="market"
        )

        # Remove position
        del self.positions[symbol]

        return True

    # Callback management
    def add_order_callback(self, event: str, callback: Callable):
        """Add order event callback."""
        if event not in self.order_callbacks:
            self.order_callbacks[event] = []

        self.order_callbacks[event].append(callback)

    def add_trade_callback(self, callback: Callable):
        """Add trade execution callback."""
        self.trade_callbacks.append(callback)

    # Order processing simulation
    async def _process_order(self, order: MockOrder):
        """Simulate order processing."""
        await self._simulate_delay(self.execution_delay)

        if order.status == "cancelled":
            return

        # Simulate partial or full fill based on fill_rate
        fill_quantity = order.quantity * self.fill_rate
        order.filled_quantity = fill_quantity
        order.remaining_quantity = order.quantity - fill_quantity
        order.status = "filled" if order.remaining_quantity == 0 else "partially_filled"
        order.filled_at = datetime.now()

        self.orders_filled += 1

        # Create trade record
        trade = {
            "id": f"trade_{order.id}",
            "order_id": order.id,
            "symbol": order.symbol,
            "quantity": fill_quantity,
            "price": order.price or 50000.00,  # Default price if not specified
            "side": order.side,
            "timestamp": order.filled_at.isoformat()
        }

        # Update position if this is a filled order
        if order.status == "filled":
            await self._update_position(order, trade)

        # Trigger callbacks
        if "order_filled" in self.order_callbacks:
            for callback in self.order_callbacks["order_filled"]:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(order, trade))
                else:
                    callback(order, trade)

        if self.trade_callbacks:
            for callback in self.trade_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(trade))
                else:
                    callback(trade)

    async def _update_position(self, order: MockOrder, trade: Dict[str, Any]):
        """Update position based on filled order."""
        symbol = order.symbol
        quantity = trade["quantity"]
        price = trade["price"]

        if symbol not in self.positions:
            self.positions[symbol] = MockPosition(
                symbol=symbol,
                quantity=0.0,
                avg_price=0.0,
                current_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                side=order.side
            )

        position = self.positions[symbol]

        if order.side == "buy":
            # Update average price for long position
            total_quantity = position.quantity + quantity
            position.avg_price = ((position.avg_price * position.quantity) +
                                (price * quantity)) / total_quantity
            position.quantity = total_quantity
        else:
            # Close position for sell order
            if position.quantity >= quantity:
                # Calculate realized PnL
                pnl = (price - position.avg_price) * quantity
                position.realized_pnl += pnl
                position.unrealized_pnl = 0.0

                if position.quantity == quantity:
                    del self.positions[symbol]
                else:
                    position.quantity -= quantity

    # Configuration methods
    def set_execution_delay(self, delay: float):
        """Set execution delay."""
        self.execution_delay = delay

    def set_fill_rate(self, rate: float):
        """Set order fill rate (0.0-1.0)."""
        self.fill_rate = max(0.0, min(1.0, rate))

    def reset_stats(self):
        """Reset engine statistics."""
        self.orders_placed = 0
        self.orders_filled = 0
        self.trades_executed = 0
        self.orders.clear()
        self.positions.clear()
        self.order_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "running": self.running,
            "orders_placed": self.orders_placed,
            "orders_filled": self.orders_filled,
            "trades_executed": self.trades_executed,
            "active_orders": len([o for o in self.orders.values() if o.status in ["pending", "partially_filled"]]),
            "positions": len(self.positions)
        }

    async def _simulate_delay(self, seconds: float):
        """Simulate delay."""
        if seconds > 0:
            await asyncio.sleep(seconds)


class RiskManagerMock:
    """Mock risk manager for testing."""

    def __init__(self):
        self.risk_checks_enabled = True
        self.max_position_size = 1000.0
        self.max_positions = 5
        self.risk_tolerance = 0.02
        self.stop_loss_percentage = 0.05
        self.take_profit_percentage = 0.10

        # Risk tracking
        self.risk_violations = []
        self.approved_orders = 0
        self.rejected_orders = 0

    async def validate_order(self, symbol: str, quantity: float, side: str,
                           price: Optional[float] = None) -> Dict[str, Any]:
        """Mock validate order against risk rules."""
        await self._simulate_delay(0.02)

        if not self.risk_checks_enabled:
            return {"approved": True, "reason": "Risk checks disabled"}

        violations = []

        # Check position size limit
        estimated_value = quantity * (price or 50000.00)
        if estimated_value > self.max_position_size:
            violations.append(f"Order value ${estimated_value:.2f} exceeds max position size ${self.max_position_size}")

        # Check max positions (simplified check)
        if len(self.risk_violations) > self.max_positions:
            violations.append(f"Too many risk violations ({len(self.risk_violations)})")

        # Check risk tolerance (simplified)
        if estimated_value > 10000 * self.risk_tolerance:
            violations.append(f"Order exceeds risk tolerance (${10000 * self.risk_tolerance:.2f})")

        if violations:
            self.risk_violations.extend(violations)
            self.rejected_orders += 1
            return {
                "approved": False,
                "reason": "; ".join(violations)
            }

        self.approved_orders += 1
        return {
            "approved": True,
            "reason": "Order approved",
            "stop_loss": price * (1 - self.stop_loss_percentage) if price else None,
            "take_profit": price * (1 + self.take_profit_percentage) if price else None
        }

    async def check_position_limits(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock check position limits."""
        await self._simulate_delay(0.01)

        violations = []
        total_exposure = 0.0

        for position in positions:
            position_value = position["quantity"] * position["current_price"]
            total_exposure += position_value

            if position_value > self.max_position_size:
                violations.append(f"Position {position['symbol']} value ${position_value:.2f} exceeds limit")

        if total_exposure > self.max_positions * self.max_position_size:
            violations.append(f"Total exposure ${total_exposure:.2f} exceeds limits")

        return {
            "within_limits": len(violations) == 0,
            "violations": violations,
            "total_exposure": total_exposure,
            "max_exposure": self.max_positions * self.max_position_size
        }

    async def calculate_position_risk(self, symbol: str, quantity: float,
                                    current_price: float) -> float:
        """Mock calculate position risk."""
        await self._simulate_delay(0.01)

        position_value = quantity * current_price
        risk_score = min(position_value / 10000.0, 1.0)  # Normalize to 0-1

        return risk_score * self.risk_tolerance

    async def get_risk_summary(self) -> Dict[str, Any]:
        """Mock get risk summary."""
        await self._simulate_delay(0.02)

        return {
            "risk_checks_enabled": self.risk_checks_enabled,
            "max_position_size": self.max_position_size,
            "max_positions": self.max_positions,
            "risk_tolerance": self.risk_tolerance,
            "approved_orders": self.approved_orders,
            "rejected_orders": self.rejected_orders,
            "active_violations": len(self.risk_violations)
        }

    # Configuration methods
    def set_risk_checks_enabled(self, enabled: bool):
        """Enable/disable risk checks."""
        self.risk_checks_enabled = enabled

    def set_max_position_size(self, size: float):
        """Set max position size."""
        self.max_position_size = size

    def set_risk_tolerance(self, tolerance: float):
        """Set risk tolerance."""
        self.risk_tolerance = tolerance

    def clear_violations(self):
        """Clear risk violations."""
        self.risk_violations.clear()

    def reset_stats(self):
        """Reset risk manager statistics."""
        self.approved_orders = 0
        self.rejected_orders = 0
        self.risk_violations.clear()

    async def _simulate_delay(self, seconds: float):
        """Simulate delay."""
        if seconds > 0:
            await asyncio.sleep(seconds)


class TradingMockBuilder:
    """Builder for creating customized trading mocks."""

    def __init__(self):
        self.config = {
            "execution_delay": 0.1,
            "fill_rate": 1.0,
            "risk_checks_enabled": True,
            "max_position_size": 1000.0,
            "initial_positions": []
        }

    def with_execution_delay(self, delay: float) -> 'TradingMockBuilder':
        """Configure execution delay."""
        self.config["execution_delay"] = delay
        return self

    def with_fill_rate(self, rate: float) -> 'TradingMockBuilder':
        """Configure fill rate."""
        self.config["fill_rate"] = rate
        return self

    def with_risk_checks(self, enabled: bool) -> 'TradingMockBuilder':
        """Configure risk checks."""
        self.config["risk_checks_enabled"] = enabled
        return self

    def with_max_position_size(self, size: float) -> 'TradingMockBuilder':
        """Configure max position size."""
        self.config["max_position_size"] = size
        return self

    def with_initial_positions(self, positions: List[Dict[str, Any]]) -> 'TradingMockBuilder':
        """Configure initial positions."""
        self.config["initial_positions"] = positions
        return self

    def build_engine(self) -> TradingEngineMock:
        """Build configured trading engine mock."""
        engine = TradingEngineMock()

        engine.set_execution_delay(self.config["execution_delay"])
        engine.set_fill_rate(self.config["fill_rate"])

        # Add initial positions
        for position_data in self.config["initial_positions"]:
            position = MockPosition(**position_data)
            engine.positions[position.symbol] = position

        return engine

    def build_risk_manager(self) -> RiskManagerMock:
        """Build configured risk manager mock."""
        risk_manager = RiskManagerMock()

        risk_manager.set_risk_checks_enabled(self.config["risk_checks_enabled"])
        risk_manager.set_max_position_size(self.config["max_position_size"])

        return risk_manager


# Convenience functions
def create_fast_trading_engine() -> TradingEngineMock:
    """Create trading engine with fast execution."""
    return (TradingMockBuilder()
            .with_execution_delay(0.01)
            .with_fill_rate(1.0)
            .build_engine())


def create_slow_trading_engine() -> TradingEngineMock:
    """Create trading engine with slow execution."""
    return (TradingMockBuilder()
            .with_execution_delay(0.5)
            .with_fill_rate(0.8)
            .build_engine())


def create_strict_risk_manager() -> RiskManagerMock:
    """Create risk manager with strict limits."""
    return (TradingMockBuilder()
            .with_risk_checks(True)
            .with_max_position_size(100.0)
            .build_risk_manager())