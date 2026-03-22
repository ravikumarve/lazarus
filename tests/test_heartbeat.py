"""
tests/test_heartbeat.py — Unit tests for agent/heartbeat.py
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from core.config import (
    BeneficiaryConfig,
    BeneficiaryVault,
    LazarusConfig,
    VaultConfig,
)


def make_config(days_since: float, armed: bool = True) -> LazarusConfig:
    """Helper: create a config with last_checkin set N days ago."""
    last_checkin = time.time() - (days_since * 86400)
    return LazarusConfig(
        owner_name="Test Owner",
        owner_email="owner@example.com",
        beneficiary=BeneficiaryConfig(
            name="Test Beneficiary",
            email="beneficiary@example.com",
            public_key_path="/path/to/key.pem",
        ),
        vault=VaultConfig(
            secret_file_path="/secrets/seed.txt",
            encrypted_file_path="/vault/encrypted.bin",
            beneficiaries=[
                BeneficiaryVault(
                    beneficiary_name="Test Beneficiary",
                    key_blob="dGVzdGtleWJsb2I="
                )
            ],
            ipfs_cid=None,
        ),
        checkin_interval_days=30,
        last_checkin_timestamp=last_checkin,
        telegram_chat_id="123456",
        armed=armed,
    )


class TestEscalationLogic:
    @patch("lazarus.agent.heartbeat.email_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.telegram_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.send_reminder_email")
    @patch("lazarus.agent.heartbeat.send_telegram_alert")
    @patch("lazarus.agent.heartbeat.send_final_warning")
    @patch("lazarus.agent.heartbeat.trigger_delivery")
    def test_no_alert_before_day_20(
        self, mock_trigger, mock_final, mock_telegram, mock_reminder, mock_email_cfg, mock_telegram_cfg
    ):
        """Before day 20, no alerts should be sent."""
        from lazarus.agent.heartbeat import heartbeat_job

        with patch("lazarus.agent.heartbeat.load_config", return_value=make_config(15)):
            heartbeat_job()

        mock_reminder.assert_not_called()
        mock_telegram.assert_not_called()
        mock_final.assert_not_called()
        mock_trigger.assert_not_called()

    @patch("lazarus.agent.heartbeat.email_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.telegram_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.send_reminder_email")
    @patch("lazarus.agent.heartbeat.send_telegram_alert")
    @patch("lazarus.agent.heartbeat.send_final_warning")
    @patch("lazarus.agent.heartbeat.trigger_delivery")
    def test_reminder_email_at_day_20(
        self, mock_trigger, mock_final, mock_telegram, mock_reminder, mock_email_cfg, mock_telegram_cfg
    ):
        """At day 20, reminder email should be sent once."""
        from lazarus.agent.heartbeat import heartbeat_job

        with patch("lazarus.agent.heartbeat.load_config", return_value=make_config(20)):
            heartbeat_job()

        mock_reminder.assert_called_once()
        mock_telegram.assert_not_called()
        mock_final.assert_not_called()
        mock_trigger.assert_not_called()

    @patch("lazarus.agent.heartbeat.email_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.telegram_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.send_reminder_email")
    @patch("lazarus.agent.heartbeat.send_telegram_alert")
    @patch("lazarus.agent.heartbeat.send_final_warning")
    @patch("lazarus.agent.heartbeat.trigger_delivery")
    def test_telegram_alert_at_day_25(
        self, mock_trigger, mock_final, mock_telegram, mock_reminder, mock_email_cfg, mock_telegram_cfg
    ):
        """At day 25, telegram alert should be sent once."""
        from lazarus.agent.heartbeat import heartbeat_job

        with patch("lazarus.agent.heartbeat.load_config", return_value=make_config(25)):
            heartbeat_job()

        mock_reminder.assert_not_called()
        mock_telegram.assert_called_once()
        mock_final.assert_not_called()
        mock_trigger.assert_not_called()

    @patch("lazarus.agent.heartbeat.email_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.telegram_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.send_reminder_email")
    @patch("lazarus.agent.heartbeat.send_telegram_alert")
    @patch("lazarus.agent.heartbeat.send_final_warning")
    @patch("lazarus.agent.heartbeat.trigger_delivery")
    def test_final_warning_at_day_28(
        self, mock_trigger, mock_final, mock_telegram, mock_reminder, mock_email_cfg, mock_telegram_cfg
    ):
        """At day 28, final warning should be sent via email and telegram."""
        from lazarus.agent.heartbeat import heartbeat_job

        with patch("lazarus.agent.heartbeat.load_config", return_value=make_config(28)):
            heartbeat_job()

        mock_reminder.assert_not_called()
        mock_telegram.assert_not_called()
        mock_final.assert_called_once()
        mock_trigger.assert_not_called()

    @patch("lazarus.agent.heartbeat.email_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.telegram_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.send_reminder_email")
    @patch("lazarus.agent.heartbeat.send_telegram_alert")
    @patch("lazarus.agent.heartbeat.send_final_warning")
    @patch("lazarus.agent.heartbeat.trigger_delivery")
    def test_trigger_fires_at_day_30(
        self, mock_trigger, mock_final, mock_telegram, mock_reminder, mock_email_cfg, mock_telegram_cfg
    ):
        """At day 30, trigger_delivery should be called once."""
        from lazarus.agent.heartbeat import heartbeat_job

        with patch("lazarus.agent.heartbeat.load_config", return_value=make_config(30)):
            heartbeat_job()

        mock_reminder.assert_not_called()
        mock_telegram.assert_not_called()
        mock_final.assert_not_called()
        mock_trigger.assert_called_once()

    @patch("lazarus.agent.heartbeat.email_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.telegram_configured", return_value=True)
    @patch("lazarus.agent.heartbeat.send_reminder_email")
    @patch("lazarus.agent.heartbeat.send_telegram_alert")
    @patch("lazarus.agent.heartbeat.send_final_warning")
    @patch("lazarus.agent.heartbeat.trigger_delivery")
    def test_trigger_does_not_double_fire(
        self, mock_trigger, mock_final, mock_telegram, mock_reminder, mock_email_cfg, mock_telegram_cfg
    ):
        """Once triggered and disarmed, should not trigger again."""
        from lazarus.agent.heartbeat import heartbeat_job, _alert_state

        _alert_state.triggered = True
        try:
            with patch("lazarus.agent.heartbeat.load_config", return_value=make_config(30, armed=False)):
                heartbeat_job()

            mock_trigger.assert_not_called()
        finally:
            _alert_state.triggered = False
