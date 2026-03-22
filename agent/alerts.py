"""
agent/alerts.py — Email and Telegram alert system for Lazarus Protocol.

Handles:
    - Owner reminder emails  (Day 20, 25, 28)
    - Owner Telegram alerts  (Day 25, 28)
    - Beneficiary delivery email (Day 30+) with encrypted attachments + decryption kit

External services used:
    - SendGrid  (SENDGRID_API_KEY, ALERT_FROM_EMAIL env vars)
    - Telegram  (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID env vars) — optional

Design:
    - Every send_*() function is side-effect-only and raises AlertError on failure.
    - Callers (heartbeat.py) decide whether to swallow or propagate errors.
    - _build_decryption_kit() is pure (no network) — tested independently.
    - All HTML email bodies are self-contained strings (no templates on disk).
"""

from __future__ import annotations

import base64
import io
import logging
import os
import shutil
import textwrap
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class AlertError(Exception):
    """Raised when an alert cannot be delivered."""
    pass


# ---------------------------------------------------------------------------
# Owner alerts — email
# ---------------------------------------------------------------------------

def send_reminder_email(owner_email: str, days_remaining: float) -> None:
    """
    Send a check-in reminder email to the owner via SendGrid.

    Args:
        owner_email:    Destination address.
        days_remaining: Days left before the switch triggers (used in subject + body).

    Raises:
        AlertError: if SendGrid is not configured or delivery fails.
    """
    days_int = max(0, int(days_remaining))
    subject  = f"⚰️ Lazarus: {days_int} day{'s' if days_int != 1 else ''} remaining — check in now"
    body     = _reminder_email_body(days_int)

    _send_email(
        to_email=owner_email,
        subject=subject,
        html_body=body,
    )
    logger.info("Reminder email sent to %s (%d days remaining)", owner_email, days_int)


def send_final_warning(
    owner_email: str,
    days_remaining: float,
    chat_id: str | None = None,
) -> None:
    """
    Send a final warning via email and (optionally) Telegram.
    Instructs the owner to run `lazarus ping` immediately.

    Args:
        owner_email:    Owner's email address.
        days_remaining: Hours-precision value shown in alerts.
        chat_id:        Telegram chat ID, or None to skip Telegram.

    Raises:
        AlertError: if both channels fail. If only one fails, logs the error
                    and continues with the other.
    """
    hours = max(0, int(days_remaining * 24))
    subject = f"⚰️ LAZARUS FINAL WARNING — triggering in ~{hours} hours"
    body    = _final_warning_body(hours)

    email_ok = True
    try:
        _send_email(to_email=owner_email, subject=subject, html_body=body)
        logger.warning("Final warning email sent to %s (~%dh remaining)", owner_email, hours)
    except AlertError as exc:
        logger.error("Final warning email failed: %s", exc)
        email_ok = False

    if chat_id:
        msg = (
            f"⚰️ *LAZARUS FINAL WARNING*\n"
            f"Triggering in approximately *{hours} hours*.\n\n"
            f"Run `lazarus ping` immediately to cancel.\n"
            f"Or reply /freeze to extend by 30 days."
        )
        try:
            _send_telegram(chat_id=chat_id, message=msg)
            logger.warning("Final warning Telegram sent to chat %s", chat_id)
        except AlertError as exc:
            logger.error("Final warning Telegram failed: %s", exc)
            if not email_ok:
                raise AlertError(
                    f"Both final warning channels failed. Email: see logs. Telegram: {exc}"
                ) from exc


# ---------------------------------------------------------------------------
# Owner alerts — Telegram
# ---------------------------------------------------------------------------

def send_telegram_alert(chat_id: str, days_remaining: float) -> None:
    """
    Send a Telegram reminder to the owner.

    Args:
        chat_id:        Telegram chat ID (numeric string).
        days_remaining: Days left before trigger (shown in message).

    Raises:
        AlertError: if Telegram is not configured or delivery fails.
    """
    days_int = max(0, int(days_remaining))
    message  = (
        f"⚰️ *Lazarus reminder*\n"
        f"*{days_int} day{'s' if days_int != 1 else ''}* until your dead man's switch triggers.\n\n"
        f"Run `lazarus ping` to reset the countdown."
    )
    _send_telegram(chat_id=chat_id, message=message)
    logger.info("Telegram reminder sent to chat %s (%d days remaining)", chat_id, days_int)


# ---------------------------------------------------------------------------
# Beneficiary delivery email
# ---------------------------------------------------------------------------

