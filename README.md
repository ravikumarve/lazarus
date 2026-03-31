# ⚰️ Lazarus Protocol

> *"Your secrets survive you."*

Lazarus is a self-hosted, open-source Dead Man's Switch for crypto holders.
If you stop checking in, your encrypted secrets are automatically delivered to your chosen beneficiary — no middleman, no cloud service, no trust required.

---

## 🚀 Current Implementation Status

### ✅ Implemented Features
- **Core Encryption Engine**: AES-256-GCM + RSA-4096 hybrid encryption
- **Configuration System**: JSON-based config with secure file permissions
- **CLI Framework**: Click-based command structure with Rich output
- **Setup Wizard**: Interactive initialization with questionary prompts
- **Heartbeat Logic**: Complete escalation ladder and trigger system
- **Manual Check-in**: Ping command for resetting countdown timer
- **Test Suite**: Comprehensive tests covering all core functionality

### ⏳ In Progress / Planned Features
- **Email Alerts**: SendGrid integration for reminder/final warnings
- **Telegram Alerts**: Bot integration for mobile notifications
- **IPFS Storage**: Distributed storage layer for redundancy
- **Agent Scheduler**: APScheduler background process
- **Delivery System**: Beneficiary email with decryption kit
- **GUI Interface**: Desktop application (Pro tier)

---

## 🛠️ Current CLI Commands

| Command | Status | Description |
|---|---|---|
| `lazarus init` | ✅ **Implemented** | Setup wizard — create your vault |
| `lazarus ping` | ✅ **Implemented** | Manual check-in (resets timer) |
| `lazarus status` | ⏳ **Stub** | Show vault status, days remaining |
| `lazarus agent start` | ⏳ **Stub** | Start background heartbeat agent |
| `lazarus agent stop` | ⏳ **Stub** | Stop the agent |
| `lazarus freeze --days N` | ⏳ **Stub** | Panic button — extend deadline |
| `lazarus test-trigger` | ⏳ **Stub** | Dry run — simulate delivery |
| `lazarus update-secret` | ⏳ **Stub** | Replace secret file with new one |

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.10+
- Cryptography libraries (auto-installed)
- SendGrid account (for email alerts)
- Telegram bot (optional, for mobile alerts)

### Quick Start

```bash
# Clone and install
git clone https://github.com/ravikumarve/lazarus
cd lazarus
pip install -r requirements.txt

# Initialize your vault
python -m lazarus init

# Set up environment variables for alerts
echo 'export SENDGRID_API_KEY="your_sendgrid_key"' >> ~/.bashrc
echo 'export ALERT_FROM_EMAIL="your@email.com"' >> ~/.bashrc
echo 'export TELEGRAM_BOT_TOKEN="your_bot_token"' >> ~/.bashrc
source ~/.bashrc

# Test the encryption (manual check-in coming soon)
python -c "
from core.encryption import generate_rsa_keypair
priv, pub = generate_rsa_keypair()
print('RSA keys generated successfully!')
"
```

### Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# Run tests
python -m pytest tests/ -v

