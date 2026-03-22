"""
tests/test_config.py — Unit tests for core/config.py
"""

import math
import time
from dataclasses import replace

import pytest

from core.config import (
    BeneficiaryConfig,
    BeneficiaryVault,
    LazarusConfig,
    VaultConfig,
    load_config,
    save_config,
    record_checkin,
    days_since_checkin,
    days_remaining,
    ConfigCorruptedError,
    get_beneficiary_key_blob,
    add_beneficiary_vault,
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


class TestLoadSaveConfig:
    def test_save_and_load_roundtrip(self, tmp_path):
        """Save a config then load it — values should be identical."""
        config = LazarusConfig(
            owner_name="Alice",
            owner_email="alice@example.com",
            beneficiary=BeneficiaryConfig(
                name="Bob",
                email="bob@example.com",
                public_key_path="/path/to/key.pem",
            ),
            vault=make_vault_config(),
            checkin_interval_days=30,
            last_checkin_timestamp=None,
            telegram_chat_id=None,
            armed=True,
        )

        config_path = tmp_path / "config.json"
        save_config(config, config_path=config_path)

        loaded = load_config(config_path=config_path)

        assert loaded.owner_name == config.owner_name
        assert loaded.owner_email == config.owner_email
        assert loaded.beneficiary.name == config.beneficiary.name
        assert loaded.beneficiary.email == config.beneficiary.email
        assert loaded.beneficiary.public_key_path == config.beneficiary.public_key_path
        assert loaded.vault.secret_file_path == config.vault.secret_file_path
        assert loaded.vault.encrypted_file_path == config.vault.encrypted_file_path
        assert len(loaded.vault.beneficiaries) == 1
        assert loaded.vault.beneficiaries[0].beneficiary_name == "Bob"
        assert loaded.vault.beneficiaries[0].key_blob == "dGVzdGtleWJsb2I="
        assert loaded.vault.ipfs_cid == config.vault.ipfs_cid
        assert loaded.checkin_interval_days == config.checkin_interval_days
        assert loaded.last_checkin_timestamp == config.last_checkin_timestamp
        assert loaded.telegram_chat_id == config.telegram_chat_id
        assert loaded.armed == config.armed

    def test_load_raises_if_not_initialised(self, tmp_path):
        """load_config() should raise FileNotFoundError if no config exists."""
        config_path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_config(config_path=config_path)


class TestCheckinHelpers:
    def test_record_checkin_sets_timestamp(self):
        """record_checkin() should set last_checkin_timestamp to current time."""
        config = LazarusConfig(
            owner_name="Test",
            owner_email="test@example.com",
            beneficiary=BeneficiaryConfig(
                name="Ben",
                email="ben@example.com",
                public_key_path="/path/key.pem",
            ),
            vault=make_vault_config(),
            last_checkin_timestamp=None,
        )

        before = time.time()
        updated = record_checkin(config)
        after = time.time()

        assert updated.last_checkin_timestamp is not None
        assert before <= updated.last_checkin_timestamp <= after

    def test_days_since_checkin_zero_after_ping(self):
        """Immediately after ping, days_since_checkin should be near zero."""
        now = time.time()
        config = LazarusConfig(
            owner_name="Test",
            owner_email="test@example.com",
            beneficiary=BeneficiaryConfig(
                name="Ben",
                email="ben@example.com",
                public_key_path="/path/key.pem",
            ),
            vault=make_vault_config(),
            last_checkin_timestamp=now,
        )

        days = days_since_checkin(config)
        assert days < 1

    def test_days_remaining_decreases_over_time(self):
        """With 10 days elapsed and 30 day interval, 20 days should remain."""
        now = time.time()
        ten_days_ago = now - (10 * 86400)
        config = LazarusConfig(
            owner_name="Test",
            owner_email="test@example.com",
            beneficiary=BeneficiaryConfig(
                name="Ben",
                email="ben@example.com",
                public_key_path="/path/key.pem",
            ),
            vault=make_vault_config(),
            checkin_interval_days=30,
            last_checkin_timestamp=ten_days_ago,
        )

        remaining = days_remaining(config)
        assert abs(remaining - 20.0) < 0.01

    def test_days_since_checkin_inf_when_never_checked_in(self):
        """When last_checkin_timestamp is None, days_since_checkin should be infinity."""
        config = LazarusConfig(
            owner_name="Test",
            owner_email="test@example.com",
            beneficiary=BeneficiaryConfig(
                name="Ben",
                email="ben@example.com",
                public_key_path="/path/key.pem",
            ),
            vault=make_vault_config(),
            last_checkin_timestamp=None,
        )

        days = days_since_checkin(config)
        assert math.isinf(days)


class TestMultiBeneficiary:
    def test_get_beneficiary_key_blob(self):
        """Should return key_blob for existing beneficiary, None otherwise."""
        config = LazarusConfig(
            owner_name="Test",
            owner_email="test@example.com",
            beneficiary=BeneficiaryConfig(
                name="Primary",
                email="primary@example.com",
                public_key_path="/path/key.pem",
            ),
            vault=VaultConfig(
                secret_file_path="/s.txt",
                encrypted_file_path="/e.bin",
                beneficiaries=[
                    BeneficiaryVault(beneficiary_name="Alice", key_blob="key_alice"),
                    BeneficiaryVault(beneficiary_name="Bob", key_blob="key_bob"),
                ],
            ),
        )

        assert get_beneficiary_key_blob(config, "Alice") == "key_alice"
        assert get_beneficiary_key_blob(config, "Bob") == "key_bob"
        assert get_beneficiary_key_blob(config, "Charlie") is None

    def test_add_beneficiary_vault(self):
        """Should add a new beneficiary to the vault."""
        config = LazarusConfig(
            owner_name="Test",
            owner_email="test@example.com",
            beneficiary=BeneficiaryConfig(
                name="Primary",
                email="primary@example.com",
                public_key_path="/path/key.pem",
            ),
            vault=VaultConfig(
                secret_file_path="/s.txt",
                encrypted_file_path="/e.bin",
                beneficiaries=[
                    BeneficiaryVault(beneficiary_name="Alice", key_blob="key_alice"),
                ],
            ),
        )

        updated = add_beneficiary_vault(config, "Bob", "key_bob")

        assert len(updated.vault.beneficiaries) == 2
        assert updated.vault.beneficiaries[0].beneficiary_name == "Alice"
        assert updated.vault.beneficiaries[1].beneficiary_name == "Bob"
        assert updated.vault.beneficiaries[1].key_blob == "key_bob"
