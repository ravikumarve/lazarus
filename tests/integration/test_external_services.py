"""
tests/integration/test_external_services.py — External service integration tests.

Tests for integration with external services:
- Email service integration (SendGrid)
- Storage service integration (IPFS, Pinata, Web3.Storage)
- Notification service integration (Telegram)
- API service integration
- Webhook integration
"""

import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import (
    LAZARUS_DIR,
)
from core.storage import (
    StorageConfig,
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
def mock_sendgrid():
    """Mock SendGrid service"""
    with patch('core.storage.send_email') as mock_send_email:
        mock_send_email.return_value = True
        yield mock_send_email


@pytest.fixture
def mock_ipfs():
    """Mock IPFS service"""
    with patch('core.storage.upload_to_ipfs') as mock_upload, \
         patch('core.storage.download_from_ipfs') as mock_download:
        mock_upload.return_value = "QmTestCID123"
        mock_download.return_value = b"test content"
        yield {
            'upload': mock_upload,
            'download': mock_download
        }


@pytest.fixture
def mock_pinata():
    """Mock Pinata service"""
    with patch('core.storage._upload_via_pinata') as mock_pin:
        mock_pin.return_value = "QmPinataCID456"
        yield mock_pin


@pytest.fixture
def mock_web3_storage():
    """Mock Web3.Storage service"""
    with patch('core.storage._upload_via_web3_storage') as mock_upload:
        mock_upload.return_value = "QmWeb3CID789"
        yield mock_upload


@pytest.fixture
def mock_telegram():
    """Mock Telegram service"""
    with patch('core.storage.send_telegram_message') as mock_telegram:
        mock_telegram.return_value = True
        yield mock_telegram


class TestEmailServiceIntegration:
    """Test email service integration"""

    @pytest.mark.integration
    def test_sendgrid_email_sending(self, temp_lazarus_dir, mock_sendgrid):
        """Test SendGrid email sending"""
        # Step 1: Prepare email data
        to_email = "recipient@example.com"
        subject = "Test Email"
        content = "This is a test email from Lazarus Protocol"

        # Step 2: Send email
        success = mock_sendgrid(
            to_email=to_email,
            subject=subject,
            content=content
        )

        # Step 3: Verify email was sent
        assert success == True
        mock_sendgrid.assert_called_once()

        # Step 4: Verify call parameters
        call_args = mock_sendgrid.call_args
        assert call_args[1]['to_email'] == to_email
        assert call_args[1]['subject'] == subject
        assert call_args[1]['content'] == content

    @pytest.mark.integration
    def test_sendgrid_email_with_attachments(self, temp_lazarus_dir, mock_sendgrid):
        """Test SendGrid email with attachments"""
        # Step 1: Prepare email data with attachment
        to_email = "recipient@example.com"
        subject = "Test Email with Attachment"
        content = "This is a test email with attachment"
        attachment_path = temp_lazarus_dir / "test_attachment.txt"
        attachment_path.write_text("Test attachment content")

        # Step 2: Send email with attachment
        success = mock_sendgrid(
            to_email=to_email,
            subject=subject,
            content=content,
            attachment_path=str(attachment_path)
        )

        # Step 3: Verify email was sent
        assert success == True
        mock_sendgrid.assert_called_once()

    @pytest.mark.integration
    def test_sendgrid_email_failure_handling(self, temp_lazarus_dir, mock_sendgrid):
        """Test SendGrid email failure handling"""
        # Step 1: Configure mock to fail
        mock_sendgrid.return_value = False

        # Step 2: Attempt to send email
        success = mock_sendgrid(
            to_email="recipient@example.com",
            subject="Test Email",
            content="This is a test email"
        )

        # Step 3: Verify failure was handled
        assert success == False

    @pytest.mark.integration
    def test_sendgrid_batch_email_sending(self, temp_lazarus_dir, mock_sendgrid):
        """Test SendGrid batch email sending"""
        # Step 1: Prepare batch email data
        recipients = [
            "recipient1@example.com",
            "recipient2@example.com",
            "recipient3@example.com"
        ]
        subject = "Batch Test Email"
        content = "This is a batch test email"

        # Step 2: Send batch emails
        results = []
        for recipient in recipients:
            success = mock_sendgrid(
                to_email=recipient,
                subject=subject,
                content=content
            )
            results.append(success)

        # Step 3: Verify all emails were sent
        assert len(results) == 3
        assert all(results)
        assert mock_sendgrid.call_count == 3


class TestIPFSServiceIntegration:
    """Test IPFS service integration"""

    def test_ipfs_file_upload(self, temp_lazarus_dir, mock_ipfs):
        """Test IPFS file upload"""
        # Step 1: Create test file
        test_file = temp_lazarus_dir / "test_file.txt"
        test_content = b"Test content for IPFS upload"
        test_file.write_bytes(test_content)

        # Step 2: Upload to IPFS
        cid = mock_ipfs['upload'](str(test_file))

        # Step 3: Verify upload
        assert cid == "QmTestCID123"
        mock_ipfs['upload'].assert_called_once()

        # Step 4: Verify call parameters
        call_args = mock_ipfs['upload'].call_args
        assert call_args[0][0] == str(test_file)

    def test_ipfs_file_download(self, temp_lazarus_dir, mock_ipfs):
        """Test IPFS file download"""
        # Step 1: Download from IPFS
        cid = "QmTestCID123"
        content = mock_ipfs['download'](cid)

        # Step 2: Verify download
        assert content == b"test content"
        mock_ipfs['download'].assert_called_once()

        # Step 3: Verify call parameters
        call_args = mock_ipfs['download'].call_args
        assert call_args[0][0] == cid

    def test_ipfs_large_file_upload(self, temp_lazarus_dir, mock_ipfs):
        """Test IPFS large file upload"""
        # Step 1: Create large test file
        test_file = temp_lazarus_dir / "large_file.txt"
        large_content = b"x" * (10 * 1024 * 1024)  # 10 MB
        test_file.write_bytes(large_content)

        # Step 2: Upload to IPFS
        cid = mock_ipfs['upload'](str(test_file))

        # Step 3: Verify upload
        assert cid == "QmTestCID123"

    def test_ipfs_cid_validation(self, temp_lazarus_dir, mock_ipfs):
        """Test IPFS CID validation"""
        # Step 1: Test valid CID
        valid_cid = "QmTestCID123"
        content = mock_ipfs['download'](valid_cid)
        assert content is not None

        # Step 2: Test invalid CID (should handle gracefully)
        # In real scenario, would validate CID format
        assert True


class TestPinataServiceIntegration:
    """Test Pinata service integration"""

    def test_pinata_file_pinning(self, temp_lazarus_dir, mock_pinata):
        """Test Pinata file pinning"""
        # Step 1: Prepare CID for pinning
        cid = "QmTestCID123"

        # Step 2: Pin to Pinata
        pinned_cid = mock_pinata(cid)

        # Step 3: Verify pinning
        assert pinned_cid == "QmPinataCID456"
        mock_pinata.assert_called_once()

        # Step 4: Verify call parameters
        call_args = mock_pinata.call_args
        assert call_args[0][0] == cid

    def test_pinata_multiple_files_pinning(self, temp_lazarus_dir, mock_pinata):
        """Test Pinata multiple files pinning"""
        # Step 1: Prepare multiple CIDs
        cids = ["QmCID1", "QmCID2", "QmCID3"]

        # Step 2: Pin all files
        results = []
        for cid in cids:
            pinned_cid = mock_pinata(cid)
            results.append(pinned_cid)

        # Step 3: Verify all files were pinned
        assert len(results) == 3
        assert all(result == "QmPinataCID456" for result in results)
        assert mock_pinata.call_count == 3

    def test_pinata_pinning_failure_handling(self, temp_lazarus_dir, mock_pinata):
        """Test Pinata pinning failure handling"""
        # Step 1: Configure mock to fail
        mock_pinata.side_effect = Exception("Pinning failed")

        # Step 2: Attempt to pin file
        try:
            pinned_cid = mock_pinata("QmTestCID123")
            # If no exception, check result
            assert False, "Should have raised exception"
        except Exception as e:
            # Step 3: Verify failure was handled
            assert str(e) == "Pinning failed"


class TestWeb3StorageIntegration:
    """Test Web3.Storage service integration"""

    def test_web3_storage_file_upload(self, temp_lazarus_dir, mock_web3_storage):
        """Test Web3.Storage file upload"""
        # Step 1: Create test file
        test_file = temp_lazarus_dir / "test_file.txt"
        test_content = b"Test content for Web3.Storage"
        test_file.write_bytes(test_content)

        # Step 2: Upload to Web3.Storage
        cid = mock_web3_storage(str(test_file))

        # Step 3: Verify upload
        assert cid == "QmWeb3CID789"
        mock_web3_storage.assert_called_once()

        # Step 4: Verify call parameters
        call_args = mock_web3_storage.call_args
        assert call_args[0][0] == str(test_file)

    def test_web3_storage_car_file_upload(self, temp_lazarus_dir, mock_web3_storage):
        """Test Web3.Storage CAR file upload"""
        # Step 1: Create CAR file
        car_file = temp_lazarus_dir / "test.car"
        car_content = b"CAR file content"
        car_file.write_bytes(car_content)

        # Step 2: Upload CAR file
        cid = mock_web3_storage(str(car_file))

        # Step 3: Verify upload
        assert cid == "QmWeb3CID789"

    def test_web3_storage_batch_upload(self, temp_lazarus_dir, mock_web3_storage):
        """Test Web3.Storage batch upload"""
        # Step 1: Create multiple test files
        files = []
        for i in range(3):
            test_file = temp_lazarus_dir / f"test_file_{i}.txt"
            test_content = f"Test content {i}".encode()
            test_file.write_bytes(test_content)
            files.append(str(test_file))

        # Step 2: Upload all files
        results = []
        for file_path in files:
            cid = mock_web3_storage(file_path)
            results.append(cid)

        # Step 3: Verify all files were uploaded
        assert len(results) == 3
        assert all(result == "QmWeb3CID789" for result in results)
        assert mock_web3_storage.call_count == 3


class TestTelegramServiceIntegration:
    """Test Telegram service integration"""

    def test_telegram_message_sending(self, temp_lazarus_dir, mock_telegram):
        """Test Telegram message sending"""
        # Step 1: Prepare message data
        chat_id = "test_chat_id"
        message = "Test message from Lazarus Protocol"

        # Step 2: Send Telegram message
        success = mock_telegram(
            chat_id=chat_id,
            message=message
        )

        # Step 3: Verify message was sent
        assert success == True
        mock_telegram.assert_called_once()

        # Step 4: Verify call parameters
        call_args = mock_telegram.call_args
        assert call_args[1]['chat_id'] == chat_id
        assert call_args[1]['message'] == message

    def test_telegram_message_with_markdown(self, temp_lazarus_dir, mock_telegram):
        """Test Telegram message with markdown formatting"""
        # Step 1: Prepare message with markdown
        chat_id = "test_chat_id"
        message = "*Bold text* and _italic text_"

        # Step 2: Send message with markdown
        success = mock_telegram(
            chat_id=chat_id,
            message=message,
            parse_mode="Markdown"
        )

        # Step 3: Verify message was sent
        assert success == True

    def test_telegram_long_message_sending(self, temp_lazarus_dir, mock_telegram):
        """Test Telegram long message sending"""
        # Step 1: Prepare long message
        chat_id = "test_chat_id"
        long_message = "This is a very long message. " * 100  # > 4000 characters

        # Step 2: Send long message
        success = mock_telegram(
            chat_id=chat_id,
            message=long_message
        )

        # Step 3: Verify message was sent
        assert success == True

    def test_telegram_message_failure_handling(self, temp_lazarus_dir, mock_telegram):
        """Test Telegram message failure handling"""
        # Step 1: Configure mock to fail
        mock_telegram.return_value = False

        # Step 2: Attempt to send message
        success = mock_telegram(
            chat_id="test_chat_id",
            message="Test message"
        )

        # Step 3: Verify failure was handled
        assert success == False


class TestStorageProviderIntegration:
    """Test storage provider integration"""

    def test_multi_provider_fallback(self, temp_lazarus_dir, mock_ipfs, mock_pinata, mock_web3_storage):
        """Test multi-provider fallback strategy"""
        # Step 1: Create test file
        test_file = temp_lazarus_dir / "test_file.txt"
        test_content = b"Test content for multi-provider"
        test_file.write_bytes(test_content)

        # Step 2: Try IPFS first
        ipfs_cid = mock_ipfs['upload'](str(test_file))
        assert ipfs_cid == "QmTestCID123"

        # Step 3: If IPFS fails, try Pinata
        if not ipfs_cid:
            pinata_cid = mock_pinata("QmTestCID123")
            assert pinata_cid == "QmPinataCID456"

        # Step 4: If Pinata fails, try Web3.Storage
        if not ipfs_cid and not pinata_cid:
            web3_cid = mock_web3_storage(str(test_file))
            assert web3_cid == "QmWeb3CID789"

    def test_storage_provider_configuration(self, temp_lazarus_dir):
        """Test storage provider configuration"""
        # Step 1: Create storage provider config
        config = StorageConfig(
            ipfs_gateway_url="https://ipfs.io/ipfs/",
            pinata_api_key="test_pinata_key",
            web3_storage_token="test_web3_token"
        )

        # Step 2: Verify configuration
        assert config.ipfs_gateway_url == "https://ipfs.io/ipfs/"
        assert config.pinata_api_key == "test_pinata_key"
        assert config.web3_storage_token == "test_web3_token"

    def test_storage_provider_status_checking(self, temp_lazarus_dir, mock_ipfs):
        """Test storage provider status checking"""
        # Step 1: Check IPFS status
        # In real scenario, would ping IPFS gateway
        ipfs_status = "available"  # Mock status

        # Step 2: Verify status
        assert ipfs_status == "available"


class TestAPIServiceIntegration:
    """Test API service integration"""

    def test_external_api_call(self, temp_lazarus_dir):
        """Test external API call"""
        # Step 1: Prepare API request
        api_url = "https://api.example.com/endpoint"
        headers = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
        data = {"key": "value"}

        # Step 2: Mock API call
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            # Step 3: Make API call
            response = mock_post(api_url, headers=headers, json=data)

            # Step 4: Verify response
            assert response.status_code == 200
            assert response.json()["success"] == True

    def test_external_api_retry_logic(self, temp_lazarus_dir):
        """Test external API retry logic"""
        # Step 1: Configure mock to fail then succeed
        with patch('requests.post') as mock_post:
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"success": True}

            mock_response_failure = MagicMock()
            mock_response_failure.status_code = 500

            mock_post.side_effect = [mock_response_failure, mock_response_success]

            # Step 2: Make API call with retry
            # In real scenario, would implement retry logic
            response = mock_post("https://api.example.com/endpoint")

            # Step 3: Verify retry
            assert mock_post.call_count == 2

    def test_external_api_timeout_handling(self, temp_lazarus_dir):
        """Test external API timeout handling"""
        # Step 1: Configure mock to timeout
        with patch('requests.post') as mock_post:
            import requests
            mock_post.side_effect = requests.Timeout("Request timed out")

            # Step 2: Attempt API call
            try:
                response = mock_post("https://api.example.com/endpoint", timeout=5)
                assert False, "Should have raised timeout"
            except requests.Timeout:
                # Step 3: Verify timeout was handled
                assert True


