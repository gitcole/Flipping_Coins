# Robinhood Crypto API Setup Guide

## ⚠️ IMPORTANT NOTICE

**Robinhood has significantly changed their API access policy. Please read this entire guide carefully before proceeding.**

## Current Robinhood API Status

### Public API Deprecation
- **Robinhood's public API has been deprecated** and is no longer available for general use
- **Individual developers cannot access the Robinhood API** through previous methods
- The API is now **restricted to institutional/partner access only**

### What's Required for API Access

To use the Robinhood Crypto API, you need **one** of the following:

1. **Institutional Account**: Registered investment advisor, hedge fund, or similar institutional entity
2. **Partner Program**: Approved partnership with Robinhood's institutional team
3. **Enterprise Access**: Large-scale trading operations with approved API access

## Credential Requirements

### For Institutional/Partner Access

If you have institutional access, you'll need these credentials:

```env
# Required Environment Variables
ROBINHOOD_CLIENT_ID=your_institutional_client_id
ROBINHOOD_CLIENT_SECRET=your_institutional_client_secret
ROBINHOOD_API_TOKEN=your_personal_api_token
ROBINHOOD_REDIRECT_URI=http://localhost:8080
ROBINHOOD_SANDBOX=false
```

### For Testing/Development (No Live Trading)

For testing the bot without live trading, you can use placeholder credentials:

```env
# Development/Test Environment Variables
ROBINHOOD_CLIENT_ID=test_client_id
ROBINHOOD_CLIENT_SECRET=test_client_secret
ROBINHOOD_API_TOKEN=test_token
ROBINHOOD_REDIRECT_URI=http://localhost:8080
ROBINHOOD_SANDBOX=true
```

## Credential Limitations and Restrictions

### API Access Limitations

1. **No Public Access**: Individual developers cannot obtain API credentials
2. **Institutional Only**: Only registered institutions can access the API
3. **Approval Required**: All applications are subject to Robinhood's approval process
4. **Compliance Requirements**: Must meet regulatory and compliance standards

### Rate Limiting

The Robinhood API implements strict rate limiting:

- **Global Rate Limit**: 100 requests per minute across all endpoints
- **Trading Endpoints**: 30 requests per minute for orders and positions
- **Market Data**: 200 requests per minute for quotes and prices
- **Account Info**: 20 requests per minute for account details

### Sandbox vs Production

#### Sandbox Environment (`ROBINHOOD_SANDBOX=true`)
- **Purpose**: Testing and development only
- **Data**: Simulated or delayed market data
- **Orders**: No real money, no market impact
- **Rate Limits**: More permissive than production

#### Production Environment (`ROBINHOOD_SANDBOX=false`)
- **Purpose**: Live trading with real money
- **Data**: Real-time market data
- **Orders**: Execute real trades
- **Rate Limits**: Strict enforcement
- **Requirements**: Institutional approval required

### Token Management

#### Access Token Lifespan
- **Expiration**: Tokens expire after 1 hour (3600 seconds)
- **Auto-refresh**: The bot automatically refreshes tokens when needed
- **Storage**: Tokens are stored securely in `.robinhood_tokens.json`

#### Refresh Token Behavior
- **Automatic**: Refresh tokens are managed automatically
- **Security**: Stored encrypted and rotated regularly
- **Expiration**: Refresh tokens have longer lifespans but do expire

### Account Requirements

#### Robinhood Account Setup
1. **Crypto Trading Enabled**: Must have crypto trading enabled in your Robinhood app
2. **Verified Identity**: Account must be fully verified and approved
3. **Sufficient Balance**: Need funds for trading (minimum order sizes apply)
4. **Approved Jurisdiction**: Must be in an approved region for crypto trading

#### Institutional Account Requirements
1. **Business Entity**: Must be a registered business (LLC, corporation, etc.)
2. **Regulatory Compliance**: Must comply with financial regulations
3. **Minimum Assets**: May have minimum asset requirements
4. **Operational History**: Established track record may be required

### Geographic Restrictions

