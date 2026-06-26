"""
CSRF token generation and validation.
"""

from __future__ import annotations

import secrets

from fastapi import Request


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
    expected_token = request.headers.get("X-CSRF-Token")
    return expected_token == token
