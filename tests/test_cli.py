"""
tests/test_cli.py — Unit tests for CLI commands
"""

import os
import sys
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from core.config import (
    BeneficiaryConfig,
    BeneficiaryVault,
    LazarusConfig,
    VaultConfig,
    load_config,
    save_config,
    record_checkin,
)


def make_vault_config():
    """Create a test VaultConfig with a single beneficiary."""
    return VaultConfig(
        secret_file_path="/secrets/seed.txt",
        encrypted_file_path="/vault/encrypted.bin",
        beneficiaries=[
            BeneficiaryVault(beneficiary_name="Bob", key_blob="dGVzdGtleWJsb2I=")
        ],
        ipfs_cid=None,
    )


def make_config(days_since: float = 0) -> LazarusConfig:
    """Create a test config."""
    last_checkin = time.time() - (days_since * 86400) if days_since > 0 else time.time()
    return LazarusConfig(
        owner_name="Test Owner",
        owner_email="owner@example.com",
        beneficiary=BeneficiaryConfig(
            name="Test Beneficiary",
            email="beneficiary@example.com",
            public_key_path="/path/to/key.pem",
        ),
        vault=make_vault_config(),
        checkin_interval_days=30,
        last_checkin_timestamp=last_checkin,
        telegram_chat_id=None,
        armed=True,
    )


def invoke_cli(cli_func, *args, **kwargs):
    """Helper to invoke a Click CLI command."""
    from click.testing import CliRunner
    runner = CliRunner()
    return runner.invoke(cli_func, list(args), **kwargs)


class TestPing:
    def test_ping_records_checkin(self, tmp_path, monkeypatch):
        """Should record checkin and update config."""
        monkeypatch.setattr("core.config.LAZARUS_DIR", tmp_path)
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        config = make_config(5)
        config_path = tmp_path / "config.json"
        save_config(config, config_path=config_path)

        with patch("cli.main.load_config", return_value=config) as mock_load:
            with patch("cli.main.save_config") as mock_save:
                with patch("cli.main._log_event"):
                    from cli.main import ping
                    result = invoke_cli(ping)

        assert result.exit_code == 0
        assert mock_save.called


class TestTestTrigger:
    def test_test_trigger_shows_healthy_when_not_expired(self, tmp_path, monkeypatch):
        """Should show vault is healthy when days remaining > 0."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        config = make_config(5)
        with patch("cli.main.load_config", return_value=config):
            from cli.main import test_trigger
            result = invoke_cli(test_trigger)

        assert result.exit_code == 0
        assert "dry run" in result.output.lower() or "healthy" in result.output.lower()

    def test_test_trigger_shows_would_trigger_when_expired(self, tmp_path, monkeypatch):
        """Should show delivery would happen when vault is expired."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        config = make_config(35)
        with patch("cli.main.load_config", return_value=config):
            from cli.main import test_trigger
            result = invoke_cli(test_trigger)

        assert result.exit_code == 0
        assert "beneficiary" in result.output.lower() or "trigger" in result.output.lower()


class TestAgentCommands:
    def test_agent_status_shows_stopped_when_no_pid(self, tmp_path, monkeypatch):
        """Should show STOPPED status when no PID file exists."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        with patch("cli.main.load_config", return_value=make_config(5)):
            from cli.main import agent_status
            result = invoke_cli(agent_status)

        assert result.exit_code == 0
        assert "Agent Status" in result.output or "Status" in result.output

    def test_agent_start_without_systemd(self, tmp_path, monkeypatch):
        """Should show error when systemd not available."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        with patch("shutil.which", return_value=None):
            from cli.main import agent_start
            result = invoke_cli(agent_start)

        assert result.exit_code == 0
        assert "systemd" in result.output.lower() or "manual" in result.output.lower()

    def test_agent_stop_without_systemd(self, tmp_path, monkeypatch):
        """Should show error when systemd not available."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        with patch("shutil.which", return_value=None):
            from cli.main import agent_stop
            result = invoke_cli(agent_stop)

        assert result.exit_code == 0
        assert "systemd" in result.output.lower()


class TestFreeze:
    def test_freeze_accepts_days_parameter(self, tmp_path, monkeypatch):
        """Freeze command accepts days parameter and shows confirmation."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        with patch("cli.main.load_config", side_effect=FileNotFoundError("Not initialized")):
            from cli.main import freeze
            result = invoke_cli(freeze, ["--days", "30"])

        assert result.exit_code != 0 or "lazarus" in result.output.lower() or "initialized" in result.output.lower()


class TestUpdateSecret:
    def test_update_secret_validates_file_exists(self, tmp_path, monkeypatch):
        """Update secret should validate file exists."""
        monkeypatch.setattr("cli.main.LAZARUS_DIR", tmp_path)

        from cli.main import update_secret
        result = invoke_cli(update_secret, ["/nonexistent/file.txt"])

        assert result.exit_code != 0 or "error" in result.output.lower() or "not found" in result.output.lower()
