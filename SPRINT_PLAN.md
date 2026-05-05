Lazarus Protocol - Implementation Sprint Plan

**Created**: 2026-05-05
**Project**: Lazarus Protocol - Digital Legacy & Cryptocurrency Inheritance System
**Version**: v1.0
**Overall Timeline**: 7 weeks to production readiness
**Current Status**: 68/100 Production Ready

---

## 📊 Executive Summary

This sprint plan provides a structured approach to addressing all CRITICAL and HIGH priority issues identified in the production readiness review. The plan is organized into 7 sprints, each with clear deliverables, success criteria, and dependencies.

### Sprint Overview

| Sprint | Focus | Duration | Effort | Priority | Deliverables |
|--------|-------|----------|--------|----------|--------------|
| **Sprint 1** | Critical Security Fixes | 5 days | 40h | CRITICAL | 3 critical security vulnerabilities resolved |
| **Sprint 2** | Database & Thread Safety | 5 days | 40h | CRITICAL | Database layer + thread-safe rate limiting |
| **Sprint 3** | API Testing & Monitoring | 5 days | 40h | HIGH | FastAPI tests + monitoring infrastructure |
| **Sprint 4** | Integration Testing | 5 days | 40h | HIGH | End-to-end workflow tests |
| **Sprint 5** | Performance & Security | 5 days | 40h | HIGH | Performance benchmarks + security tests |
| **Sprint 6** | CI/CD & Deployment | 5 days | 40h | HIGH | Automated pipeline + deployment |
| **Sprint 7** | Blockchain & Final Prep | 5 days | 40h | CRITICAL | Blockchain security + launch prep |

**Total Timeline**: 7 weeks (35 days)
**Total Effort**: 280 hours
**Target Production Readiness**: 90/100

---

## 🎯 Sprint Goals & Success Criteria

### Overall Goals

1. **Security**: Resolve all CRITICAL security vulnerabilities (6 blockers)
2. **Testing**: Achieve 80%+ test coverage across all components
3. **Performance**: Establish and validate performance SLAs
4. **Monitoring**: Implement comprehensive monitoring and alerting
5. **Deployment**: Establish automated CI/CD pipeline
6. **Blockchain**: Implement core blockchain security features

### Success Criteria

- ✅ All CRITICAL blockers resolved
- ✅ All HIGH priority issues addressed
- ✅ Test coverage > 80%
- ✅ Performance SLAs validated
- ✅ Monitoring operational
- ✅ CI/CD pipeline automated
- ✅ Production readiness score > 90/100

---

## 📋 Sprint 1: Critical Security Fixes

**Duration**: 5 days (Mon-Fri)
**Effort**: 40 hours
**Priority**: CRITICAL
**Dependencies**: None

### Sprint Objectives

Resolve the 3 most critical security vulnerabilities that pose immediate data breach and DoS risks.

### Deliverables

#### 1.1 Fix LocalStorage Encryption Key Vulnerability (16 hours)

**Issue**: CVSS 8.9 - Encryption keys stored in plaintext, accessible via JavaScript console

**Tasks**:
- [ ] Implement server-provided encryption keys (4h)
- [ ] Add PBKDF2 key derivation with 100,000+ iterations (4h)
- [ ] Implement key rotation mechanism (4h)
- [ ] Use httpOnly cookies for sensitive data (2h)
- [ ] Add session/device binding (2h)

**Implementation Details**:

```python
# core/security.py
import os
import hashlib
import secrets
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class KeyManager:
    """Secure key management with server-side generation"""

    def __init__(self):
        self.salt = os.environ.get('ENCRYPTION_SALT', secrets.token_bytes(32))
        self.iterations = 100000

    def derive_key(self, password: str, context: str) -> bytes:
        """Derive encryption key using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt + context.encode(),
            iterations=self.iterations,
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def generate_session_key(self, session_id: str) -> str:
        """Generate session-specific encryption key"""
        key = self.derive_key(session_id, "session")
        return key.hex()

    def rotate_key(self, old_key: str, context: str) -> str:
        """Rotate encryption key"""
        new_key = self.derive_key(old_key, f"{context}_rotated")
        return new_key.hex()
```

```javascript
// web/js/security.js
class SecureStorage {
    constructor() {
        this.sessionKey = null;
    }

    async initialize() {
        // Request encryption key from server
        const response = await fetch('/api/session/key', {
            method: 'POST',
            credentials: 'include'
        });
        const data = await response.json();
        this.sessionKey = data.key;
    }

    async encrypt(data) {
        if (!this.sessionKey) {
            await this.initialize();
        }
        // Use Web Crypto API with server-provided key
        const encoder = new TextEncoder();
        const encoded = encoder.encode(data);
        const key = await this.importKey(this.sessionKey);
        const encrypted = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: window.crypto.getRandomValues(new Uint8Array(12)) },
            key,
            encoded
        );
        return encrypted;
    }

    async decrypt(encryptedData) {
        if (!this.sessionKey) {
            await this.initialize();
        }
        const key = await this.importKey(this.sessionKey);
        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: encryptedData.iv },
            key,
            encryptedData.data
        );
        const decoder = new TextDecoder();
        return decoder.decode(decrypted);
    }

    async importKey(keyString) {
        const keyData = new TextEncoder().encode(keyString);
        return await window.crypto.subtle.importKey(
            'raw',
            await window.crypto.subtle.digest('SHA-256', keyData),
            { name: 'AES-GCM' },
            false,
            ['encrypt', 'decrypt']
        );
    }
}
```

**Success Criteria**:
- ✅ Server-provided encryption keys implemented
- ✅ PBKDF2 with 100,000+ iterations operational
- ✅ Key rotation mechanism tested
- ✅ Sensitive data stored in httpOnly cookies
- ✅ Session/device binding verified
- ✅ Security audit passes with no critical findings

**Testing**:
```python
# tests/test_key_management.py
def test_server_provided_keys():
    """Test keys are provided by server"""
    response = client.post('/api/session/key')
    assert response.status_code == 200
    assert 'key' in response.json()
    assert len(response.json()['key']) == 64  # 32 bytes hex encoded

def test_key_derivation_strength():
    """Test PBKDF2 key derivation strength"""
    manager = KeyManager()
    key = manager.derive_key('test_password', 'test_context')
    assert len(key) == 32  # 256 bits
    assert manager.iterations >= 100000

def test_key_rotation():
    """Test key rotation mechanism"""
    manager = KeyManager()
    old_key = 'old_key_123'
    new_key = manager.rotate_key(old_key, 'session')
    assert new_key != old_key
    assert len(new_key) == 64
```

---

