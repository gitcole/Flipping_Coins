import base64
import datetime
import requests
from nacl.signing import SigningKey

API_KEY = "rh-api-db9d13e4-6bf2-4830-92ed-48a8b542208c"
BASE64_PRIVATE_KEY = "u/NAwNiSEvkLAqb14nXAWmTsC9SqRcwbkTzvG4wTL6g="

print("=" * 60)
print("DIAGNOSTIC TEST - API REQUEST DETAILS")
print("=" * 60)

# Prepare request
private_key_seed = base64.b64decode(BASE64_PRIVATE_KEY)
private_key = SigningKey(private_key_seed)

timestamp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
path = "/api/v1/crypto/trading/accounts/"
method = "GET"
body = ""

# Create message to sign
message_to_sign = f"{API_KEY}{timestamp}{path}{method}{body}"
signed = private_key.sign(message_to_sign.encode("utf-8"))
signature = base64.b64encode(signed.signature).decode("utf-8")

print(f"\nAPI Key: {API_KEY}")
print(f"Timestamp: {timestamp}")
print(f"Path: {path}")
print(f"Method: {method}")
print(f"Body: '{body}'")
print(f"\nMessage to sign:")
print(f"  {message_to_sign}")
print(f"\nMessage length: {len(message_to_sign)} characters")
print(f"Message bytes: {message_to_sign.encode('utf-8')}")
print(f"\nGenerated Signature: {signature}")

# Prepare headers
headers = {
    "x-api-key": API_KEY,
    "x-signature": signature,
    "x-timestamp": str(timestamp),
}

print(f"\nHeaders:")
for key, value in headers.items():
    print(f"  {key}: {value}")

# Make request
url = f"https://trading.robinhood.com{path}"
print(f"\nFull URL: {url}")
print("\nMaking request...")
print("-" * 60)

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nResponse Body:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TROUBLESHOOTING STEPS:")
print("=" * 60)
print("1. Verify the public key registered on Robinhood:")
print(f"   KVnS3tcaYmyGIsrNNKwfdZ6jLaeZ+GE9fM6DDuv6Ke4=")
print("\n2. Check if the API key status is 'Active' in the portal")
print("\n3. Ensure you registered the key in the CRYPTO section")
print("   (not regular stocks)")
print("\n4. Try deleting and recreating the API credential if needed")
print("=" * 60)
