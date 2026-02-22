"""
Crypto utilities for encrypting/decrypting files using hashing.py
Can be imported as a library or used standalone
"""
import gzip
from hashing import sha256, RNG

def encrypt_bytes(data, password):
    """
    Encrypt bytes using stream cipher with RNG keystream
    
    Args:
        data: bytes to encrypt
        password: password string or bytes
    
    Returns:
        encrypted bytes
    """
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Generate encryption key from password using SHA256
    key_hash = sha256(password)
    # Convert hex hash to integer seed for RNG
    seed = int(key_hash[:16], 16)  # Use first 64 bits as seed
    
    # Initialize RNG with seed
    rng = RNG(seed)
    
    # Generate keystream and XOR with data
    encrypted = bytearray()
    for byte in data:
        # Get next random byte from RNG
        key_byte = rng.next() & 0xFF
        # XOR with data byte
        encrypted.append(byte ^ key_byte)
    
    return bytes(encrypted)

def decrypt_bytes(data, password):
    """
    Decrypt bytes (XOR is symmetric, so same as encrypt)
    
    Args:
        data: encrypted bytes
        password: password string or bytes
    
    Returns:
        decrypted bytes
    """
    return encrypt_bytes(data, password)

def compress_and_encrypt(data, password):
    """
    Compress data with gzip and then encrypt
    
    Args:
        data: bytes or string to compress and encrypt
        password: password string
    
    Returns:
        compressed and encrypted bytes
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Compress
    compressed = gzip.compress(data)
    
    # Encrypt
    encrypted = encrypt_bytes(compressed, password)
    
    return encrypted

def decrypt_and_decompress(data, password):
    """
    Decrypt and decompress data
    
    Args:
        data: encrypted and compressed bytes
        password: password string
    
    Returns:
        decompressed bytes, or None if decryption failed
    """
    # Decrypt
    decrypted = decrypt_bytes(data, password)
    
    # Decompress
    try:
        decompressed = gzip.decompress(decrypted)
        return decompressed
    except Exception:
        # Wrong password or corrupted data
        return None

def encrypt_file(input_path, output_path, password, compress=True):
    """
    Encrypt a file and save to output path
    
    Args:
        input_path: path to input file
        output_path: path to save encrypted file
        password: encryption password
        compress: whether to compress before encrypting (default: True)
    
    Returns:
        dict with statistics (original_size, final_size, etc.)
    """
    # Read input file
    with open(input_path, 'rb') as f:
        data = f.read()
    
    original_size = len(data)
    
    # Encrypt (with optional compression)
    if compress:
        encrypted = compress_and_encrypt(data, password)
    else:
        encrypted = encrypt_bytes(data, password)
    
    # Write output file
    with open(output_path, 'wb') as f:
        f.write(encrypted)
    
    final_size = len(encrypted)
    
    return {
        'original_size': original_size,
        'final_size': final_size,
        'compression_ratio': final_size / original_size if original_size > 0 else 0,
        'compressed': compress
    }

def decrypt_file(input_path, output_path, password, compressed=True):
    """
    Decrypt a file and save to output path
    
    Args:
        input_path: path to encrypted file
        output_path: path to save decrypted file
        password: decryption password
        compressed: whether file was compressed before encryption
    
    Returns:
        True if successful, False if decryption failed
    """
    # Read encrypted file
    with open(input_path, 'rb') as f:
        encrypted = f.read()
    
    # Decrypt (with optional decompression)
    if compressed:
        decrypted = decrypt_and_decompress(encrypted, password)
        if decrypted is None:
            return False
    else:
        decrypted = decrypt_bytes(encrypted, password)
    
    # Write output file
    with open(output_path, 'wb') as f:
        f.write(decrypted)
    
    return True

# Example usage
if __name__ == '__main__':
    print("Crypto Utils Library")
    print("=" * 50)
    print()
    print("Example: Encrypt and decrypt a message")
    
    # Example 1: Simple encryption
    message = "Hello, this is a secret message!"
    password = "my_secret_password"
    
    print(f"Original: {message}")
    
    # Encrypt
    encrypted = encrypt_bytes(message.encode(), password)
    print(f"Encrypted (hex): {encrypted.hex()[:50]}...")
    
    # Decrypt
    decrypted = decrypt_bytes(encrypted, password)
    print(f"Decrypted: {decrypted.decode()}")
    
    print()
    print("Example: Compress and encrypt")
    
    # Example 2: With compression
    long_message = "abc" * 100  # Repetitive data compresses well
    compressed_encrypted = compress_and_encrypt(long_message, password)
    
    print(f"Original size: {len(long_message)} bytes")
    print(f"Compressed+Encrypted: {len(compressed_encrypted)} bytes")
    print(f"Compression ratio: {len(compressed_encrypted)/len(long_message)*100:.1f}%")
    
    # Decrypt and decompress
    decrypted_decompressed = decrypt_and_decompress(compressed_encrypted, password)
    print(f"Match: {decrypted_decompressed.decode() == long_message}")
