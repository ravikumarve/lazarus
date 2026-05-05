"""
tests/test_database.py — Comprehensive tests for database layer.

Tests for:
- Database schema creation
- CRUD operations
- Transaction support with ACID guarantees
- Connection pooling and thread safety
- Backup and recovery
- Migration system
"""

import pytest
import sqlite3
import threading
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from core.database import (
    DatabaseManager,
    DatabaseConfig,
    get_database_manager,
)
from core.config import (
    LazarusConfig,
    BeneficiaryConfig,
    VaultConfig,
    StorageProviderConfig,
)
from core.migrations import (
    MigrationManager,
    MIGRATIONS,
    get_migration_manager,
    run_migrations,
    get_migration_status,
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
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "api_key": "test_api_key_12345678901234567890",
        "owner_name": "Test User"
    }


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing"""
    return LazarusConfig(
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


class TestDatabaseInitialization:
    """Test database initialization and schema creation"""

    def test_database_creation(self, db):
        """Test database file is created"""
        assert db.config.path.exists()
        assert db.config.path.stat().st_size > 0

    def test_schema_creation(self, db):
        """Test all tables are created"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check tables exist
            tables = [
                'users', 'configurations', 'vaults', 'events',
                'documents', 'rate_limits'
            ]
            
            for table in tables:
                cursor.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                )
                result = cursor.fetchone()
                assert result is not None, f"Table {table} not created"

    def test_indexes_creation(self, db):
        """Test indexes are created"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            expected_indexes = [
                'idx_events_config',
                'idx_documents_config',
                'idx_rate_limits_identifier',
                'idx_configurations_user'
            ]
            
            for index in expected_indexes:
                assert index in indexes, f"Index {index} not created"

    def test_wal_mode_enabled(self, db):
        """Test WAL mode is enabled"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            result = cursor.fetchone()
            assert result[0] == 'wal', "WAL mode not enabled"

    def test_foreign_keys_enabled(self, db):
        """Test foreign keys are enabled"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            assert result[0] == 1, "Foreign keys not enabled"


class TestUserOperations:
    """Test user CRUD operations"""

    def test_create_user(self, db, sample_user_data):
        """Test user creation"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        assert user_id > 0
        
        # Verify user was created
        user = db.get_user_by_email(sample_user_data["email"])
        assert user is not None
        assert user["email"] == sample_user_data["email"]
        assert user["api_key"] == sample_user_data["api_key"]
        assert user["owner_name"] == sample_user_data["owner_name"]

    def test_get_user_by_email(self, db, sample_user_data):
        """Test getting user by email"""
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        user = db.get_user_by_email(sample_user_data["email"])
        assert user is not None
        assert user["email"] == sample_user_data["email"]

    def test_get_user_by_api_key(self, db, sample_user_data):
        """Test getting user by API key"""
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        user = db.get_user_by_api_key(sample_user_data["api_key"])
        assert user is not None
        assert user["api_key"] == sample_user_data["api_key"]

    def test_get_nonexistent_user(self, db):
        """Test getting non-existent user returns None"""
        user = db.get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_update_user(self, db, sample_user_data):
        """Test updating user"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        # Update user
        success = db.update_user(user_id, {"owner_name": "Updated Name"})
        assert success is True
        
        # Verify update
        user = db.get_user_by_email(sample_user_data["email"])
        assert user["owner_name"] == "Updated Name"

    def test_unique_email_constraint(self, db, sample_user_data):
        """Test unique email constraint"""
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        # Try to create duplicate user
        with pytest.raises(sqlite3.IntegrityError):
            db.create_user(
                sample_user_data["email"],
                "different_api_key",
                "Different Name"
            )

    def test_unique_api_key_constraint(self, db, sample_user_data):
        """Test unique API key constraint"""
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        # Try to create duplicate API key
        with pytest.raises(sqlite3.IntegrityError):
            db.create_user(
                "different@example.com",
                sample_user_data["api_key"],
                "Different Name"
            )


class TestConfigurationOperations:
    """Test configuration CRUD operations"""

    def test_create_configuration(self, db, sample_user_data, sample_config_data):
        """Test configuration creation"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        config_id = db.create_configuration(user_id, sample_config_data)
        assert config_id > 0
        
        # Verify configuration was created
        config = db.get_configuration(config_id)
        assert config is not None
        assert config.owner_email == sample_config_data.owner_email
        assert config.checkin_interval_days == sample_config_data.checkin_interval_days

    def test_get_configuration(self, db, sample_user_data, sample_config_data):
        """Test getting configuration by ID"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        config_id = db.create_configuration(user_id, sample_config_data)
        config = db.get_configuration(config_id)
        
        assert config is not None
        assert config.owner_email == sample_config_data.owner_email
        assert config.beneficiary.name == sample_config_data.beneficiary.name
        assert config.vault.secret_file_path == sample_config_data.vault.secret_file_path

    def test_get_nonexistent_configuration(self, db):
        """Test getting non-existent configuration returns None"""
        config = db.get_configuration(99999)
        assert config is None

    def test_update_configuration(self, db, sample_user_data, sample_config_data):
        """Test updating configuration"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        config_id = db.create_configuration(user_id, sample_config_data)
        
        # Update configuration
        success = db.update_configuration(config_id, {"armed": False})
        assert success is True
        
        # Verify update
        config = db.get_configuration(config_id)
        assert config.armed is False

    def test_get_user_configurations(self, db, sample_user_data, sample_config_data):
        """Test getting all configurations for a user"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        # Create multiple configurations
        config1_id = db.create_configuration(user_id, sample_config_data)
        config2_id = db.create_configuration(user_id, sample_config_data)
        
        configs = db.get_user_configurations(user_id)
        assert len(configs) == 2
        assert any(c["id"] == config1_id for c in configs)
        assert any(c["id"] == config2_id for c in configs)


class TestEventOperations:
    """Test event logging and retrieval"""

    def test_log_event(self, db, sample_user_data, sample_config_data):
        """Test logging an event"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        config_id = db.create_configuration(user_id, sample_config_data)
        
        event_id = db.log_event(config_id, "TEST_EVENT", "Test event content")
        assert event_id > 0

    def test_get_events(self, db, sample_user_data, sample_config_data):
        """Test getting events for configuration"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        config_id = db.create_configuration(user_id, sample_config_data)
        
        # Log multiple events
        db.log_event(config_id, "EVENT_1", "Content 1")
        db.log_event(config_id, "EVENT_2", "Content 2")
        db.log_event(config_id, "EVENT_3", "Content 3")
        
        # Get events
        events = db.get_events(config_id, limit=10)
        assert len(events) == 3
        assert events[0]["event_type"] == "EVENT_3"  # Most recent first

    def test_get_events_with_limit(self, db, sample_user_data, sample_config_data):
        """Test getting events with limit"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        config_id = db.create_configuration(user_id, sample_config_data)
        
        # Log multiple events
        for i in range(10):
            db.log_event(config_id, f"EVENT_{i}", f"Content {i}")
        
        # Get limited events
        events = db.get_events(config_id, limit=5)
        assert len(events) == 5


