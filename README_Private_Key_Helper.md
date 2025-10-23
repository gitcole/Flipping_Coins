# 🔐 Robinhood Private Key Helper

A comprehensive tool to help you find, configure, and test your Robinhood Private Key for the crypto trading bot.

## ⚠️ Important Notice

**Robinhood has restricted their API to institutional users only.** Individual developers cannot access the Robinhood API. You need institutional or partner access for live trading.

## 🚀 Features

- **🔒 Secure Credential Input**: Masked input for sensitive data
- **🚀 Automated Configuration**: Automatically updates `.env` file
- **✅ Comprehensive Testing**: Validates credentials and API connectivity
- **📋 Detailed Guidance**: Step-by-step institutional access instructions
- **🔧 Connection Validation**: Tests authentication and API endpoints
- **📊 Test Results**: Detailed pass/fail reporting with troubleshooting

## 📋 Prerequisites

Before using this helper:

1. **Obtain Institutional Access** (see guide below)
2. **Python 3.11+** installed
3. **Required packages** installed:
   ```bash
   pip install aiohttp structlog python-dotenv pydantic
   ```

## 🎯 Quick Start

### Run the Setup Wizard

```bash
python robinhood_private_key_helper.py
```

The interactive wizard will guide you through:
1. **Credential Input** - Secure entry of your API credentials
2. **Format Validation** - Checks credential format and structure
3. **Configuration Update** - Updates `config/.env` automatically
4. **Authentication Testing** - Validates credentials with Robinhood API
5. **Results Summary** - Shows detailed test results and next steps

### Test Existing Setup

```bash
python robinhood_private_key_helper.py --test
```

### Get Help

```bash
python robinhood_private_key_helper.py --help
```

## 🏢 Obtaining Institutional Access

### Step 1: Contact Robinhood Institutional Team

Send an email to: **institutional@robinhood.com**
- Subject: "API Access Request for Crypto Trading Application"

### Step 2: Provide Required Information

- Company name and type (RIA, hedge fund, etc.)
- Regulatory registration numbers (CRD, SEC, etc.)
- Description of your trading operations
- Technical requirements and use case
- Compliance and risk management procedures

### Step 3: Complete Application Process

1. Fill out institutional application forms
2. Provide compliance documentation
3. Complete technical integration requirements
4. Sign partnership agreements

### Step 4: Receive Your Credentials

Once approved, you'll receive:
- **Client ID**: Your application's identifier
- **Client Secret**: Secret key for OAuth authentication
- **API Token**: Personal access token for your account
- **Documentation**: Institutional API documentation

## 🔧 Configuration Options

### Environment Variables Updated

The helper script configures these variables in `config/.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `ROBINHOOD_API_TOKEN` | Personal API token | Yes |
| `ROBINHOOD_CLIENT_ID` | OAuth client identifier | Yes |
| `ROBINHOOD_CLIENT_SECRET` | OAuth client secret | Yes |
| `ROBINHOOD_REDIRECT_URI` | OAuth redirect URL | No (default: `http://localhost`) |
| `ROBINHOOD_SANDBOX` | Use sandbox environment | No (default: `true`) |

### Sandbox vs Production

- **Sandbox Mode** (`ROBINHOOD_SANDBOX=true`):
  - Testing and development only
  - Simulated or delayed market data
  - No real money, no market impact
  - More permissive rate limits

- **Production Mode** (`ROBINHOOD_SANDBOX=false`):
  - Live trading with real money
  - Real-time market data
  - Executes real trades
  - Strict rate limits
  - Requires institutional approval

## 🧪 Testing Your Setup

The helper script performs comprehensive testing:

### Authentication Tests
- ✅ Credential format validation
- ✅ Access token generation
- ✅ API endpoint connectivity
- ✅ Account permission verification

### Common Test Results

**✅ All Tests Passed**
- Credentials are valid and working
- Ready to start the trading bot
- Can proceed with `python -m src`

**❌ Authentication Failed**
- Invalid credentials or permissions
- Account may not have crypto trading enabled
- Need to verify institutional access

**❌ Network Issues**
- Cannot connect to Robinhood API
- Check internet connection
- Verify firewall settings

## 🔍 Troubleshooting

### Common Issues

#### "Invalid Client Credentials"
- **Cause**: Incorrect Client ID or Secret
- **Solution**: Verify credentials with Robinhood institutional team

#### "Insufficient Permissions"
- **Cause**: Account doesn't have crypto trading enabled
- **Solution**: Enable crypto trading in your Robinhood app

#### "Rate Limit Exceeded"
- **Cause**: Too many API requests
- **Solution**: The bot has built-in rate limiting; wait and retry

### Getting Additional Help

1. **Check the logs**: `logs/robinhood_helper.log`
2. **Test individual components**: Use the `--test` flag
3. **Contact Robinhood**: institutional@robinhood.com
4. **Review API documentation**: Institutional API docs from Robinhood

## 🔒 Security Features

- **Masked Input**: Sensitive fields (tokens, secrets) are masked during entry
- **Secure Storage**: Credentials stored in `.env` file (gitignored)
- **Input Validation**: All credentials validated before saving
- **Connection Testing**: Validates credentials work before saving
- **Error Handling**: Graceful handling of authentication failures

## 📁 File Structure

```
├── robinhood_private_key_helper.py  # Main helper script
├── config/
│   └── .env                         # Configuration file (updated automatically)
├── logs/
│   └── robinhood_helper.log         # Detailed logs (created automatically)
└── README_Private_Key_Helper.md     # This file
```

## 🚀 Next Steps

After successful setup:

1. **Start the trading bot**:
   ```bash
   python -m src
   ```

2. **Monitor performance**:
   ```bash
   tail -f logs/trading_bot.log
   ```

3. **Configure strategies**:
   - Edit strategy parameters in `config/.env`
   - Review risk management settings
   - Set appropriate position limits

4. **Test with small amounts**:
   - Start with small position sizes
   - Monitor bot behavior
   - Adjust settings as needed

## ⚠️ Disclaimers

- **Trading cryptocurrency involves substantial risk of loss**
- **This bot is for educational and research purposes**
- **Past performance does not guarantee future results**
- **Always understand the risks before live trading**
- **Consider consulting with financial advisors**
- **The authors are not responsible for any financial losses**

## 🔄 Updates and Support

For issues or improvements:
1. Check this troubleshooting guide
2. Review the application logs
3. Test individual components
4. Contact Robinhood institutional support for API issues