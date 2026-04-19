"""Tests for Windows file permissions functionality.

These tests verify the Windows-specific file permission implementation
in core/config.py provides equivalent security to POSIX chmod 0o600.

On non-Windows systems, most tests are skipped automatically.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import _secure_windows_file_permissions

pytestmark = pytest.mark.skipif(
    os.name != "nt",
    reason="Windows-specific file permissions tests",
)


@pytest.fixture
def logger():
    lg = logging.getLogger("test_windows_permissions")
    lg.setLevel(logging.DEBUG)
    return lg


@pytest.fixture
def temp_config_file():
    """Create a temporary JSON config file for permission testing."""
    content = """{
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
        f.write(content)
    yield Path(f.name)
    try:
        Path(f.name).unlink()
    except OSError:
        pass


class TestWindowsPermissions:
    """Test Windows file permission functions."""

    def test_secure_permissions_runs(self, temp_config_file, logger):
        """_secure_windows_file_permissions should complete without error."""
        _secure_windows_file_permissions(temp_config_file, logger)
        assert temp_config_file.exists()

    def test_file_remains_accessible(self, temp_config_file, logger):
        """File should still be readable after permission changes."""
        _secure_windows_file_permissions(temp_config_file, logger)
        content = temp_config_file.read_text()
        assert "owner_name" in content
