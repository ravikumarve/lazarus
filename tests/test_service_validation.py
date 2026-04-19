"""Validation utility for Lazarus systemd service configuration.

Run with: pytest tests/test_service_validation.py -v
Or standalone: python tests/test_service_validation.py
"""

import os
import sys
import subprocess
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestServiceConfiguration:
    """Validate Lazarus systemd service configuration."""

    def test_python_imports(self):
        """Python should be able to import Lazarus modules."""
        from cli.main import cli  # noqa: F401
        from core.config import load_config  # noqa: F401

    def test_env_example_exists(self):
        """.env.example file should exist."""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists(), ".env.example not found"

    def test_service_file_exists(self):
        """lazarus.service file should exist."""
        service_path = Path(__file__).parent.parent / "lazarus.service"
        assert service_path.exists(), "lazarus.service not found"

    def test_service_file_configuration(self):
        """Service file should contain required configurations."""
        service_path = Path(__file__).parent.parent / "lazarus.service"
        content = service_path.read_text()
        required = ["WorkingDirectory=", "ExecStart="]
        for req in required:
            assert req in content, f"Missing in service file: {req}"

    @pytest.mark.skipif(
        os.name == "nt",
        reason="systemd not available on Windows",
    )
    def test_systemd_available(self):
        """systemd user services should be available."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0 or "not loaded" in result.stderr.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("systemctl not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
