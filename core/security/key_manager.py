"""
Server-side key management with PBKDF2 derivation, session keys, and API key auth.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.security.constants import (
    API_KEY_ENV,
    API_KEY_MIN_LENGTH,
    DEVICE_BINDING_WINDOW,
    ENCRYPTION_SALT_ENV,
    KEY_ROTATION_INTERVAL,
    PBKDF2_ITERATIONS,
    SESSION_KEY_EXPIRY,
)

# Try to import cryptography for PBKDF2
try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logging.warning("cryptography library not available, using fallback key derivation")


@dataclass
class SessionKey:
    """Session key with metadata"""
    key_id: str
    key: str
    session_id: str
    user_agent: str
    ip_address: str
    created_at: datetime
    expires_at: datetime
    device_fingerprint: str


class KeyManager:
    """
    Secure key management with server-side generation and PBKDF2 derivation.

    This class provides:
    - Server-provided encryption keys
    - PBKDF2 key derivation with 100,000+ iterations
    - Key rotation mechanism
    - Session and device binding
    """

    def __init__(self):
        self.salt = self._get_or_generate_salt()
        self.iterations = PBKDF2_ITERATIONS
        self._session_keys: Dict[str, SessionKey] = {}
        self._used_csrf_tokens: set = set()
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._stop_event = threading.Event()
        self._logger = logging.getLogger("lazarus.security.key_manager")
        self._start_cleanup_thread()

    def _get_or_generate_salt(self) -> bytes:
        """Get encryption salt from environment or generate one"""
        salt_env = os.environ.get(ENCRYPTION_SALT_ENV)
        if salt_env:
            try:
                return bytes.fromhex(salt_env)
            except ValueError:
                logging.warning("Invalid encryption salt in environment, generating new one")
        salt = secrets.token_bytes(32)
        logging.info(f"Generated new encryption salt. Set {ENCRYPTION_SALT_ENV} environment variable to persist.")
        return salt

    def derive_key(self, password: str, context: Union[str, bytes]) -> bytes:
        """
        Derive encryption key using PBKDF2.

        Args:
            password: Password or seed for key derivation
            context: Context string or bytes for key derivation

        Returns:
            Derived key as bytes
        """
        context_bytes = context.encode('utf-8') if isinstance(context, str) else context
        if CRYPTOGRAPHY_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt + context_bytes,
                iterations=self.iterations,
                backend=default_backend()
            )
            return kdf.derive(password.encode())
        else:
            return hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                self.salt + context_bytes,
                self.iterations
            )

    def generate_session_key(
        self,
        session_id: str,
        user_agent: str,
        ip_address: str,
        device_fingerprint: Optional[str] = None
    ) -> SessionKey:
        """
        Generate session-specific encryption key.

        Args:
            session_id: Unique session identifier
            user_agent: User agent string for device binding
            ip_address: IP address for session tracking
            device_fingerprint: Optional device fingerprint for enhanced binding

        Returns:
            SessionKey object with derived key and metadata
        """
        key_id = secrets.token_urlsafe(16)
        key_bytes = self.derive_key(session_id, "session")
        key_hex = key_bytes.hex()
        if not device_fingerprint:
            device_fingerprint = self._generate_device_fingerprint(user_agent, ip_address)
        now = datetime.now(UTC)
        session_key = SessionKey(
            key_id=key_id,
            key=key_hex,
            session_id=session_id,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now,
            expires_at=now + timedelta(seconds=SESSION_KEY_EXPIRY),
            device_fingerprint=device_fingerprint
        )
        with self._lock:
            self._session_keys[key_id] = session_key
        return session_key

    def rotate_key(self, old_key_id: str, context: str = "rotation") -> Optional[SessionKey]:
        """Rotate encryption key for enhanced security."""
        with self._lock:
            old_session_key = self._session_keys.get(old_key_id)
            if not old_session_key:
                return None
            new_key_id = secrets.token_urlsafe(16)
            key_bytes = self.derive_key(old_session_key.session_id + "_rotated", context)
            key_hex = key_bytes.hex()
            now = datetime.now(UTC)
            new_session_key = SessionKey(
                key_id=new_key_id, key=key_hex,
                session_id=old_session_key.session_id,
                user_agent=old_session_key.user_agent,
                ip_address=old_session_key.ip_address,
                created_at=now,
                expires_at=now + timedelta(seconds=SESSION_KEY_EXPIRY),
                device_fingerprint=old_session_key.device_fingerprint
            )
            del self._session_keys[old_key_id]
            self._session_keys[new_key_id] = new_session_key
            return new_session_key

    def validate_session_key(self, key_id: str, user_agent: str, ip_address: str) -> Optional[SessionKey]:
        """Validate session key and check device binding."""
        with self._lock:
            session_key = self._session_keys.get(key_id)
            if not session_key:
                return None
            if datetime.now(UTC) > session_key.expires_at:
                del self._session_keys[key_id]
                return None
            if session_key.user_agent != user_agent:
                logging.warning(f"Device binding mismatch for key {key_id}: user agent changed")
                return None
            if session_key.ip_address != ip_address:
                logging.info(f"IP address changed for key {key_id}: {session_key.ip_address} -> {ip_address}")
            return session_key

    def _generate_device_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate device fingerprint for session binding."""
        fingerprint_data = f"{user_agent}:{ip_address}".encode()
        return hashlib.sha256(fingerprint_data).hexdigest()

    def _start_cleanup_thread(self):
        """Start background cleanup thread for expired keys"""
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        """Background cleanup loop"""
        while not self._stop_event.is_set():
            try:
                self._cleanup_expired_keys()
                self._stop_event.wait(300)
            except Exception as e:
                logging.error(f"Key cleanup error: {e}")

    def _cleanup_expired_keys(self):
        """Clean up expired session keys"""
        with self._lock:
            now = datetime.now(UTC)
            expired_keys = [
                key_id for key_id, session_key in self._session_keys.items()
                if now > session_key.expires_at
            ]
            for key_id in expired_keys:
                del self._session_keys[key_id]
            if expired_keys:
                logging.info(f"Cleaned up {len(expired_keys)} expired session keys")

    def generate_csrf_token(self, session_id: Optional[str] = None) -> str:
        """Generate a CSRF token for session protection."""
        token = secrets.token_hex(32)
        self._logger.debug(f"Generated CSRF token for session: {session_id}")
        return token

    def verify_csrf_token(self, token: str, session_id: Optional[str] = None, request: Optional[Any] = None) -> bool:
        """Verify a CSRF token (alias for validate_csrf_token)."""
        return self.validate_csrf_token(token, session_id)

    def validate_csrf_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """Validate a CSRF token with reuse prevention."""
        if token in self._used_csrf_tokens:
            self._logger.warning(f"CSRF token reuse detected for session: {session_id}")
            return False
        try:
            int(token, 16)
            is_valid = len(token) == 64
        except ValueError:
            self._logger.warning(f"Invalid CSRF token format for session: {session_id}")
            return False
        if is_valid:
            self._used_csrf_tokens.add(token)
            self._logger.debug(f"Validated CSRF token for session: {session_id}")
            if len(self._used_csrf_tokens) > 10000:
                self._used_csrf_tokens.clear()
        else:
            self._logger.warning(f"Invalid CSRF token length for session: {session_id}")
        return is_valid

    def stop(self):
        """Stop cleanup thread"""
        self._stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def __del__(self):
        """Cleanup on deletion"""
        self.stop()


# Global key manager instance
key_manager = KeyManager()

# HTTP bearer security scheme
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    """Get API key from environment variable."""
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise ValueError(f"API key not set. Please set {API_KEY_ENV} environment variable.")
    if len(api_key) < API_KEY_MIN_LENGTH:
        raise ValueError(
            f"API key must be at least {API_KEY_MIN_LENGTH} characters. "
            f"Current length: {len(api_key)}"
        )
    return api_key


def verify_api_key(credentials: Optional[Union[str, HTTPAuthorizationCredentials]]) -> bool:
    """Verify API key from Authorization header or plain string."""
    if isinstance(credentials, str):
        try:
            expected_key = get_api_key()
            if not credentials:
                return False
            return credentials == expected_key
        except ValueError:
            return False

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide Authorization: Bearer YOUR_API_KEY",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        expected_key = get_api_key()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    if credentials.credentials != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


def require_auth(func: Callable) -> Callable:
    """Decorator to require API key authentication for an endpoint."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if request:
            credentials = await security(request)
            verify_api_key(credentials)
        return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
    return wrapper
