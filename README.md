<h1 align="center">⚰️ Lazarus Protocol</h1>

<p align="center">
  <strong>Your crypto secrets survive you — self-hosted dead man's switch for digital asset holders</strong>
</p>

<p align="center">
  <a href="https://github.com/ravikumarve/lazarus/stargazers">
    <img src="https://img.shields.io/github/stars/ravikumarve/lazarus?style=social" alt="GitHub stars" />
  </a>
  <a href="https://github.com/ravikumarve/lazarus/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/ravikumarve/lazarus" alt="License" />
  </a>
  <a href="https://pypi.org/project/lazarus-protocol/">
    <img src="https://img.shields.io/pypi/v/lazarus-protocol" alt="PyPI version" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python version" />
  </a>
  <a href="https://github.com/ravikumarve/lazarus/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/ravikumarve/lazarus/ci.yml" alt="Build Status" />
  </a>
  <a href="https://github.com/ravikumarve/lazarus/issues">
    <img src="https://img.shields.io/github/issues/ravikumarve/lazarus" alt="Open Issues" />
  </a>
</p>

<p align="center">
  <strong>📺 Demo Coming Soon</strong><br/>
  <em>See <a href="assets/demo-instructions.md">demo creation guide</a> for details</em>
</p>

---

## ✨ Why Lazarus Protocol Exists

**For crypto holders who need a failsafe:** When you're gone, your digital assets shouldn't be lost forever. Lazarus Protocol ensures your encrypted secrets — private keys, wallet phrases, access credentials — are automatically delivered to your chosen beneficiary if you stop checking in.

**No middlemen. No cloud services. No trust required.** Your secrets stay encrypted until delivery, and the entire system runs on your own hardware.

## 🚀 Features That Protect Your Legacy

- **🔐 Military-Grade Encryption**: AES-256-GCM + RSA-4096 hybrid encryption — your secrets stay encrypted until delivery
- **⏰ Automated Heartbeat Monitoring**: Background agent checks if you're active and triggers alerts if you miss check-ins
- **📧 Multi-Channel Alerts**: Email (SendGrid) + Telegram notifications with escalating urgency
- **🛡️ Self-Hosted Security**: No cloud dependencies — your data never leaves your control
- **💻 Cross-Platform**: Full Windows, Linux, and macOS support with identical security guarantees
- **⚡ Production Ready**: Systemd service integration for 24/7 reliability
- **🧪 Comprehensive Testing**: 20+ passing tests covering all critical functionality

## 📦 Quick Start (30 Seconds to Safety)

```bash
# Install from PyPI
pip install lazarus-protocol

# Initialize your vault (creates ~/.lazarus/config.json)
lazarus init

# Start the background monitoring agent
lazarus agent start --daemon

# Perform manual check-in (resets the countdown)
lazarus ping
```

## 🎯 How It Works

1. **Setup**: You encrypt your secrets and specify a beneficiary email
2. **Monitoring**: The background agent runs 24/7, waiting for your periodic check-ins
3. **Escalation**: If you miss check-ins, alerts escalate from reminders to final warnings
4. **Delivery**: If all alerts go unanswered, encrypted secrets are delivered with decryption instructions
5. **Recovery**: Your beneficiary receives everything needed to decrypt your legacy

## 🔧 Advanced Setup

### Email Alerts (Recommended)
```bash
# Set up SendGrid for email alerts
export SENDGRID_API_KEY="your_sendgrid_key"
export ALERT_FROM_EMAIL="your@email.com"
```

### Telegram Alerts (Optional)
```bash
# Set up Telegram bot for mobile notifications
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### IPFS Storage (Optional but Recommended)

Lazarus Protocol supports IPFS (InterPlanetary File System) for redundant storage of your encrypted vault. While local storage is sufficient for basic operation, IPFS provides:

- **Redundancy**: Multiple copies across the IPFS network
- **Resilience**: Survives local hardware failure
- **Accessibility**: Beneficiaries can retrieve from any IPFS node
- **Censorship Resistance**: Decentralized storage can't be taken down

#### Option 1: Local IPFS Node (Recommended for Privacy)

```bash
# Install IPFS Kubo (official Go implementation)
# Linux/macOS:
curl -O https://dist.ipfs.tech/kubo/v0.28.0/kubo_v0.28.0_linux-amd64.tar.gz  # Linux
curl -O https://dist.ipfs.tech/kubo/v0.28.0/kubo_v0.28.0_darwin-amd64.tar.gz  # macOS

# Extract and install
tar -xvzf kubo_v0.28.0_*.tar.gz
cd kubo
sudo ./install.sh

# Windows (PowerShell):
# Download from https://dist.ipfs.tech/kubo/v0.28.0/kubo_v0.28.0_windows-amd64.zip
# Extract and add to PATH

# Initialize your IPFS node
ipfs init --profile=lowpower

# Configure for local network only (enhanced privacy)
ipfs config Addresses.Gateway /ip4/127.0.0.1/tcp/8080
ipfs config Addresses.API /ip4/127.0.0.1/tcp/5001

# Start the IPFS daemon
ipfs daemon &

# Verify IPFS is running
ipfs id
```

#### Option 2: Pinata Cloud (Easy Setup)

For cloud-based IPFS without running your own node:

```bash
# Sign up at https://pinata.cloud (free tier available)
# Get your API keys from the dashboard

