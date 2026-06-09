# 🔧 Lazarus Protocol - Troubleshooting Guide

Comprehensive troubleshooting documentation for Lazarus Protocol. Solutions to common issues, error messages, and recovery procedures.

## 📋 Table of Contents

- [Troubleshooting Overview](#troubleshooting-overview)
- [Common Issues](#common-issues)
- [Error Messages](#error-messages)
- [Debug Mode](#debug-mode)
- [Recovery Procedures](#recovery-procedures)
- [Platform-Specific Issues](#platform-specific-issues)
- [Getting Help](#getting-help)

---

## 🔍 Troubleshooting Overview

### Troubleshooting Methodology

When encountering issues with Lazarus Protocol, follow this systematic approach:

```
┌─────────────────────────────────────────────────────────────┐
│                    Troubleshooting Flow                       │
└─────────────────────────────────────────────────────────────┘

1. Identify the Problem
   └─ What are you trying to do?
   └─ What error message are you seeing?
   └─ When did the problem start?

2. Check the Basics
   └─ Is Lazarus installed correctly?
   └─ Is configuration valid?
   └─ Are files accessible?

3. Review Logs
   └─ Check Lazarus logs
   └─ Check system logs
   └─ Look for error patterns

4. Try Common Solutions
   └─ Restart the service
   └─ Reinstall dependencies
   └─ Restore from backup

5. Escalate if Needed
   └─ Search existing issues
   └─ Ask for help
   └─ Report bug if needed
```

### Quick Diagnostic Commands

```bash
# Check installation
lazarus --version

# Check configuration
lazarus status

# Check file permissions
ls -la ~/.lazarus/

# Check logs
tail -f ~/.lazarus/logs/lazarus.log

# Check dependencies
python -c "import cryptography, click, rich; print('✅ Dependencies OK')"
```

---

## 🐛 Common Issues

### Installation Issues

#### Issue: "python: command not found"

**Symptoms:**
```bash
$ python --version
bash: python: command not found
```

**Causes:**
- Python not installed
- Python not in PATH
- Using `python3` instead of `python`

**Solutions:**

**Solution 1: Install Python**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# macOS
brew install python

# Windows
# Download from https://www.python.org/downloads/
```

**Solution 2: Create Alias**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'alias python=python3' >> ~/.bashrc
echo 'alias pip=pip3' >> ~/.bashrc
source ~/.bashrc
```

**Solution 3: Use python3 directly**
```bash
python3 --version
pip3 install lazarus-protocol
```

---

#### Issue: "pip: command not found"

**Symptoms:**
```bash
$ pip install lazarus-protocol
bash: pip: command not found
```

**Causes:**
- pip not installed
- pip not in PATH

**Solutions:**

**Solution 1: Install pip**
```bash
# Ubuntu/Debian
sudo apt install python3-pip

# macOS
brew install python

# Windows
# Included with Python installer
```

**Solution 2: Use get-pip.py**
```bash
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
```

**Solution 3: Use python3 -m pip**
```bash
python3 -m pip install lazarus-protocol
```

---

#### Issue: "Permission denied" during installation

**Symptoms:**
```bash
$ pip install lazarus-protocol
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Causes:**
- Trying to install to system directory
- Insufficient permissions

**Solutions:**

**Solution 1: Install to user directory**
```bash
pip install --user lazarus-protocol
```

**Solution 2: Use virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install lazarus-protocol
```

**Solution 3: Use sudo (not recommended)**
```bash
sudo pip install lazarus-protocol
```

---

### Configuration Issues

#### Issue: "FileNotFoundError: Lazarus config not found"

**Symptoms:**
```bash
$ lazarus status
❌ Lazarus not initialized.
Run: python -m lazarus init
```

**Causes:**
- Configuration not created
- Configuration deleted
- Wrong configuration path

**Solutions:**

**Solution 1: Run setup wizard**
```bash
lazarus init
```

**Solution 2: Check if configuration exists**
```bash
ls -la ~/.lazarus/config.json
```

**Solution 3: Create configuration manually**
```bash
mkdir -p ~/.lazarus
lazarus init
```

---

#### Issue: "ConfigCorruptedError: Config file is missing required fields"

**Symptoms:**
```bash
$ lazarus status
❌ Config file is corrupted: Config file is missing required fields
```

**Causes:**
- Manual editing error
- Incomplete configuration
- Version mismatch

**Solutions:**

**Solution 1: Restore from backup**
```bash
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

**Solution 2: Re-run setup wizard**
```bash
# Backup current config first
cp ~/.lazarus/config.json ~/.lazarus/config.json.backup

# Re-run setup
lazarus init
```

**Solution 3: Fix configuration manually**
```bash
# Open configuration
nano ~/.lazarus/config.json

# Ensure all required fields are present:
# - owner_name
# - owner_email
# - beneficiary.name
# - beneficiary.email
# - beneficiary.public_key_path
# - vault.secret_file_path
# - vault.encrypted_file_path
# - vault.key_blob
```

---

#### Issue: "beneficiary public key not found"

**Symptoms:**
```bash
$ lazarus status
❌ Config file is corrupted: beneficiary public key not found: /path/to/key.pem
```

**Causes:**
- Public key file moved/deleted
- Wrong path in configuration
- File permissions issue

**Solutions:**

**Solution 1: Locate public key**
```bash
# Search for public key
find ~ -name "*public*.pem" -o -name "*beneficiary*.pem"

# Or check common locations
ls -la ~/beneficiary_public.pem
ls -la ~/.ssh/beneficiary_public.pem
```

**Solution 2: Update configuration with correct path**
```bash
# Edit configuration
nano ~/.lazarus/config.json

# Update beneficiary.public_key_path with correct path
```

**Solution 3: Regenerate public key**
```bash
# If you have the private key, extract public key
openssl rsa -in beneficiary_private.pem -pubout -out beneficiary_public.pem

# Update configuration
nano ~/.lazarus/config.json
```

---

### Encryption Issues

#### Issue: "DecryptionError: Failed to decrypt file"

**Symptoms:**
```bash
$ lazarus test-trigger
❌ Error during test trigger: DecryptionError: Failed to decrypt file
```

**Causes:**
- Wrong beneficiary private key
- Corrupted encrypted file
- Key blob mismatch

**Solutions:**

**Solution 1: Verify beneficiary private key**
```bash
# Check if private key exists
ls -la beneficiary_private.pem

# Verify key format
openssl rsa -in beneficiary_private.pem -check -noout

# Test decryption with known good data
```

**Solution 2: Verify encrypted file integrity**
```bash
# Check if file exists
ls -la ~/.lazarus/encrypted_secrets.bin

# Check file size (should be > 0)
du -h ~/.lazarus/encrypted_secrets.bin

# Re-encrypt if corrupted
lazarus update-secret /path/to/secrets.txt
```

**Solution 3: Verify key blob**
```bash
# Check if key_blob is present in config
grep "key_blob" ~/.lazarus/config.json

# Should be base64-encoded string
# If empty or corrupted, re-encrypt
lazarus update-secret /path/to/secrets.txt
```

---

#### Issue: "InvalidTag: Authentication failed"

**Symptoms:**
```bash
$ lazarus test-trigger
❌ Error during test trigger: InvalidTag: Authentication failed
```

**Causes:**
- Encrypted file tampered with
- Wrong nonce used
- Corrupted authentication tag

**Solutions:**

**Solution 1: Restore from backup**
```bash
# Restore encrypted file from backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

**Solution 2: Re-encrypt secrets**
```bash
# Re-encrypt with fresh keys
lazarus update-secret /path/to/secrets.txt
```

**Solution 3: Verify file integrity**
```bash
# Check for file corruption
md5sum ~/.lazarus/encrypted_secrets.bin

# Compare with backup
md5sum backup/encrypted_secrets.bin
```

---

### Agent Issues

#### Issue: "Agent won't start"

**Symptoms:**
```bash
$ lazarus agent start
❌ Failed to start agent: [error message]
```

**Causes:**
- Agent already running
- Configuration error
- Missing dependencies

**Solutions:**

**Solution 1: Check if agent is already running**
```bash
# Check for running processes
ps aux | grep lazarus

# If running, stop first
lazarus agent stop
```

**Solution 2: Check configuration**
```bash
# Validate configuration
lazarus status

# Fix any errors
lazarus init
```

**Solution 3: Install missing dependencies**
```bash
# Install APScheduler
pip install APScheduler

# Or install all dependencies
pip install -r requirements.txt
```

---

#### Issue: "Agent stops unexpectedly"

**Symptoms:**
```bash
$ lazarus agent start
✓ Agent started successfully

# Later...
$ ps aux | grep lazarus
# No process found
```

**Causes:**
- Unhandled exception
- System resource limits
- Configuration error

**Solutions:**

**Solution 1: Check logs**
```bash
# View agent logs
tail -f ~/.lazarus/logs/lazarus.log

# Look for errors or exceptions
grep ERROR ~/.lazarus/logs/lazarus.log
```

**Solution 2: Run in foreground for debugging**
```bash
# Run agent in foreground
python -m agent.heartbeat

# Watch for errors
```

**Solution 3: Check system resources**
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check process limits
ulimit -a
```

---

### Email Alert Issues

#### Issue: "Email not being sent"

**Symptoms:**
```bash
$ lazarus test-trigger
❌ Email not configured
```

**Causes:**
- SendGrid not configured
- Invalid API key
- Network issues

**Solutions:**

**Solution 1: Configure SendGrid**
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env

# Add:
# SENDGRID_API_KEY=your_actual_api_key
# ALERT_FROM_EMAIL=your_email@example.com
# ALERT_TO_EMAIL=recipient@example.com
```

**Solution 2: Verify API key**
```bash
# Test SendGrid API key
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"personalizations":[{"to":[{"email":"test@example.com"}]}],"from":{"email":"test@example.com"},"subject":"Test","content":[{"type":"text/plain","value":"Test"}]}'
```

**Solution 3: Check network connectivity**
```bash
# Test DNS resolution
nslookup api.sendgrid.com

# Test connectivity
ping api.sendgrid.com

# Test HTTPS
curl -I https://api.sendgrid.com
```

---

#### Issue: "SendGrid API error: 401 Unauthorized"

**Symptoms:**
```bash
$ lazarus test-trigger
❌ SendGrid API error: 401 Unauthorized
```

**Causes:**
- Invalid API key
- Expired API key
- Wrong API key

**Solutions:**

**Solution 1: Verify API key**
```bash
# Check .env file
cat .env | grep SENDGRID_API_KEY

# Ensure no extra spaces or quotes
```

**Solution 2: Regenerate API key**
```bash
# Log in to SendGrid dashboard
# Navigate to Settings > API Keys
# Create new API key
# Update .env file
```

**Solution 3: Test API key**
```bash
# Test with curl
curl -X GET https://api.sendgrid.com/v3/user/profile \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

### IPFS Issues

#### Issue: "IPFS connection failed"

**Symptoms:**
```bash
$ lazarus ipfs test
❌ IPFS connection failed: Connection refused
```

**Causes:**
- IPFS daemon not running
- Wrong IPFS API URL
- Network issues

**Solutions:**

**Solution 1: Start IPFS daemon**
```bash
# Start IPFS daemon
ipfs daemon &

# Verify it's running
ipfs id
```

**Solution 2: Check IPFS configuration**
```bash
# Check IPFS API URL
cat ~/.lazarus/config.json | grep ipfs_api_url

# Should be: http://127.0.0.1:5001
```

**Solution 3: Test IPFS connectivity**
```bash
# Test IPFS API
curl http://127.0.0.1:5001/api/v0/id

# Should return JSON with peer ID
```

---

#### Issue: "IPFS upload failed"

**Symptoms:**
```bash
$ lazarus ipfs store ~/.lazarus/encrypted_secrets.bin
❌ IPFS upload failed: [error message]
```

**Causes:**
- File too large
- Insufficient IPFS resources
- Network timeout

**Solutions:**

**Solution 1: Check file size**
```bash
# Check file size
du -h ~/.lazarus/encrypted_secrets.bin

# IPFS may have size limits
# Consider compressing large files
```

**Solution 2: Increase timeout**
```bash
# Edit configuration
nano ~/.lazarus/config.json

# Increase timeout in storage_config
{
  "storage_config": {
    "timeout": 60
  }
}
```

**Solution 3: Check IPFS resources**
```bash
# Check IPFS repo size
ipfs repo stat

# Check IPFS peers
ipfs swarm peers
```

---

### Web Dashboard Issues

#### Issue: "Dashboard won't load"

**Symptoms:**
```
Browser shows: "This site can't be reached"
```

**Causes:**
- Web server not running
- Wrong port
- Firewall blocking

**Solutions:**

**Solution 1: Start web server**
```bash
# Start web server
python -m web.server

# Or use CLI
lazarus dashboard
```

**Solution 2: Check port**
```bash
# Check if port is in use
netstat -tulpn | grep 8000

# Try different port
python -m web.server --port 8001
```

**Solution 3: Check firewall**
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

---

#### Issue: "Dashboard shows errors"

**Symptoms:**
```
Dashboard shows: "Error loading configuration"
```

**Causes:**
- Configuration error
- Permission error
- Missing files

**Solutions:**

**Solution 1: Check configuration**
```bash
# Validate configuration
lazarus status

# Fix any errors
lazarus init
```

**Solution 2: Check file permissions**
```bash
# Check permissions
ls -la ~/.lazarus/

# Fix permissions
chmod 700 ~/.lazarus
chmod 600 ~/.lazarus/config.json
```

**Solution 3: Check web server logs**
```bash
# View web server logs
tail -f ~/.lazarus/logs/web-server.log

# Look for errors
grep ERROR ~/.lazarus/logs/web-server.log
```

---

## 📝 Error Messages

### Configuration Errors

#### "ConfigCorruptedError: Config file is not valid JSON"

**Meaning:** Configuration file is not valid JSON

**Solution:**
```bash
# Validate JSON
python -m json.tool ~/.lazarus/config.json

# Fix syntax errors
nano ~/.lazarus/config.json
```

#### "ConfigCorruptedError: Config file is missing required fields"

**Meaning:** Configuration is missing required fields

**Solution:**
```bash
# Re-run setup wizard
lazarus init

# Or manually add missing fields
nano ~/.lazarus/config.json
```

### Encryption Errors

#### "DecryptionError: Failed to decrypt file"

**Meaning:** Decryption failed (wrong key or corrupted file)

**Solution:**
```bash
# Verify beneficiary private key
openssl rsa -in beneficiary_private.pem -check -noout

# Re-encrypt if needed
lazarus update-secret /path/to/secrets.txt
```

#### "InvalidTag: Authentication failed"

**Meaning:** Encrypted file was tampered with

**Solution:**
```bash
# Restore from backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/

# Or re-encrypt
lazarus update-secret /path/to/secrets.txt
```

### Network Errors

#### "ConnectionError: Failed to connect to SendGrid"

**Meaning:** Cannot connect to SendGrid API

**Solution:**
```bash
# Test network connectivity
ping api.sendgrid.com

# Check firewall
sudo ufw status

# Test HTTPS
curl -I https://api.sendgrid.com
```

#### "TimeoutError: Request timed out"

**Meaning:** Request took too long

**Solution:**
```bash
# Increase timeout in configuration
nano ~/.lazarus/config.json

# Add to storage_config:
{
  "storage_config": {
    "timeout": 60
  }
}
```

### File System Errors

#### "PermissionError: [Errno 13] Permission denied"

**Meaning:** Insufficient file permissions

**Solution:**
```bash
# Fix file permissions
chmod 600 ~/.lazarus/config.json
chmod 600 ~/.lazarus/encrypted_secrets.bin
chmod 700 ~/.lazarus
```

#### "FileNotFoundError: [Errno 2] No such file or directory"

**Meaning:** File or directory not found

**Solution:**
```bash
# Create missing directory
mkdir -p ~/.lazarus

# Or restore from backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

---

## 🐛 Debug Mode

### Enabling Debug Logging

#### Method 1: Environment Variable

```bash
# Set debug log level
export LAZARUS_LOG_LEVEL=DEBUG

# Run command
lazarus status
```

#### Method 2: Command Line Flag

```bash
# Run with verbose flag
lazarus --verbose status
```

#### Method 3: Configuration File

```bash
# Edit configuration
nano ~/.lazarus/config.json

# Add logging configuration (if supported)
```

### Viewing Debug Logs

```bash
# View all logs
tail -f ~/.lazarus/logs/lazarus.log

# View only errors
grep ERROR ~/.lazarus/logs/lazarus.log

# View only debug messages
grep DEBUG ~/.lazarus/logs/lazarus.log

# View recent logs
tail -100 ~/.lazarus/logs/lazarus.log
```

### Debugging Common Issues

#### Debugging Configuration Issues

```bash
# Enable debug logging
export LAZARUS_LOG_LEVEL=DEBUG

# Load configuration
python -c "
from core.config import load_config, validate_config
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    config = load_config()
    errors = validate_config(config)
    if errors:
        print('Configuration errors:')
        for error in errors:
            print(f'  - {error}')
    else:
        print('Configuration is valid')
        print(f'Owner: {config.owner_name}')
        print(f'Beneficiary: {config.beneficiary.name}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
"
```

#### Debugging Encryption Issues

```bash
# Test encryption
python -c "
from core.encryption import generate_rsa_keypair, encrypt_file, decrypt_file
from pathlib import Path
import tempfile
import logging

logging.basicConfig(level=logging.DEBUG)

# Generate test keypair
priv, pub = generate_rsa_keypair()
print('✓ Generated test keypair')

# Create test file
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
    f.write('Test secret content')
    test_file = Path(f.name)

print(f'✓ Created test file: {test_file}')

# Encrypt
try:
    encrypted_path, key_blob = encrypt_file(test_file, pub, Path('/tmp'))
    print(f'✓ Encrypted to: {encrypted_path}')
    print(f'✓ Key blob size: {len(key_blob)} bytes')
except Exception as e:
    print(f'✗ Encryption failed: {e}')
    import traceback
    traceback.print_exc()

# Decrypt
try:
    decrypted_path = decrypt_file(encrypted_path, key_blob, priv, Path('/tmp/decrypted'))
    print(f'✓ Decrypted to: {decrypted_path}')

    # Verify content
    original = test_file.read_text()
    decrypted = decrypted_path.read_text()
    if original == decrypted:
        print('✓ Content matches!')
    else:
        print('✗ Content mismatch!')
except Exception as e:
    print(f'✗ Decryption failed: {e}')
    import traceback
    traceback.print_exc()

# Cleanup
test_file.unlink()
encrypted_path.unlink()
decrypted_path.unlink()
print('✓ Cleanup complete')
"
```

#### Debugging Agent Issues

```bash
# Run agent in foreground
python -m agent.heartbeat

# Watch for errors and exceptions
# Press Ctrl+C to stop
```

---

## 🔄 Recovery Procedures

### Recovering from Corrupted Configuration

#### Step 1: Backup Current Configuration

```bash
# Backup current configuration
cp ~/.lazarus/config.json ~/.lazarus/config.json.corrupted
```

#### Step 2: Restore from Backup

```bash
# Restore from backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

#### Step 3: Verify Configuration

```bash
# Validate configuration
lazarus status

# Test functionality
lazarus test-trigger
```

### Recovering from Lost Beneficiary Key

#### Step 1: Check for Backups

```bash
# Search for backup keys
find ~ -name "*beneficiary*private*.pem"
find ~ -name "*private*.pem"

# Check common backup locations
ls -la ~/Documents/backups/
ls -la ~/Dropbox/backups/
```

#### Step 2: Contact Beneficiary

```bash
# Ask beneficiary if they have their private key
# They should have it stored securely
```

#### Step 3: Re-encrypt with New Key

```bash
# If key is permanently lost, generate new key pair
openssl genrsa -out beneficiary_private_new.pem 4096
openssl rsa -in beneficiary_private_new.pem -pubout -out beneficiary_public_new.pem

# Re-encrypt secrets
lazarus update-secret /path/to/secrets.txt
# Use new public key during setup

# Securely provide new private key to beneficiary
```

### Recovering from System Crash

#### Step 1: Check System Status

```bash
# Check disk space
df -h

# Check memory
free -h

# Check processes
ps aux | grep lazarus
```

#### Step 2: Restore Configuration

```bash
# Restore from backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

#### Step 3: Restart Services

```bash
# Start agent
lazarus agent start

# Verify status
lazarus status
```

### Recovering from Accidental Deletion

#### Step 1: Check for Backups

```bash
# List available backups
ls -la lazarus-backup-*.tar.gz

# Find most recent backup
ls -lt lazarus-backup-*.tar.gz | head -1
```

#### Step 2: Restore from Backup

```bash
# Restore from most recent backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

#### Step 3: Verify Restore

```bash
# Verify configuration
lazarus status

# Test functionality
lazarus test-trigger
```

---

## 💻 Platform-Specific Issues

### Linux Issues

#### Issue: "ImportError: No module named '_ctypes'"

**Solution:**
```bash
# Install libffi-dev
sudo apt install libffi-dev

# Reinstall cryptography
pip install --force-reinstall cryptography
```

#### Issue: "Permission denied on ~/.lazarus"

**Solution:**
```bash
# Fix permissions
sudo chown -R $USER:$USER ~/.lazarus
chmod 700 ~/.lazarus
chmod 600 ~/.lazarus/*
```

### macOS Issues

#### Issue: "openssl" related errors

**Solution:**
```bash
# Install OpenSSL via Homebrew
brew install openssl

# Set OpenSSL path
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"

# Reinstall cryptography
pip install --force-reinstall cryptography
```

#### Issue: "Command not found: lazarus"

**Solution:**
```bash
# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

### Windows Issues

#### Issue: "Microsoft Visual C++ 14.0 is required"

**Solution:**
```powershell
# Download and install Visual Studio Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Or use pre-built wheels
pip install --only-binary :all: lazarus-protocol
```

#### Issue: "File path too long"

**Solution:**
```powershell
# Enable long path support
# Requires Windows 10 or later

# Or use shorter paths
# Move Lazarus to C:\lazarus\
```

---

## 🆘 Getting Help

### Self-Help Resources

#### Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 15 minutes
- [Installation Guide](INSTALLATION.md) - Installation instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Configuration Guide](CONFIGURATION.md) - Configuration options

#### Search Existing Issues

```bash
# Search GitHub issues
# Visit: https://github.com/ravikumarve/lazarus/issues

# Use search terms:
# - Error message
# - Symptom description
# - Platform name
```

### Community Support

#### GitHub Discussions

- **URL:** https://github.com/ravikumarve/lazarus/discussions
- **When to use:** Questions, feature requests, general discussion

#### Email Support

- **Email:** ravikumarve@protonmail.com
- **When to use:** Security issues, private questions
- **Response time:** Within 48 hours

### Reporting Bugs

#### Before Reporting

1. **Search existing issues**
   - Check if bug already reported
   - Add comments to existing issues

2. **Gather information**
   - Lazarus version
   - Python version
   - Operating system
   - Error messages
   - Steps to reproduce

3. **Create minimal reproduction**
   - Simplify the issue
   - Remove unnecessary steps
   - Test on clean system

#### Bug Report Template

```markdown
## Description
[Brief description of the bug]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Lazarus Version: [version]
- Python Version: [version]
- Operating System: [OS]
- Installation Method: [PyPI/Docker/Source]

## Error Messages
```
[Paste error messages here]
```

## Additional Context
[Any other relevant information]
```

### Security Issues

#### Reporting Security Vulnerabilities

**DO NOT:**
- Create public issues
- Disclose publicly
- Post on forums

**DO:**
- Email: ravikumarve@protonmail.com
- Subject: "SECURITY: Vulnerability in Lazarus Protocol"
- Include detailed description
- Include steps to reproduce

**Response Time:** Within 48 hours

---

## 📚 Additional Resources

### Debugging Tools

#### Python Debugger

```bash
# Run with debugger
python -m pdb -m cli.main status

# Common pdb commands:
# - n: next line
# - s: step into function
# - c: continue
# - p variable: print variable
# - q: quit
```

#### System Monitoring

```bash
# Monitor system resources
htop

# Monitor network
iftop

# Monitor disk I/O
iotop
```

### Log Analysis

#### Log Rotation

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/lazarus

# Add:
~/.lazarus/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

#### Log Aggregation

```bash
# View all logs
cat ~/.lazarus/logs/*.log

# Search for errors
grep -r ERROR ~/.lazarus/logs/

# Search for specific time range
grep "2026-04-27" ~/.lazarus/logs/*.log
```

---

## 🎯 Conclusion

Troubleshooting is an essential skill for maintaining Lazarus Protocol. By following this guide and using the systematic approach outlined, you can resolve most issues quickly and effectively.

**Remember:**
- Always check logs first
- Keep regular backups
- Test changes before deploying
- Don't hesitate to ask for help

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
