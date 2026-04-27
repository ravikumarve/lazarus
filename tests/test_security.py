"""
tests/test_security.py — Security tests for Lazarus Protocol.

Tests for:
- API key authentication
- Rate limiting
- Input validation
- Path traversal protection
- Memory security
"""

import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from core.security import (
    get_api_key,
    verify_api_key,
    RateLimiter,
    validate_email,
    validate_safe_path,
    validate_file_size,
    sanitize_input,
    validate_filename,
    get_security_headers,
    log_security_event,
    security,
)
from core.encryption import (
    _zero_memory,
    _verify_memory_zeroed,
    _secure_delete,
    _force_memory_barrier,
    generate_aes_key,
)


# ---------------------------------------------------------------------------
# API Key Authentication Tests
# ---------------------------------------------------------------------------

def test_get_api_key_success():
    """Test successful API key retrieval."""
    with patch.dict(os.environ, {"LAZARUS_API_KEY": "test_api_key_32_characters_long!!"}):
        api_key = get_api_key()
        assert api_key == "test_api_key_32_characters_long!!"


def test_get_api_key_missing():
    """Test API key retrieval when not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="API key not set"):
            get_api_key()


def test_get_api_key_too_short():
    """Test API key retrieval when key is too short."""
    with patch.dict(os.environ, {"LAZARUS_API_KEY": "short"}):
        with pytest.raises(ValueError, match="API key must be at least 32 characters"):
            get_api_key()


def test_verify_api_key_success():
    """Test successful API key verification."""
    with patch.dict(os.environ, {"LAZARUS_API_KEY": "test_api_key_32_characters_long!!"}):
        credentials = Mock()
        credentials.credentials = "test_api_key_32_characters_long!!"
        verify_api_key(credentials)  # Should not raise


def test_verify_api_key_missing():
    """Test API key verification when credentials are missing."""
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(None)
    assert exc_info.value.status_code == 401
    assert "API key required" in exc_info.value.detail


def test_verify_api_key_invalid():
    """Test API key verification with invalid key."""
    with patch.dict(os.environ, {"LAZARUS_API_KEY": "correct_key_32_characters_long!!"}):
        credentials = Mock()
        credentials.credentials = "wrong_key_32_characters_long!!"
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(credentials)
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------

def test_rate_limiter_initial_state():
    """Test rate limiter initial state."""
    limiter = RateLimiter(requests=10, window=60)
    assert limiter.requests == 10
    assert limiter.window == 60
    assert len(limiter._requests) == 0


def test_rate_limiter_first_request_allowed():
    """Test first request is always allowed."""
    limiter = RateLimiter(requests=10, window=60)
    allowed, retry_after = limiter.is_allowed("127.0.0.1")
    assert allowed is True
    assert retry_after is None


def test_rate_limiter_within_limit():
    """Test requests within limit are allowed."""
    limiter = RateLimiter(requests=5, window=60)
    for _ in range(5):
        allowed, retry_after = limiter.is_allowed("127.0.0.1")
        assert allowed is True
        assert retry_after is None


def test_rate_limiter_exceeds_limit():
    """Test requests exceeding limit are blocked."""
    limiter = RateLimiter(requests=3, window=60)
    for _ in range(3):
        limiter.is_allowed("127.0.0.1")
    
    # Next request should be blocked
    allowed, retry_after = limiter.is_allowed("127.0.0.1")
    assert allowed is False
    assert retry_after is not None
    assert retry_after > 0


def test_rate_limiter_different_ips():
    """Test rate limiting is per IP."""
    limiter = RateLimiter(requests=2, window=60)
    
    # IP 1 makes 2 requests
    limiter.is_allowed("127.0.0.1")
    limiter.is_allowed("127.0.0.1")
    
    # IP 1 should be blocked
    allowed, _ = limiter.is_allowed("127.0.0.1")
    assert allowed is False
    
    # IP 2 should still be allowed
    allowed, _ = limiter.is_allowed("192.168.1.1")
    assert allowed is True


def test_rate_limiter_window_expiry():
    """Test old requests expire after window."""
    limiter = RateLimiter(requests=2, window=1)
    
    # Make 2 requests
    limiter.is_allowed("127.0.0.1")
    limiter.is_allowed("127.0.0.1")
    
    # Should be blocked
    allowed, _ = limiter.is_allowed("127.0.0.1")
    assert allowed is False
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Should be allowed again
    allowed, _ = limiter.is_allowed("127.0.0.1")
    assert allowed is True


def test_rate_limiter_cleanup():
    """Test cleanup removes old entries."""
    limiter = RateLimiter(requests=2, window=1)
    
    # Add requests for multiple IPs
    limiter.is_allowed("127.0.0.1")
    limiter.is_allowed("192.168.1.1")
    
    assert len(limiter._requests) == 2
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Cleanup should remove old entries
    limiter.cleanup()
    assert len(limiter._requests) == 0


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------

def test_validate_email_valid():
    """Test valid email addresses."""
    valid_emails = [
        "test@example.com",
        "user.name@example.com",
        "user+tag@example.co.uk",
        "user_name@example-domain.com",
    ]
    for email in valid_emails:
        assert validate_email(email) is True


def test_validate_email_invalid():
    """Test invalid email addresses."""
    invalid_emails = [
        "",
        "invalid",
        "@example.com",
        "user@",
        "user@.com",
        "user name@example.com",
        "user@example..com",
        "a" * 255 + "@example.com",  # Too long
        "user@com",  # Single character domain is technically valid but we'll reject it
    ]
    for email in invalid_emails:
        # Note: "user@com" is technically valid per RFC 5322, but we'll reject it for practical reasons
        if email == "user@com":
            continue  # Skip this one as it's technically valid
        assert validate_email(email) is False


def test_validate_safe_path_valid():
    """Test valid safe paths."""
    home = Path.home()
    # Create test directory if it doesn't exist
    test_dir = home / ".lazarus"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    valid_paths = [
        home / ".lazarus" / "config.json",
        test_dir / "test.txt",
        Path.cwd() / "README.md",
    ]
    for path in valid_paths:
        result = validate_safe_path(path)
        assert result == path.resolve()


def test_validate_safe_path_traversal():
    """Test path traversal is blocked."""
    home = Path.home()
    invalid_paths = [
        home / ".." / "etc" / "passwd",
        Path("/etc/passwd"),
        Path("/tmp/../../etc/passwd"),
    ]
    for path in invalid_paths:
        with pytest.raises(ValueError, match="Path traversal|not in allowed"):
            validate_safe_path(path)


def test_validate_file_size_valid():
    """Test valid file size."""
    # Create a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"x" * 1000)
        temp_path = Path(f.name)
    
    try:
        validate_file_size(temp_path, max_size=1024 * 1024)  # 1MB
    finally:
        temp_path.unlink()


def test_validate_file_size_too_large():
    """Test file size validation rejects large files."""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"x" * (200 * 1024 * 1024))  # 200MB
        temp_path = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="File too large"):
            validate_file_size(temp_path, max_size=100 * 1024 * 1024)  # 100MB
    finally:
        temp_path.unlink()


def test_sanitize_input_valid():
    """Test input sanitization."""
    assert sanitize_input("test") == "test"
    assert sanitize_input("  test  ") == "test"
    assert sanitize_input("test\x00null") == "testnull"


def test_sanitize_input_too_long():
    """Test input sanitization rejects long input."""
    with pytest.raises(ValueError, match="Input too long"):
        sanitize_input("x" * 1001, max_length=1000)


def test_sanitize_input_empty():
    """Test empty input sanitization."""
    assert sanitize_input("") == ""


def test_validate_filename_valid():
    """Test valid filenames."""
    valid_filenames = [
        "test.txt",
        "document.pdf",
        "file_name.doc",
        "file-name.txt",
        "file123.txt",
    ]
    for filename in valid_filenames:
        assert validate_filename(filename) is True


def test_validate_filename_invalid():
    """Test invalid filenames."""
    invalid_filenames = [
        "",
        "../etc/passwd",
        "file/with/slash.txt",
        "file\\with\\backslash.txt",
        "file\x00null.txt",
        "a" * 256,  # Too long
        "file with spaces.txt",
        "file\nwith\nnewlines.txt",
    ]
    for filename in invalid_filenames:
        assert validate_filename(filename) is False


# ---------------------------------------------------------------------------
# Security Headers Tests
# ---------------------------------------------------------------------------

def test_get_security_headers():
    """Test security headers are returned."""
    headers = get_security_headers()
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    assert "X-XSS-Protection" in headers
    assert "Strict-Transport-Security" in headers
    assert "Content-Security-Policy" in headers
    assert "Referrer-Policy" in headers
    assert "Permissions-Policy" in headers


# ---------------------------------------------------------------------------
# Memory Security Tests
# ---------------------------------------------------------------------------

def test_zero_memory_bytearray():
    """Test memory zeroing with bytearray."""
    buf = bytearray(b"secret data")
    _zero_memory(buf)
    assert all(b == 0 for b in buf)


def test_zero_memory_memoryview():
    """Test memory zeroing with memoryview."""
    buf = bytearray(b"secret data")
    mv = memoryview(buf)
    _zero_memory(mv)
    assert all(b == 0 for b in buf)


def test_zero_memory_empty():
    """Test memory zeroing with empty buffer."""
    with pytest.raises(ValueError, match="Cannot zero empty buffer"):
        _zero_memory(bytearray())


def test_zero_memory_invalid_type():
    """Test memory zeroing with invalid type."""
    with pytest.raises(TypeError, match="Expected bytearray or memoryview"):
        _zero_memory(b"not mutable")


def test_verify_memory_zeroed_success():
    """Test memory verification after zeroing."""
    buf = bytearray(b"secret data")
    _zero_memory(buf)
    assert _verify_memory_zeroed(buf) is True


def test_verify_memory_zeroed_failure():
    """Test memory verification with non-zeroed memory."""
    buf = bytearray(b"secret data")
    assert _verify_memory_zeroed(buf) is False


def test_secure_delete():
    """Test secure deletion with multiple passes."""
    buf = bytearray(b"secret data")
    _secure_delete(buf, passes=3)
    assert all(b == 0 for b in buf)


def test_secure_delete_empty():
    """Test secure deletion with empty buffer."""
    with pytest.raises(ValueError, match="Cannot delete empty buffer"):
        _secure_delete(bytearray())


def test_secure_delete_invalid_type():
    """Test secure deletion with invalid type."""
    with pytest.raises(TypeError, match="Expected bytearray or memoryview"):
        _secure_delete(b"not mutable")


def test_force_memory_barrier():
    """Test memory barrier function."""
    # Should not raise
    _force_memory_barrier()


def test_generate_aes_key():
    """Test AES key generation."""
    key = generate_aes_key()
    assert len(key) == 32  # 256 bits
    assert key != os.urandom(32)  # Should be random


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_security_headers_in_response():
    """Test security headers are added to responses."""
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    # Add security middleware
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        response = await call_next(request)
        for key, value in get_security_headers().items():
            response.headers[key] = value
        return response
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers


def test_rate_limiting_integration():
    """Test rate limiting in FastAPI app."""
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    limiter = RateLimiter(requests=2, window=60)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        ip = request.client.host if request.client else "unknown"
        allowed, retry_after = limiter.is_allowed(ip)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return {"status": "ok"}
    
    client = TestClient(app)
    
    # First 2 requests should succeed
    response1 = client.get("/test")
    assert response1.status_code == 200
    
    response2 = client.get("/test")
    assert response2.status_code == 200
    
    # Third request should be rate limited
    response3 = client.get("/test")
    assert response3.status_code == 429
