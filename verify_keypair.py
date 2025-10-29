import nacl.signing
import base64

print("=" * 60)
print("VERIFYING KEY PAIR")
print("=" * 60)

# Our generated keys
private_key_base64 = "u/NAwNiSEvkLAqb14nXAWmTsC9SqRcwbkTzvG4wTL6g="
public_key_base64 = "KVnS3tcaYmyGIsrNNKwfdZ6jLaeZ+GE9fM6DDuv6Ke4="

# Decode keys
private_key_seed = base64.b64decode(private_key_base64)
public_key_bytes = base64.b64decode(public_key_base64)

# Create key objects
private_key = nacl.signing.SigningKey(private_key_seed)
public_key_from_private = private_key.verify_key
public_key = nacl.signing.VerifyKey(public_key_bytes)

# Check if they match
derived_public_key_base64 = base64.b64encode(bytes(public_key_from_private)).decode()
provided_public_key_base64 = public_key_base64

print(f"\nPrivate Key: {private_key_base64}")
print(f"\nPublic Key (provided): {provided_public_key_base64}")
print(f"Public Key (derived from private): {derived_public_key_base64}")
print(f"\nKeys Match: {derived_public_key_base64 == provided_public_key_base64}")

# Test signing and verification
test_message = "test message"
signed = private_key.sign(test_message.encode())

try:
    public_key.verify(signed.message, signed.signature)
    print("\n[+] Signature verification: SUCCESS")
    print("The private and public keys are a valid pair!")
except:
    print("\n[!] Signature verification: FAILED")
    print("The keys do NOT form a valid pair!")

print("\n" + "=" * 60)
