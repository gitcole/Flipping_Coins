"""
Mock implementations for external API dependencies.
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Union
from unittest.mock import AsyncMock, Mock
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class MockApiResponse:
    """Represents a mock API response."""
    data: Any
    status_code: int = 200
    headers: Dict[str, str] = None
    delay: float = 0.0  # Simulate network delay

    def __post_init__(self):
        if self.headers is None:
            self.headers = {"Content-Type": "application/json"}


class RobinhoodApiMock:
    """Comprehensive mock for Robinhood API client."""

    def __init__(self):
        self.authenticated = False
        self.auth_token = "mock_auth_token"
        self.request_count = 0
        self.error_mode = False
        self.error_rate = 0.0  # 0-1.0

        # Storage for mock data
        self._accounts = {}
        self._instruments = {}
        self._quotes = {}
        self._orders = {}
        self._positions = {}
        self._market_data = {}

        self._setup_default_data()
        self._setup_crypto_data()

    def _setup_default_data(self):
        """Setup default mock data."""
        # Default account
        self._accounts["default"] = {
            "id": "mock_account_id",
            "account_number": "123456789",
            "cash_balance": "10000.00",
            "equity": "10000.00",
            "buying_power": "10000.00",
            "currency": "USD"
        }

        # Default instruments
        self._instruments = {
            "BTC": {
                "id": "crypto_btc_id",
                "symbol": "BTC",
                "name": "Bitcoin",
                "type": "cryptocurrency",
                "tradability": "tradable",
                "min_order_size": "0.00000001",
                "max_order_size": "100.0"
            },
            "ETH": {
                "id": "crypto_eth_id",
                "symbol": "ETH",
                "name": "Ethereum",
                "type": "cryptocurrency",
                "tradability": "tradable",
                "min_order_size": "0.00000001",
                "max_order_size": "1000.0"
            }
        }

        # Default quotes
        self._quotes = {
            "BTC": {
                "symbol": "BTC",
                "ask_price": "50000.00",
                "bid_price": "49990.00",
                "last_trade_price": "50000.00",
                "volume": "1000000",
                "high_24h": "51000.00",
                "low_24h": "49000.00"
            },
            "ETH": {
                "symbol": "ETH",
                "ask_price": "3000.00",
                "bid_price": "2995.00",
                "last_trade_price": "3000.00",
                "volume": "500000",
                "high_24h": "3100.00",
                "low_24h": "2900.00"
            }
        }

        # Default positions
        self._positions = {
            "BTC": {
                "symbol": "BTC",
                "quantity": "0.1",
                "average_price": "45000.00",
                "current_price": "50000.00",
                "unrealized_pnl": "500.00"
            }
        }

        # Crypto-specific data
        self._crypto_accounts = {}
        self._crypto_positions = {}
        self._crypto_orders = {}
        self._crypto_quotes = {}

    def _setup_crypto_data(self):
        """Setup default crypto API mock data."""
        # Default crypto account
        self._crypto_accounts["default"] = {
            "id": "crypto_account_id",
            "account_number": "CRYPTO123456",
            "status": "active",
            "buying_power": "10000.00",
            "cash_balance": "5000.00",
            "currency": "USD"
        }

        # Default crypto positions
        self._crypto_positions = {
            "BTC": {
                "asset_code": "BTC",
                "quantity": "0.1",
                "average_cost": "50000.00",
                "current_price": "51000.00",
                "market_value": "5100.00",
                "unrealized_pnl": "100.00",
                "unrealized_pnl_percent": "2.00"
            },
            "ETH": {
                "asset_code": "ETH",
                "quantity": "1.0",
                "average_cost": "3000.00",
                "current_price": "3100.00",
                "market_value": "3100.00",
                "unrealized_pnl": "100.00",
                "unrealized_pnl_percent": "3.33"
            }
        }

        # Default crypto quotes
        self._crypto_quotes = {
            "BTC": {
                "symbol": "BTC",
                "bid_price": "49990.00",
                "ask_price": "50010.00",
                "last_trade_price": "50000.00",
                "volume_24h": "1000000.00",
                "high_24h": "51000.00",
                "low_24h": "49000.00"
            },
            "ETH": {
                "symbol": "ETH",
                "bid_price": "2990.00",
                "ask_price": "3010.00",
                "last_trade_price": "3000.00",
                "volume_24h": "500000.00",
                "high_24h": "3100.00",
                "low_24h": "2900.00"
            }
        }

        # Default crypto orders
        self._crypto_orders = {}

    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """Mock authentication."""
        await self._simulate_delay(0.1)

        if self.error_mode and self._should_error():
            raise Exception("Authentication failed")

        self.authenticated = True
        return {
            "token": self.auth_token,
            "expires_at": datetime.now() + timedelta(hours=24)
        }

    async def get_account_info(self) -> Dict[str, Any]:
        """Mock get account information."""
        await self._simulate_delay(0.05)

        if not self.authenticated:
            raise Exception("Not authenticated")

        if self.error_mode and self._should_error():
            raise Exception("Failed to get account info")

        return self._accounts["default"].copy()

    async def get_instruments(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock get instruments."""
        await self._simulate_delay(0.03)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get instruments")

        instruments = list(self._instruments.values())
        if symbol:
            instruments = [i for i in instruments if i["symbol"] == symbol]

        return instruments

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Mock get quote for a symbol."""
        await self._simulate_delay(0.02)

        if self.error_mode and self._should_error():
            raise Exception(f"Failed to get quote for {symbol}")

        if symbol not in self._quotes:
            raise Exception(f"Quote not found for {symbol}")

        return self._quotes[symbol].copy()

    async def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Mock get quotes for multiple symbols."""
        await self._simulate_delay(0.05)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get quotes")

        result = {}
        for symbol in symbols:
            if symbol in self._quotes:
                result[symbol] = self._quotes[symbol].copy()
            else:
                result[symbol] = {"error": f"Quote not found for {symbol}"}

        return result

    async def place_order(self, **order_data) -> Dict[str, Any]:
        """Mock place order."""
        await self._simulate_delay(0.1)

        if not self.authenticated:
            raise Exception("Not authenticated")

        if self.error_mode and self._should_error():
            raise Exception("Failed to place order")

        order_id = f"mock_order_{int(time.time() * 1000)}"

        order = {
            "id": order_id,
            "symbol": order_data.get("symbol"),
            "quantity": order_data.get("quantity"),
            "side": order_data.get("side"),
            "type": order_data.get("type", "limit"),
            "price": order_data.get("price"),
            "status": "placed",
            "created_at": datetime.now().isoformat()
        }

        self._orders[order_id] = order
        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Mock cancel order."""
        await self._simulate_delay(0.05)

        if not self.authenticated:
            raise Exception("Not authenticated")

        if self.error_mode and self._should_error():
            raise Exception("Failed to cancel order")

        if order_id in self._orders:
            self._orders[order_id]["status"] = "cancelled"
            return True

        return False

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Mock get order details."""
        await self._simulate_delay(0.03)

        if order_id not in self._orders:
            raise Exception(f"Order {order_id} not found")

        return self._orders[order_id].copy()

    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock get orders."""
        await self._simulate_delay(0.04)

        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o["status"] == status]

        return orders

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Mock get positions."""
        await self._simulate_delay(0.03)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get positions")

        return list(self._positions.values())

    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Mock get position for a symbol."""
        await self._simulate_delay(0.02)

        if symbol not in self._positions:
            raise Exception(f"Position not found for {symbol}")

        return self._positions[symbol].copy()

    async def close_position(self, symbol: str, quantity: Optional[str] = None) -> Dict[str, Any]:
        """Mock close position."""
        await self._simulate_delay(0.1)

        if symbol not in self._positions:
            raise Exception(f"No position found for {symbol}")

        position = self._positions[symbol]
        close_quantity = quantity or position["quantity"]

        order = await self.place_order(
            symbol=symbol,
            quantity=close_quantity,
            side="sell" if position.get("side", "long") == "long" else "buy",
            type="market"
        )

        # Update position
        if float(position["quantity"]) <= float(close_quantity):
            del self._positions[symbol]
        else:
            position["quantity"] = str(float(position["quantity"]) - float(close_quantity))

        return order

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Mock get market data."""
        await self._simulate_delay(0.02)

        if symbol not in self._quotes:
            raise Exception(f"Market data not found for {symbol}")

        quote = self._quotes[symbol]
        return {
            "symbol": symbol,
            "price": quote["last_trade_price"],
            "volume": quote["volume"],
            "change_24h": "2.5",
            "high_24h": quote["high_24h"],
            "low_24h": quote["low_24h"],
            "timestamp": datetime.now().isoformat()
        }

    # Crypto API Mock Methods

    async def get_crypto_account(self) -> Dict[str, Any]:
        """Mock get crypto trading account."""
        await self._simulate_delay(0.03)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get crypto account")

        return self._crypto_accounts["default"].copy()

    async def get_crypto_positions(self, asset_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Mock get crypto positions."""
        await self._simulate_delay(0.04)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get crypto positions")

        positions = list(self._crypto_positions.values())
        if asset_codes:
            positions = [p for p in positions if p["asset_code"] in asset_codes]

        return {"results": positions}

    async def get_crypto_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Mock get crypto quotes for multiple symbols."""
        await self._simulate_delay(0.03)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get crypto quotes")

        results = []
        for symbol in symbols:
            if symbol in self._crypto_quotes:
                results.append(self._crypto_quotes[symbol].copy())
            else:
                results.append({"symbol": symbol, "error": f"Quote not found for {symbol}"})

        return {"results": results}

    async def get_crypto_quote(self, symbol: str) -> Dict[str, Any]:
        """Mock get crypto quote for single symbol."""
        await self._simulate_delay(0.02)

        if self.error_mode and self._should_error():
            raise Exception(f"Failed to get crypto quote for {symbol}")

        if symbol not in self._crypto_quotes:
            raise Exception(f"Crypto quote not found for {symbol}")

        return self._crypto_quotes[symbol].copy()

    async def get_crypto_estimated_price(self, symbol: str, side: str, quantity: str) -> Dict[str, Any]:
        """Mock get estimated price for crypto trade."""
        await self._simulate_delay(0.02)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get estimated price")

        # Return mock estimated price data
        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "estimated_price": "50000.00",
            "estimated_fees": "5.00",
            "estimated_total": str(float(quantity) * 50000.00 + 5.00)
        }

    async def place_crypto_order(self, **order_data) -> Dict[str, Any]:
        """Mock place crypto order."""
        await self._simulate_delay(0.1)

        if not self.authenticated:
            raise Exception("Not authenticated")

        if self.error_mode and self._should_error():
            raise Exception("Failed to place crypto order")

        order_id = f"crypto_order_{int(time.time() * 1000)}"
        client_order_id = order_data.get("client_order_id", f"client_{order_id}")

        order = {
            "id": order_id,
            "client_order_id": client_order_id,
            "side": order_data.get("side"),
            "order_type": order_data.get("type", "market"),
            "symbol": order_data.get("symbol"),
            "quantity": order_data.get("quantity"),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        if "price" in order_data:
            order["price"] = order_data["price"]
        if "stop_price" in order_data:
            order["stop_price"] = order_data["stop_price"]

        self._crypto_orders[order_id] = order
        return order

    async def get_crypto_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Mock get crypto orders."""
        await self._simulate_delay(0.04)

        if self.error_mode and self._should_error():
            raise Exception("Failed to get crypto orders")

        orders = list(self._crypto_orders.values())
        if symbol:
            orders = [o for o in orders if o["symbol"] == symbol]

        return {"results": orders}

    async def get_crypto_order(self, order_id: str) -> Dict[str, Any]:
        """Mock get specific crypto order."""
        await self._simulate_delay(0.03)

        if order_id not in self._crypto_orders:
            raise Exception(f"Crypto order {order_id} not found")

        return self._crypto_orders[order_id].copy()

    async def cancel_crypto_order(self, order_id: str) -> Dict[str, Any]:
        """Mock cancel crypto order."""
        await self._simulate_delay(0.05)

        if not self.authenticated:
            raise Exception("Not authenticated")

        if self.error_mode and self._should_error():
            raise Exception("Failed to cancel crypto order")

        if order_id in self._crypto_orders:
            self._crypto_orders[order_id]["status"] = "cancelled"
            return {"id": order_id, "status": "cancelled"}

        raise Exception(f"Crypto order {order_id} not found")

    # Configuration methods
    def set_error_mode(self, enabled: bool = True, rate: float = 0.1):
        """Enable/disable error mode for testing error handling."""
        self.error_mode = enabled
        self.error_rate = rate

    def set_quote_price(self, symbol: str, price: float):
        """Set quote price for a symbol."""
        if symbol in self._quotes:
            self._quotes[symbol]["ask_price"] = str(price)
            self._quotes[symbol]["bid_price"] = str(price * 0.9998)
            self._quotes[symbol]["last_trade_price"] = str(price)

    def add_position(self, symbol: str, quantity: str, avg_price: str):
        """Add a position for testing."""
        self._positions[symbol] = {
            "symbol": symbol,
            "quantity": quantity,
            "average_price": avg_price,
            "current_price": self._quotes.get(symbol, {}).get("last_trade_price", "0"),
            "unrealized_pnl": "0.00"
        }

    def clear_positions(self):
        """Clear all positions."""
        self._positions.clear()

    def get_request_count(self) -> int:
        """Get total request count."""
        return self.request_count

    def set_crypto_quote_price(self, symbol: str, price: float):
        """Set crypto quote price for a symbol."""
        if symbol in self._crypto_quotes:
            self._crypto_quotes[symbol]["bid_price"] = str(price * 0.9998)
            self._crypto_quotes[symbol]["ask_price"] = str(price * 1.0002)
            self._crypto_quotes[symbol]["last_trade_price"] = str(price)

    def add_crypto_position(self, asset_code: str, quantity: str, avg_cost: str):
        """Add a crypto position for testing."""
        self._crypto_positions[asset_code] = {
            "asset_code": asset_code,
            "quantity": quantity,
            "average_cost": avg_cost,
            "current_price": self._crypto_quotes.get(asset_code, {}).get("last_trade_price", "0"),
            "market_value": str(float(quantity) * float(self._crypto_quotes.get(asset_code, {}).get("last_trade_price", "0"))),
            "unrealized_pnl": "0.00",
            "unrealized_pnl_percent": "0.00"
        }

    def clear_crypto_positions(self):
        """Clear all crypto positions."""
        self._crypto_positions.clear()

    def clear_crypto_orders(self):
        """Clear all crypto orders."""
        self._crypto_orders.clear()

    async def _simulate_delay(self, seconds: float):
        """Simulate network delay."""
        if seconds > 0:
            await asyncio.sleep(seconds)
        self.request_count += 1

    def _should_error(self) -> bool:
        """Determine if request should error based on error rate."""
        import random
        return random.random() < self.error_rate


class MockApiClientBuilder:
    """Builder for creating customized API mocks."""

    def __init__(self):
        self.config = {
            "authenticated": False,
            "delay": 0.0,
            "error_mode": False,
            "error_rate": 0.0,
            "custom_responses": {}
        }

    def with_authentication(self, token: str = "mock_token") -> 'MockApiClientBuilder':
        """Configure authentication."""
        self.config["authenticated"] = True
        self.config["auth_token"] = token
        return self

    def with_delay(self, seconds: float) -> 'MockApiClientBuilder':
        """Configure response delay."""
        self.config["delay"] = seconds
        return self

    def with_error_mode(self, rate: float = 0.1) -> 'MockApiClientBuilder':
        """Configure error mode."""
        self.config["error_mode"] = True
        self.config["error_rate"] = rate
        return self

    def with_custom_response(self, method: str, response: Dict[str, Any]) -> 'MockApiClientBuilder':
        """Add custom response for a method."""
        self.config["custom_responses"][method] = response
        return self

    def build(self) -> RobinhoodApiMock:
        """Build the configured API mock."""
        mock = RobinhoodApiMock()

        if self.config["authenticated"]:
            mock.authenticated = True
            mock.auth_token = self.config["auth_token"]

        if self.config["delay"] > 0:
            # Patch the delay method to use configured delay
            original_simulate_delay = mock._simulate_delay
            async def custom_delay(seconds):
                await original_simulate_delay(self.config["delay"])
            mock._simulate_delay = custom_delay

        if self.config["error_mode"]:
            mock.set_error_mode(True, self.config["error_rate"])

        return mock


class EnhancedApiMock(RobinhoodApiMock):
    """Enhanced API mock with additional error scenarios and edge cases."""

    def __init__(self):
        super().__init__()
        self._error_patterns = {}
        self._network_conditions = {}
        self._rate_limit_history = []
        self._response_delays = {}

    def set_error_pattern(self, endpoint_pattern: str, error_type: str, frequency: float = 0.5):
        """Set specific error patterns for different endpoints."""
        self._error_patterns[endpoint_pattern] = {
            'error_type': error_type,
            'frequency': frequency
        }

    def set_network_condition(self, condition: str, duration: float = 60.0):
        """Set network conditions like latency, packet loss, etc."""
        self._network_conditions[condition] = {
            'start_time': time.time(),
            'duration': duration,
            'active': True
        }

    def set_variable_response_delay(self, endpoint: str, delay_range: tuple = (0.1, 2.0)):
        """Set variable response delays for specific endpoints."""
        self._response_delays[endpoint] = delay_range

    async def _simulate_enhanced_delay(self, seconds: float):
        """Enhanced delay simulation with network conditions."""
        # Check for active network conditions
        current_time = time.time()
        active_conditions = []

        for condition, config in self._network_conditions.items():
            if (config['active'] and
                current_time >= config['start_time'] and
                current_time <= config['start_time'] + config['duration']):
                active_conditions.append(condition)

        # Apply network condition effects
        for condition in active_conditions:
            if condition == 'high_latency':
                seconds += 1.0  # Add 1 second latency
            elif condition == 'packet_loss':
                if time.time() % 3 < 1:  # 33% packet loss
                    raise Exception("Simulated packet loss")

        # Apply variable delays
        if hasattr(self, '_current_endpoint') and self._current_endpoint in self._response_delays:
            min_delay, max_delay = self._response_delays[self._current_endpoint]
            import random
            seconds = random.uniform(min_delay, max_delay)

        await self._simulate_delay(seconds)

    def should_error_for_endpoint(self, endpoint: str) -> bool:
        """Check if an endpoint should return an error based on patterns."""
        for pattern, config in self._error_patterns.items():
            if pattern in endpoint:
                import random
                return random.random() < config['frequency']

        return False

    def get_error_for_endpoint(self, endpoint: str) -> Optional[str]:
        """Get the error type for a specific endpoint."""
        for pattern, config in self._error_patterns.items():
            if pattern in endpoint:
                return config['error_type']
        return None

    async def simulate_rate_limit_exceeded(self):
        """Simulate rate limit exceeded scenario."""
        from src.core.api.exceptions import RateLimitError

        self._rate_limit_history.append({
            'timestamp': time.time(),
            'event': 'rate_limit_exceeded'
        })

        raise RateLimitError("Rate limit exceeded", retry_after=60)

    async def simulate_network_timeout(self):
        """Simulate network timeout."""
        await asyncio.sleep(0.1)  # Brief delay then timeout
        raise asyncio.TimeoutError("Network request timed out")

    async def simulate_malformed_response(self):
        """Simulate malformed JSON response."""
        return "invalid json response {"

    async def simulate_empty_response(self):
        """Simulate empty response."""
        return ""

    async def simulate_large_response(self, size_mb: float = 1.0):
        """Simulate large response."""
        large_data = "x" * int(size_mb * 1024 * 1024)  # Create large string
        return {"data": large_data}

    def get_rate_limit_history(self) -> List[Dict[str, Any]]:
        """Get rate limit event history."""
        return self._rate_limit_history.copy()

    def clear_error_patterns(self):
        """Clear all error patterns."""
        self._error_patterns.clear()

    def clear_network_conditions(self):
        """Clear all network conditions."""
        self._network_conditions.clear()


class MockScenarioBuilder:
    """Builder for creating complex mock scenarios."""

    def __init__(self):
        self.mock = EnhancedApiMock()
        self.scenario_steps = []
        self.current_step = 0

    def add_step(self, step_type: str, **kwargs):
        """Add a step to the scenario."""
        self.scenario_steps.append({
            'type': step_type,
            'config': kwargs
        })
        return self

    def add_delay_step(self, delay: float):
        """Add a delay step."""
        return self.add_step('delay', seconds=delay)

    def add_error_step(self, error_type: str, endpoint_pattern: str = "*"):
        """Add an error step."""
        return self.add_step('error', error_type=error_type, pattern=endpoint_pattern)

    def add_rate_limit_step(self, request_count: int = 10):
        """Add a rate limit step."""
        return self.add_step('rate_limit', request_count=request_count)

    def add_network_condition_step(self, condition: str, duration: float = 5.0):
        """Add a network condition step."""
        return self.add_step('network_condition', condition=condition, duration=duration)

    def add_response_step(self, endpoint: str, response: Any):
        """Add a custom response step."""
        return self.add_step('response', endpoint=endpoint, response=response)

    def build_scenario(self) -> 'ScenarioMock':
        """Build the scenario mock."""
        return ScenarioMock(self.mock, self.scenario_steps)


class ScenarioMock:
    """Mock that executes predefined scenarios."""

    def __init__(self, base_mock: EnhancedApiMock, steps: List[Dict[str, Any]]):
        self.base_mock = base_mock
        self.steps = steps
        self.current_step = 0
        self.request_count = 0

    async def execute_request(self, method: str, endpoint: str, **kwargs):
        """Execute a request according to the current scenario step."""
        self.request_count += 1

        # Find matching step
        current_step = None
        for step in self.steps:
            if step['type'] == 'response' and step['config']['endpoint'] in endpoint:
                current_step = step
                break
            elif step['type'] != 'response':  # Non-response steps apply to all requests
                current_step = step
                break

        if current_step:
            step_type = current_step['type']
            step_config = current_step['config']

            if step_type == 'delay':
                await self.base_mock._simulate_delay(step_config['seconds'])
            elif step_type == 'error':
                if step_config.get('pattern', '*') in endpoint:
                    error_type = step_config['error_type']
                    if error_type == 'timeout':
                        raise asyncio.TimeoutError("Simulated timeout")
                    elif error_type == 'network':
                        raise Exception("Simulated network error")
                    elif error_type == 'auth':
                        from src.core.api.exceptions import AuthenticationError
                        raise AuthenticationError("Simulated auth error")
            elif step_type == 'rate_limit':
                if self.request_count >= step_config['request_count']:
                    await self.base_mock.simulate_rate_limit_exceeded()
            elif step_type == 'network_condition':
                # Apply network condition if active
                pass
            elif step_type == 'response':
                return step_config['response']

        # Default behavior - delegate to base mock
        return await self.base_mock._simulate_request(method, endpoint, **kwargs)

    async def _simulate_request(self, method: str, endpoint: str, **kwargs):
        """Simulate a request (placeholder for actual implementation)."""
        # This would be implemented to delegate to the appropriate mock method
        # For now, return a generic response
        return {"data": "mock_response", "endpoint": endpoint, "method": method}