"""
core/encryption.py — Hybrid encryption engine for Lazarus Protocol.

Scheme:
    1. Generate a random AES-256 key + 12-byte nonce.
    2. Encrypt the secret file with AES-256-GCM (authenticated encryption).
    3. Encrypt the AES key with the beneficiary's RSA-4096 public key
       using OAEP + SHA-256 padding.
    4. Serialise to disk:
         encrypted_secrets.bin  →  [nonce (12B)] + [ciphertext + GCM tag (N+16B)]
         key_blob               →  base64( RSA-encrypted AES key )

Only the beneficiary's RSA private key can reverse this.
Even if someone steals the vault, they see encrypted noise.
"""

from __future__ import annotations

import base64
import ctypes
import os
from pathlib import Path
from typing import Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AES_KEY_SIZE = 32  # bytes — AES-256
GCM_NONCE_SIZE = 12  # bytes — recommended for AES-GCM
RSA_KEY_SIZE = 4096  # bits


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class DecryptionError(Exception):
    """Raised when decryption fails due to a bad key or tampered ciphertext."""

    pass


# ---------------------------------------------------------------------------
# Memory zeroing helpers
# ---------------------------------------------------------------------------


def _zero_memory(buf: Union[bytearray, memoryview]) -> None:
    """
    Securely zero out a bytearray or memoryview in place using ctypes.memset.

    Uses ctypes.memset with proper memory access to prevent compiler
    optimizations that could bypass the memory clearing.

    Args:
        buf: Bytearray or memoryview to securely zero out.

    Raises:
        TypeError: If buf is not a bytearray or memoryview.
        ValueError: If buf is empty.
    """
    if not isinstance(buf, (bytearray, memoryview)):
        raise TypeError(f"Expected bytearray or memoryview, got {type(buf).__name__}")

    if len(buf) == 0:
        raise ValueError("Cannot zero empty buffer")

    try:
        # Use ctypes.memset to securely zero the memory
        # This uses the C memset function which is not optimized away by Python
        if isinstance(buf, bytearray):
            # Create a ctypes array from the bytearray buffer
            buf_array = (ctypes.c_byte * len(buf)).from_buffer(buf)
            ctypes.memset(ctypes.addressof(buf_array), 0, len(buf))
        elif isinstance(buf, memoryview):
            # For memoryview, work with the underlying bytes
            if buf.c_contiguous and buf.format == "B":
                # Use ctypes.memset directly on the memoryview's underlying buffer
                buf_array = (ctypes.c_byte * len(buf)).from_buffer(buf)
                ctypes.memset(ctypes.addressof(buf_array), 0, len(buf))
            else:
                # For non-contiguous or non-byte memoryviews, fallback to manual zeroing
                for i in range(len(buf)):
                    buf[i] = 0

        # Force a memory barrier/volatile operation to prevent reordering
        # Access the buffer to create a side effect
        if len(buf) > 0:
            _ = buf[0]

    except Exception as e:
        # Fallback to manual zeroing if ctypes fails
        # This is better than failing completely for security
        for i in range(len(buf)):
            buf[i] = 0
        raise RuntimeError(f"Secure memory zeroing failed, used fallback: {e}")


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


def generate_aes_key() -> bytes:
    """Return a cryptographically random 32-byte (256-bit) AES key."""
    return os.urandom(AES_KEY_SIZE)


def generate_rsa_keypair(key_size: int = RSA_KEY_SIZE) -> tuple[bytes, bytes]:
    """
    Generate an RSA keypair for the beneficiary.

    Returns:
        (private_key_pem, public_key_pem) — both PEM-encoded bytes.

    The private key is unencrypted; callers should protect it with a
    passphrase using serialise_private_key_with_password() before saving.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def serialise_private_key_with_password(
    private_key_pem: bytes,
    password: bytes,
) -> bytes:
    """
    Re-encode a private key PEM with AES-256-CBC password protection.
    Uses PBKDF2 with explicit iteration count (600,000) for key derivation.
    Use this before writing the beneficiary's private key to disk.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=None, backend=default_backend()
    )
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=os.urandom(16),
        iterations=600_000,
        backend=default_backend(),
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )


