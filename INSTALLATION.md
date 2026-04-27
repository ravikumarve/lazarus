# 📦 Lazarus Protocol - Installation Guide

Comprehensive installation instructions for Lazarus Protocol across all platforms and deployment methods.

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Verification Steps](#verification-steps)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

---

## 💻 System Requirements

### Minimum Requirements
- **Python**: 3.10 or higher
- **RAM**: 512 MB minimum, 1 GB recommended
- **Disk Space**: 100 MB for installation, 500 MB for data
- **Network**: Internet connection for initial setup and updates

### Recommended Requirements
- **Python**: 3.11 or higher
- **RAM**: 2 GB or more
- **Disk Space**: 1 GB or more
- **Network**: Stable internet connection for IPFS and email alerts

### Operating System Support
- ✅ **Linux**: Ubuntu 20.04+, Debian 11+, CentOS 8+, Arch Linux
- ✅ **macOS**: macOS 11 (Big Sur) or later
- ✅ **Windows**: Windows 10 or later
- ✅ **Docker**: Any platform with Docker installed

---

## 🚀 Installation Methods

Choose the installation method that best fits your needs:

### Method Comparison

| Method | Difficulty | Isolation | Updates | Best For |
|--------|-----------|-----------|---------|----------|
| **PyPI** | ⭐ Easy | ❌ No | ✅ Easy | Quick setup, personal use |
| **Docker** | ⭐⭐ Medium | ✅ Yes | ✅ Easy | Production, testing |
| **Source** | ⭐⭐⭐ Hard | ❌ No | ✅ Manual | Development, customization |

---

## 📦 Method 1: PyPI Installation (Recommended)

### Prerequisites

```bash
# Check Python version (must be 3.10+)
python --version

# If Python is not installed or too old:
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11 python3-pip

# macOS (using Homebrew):
brew install python@3.11

# Windows:
# Download from https://www.python.org/downloads/
```

### Installation Steps

#### Step 1: Install Lazarus Protocol

```bash
# Install the latest stable version
pip install lazarus-protocol

# Or install a specific version
pip install lazarus-protocol==0.1.0
```

#### Step 2: Verify Installation

```bash
# Check version
lazarus --version

# View help
lazarus --help

# List available commands
lazarus --help
```

#### Step 3: Initialize Configuration

```bash
# Run the setup wizard
lazarus init

# This will create ~/.lazarus/ directory with:
# - config.json (your configuration)
# - encrypted_secrets.bin (your encrypted vault)
```

### Upgrading

```bash
# Upgrade to the latest version
pip install --upgrade lazarus-protocol

# Check what version you have
lazarus --version
```

### Uninstalling

```bash
# Remove the package
pip uninstall lazarus-protocol

# Remove configuration and data (optional)
rm -rf ~/.lazarus/
```

---

## 🐳 Method 2: Docker Installation

### Prerequisites

```bash
# Install Docker
# Ubuntu/Debian:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS:
# Download Docker Desktop from https://www.docker.com/products/docker-desktop

# Windows:
# Download Docker Desktop from https://www.docker.com/products/docker-desktop

# Verify Docker installation
docker --version
docker-compose --version
```

### Installation Steps

#### Option A: Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start the service
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Option B: Using Docker Run

```bash
# Pull the latest image
docker pull ghcr.io/ravikumarve/lazarus:latest

# Run the container
docker run -d \
  --name lazarus \
  -v ~/.lazarus:/app/.lazarus \
  -v $(pwd)/.env:/app/.env \
  -p 8000:8000 \
  --restart unless-stopped \
  ghcr.io/ravikumarve/lazarus:latest

# Check if running
docker ps | grep lazarus
```

#### Option C: Build from Source

```bash
# Clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Build the image
docker build -t lazarus-protocol .

# Run the container
docker run -d \
  --name lazarus \
  -v ~/.lazarus:/app/.lazarus \
  -p 8000:8000 \
  --restart unless-stopped \
  lazarus-protocol
```

### Docker Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect lazarus_data

# Backup volume
docker run --rm -v lazarus_data:/data -v $(pwd):/backup \
  alpine tar -czf /backup/lazarus-backup.tar.gz /data

# Restore volume
docker run --rm -v lazarus_data:/data -v $(pwd):/backup \
  alpine tar -xzf /backup/lazarus-backup.tar.gz -C /
```

### Updating Docker Installation

```bash
# Stop and remove old container
docker-compose down

# Pull latest images
docker-compose pull

# Start updated containers
docker-compose up -d

# Or rebuild from source
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Uninstalling Docker Installation

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: This deletes all data)
docker-compose down -v

# Remove images
docker rmi ghcr.io/ravikumarve/lazarus:latest

