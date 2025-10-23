# 📖 Examples & Tutorials

This document provides comprehensive code examples and tutorials for using the Robinhood Crypto Trading Bot.

## Quick Start Examples

### Basic Bot Usage

```python
import asyncio
from src.core.api.robinhood.client import RobinhoodClient

async def basic_example():
    """Basic example of using the Robinhood client."""
    async with RobinhoodClient(sandbox=True) as client:
        # Get account information
        account = await client.get_account()
        print(f"Account: {account}")

        # Get current prices for multiple symbols
        symbols = ["BTC", "ETH", "DOGE"]
        quotes = await client.get_quotes(symbols)

        for quote in quotes:
            print(f"{quote.symbol}: ${quote.price} ({quote.change_24h:+.2%})")

        # Place a buy order
        order = await client.place_order({
            "symbol": "BTC",
            "side": "buy",
            "type": "market",
            "quantity": 0.001
        })
        print(f"Order placed: {order.id}")

# Run the example
asyncio.run(basic_example())
```

### Interactive Mode Usage

```bash
# Start the bot in interactive mode
python -m src

# The bot will show an interactive prompt:
🤖 Robinhood Bot > help

# Available commands:
📋 AVAILABLE COMMANDS:
   📊 status     - Show bot status & component health
   💰 prices     - Show current crypto prices
   💱 cryptos    - Show crypto positions & available cryptos
   📈 portfolio  - Show portfolio information
   🎯 strategies - List/manage trading strategies
   ⚠️  risk       - Show/modify risk settings
   ⚙️  config     - Show current configuration
   ⚡ trading    - Enable/disable trading

# Example usage:
🤖 Robinhood Bot > prices
🤖 Robinhood Bot > trading on
🤖 Robinhood Bot > strategies
```

## Strategy Development

### Creating a Custom Strategy

```python
from src.strategies.base.strategy import BaseStrategy
from decimal import Decimal
from typing import List, Dict, Optional

class MyMomentumStrategy(BaseStrategy):
    """A simple momentum-based trading strategy."""

    def __init__(self, config):
        super().__init__(config)
        self.name = "momentum_strategy"
        self.lookback_period = getattr(config, 'lookback_period', 20)
        self.entry_threshold = getattr(config, 'entry_threshold', 0.02)

    async def generate_signals(self, market_data: Dict) -> List[Dict]:
        """Generate trading signals based on momentum indicators."""
        signals = []

        # Calculate momentum (simplified example)
        momentum = self.calculate_momentum(market_data)

        if momentum > self.entry_threshold:
            # Strong upward momentum - buy signal
            signal = {
                'action': 'BUY',
                'symbol': market_data['symbol'],
                'quantity': self.calculate_position_size(market_data),
                'confidence': min(momentum / self.entry_threshold, 1.0),
                'reason': f'Momentum: {momentum:.4f}'
            }
            signals.append(signal)

        elif momentum < -self.entry_threshold:
            # Strong downward momentum - sell signal
            signal = {
                'action': 'SELL',
                'symbol': market_data['symbol'],
                'quantity': self.calculate_position_size(market_data),
                'confidence': min(abs(momentum) / self.entry_threshold, 1.0),
                'reason': f'Momentum: {momentum:.4f}'
            }
            signals.append(signal)

        return signals

    def calculate_momentum(self, market_data: Dict) -> float:
        """Calculate momentum indicator (simplified)."""
        # This is a simplified example - real implementation would use
        # proper technical indicators like RSI, MACD, etc.
        current_price = market_data['price']
        avg_price = market_data.get('avg_price_20', current_price)

        return (current_price - avg_price) / avg_price

    def calculate_position_size(self, market_data: Dict) -> Decimal:
        """Calculate position size based on risk management."""
        capital = getattr(self.config, 'capital', Decimal('1000'))
        risk_per_trade = getattr(self.config, 'risk_per_trade', 0.02)

        # Risk-based position sizing
        stop_loss_distance = 0.05  # 5% stop loss
        risk_amount = capital * Decimal(str(risk_per_trade))

        price = Decimal(str(market_data['price']))
        position_value = risk_amount / Decimal(str(stop_loss_distance))

        return position_value / price

# Register the strategy
from src.core.app.orchestrator import ApplicationOrchestrator

async def register_strategy():
    orchestrator = ApplicationOrchestrator()

    # Create strategy instance
    strategy_config = type('Config', (), {
        'lookback_period': 20,
        'entry_threshold': 0.02,
        'capital': Decimal('1000'),
        'risk_per_trade': 0.02
    })()

    strategy = MyMomentumStrategy(strategy_config)

    # Register with orchestrator
    await orchestrator.strategy_registry.register_strategy(
        "momentum_strategy",
        strategy
    )

    # Enable the strategy
    await orchestrator.strategy_registry.enable_strategy("momentum_strategy")

asyncio.run(register_strategy())
```

