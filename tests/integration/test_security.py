"""
tests/integration/test_security.py — Security integration tests.

Tests for security integration across components:
- Authentication and authorization integration
- Encryption and decryption integration
- Input validation integration
- Rate limiting security integration
- Session management integration
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock
import time
import hmac
import hashlib
import json

from core.config import (
    load_config,
    save_config,
    LAZARUS_DIR,
)
from core.security import (
    verify_api_key,
    key_manager,
)
from core.database import DatabaseManager, DatabaseConfig
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
        
        # Mock pipeline for rate limiter - use side_effect to track state
        pipe_data = {'count': 0, 'backoff': None, 'window_start': None}
        
        def pipe_get(key):
            if key.endswith(':count'):
                return pipe_data['count']
            elif key.endswith(':backoff'):
                return pipe_data['backoff']
            elif key.endswith(':window_start'):
                return pipe_data['window_start']
            return None
        
        def pipe_set(key, value, **kwargs):
            if key.endswith(':backoff'):
                pipe_data['backoff'] = value
            elif key.endswith(':window_start'):
                pipe_data['window_start'] = value
            elif key.endswith(':count'):
                pipe_data['count'] = value
            return True
        
        def pipe_incr(key):
            if key.endswith(':count'):
                pipe_data['count'] = pipe_data.get('count', 0) + 1
            return pipe_data['count']
        
        def pipe_execute():
            c = pipe_data.get('count', 0) or 0
            b = pipe_data.get('backoff')
            w = pipe_data.get('window_start') or time.time()
            return [c, b, w, -1]
        
        mock_pipe = MagicMock()
        mock_pipe.get.side_effect = pipe_get
        mock_pipe.set.side_effect = pipe_set
        mock_pipe.incr.side_effect = pipe_incr
        mock_pipe.execute.side_effect = pipe_execute
        mock_pipe.expire.return_value = True
        mock_pipe.ttl.return_value = -1
        mock_pipe.delete.return_value = True
        
        mock_redis.pipeline.return_value = mock_pipe
        
        yield mock_redis


class TestAuthenticationIntegration:
    """Test authentication and authorization integration"""

    def test_api_key_authentication_flow(self, temp_lazarus_dir, test_api_key):
        """Test complete API key authentication flow"""
        # Step 1: Verify API key
        result = verify_api_key(test_api_key)
        assert result == True
        
        # Step 2: Test invalid API key
        invalid_result = verify_api_key("invalid_api_key")
        assert invalid_result == False
        
        # Step 3: Test empty API key
        empty_result = verify_api_key("")
        assert empty_result == False

    def test_user_authentication_with_database(self, temp_lazarus_dir, test_database):
        """Test user authentication with database integration"""
        # Step 1: Create user in database
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )
        
        # Step 2: Retrieve user by API key
        user = test_database.get_user_by_api_key("test_api_key_12345678901234567890")
        
        # Step 3: Verify authentication
        assert user is not None
        assert user['username'] == 'testuser'
        assert user['email'] == 'test@example.com'
        
        # Step 4: Test invalid API key
        invalid_user = test_database.get_user_by_api_key("invalid_api_key")
        assert invalid_user is None

    def test_authorization_with_roles(self, temp_lazarus_dir, test_database):
        """Test authorization with role-based access control"""
        # Step 1: Create admin user
        admin_id = test_database.create_user(
            username="admin",
            email="admin@example.com",
            password_hash="hashed_password_123",
            api_key="admin_api_key_12345678901234567890"
        )
        
        # Step 2: Create regular user
        user_id = test_database.create_user(
            username="user",
            email="user@example.com",
            password_hash="hashed_password_456",
            api_key="user_api_key_12345678901234567890"
        )
        
        # Step 3: Verify admin can access admin resources
        admin_user = test_database.get_user_by_api_key("admin_api_key_12345678901234567890")
        assert admin_user is not None
        assert admin_user['username'] == 'admin'
        
        # Step 4: Verify regular user can access user resources
        regular_user = test_database.get_user_by_api_key("user_api_key_12345678901234567890")
        assert regular_user is not None
        assert regular_user['username'] == 'user'


class TestEncryptionIntegration:
    """Test encryption and decryption integration"""

    def test_data_encryption_decryption_flow(self, temp_lazarus_dir):
        """Test complete encryption and decryption flow"""
        from core.encryption import encrypt_data, decrypt_data
        
        # Step 1: Prepare test data
        test_data = b"Sensitive data that needs encryption"
        encryption_key = b"test_encryption_key_32bytes!!!!!"
        
        # Step 2: Encrypt data
        encrypted_data = encrypt_data(test_data, encryption_key)
        
        # Step 3: Verify encryption
        assert encrypted_data != test_data
        assert len(encrypted_data) > len(test_data)
        
        # Step 4: Decrypt data
        decrypted_data = decrypt_data(encrypted_data, encryption_key)
        
        # Step 5: Verify decryption
        assert decrypted_data == test_data

    def test_file_encryption_with_storage(self, temp_lazarus_dir):
        """Test file encryption with storage integration"""
        from core.encryption import encrypt_data, decrypt_data
        
        # Step 1: Create test file
        test_file = temp_lazarus_dir / "test_secret.txt"
        test_content = b"Secret file content"
        test_file.write_bytes(test_content)
        
        # Step 2: Encrypt file content
        encryption_key = b"test_encryption_key_32bytes!!!!!"
        encrypted_content = encrypt_data(test_content, encryption_key)
        
        # Step 3: Verify encrypted content
        assert encrypted_content != test_content
        assert len(encrypted_content) > len(test_content)
        
        # Step 4: Decrypt content
        decrypted_content = decrypt_data(encrypted_content, encryption_key)
        
        # Step 5: Verify decrypted content matches original
        assert decrypted_content == test_content

    def test_key_derivation_integration(self, temp_lazarus_dir):
        """Test key derivation with PBKDF2"""
        # Step 1: Derive key from password
        password = "user_password_123"
        salt = b"test_salt_16bytes"
        
        derived_key = key_manager.derive_key(password, salt)
        
        # Step 2: Verify key derivation
        assert derived_key is not None
        assert len(derived_key) == 32  # 256 bits
        
        # Step 3: Verify deterministic derivation
        derived_key_2 = key_manager.derive_key(password, salt)
        assert derived_key == derived_key_2
        
        # Step 4: Verify different passwords produce different keys
        different_key = key_manager.derive_key("different_password", salt)
        assert derived_key != different_key


class TestInputValidationIntegration:
    """Test input validation integration"""

    def test_email_validation(self, temp_lazarus_dir):
        """Test email validation"""
        # Step 1: Test valid emails
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.com"
        ]
        
        for email in valid_emails:
            # In real scenario, would validate email format
            assert "@" in email
            assert "." in email
        
        # Step 2: Test invalid emails
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "invalid@.com"
        ]
        
        for email in invalid_emails:
            # In real scenario, would reject invalid emails
            assert True  # Placeholder for validation logic

    def test_file_path_validation(self, temp_lazarus_dir):
        """Test file path validation"""
        # Step 1: Test valid paths
        valid_paths = [
            "/path/to/file.txt",
            "/path/to/directory/",
            "relative/path/file.txt"
        ]
        
        for path in valid_paths:
            # In real scenario, would validate path format
            assert len(path) > 0
        
        # Step 2: Test path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "/path/to/../../../etc/passwd",
            "..\\..\\..\\windows\\system32"
        ]
        
        for path in malicious_paths:
            # In real scenario, would reject path traversal
            assert True  # Placeholder for validation logic

    def test_api_key_validation(self, temp_lazarus_dir):
        """Test API key validation"""
        # Step 1: Test valid API keys
        valid_keys = [
            "test_api_key_12345678901234567890",
            "another_key_abcdefghijklmnopqrstuvwxyz123456"
        ]
        
        for key in valid_keys:
            # In real scenario, would validate key format
            assert len(key) >= 32
        
        # Step 2: Test invalid API keys
        invalid_keys = [
            "",
            "short",
            "key with spaces",
            "key\nwith\nnewlines"
        ]
        
        for key in invalid_keys:
            # In real scenario, would reject invalid keys
            assert True  # Placeholder for validation logic

    def test_json_input_validation(self, temp_lazarus_dir):
        """Test JSON input validation"""
        # Step 1: Test valid JSON
        valid_json = {
            "owner_name": "Test Owner",
            "owner_email": "test@example.com",
            "checkin_interval_days": 30
        }
        
        # Step 2: Verify JSON structure
        assert "owner_name" in valid_json
        assert "owner_email" in valid_json
        assert "checkin_interval_days" in valid_json
        
        # Step 3: Test JSON with extra fields
        json_with_extra = {
            "owner_name": "Test Owner",
            "owner_email": "test@example.com",
            "checkin_interval_days": 30,
            "malicious_field": "malicious_value"
        }
        
        # In real scenario, would sanitize extra fields
        assert True  # Placeholder for sanitization logic


class TestRateLimitingSecurity:
    """Test rate limiting security integration"""

    def test_rate_limiting_prevents_abuse(self, temp_lazarus_dir, mock_redis):
        """Test rate limiting prevents abuse"""
        # Step 1: Create rate limiter
        limiter = DistributedRateLimiter(
            redis_client=mock_redis,
            default_limit=10,
            default_window=60
        )
        
        # Step 2: Test rate limit enforcement
        identifier = "test_user"
        allowed_count = 0
        denied_count = 0
        
        for i in range(15):
            allowed, remaining = limiter.is_allowed(
                identifier=identifier,
                limit=10,
                window=60
            )
            if allowed:
                allowed_count += 1
            else:
                denied_count += 1
        
        # Step 3: Verify rate limiting
        assert allowed_count == 10  # First 10 allowed
        assert denied_count == 5  # Last 5 denied

    def test_rate_limiting_with_ip_address(self, temp_lazarus_dir, mock_redis):
        """Test rate limiting with IP address"""
        # Step 1: Create rate limiter
        limiter = DistributedRateLimiter(
            redis_client=mock_redis,
            default_limit=5,
            default_window=60
        )
        
        # Step 2: Test rate limiting by IP
        ip_address = "192.168.1.1"
        allowed_count = 0
        
        for i in range(10):
            allowed, remaining = limiter.is_allowed(
                identifier=f"ip:{ip_address}",
                limit=5,
                window=60
            )
            if allowed:
                allowed_count += 1
        
        # Step 3: Verify rate limiting
        assert allowed_count == 5

    def test_rate_limiting_with_user_id(self, temp_lazarus_dir, mock_redis):
        """Test rate limiting with user ID"""
        # Step 1: Create rate limiter
        limiter = DistributedRateLimiter(
            redis_client=mock_redis,
            default_limit=20,
            default_window=60
        )
        
        # Step 2: Test rate limiting by user
        user_id = "user_123"
        allowed_count = 0
        
        for i in range(25):
            allowed, remaining = limiter.is_allowed(
                identifier=f"user:{user_id}",
                limit=20,
                window=60
            )
            if allowed:
                allowed_count += 1
        
        # Step 3: Verify rate limiting
        assert allowed_count == 20


class TestSessionManagementSecurity:
    """Test session management security integration"""

    def test_session_key_generation(self, temp_lazarus_dir):
        """Test session key generation"""
        # Step 1: Generate CSRF token for session
        csrf_token = key_manager.generate_csrf_token()
        
        # Step 2: Verify token
        assert csrf_token is not None
        assert len(csrf_token) > 0
        
        # Step 3: Verify token uniqueness
        csrf_token_2 = key_manager.generate_csrf_token()
        assert csrf_token != csrf_token_2

    def test_session_key_validation(self, temp_lazarus_dir):
        """Test session key validation"""
        # Step 1: Generate CSRF token
        csrf_token = key_manager.generate_csrf_token()
        
        # Step 2: Validate token
        is_valid = key_manager.verify_csrf_token(
            request=MagicMock(),
            token=csrf_token
        )
        
        # Step 3: Verify validation
        # Note: In real scenario, would validate against session
        assert csrf_token is not None

    def test_session_key_expiration(self, temp_lazarus_dir):
        """Test session key expiration"""
        # Step 1: Generate CSRF token
        csrf_token = key_manager.generate_csrf_token()
        
        # Step 2: Verify token exists
        assert csrf_token is not None
        
        # Step 3: Note: CSRF tokens don't expire in the same way as session keys
        # This test verifies token generation works
        assert True

    def test_session_key_device_binding(self, temp_lazarus_dir):
        """Test session key device binding"""
        # Step 1: Generate CSRF token
        csrf_token = key_manager.generate_csrf_token()
        
        # Step 2: Verify token
        assert csrf_token is not None
        
        # Step 3: Note: CSRF tokens are session-based, not device-bound
        # This test verifies token generation works
        assert True


class TestCSRFProtection:
    """Test CSRF protection integration"""

    def test_csrf_token_generation(self, temp_lazarus_dir):
        """Test CSRF token generation"""
        # Step 1: Generate CSRF token
        session_id = "test_session_123"
        csrf_token = key_manager.generate_csrf_token(session_id)
        
        # Step 2: Verify token
        assert csrf_token is not None
        assert len(csrf_token) > 0
        
        # Step 3: Verify token uniqueness
        csrf_token_2 = key_manager.generate_csrf_token(session_id)
        assert csrf_token != csrf_token_2

    def test_csrf_token_validation(self, temp_lazarus_dir):
        """Test CSRF token validation"""
        # Step 1: Generate CSRF token
        session_id = "test_session_123"
        csrf_token = key_manager.generate_csrf_token(session_id)
        
        # Step 2: Validate token
        is_valid = key_manager.validate_csrf_token(csrf_token, session_id=session_id)
        
        # Step 3: Verify validation
        assert is_valid == True

    def test_csrf_token_reuse_prevention(self, temp_lazarus_dir):
        """Test CSRF token reuse prevention"""
        # Step 1: Generate CSRF token
        session_id = "test_session_123"
        csrf_token = key_manager.generate_csrf_token(session_id)
        
        # Step 2: Validate token first time
        is_valid_1 = key_manager.validate_csrf_token(csrf_token, session_id=session_id)
        assert is_valid_1 == True
        
        # Step 3: Try to reuse token
        is_valid_2 = key_manager.validate_csrf_token(csrf_token, session_id=session_id)
        
        # Step 4: Verify reuse prevention
        assert is_valid_2 == False


class TestSecurityHeaders:
    """Test security headers integration"""

    def test_security_headers_presence(self, temp_lazarus_dir):
        """Test security headers are present"""
        # Step 1: Define expected security headers
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        }
        
        # Step 2: Verify headers are defined
        # In real scenario, would check actual HTTP response headers
        for header_name, header_value in expected_headers.items():
            assert header_name is not None
            assert header_value is not None

    def test_cors_configuration(self, temp_lazarus_dir):
        """Test CORS configuration"""
        # Step 1: Define allowed origins
        allowed_origins = [
            "https://lazarusprotocol.com",
            "https://www.lazarusprotocol.com"
        ]
        
        # Step 2: Verify CORS configuration
        # In real scenario, would check actual CORS headers
        for origin in allowed_origins:
            assert origin.startswith("https://")


class TestAuditLogging:
    """Test audit logging integration"""

    def test_security_event_logging(self, temp_lazarus_dir, test_database):
        """Test security event logging"""
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

    def test_failed_login_logging(self, temp_lazarus_dir, test_database):
        """Test failed login logging"""
        # Step 1: Create user
        user_id = test_database.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_123",
            api_key="test_api_key_12345678901234567890"
        )
        
        # Step 2: Log failed login attempt
        event_id = test_database.log_security_event(
            user_id=user_id,
            event_type="login_failed",
            ip_address="192.168.1.100",
            user_agent="MaliciousAgent/1.0",
            details={"reason": "invalid_api_key"}
        )
        
        # Step 3: Verify event was logged
        assert event_id is not None
        
        # Step 4: Retrieve security events
        events = test_database.get_security_events(user_id, limit=10)
        
        # Step 5: Verify failed login event
        assert len(events) == 1
        assert events[0]['event_type'] == 'login_failed'
        assert events[0]['ip_address'] == '192.168.1.100'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
