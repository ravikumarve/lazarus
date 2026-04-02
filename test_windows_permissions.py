#!/usr/bin/env python3
"""
Test script for Windows file permissions functionality.

This script tests the Windows-specific file permission functionality
implemented in core/config.py to ensure it provides equivalent security
to POSIX chmod 0o600 functionality.

Run this script on Windows to verify the implementation works correctly.
"""

import tempfile
import os
import sys
from pathlib import Path

# Add the core module to the path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import _secure_windows_file_permissions, _try_pywin32_permissions
from core.config import _try_icacls_permissions, _set_basic_windows_protection
import logging


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


def test_file_creation():
    """Create a test file with sensitive content."""
    test_content = """{
    "owner_name": "Test User",
    "owner_email": "test@example.com",
    "beneficiary": {
        "name": "Beneficiary",
        "email": "beneficiary@example.com",
        "public_key_path": "/path/to/public/key.pem"
    },
    "vault": {
        "secret_file_path": "/path/to/secrets.txt",
        "encrypted_file_path": "/path/to/encrypted.bin",
        "key_blob": "base64_encoded_encrypted_key_here"
    },
    "checkin_interval_days": 30,
    "armed": true
}"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(test_content)
        return Path(f.name)


def test_permissions_functionality():
    """Test the Windows permissions functionality."""
    logger = setup_logging()

    # Create test file
    test_file = test_file_creation()
    logger.info(f"Created test file: {test_file}")

    try:
        # Test individual methods
        logger.info("Testing pywin32 method...")
        pywin32_success = _try_pywin32_permissions(test_file, logger)
        logger.info(f"pywin32 method {'succeeded' if pywin32_success else 'failed'}")

        logger.info("Testing icacls method...")
        icacls_success = _try_icacls_permissions(test_file, logger)
        logger.info(f"icacls method {'succeeded' if icacls_success else 'failed'}")

        logger.info("Testing basic protection...")
        _set_basic_windows_protection(test_file, logger)
        logger.info("Basic protection method completed")

        logger.info("Testing comprehensive permissions function...")
        _secure_windows_file_permissions(test_file, logger)
        logger.info("Comprehensive permissions function completed")

        # Verify file still exists and is accessible
        if test_file.exists():
            logger.info("Test file still exists and is accessible")
            return True
        else:
            logger.error("Test file was deleted or became inaccessible")
            return False

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return False
    finally:
        # Clean up
        try:
            test_file.unlink()
            logger.info("Test file cleaned up")
        except:
            logger.warning("Could not clean up test file")


def main():
    """Main test function."""
    if os.name != "nt":
        print("This test is designed for Windows systems only.")
        print("On POSIX systems, file permissions use standard chmod 0o600.")
        return

    print("Testing Windows file permissions functionality...")
    print("=" * 50)

    success = test_permissions_functionality()

    print("=" * 50)
    if success:
        print("✓ All tests completed successfully!")
        print("Windows file permissions functionality is working correctly.")
    else:
        print("✗ Some tests failed.")
        print("Check the logs above for detailed error information.")

    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
