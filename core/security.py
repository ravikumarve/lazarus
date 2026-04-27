"""
core/security.py — Security utilities for Lazarus Protocol.

Provides:
- API key authentication
- Rate limiting
- CSRF protection
- Input validation
- Path traversal protection
- Security headers
"""

from __future__ import annotations

import os
import re
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, UTC
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_KEY_ENV = "LAZARUS_API_KEY"
API_KEY_MIN_LENGTH = 32
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # seconds
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_PATHS = [
    Path.home() / ".lazarus",
    Path.cwd(),
]


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def get_api_key() -> str:
    """
    Get API key from environment variable.
    
    Returns:
        API key string.
    
    Raises:
        ValueError: If API key is not set or too short.
    """
    api_key = os.environ.get(API_KEY_ENV)
    
    if not api_key:
        raise ValueError(
            f"API key not set. Please set {API_KEY_ENV} environment variable."
        )
    
    if len(api_key) < API_KEY_MIN_LENGTH:
        raise ValueError(
            f"API key must be at least {API_KEY_MIN_LENGTH} characters. "
            f"Current length: {len(api_key)}"
        )
    
    return api_key


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials]) -> None:
    """
    Verify API key from Authorization header.
    
    Args:
        credentials: HTTP Authorization credentials.
    
    Raises:
        HTTPException: If authentication fails.
    """
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


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require API key authentication for an endpoint.
    
    Args:
        func: FastAPI endpoint function.
    
    Returns:
        Wrapped function with authentication check.
    """
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


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Tracks requests per IP address within a time window.
    """
    
    def __init__(self, requests: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW):
        """
        Initialize rate limiter.
        
        Args:
            requests: Maximum requests per window.
            window: Time window in seconds.
        """
        self.requests = requests
        self.window = window
        self._requests: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, ip: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed for given IP.
        
        Args:
            ip: IP address.
        
        Returns:
            (is_allowed, retry_after) tuple.
        """
        now = time.time()
        
        # Clean old requests outside the window
        self._requests[ip] = [
            timestamp for timestamp in self._requests[ip]
            if now - timestamp < self.window
        ]
        
        # Check if limit exceeded
        if len(self._requests[ip]) >= self.requests:
            # Calculate retry after
            oldest = min(self._requests[ip])
            retry_after = int(self.window - (now - oldest)) + 1
            return False, retry_after
        
        # Add current request
        self._requests[ip].append(now)
        return True, None
    
    def cleanup(self) -> None:
        """Clean up old entries to prevent memory leaks."""
        now = time.time()
        for ip in list(self._requests.keys()):
            self._requests[ip] = [
                timestamp for timestamp in self._requests[ip]
                if now - timestamp < self.window
            ]
            if not self._requests[ip]:
                del self._requests[ip]


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(request: Request) -> None:
    """
    Check rate limit for current request.
    
    Args:
        request: FastAPI Request object.
    
    Raises:
        HTTPException: If rate limit exceeded.
    """
    ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.is_allowed(ip)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


# ---------------------------------------------------------------------------
# CSRF Protection
# ---------------------------------------------------------------------------

def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token.
    
    Returns:
        Cryptographically secure random token.
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(request: Request, token: str) -> bool:
    """
    Verify CSRF token from request.
    
    Args:
        request: FastAPI Request object.
        token: CSRF token to verify.
    
    Returns:
        True if token is valid, False otherwise.
    """
    # In production, this should validate against session storage
    # For now, we'll implement a simple check
    expected_token = request.headers.get("X-CSRF-Token")
    return expected_token == token


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate.
    
    Returns:
        True if valid, False otherwise.
    """
    if not email or len(email) > 254:
        return False
    
    # RFC 5322 compliant email regex
    pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    return bool(re.match(pattern, email))


def validate_safe_path(path: Path, allowed_paths: Optional[list[Path]] = None) -> Path:
    """
    Validate that a path is safe and within allowed directories.
    
    Args:
        path: Path to validate.
        allowed_paths: List of allowed base paths. Defaults to ALLOWED_PATHS.
    
    Returns:
        Resolved absolute path.
    
    Raises:
        ValueError: If path is unsafe or outside allowed directories.
    """
    if allowed_paths is None:
        allowed_paths = ALLOWED_PATHS
    
    # Resolve to absolute path
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")
    
    # Check for path traversal attempts
    if ".." in str(path):
        raise ValueError("Path traversal detected")
    
    # Check if path is within allowed directories
    is_allowed = False
    for allowed in allowed_paths:
        try:
            allowed_resolved = allowed.resolve()
            if resolved == allowed_resolved or str(resolved).startswith(str(allowed_resolved)):
                is_allowed = True
                break
        except (OSError, RuntimeError):
            continue
    
    if not is_allowed:
        raise ValueError(f"Path not in allowed directories: {resolved}")
    
    return resolved


def validate_file_size(file_path: Path, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Validate file size is within limits.
    
    Args:
        file_path: Path to file.
        max_size: Maximum allowed size in bytes.
    
    Raises:
        ValueError: If file is too large.
    """
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    size = file_path.stat().st_size
    if size > max_size:
        raise ValueError(
            f"File too large: {size} bytes (max {max_size} bytes)"
        )


def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize user input string.
    
    Args:
        input_str: Input string to sanitize.
        max_length: Maximum allowed length.
    
    Returns:
        Sanitized string.
    
    Raises:
        ValueError: If input is too long.
    """
    if not input_str:
        return ""
    
    if len(input_str) > max_length:
        raise ValueError(f"Input too long: {len(input_str)} characters (max {max_length})")
    
    # Remove null bytes
    sanitized = input_str.replace("\x00", "")
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def validate_filename(filename: str) -> bool:
    """
    Validate filename is safe.
    
    Args:
        filename: Filename to validate.
    
    Returns:
        True if safe, False otherwise.
    """
    if not filename or len(filename) > 255:
        return False
    
    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    
    # Check for null bytes
    if "\x00" in filename:
        return False
    
    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        return False
    
    # Allow only safe characters
    safe_pattern = r"^[a-zA-Z0-9._-]+$"
    return bool(re.match(safe_pattern, filename))


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

def get_security_headers() -> dict[str, str]:
    """
    Get security headers for HTTP responses.
    
    Returns:
        Dictionary of security headers.
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }


# ---------------------------------------------------------------------------
# Security Logging
# ---------------------------------------------------------------------------

import logging

security_logger = logging.getLogger("lazarus.security")


def log_security_event(
    event_type: str,
    ip: str,
    details: str,
    level: int = logging.WARNING
) -> None:
    """
    Log security event.
    
    Args:
        event_type: Type of security event (e.g., "AUTH_FAILURE", "RATE_LIMIT").
        ip: IP address of client.
        details: Event details.
        level: Log level.
    """
    security_logger.log(
        level,
        f"[{event_type}] IP={ip} Details={details}"
    )


# ---------------------------------------------------------------------------
# Async import for decorator
# ---------------------------------------------------------------------------

import asyncio
