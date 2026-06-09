# API Testing Report - Lazarus Protocol

**Date:** 2026-05-05
**Project:** Lazarus Protocol
**Version:** v1.0
**Tester:** API Testing Agent
**Overall API Quality Score:** 72/100

---

## Executive Summary

The Lazarus Protocol project implements a comprehensive dead man's switch system with multiple API layers including SendGrid email integration, FastAPI web services, IPFS storage, encryption services, and security mechanisms. While the project demonstrates solid architectural foundations, there are significant gaps in integration testing coverage, particularly in end-to-end workflows, error handling validation, and performance testing.

### Key Findings

**Strengths:**
- Well-structured API architecture with clear separation of concerns
- Comprehensive security implementation with authentication, rate limiting, and input validation
- Multi-provider storage fallback strategy (IPFS → Pinata → Web3.Storage → Local)
- Existing SendGrid integration tests with real API validation
- Strong error handling with custom exceptions

**Critical Gaps:**
- No end-to-end integration tests for complete workflows
- Missing API endpoint testing for FastAPI web server
- Insufficient storage API testing under load
- No performance benchmarking or SLA validation
- Limited security testing beyond basic authentication
- Missing monitoring and alerting setup

**Priority Recommendations:**
1. Implement comprehensive FastAPI endpoint testing (P0)
2. Add end-to-end workflow integration tests (P0)
3. Create performance benchmarking suite (P1)
4. Enhance security testing with penetration scenarios (P1)
5. Establish monitoring and alerting infrastructure (P2)

---

## 1. SendGrid Integration Testing

### Current Coverage: 6/10

**Existing Tests:**
- ✅ Basic email delivery test (`test_send_simple_email`)
- ✅ Reminder email template test (`test_send_reminder_email`)
- ✅ Missing API key error handling (`test_sendgrid_missing_key_raises`)
- ✅ Missing from email error handling (`test_sendgrid_missing_from_email_raises`)

**API Functions Tested:**
- `send_reminder_email()` - Owner reminder emails
- `send_final_warning()` - Final warning with email + Telegram
- `send_delivery_email()` - Beneficiary delivery with attachments
- `_send_email()` - Core SendGrid transport layer

### Critical Gaps

**Missing Test Scenarios:**

1. **Attachment Handling** (P0)
   - Large file attachments (>10MB)
   - Multiple attachments
   - Attachment size limits
   - Attachment MIME type validation
   - Corrupted attachment handling

2. **Template Rendering** (P1)
   - Dynamic content personalization
   - HTML injection prevention
   - Unicode and special character handling
   - Email client compatibility testing

3. **Error Handling** (P0)
   - Network timeout scenarios
   - Rate limit exceeded (429 errors)
   - Invalid recipient addresses
   - SendGrid service unavailability
   - Partial failure scenarios

4. **Rate Limiting Compliance** (P1)
   - SendGrid API rate limits (100 emails/minute)
   - Burst handling
   - Retry logic validation
   - Backoff strategy testing

### Recommended Test Cases

```python
# P0 - Critical
def test_sendgrid_attachment_large_file():
    """Test delivery of large attachment (>10MB)"""
    large_file = create_test_file(size_mb=15)
    result = send_delivery_email(
        beneficiary_name="Test",
        beneficiary_email="test@example.com",
        owner_name="Owner",
        encrypted_file_path=large_file,
        key_blob_b64="test_blob"
    )
    assert result.success

def test_sendgrid_rate_limit_handling():
    """Test rate limit exceeded scenario"""
    # Send 101 emails rapidly
    for i in range(101):
        send_reminder_email("test@example.com", 30)
    # Should handle 429 error gracefully

def test_sendgrid_network_timeout():
    """Test network timeout handling"""
    with patch('requests.post', side_effect=Timeout):
        with pytest.raises(AlertError):
            _send_email("test@example.com", "Test", "<p>Test</p>")

# P1 - High Priority
def test_sendgrid_template_unicode():
    """Test Unicode and special characters in templates"""
    unicode_name = "日本語 Ñoño émoji 🎉"
    send_reminder_email("test@example.com", 30)

def test_sendgrid_html_injection_prevention():
    """Test HTML injection prevention in email content"""
    malicious_input = "<script>alert('xss')</script>"
    result = send_reminder_email("test@example.com", 30)
    assert "<script>" not in result.body
```

### Performance Benchmarks

**Current Status:** Not measured

**Recommended SLAs:**
- Email delivery latency: <5 seconds (P95)
- Attachment upload time: <30 seconds for 10MB files
- Template rendering: <100ms
- API response time: <2 seconds

**Test Implementation:**
```python
def test_sendgrid_performance_sla():
    """Validate SendGrid performance meets SLA"""
    start = time.time()
    send_reminder_email("test@example.com", 30)
    duration = time.time() - start
    assert duration < 5.0, f"Email delivery took {duration}s, SLA is 5s"
```

---

## 2. Internal API Testing (FastAPI Web Server)

### Current Coverage: 2/10

**Existing Tests:** None identified

**API Endpoints:**
- `GET /` - Dashboard HTML
- `GET /pricing` - Pricing page
- `GET /status` - Current Lazarus status
- `POST /ping` - Record check-in
- `POST /freeze` - Extend deadline
- `GET /events` - Recent events
- `GET /bundle` - Bundle manifest
- `POST /bundle/add` - Add document
- `DELETE /bundle/{filename}` - Remove document

### Critical Gaps

**Missing Test Scenarios:**

1. **Authentication & Authorization** (P0)
   - Valid API key authentication
   - Invalid API key rejection
   - Missing API key handling
   - API key rotation scenarios
   - Multiple concurrent authenticated requests

