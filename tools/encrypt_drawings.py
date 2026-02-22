#!/usr/bin/env python3
"""
Encrypt and compress drawings.json using custom encryption based on hashing.py
"""
import os
import json
import gzip
import getpass
from hashing import sha256, RNG

INPUT_FILE = 'drawings.json'
OUTPUT_FILE = 'drawings.enc'

def encrypt_data(data, password):
    """
    Encrypt data using stream cipher with RNG keystream
    Args:
        data: bytes to encrypt
        password: password string
    Returns:
        encrypted bytes
    """
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

def decrypt_data(data, password):
    """
    Decrypt data (same as encrypt since XOR is symmetric)
    """
    return encrypt_data(data, password)

def compress_and_encrypt(input_file, output_file, password):
    """
    Read JSON, compress with gzip, encrypt, and save
    """
    print(f"[1/4] Reading {input_file}...")
    with open(input_file, 'r') as f:
        data = f.read()
    
    print(f"[2/4] Compressing data...")
    # Compress the JSON data
    compressed = gzip.compress(data.encode('utf-8'))
    original_size = len(data.encode('utf-8'))
    compressed_size = len(compressed)
    print(f"      Original size: {original_size} bytes")
    print(f"      Compressed size: {compressed_size} bytes")
    print(f"      Compression ratio: {compressed_size/original_size*100:.1f}%")
    
    print(f"[3/4] Encrypting data...")
    # Encrypt the compressed data
    encrypted = encrypt_data(compressed, password)
    
    print(f"[4/4] Saving to {output_file}...")
    # Save encrypted data
    with open(output_file, 'wb') as f:
        f.write(encrypted)
    
    print(f"\n✓ Success! Encrypted file saved as '{output_file}'")
    print(f"  Final size: {len(encrypted)} bytes")

def decompress_and_decrypt(input_file, output_file, password):
    """
    Read encrypted file, decrypt, decompress, and save
    """
    print(f"[1/4] Reading {input_file}...")
    with open(input_file, 'rb') as f:
        encrypted = f.read()
    
    print(f"[2/4] Decrypting data...")
    # Decrypt the data
    decrypted = decrypt_data(encrypted, password)
    
    print(f"[3/4] Decompressing data...")
    # Decompress
    try:
        decompressed = gzip.decompress(decrypted)
    except Exception as e:
        print(f"✗ Decryption failed! Wrong password or corrupted file.")
        return False
    
    print(f"[4/4] Saving to {output_file}...")
    # Save decompressed JSON
    with open(output_file, 'w') as f:
        f.write(decompressed.decode('utf-8'))
    
    print(f"\n✓ Success! Decrypted file saved as '{output_file}'")
    return True

def main():
    print("=" * 60)
    print("  Drawings JSON Encryption Tool")
    print("=" * 60)
    print()
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"✗ Error: {INPUT_FILE} not found!")
        return
    
    print("Choose operation:")
    print("  1. Encrypt (compress + encrypt drawings.json)")
    print("  2. Decrypt (decrypt + decompress drawings.enc)")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == '1':
        # Encrypt mode
        print()
        password = getpass.getpass("Enter encryption password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("✗ Passwords don't match!")
            return
        
        if len(password) < 8:
            print("✗ Password must be at least 8 characters!")
            return
        
        print()
        compress_and_encrypt(INPUT_FILE, OUTPUT_FILE, password)
        
    elif choice == '2':
        # Decrypt mode
        if not os.path.exists(OUTPUT_FILE):
            print(f"✗ Error: {OUTPUT_FILE} not found!")
            return
        
        print()
        password = getpass.getpass("Enter decryption password: ")
        print()
        
        output = 'drawings_decrypted.json'
        success = decompress_and_decrypt(OUTPUT_FILE, output, password)
        
        if success:
            print()
            print("You can now compare the decrypted file with the original:")
            print(f"  diff {INPUT_FILE} {output}")
    
    else:
        print("✗ Invalid choice!")

if __name__ == '__main__':
    main()