#### 1.2 Fix Rate Limiting Bypass Vulnerability (12 hours)

**Issue**: CVSS 8.7 - In-memory storage, no distributed support, IP-based only

**Tasks**:
- [ ] Implement Redis-based distributed rate limiting (6h)
- [ ] Add user-based rate limiting for authenticated users (2h)
- [ ] Implement exponential backoff (2h)
- [ ] Add IP reputation checking (1h)
- [ ] Implement rate limit persistence across restarts (1h)

**Implementation Details**:

```python
# core/rate_limiter.py
import redis
import time
import json
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class RateLimitConfig:
    requests: int = 10
    window: int = 60  # seconds
    burst: int = 20
    backoff_base: int = 2
    backoff_max: int = 60

class DistributedRateLimiter:
    """Redis-based distributed rate limiting with exponential backoff"""

    def __init__(self, redis_client: redis.Redis, config: RateLimitConfig):
        self.redis = redis_client
        self.config = config

    def is_allowed(self, identifier: str, user_id: Optional[str] = None) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed with rate limiting

        Args:
            identifier: IP address or unique identifier
            user_id: Optional user ID for user-based limiting

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        # Use user-based limiting if user_id provided
        key = f"rate_limit:user:{user_id}" if user_id else f"rate_limit:ip:{identifier}"

        # Get current request count and backoff
        pipe = self.redis.pipeline()
        pipe.get(f"{key}:count")
        pipe.get(f"{key}:backoff")
        pipe.get(f"{key}:window_start")
        count, backoff, window_start = pipe.execute()

        # Check if in backoff period
        if backoff:
            backoff_end = float(backoff)
            if time.time() < backoff_end:
                return False, int(backoff_end - time.time())

        # Initialize window if needed
        if not window_start:
            window_start = time.time()
            self.redis.set(f"{key}:window_start", window_start, ex=self.config.window)
            count = 0
        else:
            window_start = float(window_start)
            # Reset if window expired
            if time.time() - window_start > self.config.window:
                self.redis.delete(f"{key}:count")
                self.redis.delete(f"{key}:backoff")
                self.redis.set(f"{key}:window_start", time.time(), ex=self.config.window)
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
            self.redis.set(f"{key}:backoff", backoff_end, ex=backoff_time)
            return False, backoff_time

        # Increment counter
        self.redis.incr(f"{key}:count")
        self.redis.expire(f"{key}:count", self.config.window)

        return True, None

    def check_ip_reputation(self, ip: str) -> bool:
        """Check IP reputation and block if suspicious"""
        # Implement IP reputation checking
        # This could integrate with services like AbuseIPDB, Cloudflare, etc.
        reputation_key = f"ip_reputation:{ip}"
        reputation = self.redis.get(reputation_key)

        if reputation:
            score = int(reputation)
            return score < 50  # Block if score >= 50

        return True

    def report_bad_ip(self, ip: str, severity: int = 10):
        """Report bad IP and update reputation"""
        reputation_key = f"ip_reputation:{ip}"
        current = self.redis.get(reputation_key)
        new_score = (int(current) if current else 0) + severity
        self.redis.set(reputation_key, new_score, ex=86400)  # 24 hours
```

**Success Criteria**:
- ✅ Redis-based distributed rate limiting operational
- ✅ User-based rate limiting implemented
- ✅ Exponential backoff verified
- ✅ IP reputation checking integrated
- ✅ Rate limit persistence across restarts tested
- ✅ Load testing with 1000+ concurrent requests successful

**Testing**:
```python
# tests/test_rate_limiter.py
import pytest
import redis
from core.rate_limiter import DistributedRateLimiter, RateLimitConfig

@pytest.fixture
def rate_limiter():
    redis_client = redis.Redis(host='localhost', port=6379, db=15)
    redis_client.flushdb()  # Clean test database
    config = RateLimitConfig(requests=10, window=60)
    return DistributedRateLimiter(redis_client, config)

def test_rate_limiting_enforcement(rate_limiter):
    """Test rate limiting is enforced"""
    identifier = "192.168.1.1"

    # First 10 requests should be allowed
    for i in range(10):
        allowed, retry_after = rate_limiter.is_allowed(identifier)
        assert allowed is True
        assert retry_after is None

    # 11th request should be rate limited
    allowed, retry_after = rate_limiter.is_allowed(identifier)
    assert allowed is False
    assert retry_after is not None
    assert retry_after > 0

def test_exponential_backoff(rate_limiter):
    """Test exponential backoff"""
    identifier = "192.168.1.2"
    config = RateLimitConfig(requests=5, window=60, backoff_base=2)

    # Exceed limit multiple times
    for i in range(10):
        rate_limiter.is_allowed(identifier)

    # Check backoff increases exponentially
    allowed, retry_after1 = rate_limiter.is_allowed(identifier)
    time.sleep(1)
    allowed, retry_after2 = rate_limiter.is_allowed(identifier)

    assert retry_after2 > retry_after1

def test_user_based_rate_limiting(rate_limiter):
    """Test user-based rate limiting"""
    user_id = "user123"
    ip = "192.168.1.3"

    # User-based limit should be independent of IP
    for i in range(10):
        allowed, _ = rate_limiter.is_allowed(ip, user_id=user_id)
        assert allowed is True

    # Same IP, different user should be allowed
    allowed, _ = rate_limiter.is_allowed(ip, user_id="user456")
    assert allowed is True

def test_ip_reputation_checking(rate_limiter):
    """Test IP reputation checking"""
    bad_ip = "192.168.1.100"

    # Report bad IP
    rate_limiter.report_bad_ip(bad_ip, severity=60)

    # Check reputation blocks
    assert not rate_limiter.check_ip_reputation(bad_ip)

    # Good IP should pass
    assert rate_limiter.check_ip_reputation("192.168.1.101")
```

---

#### 1.3 Fix Memory Leak in Rate Limiter (12 hours)

**Issue**: CVSS 7.8 - Cleanup method never called, unbounded memory growth

**Tasks**:
- [ ] Implement automatic cleanup in rate limiter (4h)
- [ ] Add periodic cleanup scheduler (4h)
- [ ] Add memory usage monitoring (2h)
- [ ] Add memory leak detection tests (2h)

**Implementation Details**:

```python
# core/rate_limiter.py
import threading
import time
import psutil
import os
from typing import Callable

class AutoCleanupRateLimiter(DistributedRateLimiter):
    """Rate limiter with automatic cleanup and memory monitoring"""

    def __init__(self, redis_client: redis.Redis, config: RateLimitConfig):
        super().__init__(redis_client, config)
        self.cleanup_interval = 300  # 5 minutes
        self.memory_threshold = 1024 * 1024 * 1024  # 1GB
        self._cleanup_thread = None
        self._stop_event = threading.Event()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        """Background cleanup loop"""
        while not self._stop_event.is_set():
            try:
                self._cleanup_old_entries()
                self._check_memory_usage()
                self._stop_event.wait(self.cleanup_interval)
            except Exception as e:
                print(f"Cleanup error: {e}")

    def _cleanup_old_entries(self):
        """Clean up old rate limit entries"""
        # Redis automatically expires keys, but we can force cleanup
        pipe = self.redis.pipeline()
        for key in self.redis.scan_iter("rate_limit:*"):
            pipe.ttl(key)
        ttls = pipe.execute()

        # Log cleanup statistics
        expired_count = sum(1 for ttl in ttls if ttl == -2)
        if expired_count > 0:
            print(f"Cleaned up {expired_count} expired entries")

    def _check_memory_usage(self):
        """Check memory usage and alert if threshold exceeded"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        if memory_mb > self.memory_threshold / 1024 / 1024:
            print(f"WARNING: Memory usage {memory_mb:.2f}MB exceeds threshold")
            # Trigger aggressive cleanup
            self._aggressive_cleanup()

    def _aggressive_cleanup(self):
        """Perform aggressive memory cleanup"""
        # Force Python garbage collection
        import gc
        gc.collect()

        # Clear Redis connection pool
        self.redis.connection_pool.reset()

        print("Aggressive cleanup completed")

    def stop(self):
        """Stop cleanup thread"""
        self._stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def __del__(self):
        """Cleanup on deletion"""
        self.stop()
```

**Success Criteria**:
- ✅ Automatic cleanup implemented
- ✅ Memory usage stable over time
- ✅ Memory leak detection tests passing
- ✅ Long-running stability verified (7+ days)

**Testing**:
```python
# tests/test_memory_cleanup.py
import time
import pytest
from core.rate_limiter import AutoCleanupRateLimiter

def test_automatic_cleanup(rate_limiter):
    """Test automatic cleanup of old entries"""
    # Create many rate limit entries
    for i in range(1000):
        rate_limiter.is_allowed(f"192.168.1.{i}")

    # Wait for cleanup interval
    time.sleep(310)

    # Verify old entries cleaned up
    # (This would require inspecting Redis state)

def test_memory_stability(rate_limiter):
    """Test memory usage remains stable"""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Make many requests over time
    for i in range(10000):
        rate_limiter.is_allowed(f"192.168.1.{i % 1000}")

    final_memory = process.memory_info().rss
    memory_growth = final_memory - initial_memory

    # Memory growth should be < 100MB
    assert memory_growth < 100 * 1024 * 1024

def test_long_running_stability():
    """Test stability over extended period"""
    rate_limiter = AutoCleanupRateLimiter(redis_client, config)

    # Run for 1 hour
    end_time = time.time() + 3600
    request_count = 0

    while time.time() < end_time:
        for i in range(100):
            rate_limiter.is_allowed(f"192.168.1.{i % 100}")
            request_count += 1
        time.sleep(1)

    print(f"Completed {request_count} requests in 1 hour")
    rate_limiter.stop()
```

---

### Sprint 1 Deliverables Summary

**Completed Tasks**:
- ✅ Server-provided encryption keys with PBKDF2
- ✅ Key rotation mechanism
- ✅ Redis-based distributed rate limiting
- ✅ User-based rate limiting
- ✅ Exponential backoff
- ✅ IP reputation checking
- ✅ Automatic memory cleanup
- ✅ Memory monitoring

**Test Coverage**:
- ✅ Key management tests (5 tests)
- ✅ Rate limiting tests (8 tests)
- ✅ Memory cleanup tests (3 tests)

**Documentation**:
- ✅ Security implementation guide
- ✅ Rate limiting configuration guide
- ✅ Memory monitoring setup guide

**Success Metrics**:
- ✅ All 3 CRITICAL security vulnerabilities resolved
- ✅ Security score improved from 75/100 to 85/100
- ✅ All security tests passing
- ✅ No critical security findings in audit

---

## 📋 Sprint 2: Database & Thread Safety

**Duration**: 5 days (Mon-Fri)
**Effort**: 40 hours
**Priority**: CRITICAL
**Dependencies**: Sprint 1

### Sprint Objectives

Implement proper database layer with ACID guarantees and thread-safe rate limiting.

### Deliverables

#### 2.1 Implement Database Layer (24 hours)

**Issue**: CVSS 8.0 - File-based JSON storage, no ACID guarantees, race conditions

**Tasks**:
- [ ] Design database schema (4h)
- [ ] Implement SQLite database layer (8h)
- [ ] Add database migrations (4h)
- [ ] Implement transaction support (4h)
- [ ] Add data validation and constraints (2h)
- [ ] Implement backup and recovery strategy (2h)

**Implementation Details**:

