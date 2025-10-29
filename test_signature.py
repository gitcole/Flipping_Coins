import nacl.signing
import base64
import json

# Test with the documented example to verify our signature generation
print("=" * 60)
print("TESTING SIGNATURE GENERATION")
print("=" * 60)

# Example from documentation
private_key_base64 = "xQnTJVeQLmw1/Mg2YimEViSpw/SdJcgNXZ5kQkAXNPU="
api_key = "rh-api-6148effc-c0b1-486c-8940-a1d099456be6"
current_timestamp = "1698708981"
path = "/api/v1/crypto/trading/orders/"
method = "POST"
body = {
    "client_order_id": "131de903-5a9c-4260-abc1-28d562a5dcf0",
    "side": "buy",
    "symbol": "BTC-USD",
    "type": "market",
    "market_order_config": {
        "asset_quantity": "0.1"
    },
}

expected_signature = "q/nEtxp/P2Or3hph3KejBqnw5o9qeuQ+hYRnB56FaHbjDsNUY9KhB1asMxohDnzdVFSD7StaTqjSd9U9HvaRAw=="

# Create private key
private_key_seed = base64.b64decode(private_key_base64)
private_key = nacl.signing.SigningKey(private_key_seed)

# Test 1: With JSON string (as the documentation shows)
body_str = json.dumps(body)
message1 = f"{api_key}{current_timestamp}{path}{method}{body_str}"
print(f"\nTest 1: Using json.dumps()")
print(f"Message: {message1}")
signed1 = private_key.sign(message1.encode("utf-8"))
signature1 = base64.b64encode(signed1.signature).decode("utf-8")
print(f"Generated Signature: {signature1}")
print(f"Expected Signature:  {expected_signature}")
print(f"Match: {signature1 == expected_signature}")

# Test 2: Without spaces in JSON
body_str_no_space = json.dumps(body, separators=(',', ':'))
message2 = f"{api_key}{current_timestamp}{path}{method}{body_str_no_space}"
print(f"\nTest 2: Using json.dumps() with no spaces")
print(f"Message: {message2}")
signed2 = private_key.sign(message2.encode("utf-8"))
signature2 = base64.b64encode(signed2.signature).decode("utf-8")
print(f"Generated Signature: {signature2}")
print(f"Expected Signature:  {expected_signature}")
print(f"Match: {signature2 == expected_signature}")

# Test 3: Manually constructed JSON string
body_str_manual = '{"client_order_id":"131de903-5a9c-4260-abc1-28d562a5dcf0","side":"buy","type":"market","symbol":"BTC-USD","market_order_config":{"asset_quantity":"0.1"}}'
message3 = f"{api_key}{current_timestamp}{path}{method}{body_str_manual}"
print(f"\nTest 3: Using manually constructed JSON")
print(f"Message: {message3}")
signed3 = private_key.sign(message3.encode("utf-8"))
signature3 = base64.b64encode(signed3.signature).decode("utf-8")
print(f"Generated Signature: {signature3}")
print(f"Expected Signature:  {expected_signature}")
print(f"Match: {signature3 == expected_signature}")

print("\n" + "=" * 60)

# Now test with our actual credentials for a GET request
print("\nTesting with actual credentials (GET request):")
print("=" * 60)

our_api_key = "rh-api-db9d13e4-6bf2-4830-92ed-48a8b542208c"
our_private_key_base64 = "u/NAwNiSEvkLAqb14nXAWmTsC9SqRcwbkTzvG4wTL6g="

our_private_key_seed = base64.b64decode(our_private_key_base64)
our_private_key = nacl.signing.SigningKey(our_private_key_seed)

# For GET request, body should be empty
import time
timestamp = int(time.time())
path = "/api/v1/crypto/trading/accounts/"
method = "GET"
body = ""

message = f"{our_api_key}{timestamp}{path}{method}{body}"
print(f"Message to sign: {message}")
signed = our_private_key.sign(message.encode("utf-8"))
signature = base64.b64encode(signed.signature).decode("utf-8")

print(f"\nGenerated signature: {signature}")
print(f"Timestamp: {timestamp}")
print(f"API Key: {our_api_key}")
print(f"Path: {path}")
print(f"Method: {method}")
print(f"Body: '{body}'")

print("\n" + "=" * 60)