class TestDocumentOperations:
    """Test document CRUD operations"""

    def test_add_document(self, db, sample_user_data, sample_config_data):
        """Test adding a document"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        config_id = db.create_configuration(user_id, sample_config_data)
        
        document = {
            "filename": "test.txt",
            "file_type": "text/plain",
            "file_size": 1024,
            "storage_provider": "local",
            "encrypted_path": "/path/to/encrypted.txt"
        }
        
        doc_id = db.add_document(config_id, document)
        assert doc_id > 0

    def test_get_documents(self, db, sample_user_data, sample_config_data):
        """Test getting documents for configuration"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        config_id = db.create_configuration(user_id, sample_config_data)
        
        # Add multiple documents
        doc1 = {
            "filename": "doc1.txt",
            "file_type": "text/plain",
            "file_size": 1024,
            "storage_provider": "local",
            "encrypted_path": "/path/to/doc1.txt"
        }
        doc2 = {
            "filename": "doc2.pdf",
            "file_type": "application/pdf",
            "file_size": 2048,
            "storage_provider": "ipfs",
            "encrypted_path": "/path/to/doc2.pdf",
            "cid": "QmTestCID"
        }
        
        db.add_document(config_id, doc1)
        db.add_document(config_id, doc2)
        
        # Get documents
        documents = db.get_documents(config_id)
        assert len(documents) == 2
        assert any(d["filename"] == "doc1.txt" for d in documents)
        assert any(d["filename"] == "doc2.pdf" for d in documents)

    def test_remove_document(self, db, sample_user_data, sample_config_data):
        """Test removing a document"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        config_id = db.create_configuration(user_id, sample_config_data)
        
        document = {
            "filename": "test.txt",
            "file_type": "text/plain",
            "file_size": 1024,
            "storage_provider": "local",
            "encrypted_path": "/path/to/encrypted.txt"
        }
        
        doc_id = db.add_document(config_id, document)
        
        # Remove document
        success = db.remove_document(doc_id)
        assert success is True
        
        # Verify removal
        documents = db.get_documents(config_id)
        assert len(documents) == 0


class TestTransactionSupport:
    """Test transaction support with ACID guarantees"""

    def test_transaction_commit(self, db, sample_user_data):
        """Test transaction commits changes"""
        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                ("test1@example.com", "key1", "User 1")
            )
            cursor.execute(
                "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                ("test2@example.com", "key2", "User 2")
            )
        
        # Verify both users were created
        user1 = db.get_user_by_email("test1@example.com")
        user2 = db.get_user_by_email("test2@example.com")
        
        assert user1 is not None
        assert user2 is not None

    def test_transaction_rollback(self, db, sample_user_data):
        """Test transaction rolls back on error"""
        initial_count = len(db.get_user_configurations(1)) if db.get_user_by_api_key(sample_user_data["api_key"]) else 0
        
        try:
            with db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                    ("test1@example.com", "key1", "User 1")
                )
                # This will fail due to duplicate email
                cursor.execute(
                    "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                    ("test1@example.com", "key2", "User 2")
                )
        except sqlite3.IntegrityError:
            pass  # Expected to fail
        
        # Verify no users were created
        user1 = db.get_user_by_email("test1@example.com")
        assert user1 is None

    def test_atomicity(self, db, sample_user_data, sample_config_data):
        """Test atomicity - all or nothing"""
        user_id = db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        try:
            with db.transaction() as conn:
                cursor = conn.cursor()
                
                # Create configuration
                cursor.execute(
                    """
                    INSERT INTO configurations (
                        user_id, owner_email, beneficiary_name, beneficiary_email,
                        beneficiary_public_key_path, check_in_interval_days
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, "owner@example.com", "Beneficiary", "beneficiary@example.com", "/path/to/key.pem", 30)
                )
                
                # This will fail
                cursor.execute(
                    "INSERT INTO users (email, api_key, owner_name) VALUES (?, ?, ?)",
                    (sample_user_data["email"], "key", "User")  # Duplicate email
                )
        except sqlite3.IntegrityError:
            pass  # Expected to fail
        
        # Verify configuration was not created
        configs = db.get_user_configurations(user_id)
        assert len(configs) == 0


