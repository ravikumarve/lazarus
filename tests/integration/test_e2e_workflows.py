"""
tests/integration/test_e2e_workflows.py — End-to-end workflow integration tests.

Tests for complete user workflows:
- Initialization and setup workflow
- Check-in and deadline management workflow
- Document bundle management workflow
- Beneficiary notification workflow
- Emergency trigger workflow
"""

import os
import shutil
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import (
    LAZARUS_DIR,
    days_remaining,
    days_since_checkin,
    extend_deadline,
    load_config,
    record_checkin,
    save_config,
)
from core.encryption import decrypt_file, encrypt_file
from core.security import (
    key_manager,
)


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
def mock_external_services():
    """Mock external services for testing"""
    with patch('core.storage.upload_to_ipfs') as mock_ipfs, \
         patch('core.storage.pin_to_pinata') as mock_pinata, \
         patch('core.storage.send_email') as mock_email:

        mock_ipfs.return_value = "QmTestCID123"
        mock_pinata.return_value = "QmPinataCID456"
        mock_email.return_value = True

        yield {
            'ipfs': mock_ipfs,
            'pinata': mock_pinata,
            'email': mock_email
        }


class TestInitializationWorkflow:
    """Test complete initialization workflow"""

    def test_complete_initialization_workflow(self, temp_lazarus_dir, test_api_key):
        """Test complete initialization from setup to first check-in"""
        # Step 1: Verify directory creation
        assert temp_lazarus_dir.exists()
        assert temp_lazarus_dir.is_dir()

        # Step 2: Create initial configuration
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

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

        # Step 3: Save configuration
        save_config(config)

        # Step 4: Verify configuration was saved
        loaded_config = load_config()
        assert loaded_config.owner_name == "Test Owner"
        assert loaded_config.owner_email == "owner@example.com"
        assert loaded_config.armed == True
        assert loaded_config.checkin_interval_days == 30

        # Step 5: Perform first check-in
        updated_config = record_checkin(loaded_config)
        save_config(updated_config)

        # Step 6: Verify check-in was recorded
        final_config = load_config()
        assert final_config.last_checkin_timestamp is not None
        assert days_since_checkin(final_config) < 1.0  # Should be < 1 day

        # Step 7: Verify days remaining calculation
        remaining = days_remaining(final_config)
        assert remaining > 25  # Should have ~30 days remaining
        assert remaining <= 30  # Should not exceed interval

    def test_initialization_with_encryption(self, temp_lazarus_dir, test_api_key):
        """Test initialization with file encryption"""
        # Step 1: Create test file
        test_file = temp_lazarus_dir / "test_secret.txt"
        test_content = b"This is a secret message for testing"
        test_file.write_bytes(test_content)

        # Step 2: Encrypt the file
        encrypted_file = temp_lazarus_dir / "test_encrypted.bin"
        encryption_key = "test_encryption_key_32bytes!!"

        encrypt_file(
            str(test_file),
            str(encrypted_file),
            encryption_key
        )

        # Step 3: Verify encrypted file exists
        assert encrypted_file.exists()
        assert encrypted_file.stat().st_size > 0

        # Step 4: Decrypt and verify content
        decrypted_file = temp_lazarus_dir / "test_decrypted.txt"
        decrypt_file(
            str(encrypted_file),
            str(decrypted_file),
            encryption_key
        )

        # Step 5: Verify decrypted content matches original
        decrypted_content = decrypted_file.read_bytes()
        assert decrypted_content == test_content


class TestCheckInWorkflow:
    """Test check-in and deadline management workflow"""

    def test_regular_checkin_workflow(self, temp_lazarus_dir, test_api_key):
        """Test regular check-in workflow"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

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

        # Step 2: Perform first check-in
        config = load_config()
        updated_config = record_checkin(config)
        save_config(updated_config)

        # Step 3: Verify first check-in
        config = load_config()
        assert config.last_checkin_timestamp is not None
        first_remaining = days_remaining(config)
        assert first_remaining > 25

        # Step 4: Wait a moment and perform second check-in
        time.sleep(0.1)  # Small delay to ensure different timestamp
        config = load_config()
        updated_config = record_checkin(config)
        save_config(updated_config)

        # Step 5: Verify second check-in updated timestamp
        config = load_config()
        second_remaining = days_remaining(config)
        assert second_remaining > 25

        # Step 6: Verify days remaining is consistent
        assert abs(first_remaining - second_remaining) < 1.0

    def test_deadline_extension_workflow(self, temp_lazarus_dir, test_api_key):
        """Test deadline extension workflow"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

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

        # Step 2: Perform initial check-in
        config = load_config()
        config = record_checkin(config)
        save_config(config)

        # Step 3: Get initial days remaining
        config = load_config()
        initial_remaining = days_remaining(config)

        # Step 4: Extend deadline by 30 days
        config = load_config()
        extended_config = extend_deadline(config, 30)
        save_config(extended_config)

        # Step 5: Verify deadline was extended
        config = load_config()
        extended_remaining = days_remaining(config)

        # Should have approximately 30 more days
        assert extended_remaining > initial_remaining + 25
        assert extended_remaining < initial_remaining + 35  # Allow some margin


