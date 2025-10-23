"""
Test data factories for creating realistic test data.
"""
import random
import time
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from decimal import Decimal
import json


@dataclass
class MarketDataConfig:
    """Configuration for market data generation."""
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "ADA", "DOT", "LINK"])
    base_prices: Dict[str, float] = field(default_factory=lambda: {
        "BTC": 50000.0,
        "ETH": 3000.0,
        "ADA": 1.5,
        "DOT": 25.0,
        "LINK": 20.0
    })
    volatility: float = 0.02  # Daily volatility
    spread_percentage: float = 0.001  # Bid-ask spread
    volume_multiplier: float = 1000000.0


@dataclass
class PositionConfig:
    """Configuration for position data generation."""
    min_quantity: float = 0.001
    max_quantity: float = 10.0
    min_price: float = 1.0
    max_price: float = 100000.0
    sides: List[str] = field(default_factory=lambda: ["long", "short"])


@dataclass
class OrderConfig:
    """Configuration for order data generation."""
    order_types: List[str] = field(default_factory=lambda: ["market", "limit", "stop", "stop_limit"])
    time_in_force: List[str] = field(default_factory=lambda: ["gtc", "ioc", "fok"])
    status_options: List[str] = field(default_factory=lambda: ["pending", "open", "filled", "cancelled", "rejected"])


