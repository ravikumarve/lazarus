# Lazarus Protocol — Quick Start Guide

> *"Your secrets survive you."*

This guide will get you up and running with Lazarus in 5 minutes. No technical knowledge required.

---

## What is Lazarus?

Lazarus is a **Dead Man's Switch** for your digital assets. If you stop checking in (or pass away), your encrypted secrets are automatically delivered to your chosen beneficiary.

**Key features:**
- Your secrets are encrypted with military-grade encryption (AES-256)
- Only your beneficiary can decrypt them — nobody else
- Runs on your own computer — no cloud, no middleman
- Check in daily with a simple command (or it triggers automatically)

---

## Step 1: Install

### Requirements
- Python 3.9 or newer
- Linux, Mac, or Windows

### Installation

```bash
# Download Lazarus
git clone https://github.com/yourname/lazarus
cd lazarus

# Install dependencies (use virtual environment recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Verify Installation

```bash
python -m lazarus doctor
```

You should see green `[OK]` checks for most items.

---

## Step 2: Set Up Your Vault

Run the setup wizard:

```bash
python -m lazarus init
```

The wizard will ask for:

1. **Your name and email** — Where reminders are sent
2. **Your secret file** — The file you want to protect (PDF, text, etc.)
3. **Beneficiary info** — Who receives your secrets:
   - Their name and email
   - Path to their public key file (ask them to generate one if they don't have it)
4. **Check-in interval** — How often you need to check in (default: 30 days)
5. **Telegram (optional)** — For instant alerts on your phone

### Example Session

```
$ python -m lazarus init

Welcome to Lazarus Protocol!

Your name: John Doe
Your email: john@example.com
Secret file path: /home/john/important.pdf
Beneficiary name: Jane Doe
Beneficiary email: jane@example.com
Beneficiary public key: /home/john/jane_public.pem
Check-in interval (days): 30

Vault created! ✓
Encrypted file: /home/john/.lazarus/vault/encrypted_secrets.bin
```

---

## Step 3: Give Beneficiary Their Private Key

Your beneficiary needs:
1. Their **private key file** (`.pem`) — they should have generated this already
2. They should keep it safe and never share it

If they don't have keys yet, they can generate them:

```bash
# On beneficiary's computer:
python -c "from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.asymmetric import rsa; key = rsa.generate_private_key(public_exponent=65537, key_size=2048); open('private_key.pem', 'wb').write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())); open('public_key.pem', 'wb').write(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))"
```

---

## Step 4: Start the Heartbeat Agent

The agent pings daily to confirm you're alive. Run it in the background:

### Linux/Mac (screen or systemd)

```bash
# Using screen (keeps running when you close terminal)
screen -S lazarus
python -m lazarus agent start
# Press Ctrl+A, then D to detach

# Or using systemd (runs automatically on boot)
sudo cp lazarus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lazarus
sudo systemctl start lazarus
```

### Windows

```powershell
# Run in background
Start-Process python -ArgumentList "-m lazarus agent start" -WindowStyle Hidden
```

---

## Step 5: Check In Daily (or automate it)

### Manual Check-in

```bash
python -m lazarus ping
```

You'll see: `Check-in recorded. Days until trigger: 30.0`

### Automated Check-in (recommended)

Add to your crontab to auto-ping:

```bash
# Edit crontab
crontab -e

# Add this line (pings at 9 AM daily):
0 9 * * * /path/to/venv/bin/python -m lazarus ping
```

---

## Step 6: Check Your Status

```bash
python -m lazarus status
```

You'll see a table with:
- ARMED/DISARMED status (should be ARMED)
- Days since ping
- Days until trigger
- Beneficiary count

---

## If You Need More Time

```bash
# Extend deadline by 30 days
python -m lazarus freeze --days 30
```

This is your panic button. Use it if you're going on vacation or need more time.

---

## What Happens When It Triggers

**Day 20:** You get a reminder email
**Day 25:** Telegram alert (if configured)
**Day 28:** Final warning
**Day 30:** Your beneficiary receives an email with:
- The encrypted vault file
- A decryption kit (Python script + instructions)

Your beneficiary just runs the script, enters their password, and gets your secrets.

---

## Troubleshooting

### `python -m lazarus doctor` shows failures

**"Python version too old":**
```bash
python --version  # Should be 3.9 or higher
```

**"Module not found":**
```bash
pip install -r requirements.txt
```

**"Config not found":**
```bash
python -m lazarus init  # Run setup first
```

### Agent isn't running

```bash
# Check agent status
python -m lazarus agent status

# Start it
python -m lazarus agent start

# Check logs
tail -f ~/.lazarus/events.log
```

### Forgot to check in

```bash
# Extend deadline
python -m lazarus freeze --days 30
```

### Beneficiary didn't receive email

1. Check spam folder
2. Verify email address in `python -m lazarus status`
3. Check delivery log: `cat ~/.lazarus/delivery.log`

### Want to test without actually sending

```bash
python -m lazarus test-trigger
```

---

## Security Notes

- **Never share your private key** — only your beneficiary needs theirs
- **Keep backup keys** — in case the original is lost
- **Check in regularly** — or automate it with crontab
- **The encrypted file is useless without the private key** — even if stolen

---

## Getting Help

- GitHub Issues: https://github.com/yourname/lazarus/issues
- Documentation: https://github.com/yourname/lazarus#readme

---

*Built with security and privacy in mind. For the people who hold their own keys.*