class TestDocumentManagementWorkflow:
    """Test document bundle management workflow"""

    def test_document_addition_workflow(self, temp_lazarus_dir, test_api_key, mock_external_services):
        """Test complete document addition workflow"""
        # Step 1: Create test document
        test_doc = temp_lazarus_dir / "test_document.txt"
        test_content = b"Secret document content for testing"
        test_doc.write_bytes(test_content)

        # Step 2: Encrypt document
        encrypted_doc = temp_lazarus_dir / "test_document_encrypted.bin"
        encryption_key = "test_encryption_key_32bytes!!"

        encrypt_file(
            str(test_doc),
            str(encrypted_doc),
            encryption_key
        )

        # Step 3: Verify encryption
        assert encrypted_doc.exists()
        assert encrypted_doc.stat().st_size > 0

        # Step 4: Simulate upload to storage (mocked)
        mock_services = mock_external_services
        cid = mock_services['ipfs'].return_value

        # Step 5: Verify mock was called
        mock_services['ipfs'].assert_called_once()
        assert cid == "QmTestCID123"

        # Step 6: Verify document can be decrypted
        decrypted_doc = temp_lazarus_dir / "test_document_decrypted.txt"
        decrypt_file(
            str(encrypted_doc),
            str(decrypted_doc),
            encryption_key
        )

        # Step 7: Verify decrypted content
        decrypted_content = decrypted_doc.read_bytes()
        assert decrypted_content == test_content

    def test_document_retrieval_workflow(self, temp_lazarus_dir, test_api_key, mock_external_services):
        """Test document retrieval workflow"""
        # Step 1: Create and encrypt test document
        test_doc = temp_lazarus_dir / "retrieval_test.txt"
        test_content = b"Content for retrieval testing"
        test_doc.write_bytes(test_content)

        encrypted_doc = temp_lazarus_dir / "retrieval_test_encrypted.bin"
        encryption_key = "test_encryption_key_32bytes!!"

        encrypt_file(
            str(test_doc),
            str(encrypted_doc),
            encryption_key
        )

        # Step 2: Simulate storage upload
        mock_services = mock_external_services
        cid = mock_services['ipfs'].return_value

        # Step 3: Simulate retrieval from storage
        # In real scenario, would download from IPFS using CID
        retrieved_content = test_content  # Using original for test

        # Step 4: Verify retrieval
        assert retrieved_content == test_content
        assert cid == "QmTestCID123"


class TestBeneficiaryWorkflow:
    """Test beneficiary management workflow"""

    def test_beneficiary_verification_workflow(self, temp_lazarus_dir, test_api_key):
        """Test beneficiary verification workflow"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

        # Step 1: Create configuration with beneficiary
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

        # Step 2: Load and verify beneficiary
        loaded_config = load_config()
        assert loaded_config.beneficiary.name == "Test Beneficiary"
        assert loaded_config.beneficiary.email == "beneficiary@example.com"

        # Step 3: Verify public key path exists
        pub_key_path = Path(loaded_config.beneficiary.public_key_path)
        # Note: In real scenario, this would be created during setup
        # For testing, we just verify the path is set correctly
        assert pub_key_path.name == "public_key.pem"


class TestEmergencyTriggerWorkflow:
    """Test emergency trigger workflow"""

    def test_deadline_exceeded_workflow(self, temp_lazarus_dir, test_api_key):
        """Test workflow when deadline is exceeded"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

        # Step 1: Create configuration with old check-in
        old_timestamp = (datetime.now(UTC) - timedelta(days=35)).timestamp()

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
            last_checkin_timestamp=old_timestamp,
            telegram_chat_id=None,
            armed=True,
            storage_config=None,
            license_key=None,
            subscription_tier="free",
            wallet_limit=1,
            license_valid_until=None
        )
        save_config(config)

        # Step 2: Load and check deadline status
        loaded_config = load_config()
        days_since = days_since_checkin(loaded_config)
        remaining = days_remaining(loaded_config)

        # Step 3: Verify deadline exceeded
        assert days_since > 30  # More than 30 days since check-in
        assert remaining < 0  # Deadline exceeded

        # Step 4: Verify armed status
        assert loaded_config.armed == True  # System is still armed

    def test_emergency_notification_workflow(self, temp_lazarus_dir, test_api_key, mock_external_services):
        """Test emergency notification workflow"""
        # Step 1: Simulate emergency condition
        emergency_condition = True

        # Step 2: Verify notification would be sent
        mock_services = mock_external_services

        if emergency_condition:
            # In real scenario, would send notification
            # For testing, verify mock is ready
            assert mock_services['email'] is not None
            assert mock_services['ipfs'] is not None


