#!/usr/bin/env python3
"""
Quick encrypt: Encrypt drawings.json with a single command
Usage: python quick_encrypt.py [password]
"""
import sys
from crypto_utils import encrypt_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_encrypt.py <password>")
        print("Example: python quick_encrypt.py my_secret_password")
        sys.exit(1)
    
    password = sys.argv[1]
    
    if len(password) < 8:
        print("✗ Password must be at least 8 characters!")
        sys.exit(1)
    
    try:
        print("Encrypting drawings.json...")
        stats = encrypt_file('drawings.json', 'drawings.enc', password, compress=True)
        
        print(f"✓ Success!")
        print(f"  Original: {stats['original_size']:,} bytes")
        print(f"  Encrypted: {stats['final_size']:,} bytes")
        print(f"  Saved: {(1-stats['compression_ratio'])*100:.1f}% space")
        print(f"\nEncrypted file: drawings.enc")
        
    except FileNotFoundError:
        print("✗ drawings.json not found!")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