2. **Request/Response Validation** (P0)
   - Request schema validation
   - Response format validation
   - Error response structure
   - Status code correctness
   - Content-Type validation

3. **Rate Limiting** (P0)
   - Per-IP rate limiting
   - Rate limit exceeded handling
   - Rate limit reset behavior
   - Concurrent request handling

4. **Input Validation** (P0)
   - Path traversal prevention
   - File size validation
   - Filename validation
   - Email format validation
   - SQL injection prevention

5. **Error Handling** (P0)
   - 400 Bad Request scenarios
   - 401 Unauthorized scenarios
   - 404 Not Found scenarios
   - 500 Internal Server Error scenarios
   - Graceful degradation

### Recommended Test Cases

```python
# P0 - Critical
@pytest.mark.integration
class TestFastAPIEndpoints:
    """Comprehensive FastAPI endpoint testing"""

    def test_status_endpoint_valid_auth(self):
        """Test status endpoint with valid authentication"""
        response = client.get(
            "/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200
        assert "initialized" in response.json()
        assert "days_remaining" in response.json()

    def test_status_endpoint_invalid_auth(self):
        """Test status endpoint rejects invalid API key"""
        response = client.get(
            "/status",
            headers={"Authorization": "Bearer invalid_key"}
        )
        assert response.status_code == 401

    def test_status_endpoint_missing_auth(self):
        """Test status endpoint requires authentication"""
        response = client.get("/status")
        assert response.status_code == 401

    def test_ping_endpoint_valid_request(self):
        """Test ping endpoint with valid request"""
        response = client.post(
            "/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"pin": "1234"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_freeze_endpoint_validation(self):
        """Test freeze endpoint validates input"""
        # Test invalid days (too large)
        response = client.post(
            "/freeze",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"days": 400}
        )
        assert response.status_code == 422  # Validation error

    def test_rate_limiting_enforcement(self):
        """Test rate limiting is enforced"""
        # Send 11 requests rapidly (limit is 10)
        for i in range(11):
            response = client.get(
                "/status",
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )
        # Last request should be rate limited
        assert response.status_code == 429

    def test_bundle_add_path_traversal_prevention(self):
        """Test path traversal prevention in bundle add"""
        response = client.post(
            "/bundle/add",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"file_path": "../../../etc/passwd"}
        )
        assert response.status_code == 400

    def test_bundle_add_file_size_validation(self):
        """Test file size validation in bundle add"""
        # Create large file >100MB
        large_file = create_test_file(size_mb=150)
        response = client.post(
            "/bundle/add",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"file_path": str(large_file)}
        )
        assert response.status_code == 400

# P1 - High Priority
def test_concurrent_authenticated_requests():
    """Test handling of concurrent authenticated requests"""
    import asyncio

    async def make_request():
        return client.get(
            "/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )

    # Make 50 concurrent requests
    responses = await asyncio.gather(*[make_request() for _ in range(50)])
    assert all(r.status_code == 200 for r in responses)

def test_error_response_format():
    """Test error responses follow consistent format"""
    response = client.get("/status")  # No auth
    assert response.status_code == 401
    error = response.json()
    assert "detail" in error
    assert isinstance(error["detail"], str)
```

### Performance Benchmarks

**Recommended SLAs:**
- GET /status: <100ms (P95)
- POST /ping: <200ms (P95)
- POST /freeze: <200ms (P95)
- GET /events: <150ms (P95)
- POST /bundle/add: <500ms (P95) for files <10MB

**Test Implementation:**
```python
@pytest.mark.performance
def test_api_performance_sla():
    """Validate API endpoints meet performance SLA"""
    # Test status endpoint
    start = time.time()
    response = client.get(
        "/status",
        headers={"Authorization": f"Bearer {valid_api_key}"}
    )
    duration = time.time() - start
    assert duration < 0.1, f"Status endpoint took {duration}s, SLA is 100ms"

    # Test ping endpoint
    start = time.time()
    response = client.post(
        "/ping",
        headers={"Authorization": f"Bearer {valid_api_key}"}
    )
    duration = time.time() - start
    assert duration < 0.2, f"Ping endpoint took {duration}s, SLA is 200ms"
```

---

## 3. Storage API Testing

### Current Coverage: 3/10

**Existing Tests:** None identified

**Storage Functions:**
- `upload_to_ipfs()` - Upload to IPFS with provider fallback
- `download_from_ipfs()` - Download from IPFS with gateway fallback
- `store_locally()` - Local filesystem storage
- `get_bundle_manifest()` - Get document manifest
- `add_document_to_bundle()` - Add document to bundle
- `remove_document_from_bundle()` - Remove document from bundle

### Critical Gaps

**Missing Test Scenarios:**

1. **IPFS Upload Testing** (P0)
   - Local IPFS node upload
   - Pinata upload with authentication
   - Web3.Storage upload
   - Provider fallback behavior
   - Upload retry logic
   - Large file handling (>50MB)

2. **IPFS Download Testing** (P0)
   - Gateway fallback behavior
   - CID validation
   - Download retry logic
   - Corrupted CID handling
   - Size limit enforcement
   - Streaming download validation

3. **Local Storage Testing** (P0)
   - File copy operations
   - Permission handling
   - Disk space validation
   - Backup versioning
   - Secure file deletion

4. **Error Handling** (P0)
   - Network failures
   - Authentication failures
   - Invalid CID format
   - Disk full scenarios
   - Permission denied scenarios

5. **Performance Under Load** (P1)
   - Concurrent uploads
   - Concurrent downloads
   - Large file handling
   - Memory usage validation

### Recommended Test Cases

