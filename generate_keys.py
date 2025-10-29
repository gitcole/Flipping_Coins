import nacl.signing
import base64

# Generate an Ed25519 keypair
private_key = nacl.signing.SigningKey.generate()
public_key = private_key.verify_key

# Convert keys to base64 strings
private_key_base64 = base64.b64encode(private_key.encode()).decode()
public_key_base64 = base64.b64encode(public_key.encode()).decode()

# Print the keys in base64 format
print("=" * 60)
print("ROBINHOOD CRYPTO API - KEY GENERATION")
print("=" * 60)
print("\nPrivate Key (Base64):")
print(private_key_base64)
print("\nPublic Key (Base64):")
print(public_key_base64)
print("\n" + "=" * 60)
print("IMPORTANT SECURITY NOTES:")
print("=" * 60)
print("1. NEVER share your private key with anyone")
print("2. Robinhood will NEVER ask for your private key")
print("3. Store your private key securely (encrypted)")
print("4. You'll need the PUBLIC key for the Robinhood API portal")
print("5. You'll need the PRIVATE key for your trading bot")
print("=" * 60)
