# ⚙️ Configuration Guide

This document provides comprehensive configuration guidance for the Robinhood Crypto Trading Bot.

## Configuration Hierarchy

The bot uses a layered configuration system that merges settings from multiple sources:

1. **Default Configuration** (`config/default.yaml`) - Base settings
2. **Environment Variables** - Runtime overrides (highest priority)
3. **YAML Configuration Files** - Structured configuration
4. **Runtime Settings** - Dynamic adjustments (lowest priority)

## Environment Configuration

### Required Environment Variables

Copy the example environment file and configure your settings:

```bash
cp config/.env.example config/.env
```

**Essential Variables:**

```env
# Application Settings
APP_NAME=crypto-trading-bot
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# Robinhood API Configuration (Required for Production)
ROBINHOOD_API_KEY=your_api_key_here
ROBINHOOD_PUBLIC_KEY=your_base64_encoded_public_key
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

# API Performance Settings
API_TIMEOUT=30
API_RETRIES=3
API_RATE_LIMIT_PER_MINUTE=100
```

### Development vs Production

**Development Environment:**
```env
# Development settings
APP_NAME=crypto-trading-bot-dev
DEBUG=true
LOG_LEVEL=DEBUG

# Use sandbox/test credentials
ROBINHOOD_API_KEY=test_key
ROBINHOOD_PUBLIC_KEY=test_public_key
ROBINHOOD_SANDBOX=true

# Conservative trading settings
TRADING_ENABLED=false
MAX_POSITIONS=3
DEFAULT_RISK_PER_TRADE=0.005
```

**Production Environment:**
```env
# Production settings
APP_NAME=crypto-trading-bot-prod
DEBUG=false
LOG_LEVEL=INFO

# Real API credentials (institutional access required)
ROBINHOOD_API_KEY=your_production_key
ROBINHOOD_PUBLIC_KEY=your_production_public_key
ROBINHOOD_SANDBOX=false

# Production trading settings
TRADING_ENABLED=true
MAX_POSITIONS=10
DEFAULT_RISK_PER_TRADE=0.02

# Enhanced monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
SLACK_WEBHOOK_URL=your_slack_webhook
```

## YAML Configuration

### Application Configuration

**config/default.yaml:**
```yaml
# Application settings
app:
  name: "crypto-trading-bot"
  version: "1.0.0"
  debug: false
  log_level: "INFO"
  environment: "production"

# API configuration
api:
  base_url: "https://trading.robinhood.com"
  timeout: 30
  retries: 3
  rate_limit_per_minute: 1000
  connection_pool:
    limit: 100          # Total connection pool size
    limit_per_host: 10  # Max connections per host
    keepalive_timeout: 30
    ttl_dns_cache: 300
  compression: true
  keep_alive: true

# WebSocket configuration
websocket:
  ping_interval: 20
  timeout: 10
  max_reconnects: 5

# Trading configuration
trading:
  enabled: true
  max_positions: 10
  default_risk_per_trade: 0.02
  min_order_size: 10.0
  max_order_value: 10000.0
  supported_symbols:
    - "BTC/USD"
    - "ETH/USD"
    - "ADA/USD"
    - "SOL/USD"
    - "DOT/USD"
    - "AVAX/USD"
    - "MATIC/USD"
    - "LINK/USD"

# Strategy configuration
strategies:
  market_making:
    enabled: true
    spread_percentage: 0.001  # 0.1% spread
    order_refresh_time: 30    # seconds
    inventory_range: 0.1      # +/- 10% of target inventory

  momentum:
    enabled: false
    lookback_period: 20
    entry_threshold: 0.02

# Risk management
risk:
  max_portfolio_risk: 0.1
  max_position_risk: 0.02
  max_correlation: 0.7
  max_drawdown: 0.2
  stop_loss_default: 0.05
  take_profit_default: 0.15

# Database configuration
database:
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: ""
    decode_responses: true

# Logging configuration
logging:
  version: 1
  formatters:
    json:
      format: "%(asctime)s %(name)s %(levelname)s %(message)s"
      datefmt: "%Y-%m-%d %H:%M:%S"
  handlers:
    console:
      class: "logging.StreamHandler"
      formatter: "json"
      stream: "ext://sys.stdout"
    file:
      class: "logging.handlers.RotatingFileHandler"
      formatter: "json"
      filename: "logs/trading_bot.log"
      maxBytes: 10485760  # 10MB
      backupCount: 5
  loggers:
    crypto_trading_bot:
      level: "INFO"
      handlers: ["console", "file"]
      propagate: false

# Monitoring configuration
monitoring:
  prometheus_enabled: true
  grafana_enabled: true
  health_check_interval: 30
  metrics_port: 9090

# Notification settings
notifications:
  slack_enabled: false
  telegram_enabled: false
  email_enabled: false
```

