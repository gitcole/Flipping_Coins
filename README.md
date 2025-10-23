# 🤖 Robinhood Crypto Trading Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)

A specialized cryptocurrency trading bot for Robinhood, built with Python, featuring real-time data processing, automated trading strategies, and comprehensive risk management for Robinhood Crypto.

> **⚠️ Important**: Robinhood has restricted their API to institutional users only. Individual developers cannot access the Robinhood API. See [API Setup Guide](ROBINHOOD_API_SETUP.md) for details.

## ✨ Features

- 🚀 **High Performance**: Asynchronous architecture with connection pooling and optimization
- 📊 **Real-time Trading**: Live market data processing and automated order execution
- 🛡️ **Risk Management**: Advanced position sizing, stop-loss, and correlation analysis
- 🎯 **Multiple Strategies**: Market making, momentum, and custom strategy support
- 📈 **Portfolio Management**: Multi-asset portfolio tracking and optimization
- 🔍 **Interactive Mode**: Command-line interface for real-time monitoring and control
- 💰 **Live Price Data**: Real-time crypto prices with fallback simulation
- ⚡ **Trading Control**: Enable/disable trading on-the-fly via interactive commands
- 🔍 **Monitoring**: Comprehensive logging, metrics, and health checks
- 🐳 **Containerized**: Docker support for easy deployment
- ☁️ **Scalable**: Redis caching and microservices architecture

## 📋 Quick Start

### 1. Prerequisites

- **Python 3.11+**
- **Redis Server** (for caching)
- **Git** (for development)
- **Docker** (optional, for containerized deployment)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/crypto-trading-bot.git
cd crypto-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config/.env.example config/.env
# Edit config/.env with your settings
```

### 3. Configuration

**For Development/Testing:**
```bash
# Use the setup script for easy configuration
python setup_credentials.py
```

**For Production (Institutional Access Required):**
See [API Setup Guide](ROBINHOOD_API_SETUP.md) for institutional access requirements.

### 4. Run the Bot

```bash
# Start Redis server (if not running)
redis-server

# Run the trading bot
python -m src
```

## 📚 Documentation

| Topic | Description | Link |
|-------|-------------|------|
| 🚀 **Quick Start** | Get up and running in minutes | [Quick Start Guide](#quick-start) |
| ⚙️ **Configuration** | Complete configuration guide | [Configuration Guide](docs/configuration.md) |
| 🔌 **API Reference** | Complete API documentation | [API Documentation](docs/api.md) |
| 🏗️ **Architecture** | System design and components | [Architecture Guide](docs/architecture.md) |
| 📖 **Examples** | Code examples and tutorials | [Examples & Tutorials](docs/examples.md) |
| 🧪 **Development** | Contributing and development setup | [Developer Guide](CONTRIBUTING.md) |
| 🔧 **API Setup** | Robinhood institutional API access | [API Setup Guide](ROBINHOOD_API_SETUP.md) |
| 📋 **Setup Helper** | Private key configuration tool | [Private Key Helper](README_Private_Key_Helper.md) |
| 🐙 **Git Setup** | Git configuration and workflow | [Git Setup Guide](GIT_SETUP.md) |

## 🏗️ Architecture

```
src/
├── core/                 # Core infrastructure
│   ├── api/             # Exchange API clients (Robinhood, etc.)
│   ├── engine/          # Trading engine & position management
│   ├── websocket/       # Real-time data streams
│   ├── config/          # Configuration management
│   └── app/             # Application orchestration
├── strategies/          # Trading strategies
│   ├── base/           # Strategy framework
│   └── market_making/  # Market making strategy
├── risk/               # Risk management system
└── utils/              # Utilities and helpers
```

## 🛠️ Installation

### System Requirements

- **Python 3.11+** - Core runtime environment
- **Redis Server** - Caching and session storage
- **Git** - Version control (for development)
- **Docker** - Optional, for containerized deployment

### Hardware Requirements

**Minimum:** 2 CPU cores, 4 GB RAM, 10 GB storage
**Recommended:** 4+ CPU cores, 8+ GB RAM, 50 GB SSD storage

### Local Installation

```bash
# Clone the repository
git clone https://github.com/your-username/crypto-trading-bot.git
cd crypto-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config/.env.example config/.env
# Edit config/.env with your settings
```

### Docker Installation

#### Using Docker Compose (Recommended)

```bash
# Copy environment file
cp config/.env.example config/.env
# Edit config/.env with your settings

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f trading-bot
```

#### Manual Docker Build

```bash
# Build and run
docker build -t crypto-trading-bot .
docker run -d --name trading-bot --env-file config/.env crypto-trading-bot
```

## ⚙️ Configuration

### Environment Variables

Key configuration in `config/.env`:

```env
# Robinhood API Configuration
ROBINHOOD_API_KEY=your_api_key_here
ROBINHOOD_PUBLIC_KEY=your_public_key_here
ROBINHOOD_SANDBOX=false

