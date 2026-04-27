"""
core/config.py — User configuration management for Lazarus Protocol.

Config is stored at ~/.lazarus/config.json (chmod 600).
This file holds everything the agent needs to operate:
  - Owner identity + alert email
  - Beneficiary details + path to their RSA public key
  - Vault metadata (encrypted file path, key blob, optional IPFS CID)
  - Check-in interval and last check-in timestamp
  - Armed/disarmed state

Design decisions:
  - Plain JSON so the vault remains readable/recoverable without this codebase.
  - chmod 600 on save — config contains the key_blob, protect it.
  - All timestamp arithmetic uses UTC epoch floats (time.time()).
  - Dataclasses keep the model explicit and IDE-friendly.
  - load_config() / save_config() are the only I/O functions — everything
    else works with in-memory LazarusConfig objects.
"""

from __future__ import annotations

import json
import logging
import math
import os
import stat
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

LAZARUS_DIR = Path.home() / ".lazarus"
CONFIG_PATH = LAZARUS_DIR / "config.json"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class BeneficiaryConfig:
    """Details of the person who receives the secrets if the switch fires."""

    name: str
    email: str
    public_key_path: str  # Absolute path to RSA-4096 public key PEM on disk


@dataclass
class VaultConfig:
    """Metadata about the encrypted secret payload."""

    secret_file_path: str  # Original plaintext path (for reference/re-encryption)
    encrypted_file_path: str  # Path to encrypted_secrets.bin
    key_blob: str  # base64(RSA-encrypted AES key) — never log this
    ipfs_cid: Optional[str] = None  # IPFS CID if the file was uploaded to IPFS


@dataclass
class StorageProviderConfig:
    """Configuration for storage providers."""

    ipfs_api_url: Optional[str] = None
    ipfs_gateway_url: Optional[str] = None
    pinata_api_key: Optional[str] = None
    pinata_secret_key: Optional[str] = None
    web3_storage_token: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    enable_local_fallback: bool = True


@dataclass
class LazarusConfig:
    """Root configuration object. Serialised to ~/.lazarus/config.json."""

    owner_name: str
    owner_email: str
    beneficiary: BeneficiaryConfig
    vault: VaultConfig
    checkin_interval_days: int = 30
    last_checkin_timestamp: Optional[float] = None  # UTC epoch float
    telegram_chat_id: Optional[str] = None
    armed: bool = True
    storage_config: Optional[StorageProviderConfig] = None
    license_key: Optional[str] = None  # Gumroad license key
    subscription_tier: str = "free"  # free/paid tier
    wallet_limit: int = 1  # maximum wallets for tier
    license_valid_until: Optional[float] = None  # UTC timestamp when license expires


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _config_to_dict(config: LazarusConfig) -> dict:
    """Convert a LazarusConfig (with nested dataclasses) to a plain dict."""
    return asdict(config)


def _config_from_dict(d: dict) -> LazarusConfig:
    """
    Reconstruct a LazarusConfig from a plain dict (e.g. loaded from JSON).
    Handles nested BeneficiaryConfig and VaultConfig explicitly so that
    JSON round-trips don't leave them as plain dicts.
    """
    beneficiary = BeneficiaryConfig(**d["beneficiary"])

    vault_d = d["vault"]
    vault = VaultConfig(
        secret_file_path=vault_d["secret_file_path"],
        encrypted_file_path=vault_d["encrypted_file_path"],
        key_blob=vault_d["key_blob"],
        ipfs_cid=vault_d.get("ipfs_cid"),
    )

    # Handle storage configuration (backward compatible)
    storage_config = None
    if "storage_config" in d and d["storage_config"] is not None:
        storage_d = d["storage_config"]
        storage_config = StorageProviderConfig(
            ipfs_api_url=storage_d.get("ipfs_api_url"),
            ipfs_gateway_url=storage_d.get("ipfs_gateway_url"),
            pinata_api_key=storage_d.get("pinata_api_key"),
            pinata_secret_key=storage_d.get("pinata_secret_key"),
            web3_storage_token=storage_d.get("web3_storage_token"),
            timeout=storage_d.get("timeout", 30),
            max_retries=storage_d.get("max_retries", 3),
            enable_local_fallback=storage_d.get("enable_local_fallback", True),
        )

    return LazarusConfig(
        owner_name=d["owner_name"],
        owner_email=d["owner_email"],
        beneficiary=beneficiary,
        vault=vault,
        checkin_interval_days=d.get("checkin_interval_days", 30),
        last_checkin_timestamp=d.get("last_checkin_timestamp"),
        telegram_chat_id=d.get("telegram_chat_id"),
        armed=d.get("armed", True),
        storage_config=storage_config,
        license_key=d.get("license_key"),
        subscription_tier=d.get("subscription_tier", "free"),
        wallet_limit=d.get("wallet_limit", 1),
        license_valid_until=d.get("license_valid_until"),
    )


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------