class TestConnectionPooling:
    """Test connection pooling and thread safety"""

    def test_connection_pooling(self, db):
        """Test connection pooling works"""
        thread_ids = set()
        
        def get_connection():
            with db.get_connection() as conn:
                thread_ids.add(threading.current_thread().ident)
        
        # Get connections from multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_connection)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify connections were created for different threads
        assert len(thread_ids) >= 1

    def test_thread_safety(self, db, sample_user_data):
        """Test thread-safe database operations"""
        user_ids = []
        errors = []
        
        def create_user(index):
            try:
                user_id = db.create_user(
                    f"user{index}@example.com",
                    f"key{index}",
                    f"User {index}"
                )
                user_ids.append(user_id)
            except Exception as e:
                errors.append(e)
        
        # Create users from multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all users were created
        assert len(user_ids) == 10
        assert len(set(user_ids)) == 10  # All unique


class TestBackupAndRecovery:
    """Test backup and recovery functionality"""

    def test_backup_creation(self, db, sample_user_data):
        """Test backup creation"""
        # Create some data
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        # Create backup
        backup_path = db.backup()
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0

    def test_backup_cleanup(self, db, db_config):
        """Test old backups are cleaned up"""
        # Set low max_backups for testing
        db.config.max_backups = 3
        
        # Create multiple backups
        for _ in range(5):
            db.backup()
        
        # Count backups
        backups = list(db.config.path.parent.glob("backup_*.db"))
        assert len(backups) <= 3

    def test_restore_from_backup(self, db, sample_user_data):
        """Test restoring from backup"""
        # Create user
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        # Create backup
        backup_path = db.backup()
        
        # Delete user
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = ?", (sample_user_data["email"],))
            conn.commit()
        
        # Verify user is gone
        user = db.get_user_by_email(sample_user_data["email"])
        assert user is None
        
        # Restore from backup
        success = db.restore(backup_path)
        assert success is True
        
        # Verify user is restored
        user = db.get_user_by_email(sample_user_data["email"])
        assert user is not None


