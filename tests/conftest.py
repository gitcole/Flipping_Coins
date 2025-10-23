"""
Shared pytest configuration and fixtures for the crypto trading bot tests.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, Mock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import only what we need and avoid problematic imports
try:
    from src.core.config.settings import Settings
except ImportError:
    # Fallback for when running tests from different directories
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from src.core.config.settings import Settings

# Optional imports that might not be available in test environment
try:
    from src.core.api.robinhood.client import RobinhoodClient
except ImportError:
    RobinhoodClient = None

try:
    from src.core.websocket.client import WebSocketClient
except ImportError:
    WebSocketClient = None

try:
    from src.core.engine.trading_engine import TradingEngine
except ImportError:
    TradingEngine = None

try:
    from src.core.risk.manager import RiskManager
except ImportError:
    try:
        from src.core.risk.risk_manager import RiskManager
    except ImportError:
        RiskManager = None


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings() -> Settings:
    """Test settings with mocked external dependencies."""
    return Settings(
        app=dict(
            name="test-bot",
            version="1.0.0",
            debug=True,
            log_level="INFO",
            environment="testing"
        ),
        robinhood=dict(
            api_key="test_api_key",
            public_key="test_public_key",
            sandbox=True
        ),
        trading=dict(
            enabled=False,
            max_positions=5,
            default_risk_per_trade=0.02,
            min_order_size=10.0
        ),
        risk=dict(
            max_portfolio_risk=0.1,
            stop_loss_default=0.05,
            take_profit_default=0.10
        ),
        database=dict(
            redis=dict(
                host="localhost",
                port=6379,
                db=1
            )
        )
    )


@pytest.fixture
def mock_robinhood_client() -> AsyncMock:
    """Mock Robinhood API client."""
    if RobinhoodClient is None:
        # Create a basic mock when import fails
        mock_client = AsyncMock()
    else:
        mock_client = AsyncMock(spec=RobinhoodClient)

    # Mock authentication
    mock_client.auth.is_authenticated.return_value = True
    mock_client.auth.get_api_key.return_value = "test_api_key"

    # Mock account info
    mock_client.get_user.return_value = {
        "id": "test_account_id",
        "cash_balance": "10000.00",
        "equity": "10000.00"
    }

    # Mock instruments
    mock_client.get_instruments.return_value = [
        {
            "id": "crypto_btc",
            "symbol": "BTC",
            "name": "Bitcoin",
            "type": "cryptocurrency"
        }
    ]

    # Mock quotes
    mock_client.get_quotes.return_value = {
        "BTC": {
            "symbol": "BTC",
            "ask_price": "50000.00",
            "bid_price": "49990.00",
            "last_trade_price": "50000.00"
        }
    }

    # Mock order methods
    mock_client.orders.place_order.return_value = {"id": "test_order_id"}
    mock_client.orders.cancel_order.return_value = True

    # Mock market data methods
    mock_client.market_data.get_crypto_quotes.return_value = {
        "BTC": {
            "symbol": "BTC",
            "price": 50000.00,
            "volume": 1000000
        }
    }

    return mock_client


@pytest.fixture
def mock_redis_client() -> Mock:
    """Mock Redis client."""
    mock_redis = Mock()

    # Mock basic Redis operations
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True

    # Mock Redis hash operations
    mock_redis.hget.return_value = None
    mock_redis.hset.return_value = True
    mock_redis.hgetall.return_value = {}

    # Mock Redis list operations
    mock_redis.lpush.return_value = True
    mock_redis.rpop.return_value = None
    mock_redis.llen.return_value = 0

    return mock_redis


@pytest.fixture
def mock_websocket_client() -> AsyncMock:
    """Mock WebSocket client."""
    mock_ws = AsyncMock(spec=WebSocketClient)

    # Mock connection methods
    mock_ws.connect.return_value = None
    mock_ws.disconnect.return_value = None
    mock_ws.is_connected.return_value = False

    # Mock message handling
    mock_ws.send_message.return_value = None

    return mock_ws


@pytest.fixture
def mock_trading_engine() -> AsyncMock:
    """Mock trading engine."""
    mock_engine = AsyncMock(spec=TradingEngine)

    # Mock engine state
    mock_engine.is_running = False
    mock_engine.positions = {}

    # Mock engine methods
    mock_engine.start.return_value = None
    mock_engine.stop.return_value = None
    mock_engine.place_order.return_value = {"id": "test_order_id"}
    mock_engine.cancel_order.return_value = True

    return mock_engine


@pytest.fixture
def mock_risk_manager() -> AsyncMock:
    """Mock risk manager."""
    mock_risk = AsyncMock(spec=RiskManager)

    # Mock risk checks
    mock_risk.validate_order.return_value = True
    mock_risk.check_position_limits.return_value = True
    mock_risk.calculate_position_risk.return_value = 0.01

    return mock_risk


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Sample market data for testing."""
    return {
        "BTC": {
            "symbol": "BTC",
            "price": 50000.00,
            "volume": 1000000,
            "change_24h": 2.5,
            "high_24h": 51000.00,
            "low_24h": 49000.00,
            "timestamp": "2024-01-01T00:00:00Z"
        },
        "ETH": {
            "symbol": "ETH",
            "price": 3000.00,
            "volume": 500000,
            "change_24h": -1.2,
            "high_24h": 3100.00,
            "low_24h": 2900.00,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def sample_position_data() -> Dict[str, Any]:
    """Sample position data for testing."""
    return {
        "BTC": {
            "symbol": "BTC",
            "quantity": 0.1,
            "avg_price": 45000.00,
            "current_price": 50000.00,
            "unrealized_pnl": 500.00,
            "realized_pnl": 0.00,
            "side": "long"
        }
    }


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """Sample order data for testing."""
    return {
        "symbol": "BTC",
        "quantity": 0.1,
        "side": "buy",
        "type": "limit",
        "price": 50000.00,
        "stop_price": None,
        "time_in_force": "gtc"
    }


@pytest.fixture
def sample_strategy_config() -> Dict[str, Any]:
    """Sample strategy configuration for testing."""
    return {
        "name": "test_strategy",
        "type": "mean_reversion",
        "symbols": ["BTC", "ETH"],
        "parameters": {
            "lookback_period": 20,
            "entry_threshold": 2.0,
            "exit_threshold": 0.5,
            "position_size": 0.1
        },
        "risk_management": {
            "max_position_size": 1000.0,
            "stop_loss": 0.05,
            "take_profit": 0.10
        }
    }


@pytest.fixture
async def async_test_context():
    """Context manager for async tests."""
    yield {
        "settings": Settings(),
        "event_loop": asyncio.get_event_loop()
    }


@pytest.fixture
def test_data_factory():
    """Factory for creating test data."""
    def create_position(symbol: str = "BTC", quantity: float = 0.1,
                       avg_price: float = 50000.00) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "quantity": quantity,
            "avg_price": avg_price,
            "current_price": avg_price * 1.1,
            "unrealized_pnl": quantity * avg_price * 0.1,
            "realized_pnl": 0.00,
            "side": "long"
        }

    def create_market_data(symbol: str = "BTC", price: float = 50000.00) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "price": price,
            "volume": 1000000,
            "change_24h": 2.5,
            "high_24h": price * 1.02,
            "low_24h": price * 0.98,
            "timestamp": "2024-01-01T00:00:00Z"
        }

    return {
        "position": create_position,
        "market_data": create_market_data
    }


# Global test configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Configure pytest-asyncio
    try:
        import pytest_asyncio
        pytest_asyncio.plugin.pytest_configure(config)
    except ImportError:
        pass  # pytest-asyncio not available

    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to ensure proper ordering."""
    # Mark all tests in unit/ as unit tests
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)