#### Supported Regions
- **Primary**: United States (50 states)
- **Limited**: US territories (Puerto Rico, US Virgin Islands)
- **Excluded**: International users (except approved institutions)

#### State-Specific Requirements
- Some states may have additional licensing requirements
- Certain states may restrict crypto trading activities
- Institutional accounts may have different requirements by state

### Trading Limitations

#### Order Types
- **Supported**: Market, limit orders
- **Not Supported**: Stop-loss, stop-limit, trailing stops (via API)
- **Minimum Sizes**: Vary by cryptocurrency (typically $1.00 minimum)

#### Position Limits
- **Maximum Positions**: Configurable in bot settings (default: 5)
- **Risk Limits**: Portfolio and per-trade risk management
- **Correlation Limits**: Maximum correlation between positions

### Security Restrictions

#### Authentication Methods
- **OAuth 2.0**: Required for all API access
- **PKCE**: Proof Key for Code Exchange for enhanced security
- **HTTPS Only**: All API communication must use HTTPS
- **No API Keys**: Does not use traditional API key/secret pairs

#### Security Best Practices
1. **Token Rotation**: Regular rotation of access tokens
2. **Secure Storage**: Credentials stored in environment variables
3. **Network Security**: API calls made over encrypted connections
4. **Access Logging**: All API access is logged for security monitoring

## Setup Instructions

### Option 1: Interactive Setup (Recommended)

The easiest way to configure your credentials is using the provided setup script:

```bash
# Run the interactive setup script
python setup_credentials.py
```

This script will:
- Guide you through credential entry
- Validate your configuration
- Set up environment variables
- Test the connection (if credentials are valid)

### Option 2: Manual Configuration

If you prefer to set up credentials manually:

1. **Copy the environment template:**
   ```bash
   cp config/.env.example config/.env
   ```

2. **Edit the configuration file:**
   ```bash
   nano config/.env  # or use your preferred editor
   ```

3. **Add your credentials:**
   ```env
   # Robinhood API Configuration
   ROBINHOOD_CLIENT_ID=your_client_id_here
   ROBINHOOD_CLIENT_SECRET=your_client_secret_here
   ROBINHOOD_API_TOKEN=your_api_token_here
   ROBINHOOD_REDIRECT_URI=http://localhost:8080
   ROBINHOOD_SANDBOX=false
   ```

## Obtaining Institutional API Access

### Step 1: Contact Robinhood Institutional

1. **Email Robinhood's Institutional Team:**
   - Send an email to: `institutional@robinhood.com`
   - Subject: "API Access Request for Crypto Trading Application"

2. **Provide Required Information:**
   - Company name and type (RIA, hedge fund, etc.)
   - Regulatory registration numbers (CRD, SEC, etc.)
   - Description of your trading operations
   - Technical requirements and use case
   - Compliance and risk management procedures

### Step 2: Complete Application Process

1. **Fill out institutional application forms**
2. **Provide compliance documentation**
3. **Complete technical integration requirements**
4. **Sign partnership agreements**

### Step 3: Receive API Credentials

Once approved, you'll receive:
- **Client ID**: Your application's identifier
- **Client Secret**: Secret key for OAuth authentication
- **API Token**: Personal access token for your account
- **Documentation**: Institutional API documentation

## Supported Crypto Symbols

The bot supports these Robinhood crypto pairs:

```
BTC/USD, ETH/USD, ADA/USD, SOL/USD, DOT/USD, AVAX/USD, MATIC/USD,
LINK/USD, UNI/USD, LTC/USD, BCH/USD, XLM/USD, ETC/USD, AAVE/USD,
COMP/USD, SNX/USD, YFI/USD, SUSHI/USD, CRV/USD, 1INCH/USD
```

## Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ROBINHOOD_CLIENT_ID` | OAuth client identifier | Yes | - |
| `ROBINHOOD_CLIENT_SECRET` | OAuth client secret | Yes | - |
| `ROBINHOOD_API_TOKEN` | Personal API token | Yes | - |
| `ROBINHOOD_REDIRECT_URI` | OAuth redirect URL | No | `http://localhost` |
| `ROBINHOOD_SANDBOX` | Use sandbox environment | No | `false` |

