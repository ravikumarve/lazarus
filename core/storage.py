"""
core/storage.py — Storage layer for Lazarus Protocol.

Primary:   IPFS via local node (IPFS_API_URL) or Pinata pinning service
Fallback:  Local filesystem copy

Upload strategy (upload_to_ipfs):
    1. Try local IPFS node  → fast, free, no API key needed
    2. Try Pinata           → cloud pinning, survives local node restart
    3. Raise StorageError   → caller falls back to local-only

Download strategy (download_from_ipfs):
    1. Try local IPFS gateway  (localhost:8080/ipfs/<cid>)
    2. Try Cloudflare gateway  (cloudflare-ipfs.com/ipfs/<cid>)
    3. Try ipfs.io gateway     (ipfs.io/ipfs/<cid>)
    4. Raise StorageError

All network calls use a configurable timeout (default 30s).
Connection errors are caught and re-raised as StorageError so
callers never have to import requests.

Environment variables:
    IPFS_API_URL        Local IPFS API (default: http://127.0.0.1:5001)
    PINATA_API_KEY      Pinata JWT/key
    PINATA_SECRET_KEY   Pinata secret
"""

from __future__ import annotations

import io
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_IPFS_API_URL    = "http://127.0.0.1:5001"
DEFAULT_IPFS_GATEWAY    = "http://127.0.0.1:8080"
PINATA_UPLOAD_URL       = "https://api.pinata.cloud/pinning/pinFileToIPFS"
PINATA_TEST_URL         = "https://api.pinata.cloud/data/testAuthentication"

# Public IPFS gateways tried in order during download
PUBLIC_GATEWAYS = [
    "https://cloudflare-ipfs.com/ipfs/{cid}",
    "https://ipfs.io/ipfs/{cid}",
    "https://gateway.pinata.cloud/ipfs/{cid}",
]

REQUEST_TIMEOUT = 30   # seconds
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # 100MB limit for IPFS downloads


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class StorageError(Exception):
    """Raised when all storage backends fail."""
    pass


# ---------------------------------------------------------------------------
# IPFS upload
# ---------------------------------------------------------------------------

