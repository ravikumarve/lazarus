"""
Security headers and event logging.
"""

from __future__ import annotations

import logging

security_logger = logging.getLogger("lazarus.security")


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