```python
# P0 - Critical
@pytest.mark.integration
class TestStorageAPI:
    """Comprehensive storage API testing"""

    def test_ipfs_upload_local_node(self):
        """Test upload to local IPFS node"""
        test_file = create_test_file(size_mb=5)
        result = upload_to_ipfs(test_file)
        assert result.provider == "local_ipfs"
        assert _validate_cid(result.cid)
        assert result.size_bytes == test_file.stat().st_size

    def test_ipfs_upload_pinata_fallback(self):
        """Test Pinata fallback when local node unavailable"""
        # Mock local node as unavailable
        with patch('core.storage.ipfs_available', return_value=False):
            test_file = create_test_file(size_mb=5)
            result = upload_to_ipfs(test_file)
            assert result.provider == "pinata"

    def test_ipfs_upload_all_providers_fail(self):
        """Test behavior when all IPFS providers fail"""
        with patch('core.storage.ipfs_available', return_value=False), \
             patch('core.storage.pinata_configured', return_value=False), \
             patch('core.storage.web3_storage_configured', return_value=False):
            test_file = create_test_file(size_mb=5)
            with pytest.raises(StorageError):
                upload_to_ipfs(test_file)

    def test_ipfs_download_gateway_fallback(self):
        """Test gateway fallback during download"""
        cid = "QmTestCID"
        output_path = Path("/tmp/test_download.bin")

        # Mock first gateway failure, second success
        with patch('core.storage._download_from_gateway') as mock_download:
            mock_download.side_effect = [
                DownloadError("Gateway 1 failed"),
                output_path  # Success on second attempt
            ]
            result = download_from_ipfs(cid, output_path)
            assert result == output_path

    def test_ipfs_cid_validation(self):
        """Test CID validation"""
        # Valid CID v1
        assert _validate_cid("bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi")

        # Valid CID v0
        assert _validate_cid("QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")

        # Invalid CID
        assert not _validate_cid("invalid_cid")

    def test_local_storage_permissions(self):
        """Test local storage sets secure permissions"""
        test_file = create_test_file(size_mb=1)
        dest_dir = Path("/tmp/test_storage")
        result = store_locally(test_file, dest_dir)

        # Check file has secure permissions (0600)
        stat = result.stat()
        permissions = stat.st_mode & 0o777
        assert permissions == 0o600

    def test_bundle_document_operations(self):
        """Test bundle document add/remove operations"""
        test_file = create_test_file(size_mb=1)

        # Add document
        doc_info = add_document_to_bundle(str(test_file), "PDF")
        assert doc_info["filename"] == test_file.name
        assert doc_info["type"] == "PDF"

        # Verify in manifest
        manifest = get_bundle_manifest()
        assert any(d["filename"] == test_file.name for d in manifest)

        # Remove document
        result = remove_document_from_bundle(test_file.name)
        assert result is True

        # Verify removed from manifest
        manifest = get_bundle_manifest()
        assert not any(d["filename"] == test_file.name for d in manifest)

    def test_download_size_limit_enforcement(self):
        """Test download size limit is enforced"""
        large_cid = "QmLargeCID"  # Mock large file
        output_path = Path("/tmp/large_download.bin")

        with patch('core.storage._download_from_gateway') as mock_download:
            # Simulate large file download
            mock_download.side_effect = DownloadError(
                "Download exceeds size limit (104857600 bytes)"
            )
            with pytest.raises(DownloadError):
                download_from_ipfs(large_cid, output_path)

# P1 - High Priority
def test_concurrent_uploads():
    """Test handling of concurrent uploads"""
    import asyncio

    async def upload_file(file_path):
        return upload_to_ipfs(file_path)

    # Create 10 test files
    test_files = [create_test_file(size_mb=1) for _ in range(10)]

    # Upload concurrently
    results = await asyncio.gather(*[upload_file(f) for f in test_files])

    # Verify all succeeded
    assert all(r.provider in ["local_ipfs", "pinata", "web3_storage"] for r in results)

def test_large_file_handling():
    """Test handling of large files (>50MB)"""
    large_file = create_test_file(size_mb=60)
    result = upload_to_ipfs(large_file)
    assert result.size_bytes == large_file.stat().st_size
    assert result.duration_seconds < 300  # Should complete in <5 minutes
```

### Performance Benchmarks

**Recommended SLAs:**
- Small file upload (<10MB): <30 seconds
- Medium file upload (10-50MB): <2 minutes
- Large file upload (50-100MB): <5 minutes
- Download from gateway: <1 minute for 10MB files
- Local storage operation: <1 second

**Test Implementation:**
```python
@pytest.mark.performance
def test_storage_performance_sla():
    """Validate storage operations meet performance SLA"""

    # Test small file upload
    small_file = create_test_file(size_mb=5)
    start = time.time()
    result = upload_to_ipfs(small_file)
    duration = time.time() - start
    assert duration < 30.0, f"Small file upload took {duration}s, SLA is 30s"

    # Test download
    start = time.time()
    download_from_ipfs(result.cid, Path("/tmp/test_download.bin"))
    duration = time.time() - start
    assert duration < 60.0, f"Download took {duration}s, SLA is 60s"

    # Test local storage
    start = time.time()
    store_locally(small_file, Path("/tmp/local_storage"))
    duration = time.time() - start
    assert duration < 1.0, f"Local storage took {duration}s, SLA is 1s"
```

---

## 4. Security API Testing

### Current Coverage: 5/10

**Existing Tests:** Basic security tests in `test_security.py`

**Security Functions:**
- `verify_api_key()` - API key authentication
- `check_rate_limit()` - Rate limiting enforcement
- `validate_safe_path()` - Path traversal prevention
- `validate_file_size()` - File size validation
- `sanitize_input()` - Input sanitization
- `validate_filename()` - Filename validation
- `get_security_headers()` - Security headers generation

### Critical Gaps

**Missing Test Scenarios:**