def send_delivery_email(
    beneficiary_name: str,
    beneficiary_email: str,
    owner_name: str,
    encrypted_file_path: Path,
    key_blob_b64: str,
    ipfs_cid: str | None = None,
) -> None:
    """
    Send the inheritance email to the beneficiary.

    Attachments:
        1. encrypted_secrets.bin  — the vault ciphertext
        2. decryption_kit.zip     — standalone decrypt.py + key_blob.txt + INSTRUCTIONS.txt

    Args:
        beneficiary_name:      Recipient's name (used in greeting).
        beneficiary_email:     Recipient's email address.
        owner_name:            Name of the deceased/missing owner.
        encrypted_file_path:   Path to encrypted_secrets.bin on disk.
        key_blob_b64:          base64-encoded RSA-wrapped AES key.
        ipfs_cid:              Optional IPFS CID for alternate retrieval.

    Raises:
        AlertError:       if delivery fails.
        FileNotFoundError: if encrypted_file_path does not exist.
    """
    encrypted_file_path = Path(encrypted_file_path)
    if not encrypted_file_path.exists():
        raise FileNotFoundError(f"Encrypted vault not found: {encrypted_file_path}")

    # Build the standalone decryption kit zip
    kit_path = _build_decryption_kit(
        key_blob_b64=key_blob_b64,
        owner_name=owner_name,
    )

    subject = f"[Lazarus] You have received an inheritance from {owner_name}"
    body    = _delivery_email_body(
        beneficiary_name=beneficiary_name,
        owner_name=owner_name,
        ipfs_cid=ipfs_cid,
    )

    attachments = [
        (encrypted_file_path, "encrypted_secrets.bin", "application/octet-stream"),
        (kit_path,            "decryption_kit.zip",    "application/zip"),
    ]

    _send_email(
        to_email=beneficiary_email,
        subject=subject,
        html_body=body,
        attachments=attachments,
    )

    logger.critical(
        "DELIVERY EMAIL SENT to %s (%s) for %s",
        beneficiary_name, beneficiary_email, owner_name,
    )


# ---------------------------------------------------------------------------
# Decryption kit builder
# ---------------------------------------------------------------------------

def _build_decryption_kit(key_blob_b64: str, owner_name: str) -> Path:
    """
    Build decryption_kit.zip in a temp directory.

    Contents:
        decrypt.py        — standalone script requiring only 'cryptography' pip package
        key_blob.txt      — the base64-encoded RSA-encrypted AES key
        INSTRUCTIONS.txt  — step-by-step guide for a non-technical beneficiary

    Returns:
        Path to the zip file (in system temp dir).

    Note:
        The temp directory is cleaned up in a finally block to prevent
        key_blob.txt from persisting on disk if zip creation fails.
    """
    import tempfile

    tmp_dir  = Path(tempfile.mkdtemp(prefix="lazarus_kit_"))
    zip_path = tmp_dir / "decryption_kit.zip"

    try:
        decrypt_script   = _standalone_decrypt_script()
        instructions_txt = _instructions_text(owner_name)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("decrypt.py",        decrypt_script)
            zf.writestr("key_blob.txt",      key_blob_b64)
            zf.writestr("INSTRUCTIONS.txt",  instructions_txt)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.debug("Decryption kit built at %s", zip_path)
    return zip_path


