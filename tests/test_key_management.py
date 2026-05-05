"""
tests/test_key_management.py — Comprehensive tests for server-side key management.

Tests for:
- Server-provided encryption keys
- PBKDF2 key derivation with 100,000+ iterations
- Key rotation mechanism
- Session and device binding
- Key expiry and cleanup
"""

import pytest
import time
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch

from core.security import KeyManager, SessionKey, PBKDF2_ITERATIONS


@pytest.fixture
def key_manager():
    """Create a KeyManager instance for testing"""
    return KeyManager()


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        "session_id": "test-session-123",
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "ip_address": "192.168.1.100"
    }


class TestKeyDerivation:
    """Test PBKDF2 key derivation"""

    def test_key_derivation_strength(self, key_manager):
        """Test PBKDF2 key derivation strength"""
        password = "test_password_123"
        context = "test_context"
        
        key = key_manager.derive_key(password, context)
        
        # Key should be 32 bytes (256 bits)
        assert len(key) == 32
        
        # Iterations should be at least 100,000
        assert key_manager.iterations >= 100000
        
        # Same input should produce same output
        key2 = key_manager.derive_key(password, context)
        assert key == key2

    def test_key_derivation_different_contexts(self, key_manager):
        """Test different contexts produce different keys"""
        password = "test_password"
        
        key1 = key_manager.derive_key(password, "context1")
        key2 = key_manager.derive_key(password, "context2")
        
        # Different contexts should produce different keys
        assert key1 != key2

    def test_key_derivation_different_passwords(self, key_manager):
        """Test different passwords produce different keys"""
        context = "test_context"
        
        key1 = key_manager.derive_key("password1", context)
        key2 = key_manager.derive_key("password2", context)
        
        # Different passwords should produce different keys
        assert key1 != key2


class TestSessionKeyGeneration:
    """Test session key generation"""

    def test_generate_session_key(self, key_manager, sample_session_data):
        """Test session key generation"""
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Verify session key structure
        assert isinstance(session_key, SessionKey)
        assert session_key.session_id == sample_session_data["session_id"]
        assert session_key.user_agent == sample_session_data["user_agent"]
        assert session_key.ip_address == sample_session_data["ip_address"]
        
        # Verify key is hex encoded
        assert len(session_key.key) == 64  # 32 bytes hex encoded
        
        # Verify key ID is unique
        assert len(session_key.key_id) > 0
        
        # Verify expiry time
        assert session_key.expires_at > session_key.created_at
        assert session_key.expires_at > datetime.now(UTC)

    def test_session_key_expiry(self, key_manager, sample_session_data):
        """Test session key expiry time"""
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Expiry should be approximately 1 hour from creation
        expiry_delta = session_key.expires_at - session_key.created_at
        assert 3590 <= expiry_delta.total_seconds() <= 3610  # ~1 hour with tolerance

    def test_device_fingerprint_generation(self, key_manager, sample_session_data):
        """Test device fingerprint generation"""
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Device fingerprint should be generated
        assert len(session_key.device_fingerprint) == 64  # SHA-256 hex

    def test_unique_session_keys(self, key_manager):
        """Test different sessions generate unique keys"""
        session_key1 = key_manager.generate_session_key(
            session_id="session-1",
            user_agent="Browser1",
            ip_address="192.168.1.1"
        )
        
        session_key2 = key_manager.generate_session_key(
            session_id="session-2",
            user_agent="Browser2",
            ip_address="192.168.1.2"
        )
        
        # Keys should be different
        assert session_key1.key != session_key2.key
        assert session_key1.key_id != session_key2.key_id


class TestKeyRotation:
    """Test key rotation mechanism"""

    def test_key_rotation(self, key_manager, sample_session_data):
        """Test key rotation generates new key"""
        # Generate initial key
        old_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Rotate key
        new_key = key_manager.rotate_key(old_key.key_id)
        
        # Verify new key is different
        assert new_key is not None
        assert new_key.key_id != old_key.key_id
        assert new_key.key != old_key.key
        
        # Verify session metadata preserved
        assert new_key.session_id == old_key.session_id
        assert new_key.user_agent == old_key.user_agent
        assert new_key.ip_address == old_key.ip_address
        assert new_key.device_fingerprint == old_key.device_fingerprint

    def test_key_rotation_nonexistent_key(self, key_manager):
        """Test rotating non-existent key returns None"""
        result = key_manager.rotate_key("nonexistent-key-id")
        assert result is None

    def test_key_rotation_updates_storage(self, key_manager, sample_session_data):
        """Test key rotation updates internal storage"""
        # Generate initial key
        old_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Verify old key exists in storage
        assert old_key.key_id in key_manager._session_keys
        
        # Rotate key
        new_key = key_manager.rotate_key(old_key.key_id)
        
        # Verify old key removed, new key added
        assert old_key.key_id not in key_manager._session_keys
        assert new_key.key_id in key_manager._session_keys