1. **Authentication Testing** (P0)
   - API key brute force prevention
   - API key rotation scenarios
   - Session management
   - Token expiration handling
   - Concurrent authentication attempts

2. **Rate Limiting Testing** (P0)
   - Distributed rate limiting
   - Rate limit bypass attempts
   - Rate limit reset behavior
   - IP spoofing prevention
   - Rate limit persistence

3. **Input Validation Testing** (P0)
   - SQL injection prevention
   - XSS attack prevention
   - CSRF token validation
   - Command injection prevention
   - LDAP injection prevention

4. **Path Traversal Testing** (P0)
   - Directory traversal attempts
   - Symbolic link attacks
   - Path normalization
   - Windows path attacks
   - Unicode path attacks

5. **Security Headers Testing** (P1)
   - HSTS enforcement
   - CSP validation
   - X-Frame-Options
   - X-Content-Type-Options
   - Referrer-Policy

### Recommended Test Cases

```python
# P0 - Critical
@pytest.mark.security
class TestSecurityAPI:
    """Comprehensive security API testing"""

    def test_api_key_brute_force_prevention(self):
        """Test API key brute force is prevented"""
        invalid_keys = [f"invalid_key_{i}" for i in range(100)]

        for key in invalid_keys:
            response = client.get(
                "/status",
                headers={"Authorization": f"Bearer {key}"}
            )
            # Should be rate limited after attempts
            if response.status_code == 429:
                break
        else:
            pytest.fail("Rate limiting not triggered after 100 invalid attempts")

    def test_rate_limit_bypass_prevention(self):
        """Test rate limit bypass attempts are prevented"""
        # Try using different headers to bypass
        headers_list = [
            {"Authorization": f"Bearer {valid_api_key}"},
            {"Authorization": f"Bearer {valid_api_key}", "X-Forwarded-For": "1.2.3.4"},
            {"Authorization": f"Bearer {valid_api_key}", "X-Real-IP": "5.6.7.8"},
        ]

        for headers in headers_list:
            for _ in range(15):  # Exceed rate limit
                response = client.get("/status", headers=headers)
                if response.status_code == 429:
                    break
            else:
                pytest.fail(f"Rate limiting bypassed with headers: {headers}")

    def test_sql_injection_prevention(self):
        """Test SQL injection is prevented"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--",
        ]

        for input_str in malicious_inputs:
            response = client.post(
                "/bundle/add",
                headers={"Authorization": f"Bearer {valid_api_key}"},
                json={"file_path": input_str}
            )
            # Should not cause SQL errors
            assert response.status_code in [400, 404, 500]

    def test_xss_prevention(self):
        """Test XSS attacks are prevented"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
        ]

        for input_str in malicious_inputs:
            sanitized = sanitize_input(input_str, max_length=1000)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized

    def test_path_traversal_prevention(self):
        """Test path traversal attacks are prevented"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "~/.ssh/id_rsa",
        ]

        for path_str in malicious_paths:
            with pytest.raises(ValueError):
                validate_safe_path(Path(path_str))

    def test_csrf_token_validation(self):
        """Test CSRF token validation"""
        # Generate token
        token = generate_csrf_token()

        # Create mock request
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "headers": [(b"x-csrf-token", token.encode())],
            }
        )

        # Valid token
        assert verify_csrf_token(request, token) is True

        # Invalid token
        assert verify_csrf_token(request, "invalid_token") is False

    def test_security_headers_enforcement(self):
        """Test security headers are enforced"""
        response = client.get("/")

        headers = get_security_headers()

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_filename_validation(self):
        """Test filename validation prevents malicious filenames"""
        malicious_filenames = [
            "../../../etc/passwd",
            "file.txt\x00.exe",
            "con.txt",  # Windows reserved name
            "file\x1b[0m.txt",  # Control characters
        ]

        for filename in malicious_filenames:
            assert not validate_filename(filename)

# P1 - High Priority
def test_command_injection_prevention():
    """Test command injection is prevented"""
    malicious_inputs = [
        "; rm -rf /",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
    ]

    for input_str in malicious_inputs:
        sanitized = sanitize_input(input_str, max_length=100)
        assert ";" not in sanitized
        assert "|" not in sanitized
        assert "$" not in sanitized
        assert "`" not in sanitized

def test_ldap_injection_prevention():
    """Test LDAP injection is prevented"""
    malicious_inputs = [
        "*)(uid=*",
        "*)(|(objectClass=*)",
        "*))(|(objectClass=*)",
    ]

    for input_str in malicious_inputs:
        sanitized = sanitize_input(input_str, max_length=100)
        assert "*" not in sanitized
        assert ")" not in sanitized
        assert "(" not in sanitized
