# 🔌 API Reference

This document provides comprehensive API documentation for the Robinhood Crypto Trading Bot.

## Core Components

### ApplicationOrchestrator

Main application controller that manages all components and their lifecycle.

**Key Methods:**
- `initialize()` - Initialize all components
- `start()` - Start the application
- `stop()` - Stop the application
- `shutdown()` - Graceful shutdown
- `get_status()` - Get comprehensive application status
- `get_component_summary()` - Get component health summary

### TradingEngine

Core trading logic and order management system.

**Key Methods:**
- `place_order()` - Place a trading order
- `cancel_order()` - Cancel an existing order
- `get_portfolio_summary()` - Get portfolio information
- `get_order_statistics()` - Get trading statistics
- `get_active_orders()` - Get list of active orders

### RiskManager

Risk assessment and position sizing system.

**Key Methods:**
- `validate_trade()` - Validate trade against risk limits
- `calculate_position_size()` - Calculate optimal position size
- `check_drawdown_limits()` - Check portfolio drawdown
- `get_risk_summary()` - Get comprehensive risk metrics

### StrategyRegistry

Manages trading strategy loading and execution.

**Key Methods:**
- `register_strategy()` - Register a new strategy
- `enable_strategy()` - Enable a strategy
- `disable_strategy()` - Disable a strategy
- `list_strategies()` - List available strategies

## API Clients

### RobinhoodClient

High-performance Robinhood API client with advanced features.

**Features:**
- Connection pooling (100 total connections, 10 per host)
- DNS caching (300s TTL) to reduce lookup times
- Keep-alive connections (30s timeout) for connection reuse
- Request compression (gzip, deflate) for reduced bandwidth
- Exponential backoff for retries (up to 30s max delay)
- Automatic rate limiting with token buckets

**Initialization:**

```python
from src.core.api.robinhood.client import RobinhoodClient

# Sandbox mode (for testing)
client = RobinhoodClient(sandbox=True)

# Production mode (requires institutional access)
client = RobinhoodClient(sandbox=False)

# With custom configuration
from src.core.api.robinhood.client import RobinhoodAPIConfig
config = RobinhoodAPIConfig(sandbox=False)
client = RobinhoodClient(config=config)
```

**Usage:**

```python
import asyncio

async def main():
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

        # Check order status
        order_status = await client.get_order(order.id)
        print(f"Order status: {order_status['state']}")

asyncio.run(main())
```

**Rate Limiting:**

The client automatically handles rate limiting with different buckets:
- **Global**: 100 requests/minute (all requests)
- **Trading**: 30 requests/minute (orders, positions)
- **Market Data**: 200 requests/minute (quotes, prices)
- **Account**: 20 requests/minute (account info, balances)

## Authentication

### RobinhoodSignatureAuth

Handles signature-based authentication for Robinhood API.

**Initialization:**

```python
from src.core.api.robinhood.auth import RobinhoodSignatureAuth

# Using private key
auth = RobinhoodSignatureAuth(
    api_key='your_api_key',
    private_key_b64='your_base64_encoded_private_key',
    sandbox=False
)

# Using public key (recommended)
auth = RobinhoodSignatureAuth(
    api_key='your_api_key',
    public_key_b64='your_base64_encoded_public_key',
    sandbox=False
)
```

**Methods:**

- `is_authenticated()` - Check if authentication is valid
- `get_api_key()` - Get the API key
- `get_public_key()` - Get the public key
- `get_private_key()` - Get the private key (if available)
- `get_auth_info()` - Get comprehensive authentication information

## Error Handling

### Exception Types

The API uses specific exception types for better error handling:

```python
from src.core.api.exceptions import (
    CryptoTradingError,
    CryptoMarketDataError,
    CryptoAuthenticationError,
    CryptoRateLimitError,
    CryptoNetworkError
)

try:
    # API call that might fail
    data = await client.get_quotes(["INVALID_SYMBOL"])
except CryptoMarketDataError as e:
    print(f"Market data error: {e}")
    # Handle gracefully - maybe fallback to different symbols
except CryptoRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Handle rate limiting - wait and retry
except CryptoNetworkError as e:
    print(f"Network error: {e}")
    # Handle network issues - retry with backoff
```

### Error Response Format

All API errors follow a consistent format:

```python
{
    "error": {
        "code": "INVALID_SYMBOL",
        "message": "Symbol not found or not supported",
        "details": {
            "symbols": ["INVALID_SYMBOL"],
            "supported_symbols": ["BTC", "ETH", "DOGE"]
        }
    }
}
```

## WebSocket API

### MarketDataClient

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
await market_data.subscribe_symbol("BTC/USD")

# Get latest price
price_data = market_data.get_latest_price("BTC/USD")
print(f"BTC/USD: ${price_data['price']}")

# Get price history
history = market_data.get_price_history("BTC/USD", limit=100)
```

**Events:**

The client emits various events for real-time updates:

```python
@market_data.on('price_update')
def on_price_update(data):
    symbol = data['symbol']
    price = data['price']
    change = data['change_24h']
    print(f"{symbol}: ${price} ({change:+.2%})")

@market_data.on('orderbook_update')
def on_orderbook_update(data):
    symbol = data['symbol']
    bids = data['bids']  # Top bid levels
    asks = data['asks']  # Top ask levels
    print(f"Orderbook updated for {symbol}")
```

## REST API Endpoints

If running with the optional web server:

### Health & Status

```bash
# Application health
GET /health
# Returns: {"status": "healthy", "components": {...}}

# Component status
GET /status
# Returns: {"market_data": "connected", "trading": "active", ...}