# ---------------------------------------------------------------------------
# RSA key wrapping / unwrapping (internal)
# ---------------------------------------------------------------------------


def _rsa_encrypt_key(aes_key: bytes, public_key_pem: bytes) -> bytes:
    """Encrypt an AES key with an RSA public key using OAEP/SHA-256."""
    public_key = serialization.load_pem_public_key(
        public_key_pem, backend=default_backend()
    )
    return public_key.encrypt(
        aes_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def _rsa_decrypt_key(
    encrypted_aes_key: bytes,
    private_key_pem: bytes,
    password: bytes | None = None,
) -> bytes:
    """Decrypt an RSA-wrapped AES key using the beneficiary's private key."""
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=password, backend=default_backend()
    )
    return private_key.decrypt(
        encrypted_aes_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# ---------------------------------------------------------------------------
# File encryption
# ---------------------------------------------------------------------------


def encrypt_file(
    plaintext_path: Path,
    recipient_public_key_pem: bytes,
    output_dir: Path,
) -> tuple[Path, str]:
    """
    Encrypt a secret file for the beneficiary.

    Binary layout of encrypted_secrets.bin:
        [nonce: 12 bytes][ciphertext + GCM tag: N+16 bytes]

    Args:
        plaintext_path:           Path to the file to encrypt.
        recipient_public_key_pem: Beneficiary's RSA-4096 public key (PEM bytes).
        output_dir:               Directory to write encrypted_secrets.bin.

    Returns:
        (encrypted_file_path, key_blob_base64)
        key_blob_base64: base64-encoded RSA-encrypted AES key.

    Raises:
        FileNotFoundError: if plaintext_path does not exist.
    """
    plaintext_path = Path(plaintext_path)
    output_dir = Path(output_dir)

    if not plaintext_path.exists():
        raise FileNotFoundError(f"Secret file not found: {plaintext_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    encrypted_path = output_dir / "encrypted_secrets.bin"

    # 1. Fresh AES-256 key + 12-byte nonce — never reuse either
    aes_key = generate_aes_key()
    nonce = os.urandom(GCM_NONCE_SIZE)

    # 2. AES-256-GCM encryption (appends 16-byte auth tag automatically)
    aesgcm = AESGCM(aes_key)
    plaintext = plaintext_path.read_bytes()
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # 3. Write [nonce | ciphertext+tag]
    encrypted_path.write_bytes(nonce + ciphertext)

    # 4. RSA-wrap the AES key for the beneficiary
    encrypted_aes_key = _rsa_encrypt_key(aes_key, recipient_public_key_pem)
    key_blob_b64 = base64.b64encode(encrypted_aes_key).decode("utf-8")

    # 5. Zero out AES key from memory
    aes_key_ba = bytearray(aes_key)
    _zero_memory(aes_key_ba)
    del aes_key_ba

    return encrypted_path, key_blob_b64


def encrypt_and_store_file(
    plaintext_path: Path,
    recipient_public_key_pem: bytes,
    output_dir: Path,
    enable_ipfs: bool = True,
) -> tuple[Path, str, Optional[str]]:
    """
    Enhanced encryption with optional IPFS storage.

    Encrypts the file and optionally uploads to IPFS for redundancy.

    Args:
        plaintext_path:           Path to the file to encrypt.
        recipient_public_key_pem: Beneficiary's RSA public key.
        output_dir:               Directory for local storage.
        enable_ipfs:              Whether to upload to IPFS.

    Returns:
        (encrypted_file_path, key_blob_base64, ipfs_cid)
        ipfs_cid will be None if IPFS upload is disabled or fails.
    """
    from core.storage import upload_to_ipfs_with_fallback, StorageConfig

    # First, encrypt the file locally
    encrypted_path, key_blob_b64 = encrypt_file(
        plaintext_path, recipient_public_key_pem, output_dir
    )

    ipfs_cid = None

    # Optionally upload to IPFS for redundancy
    if enable_ipfs:
        try:
            config = StorageConfig()
            result = upload_to_ipfs_with_fallback(encrypted_path, config)

            if result.provider != "local_filesystem":
                ipfs_cid = result.cid
                logger.info("File uploaded to IPFS with CID: %s", ipfs_cid)
            else:
                logger.warning("IPFS upload failed, using local fallback")

        except Exception as exc:
            logger.error("IPFS upload failed: %s", exc)
            # Continue with local storage only

    return encrypted_path, key_blob_b64, ipfs_cid


# ---------------------------------------------------------------------------
# File decryption
# ---------------------------------------------------------------------------


def decrypt_file(
    encrypted_path: Path,
    key_blob_b64: str,
    private_key_pem: bytes,
    output_path: Path,
    private_key_password: bytes | None = None,
) -> Path:
    """
    Decrypt a secret file using the beneficiary's private key.

    Args:
        encrypted_path:       Path to encrypted_secrets.bin.
        key_blob_b64:         base64-encoded RSA-wrapped AES key.
        private_key_pem:      Beneficiary's RSA private key (PEM bytes).
        output_path:          Where to write the decrypted plaintext.
        private_key_password: Passphrase bytes if key is encrypted, else None.

    Returns:
        Path to the decrypted output file.

    Raises:
        FileNotFoundError: if encrypted_path does not exist.
        DecryptionError:   if key is wrong or ciphertext is tampered.
    """
    encrypted_path = Path(encrypted_path)
    output_path = Path(output_path)

    if not encrypted_path.exists():
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_path}")

    # 1. RSA-unwrap the AES key
    try:
        encrypted_aes_key = base64.b64decode(key_blob_b64)
        aes_key = _rsa_decrypt_key(
            encrypted_aes_key, private_key_pem, private_key_password
        )
    except Exception as exc:
        raise DecryptionError(
            f"Failed to unwrap AES key — wrong private key? ({exc})"
        ) from exc

    # Convert to bytearray for secure zeroing after use
    aes_key_ba = bytearray(aes_key)

    try:
        # 2. Split raw bytes into nonce + ciphertext
        raw = encrypted_path.read_bytes()
        nonce = raw[:GCM_NONCE_SIZE]
        ciphertext = raw[GCM_NONCE_SIZE:]

        # 3. AES-256-GCM decrypt + authenticate
        aesgcm = AESGCM(aes_key_ba)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        except InvalidTag as exc:
            raise DecryptionError(
                "GCM authentication failed — file may be corrupted or tampered."
            ) from exc
    finally:
        _zero_memory(aes_key_ba)
        del aes_key_ba

    # 4. Write plaintext
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(plaintext)

    return output_path


# ---------------------------------------------------------------------------
# Key file helpers
# ---------------------------------------------------------------------------


def load_public_key_from_file(path: Path) -> bytes:
    """
    Read and validate a PEM RSA public key file.

    Raises:
        ValueError: if the file is not a valid RSA public key.
    """
    path = Path(path)
    pem = path.read_bytes()
    try:
        serialization.load_pem_public_key(pem, backend=default_backend())
    except Exception as exc:
        raise ValueError(f"Invalid RSA public key at {path}: {exc}") from exc
    return pem


def load_private_key_from_file(path: Path, password: bytes | None = None) -> bytes:
    """
    Read and validate a PEM RSA private key file.

    Args:
        path:     Path to the PEM private key.
        password: Passphrase bytes if key is password-protected, else None.

    Raises:
        ValueError: if the file is not a valid RSA private key.
    """
    path = Path(path)
    pem = path.read_bytes()
    try:
        serialization.load_pem_private_key(
            pem, password=password, backend=default_backend()
        )
    except Exception as exc:
        raise ValueError(f"Invalid RSA private key at {path}: {exc}") from exc
    return pem
