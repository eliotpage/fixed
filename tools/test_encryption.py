#!/usr/bin/env python3
"""
Quick test of file encryption with drawings.json
"""
from crypto_utils import encrypt_file, decrypt_file
import os

def main():
    print("Testing file encryption with drawings.json")
    print("=" * 60)
    
    # Check if drawings.json exists
    if not os.path.exists('drawings.json'):
        print("✗ drawings.json not found!")
        return
    
    password = "test_password_123"
    
    print("\n[1/3] Encrypting drawings.json...")
    stats = encrypt_file('drawings.json', 'drawings_test.enc', password, compress=True)
    
    print(f"  Original size: {stats['original_size']:,} bytes")
    print(f"  Encrypted size: {stats['final_size']:,} bytes")
    print(f"  Compression ratio: {stats['compression_ratio']*100:.1f}%")
    print(f"  Space saved: {(1-stats['compression_ratio'])*100:.1f}%")
    
    print("\n[2/3] Decrypting drawings_test.enc...")
    success = decrypt_file('drawings_test.enc', 'drawings_test_decrypted.json', password)
    
    if success:
        print("  ✓ Decryption successful!")
    else:
        print("  ✗ Decryption failed!")
        return
    
    print("\n[3/3] Verifying files match...")
    # Compare original and decrypted
    with open('drawings.json', 'rb') as f:
        original = f.read()
    with open('drawings_test_decrypted.json', 'rb') as f:
        decrypted = f.read()
    
    if original == decrypted:
        print("  ✓ Files match perfectly!")
    else:
        print("  ✗ Files don't match!")
        return
    
    # Test with wrong password
    print("\n[Test] Trying wrong password...")
    success = decrypt_file('drawings_test.enc', 'drawings_wrong.json', 'wrong_password')
    if not success:
        print("  ✓ Wrong password correctly rejected!")
    else:
        print("  ✗ Wrong password was accepted (shouldn't happen)")
    
    # Cleanup
    print("\n[Cleanup] Removing test files...")
    os.remove('drawings_test.enc')
    os.remove('drawings_test_decrypted.json')
    if os.path.exists('drawings_wrong.json'):
        os.remove('drawings_wrong.json')
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! Encryption system working correctly.")
    print("=" * 60)

if __name__ == '__main__':
    main()