# Trading Configuration
TRADING_ENABLED=true
MAX_POSITIONS=5
DEFAULT_RISK_PER_TRADE=0.01

# Risk Management
MAX_PORTFOLIO_RISK=0.05
STOP_LOSS_DEFAULT=0.03
TAKE_PROFIT_DEFAULT=0.10

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
```

### YAML Configuration

Advanced settings in `config/default.yaml`:

```yaml
# Application settings
app:
  name: "crypto-trading-bot"
  version: "1.0.0"
  debug: false
  log_level: "INFO"

# Trading configuration
trading:
  enabled: false
  max_positions: 10
  supported_symbols:
    - "BTC/USDT"
    - "ETH/USDT"

# Risk management
risk:
  max_portfolio_risk: 0.1
  max_correlation: 0.7
  stop_loss_default: 0.05
  take_profit_default: 0.15
```

## 🚀 Getting Started

### Initial Setup

1. **For Development/Testing:**
```bash
# Use the interactive setup script
python setup_credentials.py
```

2. **For Production (Institutional Access):**
   - See [API Setup Guide](ROBINHOOD_API_SETUP.md)
   - Requires institutional approval from Robinhood
   - Contact: institutional@robinhood.com

### Start the Bot

```bash
# Start Redis server (if not running)
redis-server

# Run the trading bot
python -m src
```

### Command Line Options

```bash
# Development mode with debug logging
python -m src

# Mock data only (no live trading)
python -m src --no-live

# Custom configuration
python -m src --config config/production.yaml

# Dry run mode
DRY_RUN=true python -m src
```

## 🎮 Usage

### Interactive Mode

Once started, the bot enters interactive mode for real-time control:

```bash
🤖 Robinhood Bot > help
📋 AVAILABLE COMMANDS:
   📊 status     - Show bot status & component health
   💰 prices     - Show current crypto prices
   💱 cryptos    - Show crypto positions & available cryptos
   📈 portfolio  - Show portfolio information
   🎯 strategies - List/manage trading strategies
   ⚠️  risk       - Show/modify risk settings
   ⚙️  config     - Show current configuration
   ⚡ trading    - Enable/disable trading
   🆘 help       - Show this help message
   👋 quit       - Exit interactive mode
```

### Code Examples

#### Basic Client Usage

```python
import asyncio
from src.core.api.robinhood.client import RobinhoodClient

async def main():
    # Create client with sandbox mode
    async with RobinhoodClient(sandbox=True) as client:
        # Get account information
        account = await client.get_account()
        print(f"Account: {account}")

        # Get current crypto quotes
        quotes = await client.get_quotes(["BTC", "ETH", "DOGE"])
        for quote in quotes:
            print(f"{quote.symbol}: ${quote.price}")

        # Place a market buy order
        order = await client.place_order({
            "symbol": "BTC",
            "side": "buy",
            "type": "market",
            "quantity": 0.001
        })
        print(f"Order placed: {order.id}")

asyncio.run(main())
```

#### Strategy Development

```python
from src.strategies.base.strategy import BaseStrategy
from decimal import Decimal

class MyCustomStrategy(BaseStrategy):
    """Custom trading strategy example."""

    async def generate_signals(self, market_data):
        """Generate trading signals based on market data."""
        if self.should_buy(market_data):
            return [{
                'action': 'BUY',
                'symbol': market_data['symbol'],
                'quantity': self.calculate_position_size(market_data),
                'confidence': 0.8
            }]

    def should_buy(self, market_data):
        """Determine if we should buy based on strategy rules."""
        return (market_data['rsi'] < 30 and
                market_data['volume'] > market_data['avg_volume'])
