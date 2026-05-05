"""
core/rate_limiter.py — Redis-based distributed rate limiting with exponential backoff.

Provides:
- Redis-based distributed rate limiting
- User-based rate limiting for authenticated users
- Exponential backoff for repeated violations
- IP reputation checking
- Rate limit persistence across restarts
- Thread-safe operations
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis library not available, rate limiting will use in-memory fallback")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests: int = 10
    window: int = 60  # seconds
    burst: int = 20
    backoff_base: int = 2
    backoff_max: int = 60
    ip_reputation_threshold: int = 50
    ip_reputation_expiry: int = 86400  # 24 hours


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    retry_after: Optional[int] = None
    remaining: Optional[int] = None
    reset_at: Optional[datetime] = None
    limit: Optional[int] = None
    reason: Optional[str] = None


class DistributedRateLimiter:
    """
    Redis-based distributed rate limiting with exponential backoff.
    
    This class provides:
    - Distributed rate limiting using Redis
    - User-based rate limiting for authenticated users
    - Exponential backoff for repeated violations
    - IP reputation checking
    - Thread-safe operations
    """

    def __init__(
        self,
        redis_client: Optional['redis.Redis'] = None,
        config: Optional[RateLimitConfig] = None
    ):
        """
        Initialize distributed rate limiter.
        
        Args:
            redis_client: Redis client instance (optional, will create if not provided)
            config: Rate limit configuration (optional, uses defaults if not provided)
        """
        self.config = config or RateLimitConfig()
        
        if REDIS_AVAILABLE and redis_client:
            self.redis = redis_client
            self.use_redis = True
        else:
            self.redis = None
            self.use_redis = False
            # Fallback to in-memory storage
            self._in_memory_storage: Dict[str, Dict[str, Any]] = {}
            logging.warning("Using in-memory rate limiting (not distributed)")
        
        self._logger = logging.getLogger("lazarus.rate_limiter")

    def is_allowed(
        self,
        identifier: str,
        user_id: Optional[str] = None,
        check_ip_reputation: bool = True
    ) -> RateLimitResult:
        """
        Check if request is allowed with rate limiting.
        
        Args:
            identifier: IP address or unique identifier
            user_id: Optional user ID for user-based limiting
            check_ip_reputation: Whether to check IP reputation

        Returns:
            RateLimitResult with allowed status and metadata
        """
        # Check IP reputation first
        if check_ip_reputation and not self._check_ip_reputation(identifier):
            return RateLimitResult(
                allowed=False,
                retry_after=self.config.backoff_max,
                reason="IP reputation check failed"
            )
        
        # Use user-based limiting if user_id provided
        key = f"rate_limit:user:{user_id}" if user_id else f"rate_limit:ip:{identifier}"
        
        if self.use_redis:
            return self._is_allowed_redis(key, identifier)
        else:
            return self._is_allowed_in_memory(key, identifier)

    def _is_allowed_redis(self, key: str, identifier: str) -> RateLimitResult:
        """Check rate limit using Redis"""
        try:
            pipe = self.redis.pipeline()
            pipe.get(f"{key}:count")
            pipe.get(f"{key}:backoff")
            pipe.get(f"{key}:window_start")
            pipe.ttl(f"{key}:count")
            results = pipe.execute()
            
            count, backoff, window_start, ttl = results
            
            # Check if in backoff period
            if backoff:
                backoff_end = float(backoff)
                if time.time() < backoff_end:
                    retry_after = int(backoff_end - time.time())
                    return RateLimitResult(
                        allowed=False,
                        retry_after=retry_after,
                        reason=f"Rate limit exceeded, backoff active"
                    )
            
            # Initialize window if needed
            if not window_start:
                window_start = time.time()
                pipe.set(f"{key}:window_start", window_start, ex=self.config.window)
                pipe.set(f"{key}:count", 0, ex=self.config.window)
                count = 0
            else:
                window_start = float(window_start)
                # Reset if window expired
                if time.time() - window_start > self.config.window:
                    pipe.delete(f"{key}:count")
                    pipe.delete(f"{key}:backoff")
                    pipe.set(f"{key}:window_start", time.time(), ex=self.config.window)
                    pipe.set(f"{key}:count", 0, ex=self.config.window)
                    count = 0
                else:
                    count = int(count) if count else 0
            
            # Check if limit exceeded
            if count >= self.config.requests:
                # Calculate exponential backoff
                backoff_time = min(
                    self.config.backoff_base ** (count - self.config.requests + 1),
                    self.config.backoff_max
                )
                backoff_end = time.time() + backoff_time
                pipe.set(f"{key}:backoff", backoff_end, ex=backoff_time)
                pipe.execute()
                
                return RateLimitResult(
                    allowed=False,
                    retry_after=backoff_time,
                    reason=f"Rate limit exceeded ({count}/{self.config.requests})"
                )
            
            # Increment counter
            pipe.incr(f"{key}:count")
            pipe.expire(f"{key}:count", self.config.window)
            pipe.execute()
            
            # Calculate remaining
            remaining = self.config.requests - (count + 1)
            reset_at = datetime.fromtimestamp(window_start + self.config.window)
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_at=reset_at,
                limit=self.config.requests
            )
            
        except Exception as e:
            self._logger.error(f"Redis rate limiting error: {e}")
            # Fallback to allow request if Redis fails
            return RateLimitResult(allowed=True, reason="Rate limiting error, allowing request")

    def _is_allowed_in_memory(self, key: str, identifier: str) -> RateLimitResult:
        """Check rate limit using in-memory storage (fallback)"""
        now = time.time()
        
        # Get or create entry
        if key not in self._in_memory_storage:
            self._in_memory_storage[key] = {
                "count": 0,
                "window_start": now,
                "backoff_until": None
            }
        
        entry = self._in_memory_storage[key]
        
        # Check if in backoff period
        if entry["backoff_until"] and now < entry["backoff_until"]:
            retry_after = int(entry["backoff_until"] - now)
            return RateLimitResult(
                allowed=False,
                retry_after=retry_after,
                reason="Rate limit exceeded, backoff active"
            )
        
        # Reset if window expired
        if now - entry["window_start"] > self.config.window:
            entry["count"] = 0
            entry["window_start"] = now
            entry["backoff_until"] = None
        
        # Check if limit exceeded
        if entry["count"] >= self.config.requests:
            # Calculate exponential backoff
            backoff_time = min(
                self.config.backoff_base ** (entry["count"] - self.config.requests + 1),
                self.config.backoff_max
            )
            entry["backoff_until"] = now + backoff_time
            
            return RateLimitResult(
                allowed=False,
                retry_after=backoff_time,
                reason=f"Rate limit exceeded ({entry['count']}/{self.config.requests})"
            )
        
        # Increment counter
        entry["count"] += 1
        
        # Calculate remaining
        remaining = self.config.requests - entry["count"]
        reset_at = datetime.fromtimestamp(entry["window_start"] + self.config.window)
        
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at,
            limit=self.config.requests
        )

    def _check_ip_reputation(self, ip: str) -> bool:
        """Check IP reputation and block if suspicious"""
        if not self.use_redis:
            return True  # Skip reputation check without Redis
        
        try:
            reputation_key = f"ip_reputation:{ip}"
            reputation = self.redis.get(reputation_key)
            
            if reputation:
                score = int(reputation)
                return score < self.config.ip_reputation_threshold
            
            return True
        except Exception as e:
            self._logger.error(f"IP reputation check error: {e}")
            return True  # Allow if reputation check fails

    def report_bad_ip(self, ip: str, severity: int = 10) -> bool:
        """
        Report bad IP and update reputation.
        
        Args:
            ip: IP address to report
            severity: Severity score to add (default: 10)

        Returns:
            True if successful, False otherwise
        """
        if not self.use_redis:
            return False
        
        try:
            reputation_key = f"ip_reputation:{ip}"
            current = self.redis.get(reputation_key)
            new_score = (int(current) if current else 0) + severity
            self.redis.set(reputation_key, new_score, ex=self.config.ip_reputation_expiry)
            
            self._logger.info(f"Reported bad IP {ip} with severity {severity}, new score: {new_score}")
            return True
        except Exception as e:
            self._logger.error(f"Error reporting bad IP: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with statistics
        """
        if self.use_redis:
            try:
                # Count active rate limit entries
                count = 0
                for key in self.redis.scan_iter("rate_limit:*"):
                    if not key.endswith(b":count"):
                        count += 1
                
                return {
                    "type": "redis",
                    "active_entries": count,
                    "config": {
                        "requests": self.config.requests,
                        "window": self.config.window,
                        "backoff_base": self.config.backoff_base,
                        "backoff_max": self.config.backoff_max
                    }
                }
            except Exception as e:
                self._logger.error(f"Error getting Redis stats: {e}")
                return {"type": "redis", "error": str(e)}
        else:
            return {
                "type": "in_memory",
                "active_entries": len(self._in_memory_storage),
                "config": {
                    "requests": self.config.requests,
                    "window": self.config.window,
                    "backoff_base": self.config.backoff_base,
                    "backoff_max": self.config.backoff_max
                }
            }

    def cleanup(self) -> None:
        """Clean up old entries"""
        if self.use_redis:
            try:
                # Redis automatically expires keys, but we can force cleanup
                pipe = self.redis.pipeline()
                for key in self.redis.scan_iter("rate_limit:*"):
                    pipe.ttl(key)
                ttls = pipe.execute()
                
                # Log cleanup statistics
                expired_count = sum(1 for ttl in ttls if ttl == -2)
                if expired_count > 0:
                    self._logger.info(f"Found {expired_count} expired rate limit entries")
            except Exception as e:
                self._logger.error(f"Error during cleanup: {e}")
        else:
            # Clean up in-memory storage
            now = time.time()
            to_delete = []
            
            for key, entry in self._in_memory_storage.items():
                # Remove entries that are outside window and not in backoff
                if now - entry["window_start"] > self.config.window and not entry["backoff_until"]:
                    to_delete.append(key)
            
            for key in to_delete:
                del self._in_memory_storage[key]
            
            if to_delete:
                self._logger.info(f"Cleaned up {len(to_delete)} expired in-memory entries")

    def reset(self, identifier: str, user_id: Optional[str] = None) -> bool:
        """
        Reset rate limit for a specific identifier.
        
        Args:
            identifier: IP address or unique identifier
            user_id: Optional user ID for user-based limiting

        Returns:
            True if successful, False otherwise
        """
        key = f"rate_limit:user:{user_id}" if user_id else f"rate_limit:ip:{identifier}"
        
        if self.use_redis:
            try:
                pipe = self.redis.pipeline()
                pipe.delete(f"{key}:count")
                pipe.delete(f"{key}:backoff")
                pipe.delete(f"{key}:window_start")
                pipe.execute()
                return True
            except Exception as e:
                self._logger.error(f"Error resetting rate limit: {e}")
                return False
        else:
            if key in self._in_memory_storage:
                del self._in_memory_storage[key]
            return True


# Global distributed rate limiter instance
distributed_rate_limiter = None


def get_distributed_rate_limiter(
    redis_client: Optional['redis.Redis'] = None,
    config: Optional[RateLimitConfig] = None
) -> DistributedRateLimiter:
    """
    Get or create global distributed rate limiter instance.
    
    Args:
        redis_client: Redis client instance (optional)
        config: Rate limit configuration (optional)

    Returns:
        DistributedRateLimiter instance
    """
    global distributed_rate_limiter
    
    if distributed_rate_limiter is None:
        distributed_rate_limiter = DistributedRateLimiter(redis_client, config)
    
    return distributed_rate_limiter
