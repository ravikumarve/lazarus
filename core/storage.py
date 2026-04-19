"""
core/storage.py — Enhanced Storage layer for Lazarus Protocol.

Primary:   IPFS via local node (IPFS_API_URL) or Pinata pinning service
Fallback:  Local filesystem copy

Upload strategy (upload_to_ipfs):
    1. Try local IPFS node  → fast, free, no API key needed
    2. Try Pinata           → cloud pinning, survives local node restart
    3. Try Web3.Storage    → decentralized storage alternative
    4. Raise StorageError   → caller falls back to local-only

Download strategy (download_from_ipfs):
    1. Try local IPFS gateway  (localhost:8080/ipfs/<cid>)
    2. Try Cloudflare gateway  (cloudflare-ipfs.com/ipfs/<cid>)
    3. Try ipfs.io gateway     (ipfs.io/ipfs/<cid>)
    4. Try dweb.link gateway   (dweb.link/ipfs/<cid>)
    5. Raise StorageError

Features:
- Retry logic with exponential backoff
- Streaming uploads/downloads for large files
- Progress tracking for large uploads
- Multiple gateway fallback support
- Configurable timeouts and retry limits
- CID validation and verification

Environment variables:
    IPFS_API_URL        Local IPFS API (default: http://127.0.0.1:5001)
    IPFS_GATEWAY_URL    Local IPFS gateway (default: http://127.0.0.1:8080)
    PINATA_API_KEY      Pinata JWT/key
    PINATA_SECRET_KEY   Pinata secret
    WEB3_STORAGE_TOKEN  Web3.Storage API token
    STORAGE_TIMEOUT     Network timeout in seconds (default: 30)
    STORAGE_RETRIES     Maximum retry attempts (default: 3)
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import time
import math
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_IPFS_API_URL = "http://127.0.0.1:5001"
DEFAULT_IPFS_GATEWAY = "http://127.0.0.1:8080"
PINATA_UPLOAD_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
PINATA_TEST_URL = "https://api.pinata.cloud/data/testAuthentication"
WEB3_STORAGE_UPLOAD_URL = "https://api.web3.storage/upload"
WEB3_STORAGE_STATUS_URL = "https://api.web3.storage/status/{cid}"

# Public IPFS gateways tried in order during download
PUBLIC_GATEWAYS = [
    "https://cloudflare-ipfs.com/ipfs/{cid}",
    "https://ipfs.io/ipfs/{cid}",
    "https://dweb.link/ipfs/{cid}",
    "https://gateway.pinata.cloud/ipfs/{cid}",
    "https://{cid}.ipfs.w3s.link",  # Web3.Storage gateway
]

# Configuration defaults
REQUEST_TIMEOUT = int(os.getenv("STORAGE_TIMEOUT", "30"))  # seconds
MAX_RETRIES = int(os.getenv("STORAGE_RETRIES", "3"))
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # 100MB limit for IPFS downloads
CHUNK_SIZE = 8192  # 8KB chunks for streaming

# CID validation patterns
CID_V1_PATTERN = r"^[bB][a-zA-Z2-7]{46,}$"
CID_V0_PATTERN = r"^[Qq][mM][a-zA-Z0-9]{44,}$"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class StorageError(Exception):
    """Raised when all storage backends fail."""

    pass


class CIDValidationError(Exception):
    """Raised when CID validation fails."""

    pass


class UploadError(Exception):
    """Raised when file upload fails."""

    pass


class DownloadError(Exception):
    """Raised when file download fails."""

    pass


# ---------------------------------------------------------------------------
# Data classes for storage configuration
# ---------------------------------------------------------------------------


@dataclass
class StorageConfig:
    """Configuration for storage providers."""

    ipfs_api_url: str = DEFAULT_IPFS_API_URL
    ipfs_gateway_url: str = DEFAULT_IPFS_GATEWAY
    pinata_api_key: Optional[str] = None
    pinata_secret_key: Optional[str] = None
    web3_storage_token: Optional[str] = None
    timeout: int = REQUEST_TIMEOUT
    max_retries: int = MAX_RETRIES
    enable_local_fallback: bool = True


@dataclass
class UploadResult:
    """Result of a successful upload operation."""

    cid: str
    provider: str
    size_bytes: int
    duration_seconds: float
    gateway_urls: List[str]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _retry_with_backoff(
    func, max_retries: int = MAX_RETRIES, timeout: int = REQUEST_TIMEOUT
):
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


def _validate_cid(cid: str) -> bool:
    """Validate that a string is a valid IPFS CID."""
    import re

    # Check for CID v1 (bafy...) or v0 (Qm...)
    if re.match(CID_V1_PATTERN, cid) or re.match(CID_V0_PATTERN, cid):
        return True

    # Check for base36 CID (used by some providers)
    if len(cid) >= 46 and cid.isalnum():
        return True

    return False


def _get_file_size(file_path: Path) -> int:
    """Get file size with proper error handling."""
    try:
        return file_path.stat().st_size
    except OSError as exc:
        raise StorageError(f"Cannot access file size: {exc}") from exc


# ---------------------------------------------------------------------------
# IPFS upload
# ---------------------------------------------------------------------------


def upload_to_ipfs(
    file_path: Path, config: Optional[StorageConfig] = None
) -> UploadResult:
    """
    Upload an encrypted file to IPFS with enhanced reliability.

    Tries providers in order: local node → Pinata → Web3.Storage.
    Returns detailed upload result with timing information.

    Args:
        file_path: Path to the file to upload.
        config:    Optional storage configuration.

    Returns:
        UploadResult with CID, provider, and metadata.

    Raises:
        FileNotFoundError: if file_path does not exist.
        StorageError:      if all upload methods fail.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    config = config or _get_default_config()
    file_size = _get_file_size(file_path)
    start_time = time.time()

    errors: List[str] = []

    # 1. Local IPFS node (fastest, no API keys)
    if ipfs_available(config):
        try:
            cid = _retry_with_backoff(
                lambda: _upload_via_local_node(file_path, config),
                max_retries=config.max_retries,
                timeout=config.timeout,
            )
            duration = time.time() - start_time

            return UploadResult(
                cid=cid,
                provider="local_ipfs",
                size_bytes=file_size,
                duration_seconds=duration,
                gateway_urls=_get_gateway_urls(cid, config),
            )
        except Exception as exc:
            logger.debug("Local IPFS upload failed: %s", exc)
            errors.append(f"local_ipfs: {exc}")
    else:
        errors.append("local_ipfs: node unavailable")

    # 2. Pinata (cloud pinning service)
    if pinata_configured(config):
        try:
            cid = _retry_with_backoff(
                lambda: _upload_via_pinata(file_path, config),
                max_retries=config.max_retries,
                timeout=config.timeout,
            )
            duration = time.time() - start_time

            return UploadResult(
                cid=cid,
                provider="pinata",
                size_bytes=file_size,
                duration_seconds=duration,
                gateway_urls=_get_gateway_urls(cid, config),
            )
        except Exception as exc:
            logger.debug("Pinata upload failed: %s", exc)
            errors.append(f"pinata: {exc}")
    else:
        errors.append("pinata: not configured")

    # 3. Web3.Storage (decentralized alternative)
    if web3_storage_configured(config):
        try:
            cid = _retry_with_backoff(
                lambda: _upload_via_web3_storage(file_path, config),
                max_retries=config.max_retries,
                timeout=config.timeout,
            )
            duration = time.time() - start_time

            return UploadResult(
                cid=cid,
                provider="web3_storage",
                size_bytes=file_size,
                duration_seconds=duration,
                gateway_urls=_get_gateway_urls(cid, config),
            )
        except Exception as exc:
            logger.debug("Web3.Storage upload failed: %s", exc)
            errors.append(f"web3_storage: {exc}")
    else:
        errors.append("web3_storage: not configured")

    raise StorageError(
        f"All IPFS upload methods failed for {file_path.name} ({file_size:,} bytes):\n  "
        + "\n  ".join(errors)
    )