### Market Making Strategy

```python
from src.strategies.base.strategy import BaseStrategy
from decimal import Decimal

class MarketMakingStrategy(BaseStrategy):
    """Advanced market making strategy with inventory management."""

    def __init__(self, config):
        super().__init__(config)
        self.name = "market_making"
        self.spread_percentage = getattr(config, 'spread_percentage', 0.001)
        self.inventory_target = getattr(config, 'inventory_target', 0.5)
        self.inventory_range = getattr(config, 'inventory_range', 0.1)
        self.order_refresh_time = getattr(config, 'order_refresh_time', 30)

    async def generate_signals(self, market_data: Dict) -> List[Dict]:
        """Generate market making orders."""
        signals = []
        current_price = Decimal(str(market_data['price']))

        # Calculate bid and ask prices
        spread = current_price * Decimal(str(self.spread_percentage))
        bid_price = current_price - spread / 2
        ask_price = current_price + spread / 2

        # Get current inventory (simplified)
        current_inventory = await self.get_current_inventory(market_data['symbol'])

        # Adjust prices based on inventory
        inventory_deviation = current_inventory - self.inventory_target

        if inventory_deviation > self.inventory_range:
            # Too much inventory - sell more aggressively
            bid_price *= Decimal('0.999')  # Tighten bid
            ask_price *= Decimal('1.001')  # Widen ask
        elif inventory_deviation < -self.inventory_range:
            # Too little inventory - buy more aggressively
            bid_price *= Decimal('1.001')  # Widen bid
            ask_price *= Decimal('0.999')  # Tighten ask

        # Create buy order (bid)
        buy_signal = {
            'action': 'BUY',
            'symbol': market_data['symbol'],
            'type': 'LIMIT',
            'quantity': self.calculate_order_quantity(current_price, bid_price),
            'price': float(bid_price),
            'time_in_force': 'GTC'
        }
        signals.append(buy_signal)

        # Create sell order (ask)
        sell_signal = {
            'action': 'SELL',
            'symbol': market_data['symbol'],
            'type': 'LIMIT',
            'quantity': self.calculate_order_quantity(current_price, ask_price),
            'price': float(ask_price),
            'time_in_force': 'GTC'
        }
        signals.append(sell_signal)

        return signals

    async def get_current_inventory(self, symbol: str) -> float:
        """Get current inventory for symbol (simplified)."""
        # In real implementation, this would query position manager
        return 0.5  # Return neutral inventory for example

    def calculate_order_quantity(self, current_price: Decimal, order_price: Decimal) -> Decimal:
        """Calculate order quantity based on price levels."""
        # Use smaller orders for orders farther from mid price
        price_distance = abs(order_price - current_price) / current_price

        base_quantity = Decimal('0.001')  # Base order size
        adjusted_quantity = base_quantity * (1 - price_distance)

        return max(adjusted_quantity, Decimal('0.0001'))  # Minimum order size
```

## Risk Management

### Custom Risk Manager