# Metrics (Prometheus format)
GET /metrics
# Returns: Prometheus-formatted metrics
```

### Trading API

```bash
# Strategy information
GET /api/strategies
# Returns: List of available and active strategies

# Portfolio data
GET /api/portfolio
# Returns: Current portfolio positions and P&L

# Trading history
GET /api/trades?limit=100&symbol=BTC/USD
# Returns: Recent trades with filtering options

# Place manual order
POST /api/orders
Content-Type: application/json

{
  "symbol": "BTC/USD",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": 0.001,
  "price": 50000
}
```

### Risk Management API

```bash
# Risk metrics
GET /api/risk
# Returns: Current risk levels and limits

# Update risk settings
POST /api/risk
Content-Type: application/json

{
  "max_portfolio_risk": 0.15,
  "max_position_risk": 0.03
}
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ROBINHOOD_API_KEY` | Robinhood API key | Yes | - |
| `ROBINHOOD_PUBLIC_KEY` | Robinhood public key (base64) | Yes | - |
| `ROBINHOOD_SANDBOX` | Use sandbox environment | No | `true` |
| `API_TIMEOUT` | Request timeout in seconds | No | `30` |
| `API_RETRIES` | Number of retry attempts | No | `3` |

### YAML Configuration

```yaml
api:
  rate_limit_per_minute: 1000
  timeout_seconds: 30
  retry_attempts: 3
  connection_pool:
    limit: 100
    limit_per_host: 10
    keepalive_timeout: 30
    ttl_dns_cache: 300
  compression: true
  keep_alive: true

websocket:
  ping_interval: 20
  timeout: 10
  max_reconnects: 5
```

## Performance Monitoring

### Metrics

The API client provides built-in performance monitoring:

```python
# Get client statistics
stats = client.get_stats()
print(f"Requests: {stats['request_count']}")
print(f"Errors: {stats['error_count']}")
print(f"Success rate: {1 - stats['error_rate']:.2%}")
print(f"Average response time: {stats['avg_response_time']:.2f}s")
```

### Logging

All API calls are logged with structured logging:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "module": "robinhood_client",
  "message": "API request completed",
  "request": {
    "method": "GET",
    "endpoint": "/crypto/quotes",
    "symbols": ["BTC", "ETH"],
    "response_time": 0.234
  },
  "response": {
    "status_code": 200,
    "data_points": 2
  }
}
```

## Best Practices

### Error Handling

Always use specific exception types for better error handling:

```python
try:
    await client.place_order(order_request)
except CryptoTradingError as e:
    # Handle trading-specific errors
    if e.code == "INSUFFICIENT_FUNDS":
        # Handle insufficient funds
        pass
    elif e.code == "INVALID_ORDER":
        # Handle invalid order parameters
        pass
except CryptoRateLimitError:
    # Handle rate limiting - implement retry with backoff
    await asyncio.sleep(60)  # Wait 1 minute
    await retry_request()
```

### Rate Limiting

The client handles rate limiting automatically, but you should still be mindful:

```python
# Good - batch requests when possible
symbols = ["BTC", "ETH", "DOGE", "ADA", "SOL"]
quotes = await client.get_quotes(symbols)

# Avoid - making too many individual requests
for symbol in symbols:
    quote = await client.get_quote(symbol)  # Rate limited!
```

### Connection Management

Always use the context manager for proper resource cleanup:

```python
# Good
async with RobinhoodClient(sandbox=True) as client:
    data = await client.get_quotes(["BTC", "ETH"])

# Avoid - manual cleanup required
client = RobinhoodClient(sandbox=True)
try:
    data = await client.get_quotes(["BTC", "ETH"])
finally:
    await client.close()  # Manual cleanup
```

## Migration Guides

### From Old API

If migrating from the old API implementation:

1. **Import Changes:**
   ```python
   # Old
   from src.core.api.robinhood.crypto import RobinhoodCrypto

   # New
   from src.core.api.robinhood.client import RobinhoodClient
   ```

2. **Authentication:**
   ```python
   # Old - manual token management
   client = RobinhoodCrypto(token="your_token")

   # New - automatic from settings
   async with RobinhoodClient(sandbox=True) as client:
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

   # New - specific exceptions
   try:
       result = await client.get_quotes(symbols)
   except CryptoMarketDataError as e:
       print(f"Market data error: {e}")
   ```

## Troubleshooting

### Common Issues

#### Authentication Problems

```python
# Check authentication status
auth_info = client.auth.get_auth_info()
print(f"Auth type: {auth_info['auth_type']}")
print(f"Authenticated: {client.auth.is_authenticated()}")

# For signature auth issues, verify keys
if auth_info['auth_type'] == 'signature':
    print(f"API key: {auth_info['api_key'][:20]}...")
    print(f"Public key: {auth_info['public_key'][:50]}...")
```

#### Rate Limiting

```python
# Check current rate limit status
stats = client.get_stats()
print(f"Requests/min: {stats['requests_per_minute']}")
print(f"Remaining: {stats['remaining_requests']}")

# If rate limited, wait before retrying
if stats['remaining_requests'] < 10:
    await asyncio.sleep(60)  # Wait 1 minute
```

#### Network Issues

```python
# Enable debug logging to see network issues
import logging
logging.getLogger('aiohttp').setLevel(logging.DEBUG)

# Check connection health
health = await client.health_check()
print(f"API reachable: {health['api_reachable']}")
print(f"Response time: {health['response_time']}s")
```

## Support

For API-related issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Review the application logs
3. Test individual components
4. Contact Robinhood institutional support for API issues