# Or remove all Lazarus-related containers and images
docker system prune -a
```

---

## 🔧 Method 3: Installation from Source

### Prerequisites

```bash
# Install Python 3.10+
# See PyPI installation section above

# Install Git
# Ubuntu/Debian:
sudo apt install git

# macOS:
brew install git

# Windows:
# Download from https://git-scm.com/downloads

# Install build tools
# Ubuntu/Debian:
sudo apt install build-essential python3-dev

# macOS:
xcode-select --install

# Windows:
# Install Visual Studio Build Tools
```

### Installation Steps

#### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Or clone a specific branch
git clone -b develop https://github.com/ravikumarve/lazarus.git
cd lazarus
```

#### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Verify activation (should show (venv) in prompt)
which python  # Linux/macOS
where python  # Windows
```

#### Step 3: Install Dependencies

```bash
# Install in development mode (recommended for contributors)
pip install -e .[dev]

# Or install in production mode
pip install -e .

# Verify installation
python -m cli.main --version
```

#### Step 4: Run Tests (Optional)

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_encryption.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Development Workflow

```bash
# Always activate virtual environment first
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Make changes to code
# ...

# Run tests
pytest tests/ -v

# Format code
black .
isort .

# Run linting
ruff check .

# Type checking
mypy .
```

### Updating Source Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin main

# Update dependencies
pip install --upgrade -e .[dev]

# Run tests to verify
pytest tests/ -v
```

### Uninstalling Source Installation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment directory
rm -rf venv/

# Remove cloned repository
cd ..
rm -rf lazarus/

# Remove configuration and data (optional)
rm -rf ~/.lazarus/
```

---

## 🖥️ Platform-Specific Instructions

### Linux Installation

#### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3 python3-pip python3-venv

# Install system dependencies
sudo apt install git build-essential python3-dev

# Install Lazarus
pip install --user lazarus-protocol

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
lazarus --version
```

#### CentOS/RHEL/Fedora

```bash
# Install Python and pip
sudo dnf install python3 python3-pip python3-devel

# Install system dependencies
sudo dnf install git gcc

# Install Lazarus
pip3 install --user lazarus-protocol

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
lazarus --version
```

#### Arch Linux

```bash
# Install Python and pip
sudo pacman -S python python-pip

# Install system dependencies
sudo pacman -S git base-devel

# Install Lazarus
pip install --user lazarus-protocol

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
lazarus --version
```

### macOS Installation

#### Using Homebrew (Recommended)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install Lazarus
pip3 install lazarus-protocol

# Verify installation
lazarus --version
```

#### Using MacPorts

```bash
# Install MacPorts if not already installed
# Download from https://www.macports.org/

# Install Python
sudo port install python311

# Install Lazarus
pip3 install lazarus-protocol

# Verify installation
lazarus --version
```

### Windows Installation

#### Using pip (Recommended)

```powershell
# Install Python from https://www.python.org/downloads/
# Make sure to check "Add Python to PATH" during installation

# Open PowerShell or Command Prompt

# Install Lazarus
pip install lazarus-protocol

# Verify installation
lazarus --version
```

#### Using Chocolatey

```powershell
# Install Chocolatey if not already installed
# Run PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python
choco install python

# Install Lazarus
pip install lazarus-protocol

# Verify installation
lazarus --version
```

#### Using Windows Package Manager (winget)

```powershell
# Install Python
winget install Python.Python.3.11

# Install Lazarus
pip install lazarus-protocol

# Verify installation
lazarus --version
```

---

## ✅ Verification Steps

After installation, verify everything is working correctly:

### Step 1: Check Version

```bash
lazarus --version
```

**Expected Output:**
```
Lazarus Protocol, version 0.1.0
```

### Step 2: View Help

```bash
lazarus --help
```

**Expected Output:**
```
Usage: lazarus [OPTIONS] COMMAND [ARGS]...

  ⚰️  Lazarus Protocol — Self-hosted dead man's switch for crypto holders.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init            Setup wizard
  ping            Manual check-in
  status          Show vault status
  agent           Manage the background heartbeat agent.
  freeze          Panic button — extend the trigger deadline by N days.
  test-trigger    Dry run — simulate delivery without actually sending anything.
  update-secret   Replace the encrypted secret file with a new one.
```

### Step 3: Test Dependencies

```bash
# Test Python imports
python -c "
import cryptography
import click
import rich
print('✅ All dependencies installed successfully')
"

# Test encryption module
python -c "
from core.encryption import generate_rsa_keypair
priv, pub = generate_rsa_keypair()
print('✅ Encryption module working')
"
```

### Step 4: Initialize Test Configuration

```bash
# Run setup wizard (you can cancel after testing)
lazarus init

