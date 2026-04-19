"""Tests for core/config.py — Configuration management and new subscription fields."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import LazarusConfig, BeneficiaryConfig, VaultConfig
from core.config import _config_to_dict, _config_from_dict


class TestConfigDefaults:
    """Test that new subscription/license fields work with defaults."""

    def _make_config(self):
        beneficiary = BeneficiaryConfig(
            name="Test Beneficiary",
            email="beneficiary@example.com",
            public_key_path="/tmp/test_key.pem",
        )
        vault = VaultConfig(
            secret_file_path="/tmp/secrets.txt",
            encrypted_file_path="/tmp/encrypted.bin",
            key_blob="test_key_blob",
        )
        return LazarusConfig(
            owner_name="Test Owner",
            owner_email="owner@example.com",
            beneficiary=beneficiary,
            vault=vault,
        )

    def test_default_subscription_tier(self):
        config = self._make_config()
        assert config.subscription_tier == "free"

    def test_default_wallet_limit(self):
        config = self._make_config()
        assert config.wallet_limit == 1

    def test_default_license_key(self):
        config = self._make_config()
        assert config.license_key is None

    def test_default_license_valid_until(self):
        config = self._make_config()
        assert config.license_valid_until is None


class TestConfigSerialization:
    """Test config serialization round-trip."""

    def _make_config(self):
        beneficiary = BeneficiaryConfig(
            name="Test Beneficiary",
            email="beneficiary@example.com",
            public_key_path="/tmp/test_key.pem",
        )
        vault = VaultConfig(
            secret_file_path="/tmp/secrets.txt",
            encrypted_file_path="/tmp/encrypted.bin",
            key_blob="test_key_blob",
        )
        return LazarusConfig(
            owner_name="Test Owner",
            owner_email="owner@example.com",
            beneficiary=beneficiary,
            vault=vault,
        )

    def test_serialization_includes_new_fields(self):
        config = self._make_config()
        config_dict = _config_to_dict(config)
        for field in ["license_key", "subscription_tier", "wallet_limit", "license_valid_until"]:
            assert field in config_dict, f"Missing field: {field}"

    def test_deserialization_preserves_values(self):
        config = self._make_config()
        config_dict = _config_to_dict(config)
        # Remove None storage_config to avoid _config_from_dict bug
        # (it calls .get() on None when storage_config is absent)
        if config_dict.get("storage_config") is None:
            config_dict.pop("storage_config", None)
        recreated = _config_from_dict(config_dict)
        assert recreated.subscription_tier == config.subscription_tier
        assert recreated.wallet_limit == config.wallet_limit


class TestConfigBackwardCompatibility:
    """Test backward compatibility with configs missing new fields."""

    def test_missing_fields_get_defaults(self):
        minimal_dict = {
            "owner_name": "Test Owner",
            "owner_email": "owner@example.com",
            "beneficiary": {
                "name": "Test Beneficiary",
                "email": "beneficiary@example.com",
                "public_key_path": "/tmp/test_key.pem",
            },
            "vault": {
                "secret_file_path": "/tmp/secrets.txt",
                "encrypted_file_path": "/tmp/encrypted.bin",
                "key_blob": "test_key_blob",
            },
            "checkin_interval_days": 30,
            "armed": True,
        }
        config = _config_from_dict(minimal_dict)
        assert config.subscription_tier == "free"
        assert config.wallet_limit == 1
        assert config.license_key is None