### Environment-Specific Configuration

**config/development.yaml:**
```yaml
app:
  name: "crypto-trading-bot-dev"
  debug: true
  log_level: "DEBUG"
  environment: "development"

api:
  base_url: "https://sandbox.robinhood.com"
  timeout: 30
  retries: 3
  rate_limit_per_minute: 50

trading:
  enabled: false  # Disabled for development
  max_positions: 3
  default_risk_per_trade: 0.005  # Very conservative

strategies:
  market_making:
    enabled: false  # Disabled for development

risk:
  max_portfolio_risk: 0.03  # Very conservative
  max_drawdown: 0.1

logging:
  level: "DEBUG"
  handlers: ["console"]  # Console only for development

monitoring:
  prometheus_enabled: false
  grafana_enabled: false
```

**config/production.yaml:**
```yaml
app:
  name: "crypto-trading-bot-prod"
  debug: false
  log_level: "INFO"
  environment: "production"

api:
  base_url: "https://trading.robinhood.com"
  timeout: 10
  retries: 5
  rate_limit_per_minute: 1000

trading:
  enabled: true
  max_positions: 15
  default_risk_per_trade: 0.02

strategies:
  market_making:
    enabled: true
    spread_percentage: 0.001
    order_refresh_time: 30

risk:
  max_portfolio_risk: 0.1
  max_drawdown: 0.2

monitoring:
  prometheus_enabled: true
  grafana_enabled: true
  health_check_interval: 30

notifications:
  slack_enabled: true
  email_enabled: true
```

## Configuration Management

### Using the Setup Script

The easiest way to configure the bot is using the interactive setup script:

```bash
# Interactive setup
python setup_credentials.py

# Test existing configuration
python setup_credentials.py --test

# Get help
python setup_credentials.py --help
```

### Manual Configuration

**1. Environment Variables:**
```bash
# Set environment variables directly
export ROBINHOOD_API_KEY="your_api_key"
export ROBINHOOD_PUBLIC_KEY="your_public_key"
export ROBINHOOD_SANDBOX=false

# Run the bot
python -m src
```

**2. Configuration Files:**
```bash
# Create custom configuration
cp config/default.yaml config/my-config.yaml

# Edit the file with your settings
nano config/my-config.yaml

# Run with custom configuration
python -m src --config config/my-config.yaml
```

**3. Runtime Configuration:**
```python
# Modify configuration at runtime
from src.core.config import get_settings

settings = get_settings()
settings.trading.enabled = False
settings.risk.max_portfolio_risk = 0.05
```

## Advanced Configuration

### Database Configuration

**Redis Configuration:**
```env
# Basic Redis
REDIS_URL=redis://localhost:6379/0

# Redis with password
REDIS_URL=redis://:password@localhost:6379/0

# Redis cluster
REDIS_URL=redis://host1:6379,host2:6379,host3:6379/0

# Redis with SSL
REDIS_URL=rediss://localhost:6380/0
```

**YAML Redis Configuration:**
```yaml
database:
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: ""
    decode_responses: true
    socket_timeout: 5
    socket_connect_timeout: 5
    retry_on_timeout: true
    max_connections: 20
```

### API Configuration

**Connection Pooling:**
```yaml
api:
  connection_pool:
    limit: 100                    # Total connections
    limit_per_host: 10           # Per host limit
    keepalive_timeout: 30        # Keep-alive timeout
    ttl_dns_cache: 300          # DNS cache TTL
    use_dns_cache: true
    fingerprint: null           # SSL fingerprint
    enable_cleanup_closed: true
```

**Rate Limiting:**
```yaml
api:
  rate_limiting:
    global:
      requests_per_minute: 1000
      burst_size: 10
    trading:
      requests_per_minute: 100
      burst_size: 5
    market_data:
      requests_per_minute: 500
      burst_size: 20
```

### Strategy Configuration