export PINATA_API_KEY="your_pinata_api_key"
export PINATA_SECRET_API_KEY="your_pinata_secret_key"
```

#### Configure Lazarus for IPFS

Add IPFS configuration to your Lazarus setup:

```bash
# For local IPFS node (default)
export IPFS_NODE_URL="http://localhost:5001"

# For Pinata cloud (optional)
export IPFS_PINATA_API_KEY="$PINATA_API_KEY"
export IPFS_PINATA_SECRET_API_KEY="$PINATA_SECRET_API_KEY"

# Or configure in ~/.lazarus/config.json:
{
  "ipfs": {
    "enabled": true,
    "node_url": "http://localhost:5001",
    "pinata_api_key": "optional_pinata_key",
    "pinata_secret": "optional_pinata_secret"
  }
}
```

#### Test IPFS Integration

```bash
# Test IPFS connection
lazarus ipfs test

# Manually store a file to IPFS
lazarus ipfs store ~/.lazarus/vault.encrypted

# Check IPFS status
lazarus ipfs status

# Retrieve from IPFS (for testing)
lazarus ipfs retrieve <cid> /tmp/recovered-file
```

### Production Deployment with Systemd
```bash
# Install as systemd service for 24/7 operation
cp lazarus.service ~/.config/systemd/user/
systemctl --user enable lazarus
systemctl --user start lazarus

# Monitor logs
journalctl --user-unit=lazarus.service -f
```

## 🏗️ Architecture

```
lazarus/
├── core/
│   ├── encryption.py      # AES-256 + RSA hybrid encryption engine
│   ├── config.py          # Secure configuration management
│   └── storage.py         # IPFS + local storage (in progress)
├── agent/
│   ├── heartbeat.py       # Heartbeat monitoring & escalation logic
│   └── alerts.py          # Email + Telegram notification system
├── cli/
│   ├── main.py            # Command-line interface
│   └── setup.py           # Interactive setup wizard
└── tests/                 # Comprehensive test suite
```

## 🛡️ Security Model

### ✅ Implemented Protections
- **Military-grade encryption** (AES-256-GCM + RSA-4096)
- **Secure memory handling** with compiler optimization-resistant zeroing
- **Cross-platform file permissions** (POSIX chmod 0o600 + Windows equivalent)
- **Tamper detection** via GCM authentication tags
- **No external dependencies** for core operation

### Threat Protection Matrix
| Threat | Protection | Status |
|---|---|---|
| Vault file stolen | Useless without private key | ✅ **Active** |
| Intercepted email | Encrypted file unreadable | ✅ **Active** |
| Cloud service hacked | No cloud — fully local | ✅ **Active** |
| Early trigger accident | Escalation ladder + freeze | ✅ **Active** |
| Forget to check in | Daily reminders + alerts | ✅ **Active** |

## 📊 Status

### ✅ Completed Features
- Core encryption engine (AES-256-GCM + RSA-4096)
- Configuration system with secure storage
- CLI framework with setup wizard
- Heartbeat logic and escalation system
- Manual check-in (ping command)
- Email alert system (SendGrid integration)
- Telegram alert system
- Agent scheduler implementation
- Beneficiary delivery system
- Decryption kit generator
- Comprehensive test suite (20+ tests)

### 🚧 In Progress
- IPFS storage layer for redundancy
- Multi-platform packaging
- Desktop GUI application
- Security audit and penetration testing

## 🐛 Troubleshooting

### Common Issues

**Module not found:**
```bash
pip install -r requirements.txt
```

**Config not found:**
```bash
lazarus init  # Run setup wizard first
```

**Permission errors:**
```bash
chmod 600 ~/.lazarus/config.json
```

**Test your setup:**
```bash
# Run full test suite
python -m pytest tests/ -v

# Test encryption specifically
python -c "
from core.encryption import encrypt_file, decrypt_file, generate_rsa_keypair
from pathlib import Path
import tempfile

# Generate test keypair
priv, pub = generate_rsa_keypair()

# Create test file
with tempfile.NamedTemporaryFile(delete=False) as f:
    f.write(b'test secret content')
    test_file = Path(f.name)

# Test encryption/decryption roundtrip
encrypted_path, key_blob = encrypt_file(test_file, pub, Path('/tmp'))
decrypted_path = decrypt_file(encrypted_path, key_blob, priv, Path('/tmp/decrypted'))

print('✅ Encryption test passed!')
print(f'Original: {test_file.read_text()}')
print(f'Decrypted: {decrypted_path.read_text()}')
"
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Commit your changes (`git commit -m 'feat: add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details. You have full rights to use, modify, and distribute this software.

## 🆘 Support

- **Documentation**: [GitHub Wiki](https://github.com/ravikumarve/lazarus/wiki)
- **Issues**: [GitHub Issues](https://github.com/ravikumarve/lazarus/issues)
- **Email**: ravikumarve@protonmail.com
- **Security Issues**: Please report via email first

---

<p align="center">
  <em>Built with paranoia and love. For the people who hold their own keys.</em>
</p>

<p align="center">
  <a href="https://github.com/ravikumarve/lazarus/stargazers">
    ⭐ Star this repo if it protects your digital legacy
  </a>
</p>