def load_config(config_path: Path = CONFIG_PATH) -> LazarusConfig:
    """
    Load and deserialise config from disk.

    Args:
        config_path: Override for testing; defaults to ~/.lazarus/config.json.

    Returns:
        LazarusConfig populated from JSON.

    Raises:
        FileNotFoundError: if Lazarus has not been initialised yet.
        ConfigCorruptedError: if the JSON is malformed or missing required fields.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Lazarus config not found at {config_path}.\nRun: python -m lazarus init"
        )

    try:
        raw = config_path.read_text(encoding="utf-8")
        d = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigCorruptedError(
            f"Config file is not valid JSON: {config_path}\n{exc}"
        ) from exc

    try:
        return _config_from_dict(d)
    except (KeyError, TypeError) as exc:
        raise ConfigCorruptedError(
            f"Config file is missing required fields: {exc}\n"
            "It may be from an older version or manually edited incorrectly."
        ) from exc


def save_config(config: LazarusConfig, config_path: Path = CONFIG_PATH) -> None:
    """
    Serialise and persist config to disk.

    - Creates ~/.lazarus/ if it doesn't exist.
    - Writes atomically: to a .tmp file, then renames (avoids partial writes).
    - Sets file permissions to 600 (owner read/write only) on all platforms.
      On Windows: uses pywin32 (preferred) or icacls.exe with proper fallbacks.

    Args:
        config:      The LazarusConfig to persist.
        config_path: Override for testing; defaults to ~/.lazarus/config.json.
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(_config_to_dict(config), indent=2)

    # Atomic write: write to temp file then rename
    tmp_path = config_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(config_path)
    except Exception:
        # Clean up temp file if rename failed
        tmp_path.unlink(missing_ok=True)
        raise

    # Lock down file permissions securely on all platforms
    _secure_file_permissions(config_path)


def _secure_file_permissions(file_path: Path) -> None:
    """
    Set secure file permissions equivalent to chmod 0o600 (read/write for owner only).

    On POSIX systems: uses os.chmod() with 0o600 permissions.
    On Windows systems: attempts to use pywin32 for robust permissions control,
    falls back to icacls.exe if pywin32 is not available, and provides basic
    protection if both methods fail.

    Args:
        file_path: Path to the file to secure
    """
    import platform
    import subprocess
    import logging

    # Set up logging for this module
    logger = logging.getLogger(__name__)

    # Check if file exists before attempting to set permissions
    if not file_path.exists():
        logger.warning(f"Cannot set permissions: file does not exist: {file_path}")
        return

    if platform.system() == "Windows":
        _secure_windows_file_permissions(file_path, logger)
    else:
        # POSIX systems (Linux, macOS): use standard chmod
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
            logger.debug(f"POSIX file permissions set to 0o600: {file_path}")
        except OSError as e:
            logger.warning(f"Could not set POSIX file permissions: {e}")


def _secure_windows_file_permissions(file_path: Path, logger: logging.Logger) -> None:
    """
    Set Windows file permissions equivalent to POSIX 0o600 (read/write for owner only).

    Attempts methods in order:
    1. pywin32 (most robust)
    2. icacls.exe (built-in Windows tool)
    3. Basic file protection (hidden attribute)

    Args:
        file_path: Path to the file to secure
        logger: Logger instance for reporting
    """
    # Try pywin32 first (most robust method)
    if _try_pywin32_permissions(file_path, logger):
        return

    # Fallback to icacls.exe
    if _try_icacls_permissions(file_path, logger):
        return

    # Final fallback: basic protection
    _set_basic_windows_protection(file_path, logger)


