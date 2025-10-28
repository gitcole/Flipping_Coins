"""
Example Trading Strategies for Robinhood Crypto Bot

CAUTION: These are examples only! Modify before using with real money.
"""

from crypto_trading_bot_enhanced import CryptoAPITrading
import json
import uuid
import time


def example_1_check_account_and_holdings():
    """Example 1: Check your account and current holdings"""
    print("=" * 60)
    print("EXAMPLE 1: Account & Holdings")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Get account info
    account = api.get_account()
    print("\nAccount Info:")
    print(json.dumps(account, indent=2))

    # Get all holdings
    holdings = api.get_holdings()
    print("\nAll Holdings:")
    print(json.dumps(holdings, indent=2))

    # Get specific holdings
    btc_holdings = api.get_holdings("BTC")
    print("\nBTC Holdings:")
    print(json.dumps(btc_holdings, indent=2))


def example_2_check_market_prices():
    """Example 2: Check current market prices"""
    print("=" * 60)
    print("EXAMPLE 2: Market Prices")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Get BTC price
    btc_price = api.get_best_bid_ask("BTC-USD")
    if btc_price and "results" in btc_price:
        result = btc_price["results"][0]
        print(f"\nBTC-USD Price: ${float(result['price']):,.2f}")
        print(f"  Buy Price (ask):  ${float(result['ask_inclusive_of_buy_spread']):,.2f}")
        print(f"  Sell Price (bid): ${float(result['bid_inclusive_of_sell_spread']):,.2f}")

    # Get multiple prices at once
    print("\nGetting multiple prices...")
    prices = api.get_best_bid_ask("BTC-USD", "ETH-USD", "SOL-USD")
    print(json.dumps(prices, indent=2))


def example_3_estimate_trade_cost():
    """Example 3: Estimate the cost of a trade before placing it"""
    print("=" * 60)
    print("EXAMPLE 3: Estimate Trade Cost")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Estimate cost to buy 0.001 BTC
    estimate = api.get_estimated_price("BTC-USD", "ask", "0.001")

    if estimate and "results" in estimate:
        for result in estimate["results"]:
            quantity = result.get("quantity", "0")
            cost = result.get("total", "0")
            price = result.get("price", "0")

            print(f"\nEstimate to BUY {quantity} BTC:")
            print(f"  Estimated Price: ${float(price):,.2f}")
            print(f"  Total Cost: ${float(cost):,.2f}")


def example_4_get_trading_pair_info():
    """Example 4: Get trading pair information and limits"""
    print("=" * 60)
    print("EXAMPLE 4: Trading Pair Info")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Get BTC-USD trading pair info
    pair_info = api.get_trading_pairs("BTC-USD")

    if pair_info and "results" in pair_info:
        result = pair_info["results"][0]
        print(f"\nBTC-USD Trading Rules:")
        print(f"  Status: {result['status']}")
        print(f"  Min Order Size: {result['min_order_size']} BTC")
        print(f"  Max Order Size: {result['max_order_size']} BTC")
        print(f"  Price Increment: ${result['quote_increment']}")
        print(f"  Asset Increment: {result['asset_increment']} BTC")


def example_5_place_small_test_order():
    """
    Example 5: Place a SMALL test market order

    WARNING: This will execute a REAL trade! Comment out to prevent execution.
    """
    print("=" * 60)
    print("EXAMPLE 5: Place Test Order (COMMENTED OUT FOR SAFETY)")
    print("=" * 60)

    # UNCOMMENT BELOW TO ACTUALLY PLACE AN ORDER
    # MAKE SURE YOU UNDERSTAND WHAT THIS DOES FIRST!

    """
    api = CryptoAPITrading(verbose=True)

    # Place a very small market buy order for BTC
    order = api.place_order(
        client_order_id=str(uuid.uuid4()),
        side="buy",
        order_type="market",
        symbol="BTC-USD",
        order_config={"asset_quantity": "0.00001"}  # Very small amount!
    )

    print("\nOrder Response:")
    print(json.dumps(order, indent=2))

    # Get order status
    if order and "id" in order:
        order_id = order["id"]
        time.sleep(2)  # Wait a bit for order to process

        status = api.get_order(order_id)
        print("\nOrder Status:")
        print(json.dumps(status, indent=2))
    """

    print("\n[!] This example is commented out for safety.")
    print("[!] Uncomment the code if you want to place a real order.")


def example_6_monitor_rate_limits():
    """Example 6: Monitor API rate limits"""
    print("=" * 60)
    print("EXAMPLE 6: Rate Limit Monitoring")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Make several requests
    for i in range(5):
        print(f"\nRequest {i + 1}:")
        api.get_account()

        # Check rate limit stats
        stats = api.get_rate_limit_stats()
        print(f"Requests in last minute: {stats['requests_last_minute']}")
        print(f"Remaining capacity: {stats['remaining_capacity']}")
        print(f"Total requests made: {stats['total_requests_made']}")

        time.sleep(1)


def example_7_get_order_history():
    """Example 7: Get your order history"""
    print("=" * 60)
    print("EXAMPLE 7: Order History")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Get all orders
    orders = api.get_orders()

    if orders and "results" in orders:
        print(f"\nFound {len(orders['results'])} orders")

        for order in orders["results"][:5]:  # Show first 5
            print(f"\nOrder ID: {order.get('id', 'N/A')}")
            print(f"  Symbol: {order.get('symbol', 'N/A')}")
            print(f"  Side: {order.get('side', 'N/A')}")
            print(f"  Type: {order.get('type', 'N/A')}")
            print(f"  State: {order.get('state', 'N/A')}")
            print(f"  Created: {order.get('created_at', 'N/A')}")
    else:
        print("\nNo orders found or error occurred")


def example_8_simple_price_alert():
    """Example 8: Simple price alert (monitor BTC price)"""
    print("=" * 60)
    print("EXAMPLE 8: Price Alert Monitor")
    print("=" * 60)

    api = CryptoAPITrading(verbose=False)  # Quiet mode

    target_price = 115000  # Alert when BTC hits this price
    check_interval = 10  # Check every 10 seconds

    print(f"\nMonitoring BTC-USD...")
    print(f"Alert when price reaches ${target_price:,}")
    print(f"Checking every {check_interval} seconds")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            price_data = api.get_best_bid_ask("BTC-USD")

            if price_data and "results" in price_data:
                current_price = float(price_data["results"][0]["price"])
                print(f"Current BTC Price: ${current_price:,.2f}", end="")

                if current_price >= target_price:
                    print(" <- ALERT! Target reached!")
                    break
                else:
                    print()

            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


# Main menu
def main():
    print("\n" + "=" * 60)
    print("ROBINHOOD CRYPTO BOT - EXAMPLE STRATEGIES")
    print("=" * 60)
    print("\nAvailable examples:")
    print("1. Check account and holdings")
    print("2. Check market prices")
    print("3. Estimate trade cost")
    print("4. Get trading pair info")
    print("5. Place small test order (DISABLED FOR SAFETY)")
    print("6. Monitor rate limits")
    print("7. Get order history")
    print("8. Simple price alert")
    print("\nTo run an example, call it directly, e.g.:")
    print("  example_1_check_account_and_holdings()")
    print("\n" + "=" * 60)

    # Run example 1 by default
    example_1_check_account_and_holdings()


if __name__ == "__main__":
    main()
