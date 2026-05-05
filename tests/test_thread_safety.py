"""
tests/test_thread_safety.py — Comprehensive thread-safety tests.

Tests for:
- Thread-safe database operations
- Thread-safe rate limiting
- Concurrent access patterns
- Race condition detection
- Lock contention handling
"""

import pytest
import threading
import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from core.database import (
    DatabaseManager,
    DatabaseConfig,
)
from core.rate_limiter import (
    DistributedRateLimiter,
    RateLimitConfig,
)
from core.config import (
    LazarusConfig,
    BeneficiaryConfig,
    VaultConfig,
)


@pytest.fixture
def temp_db_path():
    """Create temporary database path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.fixture
def db_config(temp_db_path):
    """Create test database configuration"""
    return DatabaseConfig(path=temp_db_path)


@pytest.fixture
def db(db_config):
    """Create test database"""
    db = DatabaseManager(db_config)
    yield db
    db.close()


@pytest.fixture
def rate_limiter():
    """Create test rate limiter"""
    return DistributedRateLimiter(config=RateLimitConfig(requests=10, window=60))


class TestDatabaseThreadSafety:
    """Test thread-safe database operations"""

    def test_concurrent_user_creation(self, db):
        """Test concurrent user creation doesn't cause race conditions"""
        user_ids = []
        errors = []
        
        def create_user(index):
            try:
                user_id = db.create_user(
                    f"user{index}@example.com",
                    f"api_key_{index}",
                    f"User {index}"
                )
                user_ids.append(user_id)
            except Exception as e:
                errors.append(e)
        
        # Create 50 users concurrently
        threads = []
        for i in range(50):
            thread = threading.Thread(target=create_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all users were created
        assert len(user_ids) == 50
        
        # Verify all user IDs are unique
        assert len(set(user_ids)) == 50

    def test_concurrent_same_user_access(self, db):
        """Test concurrent access to same user doesn't cause corruption"""
        user_id = db.create_user("test@example.com", "test_key", "Test User")
        
        results = []
        errors = []
        
        def access_user():
            try:
                user = db.get_user_by_email("test@example.com")
                results.append(user)
            except Exception as e:
                errors.append(e)
        
        # Access same user 100 times concurrently
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=access_user)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all results are consistent
        assert len(results) == 100
        assert all(r["email"] == "test@example.com" for r in results)

    def test_concurrent_configuration_updates(self, db):
        """Test concurrent configuration updates don't cause corruption"""
        user_id = db.create_user("test@example.com", "test_key", "Test User")
        
        config_data = LazarusConfig(
            owner_name="Test Owner",
            owner_email="owner@example.com",
            beneficiary=BeneficiaryConfig(
                name="Test Beneficiary",
                email="beneficiary@example.com",
                public_key_path="/path/to/public_key.pem"
            ),
            vault=VaultConfig(
                secret_file_path="/path/to/secret.txt",
                encrypted_file_path="/path/to/encrypted.bin",
                key_blob="base64_encoded_key_blob"
            ),
            checkin_interval_days=30,
            armed=True
        )
        
        config_id = db.create_configuration(user_id, config_data)
        
        results = []
        errors = []
        
        def update_config(index):
            try:
                success = db.update_configuration(config_id, {"armed": index % 2 == 0})
                results.append(success)
            except Exception as e:
                errors.append(e)
        
        # Update configuration 50 times concurrently
        threads = []
        for i in range(50):
            thread = threading.Thread(target=update_config, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all updates succeeded
        assert len(results) == 50
        assert all(results)

    def test_concurrent_event_logging(self, db):
        """Test concurrent event logging doesn't cause corruption"""
        user_id = db.create_user("test@example.com", "test_key", "Test User")
        
        config_data = LazarusConfig(
            owner_name="Test Owner",
            owner_email="owner@example.com",
            beneficiary=BeneficiaryConfig(
                name="Test Beneficiary",
                email="beneficiary@example.com",
                public_key_path="/path/to/public_key.pem"
            ),
            vault=VaultConfig(
                secret_file_path="/path/to/secret.txt",
                encrypted_file_path="/path/to/encrypted.bin",
                key_blob="base64_encoded_key_blob"
            ),
            checkin_interval_days=30,
            armed=True
        )
        
        config_id = db.create_configuration(user_id, config_data)
        
        event_ids = []
        errors = []
        
        def log_event(index):
            try:
                event_id = db.log_event(config_id, f"EVENT_{index}", f"Content {index}")
                event_ids.append(event_id)
            except Exception as e:
                errors.append(e)
        
        # Log 100 events concurrently
        threads = []
        for i in range(100):
            thread = threading.Thread(target=log_event, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all events were logged
        assert len(event_ids) == 100
        
        # Verify all event IDs are unique
        assert len(set(event_ids)) == 100

    def test_concurrent_transaction_operations(self, db):
        """Test concurrent transaction operations don't cause corruption"""
        results = []
        errors = []
        
        def create_user_in_transaction(index):
            try:
                with db.transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                        (f"user{index}@example.com", f"key{index}", f"User {index}")
                    )
                    cursor.execute(
                        "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                        (f"user{index}_2@example.com", f"key{index}_2", f"User {index}_2")
                    )
                results.append(True)
            except Exception as e:
                errors.append(e)
        
        # Create 20 transactions concurrently
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_user_in_transaction, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all transactions succeeded
        assert len(results) == 20

    def test_high_concurrency_load(self, db):
        """Test database under high concurrency load"""
        user_ids = []
        errors = []
        
        def create_user(index):
            try:
                user_id = db.create_user(
                    f"user{index}@example.com",
                    f"api_key_{index}",
                    f"User {index}"
                )
                user_ids.append(user_id)
            except Exception as e:
                errors.append(e)
        
        # Create 200 users concurrently using thread pool
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(create_user, i) for i in range(200)]
            for future in as_completed(futures):
                pass  # Wait for all to complete
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all users were created
        assert len(user_ids) == 200
        
        # Verify all user IDs are unique
        assert len(set(user_ids)) == 200


