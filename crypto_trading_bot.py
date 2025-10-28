import base64
import datetime
import json
from typing import Any, Dict, Optional
import uuid
import os
import requests
from nacl.signing import SigningKey
from pathlib import Path

# Load environment variables from .env file
def load_env():
    """Load API credentials from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables
load_env()

# API credentials from environment variables
API_KEY = os.getenv("RH_API_KEY")
BASE64_PRIVATE_KEY = os.getenv("RH_BASE64_PRIVATE_KEY")

# Validate credentials are loaded
if not API_KEY or not BASE64_PRIVATE_KEY:
    raise ValueError("API credentials not found. Please ensure .env file exists with RH_API_KEY and RH_BASE64_PRIVATE_KEY")

class CryptoAPITrading:
    def __init__(self):
        self.api_key = API_KEY
        private_key_seed = base64.b64decode(BASE64_PRIVATE_KEY)
        self.private_key = SigningKey(private_key_seed)
        self.base_url = "https://trading.robinhood.com"

    @staticmethod
    def _get_current_timestamp() -> int:
        return int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())

    @staticmethod
    def get_query_params(key: str, *args: Optional[str]) -> str:
        if not args:
            return ""

        params = []
        for arg in args:
            params.append(f"{key}={arg}")

        return "?" + "&".join(params)

    def make_api_request(self, method: str, path: str, body: str = "") -> Any:
        timestamp = self._get_current_timestamp()
        headers = self.get_authorization_header(method, path, body, timestamp)
        url = self.base_url + path

        try:
            response = {}
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json.loads(body), timeout=10)

            # Print response status for debugging
            print(f"API Request: {method} {path}")
            print(f"Status Code: {response.status_code}")

            if response.status_code != 200:
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {dict(response.headers)}")

            # Check if response has JSON content
            if response.text:
                return response.json()
            else:
                print("Empty response body")
                return {"status_code": response.status_code, "error": "Empty response"}

        except requests.RequestException as e:
            print(f"Error making API request: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response text: {response.text}")
            return None

    def get_authorization_header(
            self, method: str, path: str, body: str, timestamp: int
    ) -> Dict[str, str]:
        message_to_sign = f"{self.api_key}{timestamp}{path}{method}{body}"
        signed = self.private_key.sign(message_to_sign.encode("utf-8"))

        return {
            "x-api-key": self.api_key,
            "x-signature": base64.b64encode(signed.signature).decode("utf-8"),
            "x-timestamp": str(timestamp),
        }

    def get_account(self) -> Any:
        """Get account information"""
        path = "/api/v1/crypto/trading/accounts/"
        return self.make_api_request("GET", path)

    def get_trading_pairs(self, *symbols: Optional[str]) -> Any:
        """
        Get trading pairs information.
        Args:
            symbols: Trading pairs like "BTC-USD", "ETH-USD". If none provided, all pairs returned.
        """
        query_params = self.get_query_params("symbol", *symbols)
        path = f"/api/v1/crypto/trading/trading_pairs/{query_params}"
        return self.make_api_request("GET", path)

    def get_holdings(self, *asset_codes: Optional[str]) -> Any:
        """
        Get crypto holdings.
        Args:
            asset_codes: Asset codes like "BTC", "ETH". If none provided, all holdings returned.
        """
        query_params = self.get_query_params("asset_code", *asset_codes)
        path = f"/api/v1/crypto/trading/holdings/{query_params}"
        return self.make_api_request("GET", path)

    def get_best_bid_ask(self, *symbols: Optional[str]) -> Any:
        """
        Get best bid and ask prices.
        Args:
            symbols: Trading pairs like "BTC-USD", "ETH-USD". If none provided, all pairs returned.
        """
        query_params = self.get_query_params("symbol", *symbols)
        path = f"/api/v1/crypto/marketdata/best_bid_ask/{query_params}"
        return self.make_api_request("GET", path)

    def get_estimated_price(self, symbol: str, side: str, quantity: str) -> Any:
        """
        Get estimated price for a trade.
        Args:
            symbol: Trading pair like "BTC-USD"
            side: "bid" (for selling), "ask" (for buying), or "both"
            quantity: Quantity as string, e.g. "0.1,1,1.999"
        """
        path = f"/api/v1/crypto/marketdata/estimated_price/?symbol={symbol}&side={side}&quantity={quantity}"
        return self.make_api_request("GET", path)

    def place_order(
            self,
            client_order_id: str,
            side: str,
            order_type: str,
            symbol: str,
            order_config: Dict[str, str],
    ) -> Any:
        """
        Place a crypto order.
        Args:
            client_order_id: Unique order ID (use str(uuid.uuid4()))
            side: "buy" or "sell"
            order_type: "market" or "limit"
            symbol: Trading pair like "BTC-USD"
            order_config: Order configuration dict, e.g. {"asset_quantity": "0.0001"}
        """
        body = {
            "client_order_id": client_order_id,
            "side": side,
            "type": order_type,
            "symbol": symbol,
            f"{order_type}_order_config": order_config,
        }
        path = "/api/v1/crypto/trading/orders/"
        return self.make_api_request("POST", path, json.dumps(body))

    def cancel_order(self, order_id: str) -> Any:
        """Cancel an order by order ID"""
        path = f"/api/v1/crypto/trading/orders/{order_id}/cancel/"
        return self.make_api_request("POST", path)

    def get_order(self, order_id: str) -> Any:
        """Get order details by order ID"""
        path = f"/api/v1/crypto/trading/orders/{order_id}/"
        return self.make_api_request("GET", path)

    def get_orders(self) -> Any:
        """Get all orders"""
        path = "/api/v1/crypto/trading/orders/"
        return self.make_api_request("GET", path)


def main():
    """
    Main function to test the API connection
    """
    print("=" * 60)
    print("ROBINHOOD CRYPTO TRADING BOT")
    print("=" * 60)

    # Check if API credentials are configured
    if API_KEY == "ADD YOUR API KEY HERE" or BASE64_PRIVATE_KEY == "ADD YOUR PRIVATE KEY HERE":
        print("\n[!] ERROR: API credentials not configured!")
        print("\nPlease follow these steps:")
        print("1. Visit the Robinhood API Credentials Portal")
        print("2. Register your PUBLIC key to get an API key")
        print("3. Update API_KEY and BASE64_PRIVATE_KEY in this file")
        print("\n" + "=" * 60)
        return

    # Initialize the trading client
    api_trading_client = CryptoAPITrading()

    print("\n[+] Testing API connection...")
    print("-" * 60)

    # Test connection by getting account info
    account_info = api_trading_client.get_account()

    if account_info:
        print("\n[+] Successfully connected to Robinhood Crypto API!")
        print("\nAccount Information:")
        print(json.dumps(account_info, indent=2))
    else:
        print("\n[!] Failed to connect to API")

    print("\n" + "=" * 60)

    """
    EXAMPLE: Build your trading strategy below

    # Get market data
    btc_price = api_trading_client.get_best_bid_ask("BTC-USD")
    print(f"BTC Price: {btc_price}")

    # Get your holdings
    holdings = api_trading_client.get_holdings()
    print(f"Holdings: {holdings}")

    # Place a market order (CAUTION: This will execute a real trade!)
    order = api_trading_client.place_order(
        str(uuid.uuid4()),
        "buy",
        "market",
        "BTC-USD",
        {"asset_quantity": "0.0001"}
    )
    print(f"Order placed: {order}")
    """


if __name__ == "__main__":
    main()