class MarketDataFactory:
    """Factory for generating market data."""

    def __init__(self, config: Optional[MarketDataConfig] = None):
        self.config = config or MarketDataConfig()
        self.price_history = {}
        self._initialize_price_history()

    def _initialize_price_history(self):
        """Initialize price history with base prices."""
        for symbol in self.config.symbols:
            base_price = self.config.base_prices.get(symbol, 100.0)
            self.price_history[symbol] = [base_price]

    def generate_quote(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate a quote for a symbol."""
        if symbol not in self.config.symbols:
            raise ValueError(f"Symbol {symbol} not in configured symbols")

        current_price = self._get_current_price(symbol)
        spread = current_price * self.config.spread_percentage

        quote = {
            "symbol": symbol,
            "ask_price": round(current_price + spread, 8),
            "bid_price": round(current_price - spread, 8),
            "last_trade_price": round(current_price, 8),
            "volume": round(random.uniform(1000, self.config.volume_multiplier), 2),
            "timestamp": timestamp or datetime.now(),
            "source": "mock"
        }

        # Update price history
        self.price_history[symbol].append(current_price)

        return quote

    def generate_quotes(self, symbols: Optional[List[str]] = None,
                       timestamp: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        """Generate quotes for multiple symbols."""
        symbols = symbols or self.config.symbols
        return {symbol: self.generate_quote(symbol, timestamp) for symbol in symbols}

    def generate_market_data(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive market data."""
        quote = self.generate_quote(symbol, timestamp)
        current_price = quote["last_trade_price"]

        # Generate OHLCV data
        price_history = self.price_history.get(symbol, [current_price])
        if len(price_history) >= 24:
            high_24h = max(price_history[-24:])
            low_24h = min(price_history[-24:])
            open_24h = price_history[-24]
        else:
            high_24h = max(price_history)
            low_24h = min(price_history)
            open_24h = price_history[0] if price_history else current_price

        change_24h = ((current_price - open_24h) / open_24h) * 100 if open_24h > 0 else 0

        market_data = {
            **quote,
            "open_24h": round(open_24h, 8),
            "high_24h": round(high_24h, 8),
            "low_24h": round(low_24h, 8),
            "change_24h": round(change_24h, 4),
            "volume_24h": round(quote["volume"] * random.uniform(0.8, 1.2), 2),
            "market_cap": round(current_price * random.uniform(1000000, 1000000000), 2),
            "circulating_supply": random.uniform(1000000, 100000000)
        }

        return market_data

    def generate_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Generate orderbook data."""
        quote = self.generate_quote(symbol)
        current_price = quote["last_trade_price"]
        spread = current_price * self.config.spread_percentage

        bids = []
        asks = []

        # Generate bids (below current price)
        for i in range(depth):
            price = current_price - spread - (i * spread * 0.1)
            quantity = random.uniform(0.1, 5.0)
            bids.append({"price": round(price, 8), "quantity": round(quantity, 8)})

        # Generate asks (above current price)
        for i in range(depth):
            price = current_price + spread + (i * spread * 0.1)
            quantity = random.uniform(0.1, 5.0)
            asks.append({"price": round(price, 8), "quantity": round(quantity, 8)})

        return {
            "symbol": symbol,
            "timestamp": quote["timestamp"],
            "bids": bids,
            "asks": asks
        }

    def generate_trade(self, symbol: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate a trade record."""
        quote = self.generate_quote(symbol, timestamp)
        side = random.choice(["buy", "sell"])
        quantity = random.uniform(0.001, 1.0)

        return {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "price": quote["last_trade_price"],
            "quantity": round(quantity, 8),
            "side": side,
            "timestamp": quote["timestamp"],
            "taker_side": side
        }

    def generate_historical_prices(self, symbol: str, days: int = 30,
                                  interval_minutes: int = 60) -> List[Dict[str, Any]]:
        """Generate historical price data."""
        prices = []
        base_time = datetime.now() - timedelta(days=days)

        for i in range(0, days * 24 * 60 // interval_minutes):
            timestamp = base_time + timedelta(minutes=i * interval_minutes)
            quote = self.generate_quote(symbol, timestamp)

            prices.append({
                "timestamp": timestamp,
                "open": quote["last_trade_price"],
                "high": round(quote["last_trade_price"] * (1 + random.uniform(0, 0.02)), 8),
                "low": round(quote["last_trade_price"] * (1 - random.uniform(0, 0.02)), 8),
                "close": quote["last_trade_price"],
                "volume": quote["volume"]
            })

        return prices

    def _get_current_price(self, symbol: str) -> float:
        """Get current price with some random walk."""
        if symbol not in self.price_history:
            return self.config.base_prices.get(symbol, 100.0)

        last_price = self.price_history[symbol][-1]
        # Random walk with drift
        drift = 0.0001  # Small upward drift
        shock = random.gauss(0, self.config.volatility)
        new_price = last_price * (1 + drift + shock)

        return max(new_price, 0.01)  # Ensure price doesn't go negative

    def reset(self):
        """Reset price history."""
        self._initialize_price_history()


class PositionFactory:
    """Factory for generating position data."""

    def __init__(self, config: Optional[PositionConfig] = None):
        self.config = config or PositionConfig()

    def generate_position(self, symbol: str = None, side: str = None,
                         quantity: float = None, avg_price: float = None) -> Dict[str, Any]:
        """Generate a position."""
        symbol = symbol or random.choice(["BTC", "ETH", "ADA", "DOT", "LINK"])
        side = side or random.choice(self.config.sides)
        quantity = quantity or round(random.uniform(self.config.min_quantity, self.config.max_quantity), 8)
        avg_price = avg_price or round(random.uniform(self.config.min_price, self.config.max_price), 2)

        # Generate current price (simulated)
        current_price = avg_price * (1 + random.uniform(-0.1, 0.1))

        unrealized_pnl = (current_price - avg_price) * quantity
        realized_pnl = round(random.uniform(-100, 100), 2)

        return {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "quantity": quantity,
            "avg_price": round(avg_price, 2),
            "current_price": round(current_price, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "side": side,
            "opened_at": datetime.now() - timedelta(days=random.randint(1, 30)),
            "updated_at": datetime.now()
        }

    def generate_positions(self, count: int, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate multiple positions."""
        symbols = symbols or ["BTC", "ETH", "ADA", "DOT", "LINK"]
        positions = []

        for _ in range(count):
            symbol = random.choice(symbols)
            position = self.generate_position(symbol=symbol)
            positions.append(position)

        return positions

    def generate_portfolio_summary(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate portfolio summary from positions."""
        total_value = sum(pos["quantity"] * pos["current_price"] for pos in positions)
        total_unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions)
        total_realized_pnl = sum(pos["realized_pnl"] for pos in positions)

        return {
            "total_positions": len(positions),
            "total_value": round(total_value, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "positions": positions
        }


class OrderFactory:
    """Factory for generating order data."""

    def __init__(self, config: Optional[OrderConfig] = None):
        self.config = config or OrderConfig()

    def generate_order(self, symbol: str = None, side: str = None,
                      order_type: str = None, quantity: float = None,
                      price: float = None) -> Dict[str, Any]:
        """Generate an order."""
        symbol = symbol or random.choice(["BTC", "ETH", "ADA", "DOT", "LINK"])
        side = side or random.choice(["buy", "sell"])
        order_type = order_type or random.choice(self.config.order_types)
        quantity = quantity or round(random.uniform(0.001, 1.0), 8)

        # Generate price based on order type
        if order_type == "market":
            price = None
            stop_price = None
        elif order_type == "limit":
            base_price = random.uniform(40000, 60000) if "BTC" in symbol else random.uniform(2000, 4000)
            price = round(base_price * (1 + random.uniform(-0.05, 0.05)), 2)
            stop_price = None
        elif order_type == "stop":
            base_price = random.uniform(40000, 60000) if "BTC" in symbol else random.uniform(2000, 4000)
            price = None
            stop_price = round(base_price * (1 + random.uniform(-0.05, 0.05)), 2)
        else:  # stop_limit
            base_price = random.uniform(40000, 60000) if "BTC" in symbol else random.uniform(2000, 4000)
            price = round(base_price * (1 + random.uniform(-0.05, 0.05)), 2)
            stop_price = round(base_price * (1 + random.uniform(-0.05, 0.05)), 2)

        status = random.choice(self.config.status_options)
        time_in_force = random.choice(self.config.time_in_force)

        return {
            "id": str(uuid.uuid4()),
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "type": order_type,
            "price": price,
            "stop_price": stop_price,
            "status": status,
            "time_in_force": time_in_force,
            "created_at": datetime.now() - timedelta(minutes=random.randint(1, 1440)),
            "updated_at": datetime.now(),
            "filled_quantity": quantity if status == "filled" else 0.0,
            "remaining_quantity": 0.0 if status == "filled" else quantity
        }

    def generate_orders(self, count: int) -> List[Dict[str, Any]]:
        """Generate multiple orders."""
        orders = []
        for _ in range(count):
            order = self.generate_order()
            orders.append(order)
        return orders


class StrategyFactory:
    """Factory for generating strategy configurations."""

    def generate_strategy_config(self, name: str = None) -> Dict[str, Any]:
        """Generate a strategy configuration."""
        name = name or f"strategy_{random.randint(1000, 9999)}"

        strategies = ["mean_reversion", "momentum", "breakout", "arbitrage", "grid"]
        strategy_type = random.choice(strategies)

        base_config = {
            "name": name,
            "type": strategy_type,
            "enabled": random.choice([True, False]),
            "symbols": random.sample(["BTC", "ETH", "ADA", "DOT", "LINK"], random.randint(1, 3))
        }

        # Add strategy-specific parameters
        if strategy_type == "mean_reversion":
            base_config["parameters"] = {
                "lookback_period": random.randint(10, 50),
                "entry_threshold": round(random.uniform(1.5, 3.0), 2),
                "exit_threshold": round(random.uniform(0.5, 1.0), 2),
                "position_size": round(random.uniform(0.01, 0.1), 4)
            }
        elif strategy_type == "momentum":
            base_config["parameters"] = {
                "lookback_period": random.randint(5, 20),
                "momentum_threshold": round(random.uniform(0.02, 0.08), 4),
                "position_size": round(random.uniform(0.01, 0.1), 4)
            }
        elif strategy_type == "breakout":
            base_config["parameters"] = {
                "lookback_period": random.randint(20, 100),
                "breakout_threshold": round(random.uniform(1.5, 3.0), 2),
                "volume_threshold": random.randint(100000, 1000000),
                "position_size": round(random.uniform(0.01, 0.1), 4)
            }

        # Add risk management parameters
        base_config["risk_management"] = {
            "max_position_size": round(random.uniform(1000, 10000), 2),
            "stop_loss_percentage": round(random.uniform(0.02, 0.10), 4),
            "take_profit_percentage": round(random.uniform(0.05, 0.20), 4),
            "max_positions": random.randint(1, 10)
        }

        return base_config

    def generate_strategy_configs(self, count: int) -> List[Dict[str, Any]]:
        """Generate multiple strategy configurations."""
        return [self.generate_strategy_config() for _ in range(count)]


class AccountFactory:
    """Factory for generating account data."""

    def generate_account_info(self) -> Dict[str, Any]:
        """Generate account information."""
        return {
            "id": str(uuid.uuid4()),
            "account_number": f"ACC{random.randint(100000, 999999)}",
            "cash_balance": round(random.uniform(1000, 100000), 2),
            "equity": round(random.uniform(1000, 100000), 2),
            "buying_power": round(random.uniform(1000, 100000), 2),
            "currency": "USD",
            "status": "active",
            "created_at": datetime.now() - timedelta(days=random.randint(30, 365))
        }

    def generate_balance_sheet(self) -> Dict[str, Any]:
        """Generate a balance sheet."""
        cash_balance = random.uniform(1000, 100000)
        total_positions_value = random.uniform(5000, 50000)
        total_equity = cash_balance + total_positions_value

        return {
            "cash_balance": round(cash_balance, 2),
            "total_positions_value": round(total_positions_value, 2),
            "total_equity": round(total_equity, 2),
            "day_trading_buying_power": round(total_equity * 4, 2),
            "maintenance_excess": round(total_equity * 0.25, 2),
            "currency": "USD",
            "timestamp": datetime.now()
        }


class TestDataFactory:
    """Main factory for generating all types of test data."""

    def __init__(self):
        self.market_factory = MarketDataFactory()
        self.position_factory = PositionFactory()
        self.order_factory = OrderFactory()
        self.strategy_factory = StrategyFactory()
        self.account_factory = AccountFactory()

    def generate_complete_test_scenario(self) -> Dict[str, Any]:
        """Generate a complete test scenario with all data types."""
        # Generate account data
        account = self.account_factory.generate_account_info()

        # Generate positions
        positions = self.position_factory.generate_positions(random.randint(1, 5))

        # Generate orders
        orders = self.order_factory.generate_orders(random.randint(0, 10))

        # Generate market data for all symbols in positions and orders
        symbols = set()
        for position in positions:
            symbols.add(position["symbol"])
        for order in orders:
            symbols.add(order["symbol"])

        symbols = list(symbols) if symbols else ["BTC", "ETH"]
        market_data = self.market_factory.generate_quotes(symbols)

        # Generate strategy configs
        strategies = self.strategy_factory.generate_strategy_configs(random.randint(1, 3))

        return {
            "account": account,
            "positions": positions,
            "orders": orders,
            "market_data": market_data,
            "strategies": strategies,
            "timestamp": datetime.now(),
            "scenario_id": str(uuid.uuid4())
        }

    def generate_bulk_test_data(self, scenarios: int = 10) -> List[Dict[str, Any]]:
        """Generate multiple test scenarios."""
        return [self.generate_complete_test_scenario() for _ in range(scenarios)]

    # Convenience methods
    def create_position(self, **kwargs) -> Dict[str, Any]:
        """Create a single position."""
        return self.position_factory.generate_position(**kwargs)

    def create_order(self, **kwargs) -> Dict[str, Any]:
        """Create a single order."""
        return self.order_factory.generate_order(**kwargs)

    def create_quote(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Create a single quote."""
        quote = self.market_factory.generate_quote(symbol)
        # Override with provided kwargs
        for key, value in kwargs.items():
            if key in quote:
                quote[key] = value
        return quote

    def create_strategy(self, **kwargs) -> Dict[str, Any]:
        """Create a single strategy."""
        return self.strategy_factory.generate_strategy_config(**kwargs)


# Global factory instance
test_data_factory = TestDataFactory()


# Convenience functions
def create_test_position(symbol: str = "BTC", side: str = "long",
                        quantity: float = 0.1, avg_price: float = 50000.0) -> Dict[str, Any]:
    """Convenience function to create a test position."""
    return test_data_factory.create_position(
        symbol=symbol, side=side, quantity=quantity, avg_price=avg_price
    )


def create_test_order(symbol: str = "BTC", side: str = "buy",
                     quantity: float = 0.1, order_type: str = "limit") -> Dict[str, Any]:
    """Convenience function to create a test order."""
    return test_data_factory.create_order(
        symbol=symbol, side=side, quantity=quantity, order_type=order_type
    )


def create_test_market_data(symbol: str = "BTC", price: float = 50000.0) -> Dict[str, Any]:
    """Convenience function to create test market data."""
    return test_data_factory.create_quote(symbol, last_trade_price=price)


def create_test_scenario() -> Dict[str, Any]:
    """Convenience function to create a complete test scenario."""
    return test_data_factory.generate_complete_test_scenario()