def _standalone_decrypt_script() -> str:
    """
    Return the source of a standalone decrypt.py that has zero
    Lazarus dependencies — only needs pip install cryptography.
    """
    return textwrap.dedent("""\
        #!/usr/bin/env python3
        \"\"\"
        Lazarus Protocol — Standalone Decryption Script
        ================================================
        Requirements: pip install cryptography
        Usage:        python decrypt.py --key key_blob.txt [--encrypted encrypted_secrets.bin]
        \"\"\"

        import argparse
        import base64
        import getpass
        import os
        import sys
        from pathlib import Path

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.exceptions import InvalidTag
        except ImportError:
            print("ERROR: cryptography library not installed.")
            print("Run: pip install cryptography")
            sys.exit(1)

        GCM_NONCE_SIZE = 12

        def _is_safe_path(path: Path, base_dir: Path) -> bool:
            \"\"\"Check if resolved path stays within base directory (prevent path traversal).\"\"\"
            try:
                resolved = path.resolve()
                base_resolved = base_dir.resolve()
                return str(resolved).startswith(str(base_resolved))
            except (OSError, RuntimeError):
                return False

        def decrypt(encrypted_path, key_blob_b64, private_key_pem, password=None):
            # 1. Validate encrypted file path
            enc_path = Path(encrypted_path).resolve()
            if not enc_path.exists():
                print(f"ERROR: Encrypted file not found: {encrypted_path}")
                sys.exit(1)
            if not enc_path.is_file():
                print(f"ERROR: Path is not a file: {encrypted_path}")
                sys.exit(1)

            # 2. Unwrap AES key with RSA private key
            try:
                private_key = serialization.load_pem_private_key(
                    private_key_pem, password=password
                )
            except Exception as e:
                print("ERROR: Failed to load private key.")
                print("  - Ensure the file is a valid RSA private key (.pem)")
                print("  - If encrypted, ensure you entered the correct password")
                print(f"  - Details: {e}")
                sys.exit(1)

            # 3. Attempt decryption
            encrypted_aes_key = base64.b64decode(key_blob_b64)
            try:
                aes_key = private_key.decrypt(
                    encrypted_aes_key,
                    asym_padding.OAEP(
                        mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None,
                    ),
                )
            except Exception as e:
                print("ERROR: Decryption failed — wrong key or corrupted data.")
                print("  - Verify you are using the correct private key")
                print("  - Verify key_blob matches this encrypted file")
                print(f"  - Details: {e}")
                sys.exit(1)

            # 4. Split nonce + ciphertext
            raw        = enc_path.read_bytes()
            nonce      = raw[:GCM_NONCE_SIZE]
            ciphertext = raw[GCM_NONCE_SIZE:]

            # 5. Decrypt + verify GCM tag
            try:
                plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, associated_data=None)
            except InvalidTag:
                print("ERROR: Authentication failed. File may be corrupted or wrong key.")
                sys.exit(1)

            return plaintext

        def main():
            parser = argparse.ArgumentParser(
                description="Lazarus Protocol — Decrypt your inheritance vault."
            )
            parser.add_argument(
                "--key", "-k",
                required=True,
                help="Path to key_blob.txt (base64-encoded RSA-encrypted AES key)"
            )
            parser.add_argument(
                "--encrypted", "-e",
                help="Path to encrypted_secrets.bin (will prompt if not provided)"
            )
            parser.add_argument(
                "--output", "-o",
                help="Output file path (will prompt if not provided)"
            )
            args = parser.parse_args()

            print("=" * 55)
            print("  Lazarus Protocol — Inheritance Decryption Tool")
            print("=" * 55)
            print()

            # Determine script directory for path safety checks
            script_dir = Path(os.path.dirname(os.path.abspath(__file__))) if "__file__" in dir() else Path.cwd()

            # Load key_blob from CLI argument
            key_input = args.key.strip()
            key_blob_path = Path(key_input).resolve()

            if not _is_safe_path(key_blob_path, script_dir):
                print("ERROR: Path traversal detected. Only relative paths allowed.")
                sys.exit(1)

            if not key_blob_path.exists():
                print(f"ERROR: key_blob file not found: {key_input}")
                sys.exit(1)

            try:
                key_blob = key_blob_path.read_text().strip()
            except Exception as e:
                print(f"ERROR: Failed to read key_blob: {e}")
                sys.exit(1)

            # Get encrypted file path
            if args.encrypted:
                enc_path = Path(args.encrypted).resolve()
            else:
                enc_input = input("Path to encrypted_secrets.bin: ").strip()
                enc_path = Path(enc_input).resolve()

            if not _is_safe_path(enc_path, script_dir):
                print("ERROR: Path traversal detected. Only relative paths allowed.")
                sys.exit(1)

            # Get output path
            if args.output:
                out_path = Path(args.output).resolve()
            else:
                out_input = input("Output file path (e.g. secrets.pdf): ").strip()
                out_path = Path(out_input).resolve()

            if not _is_safe_path(out_path, script_dir):
                print("ERROR: Path traversal detected. Only relative paths allowed.")
                sys.exit(1)

            # Get private key path
            priv_input = input("Path to your private key (.pem): ").strip()
            priv_path = Path(priv_input).resolve()

            if not _is_safe_path(priv_path, script_dir):
                print("ERROR: Path traversal detected. Only relative paths allowed.")
                sys.exit(1)

            if not priv_path.exists():
                print(f"ERROR: Private key file not found: {priv_input}")
                sys.exit(1)

            # Try unencrypted key first, prompt for password if encrypted
            try:
                priv_pem = priv_path.read_bytes()
                serialization.load_pem_private_key(priv_pem, password=None)
                password = None
                print("(Unencrypted key detected)")
            except Exception:
                pw_str = getpass.getpass("Private key password: ")
                password = pw_str.encode()

            print("\\nDecrypting...")
            try:
                plaintext = decrypt(enc_path, key_blob, priv_pem, password)
                out_path.write_bytes(plaintext)
                print(f"\\nDecrypted file saved to: {out_path}")
                print("You can now open it with any standard application.")
            except Exception as e:
                print(f"ERROR: Decryption failed: {e}")
                sys.exit(1)

        if __name__ == "__main__":
            main()
    """)


