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
    - Retry with exponential backoff: 3 retries, wait 2s, 4s, 8s between attempts.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import shutil
import textwrap
import time
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class AlertError(Exception):
    """Raised when an alert cannot be delivered."""
    pass


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _send_with_retry(send_fn, label: str) -> None:
    """
    Call a send function with exponential backoff retry.
    
    Args:
        send_fn: Callable that performs the send operation.
        label: Human-readable label for logging.
    
    Raises:
        AlertError: if all retries fail.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            send_fn()
            if attempt > 1:
                logger.info("%s succeeded on attempt %d", label, attempt)
            return
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1]
                logger.warning(
                    "%s failed on attempt %d/%d (will retry in %ds): %s",
                    label, attempt, MAX_RETRIES, delay, exc
                )
                time.sleep(delay)
            else:
                logger.error(
                    "%s failed on all %d attempts: %s",
                    label, MAX_RETRIES, exc
                )
    raise AlertError(f"{label} failed after {MAX_RETRIES} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Owner alerts — email
# ---------------------------------------------------------------------------

def send_reminder_email(owner_email: str, days_remaining: float) -> None:
    """
    Send a check-in reminder email to the owner via SendGrid.
    Retries up to 3 times with exponential backoff.

    Args:
        owner_email:    Destination address.
        days_remaining: Days left before the switch triggers (used in subject + body).

    Raises:
        AlertError: if SendGrid is not configured or delivery fails after retries.
    """
    days_int = max(0, int(days_remaining))
    subject  = f"⚰️ Lazarus: {days_int} day{'s' if days_int != 1 else ''} remaining — check in now"
    body     = _reminder_email_body(days_int)

    def do_send():
        _send_email(
            to_email=owner_email,
            subject=subject,
            html_body=body,
        )

    _send_with_retry(do_send, f"Reminder email to {owner_email}")
    logger.info("Reminder email sent to %s (%d days remaining)", owner_email, days_int)


def send_final_warning(
    owner_email: str,
    days_remaining: float,
    chat_id: str | None = None,
) -> None:
    """
    Send a final warning via email and (optionally) Telegram.
    Retries up to 3 times with exponential backoff for each channel.
    Instructs the owner to run `lazarus ping` immediately.

    Args:
        owner_email:    Owner's email address.
        days_remaining: Hours-precision value shown in alerts.
        chat_id:        Telegram chat ID, or None to skip Telegram.

    Raises:
        AlertError: if both channels fail after retries. If only one fails, logs the error
                    and continues with the other.
    """
    hours = max(0, int(days_remaining * 24))
    subject = f"⚰️ LAZARUS FINAL WARNING — triggering in ~{hours} hours"
    body    = _final_warning_body(hours)

    email_ok = True
    try:
        def do_email():
            _send_email(to_email=owner_email, subject=subject, html_body=body)
        _send_with_retry(do_email, f"Final warning email to {owner_email}")
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
            def do_telegram():
                _send_telegram(chat_id=chat_id, message=msg)
            _send_with_retry(do_telegram, f"Final warning Telegram to {chat_id}")
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
    Retries up to 3 times with exponential backoff.

    Args:
        chat_id:        Telegram chat ID (numeric string).
        days_remaining: Days left before trigger (shown in message).

    Raises:
        AlertError: if Telegram is not configured or delivery fails after retries.
    """
    days_int = max(0, int(days_remaining))
    message  = (
        f"⚰️ *Lazarus reminder*\n"
        f"*{days_int} day{'s' if days_int != 1 else ''}* until your dead man's switch triggers.\n\n"
        f"Run `lazarus ping` to reset the countdown."
    )

    def do_send():
        _send_telegram(chat_id=chat_id, message=message)

    _send_with_retry(do_send, f"Telegram alert to {chat_id}")
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
    Retries up to 3 times with exponential backoff.

    Attachments:
        1. encrypted_secrets.bin  — the vault ciphertext
        2. decryption_kit.zip     — standalone decrypt.py + key_blob.txt + INSTRUCTIONS.txt

    Args:
        beneficiary_name:      Recipient's name (used in greeting).
        beneficiary_email:     Recipient's email address.
        owner_name:            Name of the deceased/missing owner.
        encrypted_file_path:   Path to encrypted_secrets.bin on disk.
        key_blob_b64:         base64-encoded RSA-wrapped AES key.
        ipfs_cid:             Optional IPFS CID for alternate retrieval.

    Raises:
        AlertError:       if delivery fails after retries.
        FileNotFoundError: if encrypted_file_path does not exist.
    """
    encrypted_file_path = Path(encrypted_file_path)
    if not encrypted_file_path.exists():
        raise FileNotFoundError(f"Encrypted vault not found: {encrypted_file_path}")

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

    def do_send():
        _send_email(
            to_email=beneficiary_email,
            subject=subject,
            html_body=body,
            attachments=attachments,
        )

    _send_with_retry(do_send, f"Delivery email to {beneficiary_email}")
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
    """Return the source of a standalone decrypt.py that has zero Lazarus dependencies."""
    return textwrap.dedent("""\
        #!/usr/bin/env python3
        \"\"\"
        Lazarus Protocol — Standalone Decryption Script
        ================================================
        Requirements: pip install cryptography
        Usage:        python decrypt.py --key key_blob.txt
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
            try:
                resolved = path.resolve()
                base_resolved = base_dir.resolve()
                return str(resolved).startswith(str(base_resolved))
            except (OSError, RuntimeError):
                return False

        def decrypt(encrypted_path, key_blob_b64, private_key_pem, password=None):
            enc_path = Path(encrypted_path).resolve()
            if not enc_path.exists():
                print(f"ERROR: Encrypted file not found: {encrypted_path}")
                sys.exit(1)
            if not enc_path.is_file():
                print(f"ERROR: Path is not a file: {encrypted_path}")
                sys.exit(1)

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

            raw = enc_path.read_bytes()
            nonce = raw[:GCM_NONCE_SIZE]
            ciphertext = raw[GCM_NONCE_SIZE:]

            try:
                plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, associated_data=None)
            except InvalidTag:
                print("ERROR: Authentication failed. File may be corrupted or wrong key.")
                sys.exit(1)

            return plaintext

        def main():
            parser = argparse.ArgumentParser(description="Lazarus Protocol — Decrypt your inheritance vault")
            parser.add_argument("--key", "-k", required=True, help="Path to key_blob.txt")
            parser.add_argument("--encrypted", "-e", help="Path to encrypted_secrets.bin")
            parser.add_argument("--output", "-o", help="Output file path")
            args = parser.parse_args()

            print("=" * 60)
            print("  Lazarus Protocol — Inheritance Decryption Tool")
            print("=" * 60)
            print()

            script_dir = Path(os.path.dirname(os.path.abspath(__file__))) if "__file__" in dir() else Path.cwd()

            key_blob_path = Path(args.key.strip()).resolve()
            if not _is_safe_path(key_blob_path, script_dir):
                print("ERROR: Path traversal detected. Only relative paths allowed.")
                sys.exit(1)
            if not key_blob_path.exists():
                print(f"ERROR: key_blob file not found: {args.key}")
                sys.exit(1)

            try:
                key_blob = key_blob_path.read_text().strip()
            except Exception as e:
                print(f"ERROR: Failed to read key_blob: {e}")
                sys.exit(1)

            enc_path = Path(args.encrypted).resolve() if args.encrypted else Path(input("Path to encrypted_secrets.bin: ").strip()).resolve()
            if not _is_safe_path(enc_path, script_dir):
                print("ERROR: Path traversal detected.")
                sys.exit(1)

            out_path = Path(args.output).resolve() if args.output else Path(input("Output file path: ").strip()).resolve()
            if not _is_safe_path(out_path, script_dir):
                print("ERROR: Path traversal detected.")
                sys.exit(1)

            priv_path = Path(input("Path to your private key (.pem): ").strip()).resolve()
            if not _is_safe_path(priv_path, script_dir):
                print("ERROR: Path traversal detected.")
                sys.exit(1)
            if not priv_path.exists():
                print(f"ERROR: Private key file not found.")
                sys.exit(1)

            try:
                priv_pem = priv_path.read_bytes()
                serialization.load_pem_private_key(priv_pem, password=None)
                password = None
            except Exception:
                password = getpass.getpass("Private key password: ").encode()

            print("\\nDecrypting...")
            try:
                plaintext = decrypt(enc_path, key_blob, priv_pem, password)
                out_path.write_bytes(plaintext)
                print(f"\\nDecrypted file saved to: {out_path}")
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
        1. Your private key file (.pem)
        2. Python 3.10 or newer
        3. pip install cryptography

        STEPS
        -----
        1. Unzip this archive.
        2. python decrypt.py --key key_blob.txt
        3. Follow the prompts.

        TROUBLESHOOTING
        ---------------
        pip install cryptography
        Contact the sender if you need help.

        This tool has no internet connection.
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
    Send an email via SendGrid (no retry — retry is handled by caller).
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
    Send a Telegram message via python-telegram-bot (no retry).
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
        Lazarus Protocol — self-sovereign inheritance.
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
      <p>To cancel immediately:</p>
      <pre style="background:#222; padding:12px; border-radius:4px; color:#2ecc71;">python -m lazarus ping</pre>
      <hr style="border-color:#333;"/>
      <p style="color:#e74c3c;">This is your final automated warning.</p>
    </body></html>
    """


def _delivery_email_body(
    beneficiary_name: str,
    owner_name: str,
    ipfs_cid: str | None,
) -> str:
    ipfs_section = ""
    if ipfs_cid:
        ipfs_section = f"<pre style='background:#222; padding:8px;'>ipfs get {ipfs_cid}</pre>"
    return f"""
    <html><body style="font-family: monospace; background:#111; color:#eee; padding:32px;">
      <h2 style="color:#e74c3c;">⚰️ Lazarus Protocol — Inheritance Delivery</h2>
      <p>Dear {beneficiary_name},</p>
      <p><strong>{owner_name}</strong> has not checked in for their configured period.</p>
      <h3>Attached files:</h3>
      <ul>
        <li><code>encrypted_secrets.bin</code> — the encrypted vault</li>
        <li><code>decryption_kit.zip</code> — everything you need to decrypt it</li>
      </ul>
      <h3>How to decrypt:</h3>
      <ol>
        <li>Unzip <code>decryption_kit.zip</code></li>
        <li>pip install cryptography</li>
        <li>python decrypt.py --key key_blob.txt</li>
      </ol>
      {ipfs_section}
      <hr style="border-color:#333;"/>
      <p style="color:#666; font-size:12px;">Sent by Lazarus Protocol</p>
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
