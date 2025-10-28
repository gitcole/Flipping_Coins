from crypto_trading_bot_enhanced import CryptoAPITrading
import json

api = CryptoAPITrading(verbose=True)

print("=" * 60)
print("CHECKING SOLANA (SOL-USD) TRADING REQUIREMENTS")
print("=" * 60)

# Get SOL-USD trading pair info
print("\n[1] SOL-USD Trading Pair Information:")
print("-" * 60)
sol_pair = api.get_trading_pairs("SOL-USD")
if sol_pair and "results" in sol_pair:
    result = sol_pair["results"][0]
    print(json.dumps(result, indent=2))

    min_order = float(result['min_order_size'])
    print(f"\n[+] Minimum Order Size: {min_order} SOL")

# Get current SOL price
print("\n[2] Current SOL-USD Price:")
print("-" * 60)
sol_price = api.get_best_bid_ask("SOL-USD")
if sol_price and "results" in sol_price:
    result = sol_price["results"][0]
    current_price = float(result['price'])
    buy_price = float(result['ask_inclusive_of_buy_spread'])

    print(f"Current Price: ${current_price:.4f}")
    print(f"Buy Price (with spread): ${buy_price:.4f}")

    # Calculate minimum dollar amount needed
    if sol_pair and "results" in sol_pair:
        min_sol = float(sol_pair["results"][0]['min_order_size'])
        min_dollar_amount = min_sol * buy_price
        print(f"\n[+] Minimum dollar amount: ${min_dollar_amount:.4f}")
        print(f"    (Based on {min_sol} SOL × ${buy_price:.4f})")

# Check if you can buy $10 worth
print("\n[3] Can you buy $10 worth of SOL?")
print("-" * 60)
if sol_pair and sol_price:
    min_sol = float(sol_pair["results"][0]['min_order_size'])
    buy_price = float(sol_price["results"][0]['ask_inclusive_of_buy_spread'])
    min_dollar = min_sol * buy_price

    if min_dollar <= 10:
        sol_amount = 10 / buy_price
        print(f"[+] YES! You can buy $10 worth of SOL")
        print(f"  $10 would get you approximately {sol_amount:.6f} SOL")
        print(f"  (at current price of ${buy_price:.4f})")
    else:
        print(f"[!] NO - Minimum order is ${min_dollar:.4f}")
        print(f"  You would need at least ${min_dollar:.4f} to buy SOL")

# Get estimated price for $10 worth of SOL
print("\n[4] Estimate for buying ~$10 worth:")
print("-" * 60)
if sol_price:
    buy_price = float(sol_price["results"][0]['ask_inclusive_of_buy_spread'])
    sol_quantity = 10 / buy_price

    # Try to get estimated price
    estimated = api.get_estimated_price("SOL-USD", "ask", f"{sol_quantity:.6f}")
    if estimated and "results" in estimated:
        print(json.dumps(estimated, indent=2))
    else:
        print(f"[Note] Calculated quantity: {sol_quantity:.6f} SOL for ~$10")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("\nROBINHOOD CRYPTO API NOTES:")
print("- Orders are placed by ASSET QUANTITY (e.g., 0.05 SOL)")
print("- NOT by dollar amount directly")
print("- You calculate: quantity = dollars / price")
print("- Must meet minimum order size requirement")
print("\nEXAMPLE ORDER FOR $10 WORTH:")
if sol_price:
    buy_price = float(sol_price["results"][0]['ask_inclusive_of_buy_spread'])
    sol_quantity = 10 / buy_price
    print(f"""
api.place_order(
    client_order_id=str(uuid.uuid4()),
    side="buy",
    order_type="market",
    symbol="SOL-USD",
    order_config={{"asset_quantity": "{sol_quantity:.6f}"}}
)
""")
print("=" * 60)