### Trading Configuration

```env
# Trading Parameters
TRADING_ENABLED=true
SUPPORTED_SYMBOLS=BTC/USD,ETH/USD,ADA/USD,SOL/USD
MAX_POSITIONS=5
MIN_ORDER_SIZE=1.0
MAX_ORDER_VALUE=1000.0

# Risk Management (Conservative settings recommended)
MAX_PORTFOLIO_RISK=0.02
DEFAULT_RISK_PER_TRADE=0.01
MAX_CORRELATION=0.7
MAX_DRAWDOWN=0.15
```

## Testing Your Setup

### With Institutional Access

1. **Test API Connection:**
   ```bash
   python -c "
   from src.core.api.robinhood.auth import RobinhoodAuth, RobinhoodAuthConfig
   import asyncio

   async def test_auth():
       config = RobinhoodAuthConfig()
       auth = RobinhoodAuth(config)
       await auth.initialize()
       print('✅ Authentication successful')
       await auth.close()

   asyncio.run(test_auth())
   "
   ```

2. **Start the Bot:**
   ```bash
   python -m src
   ```

### Without Institutional Access (Development Mode)

1. **Use placeholder credentials for testing:**
   ```bash
   python setup_credentials.py
   # Choose "manual token" option and enter any test values
   ```

2. **Run in development mode:**
   ```bash
   python -m src --no-live
   ```

## Troubleshooting Common Issues

### Authentication Problems

#### "Invalid Client Credentials" Error
**Symptoms:**
- Authentication fails with "invalid_client" error
- Cannot generate access tokens

**Causes:**
1. Incorrect `ROBINHOOD_CLIENT_ID` or `ROBINHOOD_CLIENT_SECRET`
2. Credentials not approved for your account
3. Using sandbox credentials in production environment

**Solutions:**
1. **Verify credentials with Robinhood:**
   ```bash
   # Double-check your credentials
   echo "Client ID: $ROBINHOOD_CLIENT_ID"
   echo "Client Secret: $ROBINHOOD_CLIENT_SECRET"
   ```

2. **Contact Robinhood institutional team:**
   - Email: institutional@robinhood.com
   - Request credential verification
   - Confirm your account has API access

3. **Check environment settings:**
   ```bash
   # Ensure you're using correct environment
   echo "Sandbox mode: $ROBINHOOD_SANDBOX"
   ```

#### "Insufficient Permissions" Error
**Symptoms:**
- API calls fail with permission errors
- Cannot access crypto trading endpoints

**Causes:**
1. Robinhood account doesn't have crypto trading enabled
2. Institutional account not properly configured
3. Geographic restrictions

**Solutions:**
1. **Enable crypto trading in Robinhood app:**
   - Open Robinhood mobile app
   - Navigate to account settings
   - Enable cryptocurrency trading

2. **Verify account status:**
   ```bash
   # Check if your account can trade crypto
   # This should be done through Robinhood support
   ```

3. **Confirm institutional approval:**
   - Contact Robinhood institutional team
   - Verify your institution is approved for crypto API access

#### Token-Related Issues

**"Token Expired" Errors:**
```bash
# Symptoms: "token_expired" or "invalid_token" errors

# Solutions:
# 1. Clear stored tokens
rm -f .robinhood_tokens.json

# 2. Restart the bot (it will refresh tokens)
python -m src

# 3. Check token file permissions
ls -la .robinhood_tokens.json
```

**"Refresh Token Invalid" Errors:**
```bash
# Symptoms: Cannot refresh access tokens

# Solutions:
# 1. The bot handles this automatically by clearing tokens
# 2. If persistent, contact Robinhood support
# 3. Verify your account is in good standing
```

### Connection Issues

#### Rate Limiting Problems
**Symptoms:**
- "rate_limit_exceeded" errors
- Requests being throttled

**Causes:**
1. Too many API requests
2. Bot making excessive calls
3. Rate limit changes by Robinhood