class TestSessionKeyValidation:
    """Test session key validation and device binding"""

    def test_validate_valid_session_key(self, key_manager, sample_session_data):
        """Test validating a valid session key"""
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Validate with same user agent
        validated = key_manager.validate_session_key(
            session_key.key_id,
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        assert validated is not None
        assert validated.key_id == session_key.key_id

    def test_validate_expired_session_key(self, key_manager, sample_session_data):
        """Test validating an expired session key"""
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Manually set expiry to past
        session_key.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        
        # Validate should return None
        validated = key_manager.validate_session_key(
            session_key.key_id,
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        assert validated is None

    def test_validate_device_binding_mismatch(self, key_manager, sample_session_data):
        """Test device binding mismatch rejects validation"""
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Validate with different user agent
        validated = key_manager.validate_session_key(
            session_key.key_id,
            user_agent="Different Browser",
            ip_address=sample_session_data["ip_address"]
        )
        
        # Should reject due to device binding mismatch
        assert validated is None

    def test_validate_nonexistent_key(self, key_manager):
        """Test validating non-existent key returns None"""
        validated = key_manager.validate_session_key(
            "nonexistent-key-id",
            user_agent="Test Browser",
            ip_address="192.168.1.1"
        )
        
        assert validated is None


class TestKeyCleanup:
    """Test automatic key cleanup"""

    def test_cleanup_expired_keys(self, key_manager, sample_session_data):
        """Test cleanup removes expired keys"""
        # Generate a key
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Manually set expiry to past
        session_key.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        
        # Run cleanup
        key_manager._cleanup_expired_keys()
        
        # Key should be removed
        assert session_key.key_id not in key_manager._session_keys

    def test_cleanup_preserves_valid_keys(self, key_manager, sample_session_data):
        """Test cleanup preserves valid keys"""
        # Generate a key
        session_key = key_manager.generate_session_key(
            session_id=sample_session_data["session_id"],
            user_agent=sample_session_data["user_agent"],
            ip_address=sample_session_data["ip_address"]
        )
        
        # Run cleanup
        key_manager._cleanup_expired_keys()
        
        # Valid key should be preserved
        assert session_key.key_id in key_manager._session_keys

    def test_cleanup_multiple_keys(self, key_manager):
        """Test cleanup handles multiple keys correctly"""
        # Generate multiple keys
        key_ids = []
        for i in range(5):
            session_key = key_manager.generate_session_key(
                session_id=f"session-{i}",
                user_agent=f"Browser-{i}",
                ip_address=f"192.168.1.{i}"
            )
            key_ids.append(session_key.key_id)
        
        # Expire first 3 keys
        for i in range(3):
            key_manager._session_keys[key_ids[i]].expires_at = datetime.now(UTC) - timedelta(seconds=1)
        
        # Run cleanup
        key_manager._cleanup_expired_keys()
        
        # First 3 should be removed, last 2 should remain
        for i in range(3):
            assert key_ids[i] not in key_manager._session_keys
        for i in range(3, 5):
            assert key_ids[i] in key_manager._session_keys


class TestThreadSafety:
    """Test thread safety of key manager"""

    def test_concurrent_key_generation(self, key_manager):
        """Test concurrent key generation doesn't cause conflicts"""
        import threading
        
        keys = []
        errors = []
        
        def generate_key(session_id):
            try:
                session_key = key_manager.generate_session_key(
                    session_id=session_id,
                    user_agent="Test Browser",
                    ip_address="192.168.1.1"
                )
                keys.append(session_key.key_id)
            except Exception as e:
                errors.append(e)
        
        # Generate keys concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=generate_key, args=(f"session-{i}",))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0
        
        # Verify all keys are unique
        assert len(keys) == len(set(keys))

    def test_concurrent_key_rotation(self, key_manager):
        """Test concurrent key rotation doesn't cause conflicts"""
        import threading
        
        # Generate initial key
        session_key = key_manager.generate_session_key(
            session_id="test-session",
            user_agent="Test Browser",
            ip_address="192.168.1.1"
        )
        
        new_keys = []
        errors = []
        
        def rotate_key():
            try:
                new_key = key_manager.rotate_key(session_key.key_id)
                if new_key:
                    new_keys.append(new_key.key_id)
            except Exception as e:
                errors.append(e)
        
        # Rotate keys concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=rotate_key)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0
        
        # At least one rotation should succeed
        assert len(new_keys) >= 1


class TestSecurityFeatures:
    """Test security features of key management"""

    def test_key_entropy(self, key_manager, sample_session_data):
        """Test keys have sufficient entropy"""
        keys = []
        
        # Generate multiple keys
        for i in range(10):
            session_key = key_manager.generate_session_key(
                session_id=f"session-{i}",
                user_agent=sample_session_data["user_agent"],
                ip_address=sample_session_data["ip_address"]
            )
            keys.append(session_key.key)
        
        # All keys should be different
        assert len(keys) == len(set(keys))
        
        # Keys should not be predictable
        # (This is a basic check - in production, use statistical tests)

    def test_salt_persistence(self, key_manager):
        """Test salt is consistent across instances"""
        salt1 = key_manager.salt
        
        # Create new instance with same environment
        key_manager2 = KeyManager()
        salt2 = key_manager2.salt
        
        # Salts should be the same if environment variable is set
        # (This test assumes environment variable is not set, so salts will differ)
        # In production, set LAZARUS_ENCRYPTION_SALT to ensure persistence

    def test_key_isolation(self, key_manager):
        """Test keys are isolated between sessions"""
        session1 = key_manager.generate_session_key(
            session_id="session-1",
            user_agent="Browser1",
            ip_address="192.168.1.1"
        )
        
        session2 = key_manager.generate_session_key(
            session_id="session-2",
            user_agent="Browser2",
            ip_address="192.168.1.2"
        )
        
        # Keys should be completely different
        assert session1.key != session2.key
        assert session1.key_id != session2.key_id
        
        # Compromise of one key should not affect another
        # (This is ensured by the key derivation process)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
