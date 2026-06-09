# 🚀 Lazarus Protocol - Quick Start Guide

Get up and running with Lazarus Protocol in 15 minutes. This guide will walk you through installing, configuring, and testing your dead man's switch.

## ⏱️ Time to Complete: 15 Minutes

### What You'll Learn
- How to install Lazarus Protocol
- How to set up your first vault
- How to configure beneficiaries
- How to test the dead man's switch
- How to perform regular check-ins

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed ([Download Python](https://www.python.org/downloads/))
- **Git** installed ([Download Git](https://git-scm.com/downloads))
- **Basic terminal/command line knowledge**
- **A beneficiary's RSA public key** (we'll help you generate one)

### Check Your Python Version

```bash
python --version
# Should show Python 3.10 or higher
```

If you don't have Python 3.10+, install it from the official website.

---

## 🎯 Installation (3 Methods)

Choose the installation method that works best for you:

### Method 1: PyPI Package (Recommended - Easiest)

```bash
# Install Lazarus Protocol
pip install lazarus-protocol

# Verify installation
lazarus --version
```

### Method 2: Docker (Best for Isolation)

```bash
# Clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Run with Docker Compose
docker-compose up -d

# Access the dashboard
# Open http://localhost:8000 in your browser
```

### Method 3: From Source (For Developers)

```bash
# Clone the repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev]

# Verify installation
python -m cli.main --version
```

---

## 🔐 Step 1: Generate Beneficiary Keys (5 Minutes)

Your beneficiary needs an RSA key pair to decrypt your secrets. Let's generate one:

### For Your Beneficiary

```bash
# Generate RSA-4096 key pair for beneficiary
openssl genrsa -out beneficiary_private.pem 4096

# Extract public key (this is what YOU need)
openssl rsa -in beneficiary_private.pem -pubout -out beneficiary_public.pem

# Secure the private key
chmod 600 beneficiary_private.pem
```

**⚠️ IMPORTANT SECURITY NOTE:**
- **Give the `beneficiary_public.pem` file to yourself** (you'll need it for setup)
- **Give the `beneficiary_private.pem` file ONLY to your beneficiary** (they need this to decrypt)
- **Never share the private key with anyone else**
- **Store the private key securely** (encrypted USB drive, password manager, etc.)

### What Just Happened?
We created a military-grade RSA-4096 key pair. The public key encrypts your secrets, and only the private key can decrypt them. This is the foundation of Lazarus Protocol's security.

---

## 📝 Step 2: Initialize Your Vault (5 Minutes)

Now let's set up your vault with the setup wizard:

```bash
# Run the setup wizard
lazarus init
```

The wizard will ask you for:

### 1. **Your Information**
```
Enter your full name: John Doe
Enter your email: john.doe@example.com
```

### 2. **Beneficiary Information**
```
Enter beneficiary's name: Jane Doe
Enter beneficiary's email: jane.doe@example.com
Enter path to beneficiary's public key: /path/to/beneficiary_public.pem
```

### 3. **Secret File Selection**
```
Enter path to your secret file: /path/to/your/secrets.txt
```

**What should be in your secret file?**
- Private keys for crypto wallets
- Recovery phrases (seed words)
- Password manager master password
- Important access credentials
- Any sensitive information your beneficiary needs

**Example secret file (`secrets.txt`):**
```
=== Bitcoin Wallet ===
Private Key: L1aW4...
Recovery Phrase: word1 word2 word3...

=== Ethereum Wallet ===
Private Key: 0xabc123...
Recovery Phrase: alpha beta gamma...

=== Password Manager ===
Master Password: superSecretPassword123
```

### 4. **Check-in Interval**
```
Enter check-in interval in days (default: 30): 30
```

**What is the check-in interval?**
- This is how often you need to "check in" to prove you're alive
- If you don't check in within this period, the dead man's switch triggers
- Common intervals: 7 days (paranoid), 30 days (balanced), 90 days (relaxed)

### 5. **Encryption Confirmation**
```
Encrypting your secrets...
✓ Encryption complete
✓ Vault created at ~/.lazarus/encrypted_secrets.bin
✓ Configuration saved at ~/.lazarus/config.json
```

**What Just Happened?**
- Your secret file was encrypted using AES-256-GCM
- The encryption key was encrypted with your beneficiary's RSA public key
- Both the encrypted file and encrypted key were stored securely
- Your configuration was saved with strict file permissions (0o600)

---

## 🧪 Step 3: Test Your Setup (2 Minutes)

Before relying on Lazarus, let's verify everything works:

### Test 1: Check Status

```bash
# View your vault status
lazarus status
```

**Expected Output:**
```
┌─────────────────────────────────────┐
│         Lazarus Status               │
├─────────────────────────────────────┤
│ Armed State      │ ✅ Armed         │
│ Owner            │ John Doe         │
│                  │ <john@...>       │
│ Beneficiary      │ Jane Doe         │
│                  │ <jane@...>       │
│ Check-in Interval│ 30 days          │
│ Days Since Ping  │ Never checked in │
│ Days Until Trigger│ ∞ days          │
│ Last Check-in    │ Never            │
└─────────────────────────────────────┘
```

### Test 2: Perform First Check-in

```bash
# Record your first check-in
lazarus ping
```

**Expected Output:**
```
✓ Check-in recorded at 2026-04-27 10:30:00 UTC
Timer started - first check-in recorded
```

### Test 3: Verify Status After Check-in

```bash
# Check status again
lazarus status
```

**Expected Output:**
```
┌─────────────────────────────────────┐
│         Lazarus Status               │
├─────────────────────────────────────┤
│ Armed State      │ ✅ Armed         │
│ Days Since Ping  │ 0.0 days ago     │
│ Days Until Trigger│ 30.0 days       │
│ Last Check-in    │ 2026-04-27...    │
└─────────────────────────────────────┘
```

### Test 4: Simulate Trigger (Dry Run)

```bash
# Test what would happen if trigger fires
lazarus test-trigger
```

**Expected Output:**
```
🔬 Test trigger (dry run)

📋 SIMULATION DETAILS
============================================================

👤 Beneficiary:
   Name:  Jane Doe
   Email: jane.doe@example.com
   Public Key: /path/to/beneficiary_public.pem

👤 Owner:
   Name:  John Doe
   Email: john.doe@example.com

🔒 Vault:
   Encrypted file: ~/.lazarus/encrypted_secrets.bin
   File size: 1,234 bytes
   Key blob present: ✅
   Check-in interval: 30 days

⏰ Trigger Status:
   🟢 OK - 30.0 days remaining

📦 What would be sent:
   1. Email to beneficiary with subject:
      '[Lazarus] You have received an inheritance from John Doe'
   2. Attachments:
      • encrypted_secrets.bin (1,234 bytes)
      • decryption_kit.zip (standalone decrypt.py + instructions)

✅ Dry run completed successfully
⚠️  This was only a simulation - no actual delivery occurred
```

---

## 📧 Step 4: Configure Email Alerts (Optional but Recommended)

To receive email notifications when the dead man's switch is about to trigger:

### Get a SendGrid API Key

1. Sign up at [SendGrid](https://sendgrid.com/) (free tier available)
2. Create an API key in your dashboard
3. Verify your sender email address

### Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your SendGrid credentials
nano .env  # or use your preferred editor
```

**Add to `.env`:**
```bash
SENDGRID_API_KEY=SG.your_actual_api_key_here
ALERT_FROM_EMAIL=lazarus@yourdomain.com
ALERT_TO_EMAIL=your_personal_email@gmail.com
```

### Test Email Configuration

```bash
# Test email delivery (requires SendGrid configured)
python -m pytest tests/test_sendgrid_integration.py -v -m integration
```

**What Just Happened?**
- You configured email alerts for notifications
- Lazarus will send you reminders before the trigger fires
- Your beneficiary will receive the encrypted secrets when triggered

---

## 🤖 Step 5: Start the Background Agent (Optional)

For automated monitoring, start the background agent:

```bash
# Start the heartbeat agent
lazarus agent start

# Check if agent is running
lazarus status
```

**What Does the Agent Do?**
- Monitors your check-in status 24/7
- Sends reminder emails before the trigger fires
- Automatically delivers secrets when the deadline passes
- Runs as a background service (daemon)

---

## 🔄 Step 6: Regular Check-ins (Ongoing)

### Daily Check-in Routine

```bash
# Perform your daily check-in
lazarus ping
```

**Expected Output:**
```
✓ Check-in recorded at 2026-04-28 10:30:00 UTC
Timer reset - next check-in due in 30.0 days
```

### Set Up Reminders

**Option 1: Calendar Reminder**
- Add a recurring calendar event for every 7 days
- Set reminder 1 day before check-in deadline

**Option 2: Cron Job (Linux/macOS)**
```bash
# Edit crontab
crontab -e

# Add weekly reminder (every Sunday at 9 AM)
0 9 * * 0 /usr/bin/notify-send "Lazarus Check-in" "Time to check in with Lazarus Protocol"
```

**Option 3: Task Scheduler (Windows)**
- Create a scheduled task
- Set to run weekly
- Action: Run `lazarus ping`

---

## 🆘 Emergency Procedures

### Extend Deadline (Panic Button)

If you need more time (e.g., traveling, no internet access):

```bash
# Extend deadline by 30 days
lazarus freeze --days 30
```

**Expected Output:**
```
✓ Deadline extended by 30 days
New check-in interval: 60 days
Next check-in due in 60.0 days
```

### Stop the Agent

```bash
# Stop the background agent
lazarus agent stop
```

### Disarm the Switch

If you want to temporarily disable the dead man's switch:

```bash
# Edit configuration
nano ~/.lazarus/config.json

# Change "armed": true to "armed": false
```

---

## 🎯 What Just Happened? Summary

You've successfully:
1. ✅ Installed Lazarus Protocol
2. ✅ Generated beneficiary encryption keys
3. ✅ Created and encrypted your vault
4. ✅ Configured your dead man's switch
5. ✅ Tested the entire system
6. ✅ Performed your first check-in
7. ✅ Set up email alerts (optional)

**Your secrets are now protected by military-grade encryption and will only be delivered to your beneficiary if you stop checking in.**

---

## 📊 Next Steps

### Recommended Actions

1. **Set Up Regular Reminders**
   - Calendar events every 7 days
   - Email notifications
   - Mobile app reminders

2. **Test with Your Beneficiary**
   - Share the decryption instructions
   - Verify they have the private key
   - Practice decryption with test data

3. **Configure Backup Storage**
   - Enable IPFS for decentralized storage
   - Set up regular backups
   - Test recovery procedures

4. **Monitor Your Status**
   - Check status weekly
   - Verify agent is running
   - Review logs periodically

### Advanced Configuration

- **IPFS Integration**: See [IPFS_STORAGE_GUIDE.md](IPFS_STORAGE_GUIDE.md)
- **Production Deployment**: See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **Security Best Practices**: See [SECURITY.md](SECURITY.md)
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## ❓ Frequently Asked Questions

### Q: What happens if I forget to check in?
**A:** You'll receive reminder emails before the trigger fires. If you still don't check in, your encrypted secrets will be delivered to your beneficiary after the check-in interval passes.

### Q: Can I change my beneficiary later?
**A:** Yes, but you'll need to re-encrypt your secrets with the new beneficiary's public key. Use `lazarus update-secret` or re-run `lazarus init`.

### Q: Is my data safe?
**A:** Yes. Your secrets are encrypted with AES-256-GCM and the encryption key is encrypted with RSA-4096. Even if someone steals your vault, they cannot decrypt it without the beneficiary's private key.

### Q: What if I lose my beneficiary's private key?
**A:** Without the beneficiary's private key, your secrets cannot be decrypted. Always keep multiple secure backups of the private key.

### Q: Can I use multiple beneficiaries?
**A:** Currently, Lazarus supports one primary beneficiary. You can encrypt your secrets multiple times with different public keys if needed.

---

## 🆘 Need Help?

### Documentation
- [Installation Guide](INSTALLATION.md) - Detailed installation instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Configuration Guide](CONFIGURATION.md) - Advanced configuration options
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

### Community
- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues) - Report bugs
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions) - Ask questions
- Email: ravikumarve@protonmail.com

### Security Issues
For security vulnerabilities, email: ravikumarve@protonmail.com with subject "SECURITY: Vulnerability in Lazarus Protocol"

---

## 🎉 Congratulations!

You've successfully set up your dead man's switch with Lazarus Protocol. Your digital legacy is now protected, and your beneficiary will receive your encrypted secrets if something happens to you.

**Remember to check in regularly!**

```bash
# Set a reminder to check in weekly
lazarus ping
```

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
