# ✨ Lazarus Protocol - Features Documentation

Comprehensive feature documentation for Lazarus Protocol. Learn about all available features, how they work, and how to use them.

## 📋 Table of Contents

- [Feature Overview](#feature-overview)
- [Core Features](#core-features)
- [Security Features](#security-features)
- [Alert Features](#alert-features)
- [Storage Features](#storage-features)
- [Management Features](#management-features)
- [Integration Features](#integration-features)
- [Advanced Features](#advanced-features)

---

## 🎯 Feature Overview

Lazarus Protocol provides a comprehensive dead man's switch solution with the following feature categories:

### Feature Categories

| Category | Features | Status |
|----------|----------|--------|
| **Core** | Dead man's switch, Check-in system, Escalation | ✅ Production Ready |
| **Security** | Encryption, Key management, File permissions | ✅ Production Ready |
| **Alerts** | Email, Telegram, Multi-channel | ✅ Production Ready |
| **Storage** | Local, IPFS, Multi-provider | ✅ Production Ready |
| **Management** | CLI, Web dashboard, API | ✅ Production Ready |
| **Integration** | Docker, Systemd, REST API | ✅ Production Ready |

---

## 🔒 Core Features

### Dead Man's Switch

#### Overview

The dead man's switch is the core feature of Lazarus Protocol. It automatically delivers your encrypted secrets to your beneficiary if you stop checking in.

#### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│              Dead Man's Switch Lifecycle                      │
└─────────────────────────────────────────────────────────────┘

1. Setup Phase
   └─ Encrypt your secrets
   └─ Configure beneficiary
   └─ Set check-in interval

2. Monitoring Phase
   └─ Background agent runs 24/7
   └─ Monitors check-in status
   └─ Tracks time since last check-in

3. Escalation Phase
   └─ Send reminder alerts
   └─ Send warning alerts
   └─ Send final warning

4. Delivery Phase
   └─ Trigger fires if deadline passes
   └─ Deliver encrypted secrets
   └─ Send decryption instructions

5. Recovery Phase
   └─ Beneficiary receives secrets
   └─ Beneficiary decrypts with private key
   └─ Switch disarms
```

#### Configuration

```bash
# Set check-in interval (days)
lazarus init
# During setup, specify interval: 30 days

# Or edit configuration
nano ~/.lazarus/config.json
{
  "checkin_interval_days": 30
}
```

#### Usage

```bash
# Check status
lazarus status

# Perform check-in
lazarus ping

# Extend deadline
lazarus freeze --days 30

# Test trigger (dry run)
lazarus test-trigger
```

#### Recommended Intervals

| Interval | Use Case | Risk Level |
|----------|----------|------------|
| **7 days** | High-risk situations, frequent travel | Low risk of accidental trigger |
| **30 days** | Balanced approach, regular check-ins | Medium risk |
| **90 days** | Low-risk situations, infrequent check-ins | High risk of accidental trigger |

---

### Check-in System

#### Overview

The check-in system allows you to prove you're alive and reset the countdown timer.

#### Check-in Methods

**Method 1: Manual Check-in (CLI)**

```bash
# Perform manual check-in
lazarus ping

# Output:
# ✓ Check-in recorded at 2026-04-27 10:30:00 UTC
# Timer reset - next check-in due in 30.0 days
```

**Method 2: Web Dashboard**

```bash
# Start web dashboard
lazarus dashboard

# Open browser to http://localhost:8000
# Click "Check In" button
```

**Method 3: API**

```bash
# Use REST API
curl -X POST http://localhost:8000/api/checkin

# Response:
# {"status": "success", "timestamp": 1714234567.123}
```

**Method 4: Automated (Cron)**

```bash
# Add to crontab for automated check-ins
crontab -e

# Add weekly check-in (every Sunday at 9 AM)
0 9 * * 0 /usr/local/bin/lazarus ping
```

#### Check-in Status

```bash
# View check-in status
lazarus status

# Output includes:
# - Days since last check-in
# - Days until trigger
# - Last check-in timestamp
# - Armed state
```

#### Check-in Reminders

Lazarus Protocol sends automatic reminders before the trigger fires:

- **7 days before**: Reminder email
- **3 days before**: Warning email
- **1 day before**: Final warning email
- **0 days (trigger)**: Delivery email

---

### Escalation System

#### Overview

The escalation system provides multiple warning levels before the dead man's switch triggers.

#### Escalation Levels

| Level | Timing | Action | Recipient |
|-------|--------|--------|-----------|
| **Level 1** | 7 days before | Reminder email | Owner |
| **Level 2** | 3 days before | Warning email | Owner |
| **Level 3** | 1 day before | Final warning | Owner + Beneficiary |
| **Level 4** | 0 days (trigger) | Delivery | Beneficiary |

#### Escalation Configuration

```bash
# Escalation timing is based on check-in interval
# For 30-day interval:
# - Level 1: 23 days after last check-in
# - Level 2: 27 days after last check-in
# - Level 3: 29 days after last check-in
# - Level 4: 30 days after last check-in
```

#### Custom Escalation

```bash
# Currently, escalation timing is automatic
# Future versions will support custom escalation schedules
```

---

## 🔐 Security Features

### Military-Grade Encryption

#### Overview

Lazarus Protocol uses AES-256-GCM + RSA-4096 hybrid encryption for maximum security.

#### Encryption Process

```
┌─────────────────────────────────────────────────────────────┐
│                    Encryption Process                        │
└─────────────────────────────────────────────────────────────┘

1. Generate Random AES-256 Key
   └─ 256-bit cryptographically secure random

2. Encrypt Secret File
   └─ Algorithm: AES-256-GCM
   └─ Key: Random AES-256 key
   └─ Nonce: 12-byte random value
   └─ Output: Ciphertext + authentication tag

3. Encrypt AES Key
   └─ Algorithm: RSA-4096-OAEP
   └─ Key: Beneficiary's public key
   └─ Padding: OAEP with SHA-256
   └─ Output: Encrypted key blob

4. Store Securely
   └─ Encrypted file: ~/.lazarus/encrypted_secrets.bin
   └─ Key blob: ~/.lazarus/config.json
   └─ File permissions: 600 (owner only)
```

#### Security Properties

| Property | Implementation | Security Level |
|----------|----------------|----------------|
| **Confidentiality** | AES-256-GCM | 256-bit security |
| **Integrity** | GCM authentication tag | Cryptographic verification |
| **Authenticity** | RSA-4096 signature | 4096-bit security |
| **Forward Secrecy** | Random AES keys per encryption | Perfect forward secrecy |

#### Usage

```bash
# Encryption happens automatically during setup
lazarus init

# Re-encrypt with new key
lazarus update-secret /path/to/secrets.txt

# Test encryption
python -c "
from core.encryption import generate_rsa_keypair, encrypt_file
priv, pub = generate_rsa_keypair()
encrypted_path, key_blob = encrypt_file(
    '/path/to/secrets.txt',
    pub,
    '/tmp'
)
print(f'Encrypted: {encrypted_path}')
print(f'Key blob: {len(key_blob)} bytes')
"
```

---

### Key Management

#### Overview

Lazarus Protocol uses RSA-4096 key pairs for encryption and decryption.

#### Key Generation

```bash
# Generate RSA-4096 key pair
openssl genrsa -out beneficiary_private.pem 4096

# Extract public key
openssl rsa -in beneficiary_private.pem -pubout -out beneficiary_public.pem

# Secure private key
chmod 600 beneficiary_private.pem
```

#### Key Storage

**Recommended Storage Methods:**

1. **Hardware Security Module (HSM)**
   ```bash
   # Use YubiKey for key storage
   yubico-piv-tool -a generate -s 9c -o beneficiary_public.pem
   ```

2. **Encrypted USB Drive**
   ```bash
   # Encrypt USB drive with LUKS
   sudo cryptsetup luksFormat /dev/sdb1
   sudo cryptsetup open /dev/sdb1 encrypted_usb
   # Store private key on mounted drive
   ```

3. **Password Manager**
   ```bash
   # Store in Bitwarden, 1Password, etc.
   # Benefits: Encrypted, MFA, audit logs
   ```

4. **Paper Wallet**
   ```bash
   # Print private key on paper
   # Store in safe or safety deposit box
   ```

#### Key Rotation

```bash
# Generate new key pair
openssl genrsa -out beneficiary_private_new.pem 4096
openssl rsa -in beneficiary_private_new.pem -pubout -out beneficiary_public_new.pem

# Re-encrypt secrets with new public key
lazarus update-secret /path/to/secrets.txt
# Use new public key during setup

# Securely destroy old keys
shred -u beneficiary_private.pem
shred -u beneficiary_public.pem
```

---

### File Permissions

#### Overview

Lazarus Protocol automatically sets secure file permissions on all platforms.

#### Permission Levels

| Platform | Directory | Config Files | Encrypted Files |
|----------|-----------|--------------|-----------------|
| **Linux/macOS** | 700 (rwx------) | 600 (rw-------) | 600 (rw-------) |
| **Windows** | Owner only | Owner only | Owner only |

#### Automatic Permission Setting

```bash
# Permissions are set automatically when:
# - Configuration is saved
# - Files are created
# - Files are modified

# Verify permissions
ls -la ~/.lazarus/

# Expected output:
# drwx------  2 user user 4096 Apr 27 10:30 .
# -rw-------  1 user user 1234 Apr 27 10:30 config.json
# -rw-------  1 user user 5678 Apr 27 10:30 encrypted_secrets.bin
```

#### Manual Permission Fix

```bash
# Fix directory permissions
chmod 700 ~/.lazarus

# Fix file permissions
chmod 600 ~/.lazarus/config.json
chmod 600 ~/.lazarus/encrypted_secrets.bin

# Windows (PowerShell)
$acl = Get-Acl "C:\Users\user\.lazarus\config.json"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $env:USERNAME,
    "Read,Write",
    "Allow"
)
$acl.SetAccessRule($accessRule)
$acl | Set-Acl "C:\Users\user\.lazarus\config.json"
```

---

## 📧 Alert Features

### Email Alerts

#### Overview

Email alerts provide notifications about check-in status and trigger events.

#### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with SendGrid credentials
nano .env

# Add:
SENDGRID_API_KEY=your_actual_api_key
ALERT_FROM_EMAIL=lazarus@yourdomain.com
ALERT_TO_EMAIL=your_personal_email@gmail.com
```

#### Alert Types

**1. Reminder Alerts**

```plaintext
Subject: [Lazarus] Reminder: Check-in due in 7 days

Body:
Hello John Doe,

This is a reminder that your Lazarus Protocol check-in is due in 7 days.

Please check in to prevent the dead man's switch from triggering.

Check in: lazarus ping
Or visit: http://localhost:8000

Last check-in: 2026-04-20 10:30:00 UTC
Next check-in due: 2026-04-27 10:30:00 UTC

Best regards,
Lazarus Protocol
```

**2. Warning Alerts**

```plaintext
Subject: [Lazarus] WARNING: Check-in due in 3 days

Body:
Hello John Doe,

WARNING: Your Lazarus Protocol check-in is due in 3 days.

Please check in immediately to prevent the dead man's switch from triggering.

Check in: lazarus ping
Or visit: http://localhost:8000

Last check-in: 2026-04-24 10:30:00 UTC
Next check-in due: 2026-04-27 10:30:00 UTC

Best regards,
Lazarus Protocol
```

**3. Final Warning**

```plaintext
Subject: [Lazarus] FINAL WARNING: Check-in due in 1 day

Body:
Hello John Doe,

FINAL WARNING: Your Lazarus Protocol check-in is due in 1 day.

Please check in immediately to prevent the dead man's switch from triggering.

If you do not check in by 2026-04-27 10:30:00 UTC, your encrypted secrets will be delivered to your beneficiary.

Check in: lazarus ping
Or visit: http://localhost:8000

Last check-in: 2026-04-26 10:30:00 UTC
Next check-in due: 2026-04-27 10:30:00 UTC

Best regards,
Lazarus Protocol
```

**4. Delivery Alert (to Beneficiary)**

```plaintext
Subject: [Lazarus] You have received an inheritance from John Doe

Body:
Hello Jane Doe,

You have received an inheritance from John Doe via Lazarus Protocol.

Attached are:
1. encrypted_secrets.bin - Encrypted vault file
2. decryption_kit.zip - Decryption instructions and tools

To decrypt:
1. Extract decryption_kit.zip
2. Run decrypt.py with your private key
3. Follow the instructions in INSTRUCTIONS.txt

If you have questions, contact: ravikumarve@protonmail.com

Best regards,
Lazarus Protocol
```

#### Testing Email Alerts

```bash
# Test email configuration
python -m pytest tests/test_sendgrid_integration.py -v -m integration

# Test trigger (dry run)
lazarus test-trigger
```

---

### Telegram Alerts

#### Overview

Telegram alerts provide mobile notifications for check-in status.

#### Configuration

```bash
# Create Telegram bot
# 1. Message @BotFather on Telegram
# 2. Create new bot
# 3. Get bot token

# Get your chat ID
# 1. Message @userinfobot on Telegram
# 2. Get your chat ID

# Add to .env
nano .env

# Add:
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

#### Alert Types

**1. Check-in Reminder**

```
🔔 Lazarus Reminder

Check-in due in 7 days!

Last check-in: 2026-04-20 10:30:00 UTC
Next check-in due: 2026-04-27 10:30:00 UTC

Check in with: lazarus ping
```

**2. Warning Alert**

```
⚠️ Lazarus Warning

Check-in due in 3 days!

Please check in immediately to prevent trigger.

Check in with: lazarus ping
```

**3. Final Warning**

```
🚨 Lazarus Final Warning

Check-in due in 1 day!

If you don't check in by 2026-04-27 10:30:00 UTC,
your secrets will be delivered to your beneficiary.

Check in with: lazarus ping
```

#### Testing Telegram Alerts

```bash
# Test Telegram configuration
python -c "
from agent.alerts import telegram_configured, send_telegram_alert

if telegram_configured():
    send_telegram_alert('Test message from Lazarus Protocol')
    print('✓ Telegram test sent')
else:
    print('✗ Telegram not configured')
"
```

---

### Multi-Channel Alerts

#### Overview

Multi-channel alerts ensure you receive notifications through multiple methods.

#### Configuration

```bash
# Configure both email and Telegram
nano .env

# Add:
SENDGRID_API_KEY=your_sendgrid_key
ALERT_FROM_EMAIL=lazarus@yourdomain.com
ALERT_TO_EMAIL=your_email@gmail.com
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

#### Alert Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Channel Alert Flow                   │
└─────────────────────────────────────────────────────────────┘

1. Check-in Due (7 days)
   ├─ Email reminder
   └─ Telegram reminder

2. Check-in Due (3 days)
   ├─ Email warning
   └─ Telegram warning

3. Check-in Due (1 day)
   ├─ Email final warning
   ├─ Telegram final warning
   └─ SMS (if configured)

4. Trigger Fired
   ├─ Email to beneficiary
   └─ Telegram to beneficiary
```

#### Benefits

- **Redundancy**: Multiple notification channels
- **Reliability**: Higher chance of receiving alerts
- **Flexibility**: Choose preferred notification method
- **Coverage**: Email + mobile notifications

---

## 💾 Storage Features

### Local Storage

#### Overview

Local storage is the primary storage method for Lazarus Protocol.

#### Storage Location

```bash
# Default location
~/.lazarus/

# Contents:
~/.lazarus/
├── config.json              # Configuration file
├── encrypted_secrets.bin    # Encrypted vault
├── logs/                    # Log files
│   └── lazarus.log
└── temp/                    # Temporary files
```

#### Advantages

- **No network dependency**: Works offline
- **Full control**: You own your data
- **Fast access**: Local file system
- **Privacy**: No cloud exposure

#### Configuration

```bash
# Default location is automatic
# Can customize with environment variable

export LAZARUS_HOME="/custom/path"
lazarus init
```

---

### IPFS Storage

#### Overview

IPFS (InterPlanetary File System) provides decentralized storage with redundancy.

#### IPFS Benefits

- **Redundancy**: Multiple copies across IPFS network
- **Resilience**: Survives local hardware failure
- **Accessibility**: Retrieve from any IPFS node
- **Censorship Resistance**: Decentralized storage

#### Configuration

**Option 1: Local IPFS Node**

```bash
# Install IPFS
curl -O https://dist.ipfs.tech/kubo/v0.28.0/kubo_v0.28.0_linux-amd64.tar.gz
tar -xvzf kubo_v0.28.0_linux-amd64.tar.gz
cd kubo
sudo ./install.sh

# Initialize IPFS
ipfs init --profile=lowpower

# Start IPFS daemon
ipfs daemon &

# Configure Lazarus
export IPFS_API_URL="http://localhost:5001"
```

**Option 2: Pinata Cloud**

```bash
# Sign up at https://pinata.cloud
# Get API keys from dashboard

# Configure Lazarus
export PINATA_API_KEY="your_pinata_key"
export PINATA_SECRET_KEY="your_pinata_secret"
```

#### Usage

```bash
# Upload to IPFS
lazarus ipfs store ~/.lazarus/encrypted_secrets.bin

# Check IPFS status
lazarus ipfs status

# Retrieve from IPFS (testing)
lazarus ipfs retrieve <cid> /tmp/recovered-file
```

#### IPFS CID

```bash
# View IPFS CID in configuration
cat ~/.lazarus/config.json | grep ipfs_cid

# Example output:
# "ipfs_cid": "QmXxx..."
```

---

### Multi-Provider Storage

#### Overview

Multi-provider storage provides automatic failover between storage providers.

#### Storage Providers

| Provider | Type | Status | Fallback |
|----------|------|--------|----------|
| **Local** | Primary | ✅ Always available | N/A |
| **IPFS Local** | Secondary | ✅ Configurable | Local |
| **Pinata** | Tertiary | ✅ Configurable | IPFS Local |
| **Web3.storage** | Quaternary | ✅ Configurable | Pinata |

#### Configuration

```bash
# Configure multiple storage providers
nano ~/.lazarus/config.json

{
  "storage_config": {
    "ipfs_api_url": "http://localhost:5001",
    "pinata_api_key": "optional_pinata_key",
    "pinata_secret_key": "optional_pinata_secret",
    "web3_storage_token": "optional_web3_token",
    "timeout": 30,
    "max_retries": 3,
    "enable_local_fallback": true
  }
}
```

#### Failover Logic

```
┌─────────────────────────────────────────────────────────────┐
│                    Storage Failover Logic                     │
└─────────────────────────────────────────────────────────────┘

1. Try Primary Storage (Local)
   └─ Success: Use local storage
   └─ Failure: Try secondary

2. Try Secondary Storage (IPFS Local)
   └─ Success: Use IPFS
   └─ Failure: Try tertiary

3. Try Tertiary Storage (Pinata)
   └─ Success: Use Pinata
   └─ Failure: Try quaternary

4. Try Quaternary Storage (Web3.storage)
   └─ Success: Use Web3.storage
   └─ Failure: Return error

5. All Failed: Return error
   └─ Log error
   └─ Notify user
```

#### Benefits

- **Reliability**: Automatic failover
- **Redundancy**: Multiple storage locations
- **Resilience**: Survives provider outages
- **Flexibility**: Choose providers based on needs

---

## 🎛️ Management Features

### CLI Interface

#### Overview

The command-line interface provides full control over Lazarus Protocol.

#### Available Commands

```bash
# View all commands
lazarus --help

# Output:
# Usage: lazarus [OPTIONS] COMMAND [ARGS]...
#
# Options:
#   --version  Show the version and exit.
#   --help     Show this message and exit.
#
# Commands:
#   init            Setup wizard
#   ping            Manual check-in
#   status          Show vault status
#   agent           Manage the background heartbeat agent.
#   freeze          Panic button — extend the trigger deadline by N days.
#   test-trigger    Dry run — simulate delivery without actually sending anything.
#   update-secret   Replace the encrypted secret file with a new one.
```

#### Command Examples

**Setup and Initialization**

```bash
# Run setup wizard
lazarus init

# View version
lazarus --version
```

**Check-in Management**

```bash
# Perform check-in
lazarus ping

# View status
lazarus status

# Extend deadline
lazarus freeze --days 30
```

**Agent Management**

```bash
# Start agent
lazarus agent start

# Stop agent
lazarus agent stop

# View agent status
lazarus status
```

**Testing and Validation**

```bash
# Test trigger (dry run)
lazarus test-trigger

# Update secret file
lazarus update-secret /path/to/secrets.txt
```

---

### Web Dashboard

#### Overview

The web dashboard provides a graphical interface for managing Lazarus Protocol.

#### Features

- **Status Overview**: View vault status at a glance
- **Check-in Button**: One-click check-in
- **Configuration Management**: Edit settings via web interface
- **Log Viewer**: View system logs
- **Dark/Light Theme**: Switch between themes
- **Mobile Responsive**: Works on mobile devices

#### Access

```bash
# Start web dashboard
lazarus dashboard

# Or start web server directly
python -m web.server

# Access in browser
# http://localhost:8000
```

#### Dashboard Sections

**1. Status Overview**

```
┌─────────────────────────────────────────┐
│         Lazarus Protocol Status          │
├─────────────────────────────────────────┤
│ Armed State:      ✅ Armed              │
│ Owner:            John Doe              │
│ Beneficiary:      Jane Doe              │
│ Check-in Interval: 30 days              │
│ Days Since Ping:  5.2 days ago         │
│ Days Until Trigger: 24.8 days           │
│ Last Check-in:    2026-04-22 10:30:00   │
└─────────────────────────────────────────┘
```

**2. Check-in Button**

```
┌─────────────────────────────────────────┐
│                                         │
│        [  Check In Now  ]                │
│                                         │
│  Last check-in: 5 days ago              │
│  Next check-in due: 25 days             │
│                                         │
└─────────────────────────────────────────┘
```

**3. Configuration Panel**

```
┌─────────────────────────────────────────┐
│         Configuration                    │
├─────────────────────────────────────────┤
│ Owner Name:      [John Doe        ]     │
│ Owner Email:     [john@...        ]     │
│ Beneficiary:     [Jane Doe        ]     │
│ Check-in Interval: [30 days      ]     │
│                                         │
│ [Save Changes]                          │
└─────────────────────────────────────────┘
```

**4. Log Viewer**

```
┌─────────────────────────────────────────┐
│         System Logs                      │
├─────────────────────────────────────────┤
│ 2026-04-27 10:30:00 INFO  Check-in...  │
│ 2026-04-27 10:30:00 INFO  Timer reset   │
│ 2026-04-26 10:30:00 INFO  Check-in...  │
│ ...                                     │
│                                         │
│ [Refresh] [Clear] [Download]            │
└─────────────────────────────────────────┘
```

---

### REST API

#### Overview

The REST API provides programmatic access to Lazarus Protocol functionality.

#### API Endpoints

**Status Endpoint**

```bash
# Get status
curl http://localhost:8000/api/status

# Response:
{
  "armed": true,
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary_name": "Jane Doe",
  "beneficiary_email": "jane.doe@example.com",
  "checkin_interval_days": 30,
  "days_since_checkin": 5.2,
  "days_until_trigger": 24.8,
  "last_checkin": "2026-04-22T10:30:00Z"
}
```

**Check-in Endpoint**

```bash
# Perform check-in
curl -X POST http://localhost:8000/api/checkin

# Response:
{
  "status": "success",
  "timestamp": 1714234567.123,
  "days_until_trigger": 30.0
}
```

**Configuration Endpoint**

```bash
# Get configuration
curl http://localhost:8000/api/config

# Response:
{
  "owner_name": "John Doe",
  "owner_email": "john.doe@example.com",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
  },
  "checkin_interval_days": 30,
  "armed": true
}
```

**Test Trigger Endpoint**

```bash
# Test trigger (dry run)
curl http://localhost:8000/api/test-trigger

# Response:
{
  "status": "dry_run",
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
  },
  "vault": {
    "encrypted_file": "/home/john/.lazarus/encrypted_secrets.bin",
    "file_size": 1234,
    "key_blob_present": true
  },
  "trigger_status": "not_due",
  "days_remaining": 24.8
}
```

#### API Authentication

```bash
# Currently, API does not require authentication
# Future versions will support API key authentication

# Example with API key (future):
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/status
```

---

## 🔌 Integration Features

### Docker Integration

#### Overview

Docker provides containerized deployment for Lazarus Protocol.

#### Docker Compose

```yaml
version: '3.8'

services:
  lazarus:
    image: ghcr.io/ravikumarve/lazarus:latest
    container_name: lazarus
    volumes:
      - lazarus_data:/app/.lazarus
      - ./ssl:/app/ssl:ro
    environment:
      - LAZARUS_SSL_CERT_FILE=/app/ssl/cert.pem
      - LAZARUS_SSL_KEY_FILE=/app/ssl/key.pem
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - ALERT_FROM_EMAIL=${ALERT_FROM_EMAIL}
      - ALERT_TO_EMAIL=${ALERT_TO_EMAIL}
    ports:
      - "8000:8000"
    restart: unless-stopped

volumes:
  lazarus_data:
```

#### Usage

```bash
# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

---

### Systemd Integration

#### Overview

Systemd provides service management for Lazarus Protocol on Linux.

#### Systemd Service File

```ini
[Unit]
Description=Lazarus Protocol Dead Man's Switch
After=network.target

[Service]
Type=simple
User=lazarus
Group=lazarus
WorkingDirectory=/opt/lazarus
Environment="PATH=/opt/lazarus/venv/bin"
ExecStart=/opt/lazarus/venv/bin/python -m agent.heartbeat
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Installation

```bash
# Create service file
sudo nano /etc/systemd/system/lazarus.service

# Copy service file content above

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable lazarus
sudo systemctl start lazarus

# Check status
sudo systemctl status lazarus

# View logs
sudo journalctl -u lazarus -f
```

---

## 🚀 Advanced Features

### License Validation

#### Overview

License validation provides subscription tier management for Lazarus Protocol.

#### License Tiers

| Tier | Wallet Limit | Features | Price |
|------|--------------|----------|-------|
| **Free** | 1 wallet | Basic features | Free |
| **Paid** | 10 wallets | All features | $49/mo |
| **Enterprise** | Unlimited | All features + support | $499/mo |

#### Configuration

```bash
# Add license key to configuration
nano ~/.lazarus/config.json

{
  "license_key": "gumroad_license_key",
  "subscription_tier": "paid",
  "wallet_limit": 10,
  "license_valid_until": 1714234567.123
}
```

#### Validation

```bash
# Validate license
python -c "
from core.license import validate_license

license_key = 'your_license_key'
is_valid, tier, wallet_limit = validate_license(license_key)

if is_valid:
    print(f'✓ License valid')
    print(f'  Tier: {tier}')
    print(f'  Wallet limit: {wallet_limit}')
else:
    print('✗ License invalid')
"
```

---

### Webhook Integration

#### Overview

Webhooks allow external systems to receive notifications from Lazarus Protocol.

#### Configuration

```bash
# Add webhook URL to configuration
nano ~/.lazarus/config.json

{
  "webhook_url": "https://your-webhook-url.com/lazarus",
  "webhook_events": [
    "checkin",
    "warning",
    "trigger"
  ]
}
```

#### Webhook Payload

**Check-in Event**

```json
{
  "event": "checkin",
  "timestamp": 1714234567.123,
  "owner": {
    "name": "John Doe",
    "email": "john.doe@example.com"
  },
  "days_until_trigger": 30.0
}
```

**Warning Event**

```json
{
  "event": "warning",
  "timestamp": 1714234567.123,
  "warning_level": 2,
  "days_until_trigger": 3.0,
  "message": "Check-in due in 3 days"
}
```

**Trigger Event**

```json
{
  "event": "trigger",
  "timestamp": 1714234567.123,
  "beneficiary": {
    "name": "Jane Doe",
    "email": "jane.doe@example.com"
  },
  "vault": {
    "encrypted_file": "/home/john/.lazarus/encrypted_secrets.bin",
    "ipfs_cid": "QmXxx..."
  }
}
```

---

### Custom Alert Templates

#### Overview

Custom alert templates allow you to customize email and notification content.

#### Email Template

```bash
# Create custom email template
nano ~/.lazarus/templates/email_reminder.txt

# Template variables:
# {{owner_name}} - Your name
# {{beneficiary_name}} - Beneficiary name
# {{days_until_trigger}} - Days until trigger
# {{last_checkin}} - Last check-in timestamp
# {{next_checkin}} - Next check-in due

# Example template:
Hello {{owner_name}},

This is a reminder that your Lazarus Protocol check-in is due in {{days_until_trigger}} days.

Please check in to prevent the dead man's switch from triggering.

Last check-in: {{last_checkin}}
Next check-in due: {{next_checkin}}

Best regards,
Lazarus Protocol
```

#### Configuration

```bash
# Add template path to configuration
nano ~/.lazarus/config.json

{
  "email_templates": {
    "reminder": "~/.lazarus/templates/email_reminder.txt",
    "warning": "~/.lazarus/templates/email_warning.txt",
    "final": "~/.lazarus/templates/email_final.txt"
  }
}
```

---

## 📚 Additional Resources

### Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 15 minutes
- [Installation Guide](INSTALLATION.md) - Installation instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

### API Reference

- [CLI Commands](API.md#cli-commands) - Command-line interface
- [Web API](API.md#web-api) - RESTful API endpoints
- [Configuration API](API.md#configuration-api) - Configuration management

### Support

- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues) - Report bugs
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions) - Ask questions
- Email: ravikumarve@protonmail.com

---

## 🎯 Conclusion

Lazarus Protocol provides a comprehensive set of features for protecting your digital legacy. From military-grade encryption to multi-channel alerts, every feature is designed with security and reliability in mind.

**Remember:**
- Use all security features for maximum protection
- Configure multiple alert channels for reliability
- Test your setup regularly
- Keep your beneficiary informed

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
