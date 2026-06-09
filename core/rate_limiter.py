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
import threading
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
    requests: int = 60
    window: int = 60  # seconds
    burst: int = 100
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
    
    def __iter__(self):
        """Make RateLimitResult iterable for unpacking"""
        return iter((self.allowed, self.remaining))


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
        config: Optional[RateLimitConfig] = None,
        default_limit: Optional[int] = None,
        default_window: Optional[int] = None
    ):
        """
        Initialize distributed rate limiter.
        
        Args:
            redis_client: Redis client instance (optional, will create if not provided)
            config: Rate limit configuration (optional, uses defaults if not provided)
            default_limit: Optional default limit to override config.requests (for backward compatibility)
            default_window: Optional default window to override config.window (for backward compatibility)
        """
        self.config = config or RateLimitConfig()
        
        # Override config.requests if default_limit is provided
        if default_limit is not None:
            self.config.requests = default_limit
        
        # Override config.window if default_window is provided
        if default_window is not None:
            self.config.window = default_window
        
        if REDIS_AVAILABLE and redis_client:
            self.redis = redis_client
            self.use_redis = True
        else:
            self.redis = None
            self.use_redis = False
            # Fallback to in-memory storage
            self._in_memory_storage: Dict[str, Dict[str, Any]] = {}
            # Thread-safe locks for in-memory storage
            self._storage_lock = threading.RLock()  # Reentrant lock for storage access
            self._key_locks: Dict[str, threading.Lock] = {}  # Per-key locks for fine-grained control
            self._key_locks_lock = threading.Lock()  # Lock for managing key_locks dictionary
            logging.warning("Using in-memory rate limiting (not distributed)")
        
        self._logger = logging.getLogger("lazarus.rate_limiter")

    def is_allowed(
        self,
        identifier: str,
        user_id: Optional[str] = None,
        check_ip_reputation: bool = True,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> RateLimitResult:
        """
        Check if request is allowed with rate limiting.
        
        Args:
            identifier: IP address or unique identifier
            user_id: Optional user ID for user-based limiting
            check_ip_reputation: Whether to check IP reputation
            limit: Optional custom limit for this request (overrides config)
            window: Optional custom window for this request (overrides config)

        Returns:
            RateLimitResult with allowed status and metadata
        """
        # Use custom limit if provided, otherwise use config
        request_limit = limit if limit is not None else self.config.requests
        request_window = window if window is not None else self.config.window
        
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
            return self._is_allowed_redis(key, identifier, request_limit, request_window)
        else:
            return self._is_allowed_in_memory(key, identifier, request_limit, request_window)

    def _is_allowed_redis(self, key: str, identifier: str, request_limit: Optional[int] = None, request_window: Optional[int] = None) -> RateLimitResult:
        """Check rate limit using Redis"""
        # Use provided limit/window or fall back to config
        limit = request_limit if request_limit is not None else self.config.requests
        window = request_window if request_window is not None else self.config.window
        try:
            pipe = self.redis.pipeline()
            pipe.get(f"{key}:count")
            pipe.get(f"{key}:backoff")
            pipe.get(f"{key}:window_start")
            pipe.ttl(f"{key}:count")
            results = pipe.execute()
            
            # Safely unpack pipeline results (handles mocks / missing keys)
            if len(results) >= 4:
                count, backoff, window_start, ttl = results
            else:
                count = backoff = window_start = ttl = None
            
            # Check if in backoff period
            if backoff:
                backoff_end = float(backoff)
                if time.time() < backoff_end:
                    # Increment count to track violations during backoff
                    count = int(count) if count else 0
                    count += 1
                    # Recalculate backoff with increased count
                    backoff_time = min(
                        self.config.backoff_base ** (count - self.config.requests + 1),
                        self.config.backoff_max
                    )
                    # Update backoff time if it increased
                    new_backoff_end = time.time() + backoff_time
                    if new_backoff_end > backoff_end:
                        pipe.set(f"{key}:backoff", new_backoff_end, ex=backoff_time)
                        pipe.execute()
                        retry_after = backoff_time
                    else:
                        pipe.execute()
                        retry_after = int(backoff_end - time.time())
                    
                    return RateLimitResult(
                        allowed=False,
                        retry_after=retry_after,
                        reason=f"Rate limit exceeded, backoff active"
                    )
            
            # Initialize window if needed
            if not window_start:
                window_start = time.time()
                pipe.set(f"{key}:window_start", window_start, ex=window)
                pipe.set(f"{key}:count", 0, ex=window)
                count = 0
            else:
                window_start = float(window_start)
                # Reset if window expired
                if time.time() - window_start > window:
                    pipe.delete(f"{key}:count")
                    pipe.delete(f"{key}:backoff")
                    pipe.set(f"{key}:window_start", time.time(), ex=window)
                    pipe.set(f"{key}:count", 0, ex=window)
                    count = 0
                else:
                    count = int(count) if count else 0
            
            # Check if limit exceeded
            if count >= limit:
                # Calculate exponential backoff
                backoff_time = min(
                    self.config.backoff_base ** (count - limit + 1),
                    self.config.backoff_max
                )
                backoff_end = time.time() + backoff_time
                pipe.set(f"{key}:backoff", backoff_end, ex=backoff_time)
                pipe.execute()
                
                return RateLimitResult(
                    allowed=False,
                    retry_after=backoff_time,
                    reason=f"Rate limit exceeded ({count}/{limit})"
                )
            
            # Increment counter
            pipe.incr(f"{key}:count")
            pipe.expire(f"{key}:count", window)
            pipe.execute()
            
            # Calculate remaining
            remaining = limit - (count + 1)
            reset_at = datetime.fromtimestamp(window_start + window)
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_at=reset_at,
                limit=limit
            )
            
        except Exception as e:
            self._logger.error(f"Redis rate limiting error: {e}")
            # Fallback to allow request if Redis fails
            return RateLimitResult(allowed=True, reason="Rate limiting error, allowing request")

    def _get_key_lock(self, key: str) -> threading.Lock:
        """
        Get or create a lock for a specific key.
        
        This provides fine-grained locking - each key has its own lock,
        allowing concurrent access to different keys while preventing
        race conditions on the same key.
        
        Args:
            key: The rate limit key
            
        Returns:
            Lock for the specific key
        """
        with self._key_locks_lock:
            if key not in self._key_locks:
                self._key_locks[key] = threading.Lock()
            return self._key_locks[key]

    def _is_allowed_in_memory(self, key: str, identifier: str, request_limit: Optional[int] = None, request_window: Optional[int] = None) -> RateLimitResult:
        """Check rate limit using in-memory storage (fallback) with thread safety"""
        # Use provided limit/window or fall back to config
        limit = request_limit if request_limit is not None else self.config.requests
        window = request_window if request_window is not None else self.config.window
        
        # Get per-key lock for this specific identifier
        key_lock = self._get_key_lock(key)
        
        with key_lock:
            now = time.time()
            
            # Get or create entry (thread-safe with key lock)
            if key not in self._in_memory_storage:
                self._in_memory_storage[key] = {
                    "count": 0,
                    "window_start": now,
                    "backoff_until": None
                }
            
            entry = self._in_memory_storage[key]
            
            # Check if in backoff period
            if entry["backoff_until"] and now < entry["backoff_until"]:
                # Increment count to track violations during backoff
                entry["count"] += 1
                # Recalculate backoff with increased count
                backoff_time = min(
                    self.config.backoff_base ** (entry["count"] - limit + 1),
                    self.config.backoff_max
                )
                # Update backoff time if it increased
                new_backoff_until = now + backoff_time
                if new_backoff_until > entry["backoff_until"]:
                    entry["backoff_until"] = new_backoff_until
                
                retry_after = int(entry["backoff_until"] - now)
                return RateLimitResult(
                    allowed=False,
                    retry_after=retry_after,
                    reason="Rate limit exceeded, backoff active"
                )
            
            # Reset if window expired
            if now - entry["window_start"] > window:
                entry["count"] = 0
                entry["window_start"] = now
                entry["backoff_until"] = None
            
            # Check if limit exceeded
            if entry["count"] >= limit:
                # Calculate exponential backoff
                backoff_time = min(
                    self.config.backoff_base ** (entry["count"] - limit + 1),
                    self.config.backoff_max
                )
                entry["backoff_until"] = now + backoff_time
                
                return RateLimitResult(
                    allowed=False,
                    retry_after=backoff_time,
                    reason=f"Rate limit exceeded ({entry['count']}/{limit})"
                )
            
            # Increment counter
            entry["count"] += 1
            
            # Calculate remaining
            remaining = limit - entry["count"]
            reset_at = datetime.fromtimestamp(entry["window_start"] + window)
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_at=reset_at,
                limit=limit
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
        """Clean up old entries (thread-safe for in-memory storage)"""
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
            # Clean up in-memory storage (thread-safe)
            with self._storage_lock:
                now = time.time()
                to_delete = []
                
                for key, entry in self._in_memory_storage.items():
                    # Remove entries that are outside window and not in backoff
                    if now - entry["window_start"] > self.config.window and not entry["backoff_until"]:
                        to_delete.append(key)
                
                for key in to_delete:
                    del self._in_memory_storage[key]
                    # Also clean up the key lock
                    with self._key_locks_lock:
                        if key in self._key_locks:
                            del self._key_locks[key]
                
                if to_delete:
                    self._logger.info(f"Cleaned up {len(to_delete)} expired in-memory entries")

    def reset(self, identifier: str, user_id: Optional[str] = None) -> bool:
        """
        Reset rate limit for a specific identifier (thread-safe for in-memory storage).
        
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
            # Thread-safe reset for in-memory storage
            key_lock = self._get_key_lock(key)
            with key_lock:
                if key in self._in_memory_storage:
                    del self._in_memory_storage[key]
                # Also clean up the key lock
                with self._key_locks_lock:
                    if key in self._key_locks:
                        del self._key_locks[key]
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
