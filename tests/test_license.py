"""Tests for core/license.py — Gumroad license validation."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.license import (
    validate_license,
    check_subscription_status,
    get_wallet_limit,
    verify_wallet_count,
    is_license_expired,
    clear_license_cache,
    get_cache_stats,
    LicenseValidationResult,
    SubscriptionTier,
    InvalidLicenseError,
    NetworkError,
    SubscriptionExpiredError,
    WalletLimitExceededError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear license cache before each test."""
    clear_license_cache()
    yield
    clear_license_cache()


MOCK_SUCCESS_RESPONSE = {
    "success": True,
    "purchase": {
        "product_name": "Lazarus Protocol Pro",
        "email": "test@example.com",
        "id": "purchase_123",
        "refunded": False,
        "chargebacked": False,
        "subscription_ended_at": None,
    },
}

MOCK_FAILURE_RESPONSE = {
    "success": False,
    "message": "License key not found",
}


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestLicenseValidation:
    """Test license validation with mock responses."""

    @patch("core.license._call_gumroad_api")
    def test_successful_validation(self, mock_api):
        mock_api.return_value = MOCK_SUCCESS_RESPONSE
        result = validate_license("TEST_LICENSE_KEY")
        assert result.valid is True
        assert result.subscription_tier == SubscriptionTier.PRO
        assert result.wallet_limit == 10
        assert result.user_email == "test@example.com"

    @patch("core.license._call_gumroad_api")
    def test_failed_validation(self, mock_api):
        mock_api.return_value = MOCK_FAILURE_RESPONSE
        result = validate_license("INVALID_LICENSE_KEY")
        assert result.valid is False
        assert "not found" in result.error_message

    @patch("core.license._call_gumroad_api")
    def test_subscription_status_active(self, mock_api):
        mock_api.return_value = MOCK_SUCCESS_RESPONSE
        status = check_subscription_status("TEST_LICENSE_KEY")
        assert status is True

    @patch("core.license._call_gumroad_api")
    def test_subscription_status_invalid(self, mock_api):
        mock_api.return_value = MOCK_FAILURE_RESPONSE
        with pytest.raises(InvalidLicenseError):
            check_subscription_status("INVALID_LICENSE_KEY")

    @patch("core.license._call_gumroad_api")
    def test_wallet_limit(self, mock_api):
        mock_api.return_value = MOCK_SUCCESS_RESPONSE
        limit = get_wallet_limit("TEST_LICENSE_KEY")
        assert limit == 10

    @patch("core.license._call_gumroad_api")
    def test_wallet_count_within_limit(self, mock_api):
        mock_api.return_value = MOCK_SUCCESS_RESPONSE
        # Should not raise
        verify_wallet_count("TEST_LICENSE_KEY", 5)

    @patch("core.license._call_gumroad_api")
    def test_wallet_count_exceeding_limit(self, mock_api):
        mock_api.return_value = MOCK_SUCCESS_RESPONSE
        with pytest.raises(WalletLimitExceededError):
            verify_wallet_count("TEST_LICENSE_KEY", 15)


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestLicenseCache:
    """Test cache functionality."""

    @patch("core.license._call_gumroad_api")
    def test_cache_hit(self, mock_api):
        mock_api.return_value = {
            "success": True,
            "purchase": {
                "product_name": "Lazarus Protocol Basic",
                "email": "test@example.com",
                "id": "purchase_123",
                "refunded": False,
                "chargebacked": False,
                "subscription_ended_at": None,
            },
        }
        result1 = validate_license("CACHED_LICENSE_KEY")
        assert mock_api.call_count == 1

        # Second call should use cache
        result2 = validate_license("CACHED_LICENSE_KEY")
        assert mock_api.call_count == 1  # Should not increase
        assert result1.valid == result2.valid

    @patch("core.license._call_gumroad_api")
    def test_cache_stats(self, mock_api):
        mock_api.return_value = MOCK_SUCCESS_RESPONSE
        validate_license("STATS_LICENSE_KEY")
        stats = get_cache_stats()
        assert stats["cache_size"] >= 1


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestLicenseErrors:
    """Test error handling."""

    @patch("core.license._call_gumroad_api")
    def test_network_error(self, mock_api):
        mock_api.side_effect = NetworkError("API unavailable")
        with pytest.raises(InvalidLicenseError):
            validate_license("TEST_LICENSE_KEY")
