#!/usr/bin/env python3
"""
Lazarus Protocol — Standalone Decryption Script
===============================================
Requirements: pip install cryptography
Usage:        python decrypt.py --key key_blob.txt

This script decrypts your inherited vault from Lazarus Protocol.
It has zero external dependencies (only the 'cryptography' library).
"""

import argparse
import base64
import getpass
import os
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag
except ImportError:
    print("ERROR: cryptography library not installed.")
    print("Run: pip install cryptography")
    sys.exit(1)

GCM_NONCE_SIZE = 12


def _is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check if resolved path stays within base directory (prevent path traversal)."""
    try:
        resolved = path.resolve()
        base_resolved = base_dir.resolve()
        return str(resolved).startswith(str(base_resolved))
    except (OSError, RuntimeError):
        return False


def decrypt(encrypted_path, key_blob_b64, private_key_pem, password=None):
    """Decrypt the vault file using the beneficiary's private key."""
    enc_path = Path(encrypted_path).resolve()
    if not enc_path.exists():
        print(f"ERROR: Encrypted file not found: {encrypted_path}")
        sys.exit(1)
    if not enc_path.is_file():
        print(f"ERROR: Path is not a file: {encrypted_path}")
        sys.exit(1)

    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=password
        )
    except Exception as e:
        print("ERROR: Failed to load private key.")
        print("  - Ensure the file is a valid RSA private key (.pem)")
        print("  - If encrypted, ensure you entered the correct password")
        print(f"  - Details: {e}")
        sys.exit(1)

    encrypted_aes_key = base64.b64decode(key_blob_b64)
    try:
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception as e:
        print("ERROR: Decryption failed — wrong key or corrupted data.")
        print("  - Verify you are using the correct private key")
        print("  - Verify key_blob matches this encrypted file")
        print(f"  - Details: {e}")
        sys.exit(1)

    raw = enc_path.read_bytes()
    nonce = raw[:GCM_NONCE_SIZE]
    ciphertext = raw[GCM_NONCE_SIZE:]

    try:
        plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, associated_data=None)
    except InvalidTag:
        print("ERROR: Authentication failed. File may be corrupted or wrong key.")
        sys.exit(1)

    return plaintext


def main():
    parser = argparse.ArgumentParser(
        description="Lazarus Protocol — Decrypt your inheritance vault"
    )
    parser.add_argument(
        "--key", "-k",
        required=True,
        help="Path to key_blob.txt (base64-encoded RSA-encrypted AES key)"
    )
    parser.add_argument(
        "--encrypted", "-e",
        help="Path to encrypted_secrets.bin (will prompt if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (will prompt if not provided)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Lazarus Protocol — Inheritance Decryption Tool")
    print("=" * 60)
    print()

    script_dir = Path(os.path.dirname(os.path.abspath(__file__))) if "__file__" in dir() else Path.cwd()

    key_input = args.key.strip()
    key_blob_path = Path(key_input).resolve()

    if not _is_safe_path(key_blob_path, script_dir):
        print("ERROR: Path traversal detected. Only relative paths allowed.")
        sys.exit(1)

    if not key_blob_path.exists():
        print(f"ERROR: key_blob file not found: {key_input}")
        sys.exit(1)

    try:
        key_blob = key_blob_path.read_text().strip()
    except Exception as e:
        print(f"ERROR: Failed to read key_blob: {e}")
        sys.exit(1)

    if args.encrypted:
        enc_path = Path(args.encrypted).resolve()
    else:
        enc_input = input("Path to encrypted_secrets.bin: ").strip()
        enc_path = Path(enc_input).resolve()

    if not _is_safe_path(enc_path, script_dir):
        print("ERROR: Path traversal detected. Only relative paths allowed.")
        sys.exit(1)

    if args.output:
        out_path = Path(args.output).resolve()
    else:
        out_input = input("Output file path (e.g. secrets.pdf): ").strip()
        out_path = Path(out_input).resolve()

    if not _is_safe_path(out_path, script_dir):
        print("ERROR: Path traversal detected. Only relative paths allowed.")
        sys.exit(1)

    priv_input = input("Path to your private key (.pem): ").strip()
    priv_path = Path(priv_input).resolve()

    if not _is_safe_path(priv_path, script_dir):
        print("ERROR: Path traversal detected. Only relative paths allowed.")
        sys.exit(1)

    if not priv_path.exists():
        print(f"ERROR: Private key file not found: {priv_input}")
        sys.exit(1)

    try:
        priv_pem = priv_path.read_bytes()
        serialization.load_pem_private_key(priv_pem, password=None)
        password = None
        print("(Unencrypted key detected)")
    except Exception:
        pw_str = getpass.getpass("Private key password: ")
        password = pw_str.encode()

    print("\nDecrypting...")
    try:
        plaintext = decrypt(enc_path, key_blob, priv_pem, password)
        out_path.write_bytes(plaintext)
        print(f"\nDecrypted file saved to: {out_path}")
        print("You can now open it with any standard application.")
    except Exception as e:
        print(f"ERROR: Decryption failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
