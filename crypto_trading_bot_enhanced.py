import base64
import datetime
import json
import time
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


class RateLimitTracker:
    """Track API rate limiting to avoid hitting limits"""
    def __init__(self):
        self.request_times = []
        self.max_per_minute = 100
        self.max_burst = 300

    def can_make_request(self) -> bool:
        """Check if we can make another request without hitting rate limits"""
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.max_burst:
            return False
        return True

    def record_request(self):
        """Record that a request was made"""
        self.request_times.append(time.time())

    def get_wait_time(self) -> float:
        """Get how long to wait before next request"""
        if not self.request_times:
            return 0

        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.max_burst:
            oldest = min(self.request_times)
            return max(0, 60 - (now - oldest))
        return 0

    def get_stats(self) -> Dict[str, int]:
        """Get current rate limit statistics"""
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]
        return {
            "requests_last_minute": len(self.request_times),
            "remaining_capacity": self.max_burst - len(self.request_times)
        }


class CryptoAPITrading:
    def __init__(self, verbose: bool = True):
        self.api_key = API_KEY
        private_key_seed = base64.b64decode(BASE64_PRIVATE_KEY)
        self.private_key = SigningKey(private_key_seed)
        self.base_url = "https://trading.robinhood.com"
        self.verbose = verbose
        self.rate_limiter = RateLimitTracker()
        self.request_count = 0

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

    def _log(self, message: str, level: str = "INFO"):
        """Log messages if verbose mode is enabled"""
        if self.verbose:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def make_api_request(
        self,
        method: str,
        path: str,
        body: str = "",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Any:
        """
        Make an API request with rate limiting, error handling, and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            body: Request body (for POST requests)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            API response as dict, or None on error
        """
        # Check rate limiting
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.get_wait_time()
            self._log(f"Rate limit reached. Waiting {wait_time:.1f} seconds...", "WARNING")
            time.sleep(wait_time)

        for attempt in range(max_retries):
            try:
                timestamp = self._get_current_timestamp()
                headers = self.get_authorization_header(method, path, body, timestamp)
                url = self.base_url + path

                self._log(f"API Request #{self.request_count + 1}: {method} {path}")

                # Make the request
                if method == "GET":
                    response = requests.get(url, headers=headers, timeout=10)
                elif method == "POST":
                    response = requests.post(
                        url,
                        headers=headers,
                        json=json.loads(body) if body else {},
                        timeout=10
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Record request for rate limiting
                self.rate_limiter.record_request()
                self.request_count += 1

                # Handle response
                if response.status_code in [200, 201]:
                    self._log(f"Success: {response.status_code}", "INFO")
                    return response.json() if response.text else {}

                elif response.status_code == 401:
                    self._log(f"Authentication failed: {response.text}", "ERROR")
                    return {"error": "authentication_failed", "details": response.text}

                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    self._log(f"Rate limited. Waiting before retry...", "WARNING")
                    time.sleep(retry_delay * (attempt + 1))
                    continue

                elif response.status_code == 400:
                    # Bad request - don't retry
                    self._log(f"Bad request: {response.text}", "ERROR")
                    return {"error": "bad_request", "details": response.text}

                elif response.status_code >= 500:
                    # Server error - retry
                    self._log(f"Server error {response.status_code}. Retrying...", "WARNING")
                    time.sleep(retry_delay * (attempt + 1))
                    continue

                else:
                    self._log(f"Unexpected status {response.status_code}: {response.text}", "ERROR")
                    return {
                        "error": "unexpected_status",
                        "status_code": response.status_code,
                        "details": response.text
                    }

            except requests.Timeout:
                self._log(f"Request timeout (attempt {attempt + 1}/{max_retries})", "WARNING")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return {"error": "timeout"}

            except requests.RequestException as e:
                self._log(f"Request error: {e}", "ERROR")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return {"error": "request_failed", "details": str(e)}

            except json.JSONDecodeError as e:
                self._log(f"JSON decode error: {e}", "ERROR")
                return {"error": "json_decode_failed", "details": str(e)}

            except Exception as e:
                self._log(f"Unexpected error: {e}", "ERROR")
                return {"error": "unexpected_error", "details": str(e)}

        # Max retries exceeded
        self._log(f"Max retries ({max_retries}) exceeded", "ERROR")
        return {"error": "max_retries_exceeded"}

    def get_authorization_header(
        self, method: str, path: str, body: str, timestamp: int
    ) -> Dict[str, str]:
        """Generate authorization headers for API request"""
        message_to_sign = f"{self.api_key}{timestamp}{path}{method}{body}"
        signed = self.private_key.sign(message_to_sign.encode("utf-8"))

        return {
            "x-api-key": self.api_key,
            "x-signature": base64.b64encode(signed.signature).decode("utf-8"),
            "x-timestamp": str(timestamp),
        }

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get current rate limiting statistics"""
        stats = self.rate_limiter.get_stats()
        stats["total_requests_made"] = self.request_count
        return stats

    # ===== API Endpoints =====

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
    Main function to test the enhanced API client
    """
    print("=" * 60)
    print("ROBINHOOD CRYPTO TRADING BOT - ENHANCED")
    print("=" * 60)

    # Initialize the trading client
    api = CryptoAPITrading(verbose=True)

    print("\n[+] Testing API connection...")
    print("-" * 60)

    # Test connection
    account_info = api.get_account()

    if account_info and "error" not in account_info:
        print("\n[+] Successfully connected to Robinhood Crypto API!")
        print("\nAccount Information:")
        print(json.dumps(account_info, indent=2))

        # Show rate limit stats
        print("\nRate Limit Statistics:")
        print(json.dumps(api.get_rate_limit_stats(), indent=2))
    else:
        print("\n[!] Failed to connect to API")
        if account_info:
            print(f"Error: {account_info}")

    print("\n" + "=" * 60)

    """
    EXAMPLE: Build your trading strategy below

    # Get market data
    btc_price = api.get_best_bid_ask("BTC-USD")
    print(f"BTC Price: {btc_price}")

    # Get your holdings
    holdings = api.get_holdings()
    print(f"Holdings: {holdings}")

    # Get estimated price (use "ask" for buying, "bid" for selling)
    estimated = api.get_estimated_price("BTC-USD", "ask", "0.001")
    print(f"Estimated price: {estimated}")

    # Place a market order (CAUTION: This will execute a real trade!)
    # order = api.place_order(
    #     str(uuid.uuid4()),
    #     "buy",
    #     "market",
    #     "BTC-USD",
    #     {"asset_quantity": "0.0001"}
    # )
    # print(f"Order placed: {order}")
    """


if __name__ == "__main__":
    main()