def _try_pywin32_permissions(file_path: Path, logger: logging.Logger) -> bool:
    """
    Attempt to set Windows permissions using pywin32.

    Returns:
        True if successful, False if pywin32 is not available or fails
    """
    try:
        import win32security
        import win32api
        import win32con

        # Get the file handle
        file_handle = win32security.CreateFile(
            str(file_path),
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None,
        )

        try:
            # Get current user's SID
            user_sid = win32security.LookupAccountName(None, win32api.GetUserName())[0]

            # Create a security descriptor
            sd = win32security.SECURITY_DESCRIPTOR()
            sd.Initialize()

            # Set DACL (Discretionary Access Control List)
            # Create an ACL that grants full control to owner only
            acl = win32security.ACL()
            acl.Initialize()

            # Add ACE for owner (full control)
            acl.AddAccessAllowedAce(
                win32security.ACL_REVISION, win32con.FILE_ALL_ACCESS, user_sid
            )

            # Set the DACL in the security descriptor
            sd.SetSecurityDescriptorDacl(1, acl, 0)

            # Set the owner in the security descriptor
            sd.SetSecurityDescriptorOwner(user_sid, 0)

            # Apply the security descriptor to the file
            win32security.SetFileSecurity(
                str(file_path),
                win32security.DACL_SECURITY_INFORMATION
                | win32security.OWNER_SECURITY_INFORMATION,
                sd,
            )

            logger.debug(
                f"Windows file permissions set successfully using pywin32: {file_path}"
            )
            return True

        finally:
            win32api.CloseHandle(file_handle)

    except ImportError:
        # pywin32 not installed
        logger.debug("pywin32 not available - falling back to icacls")
        return False

    except Exception as e:
        logger.warning(f"Failed to set Windows permissions using pywin32: {e}")
        return False


