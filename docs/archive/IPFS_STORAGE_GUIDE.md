# Lazarus Protocol - IPFS Storage Guide

## Overview

The enhanced IPFS storage layer provides robust, reliable decentralized storage for Lazarus Protocol vaults. It supports multiple storage providers with automatic fallback and retry logic.

## Features

- **Multi-provider support**: Local IPFS node, Pinata, Web3.Storage
- **Automatic fallback**: Falls back to local storage if IPFS fails
- **Retry logic**: Exponential backoff with configurable retries
- **Progress tracking**: Real-time upload/download progress
- **CID validation**: Ensures content integrity
- **Security**: Size limits and HTTPS enforcement

## Configuration

### Environment Variables

```bash
# IPFS Configuration
IPFS_API_URL="http://127.0.0.1:5001"          # Local IPFS API
IPFS_GATEWAY_URL="http://127.0.0.1:8080"       # Local IPFS gateway

# Pinata Configuration
PINATA_API_KEY="your_pinata_api_key"
PINATA_SECRET_KEY="your_pinata_secret_key"

# Web3.Storage Configuration
WEB3_STORAGE_TOKEN="your_web3_storage_token"

# Performance Configuration
STORAGE_TIMEOUT="30"                          # Timeout in seconds
STORAGE_RETRIES="3"                           # Maximum retry attempts
DISABLE_LOCAL_FALLBACK="false"                 # Disable local fallback
```

### Programmatic Configuration

```python
from core.storage import StorageConfig

config = StorageConfig(
    ipfs_api_url="http://127.0.0.1:5001",
    ipfs_gateway_url="http://127.0.0.1:8080",
    pinata_api_key="your_key",
    pinata_secret_key="your_secret",
    web3_storage_token="your_token",
    timeout=30,
    max_retries=3,
    enable_local_fallback=True
)
```

## Usage

### Basic File Upload

```python
from core.storage import upload_to_ipfs, upload_to_ipfs_with_fallback
from pathlib import Path

# Upload with IPFS fallback
file_path = Path("/path/to/encrypted_secrets.bin")
result = upload_to_ipfs_with_fallback(file_path)

print(f"CID: {result.cid}")
print(f"Provider: {result.provider}")
print(f"Size: {result.size_bytes} bytes")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Gateway URLs: {result.gateway_urls}")
```

### File Download

```python
from core.storage import download_from_ipfs
from pathlib import Path

# Download from IPFS
cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
output_path = Path("/path/to/downloaded_file.bin")

downloaded_path = download_from_ipfs(cid, output_path)
print(f"Downloaded to: {downloaded_path}")
```

### Integrated Encryption with IPFS

```python
from core.encryption import encrypt_and_store_file
from pathlib import Path

# Encrypt and store with IPFS
plaintext_path = Path("/path/to/secrets.txt")
public_key_pem = b"-----BEGIN PUBLIC KEY-----..."
output_dir = Path("/path/to/vault")

encrypted_path, key_blob, ipfs_cid = encrypt_and_store_file(
    plaintext_path,
    public_key_pem,
    output_dir,
    enable_ipfs=True
)

print(f"Encrypted file: {encrypted_path}")
print(f"Key blob: {key_blob}")
print(f"IPFS CID: {ipfs_cid}")  # None if IPFS disabled or failed
```

## Storage Providers

### 1. Local IPFS Node
**Priority**: Primary (fastest, no API keys)
**Requirements**: Local IPFS daemon running
**Configuration**: `IPFS_API_URL`, `IPFS_GATEWAY_URL`

### 2. Pinata
**Priority**: Secondary (cloud pinning)
**Requirements**: Pinata API keys
**Configuration**: `PINATA_API_KEY`, `PINATA_SECRET_KEY`

### 3. Web3.Storage
**Priority**: Tertiary (decentralized)
**Requirements**: Web3.Storage token
**Configuration**: `WEB3_STORAGE_TOKEN`

### 4. Local Fallback
**Priority**: Final (always available)
**Requirements**: Local filesystem access
**Configuration**: Automatic

## Error Handling

The storage layer provides comprehensive error handling:

```python
from core.storage import StorageError, CIDValidationError, DownloadError

try:
    result = upload_to_ipfs(file_path)
except StorageError as e:
    print(f"All storage providers failed: {e}")
except CIDValidationError as e:
    print(f"Invalid CID format: {e}")
except DownloadError as e:
    print(f"Download failed: {e}")
```

## Status Monitoring

```python
from core.storage import get_storage_status

status = get_storage_status()
print("Storage Status:")
print(f"Local IPFS: {status['local_ipfs']['reachable']}")
print(f"Pinata: {status['pinata']['configured']} / {status['pinata']['reachable']}")
print(f"Web3.Storage: {status['web3_storage']['configured']} / {status['web3_storage']['reachable']}")
print(f"Local Fallback: {status['local_fallback']['available']}")
```

## Best Practices

1. **Always enable local fallback**: Ensures vault availability
2. **Use multiple providers**: Redundancy improves reliability
3. **Monitor storage status**: Regular checks prevent silent failures
4. **Set appropriate timeouts**: Balance between reliability and performance
5. **Validate CIDs**: Ensure content integrity after upload

## Troubleshooting

### Common Issues

1. **IPFS node not reachable**
   - Check if IPFS daemon is running: `ipfs daemon`
   - Verify API URL in configuration

2. **Pinata authentication failed**
   - Check API keys are correct
   - Verify Pinata account is active

3. **Web3.Storage token invalid**
   - Regenerate token at web3.storage
   - Check token permissions

4. **Download size limits**
   - Files >100MB are blocked for security
   - Consider splitting large files

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tips

1. **Large files**: Use streaming uploads/downloads
2. **High latency**: Increase timeout settings
3. **Unreliable networks**: Increase retry count
4. **Frequent failures**: Add more storage providers

## Security Considerations

1. **HTTPS enforcement**: Non-HTTPS gateways are warned
2. **Size limits**: Prevents malicious large downloads
3. **CID validation**: Ensures content authenticity
4. **Secure permissions**: Local files have restricted access

---

For more information, see the [core storage implementation](../core/storage.py) and [encryption integration](../core/encryption.py).