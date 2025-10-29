"""
Buy $5 worth of SOL
"""

from buy_by_dollar_amount import buy_crypto_by_dollars, calculate_quantity_from_dollars, CryptoAPITrading
import json

print("=" * 60)
print("BUY $5 WORTH OF SOLANA (SOL)")
print("=" * 60)

api = CryptoAPITrading(verbose=True)

# Step 1: Calculate what $5 will buy
print("\n[STEP 1] Calculating $5 worth of SOL...")
print("-" * 60)
calc = calculate_quantity_from_dollars(api, "SOL-USD", 5)

if "error" in calc:
    print(f"Error: {calc['error']}")
    exit(1)

print(f"\nCalculation Results:")
print(f"  Symbol: {calc['symbol']}")
print(f"  Current Price: ${calc['current_price']:.2f}")
print(f"  Buy Price (with spread): ${calc['buy_price']:.2f}")
print(f"  SOL Quantity: {calc['quantity']:.6f}")
print(f"  Actual Cost: ${calc['actual_cost']:.2f}")
print(f"  Valid Order: {calc['is_valid']}")

# Step 2: Preview the order
print("\n[STEP 2] Order Preview (NOT executed yet)")
print("-" * 60)
preview = buy_crypto_by_dollars(api, "SOL-USD", 5, confirm=False)
print(json.dumps(preview, indent=2))

# Step 3: Execute the order
print("\n[STEP 3] Executing Order...")
print("-" * 60)
print("Placing BUY order for SOL-USD...")

result = buy_crypto_by_dollars(api, "SOL-USD", 5, confirm=True)

if "error" in result:
    print(f"\n[!] Order FAILED")
    print(json.dumps(result, indent=2))
else:
    print(f"\n[+] Order PLACED Successfully!")
    print("\nOrder Details:")
    print(json.dumps(result, indent=2))

    # Get updated holdings
    print("\n[STEP 4] Checking Updated Holdings...")
    print("-" * 60)
    holdings = api.get_holdings("SOL")

    if holdings and "results" in holdings:
        if holdings["results"]:
            sol_holding = holdings["results"][0]
            print(f"\nYour SOL Holdings:")
            print(f"  Total Quantity: {sol_holding['total_quantity']}")
            print(f"  Available for Trading: {sol_holding['quantity_available_for_trading']}")
        else:
            print("SOL holdings not yet reflected (may take a moment to update)")

    # Get updated account info
    print("\n[STEP 5] Checking Updated Account Balance...")
    print("-" * 60)
    account = api.get_account()
    if account:
        print(f"\nBuying Power: ${account['buying_power']}")
        print(f"Account Status: {account['status']}")

print("\n" + "=" * 60)
print("TRANSACTION COMPLETE")
print("=" * 60)