```python
from src.risk.manager import RiskManager
from decimal import Decimal

class CustomRiskManager(RiskManager):
    """Custom risk manager with additional constraints."""

    def __init__(self, config):
        super().__init__(config)
        self.max_sector_exposure = getattr(config, 'max_sector_exposure', 0.3)
        self.correlation_threshold = getattr(config, 'correlation_threshold', 0.7)

    async def validate_trade(self, order: Dict) -> bool:
        """Enhanced trade validation with sector and correlation limits."""
        # Basic validation from parent class
        if not await super().validate_trade(order):
            return False

        # Check sector exposure
        if not self.check_sector_exposure(order):
            return False

        # Check correlation limits
        if not self.check_correlation_limits(order):
            return False

        return True

    def check_sector_exposure(self, order: Dict) -> bool:
        """Check if trade would exceed sector exposure limits."""
        symbol = order['symbol']
        sector = self.get_symbol_sector(symbol)

        current_sector_exposure = self.get_sector_exposure(sector)
        trade_value = Decimal(str(order['quantity'])) * Decimal(str(order['price']))

        if current_sector_exposure + trade_value > self.max_sector_exposure:
            self.logger.warning(
                f"Sector exposure limit exceeded for {sector}. "
                f"Current: {current_sector_exposure}, Trade: {trade_value}, "
                f"Limit: {self.max_sector_exposure}"
            )
            return False

        return True

    def check_correlation_limits(self, order: Dict) -> bool:
        """Check correlation limits with existing positions."""
        symbol = order['symbol']

        for position_symbol, position in self.positions.items():
            if position_symbol == symbol:
                continue

            correlation = self.get_correlation(symbol, position_symbol)
            if correlation > self.correlation_threshold:
                self.logger.warning(
                    f"High correlation detected between {symbol} and {position_symbol}. "
                    f"Correlation: {correlation:.2f}, Threshold: {self.correlation_threshold}"
                )
                return False

        return True

    def get_symbol_sector(self, symbol: str) -> str:
        """Get sector classification for symbol."""
        # Simplified sector classification
        sector_map = {
            'BTC': 'digital_gold',
            'ETH': 'smart_contract',
            'DOGE': 'meme',
            'ADA': 'smart_contract',
            'SOL': 'smart_contract'
        }
        return sector_map.get(symbol, 'other')

    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols."""
        # In real implementation, this would use historical price data
        # For example, this could use 30-day rolling correlation
        return 0.5  # Placeholder
```

## Configuration Examples

### Environment Configuration

```bash
# Development environment
cp config/.env.example config/.env
```

**config/.env:**
```env
# Application
APP_NAME=robinhood-crypto-bot
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=DEBUG

# Robinhood API (Development)
ROBINHOOD_API_KEY=test_api_key
ROBINHOOD_PUBLIC_KEY=test_public_key_base64
ROBINHOOD_SANDBOX=true

# Trading
TRADING_ENABLED=false
MAX_POSITIONS=3
DEFAULT_RISK_PER_TRADE=0.01

# Risk Management
MAX_PORTFOLIO_RISK=0.05
STOP_LOSS_DEFAULT=0.03
TAKE_PROFIT_DEFAULT=0.10

# Redis
REDIS_URL=redis://localhost:6379/0
```

### YAML Configuration

**config/development.yaml:**
```yaml
app:
  name: "crypto-trading-bot-dev"
  version: "1.0.0"
  debug: true
  log_level: "DEBUG"

api:
  base_url: "https://sandbox.robinhood.com"
  timeout: 30
  retries: 3
  rate_limit_per_minute: 50

trading:
  enabled: false
  max_positions: 3
  default_risk_per_trade: 0.01
  supported_symbols:
    - "BTC/USD"
    - "ETH/USD"
    - "DOGE/USD"

strategies:
  market_making:
    enabled: false
    spread_percentage: 0.002
    order_refresh_time: 60

risk:
  max_portfolio_risk: 0.05
  max_correlation: 0.6
  stop_loss_default: 0.03
  take_profit_default: 0.10

logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/development.log"
```

**config/production.yaml:**
```yaml
app:
  name: "crypto-trading-bot-prod"
  version: "1.0.0"
  debug: false
  log_level: "INFO"

api:
  base_url: "https://trading.robinhood.com"
  timeout: 10
  retries: 5
  rate_limit_per_minute: 1000

trading:
  enabled: true
  max_positions: 10
  default_risk_per_trade: 0.02
  supported_symbols:
    - "BTC/USD"
    - "ETH/USD"
    - "ADA/USD"
    - "SOL/USD"
    - "DOT/USD"

strategies:
  market_making:
    enabled: true
    spread_percentage: 0.001
    order_refresh_time: 30
    inventory_range: 0.1

risk:
  max_portfolio_risk: 0.1
  max_correlation: 0.7
  stop_loss_default: 0.05
  take_profit_default: 0.15

monitoring:
  prometheus_enabled: true
  grafana_enabled: true
  health_check_interval: 30
```

## Advanced Usage

