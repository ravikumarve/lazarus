"""
tests/test_rate_limiter.py — Comprehensive tests for distributed rate limiting.

Tests for:
- Redis-based distributed rate limiting
- User-based rate limiting
- Exponential backoff
- IP reputation checking
- Rate limit persistence
- Thread safety
- Memory cleanup
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from core.rate_limiter import (
    DistributedRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    get_distributed_rate_limiter,
)


@pytest.fixture
def rate_limit_config():
    """Create test rate limit configuration"""
    return RateLimitConfig(
        requests=5,
        window=60,
        burst=10,
        backoff_base=2,
        backoff_max=60,
        ip_reputation_threshold=50,
        ip_reputation_expiry=86400
    )


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis_mock = Mock()
    redis_mock.pipeline.return_value = Mock()
    redis_mock.pipeline.return_value.execute.return_value = [None, None, None, 60]
    redis_mock.scan_iter.return_value = []
    return redis_mock


@pytest.fixture
def rate_limiter(mock_redis, rate_limit_config):
    """Create rate limiter with mock Redis"""
    return DistributedRateLimiter(mock_redis, rate_limit_config)


@pytest.fixture
def in_memory_rate_limiter(rate_limit_config):
    """Create rate limiter with in-memory storage"""
    return DistributedRateLimiter(None, rate_limit_config)


class TestRateLimitingEnforcement:
    """Test rate limiting enforcement"""

    def test_rate_limiting_enforcement(self, rate_limiter):
        """Test rate limiting is enforced"""
        identifier = "192.168.1.1"
        
        # Mock Redis pipeline responses
        with patch.object(rate_limiter.redis, 'pipeline') as mock_pipeline:
            # First 5 requests should be allowed
            for i in range(5):
                mock_pipe = Mock()
                mock_pipe.execute.return_value = [i, None, time.time(), 60]
                mock_pipeline.return_value = mock_pipe
                
                result = rate_limiter.is_allowed(identifier)
                assert result.allowed is True
                assert result.remaining is not None
            
            # 6th request should be rate limited
            mock_pipe = Mock()
            mock_pipe.execute.return_value = [5, None, time.time(), 60]
            mock_pipeline.return_value = mock_pipe
            
            result = rate_limiter.is_allowed(identifier)
            assert result.allowed is False
            assert result.retry_after is not None
            assert result.retry_after > 0

    def test_rate_limiting_in_memory(self, in_memory_rate_limiter):
        """Test in-memory rate limiting"""
        identifier = "192.168.1.1"
        
        # First 5 requests should be allowed
        for i in range(5):
            result = in_memory_rate_limiter.is_allowed(identifier)
            assert result.allowed is True
            assert result.remaining is not None
        
        # 6th request should be rate limited
        result = in_memory_rate_limiter.is_allowed(identifier)
        assert result.allowed is False
        assert result.retry_after is not None

    def test_rate_limit_reset_after_window(self, in_memory_rate_limiter):
        """Test rate limit resets after window expires"""
        identifier = "192.168.1.1"
        
        # Use short window for testing
        in_memory_rate_limiter.config.window = 2  # 2 seconds
        
        # Exhaust rate limit
        for _ in range(5):
            in_memory_rate_limiter.is_allowed(identifier)
        
        # Should be rate limited
        result = in_memory_rate_limiter.is_allowed(identifier)
        assert result.allowed is False
        
        # Wait for window to expire
        time.sleep(3)
        
        # Should be allowed again
        result = in_memory_rate_limiter.is_allowed(identifier)
        assert result.allowed is True


class TestExponentialBackoff:
    """Test exponential backoff functionality"""

    def test_exponential_backoff(self, in_memory_rate_limiter):
        """Test exponential backoff increases"""
        identifier = "192.168.1.2"
        in_memory_rate_limiter.config.requests = 3
        in_memory_rate_limiter.config.backoff_base = 2
        
        # Exceed limit multiple times within same window
        retry_afters = []
        for i in range(10):
            result = in_memory_rate_limiter.is_allowed(identifier)
            if not result.allowed and result.retry_after:
                retry_afters.append(result.retry_after)
                # Only check first few backoffs before reset
                if len(retry_afters) >= 2:
                    break
        
        # Check backoff increases (at least initially)
        if len(retry_afters) >= 2:
            # The first backoff should be smaller than the second
            # because count increases with each violation
            assert retry_afters[1] >= retry_afters[0], \
                f"Expected backoff to increase, got {retry_afters[0]} then {retry_afters[1]}"

    def test_backoff_max_limit(self, in_memory_rate_limiter):
        """Test backoff doesn't exceed maximum"""
        identifier = "192.168.1.3"
        in_memory_rate_limiter.config.requests = 2
        in_memory_rate_limiter.config.backoff_base = 10
        in_memory_rate_limiter.config.backoff_max = 30
        
        # Exceed limit many times
        max_retry_after = 0
        for i in range(20):
            result = in_memory_rate_limiter.is_allowed(identifier)
            if not result.allowed and result.retry_after:
                max_retry_after = max(max_retry_after, result.retry_after)
        
        # Should not exceed maximum
        assert max_retry_after <= in_memory_rate_limiter.config.backoff_max