# Run coverage report
python -m pytest tests/ --cov=.
```

---

## 🏗️ Architecture Overview

```
lazarus/
├── core/
│   ├── encryption.py      ✅ AES-256 + RSA hybrid encryption engine
│   ├── storage.py         ⏳ IPFS upload/download + local fallback
│   └── config.py          ✅ User config management (~/.lazarus/config.json)
│
├── cli/
│   ├── main.py            ✅ CLI entry point structure
│   └── setup.py           ✅ Interactive setup wizard
│
├── agent/
│   ├── heartbeat.py       ✅ Heartbeat logic + escalation ladder
│   └── alerts.py          ⏳ Email + Telegram alert system
│
├── contracts/             ⏳ (Optional) Solidity vault for on-chain trigger
│
├── tests/                 ✅ Full test suite (20 passing tests)
├── docs/                  📚 Guides and tutorials
└── examples/              🎯 Example secrets files and configs
```

---

## 🔐 Security Model

### ✅ Implemented Protections
- **Military-grade encryption**: AES-256-GCM + RSA-4096 hybrid scheme
- **Memory zeroing**: Sensitive keys cleared from memory after use
- **Secure file permissions**: Config files locked to owner (chmod 600)
- **No cloud dependencies**: Fully local operation by default
- **Tamper detection**: GCM authentication tags prevent ciphertext modification

### 🔄 In Progress
- **IPFS redundancy**: Distributed storage for survivability
- **Multi-factor delivery**: Email + IPFS + local fallback
- **Beneficiary verification**: Test decryption during setup
- **Rate limiting**: Protection against brute force attacks

### Threat Model

| Threat | Protection | Status |
|---|---|---|
| Someone steals vault file | Useless without private key | ✅ **Implemented** |
| Intercepted email | Encrypted file unreadable | ⏳ **In Progress** |
| Lazarus servers hacked | No servers — fully local | ✅ **Implemented** |
| Beneficiary loses key | Verification during setup | ⏳ **In Progress** |
| Early trigger accident | Escalation ladder + freeze | ✅ **Implemented** |
| Forget to ping | Daily reminders + alerts | ⏳ **In Progress** |

---

## 🗓️ Roadmap

### Q2 2025 - Core Completion
- [x] Project architecture and encryption engine
- [x] Configuration system with secure storage
- [x] CLI framework and setup wizard
- [x] Heartbeat logic and escalation system
- [x] Manual check-in (ping command)
- [ ] Email alert system (SendGrid integration)
- [ ] Telegram alert system
- [ ] IPFS storage layer
- [ ] Agent scheduler implementation

### Q3 2025 - Production Ready
- [ ] Beneficiary delivery system
- [ ] Decryption kit generator
- [ ] Multi-platform packaging
- [ ] Comprehensive documentation
- [ ] Security audit and penetration testing

### Q4 2025 - Advanced Features
- [ ] Desktop GUI application
- [ ] Multi-beneficiary support
- [ ] Legal document storage
- [ ] Blockchain integration (optional)
- [ ] Mobile app companion

---

## 💰 Pricing Tiers

| Tier | Price | Status | Includes |
|---|---|---|---|
| **Basic** | $35 | ✅ **Available** | Full source code + PDF guide |
| **Pro** | $79 | ⏳ **Q3 2025** | Source + packaged desktop app + video walkthrough |
| **Enterprise** | $199 | ⏳ **Q4 2025** | Multi-user + legal support + priority updates |

*Note: All tiers include lifetime updates and self-hosted rights.*

---

## 🆘 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt
```

**"Config not found" error:**
```bash
# Run the setup wizard first
python -m lazarus init
```

**Encryption errors:**
```bash
# Test basic encryption functionality
python -m pytest tests/test_encryption.py -v
```

**Test ping functionality:**
```bash
# Test manual check-in
python -m lazarus ping
```

**Permission errors:**
```bash
# Check file permissions on config
ls -la ~/.lazarus/
chmod 600 ~/.lazarus/config.json
```

### Testing Your Setup

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

---

## 🧪 Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_encryption.py
python -m pytest tests/test_config.py
python -m pytest tests/test_heartbeat.py

# With coverage report
python -m pytest tests/ --cov=. --cov-report=html
```

### Code Style

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Manual formatting check
python -m black . --check
python -m isort . --check-only
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📜 License

MIT License — do whatever you want with it.

---

## 🙋‍♂️ Support

- **Documentation**: [GitHub Wiki](https://github.com/ravikumarve/lazarus/wiki)
- **Issues**: [GitHub Issues](https://github.com/ravikumarve/lazarus/issues)
- **Email**: ravikumarve@protonmail.com
- **Security**: Please report security issues via email

---

*Built with paranoia and love. For the people who hold their own keys.*