# Or create a test configuration manually
mkdir -p ~/.lazarus
echo '{"test": true}' > ~/.lazarus/config.json

# Check if configuration exists
lazarus status
```

### Step 5: Run Test Suite (Optional)

```bash
# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_encryption.py -v
pytest tests/test_config.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

---

## 🔧 Troubleshooting

### Common Installation Issues

#### Issue: "python: command not found"

**Solution:**
```bash
# Check if python3 is available
python3 --version

# Create alias (add to ~/.bashrc or ~/.zshrc)
alias python=python3
alias pip=pip3
```

#### Issue: "pip: command not found"

**Solution:**
```bash
# Install pip
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py

# Or use system package manager
# Ubuntu/Debian:
sudo apt install python3-pip

# macOS:
brew install python
```

#### Issue: "Permission denied" during installation

**Solution:**
```bash
# Install to user directory
pip install --user lazarus-protocol

# Or use virtual environment
python -m venv venv
source venv/bin/activate
pip install lazarus-protocol
```

#### Issue: "ModuleNotFoundError: No module named 'cryptography'"

**Solution:**
```bash
# Install build dependencies
# Ubuntu/Debian:
sudo apt install build-essential python3-dev libssl-dev

# macOS:
xcode-select --install
brew install openssl

# Reinstall cryptography
pip install --force-reinstall cryptography
```

#### Issue: Docker container won't start

**Solution:**
```bash
# Check Docker logs
docker logs lazarus

# Check container status
docker ps -a | grep lazarus

# Restart container
docker restart lazarus

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Issue: "FileNotFoundError: Lazarus config not found"

**Solution:**
```bash
# Run setup wizard
lazarus init

# Or create configuration manually
mkdir -p ~/.lazarus
lazarus init
```

### Platform-Specific Issues

#### Linux: "ImportError: No module named '_ctypes'"

**Solution:**
```bash
# Install libffi-dev
sudo apt install libffi-dev

# Reinstall Python packages
pip install --force-reinstall lazarus-protocol
```

#### macOS: "openssl" related errors

**Solution:**
```bash
# Install OpenSSL via Homebrew
brew install openssl

# Set OpenSSL path
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"
pip install --force-reinstall cryptography
```

#### Windows: "Microsoft Visual C++ 14.0 is required"

**Solution:**
```powershell
# Download and install Visual Studio Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Or use pre-built wheels
pip install --only-binary :all: lazarus-protocol
```

### Getting Help

If you encounter issues not covered here:

1. **Check the logs:**
   ```bash
   # View detailed logs
   lazarus --verbose status

   # Or check log files
   tail -f ~/.lazarus/logs/lazarus.log
   ```

2. **Run in debug mode:**
   ```bash
   export LAZARUS_LOG_LEVEL=DEBUG
   lazarus status
   ```

3. **Search existing issues:**
   - [GitHub Issues](https://github.com/ravikumarve/lazarus/issues)

4. **Ask for help:**
   - [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions)
   - Email: ravikumarve@protonmail.com

---

## 🗑️ Uninstallation

### Complete Removal

#### PyPI Installation

```bash
# Uninstall package
pip uninstall lazarus-protocol

# Remove configuration and data
rm -rf ~/.lazarus/

# Remove any remaining files
rm -rf ~/.local/lib/python*/site-packages/lazarus*

# Clean up pip cache
pip cache purge
```

#### Docker Installation

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker rmi ghcr.io/ravikumarve/lazarus:latest

# Remove all Lazarus-related resources
docker system prune -a --filter label=com.lazarus.app
```

#### Source Installation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv/

# Remove cloned repository
cd ..
rm -rf lazarus/

# Remove configuration and data
rm -rf ~/.lazarus/
```

### Backup Before Uninstalling

```bash
# Backup configuration
tar -czf lazarus-backup-$(date +%Y%m%d).tar.gz ~/.lazarus/

# Backup Docker volumes
docker run --rm -v lazarus_data:/data -v $(pwd):/backup \
  alpine tar -czf /backup/lazarus-data-backup.tar.gz /data
```

---

## 📚 Next Steps

After successful installation:

1. **Quick Start:** Follow the [Quick Start Guide](QUICKSTART.md)
2. **Configuration:** See [Configuration Guide](CONFIGURATION.md)
3. **Security:** Read [Security Guide](SECURITY.md)
4. **Deployment:** Check [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)

---

## 🆘 Support

### Documentation
- [Quick Start](QUICKSTART.md) - Get started in 15 minutes
- [Security Guide](SECURITY.md) - Security best practices
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [API Reference](API.md) - Complete API documentation

### Community
- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues) - Report bugs
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions) - Ask questions
- Email: ravikumarve@protonmail.com

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