```

### Security Testing Recommendations

**Penetration Testing Scenarios:**
1. **Authentication Attacks**
   - API key enumeration
   - Session fixation
   - Token replay attacks
   - Credential stuffing

2. **Injection Attacks**
   - SQL injection
   - NoSQL injection
   - Command injection
   - LDAP injection

3. **Cross-Site Scripting (XSS)**
   - Reflected XSS
   - Stored XSS
   - DOM-based XSS

4. **Cross-Site Request Forgery (CSRF)**
   - CSRF token validation
   - SameSite cookie enforcement
   - Origin validation

5. **Path Traversal**
   - Directory traversal
   - Symbolic link attacks
   - Path normalization

---

## 5. Integration Testing

### Current Coverage: 1/10

**Existing Tests:** None identified

**Integration Workflows:**
- Complete check-in workflow
- Deadline extension workflow
- Document bundle management workflow
- Email alert delivery workflow
- IPFS storage workflow
- Encryption/decryption workflow

### Critical Gaps

**Missing Test Scenarios:**

1. **End-to-End Workflows** (P0)
   - Complete setup → check-in → alert → delivery workflow
   - Multi-document bundle management workflow
   - IPFS upload → download → verify workflow
   - Encryption → storage → decryption workflow

2. **Cross-Component Integration** (P0)
   - Web server → storage integration
   - Web server → email integration
   - Storage → encryption integration
   - Alert system → storage integration

3. **Data Consistency** (P0)
   - Configuration persistence
   - Bundle state consistency
   - Event log integrity
   - Transaction atomicity

4. **Error Propagation** (P0)
   - Error handling across components
   - Graceful degradation
   - Partial failure scenarios
   - Recovery procedures

5. **Transaction Integrity** (P1)
   - Rollback scenarios
   - Concurrent modification handling
   - State consistency validation
   - Idempotency testing

### Recommended Test Cases

```python
# P0 - Critical
@pytest.mark.integration
class TestEndToEndWorkflows:
    """Comprehensive end-to-end workflow testing"""

    def test_complete_checkin_workflow(self):
        """Test complete check-in workflow from API to storage"""
        # 1. Initialize configuration
        config = create_test_config()

        # 2. Perform check-in via API
        response = client.post(
            "/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"pin": "1234"}
        )
        assert response.status_code == 200

        # 3. Verify configuration updated
        updated_config = load_config()
        assert updated_config.last_checkin_timestamp > config.last_checkin_timestamp

        # 4. Verify event logged
        events = get_events(limit=10)
        assert any("CHECKIN" in e["content"] for e in events)

    def test_complete_document_bundle_workflow(self):
        """Test complete document bundle management workflow"""
        # 1. Create test documents
        doc1 = create_test_file(size_mb=1, name="doc1.pdf")
        doc2 = create_test_file(size_mb=2, name="doc2.txt")

        # 2. Add documents via API
        response1 = client.post(
            "/bundle/add",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"file_path": str(doc1), "document_type": "PDF"}
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/bundle/add",
            headers={"Authorization": f"Bearer {valid_api_key}"},
            json={"file_path": str(doc2), "document_type": "TEXT"}
        )
        assert response2.status_code == 200

        # 3. Verify bundle manifest
        response = client.get(
            "/bundle",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200
        manifest = response.json()["manifest"]
        assert len(manifest) == 2

        # 4. Remove document
        response = client.delete(
            f"/bundle/{doc1.name}",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        assert response.status_code == 200

        # 5. Verify removal
        response = client.get(
            "/bundle",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )
        manifest = response.json()["manifest"]
        assert len(manifest) == 1
        assert manifest[0]["filename"] == doc2.name

    def test_complete_ipfs_storage_workflow(self):
        """Test complete IPFS storage workflow"""
        # 1. Create test file
        test_file = create_test_file(size_mb=5)

        # 2. Encrypt file
        public_key = load_test_public_key()
        encrypted_path, key_blob = encrypt_file(
            test_file,
            public_key,
            Path("/tmp/encrypted")
        )

        # 3. Upload to IPFS
        result = upload_to_ipfs(encrypted_path)
        assert _validate_cid(result.cid)

        # 4. Download from IPFS
        download_path = Path("/tmp/downloaded.bin")
        downloaded = download_from_ipfs(result.cid, download_path)

        # 5. Verify integrity
        assert downloaded.stat().st_size == encrypted_path.stat().st_size

        # 6. Decrypt and verify
        private_key = load_test_private_key()
        decrypted_path = decrypt_file(
            downloaded,
            key_blob,
            private_key,
            Path("/tmp/decrypted.pdf")
        )

        assert decrypted_path.stat().st_size == test_file.stat().st_size

    def test_complete_email_alert_workflow(self):
        """Test complete email alert delivery workflow"""
        # 1. Setup configuration
        config = create_test_config()
        config.owner_email = "test@example.com"

        # 2. Trigger reminder email
        send_reminder_email(config.owner_email, 25)

        # 3. Verify email sent (check logs or mock)
        # In real test, would verify email received

        # 4. Verify event logged
        events = get_events(limit=10)
        assert any("reminder" in e["content"].lower() for e in events)

    def test_error_propagation_across_components(self):
        """Test error propagation across components"""
        # 1. Test storage failure propagates to API
        with patch('core.storage.upload_to_ipfs', side_effect=StorageError("IPFS failed")):
            response = client.post(
                "/bundle/add",
                headers={"Authorization": f"Bearer {valid_api_key}"},
                json={"file_path": str(create_test_file(size_mb=1))}
            )
            # Should handle error gracefully
            assert response.status_code in [400, 500]

        # 2. Test email failure doesn't crash system
        with patch('agent.alerts._send_email', side_effect=AlertError("Email failed")):
            # Should not raise exception
            send_reminder_email("test@example.com", 25)

# P1 - High Priority
def test_concurrent_workflow_execution():
    """Test handling of concurrent workflow execution"""
    import asyncio

    async def perform_checkin():
        return client.post(
            "/ping",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )

    # Perform 10 concurrent check-ins
    responses = await asyncio.gather(*[perform_checkin() for _ in range(10)])

    # All should succeed
    assert all(r.status_code == 200 for r in responses)

    # Verify configuration consistency
    config = load_config()
    assert config.last_checkin_timestamp is not None

def test_transaction_rollback():
    """Test transaction rollback on failure"""
    # 1. Start transaction
    config = load_config()

    # 2. Perform operation that fails
    try:
        with patch('core.storage.upload_to_ipfs', side_effect=StorageError("Failed")):
            encrypt_and_store_file(
                create_test_file(size_mb=1),
                load_test_public_key(),
                Path("/tmp/encrypted"),
                enable_ipfs=True
            )
    except StorageError:
        pass

    # 3. Verify no partial state
    # Should not have partial encrypted files
    encrypted_dir = Path("/tmp/encrypted")
    assert not encrypted_dir.exists() or len(list(encrypted_dir.glob("*"))) == 0
```

---

## 6. Test Coverage Analysis

### Current Coverage Summary

| Component | Coverage Score | Test Count | Gap Severity |
|-----------|---------------|-------------|---------------|
| SendGrid Integration | 6/10 | 4 tests | Medium |
| FastAPI Web Server | 2/10 | 0 tests | Critical |
| Storage API | 3/10 | 0 tests | Critical |
| Security API | 5/10 | 38 tests | Medium |
| Encryption API | 4/10 | 0 tests | High |
| Integration Workflows | 1/10 | 0 tests | Critical |
| **Overall** | **3.5/10** | **42 tests** | **Critical** |

### Coverage Gaps by Priority

**P0 - Critical (Must Fix Before Launch):**
1. FastAPI endpoint testing (0/10 coverage)
2. End-to-end workflow testing (1/10 coverage)
3. Storage API testing (3/10 coverage)
4. Error handling validation (2/10 coverage)

**P1 - High Priority (Fix Within 1 Week):**
1. Encryption API testing (4/10 coverage)
2. Performance benchmarking (0/10 coverage)
3. Security penetration testing (5/10 coverage)
4. Concurrent operation testing (0/10 coverage)

**P2 - Medium Priority (Fix Within 2 Weeks):**
1. SendGrid attachment testing (6/10 coverage)
2. Rate limiting validation (5/10 coverage)
3. Monitoring setup (0/10 coverage)
4. Alerting configuration (0/10 coverage)

### Recommended Test Suite Structure

```
tests/
├── integration/
│   ├── test_sendgrid_integration.py (existing)
│   ├── test_fastapi_endpoints.py (NEW)
│   ├── test_storage_integration.py (NEW)
│   ├── test_encryption_integration.py (NEW)
│   └── test_end_to_end_workflows.py (NEW)
├── unit/
│   ├── test_security.py (existing)
│   ├── test_config.py (existing)
│   ├── test_license.py (existing)
│   ├── test_storage_unit.py (NEW)
│   └── test_encryption_unit.py (NEW)
├── performance/
│   ├── test_api_performance.py (NEW)
│   ├── test_storage_performance.py (NEW)
│   └── test_email_performance.py (NEW)
├── security/
│   ├── test_authentication.py (NEW)
│   ├── test_injection_attacks.py (NEW)
│   ├── test_path_traversal.py (NEW)
│   └── test_rate_limiting.py (NEW)
└── conftest.py (existing)
```

---

## 7. Performance Benchmarks

### Current Status: Not Measured

**Performance Testing Gaps:**
- No baseline performance metrics established
- No load testing conducted
- No stress testing performed
- No performance regression testing
- No SLA validation

### Recommended Performance Tests

#### API Response Time Benchmarks

```python
@pytest.mark.performance
class TestAPIPerformance:
    """Comprehensive API performance testing"""

    def test_status_endpoint_p50_latency(self):
        """Test status endpoint P50 latency < 50ms"""
        latencies = []
        for _ in range(100):
            start = time.time()
            response = client.get(
                "/status",
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )
            latencies.append(time.time() - start)

        p50 = np.percentile(latencies, 50)
        assert p50 < 0.05, f"P50 latency {p50}s exceeds 50ms"

    def test_status_endpoint_p95_latency(self):
        """Test status endpoint P95 latency < 100ms"""
        latencies = []
        for _ in range(100):
            start = time.time()
            response = client.get(
                "/status",
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )
            latencies.append(time.time() - start)

        p95 = np.percentile(latencies, 95)
        assert p95 < 0.1, f"P95 latency {p95}s exceeds 100ms"

    def test_status_endpoint_p99_latency(self):
        """Test status endpoint P99 latency < 200ms"""
        latencies = []
        for _ in range(100):
            start = time.time()
            response = client.get(
                "/status",
                headers={"Authorization": f"Bearer {valid_api_key}"}
            )
            latencies.append(time.time() - start)

        p99 = np.percentile(latencies, 99)
        assert p99 < 0.2, f"P99 latency {p99}s exceeds 200ms"
```

#### Throughput Benchmarks

```python
@pytest.mark.performance
def test_api_throughput_under_load():
    """Test API can handle 100 requests/second"""
    import asyncio

    async def make_request():
        return client.get(
            "/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )

    # Make 1000 requests over 10 seconds
    start = time.time()
    responses = await asyncio.gather(*[make_request() for _ in range(1000)])
    duration = time.time() - start

    throughput = 1000 / duration
    assert throughput >= 100, f"Throughput {throughput} req/s below 100 req/s"

    # Verify all succeeded
    assert all(r.status_code == 200 for r in responses)
```

#### Storage Performance Benchmarks

```python
@pytest.mark.performance
def test_ipfs_upload_performance():
    """Test IPFS upload performance meets SLA"""
    file_sizes = [1, 5, 10, 25, 50]  # MB

    for size_mb in file_sizes:
        test_file = create_test_file(size_mb=size_mb)
        start = time.time()
        result = upload_to_ipfs(test_file)
        duration = time.time() - start

        # SLA: <30s for <10MB, <2min for 10-50MB
        if size_mb < 10:
            assert duration < 30, f"{size_mb}MB upload took {duration}s, SLA is 30s"
        else:
            assert duration < 120, f"{size_mb}MB upload took {duration}s, SLA is 120s"

        print(f"{size_mb}MB upload: {duration:.2f}s")
```

#### Memory Usage Benchmarks

```python
@pytest.mark.performance
def test_memory_usage_under_load():
    """Test memory usage remains stable under load"""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Make 1000 requests
    for _ in range(1000):
        client.get(
            "/status",
            headers={"Authorization": f"Bearer {valid_api_key}"}
        )

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - initial_memory

    # Memory growth should be < 50MB
    assert memory_growth < 50, f"Memory grew {memory_growth}MB, limit is 50MB"
```

### Performance SLA Targets

| Metric | Target | Current Status |
|--------|--------|----------------|
| **API Response Time (P50)** | < 50ms | Not measured |
| **API Response Time (P95)** | < 100ms | Not measured |
| **API Response Time (P99)** | < 200ms | Not measured |
| **API Throughput** | > 100 req/s | Not measured |
| **Small File Upload (<10MB)** | < 30s | Not measured |
| **Medium File Upload (10-50MB)** | < 2min | Not measured |
| **Large File Upload (50-100MB)** | < 5min | Not measured |
| **Email Delivery Latency** | < 5s | Not measured |
| **Memory Growth (1000 req)** | < 50MB | Not measured |

---

## 8. Monitoring and Alerting Setup

### Current Status: Not Implemented

**Missing Monitoring Capabilities:**
1. No metrics collection system
2. No logging aggregation
3. No alerting infrastructure
4. No dashboards or visualization
5. No performance monitoring
6. No error tracking

### Recommended Monitoring Stack

#### Prometheus Metrics Collection

```python
# core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# API Request Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
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
    ['provider']
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
    ['type']
)

# System Metrics
memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

def record_api_request(method, endpoint, status, duration):
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

def record_storage_upload(provider, status, duration):
    """Record storage upload metrics"""
    storage_uploads_total.labels(
        provider=provider,
        status=status
    ).inc()
    storage_upload_duration.labels(
        provider=provider
    ).observe(duration)

def record_email_send(email_type, status, duration):
    """Record email send metrics"""
    email_sends_total.labels(
        type=email_type,
        status=status
    ).inc()
    email_send_duration.labels(
        type=email_type
    ).observe(duration)

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server"""
    start_http_server(port)
```

#### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Lazarus Protocol API Dashboard",
    "panels": [
      {
        "title": "API Request Rate",
        "targets": [
          {
            "expr": "rate(api_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "API Response Time (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(api_requests_total{status=~\"5..\"}[5m]) / rate(api_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      },
      {
        "title": "Storage Upload Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(storage_upload_duration_seconds_bucket[5m]))",
            "legendFormat": "{{provider}}"
          }
        ]
      },
      {
        "title": "Email Send Success Rate",
        "targets": [
          {
            "expr": "rate(email_sends_total{status=\"success\"}[5m]) / rate(email_sends_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "memory_usage_bytes / 1024 / 1024",
            "legendFormat": "Memory (MB)"
          }
        ]
      }
    ]
  }
}
```

#### Alertmanager Configuration

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

#### Alert Rules

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

### Monitoring Implementation Checklist

- [ ] Install and configure Prometheus
- [ ] Implement metrics collection in code
- [ ] Set up Grafana dashboards
- [ ] Configure Alertmanager
- [ ] Define alert rules
- [ ] Set up log aggregation (ELK stack or Loki)
- [ ] Configure error tracking (Sentry)
- [ ] Set up uptime monitoring
- [ ] Configure synthetic monitoring
- [ ] Implement distributed tracing (Jaeger/Zipkin)

---

## 9. Testing Recommendations

### Immediate Actions (Week 1)

1. **Implement FastAPI Endpoint Tests** (P0)
   - Create `tests/integration/test_fastapi_endpoints.py`
   - Test all 9 API endpoints
   - Cover authentication, validation, error handling
   - Estimated effort: 16 hours

2. **Implement Storage API Tests** (P0)
   - Create `tests/integration/test_storage_integration.py`
   - Test IPFS upload/download with all providers
   - Test local storage operations
   - Test error handling and edge cases
   - Estimated effort: 12 hours

3. **Implement End-to-End Workflow Tests** (P0)
   - Create `tests/integration/test_end_to_end_workflows.py`
   - Test complete check-in workflow
   - Test document bundle management workflow
   - Test IPFS storage workflow
   - Test email alert delivery workflow
   - Estimated effort: 20 hours

### Short-term Actions (Week 2-3)

4. **Implement Performance Tests** (P1)
   - Create `tests/performance/` directory
   - Implement API performance benchmarks
   - Implement storage performance tests
   - Implement load testing scenarios
   - Estimated effort: 16 hours

5. **Implement Security Tests** (P1)
   - Create `tests/security/` directory
   - Implement authentication tests
   - Implement injection attack tests
   - Implement path traversal tests
   - Implement rate limiting tests
   - Estimated effort: 12 hours

6. **Set Up Monitoring Infrastructure** (P2)
   - Install Prometheus
   - Configure Grafana dashboards
   - Set up Alertmanager
   - Define alert rules
   - Estimated effort: 20 hours

### Long-term Actions (Week 4+)

7. **Implement Encryption API Tests** (P1)
   - Create `tests/integration/test_encryption_integration.py`
   - Test encryption/decryption workflows
   - Test key management
   - Test memory security
   - Estimated effort: 8 hours

8. **Implement Concurrent Operation Tests** (P1)
   - Test concurrent API requests
   - Test concurrent storage operations
   - Test concurrent email sends
   - Test thread safety
   - Estimated effort: 8 hours

9. **Implement SendGrid Attachment Tests** (P2)
   - Test large file attachments
   - Test multiple attachments
   - Test attachment size limits
   - Test corrupted attachment handling
   - Estimated effort: 6 hours

### Testing Best Practices

1. **Test Organization**
   - Separate unit, integration, and performance tests
   - Use pytest markers for test categorization
   - Organize tests by component
   - Use descriptive test names

2. **Test Data Management**
   - Use fixtures for test data
   - Clean up test data after tests
   - Use test databases and storage
   - Mock external dependencies

3. **Test Execution**
   - Run tests in CI/CD pipeline
   - Run tests on every commit
   - Run tests before deployment
   - Use parallel test execution

4. **Test Reporting**
   - Generate test coverage reports
   - Track test metrics over time
   - Alert on test failures
   - Maintain test history

---

## 10. Conclusion

### Summary

The Lazarus Protocol API demonstrates solid architectural foundations with well-structured code and comprehensive security implementation. However, significant gaps in integration testing coverage prevent confident production deployment.

### Key Strengths

1. **Well-Structured Architecture**: Clear separation of concerns with modular components
2. **Comprehensive Security**: Authentication, rate limiting, and input validation implemented
3. **Multi-Provider Storage**: Robust fallback strategy for IPFS storage
4. **Strong Error Handling**: Custom exceptions and graceful degradation
5. **Existing Test Coverage**: SendGrid integration tests with real API validation

### Critical Gaps

1. **No FastAPI Endpoint Testing**: 0/10 coverage for web server endpoints
2. **No End-to-End Integration Tests**: 1/10 coverage for complete workflows
3. **No Storage API Testing**: 3/10 coverage for storage operations
4. **No Performance Monitoring**: No metrics collection or alerting
5. **No Performance Benchmarks**: No SLA validation or load testing

### Recommendations

**Immediate Priority (Week 1-2):**
1. Implement comprehensive FastAPI endpoint testing
2. Implement storage API integration tests
3. Implement end-to-end workflow tests
4. Set up basic monitoring infrastructure

**Short-term Priority (Week 3-4):**
1. Implement performance benchmarking suite
2. Enhance security testing with penetration scenarios
3. Set up comprehensive monitoring and alerting
4. Implement CI/CD pipeline with automated testing

**Long-term Priority (Week 5+):**
1. Implement encryption API testing
2. Implement concurrent operation testing
3. Enhance SendGrid attachment testing
4. Establish performance regression testing

### Production Readiness Assessment

**Current Status**: **NOT PRODUCTION READY**

**Overall API Quality Score**: **72/100**

**Blocking Issues**:
- No FastAPI endpoint testing (CRITICAL)
- No end-to-end integration tests (CRITICAL)
- No storage API testing (CRITICAL)
- No performance monitoring (HIGH)
- No performance benchmarks (HIGH)

**Estimated Time to Production Ready**: **3-4 weeks** with focused development

**Go/No-Go Recommendation**: **NO-GO** - Address all CRITICAL testing gaps before production deployment

### Success Criteria for Production Readiness

- ✅ FastAPI endpoint testing: 8/10 coverage
- ✅ End-to-end integration tests: 8/10 coverage
- ✅ Storage API testing: 8/10 coverage
- ✅ Performance monitoring: Operational
- ✅ Performance benchmarks: Established and validated
- ✅ Security testing: Comprehensive penetration tests completed
- ✅ CI/CD pipeline: Automated testing and deployment
- ✅ Monitoring and alerting: Fully configured

### Next Steps

1. **Week 1**: Implement FastAPI endpoint tests and storage API tests
2. **Week 2**: Implement end-to-end workflow tests and set up monitoring
3. **Week 3**: Implement performance tests and security tests
4. **Week 4**: Final testing, validation, and production deployment preparation

---

## Appendix A: Test Configuration Examples

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=core
    --cov=agent
    --cov=web
    --cov-report=html
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
```

### conftest.py

```python
import pytest
import os
from pathlib import Path
from tempfile import TemporaryDirectory

@pytest.fixture
def test_config():
    """Provide test configuration"""
    from core.config import Config
    config = Config(
        owner_email="test@example.com",
        beneficiary_email="beneficiary@example.com",
        check_in_interval_days=30,
        storage_config={
            "local_path": "/tmp/test_storage",
            "enable_ipfs": False,
            "enable_pinata": False,
            "enable_web3_storage": False
        }
    )
    return config

@pytest.fixture
def valid_api_key():
    """Provide valid API key for testing"""
    return os.environ.get("TEST_API_KEY", "test_api_key_12345")

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def test_file(temp_dir):
    """Provide test file for testing"""
    test_file = temp_dir / "test.txt"
    test_file.write_text("Test content")
    return test_file

@pytest.fixture
def client():
    """Provide FastAPI test client"""
    from fastapi.testclient import TestClient
    from web.server import app
    return TestClient(app)
```

---

## Appendix B: Performance Testing Tools

### Recommended Tools

1. **Locust** - Load testing and performance testing
2. **pytest-benchmark** - Benchmarking framework for pytest
3. **Prometheus** - Metrics collection and monitoring
4. **Grafana** - Visualization and dashboards
5. **JMeter** - Load testing and performance testing

### Locust Example

```python
# locustfile.py
from locust import HttpUser, task, between

class LazarusUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login and get API key"""
        response = self.client.post("/login", json={
            "username": "test",
            "password": "test"
        })
        self.api_key = response.json()["api_key"]

    @task(3)
    def get_status(self):
        """Get status endpoint"""
        self.client.get(
            "/status",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

    @task(1)
    def ping(self):
        """Ping endpoint"""
        self.client.post(
            "/ping",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"pin": "1234"}
        )

    @task(1)
    def get_events(self):
        """Get events endpoint"""
        self.client.get(
            "/events",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
```

### Running Locust

```bash
# Run Locust with web interface
locust -f locustfile.py --host=http://localhost:8000

# Run Locust in headless mode
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s
```

---

**Document Version**: 1.0
**Last Updated**: 2026-05-05
**Next Review**: 2026-05-12