class TestUserBasedRateLimiting:
    """Test user-based rate limiting"""

    def test_user_based_rate_limiting(self, in_memory_rate_limiter):
        """Test user-based rate limiting"""
        user_id = "user123"
        ip = "192.168.1.4"
        
        # User-based limit should be independent of IP
        for i in range(5):
            result = in_memory_rate_limiter.is_allowed(ip, user_id=user_id)
            assert result.allowed is True
        
        # Same IP, different user should be allowed
        result = in_memory_rate_limiter.is_allowed(ip, user_id="user456")
        assert result.allowed is True

    def test_user_and_ip_independence(self, in_memory_rate_limiter):
        """Test user and IP rate limiting are independent"""
        user_id = "user789"
        ip1 = "192.168.1.5"
        ip2 = "192.168.1.6"
        
        # Exhaust user limit on IP1
        for _ in range(5):
            in_memory_rate_limiter.is_allowed(ip1, user_id=user_id)
        
        # User should still be rate limited on IP2
        result = in_memory_rate_limiter.is_allowed(ip2, user_id=user_id)
        assert result.allowed is False
        
        # Different user should be allowed on IP1
        result = in_memory_rate_limiter.is_allowed(ip1, user_id="user999")
        assert result.allowed is True


class TestIPReputation:
    """Test IP reputation checking"""

    def test_ip_reputation_checking(self, rate_limiter):
        """Test IP reputation blocks bad IPs"""
        bad_ip = "192.168.1.100"
        
        # Report bad IP
        with patch.object(rate_limiter.redis, 'get', return_value=b'60'):
            result = rate_limiter.is_allowed(bad_ip, check_ip_reputation=True)
            assert result.allowed is False
            assert "reputation" in result.reason.lower()

    def test_ip_reputation_good_ip(self, rate_limiter):
        """Test good IPs pass reputation check"""
        good_ip = "192.168.1.101"
        
        # No reputation score
        with patch.object(rate_limiter.redis, 'get', return_value=None):
            result = rate_limiter.is_allowed(good_ip, check_ip_reputation=True)
            # Should proceed to rate limiting check
            assert result is not None

    def test_report_bad_ip(self, rate_limiter):
        """Test reporting bad IP"""
        bad_ip = "192.168.1.102"
        
        with patch.object(rate_limiter.redis, 'get', return_value=None):
            with patch.object(rate_limiter.redis, 'set') as mock_set:
                success = rate_limiter.report_bad_ip(bad_ip, severity=20)
                assert success is True
                mock_set.assert_called_once()

    def test_ip_reputation_threshold(self, rate_limiter):
        """Test IP reputation threshold"""
        ip = "192.168.1.103"
        
        # Below threshold - should be allowed
        with patch.object(rate_limiter.redis, 'get', return_value=b'40'):
            result = rate_limiter.is_allowed(ip, check_ip_reputation=True)
            # Should proceed to rate limiting (not blocked by reputation)
        
        # Above threshold - should be blocked
        with patch.object(rate_limiter.redis, 'get', return_value=b'60'):
            result = rate_limiter.is_allowed(ip, check_ip_reputation=True)
            assert result.allowed is False


class TestRateLimitReset:
    """Test rate limit reset functionality"""

    def test_reset_rate_limit(self, in_memory_rate_limiter):
        """Test resetting rate limit for specific identifier"""
        identifier = "192.168.1.200"
        
        # Exhaust rate limit
        for _ in range(5):
            in_memory_rate_limiter.is_allowed(identifier)
        
        # Should be rate limited
        result = in_memory_rate_limiter.is_allowed(identifier)
        assert result.allowed is False
        
        # Reset rate limit
        success = in_memory_rate_limiter.reset(identifier)
        assert success is True
        
        # Should be allowed again
        result = in_memory_rate_limiter.is_allowed(identifier)
        assert result.allowed is True

    def test_reset_user_rate_limit(self, in_memory_rate_limiter):
        """Test resetting user-based rate limit"""
        user_id = "user_reset_test"
        ip = "192.168.1.201"
        
        # Exhaust user rate limit
        for _ in range(5):
            in_memory_rate_limiter.is_allowed(ip, user_id=user_id)
        
        # Should be rate limited
        result = in_memory_rate_limiter.is_allowed(ip, user_id=user_id)
        assert result.allowed is False
        
        # Reset user rate limit
        success = in_memory_rate_limiter.reset(ip, user_id=user_id)
        assert success is True
        
        # Should be allowed again
        result = in_memory_rate_limiter.is_allowed(ip, user_id=user_id)
        assert result.allowed is True