**Market Making Strategy:**
```yaml
strategies:
  market_making:
    enabled: true
    spread_percentage: 0.001      # 0.1% spread
    order_refresh_time: 30        # Refresh orders every 30s
    inventory_target: 0.5         # Target 50% inventory
    inventory_range: 0.1          # +/- 10% range
    max_order_size: 1000.0        # Maximum order size
    min_order_size: 10.0          # Minimum order size
    price_bands: 100              # Number of price bands
    skew_enabled: true            # Enable inventory skewing
    hedging_enabled: false        # Enable hedging
```

**Momentum Strategy:**
```yaml
strategies:
  momentum:
    enabled: true
    lookback_period: 20           # Lookback for momentum calculation
    entry_threshold: 0.02         # Entry threshold (2%)
    exit_threshold: 0.01          # Exit threshold (1%)
    rsi_period: 14                # RSI calculation period
    rsi_overbought: 70            # RSI overbought level
    rsi_oversold: 30              # RSI oversold level
    volume_filter: 1.5            # Volume must be 1.5x average
    stop_loss: 0.05               # 5% stop loss
    take_profit: 0.10             # 10% take profit
```

### Risk Configuration

**Portfolio Risk:**
```yaml
risk:
  max_portfolio_risk: 0.1       # 10% max portfolio risk
  max_sector_risk: 0.3          # 30% max sector risk
  max_single_position: 0.05     # 5% max single position
  max_correlation: 0.7          # 70% max correlation
  max_drawdown: 0.2            # 20% max drawdown
  recovery_factor: 2.0         # Recovery factor for position sizing
```

**Dynamic Risk Adjustment:**
```python
# Adjust risk based on market conditions
def adjust_risk_for_volatility(current_volatility: float, base_risk: float) -> float:
    """Adjust risk based on market volatility."""
    if current_volatility > 0.5:  # High volatility
        return base_risk * 0.5    # Reduce risk by 50%
    elif current_volatility < 0.2:  # Low volatility
        return base_risk * 1.2    # Increase risk by 20%
    else:
        return base_risk

# Apply dynamic risk adjustment
current_volatility = calculate_market_volatility()
adjusted_risk = adjust_risk_for_volatility(current_volatility, base_risk)
```

### Monitoring Configuration

**Prometheus Metrics:**
```yaml
monitoring:
  prometheus:
    enabled: true
    port: 9090
    path: "/metrics"
    collect_per_method: true
    buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

  grafana:
    enabled: true
    port: 3000
    admin_password: "secure_password"
    dashboards:
      - name: "Trading Performance"
        source: "dashboards/trading.json"
      - name: "Risk Metrics"
        source: "dashboards/risk.json"
```

**Health Checks:**
```yaml
monitoring:
  health_checks:
    enabled: true
    interval: 30                  # Check every 30 seconds
    timeout: 10                   # 10 second timeout
    endpoints:
      - name: "API Connectivity"
        url: "https://trading.robinhood.com/health"
        expected_status: 200
      - name: "Database Connectivity"
        type: "redis"
        expected_response: "PONG"
      - name: "Strategy Health"
        type: "component"
        component: "strategy_registry"
```

### Notification Configuration

**Slack Integration:**
```env
# Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=trading-alerts
SLACK_USERNAME=trading-bot
```

**Email Configuration:**
```env
# Email notifications
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENTS=alerts@yourcompany.com
```

**Telegram Configuration:**
```env
# Telegram notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**YAML Notification Settings:**
```yaml
notifications:
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/..."
    channel: "#trading-alerts"
    username: "Trading Bot"
    events:
      - order_filled
      - risk_breach
      - system_error

  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "bot@yourcompany.com"
    password: "app_password"
    recipients: ["admin@yourcompany.com"]
    events:
      - system_error
      - risk_breach

  telegram:
    enabled: true
    bot_token: "your_bot_token"
    chat_id: "your_chat_id"
    events:
      - order_filled
      - position_closed
```

## Configuration Validation

### Validation Rules

The configuration system includes built-in validation:

```python
from pydantic import BaseModel, validator
from typing import List, Optional

class TradingConfig(BaseModel):
    """Trading configuration with validation."""

    enabled: bool
    max_positions: int
    default_risk_per_trade: float
    supported_symbols: List[str]

    @validator('max_positions')
    def validate_max_positions(cls, v):
        if not 1 <= v <= 100:
            raise ValueError('max_positions must be between 1 and 100')
        return v

    @validator('default_risk_per_trade')
    def validate_risk_per_trade(cls, v):
        if not 0.001 <= v <= 0.1:
            raise ValueError('default_risk_per_trade must be between 0.001 and 0.1')
        return v

    @validator('supported_symbols')
    def validate_symbols(cls, v):
        if len(v) == 0:
            raise ValueError('At least one symbol must be supported')
        return v
