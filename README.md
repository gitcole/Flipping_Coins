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
- 🔑 **Simplified Scripts**: Ready-to-use trading scripts for common operations

## 📁 Project Files

| File | Description |
|------|-------------|
| `src/` | Main application source code |
| `crypto_trading_bot.py` | Basic trading bot with core functionality |
| `crypto_trading_bot_enhanced.py` | **RECOMMENDED** - Enhanced bot with error handling & rate limiting |
| `buy_5_sol.py`, `buy_by_dollar_amount.py`, `check_order_status.py` | Custom trading scripts |
| `config/` | Configuration files |
| `tests/` | Test suite |

## 🚀 Quick Start

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

# Or run the simplified bot
python crypto_trading_bot_enhanced.py
```

## 🔑 API Credentials Setup

⚠️ **IMPORTANT:** Your API credentials are stored in `.env` file (not tracked by Git)

To configure your credentials:

1. Create a `.env` file in the project root
2. Add your Robinhood API credentials:
```bash
RH_API_KEY=your-api-key-here
RH_BASE64_PRIVATE_KEY=your-private-key-here
RH_PUBLIC_KEY=your-public-key-here
RH_ACCOUNT_NUMBER=your-account-number
```

3. **NEVER commit the `.env` file to Git** - it's already in `.gitignore`

## 💰 Account Info

- Your account information will be loaded from the `.env` file
- Run the bot to see your current holdings and buying power

## ⚡ Enhanced Bot Features

The `crypto_trading_bot_enhanced.py` includes:

### 1. **Rate Limiting**
- Automatically tracks API requests
- Prevents hitting the 100 req/min or 300 burst limit
- Shows remaining capacity

### 2. **Error Handling**
- Automatic retries for transient errors
- Handles timeouts gracefully
- Specific error types for debugging

### 3. **Logging**
- Timestamps on all requests
- Different log levels (INFO, WARNING, ERROR)
- Request counting

### 4. **Statistics**
```python
stats = api.get_rate_limit_stats()
# Returns:
# {
#   "requests_last_minute": 5,
#   "remaining_capacity": 295,
#   "total_requests_made": 15
# }
```

## 📊 Available API Functions

### Account & Holdings
- `get_account()` - Get account information
- `get_holdings()` - Get your crypto holdings
- `get_holdings("BTC", "ETH")` - Get specific holdings

### Market Data
- `get_best_bid_ask("BTC-USD")` - Get current best bid/ask prices
- `get_trading_pairs("BTC-USD")` - Get trading pair info
- `get_estimated_price("BTC-USD", "ask", "0.001")` - Get estimated price for a trade
  - Use `"ask"` when buying
  - Use `"bid"` when selling

### Orders
- `place_order(...)` - Place a buy/sell order
- `get_orders()` - Get all your orders
- `get_order(order_id)` - Get specific order details
- `cancel_order(order_id)` - Cancel an order

## 💡 Example Usage

### Basic Usage
```python
from crypto_trading_bot_enhanced import CryptoAPITrading
import json

# Initialize bot
api = CryptoAPITrading(verbose=True)

# Get BTC price
btc_price = api.get_best_bid_ask("BTC-USD")
print(json.dumps(btc_price, indent=2))

# Get your holdings
holdings = api.get_holdings()
print(json.dumps(holdings, indent=2))

# Get estimated price for buying 0.001 BTC
estimated = api.get_estimated_price("BTC-USD", "ask", "0.001")
print(json.dumps(estimated, indent=2))

# CAUTION: Place a real order (this will execute!)
# order = api.place_order(
#     str(uuid.uuid4()),
#     "buy",
#     "market",
#     "BTC-USD",
#     {"asset_quantity": "0.0001"}
# )
```

### Async Usage
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

## 🔒 Rate Limits

- **Standard:** 100 requests/minute
- **Burst:** 300 requests/minute
- **Timestamp validity:** 30 seconds

The enhanced bot automatically manages these limits for you!

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

## 🛠️ Installation

### System Requirements

- **Python 3.11+** - Core runtime environment
- **Redis Server** - Caching and session storage
- **Git** - Version control (for development)
- **Docker** - Optional, for containerized deployment

### Hardware Requirements

**Minimum:** 2 CPU cores, 4 GB RAM, 10 GB storage
**Recommended:** 4+ CPU cores, 8+ GB RAM, 50 GB SSD storage

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

## ⚠️ Important Notes

### Before Trading:
1. **Test with small amounts first!**
2. Orders are REAL and will execute immediately
3. Market orders execute at current market price
4. Always check your buying power before placing orders

### Timestamp Expiry:
- API signatures expire after 30 seconds
- The bot generates fresh timestamps for each request
- Never reuse old signatures

### Best Practices:
- Use the enhanced bot for production
- Always use `str(uuid.uuid4())` for unique order IDs
- Check order status after placing
- Implement your own risk management

## 🛠️ Troubleshooting

### Connection Issues:
1. Verify API key is active in Robinhood portal
2. Check that public/private keys match
3. Ensure system time is accurate (for timestamps)

### Rate Limit Errors:
- The enhanced bot handles this automatically
- Wait 60 seconds if you hit the burst limit

### Authentication Failures:
- Regenerate keys using `generate_keys.py`
- Delete and recreate API credential in portal
- Ensure you registered the PUBLIC key, not private

## 🏥 Health Checks

### Application Health
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", "components": {...}}
```

### API Connectivity
```bash
python -c "
from src.core.api.client import ExchangeAPIClient
client = ExchangeAPIClient('your_api_key', 'your_secret')
print('API Connection:', 'OK' if client.test_connection() else 'FAILED')
"
```

### Strategy Loading
```bash
python -c "
from src.strategies.registry import StrategyRegistry
registry = StrategyRegistry()
strategies = registry.list_strategies()
print(f'Loaded strategies: {strategies}')
"
```

## 🎯 Next Steps

1. **Test the bot** with the example code
2. **Build your strategy** in the main() function
3. **Implement risk management** (stop-loss, take-profit, etc.)
4. **Add monitoring** and alerting
5. **Backtest** your strategy before going live

## 🛡️ Risk Management

- **Position Limits**: Maximum positions per strategy
- **Risk per Trade**: Percentage-based position sizing
- **Correlation Limits**: Maximum asset correlation
- **Stop Loss/Take Profit**: Automated exit strategies
- **Maximum Drawdown**: Portfolio protection

## 📡 API Reference

For full API documentation, visit:
https://docs.robinhood.com/crypto/trading-api

## 🚀 Deployment

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

## 🤝 Contributing

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

### Code Standards

- **Black**: Code formatting (run `black src/ tests/`)
- **isort**: Import sorting (run `isort src/ tests/`)
- **mypy**: Type checking (run `mypy src/`)
- **flake8**: Linting (run `flake8 src/ tests/`)

## ⚡ Rate Limits

- **Standard:** 100 requests/minute
- **Burst:** 300 requests/minute
- **Timestamp validity:** 30 seconds

The enhanced bot automatically manages these limits for you!

## ✅ Setup Complete!

All systems are operational. Your bot is ready to trade!

**Current Status:**
- ✅ API credentials configured
- ✅ Connection verified
- ✅ Error handling enabled
- ✅ Rate limiting active
- ✅ All endpoints tested

Happy trading! 🚀

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this software.

Cryptocurrency trading involves substantial risk of loss and is not suitable for every investor. Past performance does not guarantee future results.