def upload_to_ipfs_with_fallback(
    file_path: Path, config: Optional[StorageConfig] = None
) -> UploadResult:
    """
    Upload to IPFS with automatic fallback to local storage.

    Returns UploadResult even if IPFS fails (uses local fallback).
    """
    config = config or _get_default_config()

    try:
        return upload_to_ipfs(file_path, config)
    except StorageError:
        if not config.enable_local_fallback:
            raise

        # Fallback to local storage
        local_path = store_locally(file_path, Path.home() / ".lazarus" / "backup")
        file_size = _get_file_size(file_path)

        return UploadResult(
            cid="local_fallback",
            provider="local_filesystem",
            size_bytes=file_size,
            duration_seconds=0.0,
            gateway_urls=[str(local_path)],
        )


def _upload_via_local_node(file_path: Path, config: StorageConfig) -> str:
    """
    POST file to local IPFS API using multipart/form-data with streaming.

    Args:
        file_path: Path to the file to upload.
        config:    Storage configuration.

    Returns:
        CID string on success.

    Raises:
        StorageError: on network error or unexpected response.
    """
    import requests

    endpoint = f"{config.ipfs_api_url.rstrip('/')}/api/v0/add"
    file_size = _get_file_size(file_path)

    # Use streaming upload for large files
    def upload_stream():
        with open(file_path, "rb") as f:
            response = requests.post(
                endpoint,
                files={"file": (file_path.name, f, "application/octet-stream")},
                params={"pin": "true", "progress": "false"},
                timeout=config.timeout,
                stream=True,
            )

        if response.status_code != 200:
            raise StorageError(
                f"IPFS API returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        cid = data.get("Hash")

        # Handle different response formats
        if not cid:
            cid_obj = data.get("cid")
            if isinstance(cid_obj, dict):
                cid = cid_obj.get("/")
            elif isinstance(cid_obj, str):
                cid = cid_obj

        if not cid or not _validate_cid(cid):
            raise StorageError(f"IPFS API response missing valid CID: {data}")

        logger.info("Uploaded %s bytes to local IPFS. CID: %s", file_size, cid)
        return cid

    return upload_stream()


def _upload_via_pinata(file_path: Path, config: StorageConfig) -> str:
    """
    Upload to Pinata pinning service with enhanced error handling.

    Args:
        file_path: Path to the file to upload.
        config:    Storage configuration.

    Returns:
        CID string on success.

    Raises:
        StorageError: on auth failure or unexpected response.
    """
    import requests

    if not config.pinata_api_key or not config.pinata_secret_key:
        raise StorageError("Pinata API keys not configured.")

    headers = {
        "pinata_api_key": config.pinata_api_key,
        "pinata_secret_api_key": config.pinata_secret_key,
    }

    file_size = _get_file_size(file_path)

    def upload_stream():
        with open(file_path, "rb") as f:
            response = requests.post(
                PINATA_UPLOAD_URL,
                files={"file": (file_path.name, f, "application/octet-stream")},
                headers=headers,
                timeout=config.timeout,
            )

        if response.status_code == 401:
            raise StorageError("Pinata authentication failed — check API keys.")
        if response.status_code != 200:
            raise StorageError(
                f"Pinata returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        cid = data.get("IpfsHash")
        if not cid or not _validate_cid(cid):
            raise StorageError(f"Pinata response missing valid CID: {data}")

        logger.info("Uploaded %s bytes to Pinata. CID: %s", file_size, cid)
        return cid

    return upload_stream()


def _upload_via_web3_storage(file_path: Path, config: StorageConfig) -> str:
    """
    Upload to Web3.Storage decentralized storage.

    Args:
        file_path: Path to the file to upload.
        config:    Storage configuration.

    Returns:
        CID string on success.

    Raises:
        StorageError: on auth failure or unexpected response.
    """
    import requests

    if not config.web3_storage_token:
        raise StorageError("Web3.Storage token not configured.")

    headers = {
        "Authorization": f"Bearer {config.web3_storage_token}",
        "Content-Type": "application/octet-stream",
    }

    file_size = _get_file_size(file_path)

    def upload_stream():
        with open(file_path, "rb") as f:
            response = requests.post(
                WEB3_STORAGE_UPLOAD_URL,
                headers=headers,
                data=f,
                timeout=config.timeout,
            )

        if response.status_code == 401:
            raise StorageError("Web3.Storage authentication failed — check token.")
        if response.status_code != 200:
            raise StorageError(
                f"Web3.Storage returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        cid = data.get("cid")
        if not cid or not _validate_cid(cid):
            raise StorageError(f"Web3.Storage response missing valid CID: {data}")

        logger.info("Uploaded %s bytes to Web3.Storage. CID: %s", file_size, cid)
        return cid

    return upload_stream()


# ---------------------------------------------------------------------------
# IPFS download
# ---------------------------------------------------------------------------


def download_from_ipfs(
    cid: str, output_path: Path, config: Optional[StorageConfig] = None
) -> Path:
    """
    Download a file from IPFS by CID with enhanced reliability.

    Tries gateways in order with retry logic and progress tracking.

    Args:
        cid:         IPFS content identifier.
        output_path: Where to save the downloaded file.
        config:      Optional storage configuration.

    Returns:
        Path to the downloaded file.

    Raises:
        StorageError: if all gateways fail.
        CIDValidationError: if CID format is invalid.
    """
    import requests

    if not _validate_cid(cid):
        raise CIDValidationError(f"Invalid CID format: {cid}")

    config = config or _get_default_config()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gateways = _get_gateway_urls(cid, config)

    errors: List[str] = []

    for gateway_url in gateways:
        try:
            return _retry_with_backoff(
                lambda: _download_from_gateway(gateway_url, output_path, config),
                max_retries=config.max_retries,
                timeout=config.timeout,
            )
        except Exception as exc:
            errors.append(f"{gateway_url}: {exc}")
            continue

    raise DownloadError(
        f"Failed to download CID {cid} from all gateways:\n  " + "\n  ".join(errors)
    )


def _download_from_gateway(
    gateway_url: str, output_path: Path, config: StorageConfig
) -> Path:
    """Download from a specific gateway with progress tracking."""
    import requests

    # Security check for non-HTTPS gateways
    if (
        not gateway_url.startswith("https://")
        and "127.0.0.1" not in gateway_url
        and "localhost" not in gateway_url
    ):
        logger.warning("Non-HTTPS IPFS gateway detected: %s", gateway_url)

    logger.debug("Trying IPFS gateway: %s", gateway_url)

    response = requests.get(gateway_url, timeout=config.timeout, stream=True)

    if response.status_code != 200:
        raise DownloadError(f"HTTP {response.status_code}: {response.reason}")

    total_bytes = 0
    start_time = time.time()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if not chunk:
                continue

            total_bytes += len(chunk)

            # Security: prevent excessively large downloads
            if total_bytes > MAX_DOWNLOAD_BYTES:
                f.close()
                output_path.unlink(missing_ok=True)
                raise DownloadError(
                    f"Download exceeds size limit ({MAX_DOWNLOAD_BYTES} bytes). "
                    f"Possible malicious content or corrupted CID."
                )

            f.write(chunk)

    duration = time.time() - start_time
    speed = total_bytes / duration if duration > 0 else 0

    logger.info(
        "Downloaded CID via %s: %s bytes in %.1fs (%.1f KB/s)",
        gateway_url,
        total_bytes,
        duration,
        speed / 1024,
    )

    return output_path


# ---------------------------------------------------------------------------
# Local fallback
# ---------------------------------------------------------------------------


def store_locally(file_path: Path, dest_dir: Path) -> Path:
    """
    Copy an encrypted file to a local destination directory.
    Creates dest_dir if it doesn't exist.
    Overwrites if a file with the same name already exists.

    Args:
        file_path: Source file to copy.
        dest_dir:  Destination directory.

    Returns:
        Path to the copied file.

    Raises:
        FileNotFoundError: if file_path does not exist.
    """
    file_path = Path(file_path)
    dest_dir = Path(dest_dir)

    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_path.name

    shutil.copy2(file_path, dest_path)

    # Set secure permissions on the copied file
    try:
        os.chmod(dest_path, 0o600)
    except OSError:
        logger.warning("Could not set secure permissions on %s", dest_path)

    logger.debug("Stored locally: %s → %s", file_path, dest_path)
    return dest_path


def store_locally_with_backup(
    file_path: Path, dest_dir: Path, max_backups: int = 5
) -> Path:
    """
    Store file locally with backup versioning.

    Creates numbered backups if file already exists.
    """
    dest_path = dest_dir / file_path.name

    if dest_path.exists():
        # Create backup with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = (
            dest_dir / f"{file_path.stem}.backup.{timestamp}{file_path.suffix}"
        )
        shutil.copy2(dest_path, backup_path)
        logger.debug("Created backup: %s", backup_path)

        # Clean up old backups
        backups = list(dest_dir.glob(f"{file_path.stem}.backup.*{file_path.suffix}"))
        backups.sort(key=os.path.getmtime)

        for old_backup in backups[:-max_backups]:
            try:
                old_backup.unlink()
                logger.debug("Cleaned up old backup: %s", old_backup)
            except OSError:
                pass

    return store_locally(file_path, dest_dir)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _get_default_config() -> StorageConfig:
    """Get default storage configuration from environment variables."""
    return StorageConfig(
        ipfs_api_url=os.getenv("IPFS_API_URL", DEFAULT_IPFS_API_URL),
        ipfs_gateway_url=os.getenv("IPFS_GATEWAY_URL", DEFAULT_IPFS_GATEWAY),
        pinata_api_key=os.getenv("PINATA_API_KEY"),
        pinata_secret_key=os.getenv("PINATA_SECRET_KEY"),
        web3_storage_token=os.getenv("WEB3_STORAGE_TOKEN"),
        timeout=int(os.getenv("STORAGE_TIMEOUT", str(REQUEST_TIMEOUT))),
        max_retries=int(os.getenv("STORAGE_RETRIES", str(MAX_RETRIES))),
        enable_local_fallback=os.getenv("DISABLE_LOCAL_FALLBACK", "").lower() != "true",
    )


def _get_gateway_urls(cid: str, config: StorageConfig) -> List[str]:
    """Get list of gateway URLs to try for a given CID."""
    gateways = [
        f"{config.ipfs_gateway_url.rstrip('/')}/ipfs/{cid}",
    ] + [gw.format(cid=cid) for gw in PUBLIC_GATEWAYS]

    return gateways


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------


def ipfs_available(config: Optional[StorageConfig] = None) -> bool:
    """
    Ping the local IPFS node. Returns True if reachable within timeout.

    Args:
        config: Optional storage configuration.
    """
    import requests

    config = config or _get_default_config()
    endpoint = f"{config.ipfs_api_url.rstrip('/')}/api/v0/version"

    try:
        response = requests.post(endpoint, timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def pinata_configured(config: Optional[StorageConfig] = None) -> bool:
    """Return True if Pinata API keys are present."""
    config = config or _get_default_config()
    return bool(config.pinata_api_key and config.pinata_secret_key)


def pinata_reachable(config: Optional[StorageConfig] = None) -> bool:
    """
    Test Pinata credentials against their authentication endpoint.
    Returns True only if keys are present AND the API accepts them.
    """
    import requests

    config = config or _get_default_config()

    if not pinata_configured(config):
        return False

    headers = {
        "pinata_api_key": config.pinata_api_key,
        "pinata_secret_api_key": config.pinata_secret_key,
    }

    try:
        r = requests.get(PINATA_TEST_URL, headers=headers, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def web3_storage_configured(config: Optional[StorageConfig] = None) -> bool:
    """Return True if Web3.Storage token is present."""
    config = config or _get_default_config()
    return bool(config.web3_storage_token)


def web3_storage_reachable(config: Optional[StorageConfig] = None) -> bool:
    """
    Test Web3.Storage credentials.
    Returns True only if token is present AND API accepts it.
    """
    import requests

    config = config or _get_default_config()

    if not web3_storage_configured(config):
        return False

    headers = {
        "Authorization": f"Bearer {config.web3_storage_token}",
    }

    try:
        # Test by getting account status
        r = requests.get("https://api.web3.storage/user", headers=headers, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def get_storage_status(config: Optional[StorageConfig] = None) -> Dict[str, Any]:
    """
    Get comprehensive status of all storage providers.
    """
    config = config or _get_default_config()

    return {
        "local_ipfs": {
            "configured": True,  # Always available to try
            "reachable": ipfs_available(config),
            "api_url": config.ipfs_api_url,
        },
        "pinata": {
            "configured": pinata_configured(config),
            "reachable": pinata_reachable(config),
        },
        "web3_storage": {
            "configured": web3_storage_configured(config),
            "reachable": web3_storage_reachable(config),
        },
        "local_fallback": {
            "configured": config.enable_local_fallback,
            "available": True,
        },
        "configuration": {
            "timeout": config.timeout,
            "max_retries": config.max_retries,
        },
    }


def get_bundle_manifest() -> list:
    """
    Get manifest of documents in the bundle.
    Returns list of document information.
    """
    from core.config import LAZARUS_DIR

    bundle_dir = LAZARUS_DIR / "bundle"
    manifest = []

    if bundle_dir.exists():
        for file_path in bundle_dir.glob("*"):
            if file_path.is_file():
                manifest.append(
                    {
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime,
                        "type": file_path.suffix.lstrip(".").upper() or "OTHER",
                    }
                )

    return manifest


def verify_cid_content(
    cid: str, expected_size: int, config: Optional[StorageConfig] = None
) -> bool:
    """
    Verify that content at CID matches expected size and is accessible.

    This helps prevent issues with partial uploads or corrupted content.
    """
    import requests

    config = config or _get_default_config()

    if not _validate_cid(cid):
        raise CIDValidationError(f"Invalid CID format: {cid}")

    # Try to get content length from headers
    gateways = _get_gateway_urls(cid, config)

    for gateway_url in gateways:
        try:
            response = requests.head(gateway_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) == expected_size:
                    logger.info("CID verification passed: %s bytes", expected_size)
                    return True
                elif content_length:
                    logger.warning(
                        "CID size mismatch: expected %s, got %s",
                        expected_size,
                        content_length,
                    )
                    return False
        except Exception as exc:
            logger.debug("CID verification failed for %s: %s", gateway_url, exc)
            continue

    # If HEAD requests don't work, try partial download
    try:
        temp_path = Path("/tmp") / f"verify_{cid[:8]}.tmp"
        downloaded = download_from_ipfs(cid, temp_path, config)
        actual_size = downloaded.stat().st_size

        # Clean up temp file
        try:
            downloaded.unlink()
        except OSError:
            pass

        if actual_size == expected_size:
            logger.info("CID verification passed: %s bytes", expected_size)
            return True
        else:
            logger.warning(
                "CID size mismatch: expected %s, got %s", expected_size, actual_size
            )
            return False

    except Exception as exc:
        logger.warning("CID verification failed: %s", exc)
        return False


def add_document_to_bundle(file_path: str, document_type: str = "OTHER") -> dict:
    """
    Add a document to the bundle.
    Returns information about the added document.
    """
    from core.config import LAZARUS_DIR
    import shutil

    source_path = Path(file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    bundle_dir = LAZARUS_DIR / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    dest_path = bundle_dir / source_path.name
    shutil.copy2(source_path, dest_path)

    return {
        "filename": dest_path.name,
        "size": dest_path.stat().st_size,
        "type": document_type,
        "added": dest_path.stat().st_mtime,
    }


def remove_document_from_bundle(filename: str) -> bool:
    """
    Remove a document from the bundle.
    Returns True if successful, False if file not found.
    """
    from core.config import LAZARUS_DIR

    file_path = LAZARUS_DIR / "bundle" / filename
    if file_path.exists():
        file_path.unlink()
        return True
    return False