class TestRateLimiterThreadSafety:
    """Test thread-safe rate limiting operations"""

    def test_concurrent_rate_limit_checks(self, rate_limiter):
        """Test concurrent rate limit checks don't cause race conditions"""
        results = []
        errors = []
        
        def check_rate_limit(index):
            try:
                result = rate_limiter.is_allowed(f"192.168.1.{index % 10}")
                results.append(result.allowed)
            except Exception as e:
                errors.append(e)
        
        # Check rate limits 100 times concurrently
        threads = []
        for i in range(100):
            thread = threading.Thread(target=check_rate_limit, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all checks completed
        assert len(results) == 100

    def test_concurrent_same_identifier(self, rate_limiter):
        """Test concurrent requests from same identifier are properly limited"""
        results = []
        errors = []
        
        def check_rate_limit():
            try:
                result = rate_limiter.is_allowed("192.168.1.1")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Make 20 requests from same IP concurrently
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=check_rate_limit)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all checks completed
        assert len(results) == 20
        
        # Count allowed requests
        allowed_count = sum(1 for r in results if r.allowed)
        
        # Should allow at most the configured limit (10)
        assert allowed_count <= 10, f"Too many requests allowed: {allowed_count}"

    def test_concurrent_different_identifiers(self, rate_limiter):
        """Test concurrent requests from different identifiers are independent"""
        results = []
        errors = []
        
        def check_rate_limit(index):
            try:
                result = rate_limiter.is_allowed(f"192.168.1.{index}")
                results.append((index, result.allowed))
            except Exception as e:
                errors.append(e)
        
        # Make requests from 20 different IPs concurrently
        threads = []
        for i in range(20):
            thread = threading.Thread(target=check_rate_limit, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all checks completed
        assert len(results) == 20
        
        # All different IPs should be allowed
        assert all(allowed for _, allowed in results)

    def test_concurrent_rate_limit_resets(self, rate_limiter):
        """Test concurrent rate limit resets don't cause corruption"""
        results = []
        errors = []
        
        def reset_rate_limit(index):
            try:
                success = rate_limiter.reset(f"192.168.1.{index}")
                results.append(success)
            except Exception as e:
                errors.append(e)
        
        # Reset 50 rate limits concurrently
        threads = []
        for i in range(50):
            thread = threading.Thread(target=reset_rate_limit, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all resets succeeded
        assert len(results) == 50
        assert all(results)

    def test_concurrent_cleanup_operations(self, rate_limiter):
        """Test concurrent cleanup operations don't cause corruption"""
        errors = []
        
        def cleanup():
            try:
                rate_limiter.cleanup()
            except Exception as e:
                errors.append(e)
        
        # Run 10 cleanup operations concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=cleanup)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_high_concurrency_rate_limiting(self, rate_limiter):
        """Test rate limiter under high concurrency load"""
        results = []
        errors = []
        
        def check_rate_limit(index):
            try:
                result = rate_limiter.is_allowed(f"192.168.1.{index % 20}")
                results.append(result.allowed)
            except Exception as e:
                errors.append(e)
        
        # Make 500 requests concurrently using thread pool
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(check_rate_limit, i) for i in range(500)]
            for future in as_completed(futures):
                pass  # Wait for all to complete
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all checks completed
        assert len(results) == 500


class TestRaceConditionDetection:
    """Test for race conditions in concurrent operations"""

    def test_database_race_condition_user_creation(self, db):
        """Test for race conditions in user creation"""
        # This test creates users with the same email from multiple threads
        # Only one should succeed due to unique constraint
        results = []
        errors = []
        
        def create_user():
            try:
                user_id = db.create_user("duplicate@example.com", "key", "User")
                results.append(user_id)
            except Exception as e:
                errors.append(e)
        
        # Try to create duplicate users concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_user)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Only one user should be created
        assert len(results) == 1, f"Expected 1 user, got {len(results)}"
        
        # Others should have failed with constraint errors
        assert len(errors) == 9

    def test_rate_limiter_race_condition_counter(self, rate_limiter):
        """Test for race conditions in rate limit counter"""
        # Make requests rapidly to test counter increment
        results = []
        errors = []
        
        def make_request():
            try:
                result = rate_limiter.is_allowed("192.168.1.100")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Make 15 requests rapidly (limit is 10)
        threads = []
        for _ in range(15):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Count allowed requests
        allowed_count = sum(1 for r in results if r.allowed)
        
        # Should allow exactly 10 requests
        assert allowed_count == 10, f"Expected 10 allowed requests, got {allowed_count}"

    def test_database_race_condition_configuration_update(self, db):
        """Test for race conditions in configuration updates"""
        user_id = db.create_user("test@example.com", "test_key", "Test User")
        
        config_data = LazarusConfig(
            owner_name="Test Owner",
            owner_email="owner@example.com",
            beneficiary=BeneficiaryConfig(
                name="Test Beneficiary",
                email="beneficiary@example.com",
                public_key_path="/path/to/public_key.pem"
            ),
            vault=VaultConfig(
                secret_file_path="/path/to/secret.txt",
                encrypted_file_path="/path/to/encrypted.bin",
                key_blob="base64_encoded_key_blob"
            ),
            checkin_interval_days=30,
            armed=True
        )
        
        config_id = db.create_configuration(user_id, config_data)
        
        results = []
        errors = []
        
        def update_configuration():
            try:
                # Read current value
                config = db.get_configuration(config_id)
                # Update with new value
                success = db.update_configuration(config_id, {"armed": not config.armed})
                results.append(success)
            except Exception as e:
                errors.append(e)
        
        # Update configuration 20 times concurrently
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=update_configuration)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all updates succeeded
        assert len(results) == 20
        assert all(results)


class TestLockContention:
    """Test lock contention under high load"""

    def test_database_lock_contention(self, db):
        """Test database handles lock contention gracefully"""
        user_id = db.create_user("test@example.com", "test_key", "Test User")
        
        results = []
        errors = []
        
        def access_user():
            try:
                user = db.get_user_by_email("test@example.com")
                results.append(user)
            except Exception as e:
                errors.append(e)
        
        # Access same user 200 times concurrently
        threads = []
        for _ in range(200):
            thread = threading.Thread(target=access_user)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all accesses completed
        assert len(results) == 200

    def test_rate_limiter_lock_contention(self, rate_limiter):
        """Test rate limiter handles lock contention gracefully"""
        results = []
        errors = []
        
        def check_rate_limit():
            try:
                result = rate_limiter.is_allowed("192.168.1.200")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Check rate limit 200 times concurrently for same IP
        threads = []
        for _ in range(200):
            thread = threading.Thread(target=check_rate_limit)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all checks completed
        assert len(results) == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
