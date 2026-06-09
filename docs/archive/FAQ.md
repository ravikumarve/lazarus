# ❓ Lazarus Protocol - FAQ

Frequently asked questions about Lazarus Protocol, covering security, functionality, and usage.

## 📋 Table of Contents

- [General Questions](#general-questions)
- [Security Questions](#security-questions)
- [Functionality Questions](#functionality-questions)
- [Technical Questions](#technical-questions)
- [Troubleshooting Questions](#troubleshooting-questions)
- [Billing and Licensing](#billing-and-licensing)
- [Support and Contact](#support-and-contact)

---

## 🌟 General Questions

### What is Lazarus Protocol?

**Lazarus Protocol** is a self-hosted dead man's switch for crypto holders. It ensures your encrypted secrets (private keys, wallet phrases, access credentials) are automatically delivered to your chosen beneficiaries if you stop checking in.

**Key Features:**
- Military-grade encryption (AES-256-GCM + RSA-4096)
- Zero-knowledge architecture (no cloud dependencies)
- Cross-platform support (Windows, Linux, macOS)
- Multi-channel alerts (Email + Telegram)
- Web dashboard with dark/light themes
- IPFS integration for decentralized storage

---

### Who is Lazarus Protocol for?

Lazarus Protocol is designed for:

**Primary Users:**
- Crypto holders with significant assets ($50K-$500K+ portfolios)
- Individuals concerned about digital legacy
- People who want to ensure their beneficiaries can access their digital assets

**Use Cases:**
- Ensuring family can access crypto assets if something happens to you
- Protecting digital inheritance
- Automating delivery of sensitive information
- Providing peace of mind for asset holders

---

### How does Lazarus Protocol work?

Lazarus Protocol works in 5 simple steps:

1. **Setup**: You encrypt your secrets and specify a beneficiary
2. **Monitoring**: The background agent runs 24/7, waiting for your periodic check-ins
3. **Escalation**: If you miss check-ins, alerts escalate from reminders to final warnings
4. **Delivery**: If all alerts go unanswered, encrypted secrets are delivered with decryption instructions
5. **Recovery**: Your beneficiary receives everything needed to decrypt your legacy

**Timeline Example (30-day interval):**
- Day 0: You check in
- Day 23: Reminder email (7 days before)
- Day 27: Warning email (3 days before)
- Day 29: Final warning (1 day before)
- Day 30: Trigger fires, secrets delivered

---

### Is Lazarus Protocol free?

**Yes!** Lazarus Protocol is open-source and free to use forever.

**Free Tier Features:**
- Full dead man's switch functionality
- Military-grade encryption
- Email alerts
- Web dashboard
- CLI interface
- Local storage

**Paid Tiers (Optional):**
- **Managed Cloud**: $49/mo - Hosted solution with support
- **Enterprise**: $499/mo - Priority support, custom features
- **Lifetime**: $199 - One-time payment, lifetime access

**No hidden fees, no subscriptions required for core functionality.**

---

### What platforms does Lazarus Protocol support?

Lazarus Protocol supports:

**Operating Systems:**
- ✅ **Windows**: Windows 10 or later
- ✅ **Linux**: Ubuntu 20.04+, Debian 11+, CentOS 8+, Arch Linux
- ✅ **macOS**: macOS 11 (Big Sur) or later

**Deployment Methods:**
- ✅ **PyPI Package**: Easy installation via pip
- ✅ **Docker**: Containerized deployment
- ✅ **Source Code**: Build from source
- ✅ **Systemd**: Linux service integration
- ✅ **Kubernetes**: Cloud-native deployment

**All platforms have identical security guarantees and functionality.**

---

### How long does it take to set up?

**Setup time: 15-30 minutes**

**Breakdown:**
- Installation: 5 minutes
- Key generation: 5 minutes
- Setup wizard: 10 minutes
- Testing: 5-10 minutes

**First-time users can be up and running in under 30 minutes.**

---

## 🔒 Security Questions

### How secure is Lazarus Protocol?

Lazarus Protocol uses **military-grade encryption**:

**Encryption Specifications:**
- **File Encryption**: AES-256-GCM (256-bit security)
- **Key Encryption**: RSA-4096-OAEP (4096-bit security)
- **Hash Function**: SHA-256
- **Random Number Generation**: OS CSPRNG

**Security Guarantees:**
- ✅ Confidentiality: Secrets encrypted before storage
- ✅ Integrity: GCM authentication tags prevent tampering
- ✅ Authenticity: RSA signatures verify origin
- ✅ Forward Secrecy: Random AES keys per encryption

**Your secrets are useless without your beneficiary's private key.**

---

### Can anyone decrypt my secrets?

**No.** Only your beneficiary can decrypt your secrets.

**Why:**
- Secrets are encrypted with AES-256-GCM
- AES key is encrypted with your beneficiary's RSA-4096 public key
- Only the corresponding RSA private key can decrypt the AES key
- Without the private key, encrypted data is mathematically impossible to decrypt

**Even if someone steals your encrypted vault file, they cannot read it.**

---

### What happens if my computer is hacked?

**Your secrets remain safe.**

**Protection:**
- Encrypted vault file is useless without private key
- Configuration file contains only metadata
- Key blob is encrypted with RSA-4096
- File permissions restrict access (600)

**However, if the hacker has access while you're logged in:**
- They could access decrypted secrets in memory
- They could perform check-ins on your behalf
- They could modify configuration

**Mitigation:**
- Use full disk encryption (BitLocker, LUKS)
- Keep system updated
- Use strong passwords
- Enable two-factor authentication

---

### Is my data stored in the cloud?

**No.** Lazarus Protocol is self-hosted.

**Storage Options:**
- **Primary**: Local storage on your machine
- **Optional**: IPFS (decentralized storage)
- **Optional**: Pinata (cloud IPFS pinning)

**No cloud services are required for core operation.**

**Benefits:**
- Your data never leaves your control
- No cloud service can access your secrets
- No monthly fees for storage
- Works offline

---

### What if I lose my beneficiary's private key?

**Your secrets cannot be recovered.**

**Why:**
- Private key is required to decrypt AES key
- Without private key, encrypted data is useless
- No backdoor or recovery mechanism exists

**Prevention:**
- Store private key in multiple secure locations
- Use hardware security modules (HSMs)
- Keep encrypted backups
- Educate beneficiary on key security

**If key is lost, you must re-encrypt secrets with a new key pair.**

---

### How do I protect my beneficiary's private key?

**Best practices for key storage:**

**1. Hardware Security Modules (HSMs)**
```bash
# Use YubiKey for key storage
yubico-piv-tool -a generate -s 9c -o beneficiary_public.pem
```

**2. Encrypted USB Drives**
```bash
# Encrypt USB drive with LUKS
sudo cryptsetup luksFormat /dev/sdb1
```

**3. Password Managers**
- Bitwarden
- 1Password
- KeePassXC

**4. Paper Wallets**
- Print private key on paper
- Store in safe or safety deposit box

**Never share private key via email, chat, or unencrypted storage.**

---

### What if Lazarus Protocol is compromised?

**Your secrets remain safe.**

**Why:**
- Encryption is done client-side
- Encrypted data is useless without keys
- No backdoor in encryption
- Open source code can be audited

**However, if the code is compromised:**
- Attacker could modify encryption
- Attacker could add backdoors
- Attacker could exfiltrate keys

**Mitigation:**
- Use verified releases
- Review code before installation
- Keep software updated
- Monitor for security advisories

---

### Is Lazarus Protocol open source?

**Yes!** Lazarus Protocol is 100% open source.

**Benefits:**
- Code can be audited by anyone
- No proprietary algorithms
- No hidden backdoors
- Community review and improvement
- Transparency and trust

**Repository:** https://github.com/ravikumarve/lazarus

**License:** MIT License

---

## ⚙️ Functionality Questions

### What happens if I forget to check in?

**You'll receive multiple reminders before the trigger fires.**

**Escalation Timeline (30-day interval):**
- **Day 23**: Reminder email
- **Day 27**: Warning email
- **Day 29**: Final warning email
- **Day 30**: Trigger fires, secrets delivered

**You have 7 days of warnings before delivery.**

---

### Can I extend the deadline if I need more time?

**Yes!** Use the freeze command:

```bash
# Extend deadline by 30 days
lazarus freeze --days 30

# Extend deadline by 7 days
lazarus freeze --days 7
```

**This is useful for:**
- Travel without internet access
- Emergencies
- Extended vacations
- Medical situations

---

### Can I change my beneficiary?

**Yes, but you'll need to re-encrypt your secrets.**

**Process:**
1. Generate new beneficiary key pair
2. Re-encrypt secrets with new public key
3. Update configuration
4. Provide new private key to beneficiary

**Command:**
```bash
# Re-run setup wizard
lazarus init

# Or update secret file
lazarus update-secret /path/to/secrets.txt
```

---

### Can I have multiple beneficiaries?

**Currently, Lazarus Protocol supports one primary beneficiary.**

**Workarounds:**
1. **Encrypt multiple times**: Encrypt secrets for each beneficiary separately
2. **Use a trusted third party**: Designate a trusted person to distribute secrets
3. **Wait for multi-beneficiary support**: Coming in future versions

**Future versions will support multiple beneficiaries with configurable delivery rules.**

---

### What types of secrets can I store?

**You can store any type of sensitive information:**

**Common Examples:**
- Crypto private keys
- Wallet recovery phrases (seed words)
- Password manager master passwords
- Access credentials
- Financial information
- Important documents
- Personal messages

**File Types Supported:**
- Text files (.txt)
- JSON files (.json)
- Any file format (encrypted as binary)

**Size Limit:** No hard limit, but larger files take longer to encrypt/decrypt.

---

### How often should I check in?

**Recommended intervals:**

| Interval | Use Case | Risk Level |
|----------|----------|------------|
| **7 days** | High-risk situations, frequent travel | Low risk of accidental trigger |
| **30 days** | Balanced approach, regular check-ins | Medium risk |
| **90 days** | Low-risk situations, infrequent check-ins | High risk of accidental trigger |

**Most users choose 30 days as a good balance.**

---

### Can I check in from multiple devices?

**Yes!** You can check in from any device with access to your Lazarus installation.

**Methods:**
- **CLI**: `lazarus ping`
- **Web Dashboard**: Click "Check In" button
- **API**: `POST /api/v1/checkin`
- **Automated**: Cron job or scheduled task

**All methods reset the countdown timer.**

---

### What happens if the trigger fires accidentally?

**You can disarm the switch and re-arm it.**

**Process:**
1. Disarm the switch
2. Notify beneficiary (if needed)
3. Re-arm when ready
4. Perform check-in

**Command:**
```bash
# Disarm switch
# Edit ~/.lazarus/config.json
# Change "armed": true to "armed": false

# Re-arm later
# Change "armed": false to "armed": true
```

---

### Can I test the trigger without actually sending emails?

**Yes!** Use the test-trigger command:

```bash
# Test trigger (dry run)
lazarus test-trigger
```

**This will:**
- Simulate the trigger process
- Show what would be sent
- Verify configuration
- NOT send actual emails
- NOT modify configuration

**Recommended: Run test-trigger after any configuration changes.**

---

## 💻 Technical Questions

### What are the system requirements?

**Minimum Requirements:**
- **CPU**: 1 core
- **RAM**: 512 MB
- **Disk**: 10 GB
- **Python**: 3.10+
- **OS**: Windows 10+, Linux 3.10+, macOS 11+

**Recommended Requirements:**
- **CPU**: 2+ cores
- **RAM**: 2 GB
- **Disk**: 50 GB
- **Python**: 3.11+
- **OS**: Latest stable release

---

### How do I install Lazarus Protocol?

**Three installation methods:**

**Method 1: PyPI (Recommended)**
```bash
pip install lazarus-protocol
lazarus init
```

**Method 2: Docker**
```bash
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus
docker-compose up -d
```

**Method 3: From Source**
```bash
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

**See [Installation Guide](INSTALLATION.md) for detailed instructions.**

---

### How do I update Lazarus Protocol?

**Update methods vary by installation:**

**PyPI Installation:**
```bash
pip install --upgrade lazarus-protocol
```

**Docker Installation:**
```bash
docker-compose pull
docker-compose up -d
```

**Source Installation:**
```bash
git pull origin main
pip install --upgrade -e .[dev]
```

**Always backup before updating.**

---

### Does Lazarus Protocol require internet access?

**For core functionality: No**

**For optional features: Yes**

**Core Features (Offline):**
- Encryption/decryption
- Check-in system
- Dead man's switch
- Local storage

**Optional Features (Online):**
- Email alerts (SendGrid)
- Telegram alerts
- IPFS storage
- Web dashboard access

**Lazarus Protocol works offline for all essential functionality.**

---

### Can I run Lazarus Protocol on a server?

**Yes!** Lazarus Protocol is designed for server deployment.

**Deployment Options:**
- **Docker**: Containerized deployment
- **Systemd**: Linux service
- **Kubernetes**: Cloud-native deployment

**See [Deployment Guide](DEPLOYMENT.md) for detailed instructions.**

---

### How do I back up my configuration?

**Manual Backup:**
```bash
# Create timestamped backup
tar -czf lazarus-backup-$(date +%Y%m%d).tar.gz ~/.lazarus/
```

**Automated Backup:**
```bash
# Add to crontab
0 2 * * * tar -czf /backups/lazarus-$(date +\%Y\%m\%d).tar.gz ~/.lazarus/
```

**Docker Backup:**
```bash
docker run --rm \
  -v lazarus_data:/data \
  -v $(pwd):/backup \
  alpine tar -czf /backup/lazarus-backup.tar.gz /data
```

**See [Deployment Guide](DEPLOYMENT.md) for more backup strategies.**

---

### How do I restore from backup?

**Manual Restore:**
```bash
# Stop service
lazarus agent stop

# Restore from backup
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/

# Start service
lazarus agent start
```

**Docker Restore:**
```bash
# Stop containers
docker-compose down

# Restore volume
docker run --rm \
  -v lazarus_data:/data \
  -v $(pwd):/backup \
  alpine tar -xzf /backup/lazarus-backup.tar.gz -C /

# Start containers
docker-compose up -d
```

---

### What logging does Lazarus Protocol provide?

**Log Locations:**
- **Application logs**: `~/.lazarus/logs/lazarus.log`
- **System logs**: `journalctl -u lazarus` (systemd)
- **Docker logs**: `docker-compose logs -f`

**Log Levels:**
- **DEBUG**: Detailed debugging information
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages

**Enable debug logging:**
```bash
export LAZARUS_LOG_LEVEL=DEBUG
```

---

## 🔧 Troubleshooting Questions

### What should I do if Lazarus Protocol won't start?

**Common solutions:**

**1. Check installation:**
```bash
lazarus --version
```

**2. Check configuration:**
```bash
lazarus status
```

**3. Check logs:**
```bash
tail -f ~/.lazarus/logs/lazarus.log
```

**4. Reinstall if needed:**
```bash
pip install --force-reinstall lazarus-protocol
```

**See [Troubleshooting Guide](TROUBLESHOOTING.md) for more solutions.**

---

### What if I get a "configuration not found" error?

**Solution:**
```bash
# Run setup wizard
lazarus init
```

**This creates the required configuration files.**

---

### What if email alerts aren't working?

**Check:**

**1. SendGrid configuration:**
```bash
cat .env | grep SENDGRID_API_KEY
```

**2. API key validity:**
```bash
curl -X GET https://api.sendgrid.com/v3/user/profile \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**3. Network connectivity:**
```bash
ping api.sendgrid.com
```

**4. Test email:**
```bash
python -m pytest tests/test_sendgrid_integration.py -v -m integration
```

---

### What if IPFS isn't working?

**Check:**

**1. IPFS daemon running:**
```bash
ipfs daemon &
```

**2. IPFS API accessible:**
```bash
curl http://localhost:5001/api/v0/id
```

**3. Configuration:**
```bash
cat ~/.lazarus/config.json | grep ipfs_api_url
```

**See [IPFS Storage Guide](IPFS_STORAGE_GUIDE.md) for more details.**

---

### What if I forget my check-in password?

**Lazarus Protocol doesn't use passwords for check-ins.**

**Check-in methods:**
- CLI command: `lazarus ping`
- Web dashboard: Click "Check In"
- API: `POST /api/v1/checkin`

**No password required - just run the command or click the button.**

---

### What if I accidentally delete my configuration?

**Restore from backup:**
```bash
tar -xzf lazarus-backup-YYYYMMDD.tar.gz -C ~/
```

**If no backup exists:**
```bash
# Re-run setup wizard
lazarus init
```

**Note: You'll need to re-encrypt your secrets with a new key pair.**

---

## 💰 Billing and Licensing Questions

### Is Lazarus Protocol really free?

**Yes!** The core software is 100% free and open source.

**What's free:**
- All core features
- Dead man's switch functionality
- Military-grade encryption
- Email alerts
- Web dashboard
- CLI interface
- Local storage
- All future updates

**What's paid (optional):**
- Managed cloud hosting ($49/mo)
- Enterprise support ($499/mo)
- Lifetime license ($199 one-time)

**No hidden fees, no subscriptions required.**

---

### What do I get with the paid tiers?

**Managed Cloud ($49/mo):**
- Hosted solution
- Automatic updates
- 24/7 monitoring
- Email support
- 99.9% uptime SLA

**Enterprise ($499/mo):**
- Everything in Managed Cloud
- Priority support
- Custom features
- Dedicated infrastructure
- SLA guarantees
- Onboarding assistance

**Lifetime ($199 one-time):**
- All current features
- All future features
- Priority support
- Early access to new features

**All tiers include the same core encryption and security.**

---

### How do I cancel my subscription?

**Subscriptions can be cancelled anytime:**

**Managed Cloud:**
- Contact support via email
- No cancellation fees
- Data export available

**Enterprise:**
- 30-day notice required
- Pro-rated refund available
- Data export and migration assistance

**Lifetime:**
- No cancellation needed (one-time payment)
- Access forever

---

### What's the refund policy?

**30-day money-back guarantee:**

**Eligible for refund:**
- Managed Cloud: Within 30 days of purchase
- Enterprise: Within 30 days of purchase
- Lifetime: Within 30 days of purchase

**Not eligible for refund:**
- After 30 days
- If service was used extensively
- If terms of service were violated

**Contact support for refund requests.**

---

### Do you offer discounts?

**Discounts available:**

**Academic Discount:**
- 50% off for students and faculty
- Requires valid .edu email

**Non-Profit Discount:**
- 50% off for registered non-profits
- Requires documentation

**Volume Discount:**
- 10% off for 5-10 users
- 20% off for 10+ users

**Open Source Contributors:**
- Free Enterprise tier for active contributors
- Requires proof of contributions

**Contact support for discount codes.**

---

## 🆘 Support and Contact

### How do I get help?

**Support channels:**

**1. Documentation**
- [Quick Start Guide](QUICKSTART.md)
- [Installation Guide](INSTALLATION.md)
- [Security Guide](SECURITY.md)
- [Configuration Guide](CONFIGURATION.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

**2. Community**
- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues)
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions)

**3. Email**
- General: ravikumarve@protonmail.com
- Security: ravikumarve@protonmail.com (subject: "SECURITY:")

**4. Paid Support**
- Managed Cloud: Email support included
- Enterprise: Priority email + phone support

---

### What's your response time?

**Response times by tier:**

**Community (Free):**
- GitHub Issues: 1-3 days
- GitHub Discussions: 1-2 days
- Email: 2-5 days

**Managed Cloud ($49/mo):**
- Email: 24 hours
- Critical issues: 4 hours

**Enterprise ($499/mo):**
- Email: 4 hours
- Phone: 1 hour
- Critical issues: 30 minutes

**Lifetime ($199):**
- Email: 24 hours
- Priority over community

---

### How do I report a bug?

**Report bugs via GitHub Issues:**

**Steps:**
1. Search existing issues first
2. Create new issue
3. Use bug report template
4. Include:
   - Lazarus version
   - Python version
   - Operating system
   - Error messages
   - Steps to reproduce

**Bug Report Template:**
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

## Error Messages
```
[Paste error messages here]
```
```

---

### How do I request a feature?

**Request features via GitHub Discussions:**

**Steps:**
1. Search existing discussions first
2. Create new discussion
3. Use feature request template
4. Include:
   - Feature description
   - Use case
   - Benefits
   - Alternative solutions

**Feature Request Template:**
```markdown
## Feature Description
[Detailed description of the feature]

## Use Case
[Describe the use case]

## Benefits
[What benefits would this feature provide?]

## Alternatives
[What alternative solutions exist?]

## Additional Context
[Any other relevant information]
```

---

### How do I report a security vulnerability?

**Security vulnerabilities should be reported privately:**

**Steps:**
1. **DO NOT** create a public issue
2. **DO NOT** disclose publicly
3. Email: ravikumarve@protonmail.com
4. Subject: "SECURITY: Vulnerability in Lazarus Protocol"
5. Include:
   - Detailed description
   - Steps to reproduce
   - Impact assessment
   - Suggested fix

**Response time:** Within 48 hours

**We will:**
- Acknowledge receipt
- Work with you to fix
- Coordinate disclosure
- Credit you in release notes

---

### Where can I find more documentation?

**Documentation available:**

**User Documentation:**
- [Quick Start Guide](QUICKSTART.md)
- [Installation Guide](INSTALLATION.md)
- [Security Guide](SECURITY.md)
- [Configuration Guide](CONFIGURATION.md)
- [Features Documentation](FEATURES.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [API Reference](API.md)
- [Deployment Guide](DEPLOYMENT.md)
- [FAQ](FAQ.md) (this document)

**Developer Documentation:**
- [Contributing Guide](CONTRIBUTING.md)
- [IPFS Storage Guide](IPFS_STORAGE_GUIDE.md)
- [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)

**Additional Resources:**
- [GitHub Wiki](https://github.com/ravikumarve/lazarus/wiki)
- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues)
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions)

---

## 🎯 Conclusion

Lazarus Protocol is designed to be secure, reliable, and easy to use. If you have questions not covered here, please reach out via our support channels.

**Remember:**
- Your secrets are protected by military-grade encryption
- Only your beneficiary can decrypt them
- Regular check-ins prevent accidental triggers
- Support is available if you need help

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