```

#### Risk Management

```python
from src.core.app.orchestrator import ApplicationOrchestrator

# Get application instance
orchestrator = ApplicationOrchestrator()

# Check current risk levels
risk_summary = orchestrator.risk_manager.get_risk_summary()
print(f"Portfolio risk: {risk_summary['total_portfolio_risk']:.2%}")
print(f"Active positions: {risk_summary['current_positions']}")

# Adjust risk parameters
orchestrator.risk_manager.max_position_risk = 0.03  # 3% per trade
orchestrator.risk_manager.max_portfolio_risk = 0.15  # 15% total
```

### API Endpoints

If running with the optional web server:

```bash
# Health check
GET /health

# Application status
GET /status

# Strategy information
GET /api/strategies

# Portfolio data
GET /api/portfolio

# Place manual order
POST /api/orders
```

### Configuration Files

#### Environment Configuration (`config/.env`)

```env
# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false

# Robinhood API Configuration
ROBINHOOD_API_TOKEN=your_robinhood_api_token
ROBINHOOD_SANDBOX=false

# Trading Parameters (Conservative settings for Robinhood)
TRADING_ENABLED=true
SUPPORTED_SYMBOLS=BTC/USD,ETH/USD,DOGE/USD
MAX_POSITIONS=5
MIN_ORDER_SIZE=1.0
MAX_ORDER_VALUE=1000.0

# Risk Management (Conservative for Robinhood)
MAX_PORTFOLIO_RISK=0.05  # 5% max portfolio risk
DEFAULT_RISK_PER_TRADE=0.01  # 1% risk per trade
MAX_CORRELATION=0.7
MAX_DRAWDOWN=0.15  # 15% max drawdown

# Database & Caching
REDIS_URL=redis://redis:6379/0
DATABASE_URL=sqlite:///data/trading_bot.db

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
SLACK_WEBHOOK_URL=your_slack_webhook_here
```

#### YAML Configuration (`config/default.yaml`)

```yaml
# Application Configuration
app:
  name: "crypto-trading-bot"
  version: "1.0.0"
  environment: "development"

# Trading Configuration
trading:
  enabled: true
  sandbox: false
  max_positions: 10
  min_order_size: 10.0
  max_order_value: 10000.0
  supported_symbols:
    - "BTC/USDT"
    - "ETH/USDT"
    - "ADA/USDT"
    - "SOL/USDT"

# Strategy Configuration
strategies:
  market_making:
    enabled: true
    spread_percentage: 0.001  # 0.1% spread
    order_refresh_time: 30  # seconds

  momentum:
    enabled: false
    lookback_period: 20
    entry_threshold: 0.02

# Risk Management
risk:
  max_portfolio_risk: 0.1
  max_position_risk: 0.02
  max_correlation: 0.7
  max_drawdown: 0.2
  stop_loss_default: 0.05
  take_profit_default: 0.15

# API Settings
api:
  rate_limit_per_minute: 1000
  timeout_seconds: 30
  retry_attempts: 3

# Logging
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/trading_bot.log"
  max_size: 100MB
  backup_count: 5
```

### Post-Installation Verification

1. **Check application health:**
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", "components": {...}}
```

2. **Verify API connectivity:**
```bash
python -c "
from src.core.api.client import ExchangeAPIClient
client = ExchangeAPIClient('your_api_key', 'your_secret')
print('API Connection:', 'OK' if client.test_connection() else 'FAILED')
"
```

3. **Check strategy loading:**
```bash
python -c "
from src.strategies.registry import StrategyRegistry
registry = StrategyRegistry()
strategies = registry.list_strategies()
print(f'Loaded strategies: {strategies}')
"
```

### Troubleshooting

#### Common Issues

**Redis Connection Failed:**
```bash
# Check if Redis is running
redis-cli ping

# Or start Redis Docker container
docker run -d -p 6379:6379 --name redis redis:alpine
```