### Custom Data Feeds

```python
from src.core.websocket.client import WebSocketClient

class CustomDataFeed(WebSocketClient):
    """Custom data feed integration."""

    async def connect(self, url: str):
        """Connect to custom data source."""
        await super().connect(url)

        # Subscribe to custom channels
        await self.send({
            'type': 'subscribe',
            'channels': ['prices', 'orderbook', 'trades']
        })

    async def on_price_update(self, data: Dict):
        """Handle price updates."""
        # Normalize data format
        normalized_data = {
            'symbol': data['symbol'],
            'price': float(data['price']),
            'timestamp': data['timestamp'],
            'source': 'custom_feed'
        }

        # Forward to price aggregator
        await self.price_aggregator.update(normalized_data)

# Usage
data_feed = CustomDataFeed()
await data_feed.connect("wss://api.custom-exchange.com/ws")
```

### Portfolio Management

```python
from src.core.engine.position_manager import PositionManager
from decimal import Decimal

class PortfolioManager:
    """Advanced portfolio management."""

    def __init__(self, position_manager: PositionManager):
        self.position_manager = position_manager

    async def rebalance_portfolio(self, target_allocation: Dict[str, float]):
        """Rebalance portfolio to target allocation."""
        current_allocation = await self.get_current_allocation()
        rebalancing_orders = []

        for symbol, target_pct in target_allocation.items():
            current_pct = current_allocation.get(symbol, 0)
            difference = target_pct - current_pct

            if abs(difference) > 0.01:  # Minimum rebalance threshold
                # Calculate rebalance order
                portfolio_value = await self.get_portfolio_value()
                target_value = portfolio_value * Decimal(str(target_pct))
                current_value = portfolio_value * Decimal(str(current_pct))

                if difference > 0:
                    # Need to buy more
                    quantity = (target_value - current_value) / Decimal(str(current_value))
                    order = {
                        'symbol': symbol,
                        'side': 'BUY',
                        'quantity': float(quantity),
                        'reason': 'rebalancing'
                    }
                else:
                    # Need to sell
                    quantity = (current_value - target_value) / Decimal(str(current_value))
                    order = {
                        'symbol': symbol,
                        'side': 'SELL',
                        'quantity': float(quantity),
                        'reason': 'rebalancing'
                    }

                rebalancing_orders.append(order)

        # Execute rebalancing orders
        for order in rebalancing_orders:
            await self.position_manager.place_order(order)

    async def get_current_allocation(self) -> Dict[str, float]:
        """Get current portfolio allocation."""
        positions = await self.position_manager.get_all_positions()
        total_value = sum(pos.value for pos in positions.values())

        allocation = {}
        for symbol, position in positions.items():
            allocation[symbol] = float(position.value / total_value) if total_value > 0 else 0

        return allocation
```

### Backtesting Framework

```python
from datetime import datetime, timedelta
from typing import List, Dict

class Backtester:
    """Historical backtesting framework."""

    def __init__(self, strategy, data_provider):
        self.strategy = strategy
        self.data_provider = data_provider
        self.results = []

    async def run_backtest(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: Decimal = Decimal('10000')
    ) -> Dict:
        """Run backtest over historical data."""

        capital = initial_capital
        positions = {}
        trades = []

        # Get historical data
        for symbol in symbols:
            historical_data = await self.data_provider.get_historical_data(
                symbol, start_date, end_date
            )

            # Process each time period
            for timestamp, market_data in historical_data.items():
                # Generate signals
                signals = await self.strategy.generate_signals(market_data)

                # Execute signals
                for signal in signals:
                    if signal['action'] == 'BUY' and capital > 0:
                        # Execute buy order
                        cost = Decimal(str(signal['quantity'])) * Decimal(str(signal['price']))
                        if cost <= capital:
                            capital -= cost
                            positions[symbol] = positions.get(symbol, 0) + signal['quantity']
                            trades.append({
                                'timestamp': timestamp,
                                'symbol': symbol,
                                'side': 'BUY',
                                'quantity': signal['quantity'],
                                'price': signal['price']
                            })

                    elif signal['action'] == 'SELL' and positions.get(symbol, 0) > 0:
                        # Execute sell order
                        revenue = Decimal(str(signal['quantity'])) * Decimal(str(signal['price']))
                        capital += revenue
                        positions[symbol] -= signal['quantity']
                        trades.append({
                            'timestamp': timestamp,
                            'symbol': symbol,
                            'side': 'SELL',
                            'quantity': signal['quantity'],
                            'price': signal['price']
                        })

        # Calculate final results
        final_value = capital + sum(
            positions[symbol] * Decimal(str(self.data_provider.get_price(symbol, end_date)))
            for symbol in positions
        )

        return {
            'initial_capital': float(initial_capital),
            'final_value': float(final_value),
            'total_return': float((final_value - initial_capital) / initial_capital),
            'total_trades': len(trades),
            'winning_trades': len([t for t in trades if t['side'] == 'SELL']),
            'losing_trades': len([t for t in trades if t['side'] == 'BUY']),
            'max_drawdown': self.calculate_max_drawdown(trades)
        }

    def calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown during backtest."""
        # Implementation for drawdown calculation
        return 0.0  # Placeholder
```

