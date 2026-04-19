"""
core/license.py — Gumroad license validation for Lazarus Protocol.

Handles license key validation, subscription status checking, and wallet limits
via Gumroad's license verification API (api.gumroad.com).

Features:
- License validation via Gumroad API
- Subscription status and wallet limit checking
- License expiration verification
- Network error handling with retry logic
- Basic caching to avoid excessive API calls
- Comprehensive error handling

Environment variables:
    GUMROAD_PRODUCT_ID   Gumroad product ID for validation
    LICENSE_CACHE_TTL     Cache TTL in seconds (default: 3600)
    LICENSE_MAX_RETRIES   Maximum retry attempts (default: 3)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

import requests

logger = logging.getLogger(__name__)

# Defaults
GUMROAD_API_URL = "https://api.gumroad.com/v2/licenses/verify"
DEFAULT_CACHE_TTL = int(os.getenv("LICENSE_CACHE_TTL", "3600"))  # 1 hour
DEFAULT_MAX_RETRIES = int(os.getenv("LICENSE_MAX_RETRIES", "3"))
DEFAULT_TIMEOUT = 30  # seconds


# Subscription tiers
class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Wallet limits by tier
TIER_WALLET_LIMITS = {
    SubscriptionTier.FREE: 1,
    SubscriptionTier.BASIC: 3,
    SubscriptionTier.PRO: 10,
    SubscriptionTier.ENTERPRISE: 50,
}

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class LicenseError(Exception):
    """Base exception for license-related errors."""

    pass


class InvalidLicenseError(LicenseError):
    """Raised when license validation fails."""

    pass


class NetworkError(LicenseError):
    """Raised when network communication fails."""

    pass


class SubscriptionExpiredError(LicenseError):
    """Raised when subscription has expired."""

    pass


class WalletLimitExceededError(LicenseError):
    """Raised when wallet limit is exceeded for tier."""

    pass


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LicenseValidationResult:
    """Result of license validation."""

    valid: bool
    subscription_tier: SubscriptionTier
    wallet_limit: int
    license_valid_until: Optional[float] = None  # UTC timestamp
    user_email: Optional[str] = None
    purchase_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class LicenseCacheEntry:
    """Cache entry for license validation results."""

    result: LicenseValidationResult
    timestamp: float
    expires_at: float


# ---------------------------------------------------------------------------
# Global cache
# ---------------------------------------------------------------------------

_license_cache: Dict[str, LicenseCacheEntry] = {}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _retry_with_backoff(func, max_retries: int = DEFAULT_MAX_RETRIES):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            wait_time = min(2**attempt, 60)  # Exponential backoff, max 60s
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1,
                max_retries,
                exc,
                wait_time,
            )
            time.sleep(wait_time)


def _clear_expired_cache():
    """Clear expired cache entries."""
    global _license_cache
    current_time = time.time()
    _license_cache = {
        key: entry
        for key, entry in _license_cache.items()
        if entry.expires_at > current_time
    }


def _get_from_cache(license_key: str) -> Optional[LicenseValidationResult]:
    """Get license validation result from cache."""
    _clear_expired_cache()
    entry = _license_cache.get(license_key)
    if entry and entry.expires_at > time.time():
        return entry.result
    return None


def _add_to_cache(
    license_key: str, result: LicenseValidationResult, ttl: int = DEFAULT_CACHE_TTL
):
    """Add license validation result to cache."""
    _clear_expired_cache()
    current_time = time.time()
    _license_cache[license_key] = LicenseCacheEntry(
        result=result, timestamp=current_time, expires_at=current_time + ttl
    )


def _clear_cache():
    """Clear the entire license cache."""
    global _license_cache
    _license_cache = {}


# ---------------------------------------------------------------------------
# Gumroad API integration
# ---------------------------------------------------------------------------


def _call_gumroad_api(
    license_key: str, product_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call Gumroad license verification API.

    Args:
        license_key: The license key to validate
        product_id: Gumroad product ID (optional, uses env var if not provided)

    Returns:
        API response as dictionary

    Raises:
        NetworkError: If API call fails
        InvalidLicenseError: If license validation fails
    """
    if product_id is None:
        product_id = os.getenv("GUMROAD_PRODUCT_ID")
        if not product_id:
            raise InvalidLicenseError("GUMROAD_PRODUCT_ID environment variable not set")

    def api_call():
        try:
            response = requests.post(
                GUMROAD_API_URL,
                data={"product_id": product_id, "license_key": license_key},
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Gumroad API request failed: %s", exc)
            raise NetworkError(f"Gumroad API request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            logger.error("Gumroad API response invalid JSON: %s", exc)
            raise NetworkError(
                f"Invalid JSON response from Gumroad API: {exc}"
            ) from exc

    return _retry_with_backoff(api_call)


def _parse_gumroad_response(response: Dict[str, Any]) -> LicenseValidationResult:
    """
    Parse Gumroad API response into LicenseValidationResult.

    Args:
        response: Gumroad API response

    Returns:
        Parsed license validation result

    Raises:
        InvalidLicenseError: If license is invalid or response format is unexpected
    """
    if not response.get("success"):
        error_msg = response.get("message", "License validation failed")
        logger.warning("Gumroad license validation failed: %s", error_msg)
        return LicenseValidationResult(
            valid=False,
            subscription_tier=SubscriptionTier.FREE,
            wallet_limit=TIER_WALLET_LIMITS[SubscriptionTier.FREE],
            error_message=error_msg,
        )

    purchase = response.get("purchase", {})

    # Determine subscription tier based on product name or custom fields
    product_name = purchase.get("product_name", "").lower()
    subscription_tier = SubscriptionTier.FREE

    if "enterprise" in product_name:
        subscription_tier = SubscriptionTier.ENTERPRISE
    elif "pro" in product_name:
        subscription_tier = SubscriptionTier.PRO
    elif "basic" in product_name:
        subscription_tier = SubscriptionTier.BASIC

    # Check if subscription has expired
    refunded = purchase.get("refunded", False)
    chargebacked = purchase.get("chargebacked", False)
    subscription_ended_at = purchase.get("subscription_ended_at")

    if refunded or chargebacked:
        return LicenseValidationResult(
            valid=False,
            subscription_tier=subscription_tier,
            wallet_limit=TIER_WALLET_LIMITS[subscription_tier],
            error_message="License has been refunded or chargebacked",
        )

    # Check subscription end date
    current_time = time.time()
    license_valid_until = None

    if subscription_ended_at:
        try:
            # Gumroad timestamps are in ISO 8601 format
            from datetime import datetime

            ended_at = datetime.fromisoformat(
                subscription_ended_at.replace("Z", "+00:00")
            )
            license_valid_until = ended_at.timestamp()

            if license_valid_until < current_time:
                return LicenseValidationResult(
                    valid=False,
                    subscription_tier=subscription_tier,
                    wallet_limit=TIER_WALLET_LIMITS[subscription_tier],
                    error_message="Subscription has expired",
                    license_valid_until=license_valid_until,
                )
        except (ValueError, TypeError):
            logger.warning(
                "Failed to parse subscription end date: %s", subscription_ended_at
            )

    return LicenseValidationResult(
        valid=True,
        subscription_tier=subscription_tier,
        wallet_limit=TIER_WALLET_LIMITS[subscription_tier],
        license_valid_until=license_valid_until,
        user_email=purchase.get("email"),
        purchase_id=purchase.get("id"),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_license(
    license_key: str, product_id: Optional[str] = None, use_cache: bool = True
) -> LicenseValidationResult:
    """
    Validate a Gumroad license key.

    Args:
        license_key: The license key to validate
        product_id: Gumroad product ID (optional)
        use_cache: Whether to use caching (default: True)

    Returns:
        LicenseValidationResult with validation details

    Raises:
        NetworkError: If API communication fails
        InvalidLicenseError: If license validation fails
    """
    if not license_key or not license_key.strip():
        raise InvalidLicenseError("License key cannot be empty")

    # Check cache first
    if use_cache:
        cached_result = _get_from_cache(license_key)
        if cached_result:
            logger.debug("Using cached license validation result")
            return cached_result

    try:
        response = _call_gumroad_api(license_key, product_id)
        result = _parse_gumroad_response(response)

        # Cache successful validations
        if result.valid and use_cache:
            _add_to_cache(license_key, result)

        return result

    except Exception as exc:
        logger.error("License validation failed: %s", exc)
        raise InvalidLicenseError(f"License validation failed: {exc}") from exc


def check_subscription_status(
    license_key: str, product_id: Optional[str] = None
) -> bool:
    """
    Check if subscription is active and valid.

    Args:
        license_key: The license key to check
        product_id: Gumroad product ID (optional)

    Returns:
        True if subscription is active and valid

    Raises:
        NetworkError: If API communication fails
        InvalidLicenseError: If license validation fails
        SubscriptionExpiredError: If subscription has expired
    """
    result = validate_license(license_key, product_id)

    if not result.valid:
        if result.error_message and "expired" in result.error_message.lower():
            raise SubscriptionExpiredError(result.error_message)
        raise InvalidLicenseError(result.error_message or "License is invalid")

    return True


def get_wallet_limit(license_key: str, product_id: Optional[str] = None) -> int:
    """
    Get wallet limit for the given license key.

    Args:
        license_key: The license key to check
        product_id: Gumroad product ID (optional)

    Returns:
        Maximum number of wallets allowed for this subscription tier

    Raises:
        NetworkError: If API communication fails
        InvalidLicenseError: If license validation fails
    """
    result = validate_license(license_key, product_id)

    if not result.valid:
        raise InvalidLicenseError(result.error_message or "License is invalid")

    return result.wallet_limit


def verify_wallet_count(
    license_key: str, current_wallet_count: int, product_id: Optional[str] = None
) -> bool:
    """
    Verify that current wallet count doesn't exceed license limit.

    Args:
        license_key: The license key to check
        current_wallet_count: Number of wallets currently configured
        product_id: Gumroad product ID (optional)

    Returns:
        True if wallet count is within limits

    Raises:
        NetworkError: If API communication fails
        InvalidLicenseError: If license validation fails
        WalletLimitExceededError: If wallet count exceeds limit
    """
    wallet_limit = get_wallet_limit(license_key, product_id)

    if current_wallet_count >= wallet_limit:
        raise WalletLimitExceededError(
            f"Wallet limit exceeded: {current_wallet_count}/{wallet_limit} wallets. "
            f"Upgrade your subscription to add more wallets."
        )

    return True


def is_license_expired(license_key: str, product_id: Optional[str] = None) -> bool:
    """
    Check if license has expired.

    Args:
        license_key: The license key to check
        product_id: Gumroad product ID (optional)

    Returns:
        True if license has expired, False otherwise

    Raises:
        NetworkError: If API communication fails
    """
    try:
        result = validate_license(license_key, product_id)

        if not result.valid:
            return True

        if result.license_valid_until:
            return result.license_valid_until < time.time()

        return False

    except InvalidLicenseError:
        return True
    except Exception:
        # If we can't determine the status, assume expired for safety
        return True


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def clear_license_cache() -> None:
    """Clear the license validation cache."""
    _clear_cache()


def get_cache_stats() -> Dict[str, Any]:
    """Get license cache statistics."""
    _clear_expired_cache()
    return {
        "cache_size": len(_license_cache),
        "cache_entries": list(_license_cache.keys()),
        "current_time": time.time(),
    }