def _instructions_text(owner_name: str) -> str:
    return textwrap.dedent(f"""\
        LAZARUS PROTOCOL — DECRYPTION INSTRUCTIONS
        ===========================================
        From: {owner_name}

        You are receiving this because {owner_name} has not checked in
        for their configured period. This is their Lazarus vault.

        WHAT YOU NEED
        -------------
        1. Your private key file (.pem) — {owner_name} gave this to you during setup.
        2. Python 3.10 or newer installed on your computer.
        3. The cryptography library: run  pip install cryptography

        STEPS
        -----
        1. Unzip this archive.
        2. Open a terminal / command prompt in this folder.
        3. Run:  python decrypt.py --key key_blob.txt
           (Or: python decrypt.py -k key_blob.txt --encrypted encrypted_secrets.bin -o output.pdf)
        4. Follow the prompts for your private key and password.
        5. Open the decrypted file — it contains {owner_name}'s instructions.

        TROUBLESHOOTING
        ---------------
        "Module not found" error → run: pip install cryptography
        "Authentication failed"  → wrong key file or corrupted archive.
                                   Contact the email sender for support.
        "Permission denied"      → run the terminal as administrator.

        This tool has no internet connection and sends nothing anywhere.
        Your privacy is fully protected.
    """)


# ---------------------------------------------------------------------------
# Email / Telegram transport layer
# ---------------------------------------------------------------------------

def _send_email(
    to_email: str,
    subject: str,
    html_body: str,
    attachments: list[tuple[Path, str, str]] | None = None,
) -> None:
    """
    Send an email via SendGrid.

    Args:
        to_email:    Recipient address.
        subject:     Email subject.
        html_body:   HTML email body.
        attachments: List of (file_path, filename, mime_type) tuples.

    Raises:
        AlertError: if SENDGRID_API_KEY is missing or send fails.
    """
    try:
        import sendgrid
        from sendgrid.helpers.mail import (
            Mail, Attachment, FileContent, FileName,
            FileType, Disposition,
        )
    except ImportError as exc:
        raise AlertError("sendgrid package not installed. Run: pip install sendgrid") from exc

    api_key   = os.getenv("SENDGRID_API_KEY")
    from_addr = os.getenv("ALERT_FROM_EMAIL")

    if not api_key:
        raise AlertError("SENDGRID_API_KEY not set in environment.")
    if not from_addr:
        raise AlertError("ALERT_FROM_EMAIL not set in environment.")

    message = Mail(
        from_email=from_addr,
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )

    if attachments:
        for file_path, filename, mime_type in attachments:
            data     = Path(file_path).read_bytes()
            encoded  = base64.b64encode(data).decode()
            att      = Attachment(
                FileContent(encoded),
                FileName(filename),
                FileType(mime_type),
                Disposition("attachment"),
            )
            message.add_attachment(att)

    try:
        client   = sendgrid.SendGridAPIClient(api_key=api_key)
        response = client.send(message)
        if response.status_code not in (200, 202):
            raise AlertError(
                f"SendGrid returned status {response.status_code}: {response.body}"
            )
    except AlertError:
        raise
    except Exception as exc:
        raise AlertError(f"SendGrid send failed: {exc}") from exc


