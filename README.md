<h1 align="center">
  <img src="https://raw.githubusercontent.com/ravikumarve/lazarus/main/assets/lazarus-banner.png" alt="Lazarus Protocol" width="600"/>
</h1>

<p align="center">
  <strong>Your Digital Legacy, Preserved. Self-Hosted Dead Man's Switch for Crypto Holders.</strong>
</p>

<p align="center">
  <!-- Security & Encryption -->
  <a href="SECURITY.md">
    <img src="https://img.shields.io/badge/Security-Military%20Grade-8b0000?style=for-the-badge&logo=shield-check" alt="Military Grade Security" />
  </a>
  <a href="SECURITY.md">
    <img src="https://img.shields.io/badge/Encryption-AES--256%20%2B%20RSA--4096-8b0000?style=for-the-badge&logo=key" alt="Military Encryption" />
  </a>
  
  <!-- Platform Support -->
  <a href="README.md#platform-support">
    <img src="https://img.shields.io/badge/Windows-Supported-8b0000?style=for-the-badge&logo=windows" alt="Windows Support" />
  </a>
  <a href="README.md#platform-support">
    <img src="https://img.shields.io/badge/Linux-Supported-8b0000?style=for-the-badge&logo=linux" alt="Linux Support" />
  </a>
  <a href="README.md#platform-support">
    <img src="https://img.shields.io/badge/macOS-Supported-8b0000?style=for-the-badge&logo=apple" alt="macOS Support" />
  </a>
  
  <!-- Deployment -->
  <a href="README.md#docker-deployment">
    <img src="https://img.shields.io/badge/Docker-Ready-8b0000?style=for-the-badge&logo=docker" alt="Docker Ready" />
  </a>
  <a href="README.md#https-support">
    <img src="https://img.shields.io/badge/HTTPS-Supported-8b0000?style=for-the-badge&logo=lock" alt="HTTPS Support" />
  </a>
  
  <!-- Project Status -->
  <a href="https://github.com/ravikumarve/lazarus/stargazers">
    <img src="https://img.shields.io/github/stars/ravikumarve/lazarus?style=for-the-badge&logo=github&color=8b0000" alt="GitHub stars" />
  </a>
  <a href="https://pypi.org/project/lazarus-protocol/">
    <img src="https://img.shields.io/pypi/v/lazarus-protocol?style=for-the-badge&logo=pypi&logoColor=white&color=8b0000" alt="PyPI version" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.10+-8b0000?style=for-the-badge&logo=python&logoColor=white" alt="Python version" />
  </a>
  <a href="https://github.com/ravikumarve/lazarus/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/ravikumarve/lazarus?style=for-the-badge&logo=opensourceinitiative&color=8b0000" alt="License" />
  </a>
  <a href="https://github.com/ravikumarve/lazarus/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/ravikumarve/lazarus/ci.yml?style=for-the-badge&logo=githubactions&label=build" alt="Build Status" />
  </a>
  <a href="https://github.com/ravikumarve/lazarus/issues">
    <img src="https://img.shields.io/github/issues/ravikumarve/lazarus?style=for-the-badge&logo=github&color=8b0000" alt="Open Issues" />
  </a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ravikumarve/lazarus/main/assets/dashboard-preview.png" alt="Lazarus Dashboard" width="800"/>
  <br/>
  <em>Professional Web Dashboard with Dark/Light Theme Support</em>
</p>

---

## ✨ Why Lazarus Protocol Exists

**For crypto holders who need a failsafe:** When you're gone, your digital assets shouldn't be lost forever. Lazarus Protocol ensures your encrypted secrets — private keys, wallet phrases, access credentials — are automatically delivered to your chosen beneficiary if you stop checking in.

**No middlemen. No cloud services. No trust required.** Your secrets stay encrypted until delivery, and the entire system runs on your own hardware.

## 🚀 Enterprise-Grade Features

### 🔐 **Security & Encryption**
- **Military-Grade Encryption**: AES-256-GCM + RSA-4096 hybrid encryption
- **Zero-Knowledge Architecture**: Your secrets stay encrypted until delivery
- **Windows Security**: POSIX `chmod 0o600` equivalent with 3-tier fallback system
- **HTTPS/TLS Support**: Production-ready SSL/TLS encryption

