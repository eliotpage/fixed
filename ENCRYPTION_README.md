# Drawings Encryption

This directory contains tools for encrypting and compressing the `drawings.json` file using custom cryptography based on `hashing.py`.

## Files

- **`encrypt_drawings.py`** - Interactive CLI tool for encrypting/decrypting drawings.json
- **`crypto_utils.py`** - Library for encryption/decryption that can be imported in other scripts
- **`hashing.py`** - Core cryptographic primitives (SHA256, RNG)

## How It Works

1. **Compression**: Data is compressed using gzip to reduce size
2. **Key Derivation**: Password is hashed with SHA256 to generate encryption key
3. **Stream Cipher**: RNG (seeded with key) generates keystream for XOR encryption
4. **Output**: Compressed + encrypted binary file

## Interactive CLI Usage

### Encrypt drawings.json

```bash
python encrypt_drawings.py
```

Choose option `1` and enter a password (min 8 characters). This will:
- Read `drawings.json`
- Compress it with gzip
- Encrypt with your password
- Save as `drawings.enc`

### Decrypt drawings.enc

```bash
python encrypt_drawings.py
```

Choose option `2` and enter your password. This will:
- Read `drawings.enc`
- Decrypt with your password
- Decompress the data
- Save as `drawings_decrypted.json`

## Library Usage

Import the crypto utilities in your own scripts:

```python
from crypto_utils import encrypt_file, decrypt_file

# Encrypt a file
stats = encrypt_file('drawings.json', 'drawings.enc', 'my_password')
print(f"Compressed to {stats['compression_ratio']*100:.1f}% of original size")

# Decrypt a file
success = decrypt_file('drawings.enc', 'output.json', 'my_password')
if success:
    print("Decryption successful!")
else:
    print("Wrong password or corrupted file!")
```

### Advanced Usage

```python
from crypto_utils import compress_and_encrypt, decrypt_and_decompress
import json

# Encrypt JSON data directly
data = {'key': 'value'}
json_str = json.dumps(data)
encrypted = compress_and_encrypt(json_str, 'password123')

# Save encrypted data
with open('data.enc', 'wb') as f:
    f.write(encrypted)

# Load and decrypt
with open('data.enc', 'rb') as f:
    encrypted = f.read()

decrypted = decrypt_and_decompress(encrypted, 'password123')
if decrypted:
    data = json.loads(decrypted.decode())
    print(data)
```

## Security Notes

⚠️ **This is a custom encryption implementation for educational/demonstration purposes.**

- Uses stream cipher (XOR with RNG keystream)
- Password hashed with SHA256 for key derivation
- No authentication (HMAC/MAC) - vulnerable to tampering
- RNG is deterministic (good for reproducibility, but simpler than cryptographic RNG)

**For production use, consider:**
- Standard libraries like `cryptography` or `pycryptodome`
- Authenticated encryption (AES-GCM, ChaCha20-Poly1305)
- Key derivation functions like PBKDF2 or Argon2

## Example Session

```bash
$ python encrypt_drawings.py
============================================================
  Drawings JSON Encryption Tool
============================================================

Choose operation:
  1. Encrypt (compress + encrypt drawings.json)
  2. Decrypt (decrypt + decompress drawings.enc)

Enter choice (1 or 2): 1

Enter encryption password: ********
Confirm password: ********

[1/4] Reading drawings.json...
[2/4] Compressing data...
      Original size: 15234 bytes
      Compressed size: 3421 bytes
      Compression ratio: 22.5%
[3/4] Encrypting data...
[4/4] Saving to drawings.enc...

✓ Success! Encrypted file saved as 'drawings.enc'
  Final size: 3421 bytes
```

## Testing

Test the encryption/decryption:

```bash
# Run the library examples
python crypto_utils.py

# Encrypt/decrypt a file
python encrypt_drawings.py
# Choose option 1, encrypt with password "test123"
# Choose option 2, decrypt with password "test123"
# Verify files match
diff drawings.json drawings_decrypted.json
```