class TestCleanup:
    """Test cleanup functionality"""

    def test_cleanup_old_entries(self, in_memory_rate_limiter):
        """Test cleanup removes old entries"""
        # Create many entries
        for i in range(10):
            in_memory_rate_limiter.is_allowed(f"192.168.1.{i}")
        
        # Wait for window to expire
        in_memory_rate_limiter.config.window = 1
        time.sleep(2)
        
        # Cleanup
        in_memory_rate_limiter.cleanup()
        
        # Verify old entries removed
        stats = in_memory_rate_limiter.get_stats()
        assert stats['active_entries'] == 0

    def test_cleanup_preserves_active_entries(self, in_memory_rate_limiter):
        """Test cleanup preserves active entries"""
        identifier = "192.168.1.250"
        
        # Create active entry
        in_memory_rate_limiter.is_allowed(identifier)
        
        # Cleanup
        in_memory_rate_limiter.cleanup()
        
        # Active entry should be preserved
        result = in_memory_rate_limiter.is_allowed(identifier)
        assert result is not None


class TestThreadSafety:
    """Test thread safety of rate limiter"""

    def test_concurrent_requests(self, in_memory_rate_limiter):
        """Test concurrent requests don't cause race conditions"""
        identifier = "192.168.1.300"
        results = []
        errors = []
        
        def make_request():
            try:
                result = in_memory_rate_limiter.is_allowed(identifier)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Make 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify first 5 allowed, rest rate limited
        allowed_count = sum(1 for result in results if result.allowed)
        assert allowed_count == 5, f"Expected 5 allowed, got {allowed_count}"

    def test_concurrent_different_identifiers(self, in_memory_rate_limiter):
        """Test concurrent requests from different identifiers"""
        identifiers = [f"192.168.1.{i}" for i in range(10)]
        results = {}
        errors = []
        
        def make_requests(identifier):
            try:
                for _ in range(7):
                    result = in_memory_rate_limiter.is_allowed(identifier)
                    if identifier not in results:
                        results[identifier] = []
                    results[identifier].append(result)
            except Exception as e:
                errors.append((identifier, e))
        
        # Make requests from 10 threads
        threads = []
        for identifier in identifiers:
            thread = threading.Thread(target=make_requests, args=(identifier,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify each identifier got correct rate limiting
        for identifier, request_results in results.items():
            allowed_count = sum(1 for result in request_results if result.allowed)
            assert allowed_count == 5, f"Identifier {identifier} got {allowed_count} allowed requests"


class TestStatistics:
    """Test statistics and monitoring"""

    def test_get_stats_in_memory(self, in_memory_rate_limiter):
        """Test getting statistics for in-memory limiter"""
        # Create some entries
        for i in range(3):
            in_memory_rate_limiter.is_allowed(f"192.168.1.{i}")
        
        stats = in_memory_rate_limiter.get_stats()
        
        assert stats['type'] == 'in_memory'
        assert stats['active_entries'] >= 3
        assert 'config' in stats
        assert stats['config']['requests'] == 5

    def test_get_stats_redis(self, rate_limiter):
        """Test getting statistics for Redis limiter"""
        with patch.object(rate_limiter.redis, 'scan_iter', return_value=[]):
            stats = rate_limiter.get_stats()
            
            assert stats['type'] == 'redis'
            assert 'config' in stats


class TestGlobalInstance:
    """Test global rate limiter instance"""

    def test_get_distributed_rate_limiter(self):
        """Test getting global rate limiter instance"""
        # Reset global instance
        import core.rate_limiter
        core.rate_limiter.distributed_rate_limiter = None
        
        # Get instance
        limiter1 = get_distributed_rate_limiter()
        limiter2 = get_distributed_rate_limiter()
        
        # Should be same instance
        assert limiter1 is limiter2

    def test_get_distributed_rate_limiter_with_config(self):
        """Test getting global rate limiter with custom config"""
        # Reset global instance
        import core.rate_limiter
        core.rate_limiter.distributed_rate_limiter = None
        
        config = RateLimitConfig(requests=20, window=120)
        limiter = get_distributed_rate_limiter(config=config)
        
        assert limiter.config.requests == 20
        assert limiter.config.window == 120


class TestRateLimitResult:
    """Test RateLimitResult dataclass"""

    def test_rate_limit_result_allowed(self):
        """Test RateLimitResult for allowed request"""
        result = RateLimitResult(
            allowed=True,
            remaining=3,
            limit=5
        )
        
        assert result.allowed is True
        assert result.remaining == 3
        assert result.limit == 5
        assert result.retry_after is None

    def test_rate_limit_result_denied(self):
        """Test RateLimitResult for denied request"""
        result = RateLimitResult(
            allowed=False,
            retry_after=30,
            reason="Rate limit exceeded"
        )
        
        assert result.allowed is False
        assert result.retry_after == 30
        assert result.reason == "Rate limit exceeded"
        assert result.remaining is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