def upload_to_ipfs(file_path: Path) -> str:
    """
    Upload an encrypted file to IPFS.

    Tries local node first, then Pinata. Raises StorageError if both fail.

    Args:
        file_path: Path to the file to upload.

    Returns:
        IPFS CID string (e.g. "QmXyz..." or "bafy...").

    Raises:
        FileNotFoundError: if file_path does not exist.
        StorageError:      if all upload methods fail.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    errors: list[str] = []

    # 1. Local IPFS node
    try:
        cid = _upload_via_local_node(file_path)
        logger.info("Uploaded to IPFS via local node. CID: %s", cid)
        return cid
    except Exception as exc:
        logger.debug("Local IPFS node unavailable: %s", exc)
        errors.append(f"local node: {exc}")

    # 2. Pinata
    if pinata_configured():
        try:
            cid = _upload_via_pinata(file_path)
            logger.info("Uploaded to IPFS via Pinata. CID: %s", cid)
            return cid
        except Exception as exc:
            logger.debug("Pinata upload failed: %s", exc)
            errors.append(f"pinata: {exc}")
    else:
        errors.append("pinata: not configured (PINATA_API_KEY missing)")

    raise StorageError(
        f"All IPFS upload methods failed for {file_path.name}:\n  " +
        "\n  ".join(errors)
    )


def _upload_via_local_node(file_path: Path) -> str:
    """
    POST file to local IPFS API using multipart/form-data.

    Uses IPFS_API_URL env var (default: http://127.0.0.1:5001).
    Returns CID string on success.

    Raises:
        requests.RequestException: on network error.
        StorageError:              on unexpected API response.
    """
    import requests

    api_url  = os.getenv("IPFS_API_URL", DEFAULT_IPFS_API_URL)
    endpoint = f"{api_url.rstrip('/')}/api/v0/add"

    with open(file_path, "rb") as f:
        response = requests.post(
            endpoint,
            files={"file": (file_path.name, f, "application/octet-stream")},
            params={"pin": "true"},
            timeout=REQUEST_TIMEOUT,
        )

    if response.status_code != 200:
        raise StorageError(
            f"IPFS API returned {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    cid = data.get("Hash")
    if not cid:
        cid_obj = data.get("cid")
        if not isinstance(cid_obj, dict):
            raise StorageError(f"IPFS API response missing valid Hash or cid field: {data}")
        cid = cid_obj.get("/")
        if not cid:
            raise StorageError(f"IPFS API response missing CID value in cid field: {data}")

    return cid


def _upload_via_pinata(file_path: Path) -> str:
    """
    Upload to Pinata pinning service.

    Requires PINATA_API_KEY and PINATA_SECRET_KEY env vars.
    Returns CID string on success.

    Raises:
        requests.RequestException: on network error.
        StorageError:              on auth failure or unexpected response.
    """
    import requests

    api_key    = os.getenv("PINATA_API_KEY", "")
    secret_key = os.getenv("PINATA_SECRET_KEY", "")

    if not api_key or not secret_key:
        raise StorageError("Pinata API keys not configured.")

    headers = {
        "pinata_api_key":        api_key,
        "pinata_secret_api_key": secret_key,
    }

    with open(file_path, "rb") as f:
        response = requests.post(
            PINATA_UPLOAD_URL,
            files={"file": (file_path.name, f, "application/octet-stream")},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

    if response.status_code == 401:
        raise StorageError("Pinata authentication failed — check API keys.")
    if response.status_code != 200:
        raise StorageError(
            f"Pinata returned {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    cid  = data.get("IpfsHash")
    if not cid:
        raise StorageError(f"Pinata response missing IpfsHash: {data}")

    return cid


# ---------------------------------------------------------------------------
# IPFS download
# ---------------------------------------------------------------------------

def download_from_ipfs(cid: str, output_path: Path) -> Path:
    """
    Download a file from IPFS by CID.

    Tries local gateway first, then public gateways in sequence.

    Args:
        cid:         IPFS content identifier.
        output_path: Where to save the downloaded file.

    Returns:
        Path to the downloaded file.

    Raises:
        StorageError: if all gateways fail.
    """
    import requests

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gateways = [
        f"{os.getenv('IPFS_API_URL', DEFAULT_IPFS_GATEWAY).rstrip('/')}/ipfs/{cid}",
    ] + [gw.format(cid=cid) for gw in PUBLIC_GATEWAYS]

    for gw in gateways:
        if not gw.startswith('https://') and '127.0.0.1' not in gw and 'localhost' not in gw:
            logger.warning('Non-HTTPS IPFS gateway detected: %s', gw)

    errors: list[str] = []
    for gateway_url in gateways:
        try:
            logger.debug("Trying IPFS gateway: %s", gateway_url)
            response = requests.get(gateway_url, timeout=REQUEST_TIMEOUT, stream=True)
            if response.status_code == 200:
                total_bytes = 0
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        total_bytes += len(chunk)
                        if total_bytes > MAX_DOWNLOAD_BYTES:
                            f.close()
                            output_path.unlink(missing_ok=True)
                            raise StorageError(
                                f"Download exceeds size limit ({MAX_DOWNLOAD_BYTES} bytes). "
                                f"Possible malicious content or corrupted CID."
                            )
                        f.write(chunk)
                logger.info("Downloaded CID %s via %s", cid, gateway_url)
                return output_path
            errors.append(f"{gateway_url}: HTTP {response.status_code}")
        except StorageError:
            raise
        except Exception as exc:
            errors.append(f"{gateway_url}: {exc}")
            continue

    raise StorageError(
        f"Failed to download CID {cid} from all gateways:\n  " +
        "\n  ".join(errors)
    )


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
    dest_dir  = Path(dest_dir)

    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_path.name

    shutil.copy2(file_path, dest_path)
    logger.debug("Stored locally: %s → %s", file_path, dest_path)
    return dest_path


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------

def ipfs_available() -> bool:
    """
    Ping the local IPFS node. Returns True if reachable within timeout.

    Uses IPFS_API_URL env var (default: http://127.0.0.1:5001).
    """
    import requests

    api_url  = os.getenv("IPFS_API_URL", DEFAULT_IPFS_API_URL)
    endpoint = f"{api_url.rstrip('/')}/api/v0/version"

    try:
        response = requests.post(endpoint, timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def pinata_configured() -> bool:
    """Return True if Pinata API keys are present in the environment."""
    return bool(os.getenv("PINATA_API_KEY") and os.getenv("PINATA_SECRET_KEY"))


def pinata_reachable() -> bool:
    """
    Test Pinata credentials against their authentication endpoint.
    Returns True only if keys are present AND the API accepts them.
    """
    import requests

    if not pinata_configured():
        return False

    headers = {
        "pinata_api_key":        os.getenv("PINATA_API_KEY", ""),
        "pinata_secret_api_key": os.getenv("PINATA_SECRET_KEY", ""),
    }
    try:
        r = requests.get(PINATA_TEST_URL, headers=headers, timeout=5)
        return r.status_code == 200
    except Exception:
        return False