def _try_icacls_permissions(file_path: Path, logger: logging.Logger) -> bool:
    """
    Attempt to set Windows permissions using icacls.exe.

    Returns:
        True if successful, False if icacls fails or is not available
    """
    import subprocess

    try:
        # Get current username - try multiple methods for robustness
        username = None
        try:
            username = os.getlogin()
        except (OSError, AttributeError):
            try:
                username = os.environ.get("USERNAME") or os.environ.get("USER")
            except:
                username = "CURRENT_USER"  # Fallback

        # Build icacls command to set owner-only permissions
        # This removes inheritance and grants read/write to current user only
        cmd = [
            "icacls",
            str(file_path),
            "/inheritance:r",  # Remove inherited permissions
            f"/grant:r {username}:(R,W)",  # Grant read/write to current user
            "/remove: Everyone",  # Remove Everyone group
            "/remove: Users",  # Remove Users group
            "/remove: Authenticated Users",  # Remove Authenticated Users
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug(
            f"Windows file permissions set successfully using icacls: {file_path}"
        )
        return True

    except subprocess.CalledProcessError as e:
        # icacls failed - log warning but continue
        logger.warning(
            f"Could not set Windows file permissions via icacls: {e}"
            f"Stdout: {e.stdout if e.stdout else 'None'}"
            f"Stderr: {e.stderr if e.stderr else 'None'}"
            "Falling back to basic file protection."
        )
        return False
    except FileNotFoundError:
        # icacls not available
        logger.warning(
            "icacls.exe not available - cannot set Windows file permissions. "
            "Consider installing Windows Support Tools or using pywin32."
        )
        return False
    except Exception as e:
        # Other unexpected errors
        logger.warning(f"Unexpected error setting Windows permissions with icacls: {e}")
        return False


def _set_basic_windows_protection(file_path: Path, logger: logging.Logger) -> None:
    """
    Set basic Windows protection when advanced methods fail.
    This includes setting hidden attribute and basic file permissions.
    """
    import subprocess

    try:
        # Set hidden attribute
        subprocess.run(["attrib", "+H", str(file_path)], check=False)
        logger.debug(f"Set hidden attribute as basic protection: {file_path}")
    except:
        logger.warning(f"Could not set hidden attribute for: {file_path}")


def config_exists(config_path: Path = CONFIG_PATH) -> bool:
    """Return True if Lazarus has been initialised (config file exists)."""
    return Path(config_path).exists()


# ---------------------------------------------------------------------------
# Check-in helpers
# ---------------------------------------------------------------------------


def record_checkin(config: LazarusConfig) -> LazarusConfig:
    """
    Stamp the current UTC time as the last check-in.

    Does NOT save to disk — caller is responsible for calling save_config().
    This keeps I/O explicit and makes the function easy to test.

    Returns:
        A new LazarusConfig with last_checkin_timestamp updated.
    """
    from dataclasses import replace

    return replace(config, last_checkin_timestamp=time.time())


def days_since_checkin(config: LazarusConfig) -> float:
    """
    Return elapsed days since the last recorded check-in.

    Returns:
        float('inf') if the user has never checked in (fresh install
        that hasn't pinged yet — treat as maximally overdue).
        Otherwise, a non-negative float (0.0 = checked in right now).
    """
    if config.last_checkin_timestamp is None:
        return float("inf")
    elapsed_seconds = time.time() - config.last_checkin_timestamp
    return max(0.0, elapsed_seconds / 86400.0)


def days_remaining(config: LazarusConfig) -> float:
    """
    Return days left before the dead man's switch triggers.

    Returns:
        Positive float = days until trigger.
        0.0 or negative = switch should have already fired.
        float('-inf') if never checked in (already overdue by infinite days).
    """
    since = days_since_checkin(config)
    if math.isinf(since):
        return float("-inf")
    return config.checkin_interval_days - since


def is_trigger_due(config: LazarusConfig) -> bool:
    """Return True if the switch should fire right now."""
    return config.armed and days_remaining(config) <= 0


def disarm(config: LazarusConfig) -> LazarusConfig:
    """
    Disarm the switch after trigger fires.
    Prevents re-triggering on subsequent agent heartbeats.

    Returns updated config — caller must save_config().
    """
    from dataclasses import replace

    return replace(config, armed=False)


def extend_deadline(config: LazarusConfig, extra_days: int) -> LazarusConfig:
    """
    Panic button: push the trigger deadline forward by extra_days.

    Implemented by increasing checkin_interval_days by extra_days.
    This is the cleanest approach: days_remaining() = interval - days_since_checkin(),
    so raising the interval directly extends the deadline without touching the
    last_checkin_timestamp (which would be clamped to 0 by days_since_checkin).

    Example: 28 days elapsed on a 30-day window → 2 days left.
    After extend_deadline(config, 30): interval=60, still 28 days elapsed → 32 days left.

    Returns updated config — caller must save_config().
    """
    from dataclasses import replace

    return replace(
        config, checkin_interval_days=config.checkin_interval_days + extra_days
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_config(config: LazarusConfig) -> list[str]:
    """
    Validate a LazarusConfig for obvious problems.

    Returns:
        List of human-readable error strings.
        Empty list = config is valid.
    """
    errors: list[str] = []

    if not config.owner_name.strip():
        errors.append("owner_name is empty")
    if "@" not in config.owner_email:
        errors.append(f"owner_email looks invalid: {config.owner_email!r}")
    if "@" not in config.beneficiary.email:
        errors.append(f"beneficiary.email looks invalid: {config.beneficiary.email!r}")

    pub_key_path = Path(config.beneficiary.public_key_path)
    if not pub_key_path.exists():
        errors.append(f"beneficiary public key not found: {pub_key_path}")

    enc_path = Path(config.vault.encrypted_file_path)
    if not enc_path.exists():
        errors.append(f"encrypted vault file not found: {enc_path}")

    if not config.vault.key_blob:
        errors.append("vault.key_blob is empty — vault cannot be decrypted")

    if config.checkin_interval_days < 1:
        errors.append(
            f"checkin_interval_days must be >= 1, got {config.checkin_interval_days}"
        )

    return errors


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ConfigCorruptedError(Exception):
    """Raised when the config file exists but cannot be parsed or is missing fields."""

    pass