```

### Configuration Testing

```bash
# Test configuration loading
python -c "
from src.core.config import initialize_config, get_settings
settings = initialize_config()
print('✅ Configuration loaded successfully')
print(f'API Key configured: {settings.robinhood.api_key is not None}')
print(f'Trading enabled: {settings.trading.enabled}')
"

# Validate configuration schema
python -c "
from src.core.config.settings import Settings
try:
    settings = Settings()
    print('✅ Configuration schema is valid')
except Exception as e:
    print(f'❌ Configuration schema error: {e}')
"
```

## Environment-Specific Setup

### Docker Configuration

**Docker Environment:**
```env
# Docker-specific settings
REDIS_URL=redis://redis:6379/0
DATABASE_URL=sqlite:///data/trading_bot.db

# API settings for container
API_BASE_URL=https://trading.robinhood.com
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  trading-bot:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ROBINHOOD_API_KEY=${ROBINHOOD_API_KEY}
      - ROBINHOOD_PUBLIC_KEY=${ROBINHOOD_PUBLIC_KEY}
      - ROBINHOOD_SANDBOX=${ROBINHOOD_SANDBOX}
    depends_on:
      - redis
      - prometheus
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

volumes:
  redis_data:
```

### Kubernetes Configuration

**ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-bot-config
data:
  config.yaml: |
    app:
      name: "crypto-trading-bot"
      environment: "production"
    trading:
      enabled: true
      max_positions: 10
    risk:
      max_portfolio_risk: 0.1
```

**Secret:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: trading-bot-secrets
type: Opaque
data:
  robinhood-api-key: <base64-encoded-api-key>
  robinhood-public-key: <base64-encoded-public-key>
  redis-password: <base64-encoded-redis-password>
```

## Best Practices

### Security

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Rotate API keys** regularly
4. **Monitor access logs** for suspicious activity
5. **Use HTTPS** for all API communications

### Performance

1. **Set appropriate timeouts** for your network
2. **Configure connection pooling** based on expected load
3. **Monitor resource usage** in production
4. **Use caching** for frequently accessed data
5. **Batch operations** when possible

### Risk Management

1. **Start conservative** and adjust based on performance
2. **Monitor correlation** between positions
3. **Set realistic expectations** for returns
4. **Regular portfolio reviews** and rebalancing
5. **Implement circuit breakers** for extreme conditions

### Monitoring

1. **Set up comprehensive logging** from day one
2. **Monitor key metrics** in real-time
3. **Set up alerts** for critical events
4. **Regular backup** of configuration and data
5. **Performance testing** before production deployment

## Troubleshooting Configuration

### Common Issues

**Configuration Not Loading:**
```bash
# Check environment variables
env | grep ROBINHOOD

# Test configuration loading
python -c "
from src.core.config import initialize_config
try:
    settings = initialize_config()
    print('✅ Configuration loaded')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

**Redis Connection Issues:**
```env
# Check Redis connectivity
REDIS_URL=redis://localhost:6379/0

# Test Redis connection
python -c "
import redis
try:
    r = redis.from_url('redis://localhost:6379/0')
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis error: {e}')
"
```

**API Configuration Issues:**
```python
# Test API configuration
from src.core.api.robinhood.client import RobinhoodClient

async def test_api_config():
    try:
        async with RobinhoodClient(sandbox=True) as client:
            health = await client.health_check()
            print(f"API Health: {health}")
    except Exception as e:
        print(f"API Error: {e}")

# Run test
import asyncio
asyncio.run(test_api_config())
```

## Configuration Migration

### Upgrading Configuration

When upgrading the bot, follow these steps:

1. **Backup current configuration:**
```bash
cp config/.env config/.env.backup
cp config/default.yaml config/default.yaml.backup
```

2. **Review new configuration options:**
```bash
# Check for new configuration options
git diff config/.env.example
git diff config/default.yaml
```

3. **Update configuration files:**
```bash
# Update environment file
cp config/.env.example config/.env
# Edit with your previous settings

# Update YAML configuration
cp config/default.yaml config/default.yaml.new
# Merge your custom settings
```

4. **Test configuration:**
```bash
python -c "
from src.core.config import initialize_config
settings = initialize_config()
print('✅ Configuration test successful')
"
```

This comprehensive configuration guide should help you set up and optimize the trading bot for your specific requirements and environment.