def _send_telegram(chat_id: str, message: str) -> None:
    """
    Send a Telegram message via python-telegram-bot (sync wrapper).

    Args:
        chat_id: Telegram chat ID (numeric string).
        message: Markdown-formatted message text.

    Raises:
        AlertError: if TELEGRAM_BOT_TOKEN is missing or send fails.
    """
    try:
        import asyncio
        import telegram
    except ImportError as exc:
        raise AlertError(
            "python-telegram-bot not installed. Run: pip install python-telegram-bot"
        ) from exc

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise AlertError("TELEGRAM_BOT_TOKEN not set in environment.")

    async def _send():
        bot = telegram.Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
        )

    try:
        asyncio.run(_send())
    except Exception as exc:
        raise AlertError(f"Telegram send failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Email body builders
# ---------------------------------------------------------------------------

def _reminder_email_body(days_remaining: int) -> str:
    urgency = "⚠️" if days_remaining <= 5 else "🔔"
    return f"""
    <html><body style="font-family: monospace; background:#111; color:#eee; padding:32px;">
      <h2 style="color:#e74c3c;">⚰️ Lazarus Protocol</h2>
      <p>{urgency} Your dead man's switch will trigger in <strong>{days_remaining} day{'s' if days_remaining != 1 else ''}</strong>.</p>
      <p>If you are alive and well, check in now:</p>
      <pre style="background:#222; padding:12px; border-radius:4px; color:#2ecc71;">python -m lazarus ping</pre>
      <p>To extend the deadline by 30 days:</p>
      <pre style="background:#222; padding:12px; border-radius:4px; color:#3498db;">python -m lazarus freeze --days 30</pre>
      <hr style="border-color:#333;"/>
      <p style="color:#666; font-size:12px;">
        Lazarus Protocol — self-sovereign inheritance.<br/>
        If you did not set this up, someone did it on your behalf.
      </p>
    </body></html>
    """


def _final_warning_body(hours_remaining: int) -> str:
    return f"""
    <html><body style="font-family: monospace; background:#111; color:#eee; padding:32px;">
      <h2 style="color:#e74c3c;">💀 LAZARUS — FINAL WARNING</h2>
      <p style="font-size:18px; color:#e74c3c;">
        Your vault will trigger in approximately <strong>{hours_remaining} hours</strong>.
      </p>
      <p>After this point, your encrypted secrets will be delivered to your beneficiary.</p>
      <p><strong>To cancel immediately:</strong></p>
      <pre style="background:#222; padding:12px; border-radius:4px; color:#2ecc71; font-size:16px;">python -m lazarus ping</pre>
      <p><strong>To extend deadline by 30 days:</strong></p>
      <pre style="background:#222; padding:12px; border-radius:4px; color:#3498db;">python -m lazarus freeze --days 30</pre>
      <hr style="border-color:#333;"/>
      <p style="color:#e74c3c; font-size:13px;">This is your final automated warning.</p>
    </body></html>
    """


def _delivery_email_body(
    beneficiary_name: str,
    owner_name: str,
    ipfs_cid: str | None,
) -> str:
    ipfs_section = ""
    if ipfs_cid:
        ipfs_section = f"""
        <p>The encrypted file is also available on IPFS:</p>
        <pre style="background:#222; padding:8px; border-radius:4px; color:#3498db;">ipfs get {ipfs_cid}</pre>
        """
    return f"""
    <html><body style="font-family: monospace; background:#111; color:#eee; padding:32px;">
      <h2 style="color:#e74c3c;">⚰️ Lazarus Protocol — Inheritance Delivery</h2>
      <p>Dear {beneficiary_name},</p>
      <p>
        <strong>{owner_name}</strong> has not checked in for their configured period.
        Per their instructions, you are receiving their encrypted Lazarus vault.
      </p>
      <h3 style="color:#f39c12;">Attached files:</h3>
      <ul>
        <li><code>encrypted_secrets.bin</code> — the encrypted vault</li>
        <li><code>decryption_kit.zip</code> — everything you need to decrypt it</li>
      </ul>
      <h3 style="color:#f39c12;">How to decrypt:</h3>
      <ol>
        <li>Unzip <code>decryption_kit.zip</code></li>
        <li>Install Python (python.org) and run: <code>pip install cryptography</code></li>
        <li>Run: <code>python decrypt.py</code> and follow the prompts</li>
        <li>You will need your private key (.pem file) that {owner_name} gave you</li>
      </ol>
      {ipfs_section}
      <p>Full instructions are inside <code>INSTRUCTIONS.txt</code> in the zip.</p>
      <hr style="border-color:#333;"/>
      <p style="color:#666; font-size:12px;">
        Sent by Lazarus Protocol — automated, self-hosted, no intermediaries.
      </p>
    </body></html>
    """


# ---------------------------------------------------------------------------
# Configuration checks
# ---------------------------------------------------------------------------

def email_configured() -> bool:
    """Return True if SendGrid credentials are present in the environment."""
    return bool(os.getenv("SENDGRID_API_KEY") and os.getenv("ALERT_FROM_EMAIL"))


def telegram_configured() -> bool:
    """Return True if Telegram bot credentials are present in the environment."""
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