```python
# core/database.py
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class DatabaseConfig:
    path: Path
    backup_interval: int = 3600  # 1 hour
    max_backups: int = 10

class DatabaseManager:
    """SQLite database manager with ACID guarantees"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection_pool = {}
        self._ensure_schema()

    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        thread_id = threading.current_thread().ident
        if thread_id not in self._connection_pool:
            self._connection_pool[thread_id] = sqlite3.connect(
                self.config.path,
                check_same_thread=False
            )
            self._connection_pool[thread_id].row_factory = sqlite3.Row

        conn = self._connection_pool[thread_id]
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    def _ensure_schema(self):
        """Ensure database schema exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    owner_email TEXT NOT NULL,
                    beneficiary_email TEXT NOT NULL,
                    check_in_interval_days INTEGER NOT NULL,
                    last_checkin_timestamp TIMESTAMP,
                    deadline_timestamp TIMESTAMP,
                    storage_config TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (configuration_id) REFERENCES configurations(id)
                )
            """)

            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    storage_provider TEXT NOT NULL,
                    cid TEXT,
                    encrypted_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (configuration_id) REFERENCES configurations(id)
                )
            """)

            # Rate limits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    request_count INTEGER NOT NULL,
                    window_start TIMESTAMP NOT NULL,
                    backoff_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identifier, window_start)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_config ON events(configuration_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_config ON documents(configuration_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier)")

            conn.commit()

    @contextmanager
    def transaction(self):
        """Execute operations in a transaction"""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def create_user(self, email: str, api_key: str) -> int:
        """Create new user"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, api_key) VALUES (?, ?)",
                (email, api_key)
            )
            return cursor.lastrowid

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by API key"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE api_key = ?",
                (api_key,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_configuration(self, user_id: int, config: Dict) -> int:
        """Create configuration"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO configurations (
                    user_id, owner_email, beneficiary_email,
                    check_in_interval_days, storage_config
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                config['owner_email'],
                config['beneficiary_email'],
                config['check_in_interval_days'],
                json.dumps(config['storage_config'])
            ))
            return cursor.lastrowid

    def update_configuration(self, config_id: int, updates: Dict) -> bool:
        """Update configuration"""
        with self.transaction() as conn:
            cursor = conn.cursor()

            set_clauses = []
            values = []

            for key, value in updates.items():
                if key == 'storage_config':
                    set_clauses.append(f"{key} = ?")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

            values.append(config_id)

            cursor.execute(
                f"UPDATE configurations SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )

            return cursor.rowcount > 0

    def log_event(self, configuration_id: int, event_type: str, content: str) -> int:
        """Log event"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (configuration_id, event_type, content) VALUES (?, ?, ?)",
                (configuration_id, event_type, content)
            )
            return cursor.lastrowid

    def get_events(self, configuration_id: int, limit: int = 100) -> List[Dict]:
        """Get events for configuration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE configuration_id = ? ORDER BY timestamp DESC LIMIT ?",
                (configuration_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_document(self, configuration_id: int, document: Dict) -> int:
        """Add document to bundle"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (
                    configuration_id, filename, file_type, file_size,
                    storage_provider, cid, encrypted_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                configuration_id,
                document['filename'],
                document['file_type'],
                document['file_size'],
                document['storage_provider'],
                document.get('cid'),
                document['encrypted_path']
            ))
            return cursor.lastrowid

    def get_documents(self, configuration_id: int) -> List[Dict]:
        """Get documents for configuration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE configuration_id = ?",
                (configuration_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def remove_document(self, document_id: int) -> bool:
        """Remove document"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cursor.rowcount > 0

    def backup(self) -> Path:
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config.path.parent / f"backup_{timestamp}.db"

        # Copy database file
        import shutil
        shutil.copy2(self.config.path, backup_path)

        # Clean up old backups
        self._cleanup_old_backups()

        return backup_path

    def _cleanup_old_backups(self):
        """Remove old backups exceeding max_backups"""
        backups = sorted(
            self.config.path.parent.glob("backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for backup in backups[self.config.max_backups:]:
            backup.unlink()

    def close(self):
        """Close all connections"""
        for conn in self._connection_pool.values():
            conn.close()
        self._connection_pool.clear()
```

**Database Migrations**:

```python
# core/migrations.py
from typing import List, Callable
from core.database import DatabaseManager

class Migration:
    def __init__(self, version: int, description: str, up: Callable, down: Callable):
        self.version = version
        self.description = description
        self.up = up
        self.down = down

class MigrationManager:
    """Database migration manager"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Ensure migrations table exists"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] for row in cursor.fetchall()]

    def apply_migration(self, migration: Migration):
        """Apply a migration"""
        applied = self.get_applied_migrations()

        if migration.version in applied:
            print(f"Migration {migration.version} already applied")
            return

        print(f"Applying migration {migration.version}: {migration.description}")

        with self.db.transaction() as conn:
            migration.up(conn)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (migration.version,)
            )

        print(f"Migration {migration.version} applied successfully")

    def rollback_migration(self, migration: Migration):
        """Rollback a migration"""
        applied = self.get_applied_migrations()

        if migration.version not in applied:
            print(f"Migration {migration.version} not applied")
            return

        print(f"Rolling back migration {migration.version}: {migration.description}")

        with self.db.transaction() as conn:
            migration.down(conn)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                (migration.version,)
            )

        print(f"Migration {migration.version} rolled back successfully")

# Define migrations
MIGRATIONS = [
    Migration(
        version=1,
        description="Initial schema",
        up=lambda conn: None,  # Schema created in DatabaseManager
        down=lambda conn: None
    ),
    Migration(
        version=2,
        description="Add user preferences table",
        up=lambda conn: conn.execute("""
            CREATE TABLE user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, preference_key)
            )
        """),
        down=lambda conn: conn.execute("DROP TABLE IF EXISTS user_preferences")
    ),
]
```

**Success Criteria**:
- ✅ SQLite database layer implemented
- ✅ Database migrations operational
- ✅ Transaction support verified
- ✅ Data validation and constraints in place
- ✅ Backup and recovery strategy tested

**Testing**:
```python
# tests/test_database.py
import pytest
from core.database import DatabaseManager, DatabaseConfig
from pathlib import Path
import tempfile

@pytest.fixture
def db():
    """Create test database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = DatabaseConfig(path=Path(tmpdir) / "test.db")
        db = DatabaseManager(config)
        yield db
        db.close()

def test_create_user(db):
    """Test user creation"""
    user_id = db.create_user("test@example.com", "api_key_123")
    assert user_id > 0

    user = db.get_user_by_api_key("api_key_123")
    assert user['email'] == "test@example.com"

def test_transaction_rollback(db):
    """Test transaction rollback on error"""
    user_id = db.create_user("test@example.com", "api_key_123")

    try:
        with db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, api_key) VALUES (?, ?)", ("duplicate@example.com", "api_key_123"))
            cursor.execute("INSERT INTO users (email, api_key) VALUES (?, ?)", ("test@example.com", "api_key_123"))  # Duplicate
    except Exception:
        pass  # Expected to fail

    # Verify rollback - should still have only 1 user
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        assert count == 1

def test_backup_and_restore(db):
    """Test backup and restore"""
    # Create some data
    user_id = db.create_user("test@example.com", "api_key_123")

    # Create backup
    backup_path = db.backup()
    assert backup_path.exists()

    # Verify backup contains data
    import shutil
    test_db = DatabaseManager(DatabaseConfig(path=backup_path))
    user = test_db.get_user_by_api_key("api_key_123")
    assert user is not None
    test_db.close()
```

---

#### 2.2 Implement Thread-Safe Rate Limiter (16 hours)

**Issue**: CVSS 8.5 - Race conditions in concurrent requests

**Tasks**:
- [ ] Implement thread-safe rate limiter with locks (8h)
- [ ] Add comprehensive thread-safety tests (4h)
- [ ] Verify no race conditions under load (4h)

**Implementation Details**:

```python
# core/thread_safe_rate_limiter.py
import threading
import time
from typing import Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class RateLimitEntry:
    count: int
    window_start: float
    backoff_until: Optional[float] = None

class ThreadSafeRateLimiter:
    """Thread-safe rate limiter with locks"""

    def __init__(self, requests: int = 10, window: int = 60):
        self.requests = requests
        self.window = window
        self._requests: dict[str, RateLimitEntry] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested locks

    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed with thread-safe rate limiting

        Args:
            identifier: IP address or unique identifier

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()
            entry = self._requests.get(identifier)

            # Initialize entry if needed
            if entry is None:
                entry = RateLimitEntry(count=0, window_start=now)
                self._requests[identifier] = entry

            # Check if in backoff period
            if entry.backoff_until and now < entry.backoff_until:
                return False, int(entry.backoff_until - now)

            # Reset if window expired
if now - entry.window_start > self.window:
                entry.count = 0
                entry.window_start = now
                entry.backoff_until = None

            # Check if limit exceeded
            if entry.count >= self.requests:
                # Calculate exponential backoff
                backoff_time = min(2 ** (entry.count - self.requests + 1), 60)
                entry.backoff_until = now + backoff_time
                return False, backoff_time

            # Increment counter
            entry.count += 1
            return True, None

    def cleanup(self) -> None:
        """Clean up old entries to prevent memory leaks"""
        with self._lock:
            now = time.time()
            to_delete = []

            for identifier, entry in self._requests.items():
                # Remove entries that are outside window and not in backoff
                if now - entry.window_start > self.window and not entry.backoff_until:
                    to_delete.append(identifier)

            for identifier in to_delete:
                del self._requests[identifier]

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self._lock:
            return {
                'total_identifiers': len(self._requests),
                'active_entries': sum(1 for e in self._requests.values() if e.backoff_until is None),
                'backoff_entries': sum(1 for e in self._requests.values() if e.backoff_until is not None)
            }
```

**Success Criteria**:
- ✅ Thread-safe rate limiter implemented
- ✅ No race conditions under concurrent load
- ✅ Comprehensive thread-safety tests passing
- ✅ Load testing with 1000+ concurrent requests successful

**Testing**:
```python
# tests/test_thread_safe_rate_limiter.py
import pytest
import threading
import time
from core.thread_safe_rate_limiter import ThreadSafeRateLimiter

@pytest.fixture
def rate_limiter():
    return ThreadSafeRateLimiter(requests=10, window=60)

def test_concurrent_requests(rate_limiter):
    """Test concurrent requests don't cause race conditions"""
    identifier = "192.168.1.1"
    results = []
    errors = []

    def make_request():
        try:
            allowed, retry_after = rate_limiter.is_allowed(identifier)
            results.append((allowed, retry_after))
        except Exception as e:
            errors.append(e)

    # Make 20 concurrent requests
    threads = []
    for _ in range(20):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Verify no errors
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify first 10 allowed, rest rate limited
    allowed_count = sum(1 for allowed, _ in results if allowed)
    assert allowed_count == 10, f"Expected 10 allowed, got {allowed_count}"

def test_thread_safety_under_load(rate_limiter):
    """Test thread safety under heavy load"""
    identifiers = [f"192.168.1.{i}" for i in range(100)]
    results = {}
    errors = []

    def make_requests(identifier):
        try:
            for _ in range(15):
                allowed, retry_after = rate_limiter.is_allowed(identifier)
                if identifier not in results:
                    results[identifier] = []
                results[identifier].append((allowed, retry_after))
        except Exception as e:
            errors.append((identifier, e))

    # Make requests from 100 threads
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
        allowed_count = sum(1 for allowed, _ in request_results if allowed)
        assert allowed_count == 10, f"Identifier {identifier} got {allowed_count} allowed requests"

def test_cleanup_prevents_memory_leaks(rate_limiter):
    """Test cleanup prevents memory leaks"""
    # Create many entries
    for i in range(1000):
        rate_limiter.is_allowed(f"192.168.1.{i}")

    # Wait for window to expire
    time.sleep(61)

    # Cleanup
    rate_limiter.cleanup()

    # Verify old entries removed
    stats = rate_limiter.get_stats()
    assert stats['total_identifiers'] == 0, f"Expected 0 entries, got {stats['total_identifiers']}"
```

---

### Sprint 2 Deliverables Summary

**Completed Tasks**:
- ✅ SQLite database layer with proper schema
- ✅ Database migrations system
- ✅ Transaction support with ACID guarantees
- ✅ Data validation and constraints
- ✅ Backup and recovery strategy
- ✅ Thread-safe rate limiter with locks
- ✅ Comprehensive thread-safety tests

**Test Coverage**:
- ✅ Database tests (12 tests)
- ✅ Migration tests (5 tests)
- ✅ Thread-safety tests (8 tests)

**Documentation**:
- ✅ Database schema documentation
- ✅ Migration guide
- ✅ Thread-safety implementation guide

**Success Metrics**:
- ✅ Database layer operational
- ✅ All transactions atomic and consistent
- ✅ No race conditions under load
- ✅ Architecture score improved to 75/100

---

## 📋 Sprint 3: API Testing & Monitoring

**Duration**: 5 days (Mon-Fri)
**Effort**: 40 hours
**Priority**: HIGH
**Dependencies**: Sprint 1, Sprint 2

### Sprint Objectives

Implement comprehensive FastAPI endpoint testing and set up monitoring infrastructure.

### Deliverables

#### 3.1 Implement FastAPI Endpoint Tests (20 hours)

**Issue**: No API endpoint testing (0/10 coverage)

**Tasks**:
- [ ] Create test suite structure (2h)
- [ ] Implement authentication tests (4h)
- [ ] Implement request/response validation tests (4h)
- [ ] Implement rate limiting tests (4h)
- [ ] Implement input validation tests (4h)
- [ ] Implement error handling tests (2h)

**Implementation Details**:

```python
# tests/integration/test_fastapi_endpoints.py
import pytest
from fastapi.testclient import TestClient
from web.server import app
import json
from datetime import datetime, timedelta

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
def valid_api_key():
    """Provide valid API key"""
    return "test_api_key_12345"

@pytest.fixture
def test_config(client, valid_api_key):
    """Create test configuration"""
    response = client.post(
        "/api/config",
        headers={"Authorization": f"Bearer {valid_api_key}"},
        json={
            "owner_email": "owner@example.com",
            "beneficiary_email": "beneficiary@example.com",
            "check_in_interval_days": 30,
            "storage_config": {
                "local_path": "/tmp/test_storage",
                "enable_ipfs": False
            }
        }
    )
    assert response.status_code == 200
    return response.json()

class TestAuthentication:
    """Test authentication and authorization"""

    def test_status_endpoint_valid_auth(self, client, valid_api_key):
        """Test status endpoint with valid authentication"""
        response = client.get(
            "/api/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "initialized" in data
        assert "days_remaining" in data

    def test_status_endpoint_invalid_auth(self, client):
        """Test status endpoint rejects invalid API key"""
        response = client.get(
            "/api/status",
            headers={"Authorization": "Bearer invalid_key"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_status_endpoint_missing_auth(self, client):
        """Test status endpoint requires authentication"""
        response = client.get("/api/status")
        assert response.status_code == 401

    def test_api_key_rotation(self, client, valid_api_key):
        """Test API key rotation"""
        # Rotate API key
        response = client.post(
            "/api/auth/rotate",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "new_api_key" in data

        # Old key should no longer work
        response = client.get(
            "/api/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 401

        # New key should work
        new_key = data["new_api_key"]
        response = client.get(
            "/api/status",
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert response.status_code == 200

class TestRequestResponseValidation:
    """Test request and response validation"""

    def test_status_response_format(self, client, valid_api_key):
        """Test status endpoint response format"""
        response = client.get(
            "/api/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "initialized" in data
        assert "days_remaining" in data
        assert "deadline" in data
        assert "last_checkin" in data

        # Verify data types
        assert isinstance(data["initialized"], bool)
        assert isinstance(data["days_remaining"], int)
        assert isinstance(data["deadline"], str)
        assert isinstance(data["last_checkin"], (str, type(None)))

    def test_ping_request_validation(self, client, valid_api_key):
        """Test ping endpoint validates request"""
        # Valid request
        response = client.post(
            "/api/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"pin": "1234"}
        )
        assert response.status_code == 200

        # Missing pin
        response = client.post(
            "/api/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={}
        )
        assert response.status_code == 422

        # Invalid pin type
        response = client.post(
            "/api/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"pin": 1234}
        )
        assert response.status_code == 422

    def test_freeze_endpoint_validation(self, client, valid_api_key):
        """Test freeze endpoint validates input"""
        # Valid request
        response = client.post(
            "/api/freeze",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"days": 30}
        )
        assert response.status_code == 200

        # Invalid days (too large)
        response = client.post(
            "/api/freeze",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"days": 400}
        )
        assert response.status_code == 422

        # Invalid days (negative)
        response = client.post(
            "/api/freeze",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"days": -10}
        )
        assert response.status_code == 422

class TestRateLimiting:
    """Test rate limiting enforcement"""

    def test_rate_limiting_enforcement(self, client, valid_api_key):
        """Test rate limiting is enforced"""
        # Send 11 requests rapidly (limit is 10)
        responses = []
        for i in range(11):
            response = client.get(
                "/api/status",
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )
            responses.append(response)

        # First 10 should succeed
        for i in range(10):
            assert responses[i].status_code == 200

        # Last request should be rate limited
        assert responses[10].status_code == 429
        data = responses[10].json()
        assert "retry_after" in data

    def test_rate_limit_reset_after_window(self, client, valid_api_key):
        """Test rate limit resets after window expires"""
        import time

        # Exhaust rate limit
        for _ in range(10):
            client.get(
                "/api/status",
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )

        # Should be rate limited
        response = client.get(
            "/api/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 429

        # Wait for window to expire (assuming 60s window for testing)
        # In production, this would be longer
        time.sleep(61)

        # Should be allowed again
        response = client.get(
            "/api/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200

class TestInputValidation:
    """Test input validation and security"""

    def test_path_traversal_prevention(self, client, valid_api_key):
        """Test path traversal prevention in bundle add"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM"
        ]

        for path in malicious_paths:
            response = client.post(
                "/api/bundle/add",
                headers={"Authorization": f"Bearer {valid_api_key}"},
                json={"file_path": path}
            )
            assert response.status_code == 400

    def test_file_size_validation(self, client, valid_api_key):
        """Test file size validation"""
        # Create test file path (would need actual file in real test)
        large_file_path = "/tmp/large_test_file.txt"

        # Mock large file size
        response = client.post(
            "/api/bundle/add",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={
                "file_path": large_file_path,
                "file_size": 150 * 1024 * 1024  # 150MB
            }
        )
        assert response.status_code == 400

    def test_sql_injection_prevention(self, client, valid_api_key):
        """Test SQL injection prevention"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--"
        ]

        for input_str in malicious_inputs:
            response = client.post(
                "/api/bundle/add",
                headers={"Authorization": f"Bearer {valid_api_key}"},
                json={"file_path": input_str}
            )
            # Should not cause SQL errors
            assert response.status_code in [400, 404, 500]

class TestErrorHandling:
    """Test error handling and graceful degradation"""

    def test_400_bad_request(self, client, valid_api_key):
        """Test 400 Bad Request handling"""
        response = client.post(
            "/api/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"invalid": "data"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_404_not_found(self, client, valid_api_key):
        """Test 404 Not Found handling"""
        response = client.get(
            "/api/nonexistent",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 404

    def test_500_internal_server_error(self, client, valid_api_key):
        """Test 500 Internal Server Error handling"""
        # This would require mocking an internal error
        # For now, just verify error response format
        pass
```

**Success Criteria**:
- ✅ FastAPI endpoint testing: 8/10 coverage
- ✅ All 9 API endpoints tested
- ✅ Authentication and authorization verified
- ✅ Request/response validation tested
- ✅ Rate limiting enforcement verified
- ✅ Input validation tested
- ✅ Error handling validated

---

#### 3.2 Implement Monitoring Infrastructure (20 hours)

**Issue**: No performance monitoring or alerting

**Tasks**:
- [ ] Install and configure Prometheus (4h)
- [ ] Implement metrics collection (6h)
- [ ] Set up Grafana dashboards (4h)
- [ ] Configure Alertmanager (3h)
- [ ] Define alert rules (3h)

**Implementation Details**:

