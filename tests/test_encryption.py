"""
tests/test_encryption.py — Unit tests for core/encryption.py
"""

import os

import pytest
from pathlib import Path

from core.encryption import (
    generate_aes_key,
    generate_rsa_keypair,
    encrypt_file,
    decrypt_file,
    DecryptionError,
    load_public_key_from_file,
)


class TestAESKey:
    def test_generate_aes_key_returns_32_bytes(self):
        """AES-256 key must be exactly 32 bytes."""
        key = generate_aes_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_generate_aes_key_is_random(self):
        """Two generated keys should never be equal."""
        key1 = generate_aes_key()
        key2 = generate_aes_key()
        assert key1 != key2


class TestRSAKeypair:
    def test_generate_keypair_returns_pem_bytes(self):
        """Both keys should be PEM-encoded bytes."""
        private_pem, public_pem = generate_rsa_keypair()
        assert isinstance(private_pem, bytes)
        assert isinstance(public_pem, bytes)
        assert private_pem.startswith(b"-----BEGIN")
        assert public_pem.startswith(b"-----BEGIN")

    def test_keypair_size_is_4096(self):
        """RSA key size should be 4096 bits."""
        from cryptography.hazmat.primitives import serialization
        private_pem, _ = generate_rsa_keypair()
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        assert private_key.key_size == 4096


class TestEncryptDecryptRoundtrip:
    def test_roundtrip_small_file(self, tmp_path):
        """Encrypt a small text file, decrypt it, verify contents match."""
        private_pem, public_pem = generate_rsa_keypair()

        plaintext = b"Hello, Lazarus! This is a secret message."
        plaintext_path = tmp_path / "secret.txt"
        plaintext_path.write_bytes(plaintext)

        output_dir = tmp_path / "encrypted"
        encrypted_path, key_blob = encrypt_file(
            plaintext_path=plaintext_path,
            recipient_public_key_pem=public_pem,
            output_dir=output_dir,
        )

        decrypted_path = tmp_path / "decrypted.txt"
        decrypt_file(
            encrypted_path=encrypted_path,
            key_blob_b64=key_blob,
            private_key_pem=private_pem,
            output_path=decrypted_path,
        )

        assert decrypted_path.read_bytes() == plaintext

    def test_roundtrip_large_file(self, tmp_path):
        """Encrypt/decrypt a ~10MB binary file."""
        private_pem, public_pem = generate_rsa_keypair()

        plaintext = os.urandom(10 * 1024 * 1024)
        plaintext_path = tmp_path / "large.bin"
        plaintext_path.write_bytes(plaintext)

        output_dir = tmp_path / "encrypted"
        encrypted_path, key_blob = encrypt_file(
            plaintext_path=plaintext_path,
            recipient_public_key_pem=public_pem,
            output_dir=output_dir,
        )

        decrypted_path = tmp_path / "decrypted.bin"
        decrypt_file(
            encrypted_path=encrypted_path,
            key_blob_b64=key_blob,
            private_key_pem=private_pem,
            output_path=decrypted_path,
        )

        assert decrypted_path.read_bytes() == plaintext

    def test_wrong_private_key_fails(self, tmp_path):
        """Decryption with a different private key should raise an error."""
        keypair_a = generate_rsa_keypair()
        keypair_b = generate_rsa_keypair()

        plaintext = b"Secret message"
        plaintext_path = tmp_path / "secret.txt"
        plaintext_path.write_bytes(plaintext)

        output_dir = tmp_path / "encrypted"
        encrypted_path, key_blob = encrypt_file(
            plaintext_path=plaintext_path,
            recipient_public_key_pem=keypair_a[1],
            output_dir=output_dir,
        )

        with pytest.raises(Exception):
            decrypt_file(
                encrypted_path=encrypted_path,
                key_blob_b64=key_blob,
                private_key_pem=keypair_b[0],
                output_path=tmp_path / "out.txt",
            )

    def test_tampered_ciphertext_fails(self, tmp_path):
        """AES-GCM authentication tag should detect tampering."""
        private_pem, public_pem = generate_rsa_keypair()

        plaintext = b"Secret message"
        plaintext_path = tmp_path / "secret.txt"
        plaintext_path.write_bytes(plaintext)

        output_dir = tmp_path / "encrypted"
        encrypted_path, key_blob = encrypt_file(
            plaintext_path=plaintext_path,
            recipient_public_key_pem=public_pem,
            output_dir=output_dir,
        )

        ciphertext = encrypted_path.read_bytes()
        tampered = bytearray(ciphertext)
        tampered[16] ^= 0xFF
        encrypted_path.write_bytes(bytes(tampered))

        with pytest.raises(DecryptionError):
            decrypt_file(
                encrypted_path=encrypted_path,
                key_blob_b64=key_blob,
                private_key_pem=private_pem,
                output_path=tmp_path / "out.txt",
            )