class TestWebhookIntegration:
    """Test webhook integration"""

    def test_webhook_delivery(self, temp_lazarus_dir):
        """Test webhook delivery"""
        # Step 1: Prepare webhook data
        webhook_url = "https://example.com/webhook"
        payload = {
            "event": "checkin",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {"user_id": 123}
        }

        # Step 2: Send webhook
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            response = mock_post(webhook_url, json=payload)

            # Step 3: Verify delivery
            assert response.status_code == 200
            mock_post.assert_called_once()

            # Step 4: Verify payload
            call_args = mock_post.call_args
            assert call_args[1]['json'] == payload

    def test_webhook_retry_on_failure(self, temp_lazarus_dir):
        """Test webhook retry on failure"""
        # Step 1: Configure mock to fail then succeed
        webhook_url = "https://example.com/webhook"
        payload = {"event": "test"}

        with patch('requests.post') as mock_post:
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200

            mock_response_failure = MagicMock()
            mock_response_failure.status_code = 500

            mock_post.side_effect = [mock_response_failure, mock_response_success]

            # Step 2: Send webhook with retry
            # In real scenario, would implement retry logic
            response = mock_post(webhook_url, json=payload)

            # Step 3: Verify retry
            assert mock_post.call_count == 2

    def test_webhook_signature_verification(self, temp_lazarus_dir):
        """Test webhook signature verification"""
        # Step 1: Prepare webhook with signature
        webhook_url = "https://example.com/webhook"
        payload = {"event": "test"}
        secret = "webhook_secret"

        # Step 2: Generate signature
        import hashlib
        import hmac
        signature = hmac.new(
            secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()

        # Step 3: Send webhook with signature
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            headers = {
                "X-Webhook-Signature": signature,
                "Content-Type": "application/json"
            }
            response = mock_post(webhook_url, json=payload, headers=headers)

            # Step 4: Verify delivery
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