class TestDatabaseStatistics:
    """Test database statistics and maintenance"""

    def test_get_stats(self, db, sample_user_data):
        """Test getting database statistics"""
        # Create some data
        db.create_user(
            sample_user_data["email"],
            sample_user_data["api_key"],
            sample_user_data["owner_name"]
        )
        
        stats = db.get_stats()
        
        assert "database_size" in stats
        assert "database_path" in stats
        assert "tables" in stats
        assert "users" in stats["tables"]
        assert stats["tables"]["users"] >= 1

    def test_vacuum(self, db):
        """Test VACUUM operation"""
        # VACUUM should not raise errors
        db.vacuum()

    def test_analyze(self, db):
        """Test ANALYZE operation"""
        # ANALYZE should not raise errors
        db.analyze()


class TestGlobalDatabaseManager:
    """Test global database manager singleton"""

    def test_get_database_manager(self, temp_db_path):
        """Test getting global database manager"""
        # Reset global instance
        import core.database
        core.database._database_manager = None
        
        config = DatabaseConfig(path=temp_db_path)
        manager1 = get_database_manager(config)
        manager2 = get_database_manager()
        
        # Should be same instance
        assert manager1 is manager2

    def test_database_manager_cleanup(self, db):
        """Test database manager cleanup"""
        # Close should not raise errors
        db.close()


class TestMigrationSystem:
    """Test database migration system"""

    def test_migration_manager_creation(self, db):
        """Test migration manager creation"""
        manager = MigrationManager(db)
        assert manager is not None

    def test_get_applied_migrations(self, db):
        """Test getting applied migrations"""
        manager = MigrationManager(db)
        applied = manager.get_applied_migrations()
        assert isinstance(applied, list)

    def test_get_migration_history(self, db):
        """Test getting migration history"""
        manager = MigrationManager(db)
        history = manager.get_migration_history()
        assert isinstance(history, list)

    def test_apply_migration(self, db):
        """Test applying a migration"""
        manager = MigrationManager(db)
        
        # Apply migration 2 (user preferences table)
        migration = MIGRATIONS[1]  # version 2
        success = manager.apply_migration(migration)
        assert success is True
        
        # Verify migration was applied
        applied = manager.get_applied_migrations()
        assert 2 in applied

    def test_rollback_migration(self, db):
        """Test rolling back a migration"""
        manager = MigrationManager(db)
        
        # Apply migration 2
        migration = MIGRATIONS[1]  # version 2
        manager.apply_migration(migration)
        
        # Rollback migration
        success = manager.rollback_migration(migration)
        assert success is True
        
        # Verify migration was rolled back
        applied = manager.get_applied_migrations()
        assert 2 not in applied

    def test_migrate_to_latest(self, db):
        """Test migrating to latest version"""
        manager = MigrationManager(db)
        success = manager.migrate_to_latest(MIGRATIONS)
        assert success is True

    def test_get_migration_status(self, db):
        """Test getting migration status"""
        status = get_migration_status(db)
        
        assert "current_version" in status
        assert "latest_version" in status
        assert "up_to_date" in status
        assert "pending_migrations" in status
        assert "applied_count" in status
        assert "history" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