## Testing Examples

### Unit Testing Strategies

```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

class TestMomentumStrategy:
    """Test cases for momentum strategy."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance for testing."""
        config = type('Config', (), {
            'lookback_period': 20,
            'entry_threshold': 0.02
        })()
        return MyMomentumStrategy(config)

    @pytest.mark.asyncio
    async def test_buy_signal_generation(self, strategy):
        """Test buy signal generation."""
        # Arrange
        market_data = {
            'symbol': 'BTC/USD',
            'price': 50000,
            'avg_price_20': 49000,
            'rsi': 25,
            'volume': 1000,
            'avg_volume': 800
        }

        # Act
        signals = await strategy.generate_signals(market_data)

        # Assert
        assert len(signals) == 1
        assert signals[0]['action'] == 'BUY'
        assert signals[0]['symbol'] == 'BTC/USD'
        assert signals[0]['confidence'] > 0.5

    @pytest.mark.asyncio
    async def test_no_signal_generation(self, strategy):
        """Test no signal when conditions not met."""
        # Arrange
        market_data = {
            'symbol': 'BTC/USD',
            'price': 50000,
            'avg_price_20': 50100,  # Price below average
            'rsi': 75,  # Overbought
            'volume': 500,
            'avg_volume': 800
        }

        # Act
        signals = await strategy.generate_signals(market_data)

        # Assert
        assert len(signals) == 0

    def test_position_sizing(self, strategy):
        """Test position size calculation."""
        # Arrange
        market_data = {
            'symbol': 'BTC/USD',
            'price': 50000
        }

        # Act
        quantity = strategy.calculate_position_size(market_data)

        # Assert
        assert isinstance(quantity, Decimal)
        assert quantity > 0
```

### Integration Testing

```python
import pytest
from unittest.mock import patch, AsyncMock

class TestRobinhoodClientIntegration:
    """Integration tests for Robinhood client."""

    @pytest.fixture
    def client(self):
        """Create Robinhood client for testing."""
        return RobinhoodClient(sandbox=True)

    @pytest.mark.asyncio
    async def test_quote_retrieval(self, client):
        """Test quote retrieval functionality."""
        with patch.object(client, '_make_request') as mock_request:
            # Mock API response
            mock_request.return_value = {
                'results': [
                    {
                        'symbol': 'BTC',
                        'price': 50000,
                        'change_24h': 0.025
                    }
                ]
            }

            # Act
            quotes = await client.get_quotes(['BTC'])

            # Assert
            assert len(quotes) == 1
            assert quotes[0].symbol == 'BTC'
            assert quotes[0].price == 50000
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling for API failures."""
        with patch.object(client, '_make_request') as mock_request:
            # Mock API error
            mock_request.side_effect = CryptoAPIError("API Error", "NETWORK_ERROR")

            # Act & Assert
            with pytest.raises(CryptoAPIError):
                await client.get_quotes(['INVALID'])
```

## Deployment Examples

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Expose port for health checks
EXPOSE 8000

# Start Redis and the application
CMD redis-server --daemonize yes && python -m src
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  trading-bot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ROBINHOOD_API_KEY=${ROBINHOOD_API_KEY}
      - ROBINHOOD_PUBLIC_KEY=${ROBINHOOD_PUBLIC_KEY}
      - ROBINHOOD_SANDBOX=${ROBINHOOD_SANDBOX}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  redis_data:
