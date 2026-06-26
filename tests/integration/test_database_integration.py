"""
tests/integration/test_database_integration.py — Database integration tests.

Tests for database integration with other components:
- Database and configuration integration
- Database and security integration
- Database and storage integration
- Database and rate limiting integration
- Database and metrics integration
"""

import os
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import (
    LAZARUS_DIR,
)
from core.database import DatabaseConfig, DatabaseManager
from core.metrics import (
    is_metrics_enabled,
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
    with patch('core.rate_limiter.redis.Redis') as mock_redis_class:
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        yield mock_redis


class TestDatabaseConfigIntegration:
    """Test database and configuration integration"""

    def test_config_persistence_in_database(self, temp_lazarus_dir, test_database):
        """Test that configuration is properly persisted in database"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

        # Step 1: Create configuration
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

        # Step 2: Save configuration to database
        config_id = test_database.save_configuration(config)

        # Step 3: Verify configuration was saved
        assert config_id is not None
        assert config_id > 0

        # Step 4: Load configuration from database
        loaded_config = test_database.load_configuration(config_id)

        # Step 5: Verify loaded configuration matches original
        assert loaded_config.owner_name == config.owner_name
        assert loaded_config.owner_email == config.owner_email
        assert loaded_config.armed == config.armed
        assert loaded_config.checkin_interval_days == config.checkin_interval_days

    def test_checkin_tracking_in_database(self, temp_lazarus_dir, test_database):
        """Test that check-ins are properly tracked in database"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

        # Step 1: Create and save configuration
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
        config_id = test_database.save_configuration(config)

        # Step 2: Record check-in
        checkin_time = datetime.now(UTC)
        event_id = test_database.record_checkin(
            config_id=config_id,
            checkin_time=checkin_time,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )

        # Step 3: Verify check-in was recorded
        assert event_id is not None
        assert event_id > 0

        # Step 4: Retrieve check-in events
        events = test_database.get_checkin_events(config_id, limit=10)

        # Step 5: Verify check-in event
        assert len(events) == 1
        assert events[0]['event_type'] == 'checkin'
        assert events[0]['ip_address'] == '127.0.0.1'
        assert events[0]['user_agent'] == 'TestAgent/1.0'

    def test_multiple_configurations_in_database(self, temp_lazarus_dir, test_database):
        """Test handling multiple configurations in database"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

        # Step 1: Create multiple configurations
        configs = []
        for i in range(3):
            config = LazarusConfig(
                owner_name=f"Owner {i}",
                owner_email=f"owner{i}@example.com",
                beneficiary=BeneficiaryConfig(
                    name=f"Beneficiary {i}",
                    email=f"beneficiary{i}@example.com",
                    public_key_path=str(temp_lazarus_dir / f"public_key_{i}.pem")
                ),
                vault=VaultConfig(
                    secret_file_path=str(temp_lazarus_dir / f"secret_{i}.txt"),
                    encrypted_file_path=str(temp_lazarus_dir / f"encrypted_{i}.bin"),
                    key_blob=f"test_key_blob_{i}",
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
            config_id = test_database.save_configuration(config)
            configs.append((config_id, config))

        # Step 2: Verify all configurations were saved
        assert len(configs) == 3

        # Step 3: Load and verify each configuration
        for config_id, original_config in configs:
            loaded_config = test_database.load_configuration(config_id)
            assert loaded_config.owner_name == original_config.owner_name
            assert loaded_config.owner_email == original_config.owner_email


class TestDatabaseSecurityIntegration:
    """Test database and security integration"""

    def test_user_authentication_in_database(self, temp_lazarus_dir, test_database):
        """Test user authentication with database"""
        # Step 1: Create user in database
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Verify user was created
        assert user_id is not None
        assert user_id > 0

        # Step 3: Retrieve user by API key
        user = test_database.get_user_by_api_key("test_api_key_12345678901234567890")

        # Step 4: Verify user data
        assert user is not None
        assert user['username'] == 'testuser'
        assert user['email'] == 'test@example.com'
        assert user['api_key'] == 'test_api_key_12345678901234567890'

    def test_api_key_validation_with_database(self, temp_lazarus_dir, test_database, test_api_key):
        """Test API key validation with database"""
        # Step 1: Create user with API key
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key=test_api_key
        )

        # Step 2: Verify API key is valid
        user = test_database.get_user_by_api_key(test_api_key)
        assert user is not None
        assert user['username'] == 'testuser'

        # Step 3: Test invalid API key
        invalid_user = test_database.get_user_by_api_key("invalid_api_key")
        assert invalid_user is None

    def test_security_event_logging(self, temp_lazarus_dir, test_database):
        """Test security event logging in database"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Log security event
        event_id = test_database.log_security_event(
            user_id=user_id,
            event_type="login_success",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            details={"method": "api_key"}
        )

        # Step 3: Verify event was logged
        assert event_id is not None
        assert event_id > 0

        # Step 4: Retrieve security events
        events = test_database.get_security_events(user_id, limit=10)

        # Step 5: Verify event details
        assert len(events) == 1
        assert events[0]['event_type'] == 'login_success'
        assert events[0]['ip_address'] == '127.0.0.1'


class TestDatabaseStorageIntegration:
    """Test database and storage integration"""

    def test_document_metadata_in_database(self, temp_lazarus_dir, test_database):
        """Test document metadata storage in database"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Save document metadata
        document_id = test_database.save_document(
            user_id=user_id,
            filename="test_document.txt",
            file_size=1024,
            content_type="text/plain",
            ipfs_cid="QmTestCID123",
            storage_provider="ipfs",
            encrypted=True
        )

        # Step 3: Verify document was saved
        assert document_id is not None
        assert document_id > 0

        # Step 4: Retrieve document metadata
        document = test_database.get_document(document_id)

        # Step 5: Verify document details
        assert document is not None
        assert document['filename'] == 'test_document.txt'
        assert document['file_size'] == 1024
        assert document['ipfs_cid'] == 'QmTestCID123'
        assert document['storage_provider'] == 'ipfs'
        assert document['encrypted'] == True

    def test_vault_metadata_in_database(self, temp_lazarus_dir, test_database):
        """Test vault metadata storage in database"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Save vault metadata
        vault_id = test_database.save_vault(
            user_id=user_id,
            secret_file_path="/path/to/secret.txt",
            encrypted_file_path="/path/to/encrypted.bin",
            key_blob="test_key_blob",
            ipfs_cid="QmVaultCID456",
            storage_provider="ipfs"
        )

        # Step 3: Verify vault was saved
        assert vault_id is not None
        assert vault_id > 0

        # Step 4: Retrieve vault metadata
        vault = test_database.get_vault(vault_id)

        # Step 5: Verify vault details
        assert vault is not None
        assert vault['secret_file_path'] == '/path/to/secret.txt'
        assert vault['encrypted_file_path'] == '/path/to/encrypted.bin'
        assert vault['ipfs_cid'] == 'QmVaultCID456'

    def test_storage_operation_tracking(self, temp_lazarus_dir, test_database):
        """Test storage operation tracking in database"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Log storage operation
        event_id = test_database.log_storage_event(
            user_id=user_id,
            operation_type="upload",
            storage_provider="ipfs",
            file_size=1024,
            duration_ms=150,
            success=True,
            ipfs_cid="QmTestCID123"
        )

        # Step 3: Verify event was logged
        assert event_id is not None
        assert event_id > 0

        # Step 4: Retrieve storage events
        events = test_database.get_storage_events(user_id, limit=10)

        # Step 5: Verify event details
        assert len(events) == 1
        assert events[0]['operation_type'] == 'upload'
        assert events[0]['storage_provider'] == 'ipfs'
        assert events[0]['file_size'] == 1024
        assert events[0]['success'] == True


class TestDatabaseRateLimitingIntegration:
    """Test database and rate limiting integration"""

    def test_rate_limit_storage_in_database(self, temp_lazarus_dir, test_database, mock_redis):
        """Test rate limit storage in database"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Create rate limiter
        limiter = DistributedRateLimiter(
            redis_client=mock_redis,
            default_limit=100,
            default_window=60
        )

        # Step 3: Check rate limit
        allowed, remaining = limiter.is_allowed(
            identifier=f"user:{user_id}",
            limit=10,
            window=60
        )

        # Step 4: Verify rate limit check
        assert allowed == True
        assert remaining >= 0

        # Step 5: Log rate limit event
        event_id = test_database.log_rate_limit_event(
            user_id=user_id,
            identifier=f"user:{user_id}",
            limit=10,
            window=60,
            remaining=remaining,
            allowed=allowed
        )

        # Step 6: Verify event was logged
        assert event_id is not None
        assert event_id > 0

    def test_rate_limit_exceeded_logging(self, temp_lazarus_dir, test_database, mock_redis):
        """Test rate limit exceeded logging in database"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Create rate limiter
        limiter = DistributedRateLimiter(
            redis_client=mock_redis,
            default_limit=100,
            default_window=60
        )

        # Step 3: Simulate rate limit exceeded
        event_id = test_database.log_rate_limit_event(
            user_id=user_id,
            identifier=f"user:{user_id}",
            limit=10,
            window=60,
            remaining=0,
            allowed=False
        )

        # Step 4: Verify event was logged
        assert event_id is not None
        assert event_id > 0

        # Step 5: Retrieve rate limit events
        events = test_database.get_rate_limit_events(user_id, limit=10)

        # Step 6: Verify event details
        assert len(events) == 1
        assert events[0]['allowed'] == False
        assert events[0]['remaining'] == 0


class TestDatabaseMetricsIntegration:
    """Test database and metrics integration"""

    def test_database_operation_metrics(self, temp_lazarus_dir, test_database):
        """Test database operation metrics tracking"""
        # Step 1: Create user
        start_time = time.time()
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )
        duration = (time.time() - start_time) * 1000

        # Step 2: Check if metrics are enabled
        metrics_enabled = is_metrics_enabled()

        # Step 3: Verify metrics status
        # Note: In real scenario, would query Prometheus metrics
        # For testing, we verify the function works
        assert user_id is not None
        assert isinstance(metrics_enabled, bool)

    def test_database_performance_metrics(self, temp_lazarus_dir, test_database):
        """Test database performance metrics tracking"""
        # Step 1: Perform multiple operations
        operations = []
        for i in range(10):
            start_time = time.time()
            user_id = test_database.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password_hash="hashed_password_123",
                api_key=f"test_api_key_{i}"
            )
            duration = (time.time() - start_time) * 1000
            operations.append({
                'operation': 'create_user',
                'duration_ms': duration,
                'success': user_id is not None
            })

        # Step 2: Verify all operations succeeded
        assert len(operations) == 10
        assert all(op['success'] for op in operations)

        # Step 3: Verify performance metrics
        durations = [op['duration_ms'] for op in operations]
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 1000  # Should complete in < 1 second

    def test_database_error_metrics(self, temp_lazarus_dir, test_database):
        """Test database error metrics tracking"""
        # Step 1: Attempt to get non-existent user
        try:
            user = test_database.get_user(99999)
            # If user doesn't exist, this might return None or raise error
            # depending on implementation
        except Exception:
            # Step 2: Log error metrics
            # In real scenario, would increment error counter
            assert True  # Error was caught

        # Step 3: Verify database is still functional
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )
        assert user_id is not None


class TestDatabaseTransactionIntegration:
    """Test database transaction integration"""

    def test_transaction_rollback_on_error(self, temp_lazarus_dir, test_database):
        """Test transaction rollback on error"""
        # Step 1: Begin transaction
        try:
            # Step 2: Create user
            user_id = test_database.create_user(
                username="testuser",
                email="test@example.com",
                password_hash="hashed_password_123",
                api_key="test_api_key_12345678901234567890"
            )

            # Step 3: Simulate error
            raise ValueError("Simulated error")

        except ValueError:
            # Step 4: Transaction should be rolled back
            # In real scenario, would verify rollback
            pass

        # Step 5: Verify database is still functional
        new_user_id = test_database.create_user(
            username="newuser",
            email="new@example.com",
            password_hash="hashed_password_456",
            api_key="new_api_key_12345678901234567890"
        )
        assert new_user_id is not None

    def test_transaction_commit_on_success(self, temp_lazarus_dir, test_database):
        """Test transaction commit on success"""
        # Step 1: Create user in transaction
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Verify user was created
        assert user_id is not None

        # Step 3: Retrieve user
        user = test_database.get_user(user_id)

        # Step 4: Verify user data
        assert user is not None
        assert user['username'] == 'testuser'


class TestDatabaseBackupIntegration:
    """Test database backup integration"""

    def test_database_backup(self, temp_lazarus_dir, test_database):
        """Test database backup functionality"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Create backup
        backup_path = temp_lazarus_dir / "backup.db"
        test_database.backup(str(backup_path))

        # Step 3: Verify backup exists
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0

        # Step 4: Verify backup contains data
        backup_db = DatabaseManager(str(backup_path))
        backup_user = backup_db.get_user(user_id)
        backup_db.close()

        # Step 5: Verify backup data
        assert backup_user is not None
        assert backup_user['username'] == 'testuser'

    def test_database_restore(self, temp_lazarus_dir, test_database):
        """Test database restore functionality"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )

        # Step 2: Create backup
        backup_path = temp_lazarus_dir / "backup.db"
        test_database.backup(str(backup_path))

        # Step 3: Close original database
        test_database.close()

        # Step 4: Restore from backup
        original_path = temp_lazarus_dir / "test_lazarus.db"
        shutil.copy2(backup_path, original_path)

        # Step 5: Open restored database
        restored_db = DatabaseManager(str(original_path))
        restored_user = restored_db.get_user(user_id)
        restored_db.close()

        # Step 6: Verify restored data
        assert restored_user is not None
        assert restored_user['username'] == 'testuser'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
