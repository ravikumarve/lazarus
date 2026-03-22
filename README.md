# ⚰️ Lazarus Protocol

> *"Your secrets survive you."*

Lazarus is a self-hosted, open-source Dead Man's Switch for crypto holders.
If you stop checking in, your encrypted secrets are automatically delivered to your chosen beneficiary — no middleman, no cloud service, no trust required.

---

## What problem does this solve?

Every self-custody crypto holder has the same nightmare: **if I die tomorrow, my family gets nothing.**

Hardware wallets, seed phrases, and private keys die with you unless you've planned for it. Lazarus solves this with a simple, cryptographically secure system:

- You set it up once in 10 minutes
- A lightweight agent pings every day to confirm you're alive
- If you stop pinging for X days → your encrypted secrets are delivered to your beneficiary
- Nobody else — not us, not a server, not a company — can read your secrets

---

## How it works (Simple Version)

```
You (Alive)          Lazarus Agent          Beneficiary
    |                     |                     |
    |-- setup secrets --->|                     |
    |-- ping daily ------>|                     |
    |                     |                     |
    |   [You stop pinging / You die]            |
    |                     |                     |
    |                     |-- deliver secrets ->|
    |                     |                     |
```

---

## Architecture Overview

```
lazarus/
├── core/
│   ├── encryption.py      # AES-256 + RSA hybrid encryption engine
│   ├── storage.py         # IPFS upload/download + local fallback
│   └── config.py          # User config management (~/.lazarus/config.json)
│
├── cli/
│   ├── main.py            # Entry point: `lazarus` command
│   └── setup.py           # `lazarus init` wizard
│
├── agent/
│   ├── heartbeat.py       # Daily ping scheduler (APScheduler)
│   └── alerts.py          # Email + Telegram alert system
│
├── contracts/             # (Optional) Solidity vault for on-chain trigger
│
├── tests/                 # Full test suite
├── docs/                  # Guides and tutorials
└── examples/              # Example secrets files and configs
```

---

## Encryption Design

Lazarus uses a **hybrid encryption scheme** — the same approach used by PGP and Signal.

```
Your Secret File (PDF / TXT)
        |
        v
  [AES-256 Key] ──encrypts──> encrypted_secrets.bin ──> IPFS / local
        |
        v
  [Beneficiary's Public Key (RSA-4096)] ──encrypts──> key_blob (stored safely)
        |
        v
  key_blob + IPFS link ──stored in──> ~/.lazarus/vault.json
```

**Why this is unbreakable:**
- The file is encrypted with AES-256 (symmetric, fast, military-grade)
- The AES key itself is encrypted with the beneficiary's public key (asymmetric)
- Only the beneficiary's private key can unlock the AES key
- Even if someone steals your vault file, they see encrypted noise

---

## The Heartbeat Agent

The agent runs silently in the background on your machine (Linux / Mac / Raspberry Pi / VPS).

```
Every 24 hours:
  → Check: is the switch still armed?
  → Log: heartbeat confirmed
  → Alert: if nearing deadline (Day 20, 25, 28 of 30)

Day 30+ without ping:
  → Trigger: send encrypted file + key blob to beneficiary
  → Via: Email (with instructions) + IPFS link
```

**Escalation ladder (not a cliff):**
- Day 20: Email to you — "Lazarus: Check-in reminder"
- Day 25: Telegram alert — "Lazarus: 5 days remaining"
- Day 28: Final warning — "Lazarus: Triggering in 48 hours. Reply ALIVE to cancel."
- Day 30: Trigger fires — beneficiary receives everything

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/yourname/lazarus
cd lazarus
pip install -r requirements.txt
```

### 2. Initialize your vault

```bash
python -m lazarus init
```

This will:
- Ask for your secret file path
- Ask for your beneficiary's email + public key
- Set your check-in interval (default: 30 days)
- Encrypt everything and store the vault locally

### 3. Start the heartbeat agent

```bash
python -m lazarus agent start
```

Add to crontab or systemd to run on boot.

### 4. Manual check-in (if needed)

```bash
python -m lazarus ping
```

---

## CLI Commands

| Command | Description |
|---|---|
| `lazarus init` | Setup wizard — create your vault |
| `lazarus ping` | Manual check-in (resets the timer) |
| `lazarus status` | Show vault status, days remaining |
| `lazarus agent start` | Start the background heartbeat agent |
| `lazarus agent stop` | Stop the agent |
| `lazarus freeze --days 30` | Panic button — extend deadline by N days |
| `lazarus test-trigger` | Dry run — simulate delivery without sending |
| `lazarus update-secret` | Replace the secret file with a new one |

---

## Beneficiary Experience

When Lazarus triggers, your beneficiary receives an email:

```
Subject: [Lazarus] You have received an inheritance from [Your Name]

[Your Name] has not checked in for 30 days. Per their instructions,
you are receiving their encrypted Lazarus vault.

Attached:
  - encrypted_secrets.bin
  - decryption_kit.zip (instructions + tool)

To decrypt:
  1. Open decryption_kit
  2. Run: python decrypt.py
  3. Enter your private key password when prompted
  4. Your file will appear as: secrets_decrypted.pdf
```

No blockchain knowledge required. No MetaMask. No IPFS. Just a Python script and their private key.

---

## Security Model

| Threat | Protection |
|---|---|
| Someone steals your vault file | Useless without beneficiary's private key |
| Someone intercepts the email | Encrypted file is unreadable without private key |
| Lazarus servers get hacked | There are no Lazarus servers — fully local |
| Beneficiary loses private key | Verified during setup (beneficiary test-decrypts a dummy file) |
| Early trigger by accident | Escalation ladder + `lazarus freeze` panic command |
| You forget to ping | Daily reminders + Telegram alerts |

---

## Roadmap

- [x] Project architecture
- [x] Core encryption engine (AES-256 + RSA)
- [x] IPFS storage layer
- [x] CLI setup wizard
- [x] Heartbeat agent with APScheduler
- [x] Email delivery system
- [x] Telegram alerts
- [x] Beneficiary decryption kit
- [x] Multi-beneficiary support
- [ ] Desktop GUI (Electron / Tkinter) — Pro tier
- [ ] Legal document storage support

---

## Pricing (Kit)

| Tier | Price | Includes |
|---|---|---|
| **Basic** | $35 | Full source code + PDF guide |
| **Pro** | $79 | Source code + packaged desktop app + video walkthrough |

---

## Philosophy

Lazarus is **not a service**. We don't hold your secrets. We don't run servers. We don't know who you are.

You run this software on your own machine. You control everything. If we disappear tomorrow, your vault still works.

This is self-sovereign inheritance.

---

## License

MIT — do whatever you want with it.

---

*Built with paranoia and love. For the people who hold their own keys.*