**Solutions:**
1. **Check current rate limits:**
   ```bash
   # The bot has built-in rate limiting, but you can monitor it
   tail -f logs/trading_bot.log | grep -i "rate.limit"
   ```

2. **Adjust bot configuration:**
   ```env
   # Reduce API call frequency in config/.env
   API_RATE_LIMIT_PER_MINUTE=50  # Reduce from default 100
   ```

3. **Enable sandbox mode for testing:**
   ```env
   ROBINHOOD_SANDBOX=true
   ```

#### Network Connectivity Issues
**Symptoms:**
- Connection timeouts
- DNS resolution failures

**Solutions:**
1. **Test basic connectivity:**
   ```bash
   # Test if you can reach Robinhood
   curl -I https://api.robinhood.com
   ```

2. **Check DNS:**
   ```bash
   nslookup api.robinhood.com
   ```

3. **Verify firewall settings:**
   ```bash
   # Ensure HTTPS traffic is allowed
   telnet api.robinhood.com 443
   ```

### Configuration Issues

#### Environment Variable Problems
**Symptoms:**
- Bot cannot find credentials
- Configuration not loading properly

**Solutions:**
1. **Verify environment file:**
   ```bash
   # Check if .env file exists and is readable
   ls -la config/.env
   cat config/.env | grep ROBINHOOD
   ```

2. **Test environment loading:**
   ```python
   # Test if environment variables are loaded
   python -c "import os; print('Client ID:', os.getenv('ROBINHOOD_CLIENT_ID', 'NOT SET'))"
   ```

3. **Recreate configuration:**
   ```bash
   # Start fresh with setup script
   python setup_credentials.py
   ```

#### Path and Import Issues
**Symptoms:**
- Import errors when starting bot
- Cannot find modules

**Solutions:**
1. **Check Python path:**
   ```bash
   # Ensure you're in the correct directory
   pwd  # Should be /path/to/crypto-trading-bot
   ls -la src/
   ```

2. **Verify Python installation:**
   ```bash
   python --version  # Should be 3.11+
   pip list | grep -E "(aiohttp|structlog|pydantic)"
   ```

3. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Trading-Specific Issues

#### "Insufficient Funds" Errors
**Symptoms:**
- Orders rejected due to insufficient funds
- Cannot place trades

**Causes:**
1. Not enough USD in Robinhood account
2. Buying power limitations
3. Account restrictions

**Solutions:**
1. **Check account balance:**
   - Log into Robinhood app
   - Verify available buying power
   - Ensure sufficient funds for intended trades

2. **Adjust position sizes:**
   ```env
   # Reduce trade sizes in config/.env
   MIN_ORDER_SIZE=1.0
   MAX_ORDER_VALUE=100.0
   ```

#### "Market Not Available" Errors
**Symptoms:**
- Cannot trade specific cryptocurrencies
- Symbol not found errors

**Causes:**
1. Cryptocurrency not supported by Robinhood
2. Trading halted for specific asset
3. Geographic restrictions

**Solutions:**
1. **Check supported symbols:**
   ```python
   # List supported cryptocurrencies
   from src.core.api.robinhood.crypto_api import RobinhoodCryptoAPI
   # The bot will show supported symbols in logs
   ```

2. **Verify symbol format:**
   ```env
   # Ensure correct symbol format in config/.env
   SUPPORTED_SYMBOLS=BTC/USD,ETH/USD,ADA/USD
   ```

### Development and Testing Issues

#### Mock Data Not Working
**Symptoms:**
- Bot not using simulated data
- Still trying to connect to live API

**Solutions:**
1. **Force mock mode:**
   ```bash
   python -m src --no-live
   ```

2. **Check configuration:**
   ```env
   # Ensure test credentials are set
   ROBINHOOD_API_TOKEN=test_token
   ROBINHOOD_SANDBOX=true
   ```

#### Logs Not Appearing
**Symptoms:**
- No log output
- Cannot see bot activity

**Solutions:**
1. **Check log configuration:**
   ```bash
   tail -f logs/trading_bot.log
   ls -la logs/
   ```

