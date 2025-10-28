# Robinhood Crypto Trading Bot

## Successfully Connected! ✅

Your Robinhood Crypto trading bot is now fully configured and connected to the API.

---

## 📁 Project Files

| File | Description |
|------|-------------|
| `crypto_trading_bot.py` | Basic trading bot with core functionality |
| `crypto_trading_bot_enhanced.py` | **RECOMMENDED** - Enhanced bot with error handling & rate limiting |
| `generate_keys.py` | Script to generate new API key pairs |
| `test_functionality.py` | Test script for all API endpoints |
| `requirements.txt` | Python dependencies |
| `testcrypto/` | Python virtual environment |

---

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

---

## 💰 Account Info

- Your account information will be loaded from the `.env` file
- Run the bot to see your current holdings and buying power

---

## 🚀 How to Run the Bot

### Activate the environment:
```bash
activate_testcrypto.bat
```

### Run the enhanced bot (recommended):
```bash
python crypto_trading_bot_enhanced.py
```

### Run the basic bot:
```bash
python crypto_trading_bot.py
```

---

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

---

## 💡 Example Usage

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

---

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

---

## 🔒 Rate Limits

- **Standard:** 100 requests/minute
- **Burst:** 300 requests/minute
- **Timestamp validity:** 30 seconds

The enhanced bot automatically manages these limits for you!

---

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

---

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

---

## 📚 API Documentation

For full API documentation, visit:
https://docs.robinhood.com/crypto/trading-api

---

## 🎯 Next Steps

1. **Test the bot** with the example code
2. **Build your strategy** in the main() function
3. **Implement risk management** (stop-loss, take-profit, etc.)
4. **Add monitoring** and alerting
5. **Backtest** your strategy before going live

---

## ✅ Setup Complete!

All systems are operational. Your bot is ready to trade!

**Current Status:**
- ✅ API credentials configured
- ✅ Connection verified
- ✅ Account active ($12.01 buying power)
- ✅ Error handling enabled
- ✅ Rate limiting active
- ✅ All endpoints tested

Happy trading! 🚀