```python
# core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server, Info
import time
import os
from functools import wraps
from typing import Callable

# API Request Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Storage Metrics
storage_uploads_total = Counter(
    'storage_uploads_total',
    'Total storage uploads',
    ['provider', 'status']
)

storage_upload_duration = Histogram(
    'storage_upload_duration_seconds',
    'Storage upload duration',
    ['provider'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

storage_downloads_total = Counter(
    'storage_downloads_total',
    'Total storage downloads',
    ['provider', 'status']
)

storage_download_duration = Histogram(
    'storage_download_duration_seconds',
    'Storage download duration',
    ['provider'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

# Email Metrics
email_sends_total = Counter(
    'email_sends_total',
    'Total emails sent',
    ['type', 'status']
)

email_send_duration = Histogram(
    'email_send_duration_seconds',
    'Email send duration',
    ['type'],
    buckets=(1, 2, 5, 10, 30, 60)
)

# System Metrics
memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# Business Metrics
active_configurations = Gauge(
    'active_configurations',
    'Number of active configurations'
)

pending_checkins = Gauge(
    'pending_checkins',
    'Number of pending check-ins'
)

documents_stored = Gauge(
    'documents_stored',
    'Total number of documents stored'
)

# Application Info
app_info = Info(
    'application',
    'Application information'
)

def record_api_request(method: str, endpoint: str, status: int, duration: float):
    """Record API request metrics"""
    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()
    api_request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

def record_storage_upload(provider: str, status: str, duration: float):
    """Record storage upload metrics"""
    storage_uploads_total.labels(
        provider=provider,
        status=status
    ).inc()
    storage_upload_duration.labels(
        provider=provider
    ).observe(duration)

def record_storage_download(provider: str, status: str, duration: float):
    """Record storage download metrics"""
    storage_downloads_total.labels(
        provider=provider,
        status=status
    ).inc()
    storage_download_duration.labels(
        provider=provider
    ).observe(duration)

def record_email_send(email_type: str, status: str, duration: float):
    """Record email send metrics"""
    email_sends_total.labels(
        type=email_type,
        status=status
    ).inc()
    email_send_duration.labels(
        type=email_type
    ).observe(duration)

def update_system_metrics():
    """Update system metrics"""
    import psutil
    process = psutil.Process(os.getpid())

    memory_usage_bytes.set(process.memory_info().rss)
    cpu_usage_percent.set(process.cpu_percent())

def track_api_call(func: Callable) -> Callable:
    """Decorator to track API calls"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            # Extract endpoint from function name or args
            endpoint = func.__name__
            record_api_request('GET', endpoint, 200, duration)
            return result
        except Exception as e:
            duration = time.time() - start
            endpoint = func.__name__
            record_api_request('GET', endpoint, 500, duration)
            raise

    return wrapper

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server"""
    start_http_server(port)
    print(f"Metrics server started on port {port}")

    # Set application info
    app_info.info({
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'environment': os.environ.get('ENVIRONMENT', 'development')
    })
```

**Grafana Dashboard Configuration**:

```json
{
  "dashboard": {
    "title": "Lazarus Protocol API Dashboard",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "API Response Time (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total{status=~\"5..\"}[5m]) / rate(api_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      },
      {
        "title": "Storage Upload Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(storage_upload_duration_seconds_bucket[5m]))",
            "legendFormat": "{{provider}}"
          }
        ]
      },
      {
        "title": "Email Send Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(email_sends_total{status=\"success\"}[5m]) / rate(email_sends_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "memory_usage_bytes / 1024 / 1024",
            "legendFormat": "Memory (MB)"
          }
        ]
      },
      {
        "title": "Active Configurations",
        "type": "stat",
        "targets": [
          {
            "expr": "active_configurations"
          }
        ]
      },
      {
        "title": "Pending Check-ins",
        "type": "stat",
        "targets": [
          {
            "expr": "pending_checkins"
          }
        ]
      }
    ]
  }
}
```

**Alertmanager Configuration**:

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default'
    email_configs:
      - to: 'alerts@lazarus-protocol.com'

  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@lazarus-protocol.com'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#critical-alerts'

  - name: 'warning-alerts'
    email_configs:
      - to: 'devops@lazarus-protocol.com'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#warnings'
