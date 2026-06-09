"""
tests/integration/test_performance.py — Performance integration tests.

Tests for performance characteristics under load:
- Concurrent request handling
- Database performance under load
- Storage performance under load
- Memory usage under load
- Response time benchmarks
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.config import (
    load_config,
    save_config,
    record_checkin,
    LAZARUS_DIR,
)
from core.database import DatabaseManager, DatabaseConfig
from core.security import (
    verify_api_key,
    key_manager,
)
from core.rate_limiter import DistributedRateLimiter


@pytest.fixture
def temp_lazarus_dir():
    """Create temporary Lazarus directory for testing"""
    temp_dir = tempfile.mkdtemp()
    original_dir = LAZARUS_DIR
    
    # Override LAZARUS_DIR for testing
    import core.config
    core.config.LAZARUS_DIR = Path(temp_dir)
    
    yield Path(temp_dir)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    core.config.LAZARUS_DIR = original_dir


@pytest.fixture
def test_api_key():
    """Provide test API key"""
    os.environ["LAZARUS_API_KEY"] = "test_api_key_12345678901234567890"
    yield "test_api_key_12345678901234567890"
    if "LAZARUS_API_KEY" in os.environ:
        del os.environ["LAZARUS_API_KEY"]


@pytest.fixture
def test_database(temp_lazarus_dir):
    """Create test database"""
    db_path = temp_lazarus_dir / "test_lazarus.db"
    config = DatabaseConfig(path=db_path)
    db = DatabaseManager(config)  # Database is automatically initialized
    yield db
    db.close()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def mock_redis():
    """Mock Redis for rate limiting tests"""
    with patch('redis.Redis') as mock_redis_class:
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        yield mock_redis


class TestConcurrentRequestHandling:
    """Test concurrent request handling performance"""

    def test_concurrent_api_key_verification(self, temp_lazarus_dir, test_api_key):
        """Test concurrent API key verification"""
        # Step 1: Perform concurrent verifications
        num_threads = 50
        results = []
        errors = []
        
        def verify_key(thread_id):
            try:
                result = verify_api_key(test_api_key)
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 2: Create threads
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=verify_key, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Step 3: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 4: Verify results
        assert len(results) == num_threads
        assert len(errors) == 0
        assert all(result[1] for result in results)
        
        # Step 5: Verify performance
        assert duration < 5.0  # Should complete in < 5 seconds
        avg_time = duration / num_threads
        assert avg_time < 0.1  # Average < 100ms per verification

    def test_concurrent_checkin_operations(self, temp_lazarus_dir, test_api_key):
        """Test concurrent check-in operations"""
        from core.config import BeneficiaryConfig, VaultConfig, LazarusConfig
        
        # Step 1: Create initial configuration
        config = LazarusConfig(
            owner_name="Test Owner",
            owner_email="owner@example.com",
            beneficiary=BeneficiaryConfig(
                name="Test Beneficiary",
                email="beneficiary@example.com",
                public_key_path=str(temp_lazarus_dir / "public_key.pem")
            ),
            vault=VaultConfig(
                secret_file_path=str(temp_lazarus_dir / "secret.txt"),
                encrypted_file_path=str(temp_lazarus_dir / "encrypted.bin"),
                key_blob="test_key_blob",
                ipfs_cid=None
            ),
            checkin_interval_days=30,
            last_checkin_timestamp=None,
            telegram_chat_id=None,
            armed=True,
            storage_config=None,
            license_key=None,
            subscription_tier="free",
            wallet_limit=1,
            license_valid_until=None
        )
        save_config(config)
        
        # Step 2: Perform concurrent check-ins
        num_threads = 20
        results = []
        errors = []
        
        def perform_checkin(thread_id):
            try:
                config = load_config()
                updated_config = record_checkin(config)
                save_config(updated_config)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 3: Create threads
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=perform_checkin, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Step 4: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 5: Verify results
        assert len(results) == num_threads
        assert len(errors) == 0
        
        # Step 6: Verify performance
        assert duration < 10.0  # Should complete in < 10 seconds
        avg_time = duration / num_threads
        assert avg_time < 0.5  # Average < 500ms per check-in

    def test_concurrent_rate_limit_checks(self, temp_lazarus_dir, mock_redis):
        """Test concurrent rate limit checks"""
        # Step 1: Create rate limiter
        limiter = DistributedRateLimiter(
            redis_client=mock_redis,
            default_limit=100,
            default_window=60
        )
        
        # Step 2: Perform concurrent rate limit checks
        num_threads = 100
        results = []
        errors = []
        
        def check_rate_limit(thread_id):
            try:
                allowed, remaining = limiter.is_allowed(
                    identifier=f"test:{thread_id}",
                    limit=10,
                    window=60
                )
                results.append((thread_id, allowed, remaining))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 3: Create threads
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=check_rate_limit, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Step 4: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 5: Verify results
        assert len(results) == num_threads
        assert len(errors) == 0
        assert all(result[1] for result in results)  # All should be allowed
        
        # Step 6: Verify performance
        assert duration < 5.0  # Should complete in < 5 seconds
        avg_time = duration / num_threads
        assert avg_time < 0.05  # Average < 50ms per check


class TestDatabasePerformance:
    """Test database performance under load"""

    def test_concurrent_user_creation(self, temp_lazarus_dir, test_database):
        """Test concurrent user creation"""
        # Step 1: Perform concurrent user creation
        num_threads = 50
        results = []
        errors = []
        
        def create_user(thread_id):
            try:
                user_id = test_database.create_user(
                    username=f"testuser{thread_id}",
                    email=f"test{thread_id}@example.com",
                    password_hash="hashed_password_123",
                    api_key=f"test_api_key_{thread_id}"
                )
                results.append((thread_id, user_id))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 2: Create threads
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=create_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Step 3: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 4: Verify results
        assert len(results) == num_threads
        assert len(errors) == 0
        assert all(result[1] is not None for result in results)
        
        # Step 5: Verify performance
        assert duration < 10.0  # Should complete in < 10 seconds
        avg_time = duration / num_threads
        assert avg_time < 0.2  # Average < 200ms per user creation

    def test_concurrent_database_queries(self, temp_lazarus_dir, test_database):
        """Test concurrent database queries"""
        # Step 1: Create test users
        user_ids = []
        for i in range(20):
            user_id = test_database.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password_hash="hashed_password_123",
                api_key=f"test_api_key_{i}"
            )
            user_ids.append(user_id)
        
        # Step 2: Perform concurrent queries
        num_threads = 100
        results = []
        errors = []
        
        def query_user(thread_id):
            try:
                user_id = user_ids[thread_id % len(user_ids)]
                user = test_database.get_user(user_id)
                results.append((thread_id, user is not None))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 3: Create threads
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=query_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Step 4: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 5: Verify results
        assert len(results) == num_threads
        assert len(errors) == 0
        assert all(result[1] for result in results)
        
        # Step 6: Verify performance
        assert duration < 5.0  # Should complete in < 5 seconds
        avg_time = duration / num_threads
        assert avg_time < 0.05  # Average < 50ms per query

    def test_database_transaction_performance(self, temp_lazarus_dir, test_database):
        """Test database transaction performance"""
        # Step 1: Perform multiple transactions
        num_transactions = 50
        results = []
        
        start_time = time.time()
        for i in range(num_transactions):
            try:
                # Create user
                user_id = test_database.create_user(
                    username=f"testuser{i}",
                    email=f"test{i}@example.com",
                    password_hash="hashed_password_123",
                    api_key=f"test_api_key_{i}"
                )
                
                # Query user
                user = test_database.get_user(user_id)
                
                results.append(user_id is not None and user is not None)
            except Exception as e:
                results.append(False)
        
        duration = time.time() - start_time
        
        # Step 2: Verify results
        assert all(results)
        
        # Step 3: Verify performance
        assert duration < 10.0  # Should complete in < 10 seconds
        avg_time = duration / num_transactions
        assert avg_time < 0.2  # Average < 200ms per transaction


class TestStoragePerformance:
    """Test storage performance under load"""

    def test_concurrent_file_encryption(self, temp_lazarus_dir):
        """Test concurrent file encryption"""
        from core.encryption import encrypt_file
        
        # Step 1: Create test files
        files = []
        for i in range(20):
            test_file = temp_lazarus_dir / f"test_file_{i}.txt"
            test_content = b"Test content for encryption " * 100  # ~2KB
            test_file.write_bytes(test_content)
            files.append(test_file)
        
        # Step 2: Perform concurrent encryption
        results = []
        errors = []
        
        def encrypt_file_thread(file_path, thread_id):
            try:
                encrypted_path = temp_lazarus_dir / f"encrypted_{thread_id}.bin"
                encrypt_file(
                    str(file_path),
                    str(encrypted_path),
                    "test_encryption_key_32bytes!!"
                )
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 3: Create threads
        start_time = time.time()
        threads = []
        for i, file_path in enumerate(files):
            thread = threading.Thread(target=encrypt_file_thread, args=(file_path, i))
            threads.append(thread)
            thread.start()
        
        # Step 4: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 5: Verify results
        assert len(results) == len(files)
        assert len(errors) == 0
        
        # Step 6: Verify performance
        assert duration < 10.0  # Should complete in < 10 seconds
        avg_time = duration / len(files)
        assert avg_time < 0.5  # Average < 500ms per encryption

    def test_concurrent_file_decryption(self, temp_lazarus_dir):
        """Test concurrent file decryption"""
        from core.encryption import encrypt_file, decrypt_file
        
        # Step 1: Create and encrypt test files
        files = []
        for i in range(20):
            test_file = temp_lazarus_dir / f"test_file_{i}.txt"
            test_content = b"Test content for decryption " * 100  # ~2KB
            test_file.write_bytes(test_content)
            
            encrypted_file = temp_lazarus_dir / f"encrypted_{i}.bin"
            encrypt_file(
                str(test_file),
                str(encrypted_file),
                "test_encryption_key_32bytes!!"
            )
            files.append(encrypted_file)
        
        # Step 2: Perform concurrent decryption
        results = []
        errors = []
        
        def decrypt_file_thread(file_path, thread_id):
            try:
                decrypted_path = temp_lazarus_dir / f"decrypted_{thread_id}.txt"
                decrypt_file(
                    str(file_path),
                    str(decrypted_path),
                    "test_encryption_key_32bytes!!"
                )
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Step 3: Create threads
        start_time = time.time()
        threads = []
        for i, file_path in enumerate(files):
            thread = threading.Thread(target=decrypt_file_thread, args=(file_path, i))
            threads.append(thread)
            thread.start()
        
        # Step 4: Wait for completion
        for thread in threads:
            thread.join()
        duration = time.time() - start_time
        
        # Step 5: Verify results
        assert len(results) == len(files)
        assert len(errors) == 0
        
        # Step 6: Verify performance
        assert duration < 10.0  # Should complete in < 10 seconds
        avg_time = duration / len(files)
        assert avg_time < 0.5  # Average < 500ms per decryption


class TestMemoryUsage:
    """Test memory usage under load"""

    def test_memory_usage_during_concurrent_operations(self, temp_lazarus_dir, test_database):
        """Test memory usage during concurrent operations"""
        import psutil
        import gc
        
        # Step 1: Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Step 2: Perform concurrent operations
        num_threads = 50
        results = []
        
        def create_and_query_user(thread_id):
            try:
                user_id = test_database.create_user(
                    username=f"testuser{thread_id}",
                    email=f"test{thread_id}@example.com",
                    password_hash="hashed_password_123",
                    api_key=f"test_api_key_{thread_id}"
                )
                user = test_database.get_user(user_id)
                results.append(user_id is not None and user is not None)
            except Exception as e:
                results.append(False)
        
        # Step 3: Create threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=create_and_query_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Step 4: Wait for completion
        for thread in threads:
            thread.join()
        
        # Step 5: Force garbage collection
        gc.collect()
        
        # Step 6: Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Step 7: Verify results
        assert all(results)
        
        # Step 8: Verify memory usage
        assert memory_increase < 100  # Should increase by < 100MB

    def test_memory_cleanup_after_operations(self, temp_lazarus_dir, test_database):
        """Test memory cleanup after operations"""
        import psutil
        import gc
        
        # Step 1: Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Step 2: Perform operations
        for i in range(100):
            user_id = test_database.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password_hash="hashed_password_123",
                api_key=f"test_api_key_{i}"
            )
            user = test_database.get_user(user_id)
        
        # Step 3: Force garbage collection
        gc.collect()
        
        # Step 4: Get memory after operations
        memory_after_ops = process.memory_info().rss / 1024 / 1024  # MB
        
        # Step 5: Close database
        test_database.close()
        
        # Step 6: Force garbage collection again
        gc.collect()
        
        # Step 7: Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Step 8: Verify memory cleanup
        assert memory_increase < 50  # Should increase by < 50MB after cleanup


class TestResponseTimeBenchmarks:
    """Test response time benchmarks"""

    def test_api_key_verification_response_time(self, temp_lazarus_dir, test_api_key):
        """Test API key verification response time"""
        # Step 1: Perform multiple verifications
        num_iterations = 100
        response_times = []
        
        for i in range(num_iterations):
            start_time = time.time()
            result = verify_api_key(test_api_key)
            duration = (time.time() - start_time) * 1000  # ms
            response_times.append(duration)
        
        # Step 2: Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Step 3: Verify performance
        assert avg_time < 10  # Average < 10ms
        assert max_time < 50  # Max < 50ms
        assert min_time < 5  # Min < 5ms

    def test_database_query_response_time(self, temp_lazarus_dir, test_database):
        """Test database query response time"""
        # Step 1: Create test user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )
        
        # Step 2: Perform multiple queries
        num_iterations = 100
        response_times = []
        
        for i in range(num_iterations):
            start_time = time.time()
            user = test_database.get_user(user_id)
            duration = (time.time() - start_time) * 1000  # ms
            response_times.append(duration)
        
        # Step 3: Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Step 4: Verify performance
        assert avg_time < 20  # Average < 20ms
        assert max_time < 100  # Max < 100ms
        assert min_time < 10  # Min < 10ms

    def test_file_encryption_response_time(self, temp_lazarus_dir):
        """Test file encryption response time"""
        from core.encryption import encrypt_file
        
        # Step 1: Create test file
        test_file = temp_lazarus_dir / "test_file.txt"
        test_content = b"Test content for encryption " * 1000  # ~20KB
        test_file.write_bytes(test_content)
        
        # Step 2: Perform multiple encryptions
        num_iterations = 50
        response_times = []
        
        for i in range(num_iterations):
            encrypted_file = temp_lazarus_dir / f"encrypted_{i}.bin"
            start_time = time.time()
            encrypt_file(
                str(test_file),
                str(encrypted_file),
                "test_encryption_key_32bytes!!"
            )
            duration = (time.time() - start_time) * 1000  # ms
            response_times.append(duration)
        
        # Step 3: Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Step 4: Verify performance
        assert avg_time < 100  # Average < 100ms
        assert max_time < 500  # Max < 500ms
        assert min_time < 50  # Min < 50ms


class TestLoadTesting:
    """Test system behavior under load"""

    def test_sustained_load(self, temp_lazarus_dir, test_database):
        """Test system under sustained load"""
        # Step 1: Perform sustained operations
        duration_seconds = 10
        operations_per_second = 10
        total_operations = duration_seconds * operations_per_second
        
        results = []
        start_time = time.time()
        
        for i in range(total_operations):
            # Perform operation
            user_id = test_database.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password_hash="hashed_password_123",
                api_key=f"test_api_key_{i}"
            )
            results.append(user_id is not None)
            
            # Sleep to maintain rate
            elapsed = time.time() - start_time
            target_time = (i + 1) / operations_per_second
            if elapsed < target_time:
                time.sleep(target_time - elapsed)
        
        # Step 2: Verify results
        assert all(results)
        assert len(results) == total_operations
        
        # Step 3: Verify timing
        actual_duration = time.time() - start_time
        assert actual_duration < duration_seconds + 2  # Allow 2s margin

    def test_burst_load(self, temp_lazarus_dir, test_database):
        """Test system under burst load"""
        # Step 1: Perform burst of operations
        burst_size = 100
        results = []
        
        start_time = time.time()
        for i in range(burst_size):
            user_id = test_database.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password_hash="hashed_password_123",
                api_key=f"test_api_key_{i}"
            )
            results.append(user_id is not None)
        duration = time.time() - start_time
        
        # Step 2: Verify results
        assert all(results)
        assert len(results) == burst_size
        
        # Step 3: Verify performance
        assert duration < 20.0  # Should complete in < 20 seconds
        ops_per_second = burst_size / duration
        assert ops_per_second > 5  # Should handle > 5 ops/sec


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
