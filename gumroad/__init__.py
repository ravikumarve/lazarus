"""
gumroad — Gumroad license verification and install hooks for Lazarus Protocol.

Provides:
- License key activation and verification via Gumroad API
- Post-install hook for license activation
- CLI interface for license management
"""

from gumroad.install_hook import (
    prompt_for_license,
    run_install_hook,
)
from gumroad.license_check import (
    LicenseInfo,
    LicenseStatus,
    activate_license,
    get_license_status,
    verify_license,
)

__all__ = [
    "verify_license",
    "activate_license",
    "get_license_status",
    "LicenseStatus",
    "LicenseInfo",
    "run_install_hook",
    "prompt_for_license",
]