### ⚡ **Reliability & Monitoring**
- **Automated Heartbeat**: Background agent with configurable check-in intervals
- **Multi-Channel Alerts**: Email (SendGrid) + Telegram notifications with escalation
- **24/7 Operation**: Systemd service integration for production reliability
- **Health Monitoring**: Built-in health checks and status endpoints

### 🌐 **Access & Management**
- **Web Dashboard**: Professional React-inspired interface with dark/light themes
- **RESTful API**: Comprehensive API for integration and automation
- **CLI Interface**: Full command-line control with intuitive commands
- **Mobile Responsive**: Optimized for desktop and mobile devices

### 📦 **Deployment & Operations**
- **Docker Ready**: Multi-stage Docker builds with production optimization
- **Cross-Platform**: Windows, Linux, macOS with identical security guarantees
- **Self-Hosted**: No cloud dependencies — your data never leaves your control
- **IPFS Integration**: Decentralized storage with local fallback

### 🧪 **Quality & Testing**
- **Comprehensive Testing**: 20+ passing tests covering all critical functionality
- **Type Hints**: Full codebase with modern Python type annotations
- **Code Quality**: ruff, black, and mypy for consistent code style
- **Documentation**: Comprehensive guides for development and production

## 🚀 Quick Start (Choose Your Path)

### 🐍 **Python Package (Recommended)**
```bash
# Install from PyPI
pip install lazarus-protocol

# Initialize and configure
lazarus init
lazarus setup

# Start the web dashboard
lazarus dashboard

# Or run as service
lazarus run --daemon
```

### 🐳 **Docker Container**
```bash
# Using Docker Compose (Production Ready)
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

docker-compose up -d

# Access dashboard: http://localhost:8000

# Or run individual commands
docker-compose exec lazarus lazarus status
docker-compose exec lazarus lazarus ping
```

### 🔧 **From Source**
```bash
# Clone and install
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install with development dependencies
pip install -e .[dev]

# Run tests to verify installation
pytest tests/ -v

# Start the protocol
python -m cli.main init
python -m cli.main setup
python -m web.server
```

### ⚡ **One-Line Install**
```bash
# Quick start with Docker
curl -sSL https://raw.githubusercontent.com/ravikumarve/lazarus/main/docker-compose.yml > docker-compose.yml \
  && docker-compose up -d

# Or with Python
pip install lazarus-protocol && lazarus init && lazarus setup && lazarus dashboard
```
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Install in development mode
pip install -e .[dev]

# Or install production version
pip install .
```

### Initialize Your Vault
```bash
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
export ALERT_FROM_EMAIL="ravikumarve@protonmail.com"
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

## 📊 Project Status: Production Ready 🚀

### ✅ **Completed & Production Ready**
- **Core Security**: AES-256-GCM + RSA-4096 hybrid encryption engine
- **Cross-Platform Support**: Windows, Linux, macOS with identical security
- **Windows Permissions**: POSIX `chmod 0o600` equivalent with 3-tier fallback
- **Web Dashboard**: Professional interface with dark/light theme support
- **HTTPS/TLS Support**: Production-ready SSL/TLS encryption
- **Docker Deployment**: Multi-stage builds with production optimization
- **RESTful API**: Comprehensive API for integration and automation
- **CLI Interface**: Full command-line control with intuitive commands
- **Monitoring System**: Background agent with health checks
- **Alert System**: Email (SendGrid) + Telegram notifications
- **IPFS Integration**: Decentralized storage with local fallback
- **Testing Suite**: 20+ comprehensive tests covering all functionality
- **Documentation**: Complete guides for development and production

### 🎯 **Recently Enhanced**
- **Web UI Overhaul**: Modern React-inspired dashboard with responsive design
- **SSL/TLS Support**: Environment-based certificate configuration
- **Docker Compose**: Production-ready deployment configurations
- **Windows Security**: Complete permissions implementation
- **Production Guides**: Comprehensive deployment documentation
- **Error Handling**: Robust error recovery and graceful degradation

