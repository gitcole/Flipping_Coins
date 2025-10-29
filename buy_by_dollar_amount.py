"""
Helper functions to buy crypto by dollar amount instead of asset quantity
"""

from crypto_trading_bot_enhanced import CryptoAPITrading
import uuid
import json


def calculate_quantity_from_dollars(api: CryptoAPITrading, symbol: str, dollars: float) -> dict:
    """
    Calculate how much crypto you can buy with a given dollar amount.

    Args:
        api: CryptoAPITrading instance
        symbol: Trading pair like "SOL-USD", "BTC-USD"
        dollars: Dollar amount you want to spend

    Returns:
        Dictionary with quantity, price, and validation info
    """
    # Get current price
    price_data = api.get_best_bid_ask(symbol)

    if not price_data or "results" not in price_data:
        return {"error": "Failed to get price data"}

    # Get buy price (ask price with spread)
    buy_price = float(price_data["results"][0]["ask_inclusive_of_buy_spread"])
    current_price = float(price_data["results"][0]["price"])

    # Calculate quantity
    quantity = dollars / buy_price

    # Get trading pair info for validation
    pair_info = api.get_trading_pairs(symbol)

    if not pair_info or "results" not in pair_info:
        return {"error": "Failed to get trading pair info"}

    min_order = float(pair_info["results"][0]["min_order_size"])
    max_order = float(pair_info["results"][0]["max_order_size"])
    asset_increment = float(pair_info["results"][0]["asset_increment"])

    # Round to proper increment
    quantity_rounded = round(quantity / asset_increment) * asset_increment
    actual_cost = quantity_rounded * buy_price

    # Validate
    is_valid = min_order <= quantity_rounded <= max_order

    return {
        "symbol": symbol,
        "dollars_requested": dollars,
        "quantity": quantity_rounded,
        "current_price": current_price,
        "buy_price": buy_price,
        "actual_cost": actual_cost,
        "min_order_size": min_order,
        "max_order_size": max_order,
        "is_valid": is_valid,
        "validation_message": "OK" if is_valid else f"Order must be between {min_order} and {max_order}"
    }


def buy_crypto_by_dollars(
    api: CryptoAPITrading,
    symbol: str,
    dollars: float,
    confirm: bool = False
) -> dict:
    """
    Buy crypto using a dollar amount instead of asset quantity.

    Args:
        api: CryptoAPITrading instance
        symbol: Trading pair like "SOL-USD", "BTC-USD"
        dollars: Dollar amount to spend
        confirm: Set to True to actually place the order (safety feature)

    Returns:
        Order response or preview
    """
    # Calculate quantity
    calc = calculate_quantity_from_dollars(api, symbol, dollars)

    if "error" in calc:
        return calc

    if not calc["is_valid"]:
        return {
            "error": "Invalid order size",
            "details": calc["validation_message"],
            "calculation": calc
        }

    # Preview mode (safety feature)
    if not confirm:
        return {
            "preview": True,
            "message": "This is a PREVIEW. Set confirm=True to place the order.",
            "order_details": {
                "symbol": calc["symbol"],
                "side": "buy",
                "type": "market",
                "quantity": calc["quantity"],
                "estimated_cost": f"${calc['actual_cost']:.2f}",
                "current_price": f"${calc['current_price']:.2f}"
            },
            "to_execute": f"buy_crypto_by_dollars(api, '{symbol}', {dollars}, confirm=True)"
        }

    # Place the actual order
    order = api.place_order(
        client_order_id=str(uuid.uuid4()),
        side="buy",
        order_type="market",
        symbol=symbol,
        order_config={"asset_quantity": str(calc["quantity"])}
    )

    return {
        "order_placed": True,
        "calculation": calc,
        "order_response": order
    }


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("BUY CRYPTO BY DOLLAR AMOUNT - HELPER")
    print("=" * 60)

    api = CryptoAPITrading(verbose=True)

    # Example 1: Calculate what $10 buys you
    print("\n[Example 1] Calculate $10 worth of SOL")
    print("-" * 60)
    calc = calculate_quantity_from_dollars(api, "SOL-USD", 10)
    print(json.dumps(calc, indent=2))

    # Example 2: Preview a $10 SOL purchase (doesn't actually buy)
    print("\n[Example 2] Preview $10 SOL purchase")
    print("-" * 60)
    preview = buy_crypto_by_dollars(api, "SOL-USD", 10, confirm=False)
    print(json.dumps(preview, indent=2))

    # Example 3: Calculate different dollar amounts
    print("\n[Example 3] Compare different amounts")
    print("-" * 60)
    for amount in [5, 10, 20, 50]:
        calc = calculate_quantity_from_dollars(api, "SOL-USD", amount)
        if "error" not in calc:
            print(f"${amount:>3} = {calc['quantity']:.6f} SOL (actual cost: ${calc['actual_cost']:.2f})")

    # Example 4: Multiple coins
    print("\n[Example 4] $10 worth of different coins")
    print("-" * 60)
    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD"]:
        calc = calculate_quantity_from_dollars(api, symbol, 10)
        if "error" not in calc:
            asset = symbol.split("-")[0]
            print(f"{asset:>5}: {calc['quantity']:.6f} (price: ${calc['current_price']:.2f})")

    print("\n" + "=" * 60)
    print("TO ACTUALLY BUY:")
    print("=" * 60)
    print("""
# This will ACTUALLY execute a trade!
result = buy_crypto_by_dollars(api, "SOL-USD", 10, confirm=True)
print(json.dumps(result, indent=2))
    """)
    print("=" * 60)