**Robinhood API Authentication Failed:**
- **For Institutional Access:** Verify your credentials with Robinhood's institutional team
- **For Testing:** Use placeholder credentials with `ROBINHOOD_SANDBOX=true`
- **Account Setup:** Ensure your Robinhood account has crypto trading enabled
- **Token Management:** The bot handles token refresh automatically
- **Permission Issues:** Confirm your institution has API access approval
- **Complete Guide:** See [ROBINHOOD_API_SETUP.md](ROBINHOOD_API_SETUP.md) for detailed troubleshooting

**Import Errors:**
```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Permission Errors:**
```bash
# Fix file permissions
chmod +x scripts/*.sh
mkdir -p logs data
chmod 755 logs data
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Robinhood API
ROBINHOOD_API_TOKEN=your_robinhood_api_token
ROBINHOOD_SANDBOX=false

# Trading (Conservative settings for Robinhood)
TRADING_ENABLED=true
MAX_POSITIONS=5
DEFAULT_RISK_PER_TRADE=0.01

# Risk Management (Conservative for Robinhood)
MAX_PORTFOLIO_RISK=0.05
STOP_LOSS_DEFAULT=0.03
TAKE_PROFIT_DEFAULT=0.10
```

### YAML Configuration

Advanced settings in `config/default.yaml`:

```yaml
trading:
  enabled: true
  max_positions: 10
  supported_symbols:
    - "BTC/USDT"
    - "ETH/USDT"
    
strategies:
  market_making:
    enabled: true
    spread_percentage: 0.001
```

## Development

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/

# Testing
pytest
```

### Project Structure

- **`src/core/`**: Core infrastructure and services
- **`src/strategies/`**: Trading strategy implementations
- **`src/risk/`**: Risk management and position sizing
- **`tests/`**: Test suite
- **`config/`**: Configuration files
- **`logs/`**: Application logs

## Usage Guide

### Crypto API Usage and Performance Optimizations

#### Robinhood Crypto API Client

The bot includes a high-performance Robinhood Crypto API client with the following optimizations:

**Performance Features:**
- Connection pooling (100 total connections, 10 per host)
- DNS caching (300s TTL) to reduce lookup times
- Keep-alive connections (30s timeout) for connection reuse
- Request compression (gzip, deflate) for reduced bandwidth
- Exponential backoff for retries (up to 30s max delay)
- Automatic rate limiting with token buckets

**Usage Examples:**

```python
import asyncio
from src.core.api.robinhood.crypto_api import RobinhoodCryptoAPI, CryptoOrderRequest

async def main():
    # Initialize the API client
    async with RobinhoodCryptoAPI() as api:
        # Get account information
        account = await api.get_account()
        print(f"Account: {account.account_number}, Balance: ${account.buying_power}")

        # Get current crypto quotes
        symbols = ["BTC", "ETH", "DOGE"]
        quotes = await api.get_quotes(symbols)
        for quote in quotes:
            print(f"{quote.symbol}: ${quote.last_trade_price}")

        # Place a market buy order
        order_request = CryptoOrderRequest(
            side="buy",
            order_type="market",
            symbol="BTC",
            quantity=0.001
        )
        order = await api.place_order(order_request)
        print(f"Order placed: {order.id}")

        # Get order status
        order_details = await api.get_order(order.id)
        print(f"Order status: {order_details['status']}")

        # Get client statistics
        stats = api.get_stats()
        print(f"Requests: {stats['request_count']}, Errors: {stats['error_count']}")

# Run the example
asyncio.run(main())
```

**Error Handling Examples:**

```python
from src.core.api.exceptions import CryptoTradingError, CryptoMarketDataError

async def safe_trading_example():
    async with RobinhoodCryptoAPI() as api:
        try:
            # This might raise CryptoMarketDataError if symbol not found
            quote = await api.get_quote("INVALID_SYMBOL")
        except CryptoMarketDataError as e:
            print(f"Market data error for symbols: {e.symbols}")
            # Handle gracefully - maybe fallback to different symbols

        try:
            # This might raise CryptoTradingError if order fails
            order = await api.place_order(order_request)
        except CryptoTradingError as e:
            print(f"Trading error for {e.symbol}: {e}")
            # Handle trading errors - check account balance, etc.
```

**Migration Guide for Existing Code:**

If you're migrating from the old API implementation:

1. **Import Changes:**
   ```python
   # Old
   from src.core.api.robinhood.crypto import RobinhoodCrypto

   # New
   from src.core.api.robinhood.crypto_api import RobinhoodCryptoAPI
   ```

2. **Authentication:**
   ```python
   # Old - manual token management
   client = RobinhoodCrypto(token="your_token")

   # New - automatic token management from settings
   async with RobinhoodCryptoAPI() as client:
       # Token loaded automatically
       pass
   ```

3. **Error Handling:**
   ```python
   # Old - generic exceptions
   try:
       result = await client.get_quotes(symbols)
   except Exception as e:
       print(f"Error: {e}")

   # New - specific crypto exceptions
   try:
       result = await client.get_quotes(symbols)
   except CryptoMarketDataError as e:
       print(f"Market data error: {e}")
   ```

4. **Performance Monitoring:**
   ```python
   # New feature - get performance stats
   stats = client.get_stats()
   print(f"Success rate: {1 - stats['error_rate']:.2%}")
   ```

**Rate Limiting Configuration:**

The API client automatically handles rate limiting with different buckets:
- **Global**: 100 requests/minute (all requests)
- **Trading**: 30 requests/minute (orders, positions)
- **Market Data**: 200 requests/minute (quotes, prices)
- **Account**: 20 requests/minute (account info, balances)

**Production Configuration:**

For production use, ensure these settings in your config:

```yaml
api:
  rate_limit_per_minute: 1000  # Adjust based on your needs
  timeout_seconds: 30
  retry_attempts: 3

# Connection pooling is automatically configured
# No additional configuration needed for performance optimizations
```

### Basic Operation

#### Starting the Bot

```bash
# Start in development mode with interactive interface
python -m src

# Start with mock data only (no live API calls)
python -m src --no-live

# Start with specific configuration
python -m src --config config/strategies.yaml

# Start in dry-run mode (no actual trades)
DRY_RUN=true python -m src

# Start with debug logging
LOG_LEVEL=DEBUG python -m src
```

#### Command Line Options

```bash
python -m src --help

# Available options:
# --no-live          Disable live price fetching (use mock data only)
# --config PATH      Use specific config file
# --help             Show help message
```

#### Interactive Mode

Once the bot is running, it enters interactive mode where you can monitor and control the system in real-time:

```bash
🤖 Robinhood Bot > help
📋 AVAILABLE COMMANDS:
   📊 status     - Show bot status & component health
   💰 prices     - Show current crypto prices
   💱 cryptos    - Show crypto positions & available cryptos
   📈 portfolio  - Show portfolio information
   🎯 strategies - List/manage trading strategies
   ⚠️  risk       - Show/modify risk settings
   ⚙️  config     - Show current configuration
   ⚡ trading    - Enable/disable trading
   🆘 help       - Show this help message
   👋 quit       - Exit interactive mode

🤖 Robinhood Bot > prices
💰 ROBINHOOD CRYPTO PRICES
==================================================
   Symbol      Price          Change
   ----------  -----------    ------
   BTC/USD     $45000.00     📈 +2.50%
   ETH/USD     $2800.00      📉 -1.20%
   ... and more

🕐 Last updated: 14:30:25
💡 Total supported symbols: 20
💡 Prices are live from Robinhood API

🤖 Robinhood Bot > trading
⚡ TRADING MANAGEMENT
=========================
Current trading status: Disabled (no trading engine)
Commands:
  on   - Enable trading
  off  - Disable trading
  back - Return to main menu

  Trading > on
  Trading enabled

🤖 Robinhood Bot > quit
✅ Robinhood Crypto Bot shutdown complete
```

#### Command Line Options

```bash
python -m src --help

# Common options:
# --config PATH       Use specific config file
# --dry-run          Run without placing real orders
# --log-level LEVEL  Set logging level (DEBUG, INFO, WARNING, ERROR)
# --profile PROFILE  Use specific docker profile
```

### Operational Commands

#### Runtime Management

```python
# In Python console (after starting bot)
from src.core.app.orchestrator import ApplicationOrchestrator

# Get application status
status = orchestrator.get_status()
print(f"Running: {status['is_running']}")
print(f"Components: {status['components']}")

# Check component health
health = orchestrator.get_component_summary()
print(f"Market data: {health['market_data_client']['connected']}")
print(f"Active strategies: {len(orchestrator.strategy_registry.list_active_strategies())}")
```

#### Strategy Management

```python
# Enable/disable strategies
await orchestrator.strategy_registry.enable_strategy("market_making")
await orchestrator.strategy_registry.disable_strategy("momentum")

# Add custom strategy
from src.strategies.custom_strategy import MyCustomStrategy
await orchestrator.strategy_registry.register_strategy("my_strategy", MyCustomStrategy)
```

#### Risk Management

```python
# Check current risk levels
risk_summary = orchestrator.risk_manager.get_risk_summary()
print(f"Portfolio risk: {risk_summary['risk_metrics']['total_portfolio_risk']:.2%}")
print(f"Active positions: {risk_summary['current_positions']}")

# Adjust risk parameters
orchestrator.risk_manager.max_position_risk = 0.03  # 3% per trade
orchestrator.risk_manager.max_portfolio_risk = 0.15  # 15% total
```

### Monitoring & Health Checks

#### Health Endpoints

```bash
# Application health
curl http://localhost:8000/health

# Component status
curl http://localhost:8000/status

# Metrics (Prometheus format)
curl http://localhost:8000/metrics

# Strategy performance
curl http://localhost:8000/api/strategies/performance
```

#### Log Monitoring

```bash
# View live logs
tail -f logs/trading_bot.log

# Filter specific logs
tail -f logs/trading_bot.log | grep -E "(ERROR|CRITICAL)"

# Log analysis
grep "Order placed" logs/trading_bot.log | wc -l  # Count orders placed
```

#### Performance Monitoring

```bash
# Check system resource usage
htop  # Or top, if htop not available

# Monitor Redis performance
redis-cli INFO | grep -E "(connected_clients|used_memory|keyspace)"

# Check disk usage
df -h logs/ data/
```

### Trading Operations

#### Manual Trading

```python
# Place a manual order
order = await orchestrator.trading_engine.place_order(
    symbol="BTC/USDT",
    side="BUY",
    order_type="LIMIT",
    quantity=0.001,
    price=50000,
    strategy="manual"
)

# Check order status
order_status = orchestrator.trading_engine.get_order(order.order_id)
print(f"Order: {order_status.status}, Filled: {order_status.filled_quantity}")

# Cancel order
await orchestrator.trading_engine.cancel_order(order.order_id)
```

#### Portfolio Management

```python
# View portfolio
portfolio = await orchestrator.trading_engine.get_portfolio_summary()
print(f"Total value: ${portfolio['portfolio_value']:,.2f}")
print(f"Positions: {len(portfolio['positions'])}")
print(f"Unrealized P&L: ${portfolio['total_unrealized_pnl']:,.2f}")

# Position details
for symbol, position in portfolio['positions'].items():
    print(f"{symbol}: {position['quantity']} @ ${position['avg_entry_price']}")
```

### Strategy Development

#### Creating Custom Strategies

```python
from src.strategies.base.strategy import BaseStrategy
from decimal import Decimal

class MyCustomStrategy(BaseStrategy):
    """Custom trading strategy example."""

    def __init__(self, config):
        super().__init__(config)
        self.name = "my_custom_strategy"

    async def generate_signals(self, market_data):
        """Generate trading signals based on market data."""
        # Your strategy logic here
        if self.should_buy(market_data):
            return [{
                'action': 'BUY',
                'symbol': market_data['symbol'],
                'quantity': self.calculate_position_size(market_data),
                'confidence': 0.8
            }]

    def should_buy(self, market_data):
        """Determine if we should buy based on strategy rules."""
        # Implement your buy logic
        return market_data['rsi'] < 30 and market_data['volume'] > market_data['avg_volume']

# Register strategy
orchestrator.strategy_registry.register_strategy("my_strategy", MyCustomStrategy)
```

### Backup & Recovery

#### Automated Backups

```bash
# Database backup
cp data/trading_bot.db data/backup/trading_bot_$(date +%Y%m%d_%H%M%S).db

# Configuration backup
cp config/.env config/backup/.env.$(date +%Y%m%d_%H%M%S)

# Logs archival
tar -czf logs/backup/logs_$(date +%Y%m%d).tar.gz logs/*.log
```

#### Recovery Procedures

```bash
# Restore from backup
cp data/backup/trading_bot_20241201_120000.db data/trading_bot.db

# Restore configuration
cp config/backup/.env.20241201_120000 config/.env

# Clear corrupted data (if needed)
rm -rf data/* logs/*
redis-cli FLUSHALL
```

### Emergency Procedures

#### Emergency Stop

```bash
# Immediate shutdown (SIGTERM)
kill -TERM $(pgrep -f "python -m src")

# Force kill (SIGKILL) - use only if necessary
kill -KILL $(pgrep -f "python -m src")

# Docker emergency stop
docker-compose down --remove-orphans
```

#### Position Emergency Closure

```python
# Close all positions immediately
for symbol, position in orchestrator.position_manager.positions.items():
    await orchestrator.trading_engine.place_order(
        symbol=symbol,
        side="SELL",
        order_type="MARKET",
        quantity=position.quantity,
        strategy="emergency_close"
    )

# Cancel all pending orders
for order in orchestrator.trading_engine.get_active_orders():
    await orchestrator.trading_engine.cancel_order(order.order_id)
```

## API Reference

### Core Components

#### ApplicationOrchestrator
Main application controller that manages all components and their lifecycle.

**Key Methods:**
- `initialize()` - Initialize all components
- `start()` - Start the application
- `stop()` - Stop the application
- `shutdown()` - Graceful shutdown
- `get_status()` - Get comprehensive application status
- `get_component_summary()` - Get component health summary

#### TradingEngine
Core trading logic and order management system.

**Key Methods:**
- `place_order()` - Place a trading order
- `cancel_order()` - Cancel an existing order
- `get_portfolio_summary()` - Get portfolio information
- `get_order_statistics()` - Get trading statistics
- `get_active_orders()` - Get list of active orders

#### RiskManager
Risk assessment and position sizing system.

**Key Methods:**
- `validate_trade()` - Validate trade against risk limits
- `calculate_position_size()` - Calculate optimal position size
- `check_drawdown_limits()` - Check portfolio drawdown
- `get_risk_summary()` - Get comprehensive risk metrics

#### StrategyRegistry
Manages trading strategy loading and execution.

**Key Methods:**
- `register_strategy()` - Register a new strategy
- `enable_strategy()` - Enable a strategy
- `disable_strategy()` - Disable a strategy
- `list_strategies()` - List available strategies

### WebSocket Clients

#### MarketDataClient
Real-time market data streaming via WebSocket.

**Features:**
- Real-time price feeds for all supported symbols
- Order book depth updates
- Trade execution streams
- Automatic reconnection with exponential backoff

**Usage:**
```python
# Access via orchestrator
market_data = orchestrator.market_data_client

# Subscribe to symbol updates
await market_data.subscribe_symbol("BTC/USDT")

# Get latest price
price_data = market_data.get_latest_price("BTC/USDT")
print(f"BTC/USDT: ${price_data['price']}")
```

#### REST API Endpoints

If running with the optional web server:

```bash
# Health check
GET /health

# Application status
GET /status

# Component metrics
GET /metrics

# Strategy information
GET /api/strategies

# Portfolio data
GET /api/portfolio

# Trading history
GET /api/trades?limit=100&symbol=BTC/USDT

# Place manual order
POST /api/orders
{
  "symbol": "BTC/USDT",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": 0.001,
  "price": 50000
}
```

## Risk Management

- **Position Limits**: Maximum positions per strategy
- **Risk per Trade**: Percentage-based position sizing
- **Correlation Limits**: Maximum asset correlation
- **Stop Loss/Take Profit**: Automated exit strategies
- **Maximum Drawdown**: Portfolio protection

## Monitoring

### Logging

Structured logging with configurable levels:
- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning conditions
- **ERROR**: Error conditions

### Metrics

Prometheus metrics for:
- Trading performance
- Strategy effectiveness  
- Risk metrics
- System health

### Grafana Dashboards

Pre-configured dashboards for:
- Portfolio performance
- Strategy comparison
- Risk analysis
- System monitoring

## Deployment

### Production Checklist

- [ ] Configure production environment variables
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up backup strategies
- [ ] Implement circuit breakers
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS encryption

### Docker Production

```bash
# Production compose
docker-compose -f docker-compose.prod.yml up -d

# Health check
curl http://localhost:8000/health
```

## Contributing

### Development Setup

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/your-username/robinhood-crypto-bot.git
   cd robinhood-crypto-bot
   ```

2. **Set up development environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development tools
   ```

3. **Configure environment:**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your settings
   ```

4. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

5. **Development workflow:**
   ```bash
   # Create feature branch
   git checkout -b feature/your-feature-name

   # Make changes and test
   python -m src --no-live  # Test with mock data

   # Run tests
   pytest tests/

   # Format code
   black src/ tests/
   isort src/ tests/

   # Commit changes
   git add .
   git commit -m "Add your feature description"

   # Push and create PR
   git push origin feature/your-feature-name
   ```

### Code Standards

- **Black**: Code formatting (run `black src/ tests/`)
- **isort**: Import sorting (run `isort src/ tests/`)
- **mypy**: Type checking (run `mypy src/`)
- **flake8**: Linting (run `flake8 src/ tests/`)

### Git Workflow

1. **Feature Branches:** Create a new branch for each feature or bug fix
2. **Small Commits:** Make frequent, small commits with descriptive messages
3. **Testing:** Ensure all tests pass before pushing
4. **Pull Requests:** Create PR with clear description and testing instructions
5. **Code Review:** Address review comments promptly

### Uploading to Git

#### Option 1: Initialize New Repository

```bash
# Initialize git repository
git init

# Add remote origin (replace with your GitHub repository URL)
git remote add origin https://github.com/your-username/robinhood-crypto-bot.git

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Robinhood Crypto Trading Bot

- Interactive command-line interface
- Live price data from Robinhood API
- Trading management controls
- Comprehensive documentation
- Fallback to mock data for testing"

# Push to main branch
git branch -M main
git push -u origin main
```

#### Option 2: Push to Existing Repository

```bash
# If you already have a repository
git remote set-url origin https://github.com/your-username/robinhood-crypto-bot.git

# Push changes
git add .
git commit -m "Update: Add live price fetching and command line options

- Added --no-live flag for mock data only
- Integrated Robinhood API authentication
- Enhanced interactive commands
- Updated documentation"

git push origin main
```

#### GitHub Setup

1. **Create Repository:**
   - Go to [GitHub.com](https://github.com)
   - Click "New repository"
   - Name: `robinhood-crypto-bot`
   - Description: "A specialized cryptocurrency trading bot for Robinhood with real-time data and interactive controls"
   - Make it public or private as needed

2. **Add License:**
   ```bash
   # If not already present
   echo "MIT License" > LICENSE
   echo "" >> LICENSE
   echo "Copyright (c) 2024 Your Name" >> LICENSE
   echo "" >> LICENSE
   echo "Permission is hereby granted, free of charge, to any person obtaining a copy..." >> LICENSE
   ```

3. **Enable Issues and Wiki:**
   - In repository settings, enable Issues for bug reports
   - Enable Wiki for additional documentation

#### Version Control Best Practices

- **Regular Commits:** Commit frequently with meaningful messages
- **Branch Protection:** Protect main branch from direct pushes
- **Release Tags:** Use semantic versioning (v1.0.0, v1.1.0, etc.)
- **Changelog:** Maintain a CHANGELOG.md file for releases

### Security Notes

⚠️ **Important:** Never commit API tokens or sensitive credentials to version control.

- ✅ Safe: Environment variables, config files in .gitignore
- ❌ Unsafe: Hardcoded tokens, committed .env files

The .gitignore already excludes sensitive files like `config/.env`, `*.key`, and `robinhood_tokens.json`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this software.

Cryptocurrency trading involves substantial risk of loss and is not suitable for every investor. Past performance does not guarantee future results.
