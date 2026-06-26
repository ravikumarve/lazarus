"""
In-memory rate limiter using sliding window algorithm.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status

from core.security.constants import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW


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
        self._requests[ip] = [
            timestamp for timestamp in self._requests[ip]
            if now - timestamp < self.window
        ]
        if len(self._requests[ip]) >= self.requests:
            oldest = min(self._requests[ip])
            retry_after = int(self.window - (now - oldest)) + 1
            return False, retry_after
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
