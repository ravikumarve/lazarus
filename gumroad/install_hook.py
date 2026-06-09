"""
gumroad/install_hook.py — Post-install hook for Gumroad license activation.

This module runs after `pip install lazarus-protocol` to prompt users
for their Gumroad license key and validate it.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from gumroad.license_check import verify_license, LicenseStatus, LicenseInfo

logger = logging.getLogger("gumroad.install_hook")


def prompt_for_license() -> Optional[str]:
    """
    Prompt user for Gumroad license key via stdin.

    Returns:
        License key string, or None if input is not available.
    """
    # Skip if not interactive
    if not sys.stdin.isatty():
        return None

    print("\n" + "=" * 60)
    print("  Lazarus Protocol — License Activation")
    print("=" * 60)
    print()
    print("  Enter your Gumroad license key to activate.")
    print("  (Press Enter to skip — you can activate later)")
    print()

    try:
        key = input("  License key: ").strip()
        return key if key else None
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def run_install_hook(
    license_key: Optional[str] = None,
    product_id: Optional[str] = None,
) -> bool:
    """
    Run the install hook: prompt for license and verify it.

    Args:
        license_key: Pre-supplied license key (skips prompt).
        product_id: Gumroad product ID.

    Returns:
        True if license is valid or skipped, False if invalid.
    """
    # Use provided key or prompt for one
    if not license_key:
        license_key = prompt_for_license()

    if not license_key:
        print("  ℹ️  Skipping license activation. Run 'lazarus activate' later.")
        return True

    print(f"  🔑 Verifying license key...")
    result = verify_license(license_key, product_id)

    if result.status == LicenseStatus.VALID:
        print(f"  ✅ License valid! Product: {result.product_name}")
        if result.email:
            print(f"     Licensed to: {result.email}")
        return True
    elif result.status == LicenseStatus.INVALID:
        print(f"  ❌ Invalid license key. Please check and try again.")
        return False
    else:
        print(f"  ⚠️  Could not verify license (network issue). You can activate later.")
        return True


def main() -> int:
    """CLI entry point for the install hook."""
    logging.basicConfig(level=logging.WARNING)

    license_key = os.environ.get("LAZARUS_LICENSE_KEY")
    product_id = os.environ.get("GUMROAD_PRODUCT_ID")

    success = run_install_hook(license_key, product_id)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
