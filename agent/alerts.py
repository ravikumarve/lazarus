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
import logging
import os
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
    subject = f"⚰️ Lazarus: {days_int} day{'s' if days_int != 1 else ''} remaining — check in now"
    body = _reminder_email_body(days_int)

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
    body = _final_warning_body(hours)

    email_ok = True
    try:
        _send_email(to_email=owner_email, subject=subject, html_body=body)
        logger.warning(
            "Final warning email sent to %s (~%dh remaining)", owner_email, hours
        )
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
    message = (
        f"⚰️ *Lazarus reminder*\n"
        f"*{days_int} day{'s' if days_int != 1 else ''}* until your dead man's switch triggers.\n\n"
        f"Run `lazarus ping` to reset the countdown."
    )
    _send_telegram(chat_id=chat_id, message=message)
    logger.info(
        "Telegram reminder sent to chat %s (%d days remaining)", chat_id, days_int
    )


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

    kit_path = None
    try:
        # Build the standalone decryption kit zip
        kit_path = _build_decryption_kit(
            key_blob_b64=key_blob_b64,
            owner_name=owner_name,
        )

        subject = f"[Lazarus] You have received an inheritance from {owner_name}"
        body = _delivery_email_body(
            beneficiary_name=beneficiary_name,
            owner_name=owner_name,
            ipfs_cid=ipfs_cid,
        )

        attachments = [
            (encrypted_file_path, "encrypted_secrets.bin", "application/octet-stream"),
            (kit_path, "decryption_kit.zip", "application/zip"),
        ]

        _send_email(
            to_email=beneficiary_email,
            subject=subject,
            html_body=body,
            attachments=attachments,
        )

        logger.critical(
            "DELIVERY EMAIL SENT to %s (%s) for %s",
            beneficiary_name,
            beneficiary_email,
            owner_name,
        )
    finally:
        # Clean up temporary decryption kit after email is sent
        if kit_path:
            _cleanup_decryption_kit(kit_path)


# ---------------------------------------------------------------------------
# Decryption kit builder
# ---------------------------------------------------------------------------


def _build_decryption_kit(key_blob_b64: str, owner_name: str) -> Path:
    """
    Build decryption_kit.zip in a persistent temporary location.

    Contents:
        decrypt.py        — standalone script requiring only 'cryptography' pip package
        key_blob.txt      — the base64-encoded RSA-encrypted AES key
        INSTRUCTIONS.txt  — step-by-step guide for a non-technical beneficiary

    Returns:
        Path to the zip file (in system temp dir).
        Caller is responsible for cleanup via _cleanup_decryption_kit().

    Note:
        The temp file is created with secure permissions and will persist
        until explicitly cleaned up to prevent race conditions with email attachments.
    """
    import tempfile

    # Create a persistent temporary file that won't be automatically deleted
    temp_fd, temp_path = tempfile.mkstemp(suffix=".zip", prefix="lazarus_kit_")
    os.close(temp_fd)  # Close the file descriptor since we'll use zipfile
    zip_path = Path(temp_path)

    try:
        decrypt_script = _standalone_decrypt_script()
        instructions_txt = _instructions_text(owner_name)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("decrypt.py", decrypt_script)
            zf.writestr("key_blob.txt", key_blob_b64)
            zf.writestr("INSTRUCTIONS.txt", instructions_txt)

        # Set secure permissions on the temp file
        os.chmod(zip_path, 0o600)  # Read/write for owner only

        logger.debug("Decryption kit built at %s", zip_path)
        return zip_path
    except Exception:
        # Clean up on any error during creation
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _cleanup_decryption_kit(kit_path: Path) -> None:
    """
    Clean up decryption kit temporary file.

    Args:
        kit_path: Path to the decryption kit zip file to clean up.

    Note:
        Safe to call multiple times - ignores missing files.
    """
    try:
        kit_path.unlink(missing_ok=True)
        logger.debug("Cleaned up decryption kit: %s", kit_path)
    except OSError as exc:
        logger.warning("Failed to clean up decryption kit %s: %s", kit_path, exc)


def _standalone_decrypt_script() -> str:
    """
    Return the source of a standalone decrypt.py that has zero
    Lazarus dependencies — only needs pip install cryptography.
    """
    template_path = Path(__file__).parent / "templates" / "standalone_decrypt.py"
    return template_path.read_text(encoding="utf-8")


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
            Attachment,
            Disposition,
            FileContent,
            FileName,
            FileType,
            Mail,
        )
    except ImportError as exc:
        raise AlertError(
            "sendgrid package not installed. Run: pip install sendgrid"
        ) from exc

    api_key = os.getenv("SENDGRID_API_KEY")
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
            data = Path(file_path).read_bytes()
            encoded = base64.b64encode(data).decode()
            att = Attachment(
                FileContent(encoded),
                FileName(filename),
                FileType(mime_type),
                Disposition("attachment"),
            )
            message.add_attachment(att)

    try:
        client = sendgrid.SendGridAPIClient(api_key=api_key)
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
      <p>{urgency} Your dead man's switch will trigger in <strong>{days_remaining} day{"s" if days_remaining != 1 else ""}</strong>.</p>
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
