#!/usr/bin/env python3
"""
Quick decrypt: Decrypt drawings.enc with a single command
Usage: python quick_decrypt.py [password] [output_file]
"""
import sys
from crypto_utils import decrypt_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_decrypt.py <password> [output_file]")
        print("Example: python quick_decrypt.py my_secret_password")
        print("         python quick_decrypt.py my_secret_password output.json")
        sys.exit(1)
    
    password = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else 'drawings_decrypted.json'
    
    try:
        print(f"Decrypting drawings.enc...")
        success = decrypt_file('drawings.enc', output, password, compressed=True)
        
        if success:
            print(f"✓ Success! Decrypted to: {output}")
        else:
            print("✗ Decryption failed! Wrong password or corrupted file.")
            sys.exit(1)
        
    except FileNotFoundError:
        print("✗ drawings.enc not found!")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
