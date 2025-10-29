import base64
import datetime
import json
from typing import Any, Dict, Optional
import uuid
import requests
from nacl.signing import SigningKey

API_KEY = "rh-api-d974c10e-3c0a-4ae1-9e9c-ac4d9fee0f1c"
BASE64_PRIVATE_KEY = "ab56rfpJte+AJlgbUHGtIomkoiELe4Li2yEh5V5lyGY="

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

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: Status {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error making API request: {e}")
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
        path = "/api/v1/crypto/trading/accounts/"
        return self.make_api_request("GET", path)

    def get_trading_pairs(self, *symbols: Optional[str]) -> Any:
        query_params = self.get_query_params("symbol", *symbols)
        path = f"/api/v1/crypto/trading/trading_pairs/{query_params}"
        return self.make_api_request("GET", path)

    def get_holdings(self, *asset_codes: Optional[str]) -> Any:
        query_params = self.get_query_params("asset_code", *asset_codes)
        path = f"/api/v1/crypto/trading/holdings/{query_params}"
        return self.make_api_request("GET", path)

    def get_best_bid_ask(self, *symbols: Optional[str]) -> Any:
        query_params = self.get_query_params("symbol", *symbols)
        path = f"/api/v1/crypto/marketdata/best_bid_ask/{query_params}"
        return self.make_api_request("GET", path)

    def get_estimated_price(self, symbol: str, side: str, quantity: str) -> Any:
        path = f"/api/v1/crypto/marketdata/estimated_price/?symbol={symbol}&side={side}&quantity={quantity}"
        return self.make_api_request("GET", path)


print("=" * 60)
print("TESTING ROBINHOOD CRYPTO API - CORE FUNCTIONALITY")
print("=" * 60)

api = CryptoAPITrading()

# Test 1: Get account info
print("\n[1] Testing: Get Account Information")
print("-" * 60)
account = api.get_account()
if account:
    print(json.dumps(account, indent=2))
else:
    print("[!] Failed to get account info")

# Test 2: Get holdings
print("\n[2] Testing: Get Holdings")
print("-" * 60)
holdings = api.get_holdings()
if holdings:
    print(json.dumps(holdings, indent=2))
else:
    print("[!] Failed to get holdings")

# Test 3: Get BTC-USD trading pair info
print("\n[3] Testing: Get BTC-USD Trading Pair")
print("-" * 60)
btc_pair = api.get_trading_pairs("BTC-USD")
if btc_pair:
    print(json.dumps(btc_pair, indent=2))
else:
    print("[!] Failed to get trading pair")

# Test 4: Get BTC-USD best bid/ask
print("\n[4] Testing: Get BTC-USD Best Bid/Ask Price")
print("-" * 60)
btc_price = api.get_best_bid_ask("BTC-USD")
if btc_price:
    print(json.dumps(btc_price, indent=2))
else:
    print("[!] Failed to get price")

# Test 5: Get estimated price for buying 0.001 BTC
print("\n[5] Testing: Get Estimated Price (Buy 0.001 BTC)")
print("-" * 60)
estimated = api.get_estimated_price("BTC-USD", "buy", "0.001")
if estimated:
    print(json.dumps(estimated, indent=2))
else:
    print("[!] Failed to get estimated price")

print("\n" + "=" * 60)
print("CORE FUNCTIONALITY TEST COMPLETE")
print("=" * 60)
