"""
core.security — Security utilities for Lazarus Protocol.

Provides:
- API key authentication
- Rate limiting
- CSRF protection
- Input validation
- Path traversal protection
- Security headers
- Server-side key management
- PBKDF2 key derivation
"""

from core.security.constants import (
    ALLOWED_PATHS,
    API_KEY_ENV,
    API_KEY_MIN_LENGTH,
    DEVICE_BINDING_WINDOW,
    ENCRYPTION_SALT_ENV,
    KEY_ROTATION_INTERVAL,
    MAX_FILE_SIZE,
    PBKDF2_ITERATIONS,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    SESSION_KEY_EXPIRY,
)

from core.security.csrf import (
    generate_csrf_token,
    verify_csrf_token,
)

from core.security.headers import (
    get_security_headers,
    log_security_event,
    security_logger,
)

from core.security.key_manager import (
    KeyManager,
    SessionKey,
    get_api_key,
    key_manager,
    require_auth,
    security,
    verify_api_key,
)

from core.security.rate_limiter import (
    RateLimiter,
    check_rate_limit,
    rate_limiter,
)

from core.security.validation import (
    sanitize_input,
    validate_email,
    validate_file_size,
    validate_filename,
    validate_safe_path,
)

__all__ = [
    # Constants
    "API_KEY_ENV",
    "API_KEY_MIN_LENGTH",
    "ALLOWED_PATHS",
    "DEVICE_BINDING_WINDOW",
    "ENCRYPTION_SALT_ENV",
    "KEY_ROTATION_INTERVAL",
    "MAX_FILE_SIZE",
    "PBKDF2_ITERATIONS",
    "RATE_LIMIT_REQUESTS",
    "RATE_LIMIT_WINDOW",
    "SESSION_KEY_EXPIRY",
    # Auth
    "KeyManager",
    "SessionKey",
    "get_api_key",
    "key_manager",
    "require_auth",
    "security",
    "verify_api_key",
    # CSRF
    "generate_csrf_token",
    "verify_csrf_token",
    # Headers
    "get_security_headers",
    "log_security_event",
    "security_logger",
    # Rate Limiter
    "RateLimiter",
    "check_rate_limit",
    "rate_limiter",
    # Validation
    "sanitize_input",
    "validate_email",
    "validate_file_size",
    "validate_filename",
    "validate_safe_path",
]