2. **Verify logging level:**
   ```env
   LOG_LEVEL=DEBUG  # In config/.env for verbose logging
   ```

3. **Create log directory:**
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

### Getting Additional Help

#### Debug Information Collection
When reporting issues, collect this information:

1. **System Information:**
   ```bash
   python --version
   pip list | grep -E "(aiohttp|structlog|pydantic|python-dotenv)"
   ```

2. **Configuration (without sensitive data):**
   ```bash
   # Show non-sensitive config
   env | grep -v -E "(TOKEN|SECRET|PASSWORD)" | grep ROBINHOOD
   ```

3. **Error Logs:**
   ```bash
   # Recent error entries
   tail -50 logs/trading_bot.log | grep -E "(ERROR|CRITICAL|EXCEPTION)"
   ```

#### Contact Information

**For Bot-Specific Issues:**
- Check this troubleshooting guide
- Review the application logs
- Test individual components

**For Robinhood API Issues:**
- **Institutional Support**: institutional@robinhood.com
- **Technical Issues**: Check Robinhood's institutional documentation
- **Account Problems**: Contact Robinhood support through your app

**For Development Issues:**
- Check the GitHub repository for similar issues
- Review the test files for examples
- Ensure you're using supported Python version (3.11+)

## Troubleshooting

### Common Issues

#### "Invalid Client Credentials"
- **Cause**: Incorrect client ID or secret
- **Solution**: Verify credentials with Robinhood institutional team

#### "Insufficient Permissions"
- **Cause**: Account doesn't have crypto trading enabled
- **Solution**: Enable crypto trading in your Robinhood app

#### "Rate Limit Exceeded"
- **Cause**: Too many API requests
- **Solution**: The bot has built-in rate limiting; wait and retry

#### "Token Expired"
- **Cause**: API token has expired
- **Solution**: Generate a new token through Robinhood's institutional portal

### Getting Help

1. **Check the logs:**
   ```bash
   tail -f logs/trading_bot.log
   ```

2. **Test individual components:**
   ```bash
   python -c "
   from src.core.api.robinhood.auth import RobinhoodAuth, RobinhoodAuthConfig
   # Test authentication
   "
   ```

3. **Contact Robinhood Support:**
   - For institutional access issues: `institutional@robinhood.com`
   - For technical problems: Check Robinhood's institutional documentation

## Security Best Practices

### Credential Management
- ✅ Store credentials in environment variables
- ✅ Use `.env` files (already gitignored)
- ✅ Rotate tokens regularly
- ✅ Never commit credentials to version control

### Account Security
- ✅ Enable two-factor authentication on your Robinhood account
- ✅ Use dedicated API accounts for trading
- ✅ Monitor account activity regularly
- ✅ Set up appropriate trading limits

## Cost Considerations

### Robinhood Fee Structure
- **Crypto Trading**: No commission fees
- **API Access**: May have institutional pricing
- **Data Usage**: Consider API rate limits and costs

### Development Costs
- **Testing**: Use sandbox mode for development
- **Mock Data**: Bot can run with simulated data for testing
- **Rate Limits**: Monitor API usage to avoid unnecessary costs

## Next Steps

1. **Obtain institutional API access** from Robinhood
2. **Configure your credentials** using the setup script
3. **Test your configuration** in sandbox mode
4. **Start with small positions** when going live
5. **Monitor performance** and adjust risk settings as needed

## Important Disclaimers

⚠️ **Trading cryptocurrency involves substantial risk of loss and is not suitable for every investor.**

- This bot is for educational and research purposes
- Past performance does not guarantee future results
- Always understand the risks before live trading
- Consider consulting with financial advisors
- The authors are not responsible for any financial losses

## Support

For issues with this trading bot:
1. Check the troubleshooting section above
2. Review the application logs
3. Test individual components
4. Check GitHub issues for similar problems

For Robinhood API issues:
1. Contact Robinhood's institutional support team
2. Review their institutional API documentation
3. Check your account permissions and settings