```

### Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-bot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-bot
  template:
    metadata:
      labels:
        app: trading-bot
    spec:
      containers:
      - name: trading-bot
        image: crypto-trading-bot:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: ROBINHOOD_API_KEY
          valueFrom:
            secretKeyRef:
              name: robinhood-secrets
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: trading-bot-service
spec:
  selector:
    app: trading-bot
  ports:
  - name: http
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring Examples

### Prometheus Metrics

```python
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Trading metrics
orders_total = Counter('orders_total', 'Total orders placed', ['symbol', 'side', 'strategy'])
order_fill_time = Histogram('order_fill_seconds', 'Order fill time', ['symbol'])

# Performance metrics
api_requests_total = Counter('api_requests_total', 'API requests', ['endpoint', 'method'])
api_request_duration = Histogram('api_request_duration_seconds', 'API request duration')

# Risk metrics
portfolio_risk = Gauge('portfolio_risk_ratio', 'Current portfolio risk ratio')
position_count = Gauge('positions_active', 'Number of active positions')

# Health metrics
component_health = Gauge('component_health', 'Component health status', ['component'])

def update_metrics():
    """Update all metrics."""
    # Update trading metrics
    orders_total.labels(symbol='BTC', side='BUY', strategy='market_making').inc()

    # Update performance metrics
    api_requests_total.labels(endpoint='/quotes', method='GET').inc()

    # Update risk metrics
    portfolio_risk.set(0.15)  # 15% portfolio risk
    position_count.set(5)     # 5 active positions

    # Update health metrics
    component_health.labels(component='api_client').set(1)  # Healthy
    component_health.labels(component='trading_engine').set(1)
```

### Logging Configuration

```python
import structlog
from python_json_logger import jsonlogger

def setup_logging():
    """Set up structured logging."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter())

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )

# Usage in code
logger = structlog.get_logger()

def place_order(order: Dict):
    """Place a trading order with logging."""
    logger.info(
        "Placing order",
        symbol=order['symbol'],
        side=order['side'],
        quantity=order['quantity'],
        price=order.get('price'),
        strategy=order.get('strategy', 'manual')
    )

    try:
        # Order placement logic
        result = await api_client.place_order(order)
        logger.info(
            "Order placed successfully",
            order_id=result['id'],
            symbol=order['symbol']
        )
        return result
    except Exception as e:
        logger.error(
            "Order placement failed",
            error=str(e),
            symbol=order['symbol'],
            side=order['side']
        )
        raise
```

## Error Handling Examples

### Circuit Breaker Pattern

```python
from src.utils.circuit_breaker import CircuitBreaker

class APIClientWithCircuitBreaker:
    """API client with circuit breaker protection."""

    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
        self.session = None

    async def make_request(self, method: str, url: str, **kwargs):
        """Make API request with circuit breaker."""
        async def _request():
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    raise APIError(f"HTTP {response.status}")
                return await response.json()

        return await self.circuit_breaker.call(_request)

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
```

### Retry Logic

```python
from src.utils.retry import retry_async

class RetryableAPIClient:
    """API client with retry logic."""

    @retry_async(
        max_attempts=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(APIError, NetworkError)
    )
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get quotes with automatic retry."""
        response = await self._make_request('GET', '/quotes', params={'symbols': symbols})

        if 'error' in response:
            raise APIError(response['error']['message'])

        return [Quote(**quote_data) for quote_data in response['results']]
```

## Best Practices

### Code Organization

1. **Keep strategies simple and focused**
2. **Use descriptive variable names**
3. **Add comprehensive docstrings**
4. **Handle errors gracefully**
5. **Log important events**

### Performance Optimization

1. **Use async/await for I/O operations**
2. **Batch API calls when possible**
3. **Cache frequently accessed data**
4. **Monitor resource usage**
5. **Profile code for bottlenecks**

### Risk Management

1. **Always use stop losses**
2. **Diversify across assets**
3. **Monitor correlation**
4. **Set realistic position sizes**
5. **Regular portfolio reviews**

### Testing

1. **Write unit tests for all components**
2. **Use mock data for testing**
3. **Test error conditions**
4. **Validate edge cases**
5. **Run integration tests**

This comprehensive set of examples should help you get started with the trading bot and understand how to extend it for your specific needs.