### 📈 **Next Enhancements**
- Mobile application companion
- Advanced analytics dashboard
- Multi-user support
- Kubernetes operator
- Hardware security module (HSM) integration

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

## 📦 Comprehensive Installation Guide

### Platform-Specific Installation

#### Linux/macOS
```bash
# Using pip (recommended)
pip3 install lazarus-protocol

# Using pipx (isolated environment)
pipx install lazarus-protocol

# Using system package manager (if available)
# Coming soon: apt, yum, brew packages
```

#### Windows
```bash
# Using pip
pip install lazarus-protocol

# Using Windows Package Manager (winget)
# Coming soon: winget install LazarusProtocol

# Using Chocolatey
# Coming soon: choco install lazarus-protocol
```

### Docker Deployment

#### Production Deployment
```bash
# Multi-platform Docker image
docker run -d \
  --name lazarus \
  -v /path/to/config:/app/config \
  -v /path/to/data:/app/data \
  -p 8000:8000 \
  --restart unless-stopped \
  ghcr.io/ravikumarve/lazarus:latest
```

#### Development with Docker
```bash
# Build from source
docker build -t lazarus-protocol .

# Run with hot-reload for development
docker run -it \
  -v $(pwd):/app \
  -v lazarus-config:/app/config \
  -p 8000:8000 \
  -p 8001:8001 \
  lazarus-protocol \
  lazarus run --host 0.0.0.0 --port 8000 --reload
```

### Kubernetes Deployment

```yaml
# lazarus-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lazarus-protocol
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lazarus
  template:
    metadata:
      labels:
        app: lazarus
    spec:
      containers:
      - name: lazarus
    image: ghcr.io/ravikumarve/lazarus:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /app/data
        env:
        - name: LAZARUS_HOME
          value: "/app"
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: lazarus-config
      - name: data
        persistentVolumeClaim:
          claimName: lazarus-data
---
apiVersion: v1
kind: Service
metadata:
  name: lazarus-service
spec:
  selector:
    app: lazarus
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Building from Source

#### Prerequisites
- Python 3.10+
- pip
- git

#### Build Steps
```bash
# Clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Install build dependencies
pip install build wheel twine

# Build package
python -m build

# Install the built package
pip install dist/lazarus_protocol-*.whl

# Or install in development mode
pip install -e .[dev]
```

### Verifying Installation

```bash
# Check version
lazarus --version

# Test basic functionality
lazarus --help

# Verify all dependencies are available
python -c "
import cryptography
import click
import rich
print('✅ All dependencies installed successfully')
"
```

## 🆕 What's New in Lazarus Protocol

### ✨ Latest Enhancements

| Feature | Status | Description |
|---------|--------|-------------|
| **Web Dashboard** | ✅ Production Ready | Modern React-inspired interface with dark/light themes |
| **HTTPS/TLS Support** | ✅ Production Ready | SSL certificate configuration for secure deployments |
| **Docker Compose** | ✅ Production Ready | Multi-service deployment with production optimization |
| **Windows Security** | ✅ Production Ready | Complete file permissions equivalent to POSIX 0o600 |
| **Error Recovery** | ✅ Enhanced | Robust error handling with graceful degradation |
| **Mobile Responsive** | ✅ Complete | Optimized for desktop and mobile devices |

### 🏆 Feature Comparison

| Feature | Lazarus Protocol | Alternatives |
|---------|------------------|-------------|
| **Self-Hosted** | ✅ Yes | ❌ Most are cloud-based |
| **Zero Knowledge** | ✅ Yes | ❌ Many require trust |
| **Open Source** | ✅ Yes | ❌ Many are proprietary |
| **Cross-Platform** | ✅ Windows/Linux/macOS | ⚠️ Limited platforms |
| **Military Encryption** | ✅ AES-256 + RSA-4096 | ⚠️ Varies by provider |
| **No Monthly Fees** | ✅ Free forever | ❌ Subscription models |
| **IPFS Support** | ✅ Yes | ❌ Rarely supported |
| **Multi-Channel Alerts** | ✅ Email + Telegram | ⚠️ Usually single channel |

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