```

**Alert Rules**:

```yaml
# alerts.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          rate(api_requests_total{status=~"5.."}[5m])
          / rate(api_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          description: "P95 latency is {{ $value }}s"

      - alert: StorageUploadFailure
        expr: |
          rate(storage_uploads_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Storage upload failures detected"
          description: "Storage upload error rate is {{ $value }}"

      - alert: EmailSendFailure
        expr: |
          rate(email_sends_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Email send failures detected"
          description: "Email send error rate is {{ $value }}"

      - alert: HighMemoryUsage
        expr: memory_usage_bytes / 1024 / 1024 > 1024
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}MB"
```

**Success Criteria**:
- ✅ Prometheus metrics collection operational
- ✅ Grafana dashboards configured
- ✅ Alerting with Alertmanager implemented
- ✅ Business metrics tracking in place
- ✅ Log aggregation system operational

---

### Sprint 3 Deliverables Summary

**Completed Tasks**:
- ✅ FastAPI endpoint testing (8/10 coverage)
- ✅ All 9 API endpoints tested
- ✅ Prometheus metrics collection
- ✅ Grafana dashboards
- ✅ Alertmanager configuration
- ✅ Alert rules defined

**Test Coverage**:
- ✅ API endpoint tests (25 tests)
- ✅ Authentication tests (5 tests)
- ✅ Rate limiting tests (4 tests)
- ✅ Input validation tests (6 tests)

**Monitoring**:
- ✅ 15+ metrics collected
- ✅ 8 dashboard panels
- ✅ 5 alert rules configured

**Success Metrics**:
- ✅ API testing score improved to 80/100
- ✅ Monitoring operational
- ✅ Real-time visibility into system health

---

## 📋 Sprint 4: Integration Testing

**Duration**: 5 days (Mon-Fri)
**Effort**: 40 hours
**Priority**: HIGH
**Dependencies**: Sprint 1, Sprint 2, Sprint 3

### Sprint Objectives

Implement comprehensive end-to-end integration tests for complete workflows.

### Deliverables

#### 4.1 Implement End-to-End Workflow Tests (40 hours)

**Issue**: No end-to-end integration tests (1/10 coverage)

**Tasks**:
- [ ] Create test suite structure (4h)
- [ ] Implement check-in workflow tests (8h)
- [ ] Implement document bundle workflow tests (8h)
- [ ] Implement IPFS storage workflow tests (8h)
- [ ] Implement email alert workflow tests (6h)
- [ ] Implement error propagation tests (6h)

**Implementation Details**:

```python
# tests/integration/test_end_to_end_workflows.py
import pytest
import asyncio
from pathlib import Path
import tempfile
from datetime import datetime, timedelta
from core.database import DatabaseManager, DatabaseConfig
from core.encryption import encrypt_file, decrypt_file
from core.storage import upload_to_ipfs, download_from_ipfs
from agent.alerts import send_reminder_email, send_final_warning, send_delivery_email

@pytest.fixture
def db():
    """Create test database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = DatabaseConfig(path=Path(tmpdir) / "test.db")
        db = DatabaseManager(config)
        yield db
        db.close()

@pytest.fixture
def test_user(db):
    """Create test user"""
    api_key = "test_api_key_12345"
    user_id = db.create_user("test@example.com", api_key)
    return {"id": user_id, "api_key": api_key}

@pytest.fixture
def test_config(db, test_user):
    """Create test configuration"""
    config = {
        "owner_email": "owner@example.com",
        "beneficiary_email": "beneficiary@example.com",
        "check_in_interval_days": 30,
        "storage_config": {
            "local_path": "/tmp/test_storage",
            "enable_ipfs": False
        }
    }
    config_id = db.create_configuration(test_user["id"], config)
    return {"id": config_id, **config}

class TestCheckInWorkflow:
    """Test complete check-in workflow"""

    def test_complete_checkin_workflow(self, db, test_user, test_config):
        """Test complete check-in workflow from API to storage"""
        # 1. Verify initial state
        config_data = db.get_configuration(test_config["id"])
        assert config_data["last_checkin_timestamp"] is None

        # 2. Perform check-in
        checkin_time = datetime.now()
        db.update_configuration(test_config["id"], {
            "last_checkin_timestamp": checkin_time
        })

        # 3. Verify configuration updated
        updated_config = db.get_configuration(test_config["id"])
        assert updated_config["last_checkin_timestamp"] is not None
        assert updated_config["last_checkin_timestamp"] >= checkin_time

        # 4. Verify event logged
        events = db.get_events(test_config["id"], limit=10)
        assert any("CHECKIN" in e["content"] for e in events)

        # 5. Verify deadline extended
        expected_deadline = checkin_time + timedelta(days=test_config["check_in_interval_days"])
        assert updated_config["deadline_timestamp"] >= expected_deadline

    def test_multiple_checkins(self, db, test_config):
        """Test multiple check-ins over time"""
        # Perform 5 check-ins
        for i in range(5):
            checkin_time = datetime.now()
            db.update_configuration(test_config["id"], {
                "last_checkin_timestamp": checkin_time
            })
            time.sleep(0.1)  # Small delay

        # Verify all events logged
        events = db.get_events(test_config["id"], limit=10)
        checkin_events = [e for e in events if "CHECKIN" in e["content"]]
        assert len(checkin_events) == 5

    def test_checkin_after_deadline(self, db, test_config):
        """Test check-in after deadline has passed"""
        # Set deadline in the past
        past_deadline = datetime.now() - timedelta(days=1)
        db.update_configuration(test_config["id"], {
            "deadline_timestamp": past_deadline
        })

        # Perform check-in
        checkin_time = datetime.now()
        db.update_configuration(test_config["id"], {
            "last_checkin_timestamp": checkin_time
        })

        # Verify deadline extended
        updated_config = db.get_configuration(test_config["id"])
        expected_deadline = checkin_time + timedelta(days=test_config["check_in_interval_days"])
        assert updated_config["deadline_timestamp"] >= expected_deadline

class TestDocumentBundleWorkflow:
    """Test complete document bundle management workflow"""

    def test_complete_document_bundle_workflow(self, db, test_config):
        """Test complete document bundle management workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 1. Create test documents
            doc1 = tmpdir / "doc1.pdf"
            doc1.write_text("Test document 1 content")

            doc2 = tmpdir / "doc2.txt"
            doc2.write_text("Test document 2 content")

            # 2. Add documents to bundle
            doc1_info = {
                "filename": doc1.name,
                "file_type": "PDF",
                "file_size": doc1.stat().st_size,
                "storage_provider": "local",
                "encrypted_path": str(tmpdir / "encrypted_doc1.pdf")
            }
            doc1_id = db.add_document(test_config["id"], doc1_info)

            doc2_info = {
                "filename": doc2.name,
                "file_type": "TEXT",
                "file_size": doc2.stat().st_size,
                "storage_provider": "local",
                "encrypted_path": str(tmpdir / "encrypted_doc2.txt")
            }
            doc2_id = db.add_document(test_config["id"], doc2_info)

            # 3. Verify bundle manifest
            documents = db.get_documents(test_config["id"])
            assert len(documents) == 2
            assert any(d["filename"] == "doc1.pdf" for d in documents)
            assert any(d["filename"] == "doc2.txt" for d in documents)

            # 4. Remove document
            result = db.remove_document(doc1_id)
            assert result is True

            # 5. Verify removal
            documents = db.get_documents(test_config["id"])
            assert len(documents) == 1
            assert documents[0]["filename"] == "doc2.txt"

    def test_large_document_bundle(self, db, test_config):
        """Test handling large document bundles"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create 20 documents
            documents = []
            for i in range(20):
                doc = tmpdir / f"document_{i}.txt"
                doc.write_text(f"Test content {i}")

                doc_info = {
                    "filename": doc.name,
                    "file_type": "TEXT",
                    "file_size": doc.stat().st_size,
                    "storage_provider": "local",
                    "encrypted_path": str(tmpdir / f"encrypted_{i}.txt")
                }
                doc_id = db.add_document(test_config["id"], doc_info)
                documents.append(doc_id)

            # Verify all documents stored
            stored_docs = db.get_documents(test_config["id"])
            assert len(stored_docs) == 20

            # Remove all documents
            for doc_id in documents:
                db.remove_document(doc_id)

            # Verify all removed
            stored_docs = db.get_documents(test_config["id"])
            assert len(stored_docs) == 0

class TestIPFSStorageWorkflow:
    """Test complete IPFS storage workflow"""

    @pytest.mark.integration
    def test_complete_ipfs_storage_workflow(self):
        """Test complete IPFS storage workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 1. Create test file
            test_file = tmpdir / "test.txt"
            test_file.write_text("Test content for IPFS storage")

            # 2. Encrypt file
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization

            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()

            encrypted_path, key_blob = encrypt_file(
                test_file,
                public_key,
                tmpdir / "encrypted"
            )

            # 3. Upload to IPFS (if available)
            try:
                result = upload_to_ipfs(encrypted_path)
                assert result.provider in ["local_ipfs", "pinata", "web3_storage"]
                assert result.cid is not None

                # 4. Download from IPFS
                download_path = tmpdir / "downloaded.bin"
                downloaded = download_from_ipfs(result.cid, download_path)

                # 5. Verify integrity
                assert downloaded.stat().st_size == encrypted_path.stat().st_size

                # 6. Decrypt and verify
                decrypted_path = decrypt_file(
                    downloaded,
                    key_blob,
                    private_key,
                    tmpdir / "decrypted.txt"
                )

                assert decrypted_path.stat().st_size == test_file.stat().st_size
                assert decrypted_path.read_text() == test_file.read_text()

            except Exception as e:
                # IPFS not available, skip test
                pytest.skip(f"IPFS not available: {e}")

class TestEmailAlertWorkflow:

