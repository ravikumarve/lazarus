"""
gumroad/license_check.py — Gumroad license verification module.

Provides standalone license key verification via Gumroad API,
independent of the core Lazarus license module.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("gumroad.license_check")

GUMROAD_API_URL = "https://api.gumroad.com/v2/licenses/verify"
REQUEST_TIMEOUT = 30


class LicenseStatus(str, Enum):
    """License activation status"""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class LicenseInfo:
    """License information returned from Gumroad API"""
    product_name: str
    license_key: str
    status: LicenseStatus
    email: Optional[str] = None
    purchaser_id: Optional[str] = None
    sale_id: Optional[str] = None
    variants: Optional[Dict[str, str]] = None
    is_subscription: bool = False
    subscription_ended_at: Optional[str] = None
    subscription_cancelled_at: Optional[str] = None
    subscription_failed_at: Optional[str] = None
    refunded: bool = False
    dispute_win: bool = False
    created_at: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


def verify_license(
    license_key: str,
    product_id: Optional[str] = None,
) -> LicenseInfo:
    """
    Verify a license key via Gumroad API.

    Args:
        license_key: The license key to verify.
        product_id: Gumroad product ID (falls back to GUMROAD_PRODUCT_ID env).

    Returns:
        LicenseInfo with status and details.
    """
    product_id = product_id or os.environ.get("GUMROAD_PRODUCT_ID")
    if not product_id:
        return LicenseInfo(
            product_name="unknown",
            license_key=license_key,
            status=LicenseStatus.ERROR,
        )

    try:
        response = requests.post(
            GUMROAD_API_URL,
            json={
                "product_id": product_id,
                "license_key": license_key,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            sale = data.get("sale", {})
            return LicenseInfo(
                product_name=sale.get("product_name", "Lazarus Protocol"),
                license_key=license_key,
                status=LicenseStatus.VALID,
                email=sale.get("email"),
                purchaser_id=sale.get("purchaser_id"),
                sale_id=sale.get("id"),
                variants=sale.get("variants"),
                is_subscription=bool(sale.get("is_subscription")),
                subscription_ended_at=sale.get("subscription_ended_at"),
                subscription_cancelled_at=sale.get("subscription_cancelled_at"),
                subscription_failed_at=sale.get("subscription_failed_at"),
                refunded=bool(sale.get("refunded")),
                dispute_win=bool(sale.get("dispute_win")),
                created_at=sale.get("created_at"),
                custom_fields=sale.get("custom_fields"),
            )
        else:
            return LicenseInfo(
                product_name="unknown",
                license_key=license_key,
                status=LicenseStatus.INVALID,
            )

    except requests.exceptions.Timeout:
        logger.error("Gumroad API timeout")
        return LicenseInfo(
            product_name="unknown",
            license_key=license_key,
            status=LicenseStatus.ERROR,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Gumroad API error: {e}")
        return LicenseInfo(
            product_name="unknown",
            license_key=license_key,
            status=LicenseStatus.ERROR,
        )


def activate_license(
    license_key: str,
    product_id: Optional[str] = None,
) -> LicenseInfo:
    """
    Activate a license key. 
    Alias for verify_license — Gumroad uses verify for both.

    Args:
        license_key: The license key to activate.
        product_id: Gumroad product ID.

    Returns:
        LicenseInfo with status and details.
    """
    return verify_license(license_key, product_id)


def get_license_status(license_key: str) -> LicenseStatus:
    """
    Quick status check for a license key.

    Args:
        license_key: The license key to check.

    Returns:
        LicenseStatus enum value.
    """
    info = verify_license(license_key)
    return info.status
