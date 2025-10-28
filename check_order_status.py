from crypto_trading_bot_enhanced import CryptoAPITrading
import json
import time

api = CryptoAPITrading(verbose=True)

order_id = "6900a780-fa30-4f6f-b81c-0c50217a2dac"

print("=" * 60)
print(f"CHECKING ORDER STATUS: {order_id}")
print("=" * 60)

# Check order status
print("\nOrder Details:")
print("-" * 60)
order = api.get_order(order_id)

if order and "error" not in order:
    print(json.dumps(order, indent=2))

    print(f"\nOrder State: {order.get('state', 'unknown')}")
    print(f"Filled Quantity: {order.get('filled_asset_quantity', '0')}")

    if order.get('average_price'):
        print(f"Average Price: ${float(order['average_price']):.2f}")

    if order.get('executions'):
        print(f"\nExecutions: {len(order['executions'])} fill(s)")
        for i, execution in enumerate(order['executions'], 1):
            print(f"  Fill #{i}:")
            print(f"    Quantity: {execution.get('asset_quantity', 'N/A')}")
            print(f"    Price: ${float(execution.get('price', 0)):.2f}")
else:
    print("Error getting order details")

# Check SOL holdings
print("\n" + "=" * 60)
print("CURRENT SOL HOLDINGS")
print("=" * 60)

time.sleep(2)  # Wait a moment for order to process

holdings = api.get_holdings("SOL")

if holdings and "results" in holdings:
    if holdings["results"]:
        print(json.dumps(holdings["results"][0], indent=2))
    else:
        print("No SOL holdings found yet (order may still be processing)")
else:
    print("Error getting holdings")

print("\n" + "=" * 60)