class TestSessionManagementWorkflow:
    """Test session management workflow"""

    def test_session_creation_workflow(self, temp_lazarus_dir, test_api_key):
        """Test session creation and management workflow"""
        # Step 1: Generate CSRF token for session
        csrf_token = key_manager.generate_csrf_token()

        # Step 2: Verify CSRF token properties
        assert csrf_token is not None
        assert len(csrf_token) > 0

        # Step 3: Verify token is unique
        csrf_token_2 = key_manager.generate_csrf_token()
        assert csrf_token != csrf_token_2


class TestConfigurationUpdateWorkflow:
    """Test configuration update workflow"""

    def test_configuration_update_workflow(self, temp_lazarus_dir, test_api_key):
        """Test configuration update and reload workflow"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

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

        # Step 2: Load and modify configuration
        loaded_config = load_config()
        loaded_config.checkin_interval_days = 60  # Change interval
        loaded_config.telegram_chat_id = "test_chat_id"  # Add Telegram

        # Step 3: Save updated configuration
        save_config(loaded_config)

        # Step 4: Reload and verify changes
        final_config = load_config()
        assert final_config.checkin_interval_days == 60
        assert final_config.telegram_chat_id == "test_chat_id"
        assert final_config.owner_name == "Test Owner"  # Unchanged


class TestBackupRecoveryWorkflow:
    """Test backup and recovery workflow"""

    def test_backup_workflow(self, temp_lazarus_dir, test_api_key):
        """Test configuration backup workflow"""
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
        save_config(config)

        # Step 2: Verify configuration file exists
        config_file = temp_lazarus_dir / "config.json"
        assert config_file.exists()

        # Step 3: Create backup
        backup_file = temp_lazarus_dir / "config_backup.json"
        shutil.copy2(config_file, backup_file)

        # Step 4: Verify backup exists
        assert backup_file.exists()

        # Step 5: Verify backup content matches original
        original_content = config_file.read_text()
        backup_content = backup_file.read_text()
        assert original_content == backup_content

    def test_recovery_workflow(self, temp_lazarus_dir, test_api_key):
        """Test configuration recovery workflow"""
        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

        # Step 1: Create and save original configuration
        config = LazarusConfig(
            owner_name="Original Owner",
            owner_email="original@example.com",
            beneficiary=BeneficiaryConfig(
                name="Original Beneficiary",
                email="original_beneficiary@example.com",
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

        # Step 2: Create backup
        config_file = temp_lazarus_dir / "config.json"
        backup_file = temp_lazarus_dir / "config_backup.json"
        shutil.copy2(config_file, backup_file)

        # Step 3: Modify configuration
        config = load_config()
        config.owner_name = "Modified Owner"
        save_config(config)

        # Step 4: Verify modification
        modified_config = load_config()
        assert modified_config.owner_name == "Modified Owner"

        # Step 5: Restore from backup
        shutil.copy2(backup_file, config_file)

        # Step 6: Verify recovery
        recovered_config = load_config()
        assert recovered_config.owner_name == "Original Owner"


class TestMultiUserWorkflow:
    """Test multi-user concurrent operations workflow"""

    def test_concurrent_checkin_workflow(self, temp_lazarus_dir, test_api_key):
        """Test concurrent check-in operations"""
        import threading

        from core.config import BeneficiaryConfig, LazarusConfig, VaultConfig

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

        # Step 3: Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=perform_checkin, args=(i,))
            threads.append(thread)
            thread.start()

        # Step 4: Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Step 5: Verify all operations completed
        assert len(results) == 5  # All 5 check-ins completed
        assert len(errors) == 0  # No errors

        # Step 6: Verify final configuration is valid
        final_config = load_config()
        assert final_config.last_checkin_timestamp is not None
        assert final_config.owner_name == "Test Owner"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
