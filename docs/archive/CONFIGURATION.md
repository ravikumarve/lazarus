# ⚙️ Lazarus Protocol - Configuration Guide

Comprehensive configuration documentation for Lazarus Protocol. Learn about all configuration options, environment variables, and best practices.

## 📋 Table of Contents

- [Configuration Overview](#configuration-overview)
- [Configuration File Structure](#configuration-file-structure)
- [Configuration Options](#configuration-options)
- [Environment Variables](#environment-variables)
- [Setup Wizard](#setup-wizard)
- [Advanced Configuration](#advanced-configuration)
- [Configuration Validation](#configuration-validation)
- [Backup and Restore](#backup-and-restore)
- [Migration Guide](#migration-guide)

---

## 📁 Configuration Overview

### Configuration Location

Lazarus Protocol stores configuration in:

```
~/.lazarus/
├── config.json              # Main configuration file
├── encrypted_secrets.bin    # Encrypted vault file
├── logs/                    # Log files
│   └── lazarus.log
└── temp/                    # Temporary files
```

### Configuration Security

- **File Permissions**: 600 (owner read/write only)
- **Encryption**: Configuration contains encrypted key blob
- **Backup**: Regular backups recommended
- **Validation**: Automatic validation on load

### Configuration Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Lifecycle                    │
└─────────────────────────────────────────────────────────────┘

1. Initial Setup
   └─ Run: lazarus init
   └─ Creates: ~/.lazarus/config.json

2. Regular Operation
   └─ Load: load_config()
   └─ Modify: Various commands
   └─ Save: save_config()

3. Updates
   └─ Edit: Manually or via commands
   └─ Validate: validate_config()
   └─ Save: save_config()

4. Backup
   └─ Archive: tar -czf backup.tar.gz ~/.lazarus/
   └─ Restore: tar -xzf backup.tar.gz -C ~/
```

---

## 📄 Configuration File Structure

### Complete Configuration Example

```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  },
  "vault": {
    "secret_file_path": "/home/john/secrets.txt",
    "encrypted_file_path": "/home/john/.lazarus/encrypted_secrets.bin",
    "key_blob": "base64_encoded_encrypted_aes_key_here",
    "ipfs_cid": "QmXxx... (optional)"
  },
  "checkin_interval_days": 30,
  "last_checkin_timestamp": 1714234567.123,
  "telegram_chat_id": "123456789 (optional)",
  "armed": true,
  "storage_config": {
    "ipfs_api_url": "http://127.0.0.1:5001",
    "ipfs_gateway_url": "http://127.0.0.1:8080",
    "pinata_api_key": "optional_pinata_key",
    "pinata_secret_key": "optional_pinata_secret",
    "web3_storage_token": "optional_web3_token",
    "timeout": 30,
    "max_retries": 3,
    "enable_local_fallback": true
  },
  "license_key": "gumroad_license_key (optional)",
  "subscription_tier": "free",
  "wallet_limit": 1,
  "license_valid_until": 1714234567.123
}
```

### Configuration Sections

#### 1. Owner Information
```json
{
  "owner_name": "Your full name",
  "owner_email": "your.email@example.com"
}
```

**Purpose:** Identifies you as the vault owner

**Requirements:**
- `owner_name`: Non-empty string
- `owner_email`: Valid email format

#### 2. Beneficiary Information
```json
{
  "beneficiary": {
    "name": "Beneficiary full name",
    "email": "beneficiary@example.com",
    "public_key_path": "/path/to/beneficiary_public.pem"
  }
}
```

**Purpose:** Identifies who receives your secrets

**Requirements:**
- `name`: Non-empty string
- `email`: Valid email format
- `public_key_path`: Absolute path to RSA-4096 public key

#### 3. Vault Configuration
```json
{
  "vault": {
    "secret_file_path": "/path/to/original/secrets.txt",
    "encrypted_file_path": "/path/to/encrypted_secrets.bin",
    "key_blob": "base64_encoded_encrypted_key",
    "ipfs_cid": "QmXxx... (optional)"
  }
}
```

**Purpose:** Metadata about your encrypted vault

**Requirements:**
- `secret_file_path`: Path to original plaintext file (reference only)
- `encrypted_file_path`: Path to encrypted vault file
- `key_blob`: Base64-encoded RSA-encrypted AES key
- `ipfs_cid`: Optional IPFS content identifier

#### 4. Check-in Configuration
```json
{
  "checkin_interval_days": 30,
  "last_checkin_timestamp": 1714234567.123
}
```

**Purpose:** Controls dead man's switch timing

**Requirements:**
- `checkin_interval_days`: Integer >= 1
- `last_checkin_timestamp`: UTC epoch timestamp (float)

#### 5. Alert Configuration
```json
{
  "telegram_chat_id": "123456789 (optional)"
}
```

**Purpose:** Additional alert channels

**Requirements:**
- `telegram_chat_id`: Optional Telegram chat ID

#### 6. System State
```json
{
  "armed": true
}
```

**Purpose:** Controls whether dead man's switch is active

**Requirements:**
- `armed`: Boolean (true/false)

#### 7. Storage Configuration
```json
{
  "storage_config": {
    "ipfs_api_url": "http://127.0.0.1:5001",
    "ipfs_gateway_url": "http://127.0.0.1:8080",
    "pinata_api_key": "optional_pinata_key",
    "pinata_secret_key": "optional_pinata_secret",
    "web3_storage_token": "optional_web3_token",
    "timeout": 30,
    "max_retries": 3,
    "enable_local_fallback": true
  }
}
```

**Purpose:** Configures storage providers

**Requirements:**
- All fields optional
- `timeout`: Integer (seconds)
- `max_retries`: Integer
- `enable_local_fallback`: Boolean

#### 8. License Configuration
```json
{
  "license_key": "gumroad_license_key (optional)",
  "subscription_tier": "free",
  "wallet_limit": 1,
  "license_valid_until": 1714234567.123
}
```

**Purpose:** License and subscription management

**Requirements:**
- `license_key`: Optional Gumroad license key
- `subscription_tier`: "free" or "paid"
- `wallet_limit`: Integer >= 1
- `license_valid_until`: UTC epoch timestamp (float)

---

## 🔧 Configuration Options

### Owner Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `owner_name` | string | Yes | - | Your full name |
| `owner_email` | string | Yes | - | Your email address |

**Example:**
```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com"
}
```

### Beneficiary Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `beneficiary.name` | string | Yes | - | Beneficiary's full name |
| `beneficiary.email` | string | Yes | - | Beneficiary's email address |
| `beneficiary.public_key_path` | string | Yes | - | Path to beneficiary's RSA public key |

**Example:**
```json
{
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  }
}
```

### Vault Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `vault.secret_file_path` | string | Yes | - | Path to original secret file |
| `vault.encrypted_file_path` | string | Yes | - | Path to encrypted vault |
| `vault.key_blob` | string | Yes | - | Base64-encoded encrypted key |
| `vault.ipfs_cid` | string | No | null | IPFS content identifier |

**Example:**
```json
{
  "vault": {
    "secret_file_path": "/home/john/secrets.txt",
    "encrypted_file_path": "/home/john/.lazarus/encrypted_secrets.bin",
    "key_blob": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
    "ipfs_cid": "QmXxx..."
  }
}
```

### Check-in Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `checkin_interval_days` | integer | No | 30 | Days between check-ins |
| `last_checkin_timestamp` | float | No | null | Last check-in time (UTC epoch) |

**Example:**
```json
{
  "checkin_interval_days": 30,
  "last_checkin_timestamp": 1714234567.123
}
```

**Recommended Intervals:**
- **7 days**: Paranoid mode (frequent check-ins)
- **30 days**: Balanced mode (recommended)
- **90 days**: Relaxed mode (infrequent check-ins)

### Alert Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `telegram_chat_id` | string | No | null | Telegram chat ID for alerts |

**Example:**
```json
{
  "telegram_chat_id": "123456789"
}
```

### System State Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `armed` | boolean | No | true | Whether dead man's switch is active |

**Example:**
```json
{
  "armed": true
}
```

### Storage Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `storage_config.ipfs_api_url` | string | No | null | IPFS API URL |
| `storage_config.ipfs_gateway_url` | string | No | null | IPFS gateway URL |
| `storage_config.pinata_api_key` | string | No | null | Pinata API key |
| `storage_config.pinata_secret_key` | string | No | null | Pinata secret key |
| `storage_config.web3_storage_token` | string | No | null | Web3.storage token |
| `storage_config.timeout` | integer | No | 30 | Request timeout (seconds) |
| `storage_config.max_retries` | integer | No | 3 | Maximum retry attempts |
| `storage_config.enable_local_fallback` | boolean | No | true | Enable local storage fallback |

**Example:**
```json
{
  "storage_config": {
    "ipfs_api_url": "http://127.0.0.1:5001",
    "ipfs_gateway_url": "http://127.0.0.1:8080",
    "timeout": 30,
    "max_retries": 3,
    "enable_local_fallback": true
  }
}
```

### License Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `license_key` | string | No | null | Gumroad license key |
| `subscription_tier` | string | No | "free" | Subscription tier |
| `wallet_limit` | integer | No | 1 | Maximum wallets |
| `license_valid_until` | float | No | null | License expiry timestamp |

**Example:**
```json
{
  "license_key": "gumroad_license_key",
  "subscription_tier": "paid",
  "wallet_limit": 10,
  "license_valid_until": 1714234567.123
}
```

---

## 🌍 Environment Variables

### Email Alert Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENDGRID_API_KEY` | Yes (for email) | - | SendGrid API key |
| `ALERT_FROM_EMAIL` | Yes (for email) | - | Sender email address |
| `ALERT_TO_EMAIL` | Yes (for email) | - | Recipient email address |

**Example:**
```bash
export SENDGRID_API_KEY="SG.your_actual_api_key_here"
export ALERT_FROM_EMAIL="lazarus@yourdomain.com"
export ALERT_TO_EMAIL="your_personal_email@gmail.com"
```

### Telegram Alert Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes (for Telegram) | - | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Yes (for Telegram) | - | Telegram chat ID |

**Example:**
```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### IPFS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IPFS_API_URL` | No | http://127.0.0.1:5001 | IPFS API URL |
| `PINATA_API_KEY` | No | - | Pinata API key |
| `PINATA_SECRET_KEY` | No | - | Pinata secret key |

**Example:**
```bash
export IPFS_API_URL="http://127.0.0.1:5001"
export PINATA_API_KEY="your_pinata_key"
export PINATA_SECRET_KEY="your_pinata_secret"
```

### SSL/TLS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LAZARUS_SSL_CERT_FILE` | No | - | SSL certificate file path |
| `LAZARUS_SSL_KEY_FILE` | No | - | SSL private key file path |

**Example:**
```bash
export LAZARUS_SSL_CERT_FILE="/etc/letsencrypt/live/yourdomain.com/fullchain.pem"
export LAZARUS_SSL_KEY_FILE="/etc/letsencrypt/live/yourdomain.com/privkey.pem"
```

### Logging Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LAZARUS_LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LAZARUS_LOG_FILE` | No | ~/.lazarus/logs/lazarus.log | Log file path |

**Example:**
```bash
export LAZARUS_LOG_LEVEL="DEBUG"
export LAZARUS_LOG_FILE="/var/log/lazarus/lazarus.log"
```

### System Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LAZARUS_HOME` | No | ~/.lazarus | Lazarus home directory |
| `LAZARUS_HOST` | No | 127.0.0.1 | Web server host |
| `LAZARUS_PORT` | No | 8000 | Web server port |

**Example:**
```bash
export LAZARUS_HOME="/opt/lazarus"
export LAZARUS_HOST="0.0.0.0"
export LAZARUS_PORT="8000"
```

### Setting Environment Variables

#### Linux/macOS

```bash
# Temporary (current session)
export SENDGRID_API_KEY="your_key"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export SENDGRID_API_KEY="your_key"' >> ~/.bashrc
source ~/.bashrc

# Using .env file
cp .env.example .env
nano .env
# Add your variables to .env
```

#### Windows

```powershell
# Temporary (current session)
$env:SENDGRID_API_KEY="your_key"

# Permanent (system-wide)
setx SENDGRID_API_KEY "your_key"

# Using .env file
# Copy .env.example to .env and edit
```

---

## 🧙 Setup Wizard

### Running the Setup Wizard

```bash
# Start the setup wizard
lazarus init
```

### Setup Wizard Flow

#### Step 1: Owner Information

```
Enter your full name: John Doe
Enter your email: john.doe@example.com
```

**Validation:**
- Name cannot be empty
- Email must contain @ symbol

#### Step 2: Beneficiary Information

```
Enter beneficiary's name: Jane Doe
Enter beneficiary's email: jane.doe@example.com
Enter path to beneficiary's public key: /home/john/beneficiary_public.pem
```

**Validation:**
- Name cannot be empty
- Email must contain @ symbol
- Public key file must exist
- Public key must be valid RSA-4096

#### Step 3: Secret File Selection

```
Enter path to your secret file: /home/john/secrets.txt
```

**Validation:**
- File must exist
- File must be readable
- File must not be empty

#### Step 4: Check-in Interval

```
Enter check-in interval in days (default: 30): 30
```

**Validation:**
- Must be integer >= 1
- Recommended: 7, 30, or 90 days

#### Step 5: Encryption Confirmation

```
Encrypting your secrets...
✓ Encryption complete
✓ Vault created at ~/.lazarus/encrypted_secrets.bin
✓ Configuration saved at ~/.lazarus/config.json
```

### Re-running the Setup Wizard

```bash
# Re-run setup wizard (will overwrite existing configuration)
lazarus init

# Or manually edit configuration
nano ~/.lazarus/config.json
```

---

## 🔧 Advanced Configuration

### Manual Configuration Editing

#### Editing Configuration File

```bash
# Open configuration file
nano ~/.lazarus/config.json

# Or use your preferred editor
vim ~/.lazarus/config.json
code ~/.lazarus/config.json
```

#### Common Manual Changes

**Change Check-in Interval:**
```json
{
  "checkin_interval_days": 60
}
```

**Add Telegram Chat ID:**
```json
{
  "telegram_chat_id": "123456789"
}
```

**Enable IPFS:**
```json
{
  "storage_config": {
    "ipfs_api_url": "http://127.0.0.1:5001",
    "enable_local_fallback": true
  }
}
```

**Disarm Switch:**
```json
{
  "armed": false
}
```

### Programmatic Configuration

#### Using Python

```python
from core.config import load_config, save_config
from dataclasses import replace

# Load configuration
config = load_config()

# Modify configuration
updated_config = replace(config, checkin_interval_days=60)

# Save configuration
save_config(updated_config)
```

#### Using CLI Commands

```bash
# Extend deadline
lazarus freeze --days 30

# Update secret file
lazarus update-secret /path/to/new/secrets.txt

# Check status
lazarus status
```

### Configuration Templates

#### Minimal Configuration

```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  },
  "vault": {
    "secret_file_path": "/home/john/secrets.txt",
    "encrypted_file_path": "/home/john/.lazarus/encrypted_secrets.bin",
    "key_blob": "base64_encoded_key"
  },
  "checkin_interval_days": 30,
  "armed": true
}
```

#### Full Configuration with All Options

```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  },
  "vault": {
    "secret_file_path": "/home/john/secrets.txt",
    "encrypted_file_path": "/home/john/.lazarus/encrypted_secrets.bin",
    "key_blob": "base64_encoded_key",
    "ipfs_cid": "QmXxx..."
  },
  "checkin_interval_days": 30,
  "last_checkin_timestamp": 1714234567.123,
  "telegram_chat_id": "123456789",
  "armed": true,
  "storage_config": {
    "ipfs_api_url": "http://127.0.0.1:5001",
    "ipfs_gateway_url": "http://127.0.0.1:8080",
    "pinata_api_key": "optional_key",
    "pinata_secret_key": "optional_secret",
    "web3_storage_token": "optional_token",
    "timeout": 30,
    "max_retries": 3,
    "enable_local_fallback": true
  },
  "license_key": "gumroad_license_key",
  "subscription_tier": "paid",
  "wallet_limit": 10,
  "license_valid_until": 1714234567.123
}
```

---

## ✅ Configuration Validation

### Automatic Validation

Configuration is automatically validated when loaded:

```python
from core.config import load_config, validate_config

# Load and validate
config = load_config()

# Explicit validation
errors = validate_config(config)
if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
```

### Validation Rules

| Field | Rule | Error Message |
|-------|------|--------------|
| `owner_name` | Non-empty | "owner_name is empty" |
| `owner_email` | Contains @ | "owner_email looks invalid" |
| `beneficiary.name` | Non-empty | "beneficiary.name is empty" |
| `beneficiary.email` | Contains @ | "beneficiary.email looks invalid" |
| `beneficiary.public_key_path` | File exists | "beneficiary public key not found" |
| `vault.encrypted_file_path` | File exists | "encrypted vault file not found" |
| `vault.key_blob` | Non-empty | "vault.key_blob is empty" |
| `checkin_interval_days` | >= 1 | "checkin_interval_days must be >= 1" |

### Manual Validation

```bash
# Validate configuration
python -c "
from core.config import load_config, validate_config

config = load_config()
errors = validate_config(config)

if errors:
    print('❌ Configuration errors:')
    for error in errors:
        print(f'  - {error}')
    exit(1)
else:
    print('✅ Configuration is valid')
"
```

### Fixing Configuration Errors

#### Error: "owner_name is empty"

**Solution:**
```json
{
  "owner_name": "John Doe"
}
```

#### Error: "beneficiary public key not found"

**Solution:**
```bash
# Verify public key exists
ls -la /path/to/beneficiary_public.pem

# Update configuration with correct path
nano ~/.lazarus/config.json
```

#### Error: "encrypted vault file not found"

**Solution:**
```bash
# Verify encrypted file exists
ls -la ~/.lazarus/encrypted_secrets.bin

# If missing, re-encrypt secrets
lazarus update-secret /path/to/secrets.txt
```

---

## 💾 Backup and Restore

### Creating Backups

#### Manual Backup

```bash
# Create timestamped backup
tar -czf lazarus-backup-$(date +%Y%m%d-%H%M%S).tar.gz ~/.lazarus/

# Verify backup
tar -tzf lazarus-backup-YYYYMMDD-HHMMSS.tar.gz
```

#### Automated Backup

```bash
# Add to crontab for daily backups
crontab -e

# Add this line (backs up at 2 AM daily)
0 2 * * * tar -czf /backups/lazarus-$(date +\%Y\%m\%d).tar.gz ~/.lazarus/
```

#### Docker Volume Backup

```bash
# Backup Docker volumes
docker run --rm \
  -v lazarus_data:/data \
  -v $(pwd):/backup \
  alpine tar -czf /backup/lazarus-data-backup.tar.gz /data
```

### Restoring from Backup

#### Manual Restore

```bash
# Stop Lazarus
lazarus agent stop

# Restore from backup
tar -xzf lazarus-backup-YYYYMMDD-HHMMSS.tar.gz -C ~/

# Verify restore
lazarus status

# Restart agent
lazarus agent start
```

#### Docker Volume Restore

```bash
# Stop containers
docker-compose down

# Restore volume
docker run --rm \
  -v lazarus_data:/data \
  -v $(pwd):/backup \
  alpine tar -xzf /backup/lazarus-data-backup.tar.gz -C /

# Start containers
docker-compose up -d
```

### Backup Best Practices

1. **Regular Backups**
   - Daily automated backups
   - Weekly full backups
   - Monthly archival backups

2. **Multiple Locations**
   - Local storage
   - Cloud storage (encrypted)
   - Off-site storage

3. **Backup Verification**
   - Regular restore tests
   - Integrity checks
   - Configuration validation

4. **Backup Security**
   - Encrypt backups
   - Secure storage
   - Access controls

---

## 🔄 Migration Guide

### Upgrading from Previous Versions

#### Version 0.0.x to 0.1.0

**Changes:**
- Added IPFS support
- Added license validation
- Enhanced storage configuration

**Migration Steps:**

```bash
# 1. Backup current configuration
tar -czf lazarus-backup-pre-upgrade.tar.gz ~/.lazarus/

# 2. Upgrade Lazarus
pip install --upgrade lazarus-protocol

# 3. Run setup wizard (will preserve existing vault)
lazarus init

# 4. Verify configuration
lazarus status

# 5. Test functionality
lazarus test-trigger
```

#### Configuration Migration

**Old Configuration (0.0.x):**
```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  },
  "vault": {
    "secret_file_path": "/home/john/secrets.txt",
    "encrypted_file_path": "/home/john/.lazarus/encrypted_secrets.bin",
    "key_blob": "base64_encoded_key"
  },
  "checkin_interval_days": 30,
  "armed": true
}
```

**New Configuration (0.1.0):**
```json
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "public_key_path": "/home/john/beneficiary_public.pem"
  },
  "vault": {
    "secret_file_path": "/home/john/secrets.txt",
    "encrypted_file_path": "/home/john/.lazarus/encrypted_secrets.bin",
    "key_blob": "base64_encoded_key",
    "ipfs_cid": null
  },
  "checkin_interval_days": 30,
  "last_checkin_timestamp": 1714234567.123,
  "telegram_chat_id": null,
  "armed": true,
  "storage_config": null,
  "license_key": null,
  "subscription_tier": "free",
  "wallet_limit": 1,
  "license_valid_until": null
}
```

### Migrating to Different Machine

#### Export Configuration

```bash
# 1. Create backup
tar -czf lazarus-migration-backup.tar.gz ~/.lazarus/

# 2. Copy to new machine
scp lazarus-migration-backup.tar.gz user@newmachine:/tmp/

# 3. On new machine, restore
tar -xzf /tmp/lazarus-migration-backup.tar.gz -C ~/

# 4. Verify configuration
lazarus status
```

#### Update Paths

If paths have changed on the new machine:

```bash
# Edit configuration
nano ~/.lazarus/config.json

# Update paths as needed
# - beneficiary.public_key_path
# - vault.secret_file_path
# - vault.encrypted_file_path
```

### Migrating to Docker

#### Export Configuration

```bash
# 1. Backup current configuration
tar -czf lazarus-docker-migration.tar.gz ~/.lazarus/

# 2. Copy to Docker host
scp lazarus-docker-migration.tar.gz docker-host:/tmp/

# 3. On Docker host, extract
tar -xzf /tmp/lazarus-docker-migration.tar.gz -C /tmp/

# 4. Copy to Docker volume
docker run --rm \
  -v lazarus_config:/config \
  -v /tmp/lazarus:/source \
  alpine sh -c "cp -r /source/* /config/"
```

#### Update Docker Compose

```yaml
version: '3.8'

services:
  lazarus:
    image: ghcr.io/ravikumarve/lazarus:latest
    volumes:
      - lazarus_config:/app/.lazarus
    environment:
      - LAZARUS_HOME=/app/.lazarus
    ports:
      - "8000:8000"

volumes:
  lazarus_config:
```

---

## 📚 Additional Resources

### Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 15 minutes
- [Installation Guide](INSTALLATION.md) - Installation instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

### API Reference

- [CLI Commands](API.md#cli-commands) - Command-line interface
- [Configuration API](API.md#configuration-api) - Configuration management
- [Web API](API.md#web-api) - RESTful API endpoints

### Support

- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues) - Report bugs
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions) - Ask questions
- Email: ravikumarve@protonmail.com

---

## 🎯 Conclusion

Proper configuration is essential for Lazarus Protocol to operate securely and reliably. By following this configuration guide, you can ensure that your dead man's switch is set up correctly and will function as intended.

**Remember:**
- Always validate configuration after changes
- Keep regular backups of your configuration
- Test your configuration regularly
- Stay informed about configuration best practices

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
