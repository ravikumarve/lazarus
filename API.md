# 📚 Lazarus Protocol - API Reference

Complete API reference for Lazarus Protocol. Includes CLI commands, web API endpoints, and configuration management.

## 📋 Table of Contents

- [API Overview](#api-overview)
- [CLI Commands](#cli-commands)
- [Web API](#web-api)
- [Configuration API](#configuration-api)
- [Error Codes](#error-codes)
- [Rate Limiting](#rate-limiting)
- [Authentication](#authentication)

---

## 🌐 API Overview

Lazarus Protocol provides multiple API interfaces:

### API Types

| API Type | Purpose | Authentication | Use Case |
|----------|---------|-----------------|----------|
| **CLI** | Command-line interface | System user | Local administration |
| **Web API** | RESTful HTTP API | None (future: API key) | Programmatic access |
| **Config API** | Python API | N/A | Integration with Python apps |

### API Versioning

- **Current Version**: v1.0.0
- **Version Format**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Backward Compatibility**: Maintained within MAJOR version

### Base URLs

```
CLI: lazarus <command>
Web API: http://localhost:8000/api/v1
Config API: Python module imports
```

---

## 💻 CLI Commands

### Command Overview

```bash
# View all commands
lazarus --help

# View command help
lazarus <command> --help

# View version
lazarus --version
```

### Global Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--version` | `-V` | Show version and exit | - |
| `--help` | `-h` | Show help message | - |
| `--verbose` | `-v` | Enable verbose output | false |
| `--quiet` | `-q` | Suppress output | false |

---

### `lazarus init`

Initialize Lazarus Protocol with setup wizard.

#### Usage

```bash
lazarus init
```

#### Description

Runs the interactive setup wizard to create and configure your vault. The wizard will guide you through:

1. Entering your information (name, email)
2. Configuring beneficiary details
3. Selecting your secret file
4. Setting check-in interval
5. Encrypting and storing your vault

#### Options

None (interactive wizard)

#### Examples

```bash
# Run setup wizard
lazarus init

# Output:
# Enter your full name: John Doe
# Enter your email: john.doe@example.com
# Enter beneficiary's name: Jane Doe
# Enter beneficiary's email: jane.doe@example.com
# Enter path to beneficiary's public key: /home/john/beneficiary_public.pem
# Enter path to your secret file: /home/john/secrets.txt
# Enter check-in interval in days (default: 30): 30
#
# Encrypting your secrets...
# ✓ Setup wizard completed successfully
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Creates `~/.lazarus/` directory if it doesn't exist
- Generates encrypted vault file
- Sets secure file permissions (600)
- Overwrites existing configuration if present

---

### `lazarus ping`

Perform manual check-in to reset countdown timer.

#### Usage

```bash
lazarus ping
```

#### Description

Records a check-in timestamp, resetting the countdown timer. This proves you're alive and prevents the dead man's switch from triggering.

#### Options

None

#### Examples

```bash
# Perform check-in
lazarus ping

# Output:
# ✓ Check-in recorded at 2026-04-27 10:30:00 UTC
# Timer reset - next check-in due in 30.0 days
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Updates `last_checkin_timestamp` in configuration
- Calculates new `days_until_trigger`
- Saves configuration atomically

---

### `lazarus status`

Display vault status and check-in information.

#### Usage

```bash
lazarus status
```

#### Description

Shows current vault status including armed state, days remaining, last check-in, and beneficiary information.

#### Options

None

#### Examples

```bash
# View status
lazarus status

# Output:
# ┌─────────────────────────────────────┐
# │         Lazarus Status               │
# ├─────────────────────────────────────┤
# │ Armed State      │ ✅ Armed         │
# │ Owner            │ John Doe         │
# │                  │ <john@...>       │
# │ Beneficiary      │ Jane Doe         │
# │                  │ <jane@...>       │
# │ Check-in Interval│ 30 days          │
# │ Days Since Ping  │ 5.2 days ago     │
# │ Days Until Trigger│ 24.8 days       │
# │ Last Check-in    │ 2026-04-22...    │
# └─────────────────────────────────────┘
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Output Fields

| Field | Description |
|-------|-------------|
| `Armed State` | Whether switch is armed (✅ Armed / ❌ Disarmed) |
| `Owner` | Your name and email |
| `Beneficiary` | Beneficiary name and email |
| `Check-in Interval` | Days between required check-ins |
| `Days Since Ping` | Days since last check-in |
| `Days Until Trigger` | Days until trigger fires |
| `Last Check-in` | Timestamp of last check-in |

---

### `lazarus agent start`

Start the background heartbeat agent.

#### Usage

```bash
lazarus agent start
```

#### Description

Starts the background agent that monitors check-in status 24/7 and sends alerts.

#### Options

None

#### Examples

```bash
# Start agent
lazarus agent start

# Output:
# Agent starting...
# ✓ Agent started successfully
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Runs as background process (daemon)
- Monitors check-in status continuously
- Sends reminder alerts automatically
- Requires APScheduler dependency

---

### `lazarus agent stop`

Stop the background heartbeat agent.

#### Usage

```bash
lazarus agent stop
```

#### Description

Stops the background agent and terminates monitoring.

#### Options

None

#### Examples

```bash
# Stop agent
lazarus agent stop

# Output:
# Agent stopping...
# ✓ Agent stopped successfully
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Gracefully stops the agent
- Completes current tasks before terminating
- Saves any pending state

---

### `lazarus freeze`

Extend the trigger deadline by N days (panic button).

#### Usage

```bash
lazarus freeze --days <days>
```

#### Description

Extends the check-in interval by the specified number of days, pushing the trigger deadline forward.

#### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--days` | `-d` | Number of days to extend deadline | 30 |

#### Examples

```bash
# Extend deadline by 30 days
lazarus freeze --days 30

# Output:
# ✓ Deadline extended by 30 days
# New check-in interval: 60 days
# Next check-in due in 60.0 days

# Extend deadline by 7 days
lazarus freeze -d 7

# Output:
# ✓ Deadline extended by 7 days
# New check-in interval: 37 days
# Next check-in due in 37.0 days
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Increases `checkin_interval_days` by specified amount
- Does not modify `last_checkin_timestamp`
- Useful for emergencies (travel, no internet access)

---

### `lazarus test-trigger`

Dry run - simulate delivery without actually sending anything.

#### Usage

```bash
lazarus test-trigger
```

#### Description

Simulates the trigger process without actually sending emails or delivering secrets. Useful for testing configuration.

#### Options

None

#### Examples

```bash
# Test trigger
lazarus test-trigger

# Output:
# 🔬 Test trigger (dry run)
#
# 📋 SIMULATION DETAILS
# ============================================================
#
# 👤 Beneficiary:
#    Name:  Jane Doe
#    Email: jane.doe@example.com
#    Public Key: /home/john/beneficiary_public.pem
#
# 👤 Owner:
#    Name:  John Doe
#    Email: john.doe@example.com
#
# 🔒 Vault:
#    Encrypted file: /home/john/.lazarus/encrypted_secrets.bin
#    File size: 1,234 bytes
#    Key blob present: ✅
#    Check-in interval: 30 days
#
# ⏰ Trigger Status:
#    🟢 OK - 24.8 days remaining
#
# 📧 Email Configuration:
#    ✅ SendGrid configured
#
# 📱 Telegram Configuration:
#    ⚪ Telegram not enabled
#
# 📦 What would be sent:
#    1. Email to beneficiary with subject:
#       '[Lazarus] You have received an inheritance from John Doe'
#    2. Attachments:
#       • encrypted_secrets.bin (1,234 bytes)
#       • decryption_kit.zip (standalone decrypt.py + instructions)
#
# ✅ Dry run completed successfully
# ⚠️  This was only a simulation - no actual delivery occurred
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Does not send actual emails
- Does not modify configuration
- Does not disarm switch
- Validates all configuration

---

### `lazarus update-secret`

Replace the encrypted secret file with a new one.

#### Usage

```bash
lazarus update-secret <new_secret_path>
```

#### Description

Re-encrypts a new secret file using the existing beneficiary's public key and updates the vault configuration.

#### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `new_secret_path` | Path to new secret file | Yes |

#### Options

None

#### Examples

```bash
# Update secret file
lazarus update-secret /home/john/new_secrets.txt

# Output:
# Updating secret from: /home/john/new_secrets.txt
# Re-encrypting file with beneficiary's public key...
# ✓ Secret file updated successfully!
#    Original file: /home/john/new_secrets.txt
#    Encrypted file: /home/john/.lazarus/encrypted_secrets.bin
#    File size: 2,345 bytes
#
# ⚠️  Important: The agent will continue using the new encrypted file.
# ⚠️     No restart of the agent is required.
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error occurred |

#### Notes

- Validates new secret file exists and is readable
- Re-encrypts with existing beneficiary public key
- Updates vault configuration
- Optionally uploads to IPFS if previously configured

---

## 🌐 Web API

### API Overview

The Web API provides RESTful endpoints for programmatic access to Lazarus Protocol.

### Base URL

```
http://localhost:8000/api/v1
```

### Content Types

```
Request:  application/json
Response: application/json
```

### Authentication

**Current**: No authentication required

**Future**: API key authentication

```bash
# Future authentication example
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/status
```

---

### GET /api/v1/status

Get current vault status.

#### Request

```bash
curl http://localhost:8000/api/v1/status
```

#### Response

```json
{
  "armed": true,
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
  },
  "checkin_interval_days": 30,
  "days_since_checkin": 5.2,
  "days_until_trigger": 24.8,
  "last_checkin": "2026-04-22T10:30:00Z",
  "trigger_due": false
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `armed` | boolean | Whether switch is armed |
| `owner_name` | string | Owner's full name |
| `owner_email` | string | Owner's email address |
| `beneficiary.name` | string | Beneficiary's full name |
| `beneficiary.email` | string | Beneficiary's email address |
| `checkin_interval_days` | integer | Days between check-ins |
| `days_since_checkin` | float | Days since last check-in |
| `days_until_trigger` | float | Days until trigger fires |
| `last_checkin` | string | ISO 8601 timestamp of last check-in |
| `trigger_due` | boolean | Whether trigger is due |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `404` | Configuration not found |
| `500` | Internal server error |

---

### POST /api/v1/checkin

Perform manual check-in.

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/checkin
```

#### Request Body

None

#### Response

```json
{
  "status": "success",
  "timestamp": 1714234567.123,
  "days_until_trigger": 30.0,
  "message": "Check-in recorded successfully"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Status of operation |
| `timestamp` | float | UTC epoch timestamp |
| `days_until_trigger` | float | Days until trigger fires |
| `message` | string | Human-readable message |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `404` | Configuration not found |
| `500` | Internal server error |

---

### GET /api/v1/config

Get current configuration.

#### Request

```bash
curl http://localhost:8000/api/v1/config
```

#### Response

```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  },
  "checkin_interval_days": 30,
  "armed": true,
  "telegram_chat_id": null
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `owner_name` | string | Owner's full name |
| `owner_email` | string | Owner's email address |
| `beneficiary.name` | string | Beneficiary's full name |
| `beneficiary.email` | string | Beneficiary's email address |
| `beneficiary.public_key_path` | string | Path to beneficiary's public key |
| `checkin_interval_days` | integer | Days between check-ins |
| `armed` | boolean | Whether switch is armed |
| `telegram_chat_id` | string | Telegram chat ID (optional) |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `404` | Configuration not found |
| `500` | Internal server error |

---

### POST /api/v1/config

Update configuration.

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "checkin_interval_days": 60
  }'
```

#### Request Body

```json
{
  "checkin_interval_days": 60
}
```

#### Response

```json
{
  "status": "success",
  "message": "Configuration updated successfully",
  "config": {
    "owner_name": "John Doe",
    "owner_email": "john.doe@example.com",
    "beneficiary": {
      "name": "Jane Doe",
      "email": "jane.doe@example.com"
    },
    "checkin_interval_days": 60,
    "armed": true
  }
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `checkin_interval_days` | integer | No | Days between check-ins |
| `armed` | boolean | No | Whether switch is armed |
| `telegram_chat_id` | string | No | Telegram chat ID |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `400` | Invalid request |
| `404` | Configuration not found |
| `500` | Internal server error |

---

### GET /api/v1/test-trigger

Test trigger (dry run).

#### Request

```bash
curl http://localhost:8000/api/v1/test-trigger
```

#### Response

```json
{
  "status": "dry_run",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
  },
  "vault": {
    "encrypted_file": "/home/john/.lazarus/encrypted_secrets.bin",
    "file_size": 1234,
    "key_blob_present": true,
    "ipfs_cid": "QmXxx..."
  },
  "trigger_status": "not_due",
  "days_remaining": 24.8,
  "email_configured": true,
  "telegram_configured": false
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Status of test |
| `beneficiary.name` | string | Beneficiary's full name |
| `beneficiary.email` | string | Beneficiary's email address |
| `vault.encrypted_file` | string | Path to encrypted file |
| `vault.file_size` | integer | Size of encrypted file in bytes |
| `vault.key_blob_present` | boolean | Whether key blob exists |
| `vault.ipfs_cid` | string | IPFS content identifier |
| `trigger_status` | string | Trigger status |
| `days_remaining` | float | Days until trigger |
| `email_configured` | boolean | Whether email is configured |
| `telegram_configured` | boolean | Whether Telegram is configured |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `404` | Configuration not found |
| `500` | Internal server error |

---

### POST /api/v1/freeze

Extend deadline by N days.

#### Request

```bash
curl -X POST http://localhost:8000/api/v1/freeze \
  -H "Content-Type: application/json" \
  -d '{
    "days": 30
  }'
```

#### Request Body

```json
{
  "days": 30
}
```

#### Response

```json
{
  "status": "success",
  "message": "Deadline extended by 30 days",
  "new_checkin_interval": 60,
  "days_until_trigger": 60.0
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `days` | integer | Yes | Number of days to extend |

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Status of operation |
| `message` | string | Human-readable message |
| `new_checkin_interval` | integer | New check-in interval |
| `days_until_trigger` | float | Days until trigger |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `400` | Invalid request |
| `404` | Configuration not found |
| `500` | Internal server error |

---

### GET /api/v1/health

Health check endpoint.

#### Request

```bash
curl http://localhost:8000/api/v1/health
```

#### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": 1714234567.123,
  "uptime": 86400.0
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Health status |
| `version` | string | API version |
| `timestamp` | float | Current timestamp |
| `uptime` | float | Server uptime in seconds |

#### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `503` | Service unavailable |

---

## 🔧 Configuration API

### Python API Overview

The Configuration API provides Python functions for managing Lazarus Protocol configuration.

### Import

```python
from core.config import (
    load_config,
    save_config,
    validate_config,
    record_checkin,
    days_remaining,
    days_since_checkin,
    is_trigger_due,
    extend_deadline,
    disarm,
    config_exists
)
```

---

### load_config()

Load configuration from disk.

#### Signature

```python
def load_config(config_path: Path = CONFIG_PATH) -> LazarusConfig
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_path` | Path | CONFIG_PATH | Path to configuration file |

#### Returns

`LazarusConfig` - Configuration object

#### Raises

| Exception | Description |
|-----------|-------------|
| `FileNotFoundError` | Configuration file not found |
| `ConfigCorruptedError` | Configuration is corrupted |

#### Example

```python
from core.config import load_config

config = load_config()
print(f"Owner: {config.owner_name}")
print(f"Beneficiary: {config.beneficiary.name}")
```

---

### save_config()

Save configuration to disk.

#### Signature

```python
def save_config(config: LazarusConfig, config_path: Path = CONFIG_PATH) -> None
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |
| `config_path` | Path | CONFIG_PATH | Path to configuration file |

#### Returns

None

#### Example

```python
from core.config import load_config, save_config
from dataclasses import replace

config = load_config()
updated_config = replace(config, checkin_interval_days=60)
save_config(updated_config)
```

---

### validate_config()

Validate configuration for errors.

#### Signature

```python
def validate_config(config: LazarusConfig) -> list[str]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |

#### Returns

`list[str]` - List of error messages (empty if valid)

#### Example

```python
from core.config import load_config, validate_config

config = load_config()
errors = validate_config(config)

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration is valid")
```

---

### record_checkin()

Record a check-in timestamp.

#### Signature

```python
def record_checkin(config: LazarusConfig) -> LazarusConfig
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |

#### Returns

`LazarusConfig` - Updated configuration with new timestamp

#### Example

```python
from core.config import load_config, save_config, record_checkin

config = load_config()
updated_config = record_checkin(config)
save_config(updated_config)
```

---

### days_remaining()

Calculate days until trigger.

#### Signature

```python
def days_remaining(config: LazarusConfig) -> float
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |

#### Returns

`float` - Days until trigger (negative if overdue)

#### Example

```python
from core.config import load_config, days_remaining

config = load_config()
remaining = days_remaining(config)

if remaining > 0:
    print(f"{remaining:.1f} days until trigger")
else:
    print(f"Trigger is {-remaining:.1f} days overdue")
```

---

### days_since_checkin()

Calculate days since last check-in.

#### Signature

```python
def days_since_checkin(config: LazarusConfig) -> float
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |

#### Returns

`float` - Days since last check-in (infinity if never checked in)

#### Example

```python
from core.config import load_config, days_since_checkin

config = load_config()
since = days_since_checkin(config)

if since == float('inf'):
    print("Never checked in")
else:
    print(f"{since:.1f} days since last check-in")
```

---

### is_trigger_due()

Check if trigger is due.

#### Signature

```python
def is_trigger_due(config: LazarusConfig) -> bool
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |

#### Returns

`bool` - True if trigger should fire

#### Example

```python
from core.config import load_config, is_trigger_due

config = load_config()

if is_trigger_due(config):
    print("Trigger is due - vault will release")
else:
    print("Trigger is not due")
```

---

### extend_deadline()

Extend deadline by N days.

#### Signature

```python
def extend_deadline(config: LazarusConfig, extra_days: int) -> LazarusConfig
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |
| `extra_days` | int | Required | Days to extend |

#### Returns

`LazarusConfig` - Updated configuration

#### Example

```python
from core.config import load_config, save_config, extend_deadline

config = load_config()
updated_config = extend_deadline(config, 30)
save_config(updated_config)
```

---

### disarm()

Disarm the switch.

#### Signature

```python
def disarm(config: LazarusConfig) -> LazarusConfig
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | LazarusConfig | Required | Configuration object |

#### Returns

`LazarusConfig` - Updated configuration

#### Example

```python
from core.config import load_config, save_config, disarm

config = load_config()
updated_config = disarm(config)
save_config(updated_config)
```

---

### config_exists()

Check if configuration exists.

#### Signature

```python
def config_exists(config_path: Path = CONFIG_PATH) -> bool
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_path` | Path | CONFIG_PATH | Path to configuration file |

#### Returns

`bool` - True if configuration exists

#### Example

```python
from core.config import config_exists

if config_exists():
    print("Lazarus is initialized")
else:
    print("Lazarus is not initialized")
```

---

## ❌ Error Codes

### HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| `200` | OK | Request successful |
| `400` | Bad Request | Invalid request parameters |
| `404` | Not Found | Resource not found |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error details"
    }
  }
}
```

### Error Codes

| Code | Message | Description |
|------|---------|-------------|
| `CONFIG_NOT_FOUND` | Configuration file not found | Run `lazarus init` |
| `CONFIG_CORRUPTED` | Configuration file is corrupted | Restore from backup |
| `INVALID_EMAIL` | Invalid email address | Check email format |
| `INVALID_KEY` | Invalid public key | Verify key file |
| `ENCRYPTION_FAILED` | Encryption failed | Check file permissions |
| `DECRYPTION_FAILED` | Decryption failed | Verify private key |
| `AGENT_RUNNING` | Agent already running | Stop agent first |
| `AGENT_NOT_RUNNING` | Agent not running | Start agent first |
| `TRIGGER_NOT_DUE` | Trigger not due | Check status |
| `FILE_NOT_FOUND` | File not found | Verify file path |
| `PERMISSION_DENIED` | Permission denied | Check file permissions |

---

## ⚡ Rate Limiting

### Current Status

**No rate limiting** is currently implemented.

### Future Implementation

Rate limiting will be added in future versions:

```bash
# Example rate-limited request
curl -H "X-Rate-Limit: 100" \
  http://localhost:8000/api/v1/status
```

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1714234567
```

---

## 🔐 Authentication

### Current Status

**No authentication** is currently required for API access.

### Future Implementation

API key authentication will be added:

```bash
# Generate API key
lazarus api-key generate

# Use API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/status
```

### API Key Management

```bash
# Generate API key
lazarus api-key generate

# List API keys
lazarus api-key list

# Revoke API key
lazarus api-key revoke <key_id>
```

---

## 📚 Additional Resources

### Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 15 minutes
- [Installation Guide](INSTALLATION.md) - Installation instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [Features Documentation](FEATURES.md) - Feature descriptions

### Support

- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues) - Report bugs
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions) - Ask questions
- Email: ravikumarve@protonmail.com

---

## 🎯 Conclusion

Lazarus Protocol provides comprehensive APIs for all functionality. Whether you prefer CLI commands, RESTful web API, or Python integration, there's an interface that suits your needs.

**Remember:**
- Use appropriate API for your use case
- Handle errors gracefully
- Validate responses
- Keep API keys secure (when implemented)

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
