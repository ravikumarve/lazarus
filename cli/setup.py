"""
cli/setup.py — Interactive setup wizard for Lazarus Protocol.

Called by `lazarus init`. Uses questionary for prompts and Rich for display.
"""

from __future__ import annotations

import os
import re
import questionary
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import BeneficiaryConfig, VaultConfig, LazarusConfig, save_config
from core.encryption import encrypt_file, load_public_key_from_file

console = Console()


def run_setup_wizard() -> None:
    """
    Full interactive setup wizard. Steps:

    1. Welcome banner
    2. Collect owner info (name, email)
    3. Collect beneficiary info (name, email, public key path)
    4. Locate secret file
    5. Set check-in interval (default 30 days)
    6. Optional: Telegram chat ID
    7. Encrypt the secret file
    8. Optional: upload to IPFS
    9. Save config to ~/.lazarus/config.json
    10. Run beneficiary verification test
    11. Confirm armed + show status summary
    """
    _print_banner()

    # Step 2 — Owner info
    owner_name = _prompt_owner_name()
    owner_email = _prompt_owner_email()

    # Step 3 — Beneficiary info
    beneficiary = _prompt_beneficiary()

    # Step 4 — Secret file
    secret_path = _prompt_secret_file()

    # Step 5 — Check-in interval
    interval = _prompt_checkin_interval()

    # Step 6 — Telegram (optional)
    telegram_chat_id = _prompt_telegram()

    # Step 7 — Encrypt
    console.print("\n[bold yellow]🔐 Encrypting your secret file...[/bold yellow]")
    encrypted_file_path, key_blob = _encrypt_secret_file(secret_path, beneficiary)

    # Step 8 — IPFS (optional)
    ipfs_cid = _prompt_ipfs_upload()

    # Step 9 — Save config
    vault_config = VaultConfig(
        secret_file_path=str(secret_path),
        encrypted_file_path=str(encrypted_file_path),
        key_blob=key_blob,
        ipfs_cid=ipfs_cid,
    )

    config = LazarusConfig(
        owner_name=owner_name,
        owner_email=owner_email,
        beneficiary=beneficiary,
        vault=vault_config,
        checkin_interval_days=interval,
        telegram_chat_id=telegram_chat_id,
        armed=True,
    )

    save_config(config)

    # Step 10 — Verification test
    _run_verification_test(config)

    # Step 11 — Done
    _print_success_summary(config)


# ---------------------------------------------------------------------------
# Individual prompt helpers (each returns validated user input)
# ---------------------------------------------------------------------------


def _print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold red]⚰️  Lazarus Protocol — Setup Wizard[/bold red]\n"
            "[dim]Your secrets survive you.[/dim]",
            border_style="red",
        )
    )


def _prompt_owner_name() -> str:
    """Ask for the owner's full name."""
    return questionary.text(
        "What's your full name?",
        validate=lambda text: True if text.strip() else "Name cannot be empty",
    ).ask()


def _prompt_owner_email() -> str:
    """Ask for the owner's email for alerts. Validates format."""
    return questionary.text(
        "What's your email for alerts?",
        validate=lambda email: "Please enter a valid email"
        if not _validate_email(email)
        else True,
    ).ask()


def _validate_email(email: str) -> bool:
    """Validate email format using RFC 5322 compliant regex pattern."""
    if not email or len(email) > 254:
        return False
    
    # RFC 5322 compliant email regex
    pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    return bool(re.match(pattern, email))


def _prompt_beneficiary() -> BeneficiaryConfig:
    """
    Ask for beneficiary name, email, and path to their RSA public key PEM.
    Returns BeneficiaryConfig dataclass matching core.config.BeneficiaryConfig.
    """
    console.print("\n[bold]👥 Beneficiary Setup[/bold]")

    name = questionary.text(
        "Beneficiary's full name:",
        validate=lambda text: True if text.strip() else "Name cannot be empty",
    ).ask()

    email = questionary.text(
        "Beneficiary's email:",
        validate=lambda email: "Please enter a valid email"
        if not _validate_email(email)
        else True,
    ).ask()

    public_key_path = questionary.path(
        "Path to beneficiary's RSA public key PEM file:",
        validate=lambda path: _validate_public_key_file(Path(path)),
    ).ask()

    return BeneficiaryConfig(name=name, email=email, public_key_path=public_key_path)


def _validate_public_key_file(path: Path) -> bool:
    """Validate that the public key file exists, is safe, and looks like a valid RSA key."""
    if not path.exists():
        return "Public key file does not exist"
    if not path.is_file():
        return "Path is not a file"
    
    # Check for path traversal attempts
    if ".." in str(path):
        return "Path traversal detected"
    
    # Check file size
    if path.stat().st_size > 1024 * 1024:  # 1MB max
        return "File is too large for a public key"
    
    # Check file is within allowed directories
    allowed_dirs = [Path.home(), Path.cwd()]
    try:
        resolved = path.resolve()
        is_allowed = False
        for allowed in allowed_dirs:
            allowed_resolved = allowed.resolve()
            if resolved == allowed_resolved or str(resolved).startswith(str(allowed_resolved)):
                is_allowed = True
                break
        
        if not is_allowed:
            return "File not in allowed directories"
    except (OSError, RuntimeError) as e:
        return f"Invalid path: {e}"

    try:
        content = path.read_text()
        if "-----BEGIN PUBLIC KEY-----" not in content:
            return "File does not contain a valid PEM public key"
        if "-----END PUBLIC KEY-----" not in content:
            return "File does not contain a complete PEM public key"
    except (IOError, UnicodeDecodeError):
        return "Could not read file as text"

    return True


def _prompt_secret_file() -> Path:
    """
    Ask for the path to the secret file to encrypt.
    Validates: file exists, readable, reasonable size (<50MB).
    """
    return questionary.path(
        "Path to your secret file to encrypt:",
        validate=lambda path: _validate_secret_file(Path(path)),
    ).ask()


def _validate_secret_file(path: Path) -> bool:
    """Validate secret file exists, is safe, and is reasonable size."""
    if not path.exists():
        return "File does not exist"
    if not path.is_file():
        return "Path is not a file"
    
    # Check for path traversal attempts
    if ".." in str(path):
        return "Path traversal detected"
    
    # Check file size
    if path.stat().st_size > 50 * 1024 * 1024:  # 50MB max
        return "File is too large (max 50MB)"
    
    # Check file is readable
    if not os.access(path, os.R_OK):
        return "File is not readable"
    
    # Check file is within allowed directories
    allowed_dirs = [Path.home(), Path.cwd()]
    try:
        resolved = path.resolve()
        is_allowed = False
        for allowed in allowed_dirs:
            allowed_resolved = allowed.resolve()
            if resolved == allowed_resolved or str(resolved).startswith(str(allowed_resolved)):
                is_allowed = True
                break
        
        if not is_allowed:
            return "File not in allowed directories"
    except (OSError, RuntimeError) as e:
        return f"Invalid path: {e}"
    
    return True


def _prompt_checkin_interval() -> int:
    """
    Ask how many days before the switch triggers (default: 30).
    """
    return int(
        questionary.text(
            "Check-in interval (days, 7-365):",
            default="30",
            validate=lambda days: _validate_interval(days),
        ).ask()
    )


def _validate_interval(days_str: str) -> bool:
    """Validate check-in interval is between 7 and 365 days."""
    try:
        days = int(days_str)
        if 7 <= days <= 365:
            return True
        return "Interval must be between 7 and 365 days"
    except ValueError:
        return "Please enter a valid number"


def _prompt_telegram() -> str | None:
    """
    Ask if user wants Telegram alerts. If yes, return chat ID string.
    Returns None if skipped.
    """
    use_telegram = questionary.confirm(
        "Would you like Telegram alerts?", default=False
    ).ask()

    if not use_telegram:
        return None

    return questionary.text(
        "Telegram chat ID:",
        validate=lambda text: True if text.strip() else "Chat ID cannot be empty",
    ).ask()


def _encrypt_secret_file(
    secret_path: Path, beneficiary: BeneficiaryConfig
) -> tuple[str, str]:
    """Encrypt the secret file and return (encrypted_path, key_blob)."""
    console.print(
        f"[dim]Loading beneficiary's public key from: {beneficiary.public_key_path}[/dim]"
    )

    # Load the beneficiary's public key
    try:
        public_key_pem = load_public_key_from_file(Path(beneficiary.public_key_path))
    except Exception as e:
        console.print(f"[red]❌ Failed to load public key: {e}[/red]")
        raise

    # Encrypt the file using the beneficiary's public key
    try:
        encrypted_path, key_blob = encrypt_file(
            plaintext_path=secret_path,
            recipient_public_key_pem=public_key_pem,
            output_dir=secret_path.parent,  # Save encrypted file in same directory
        )

        console.print(f"[green]✓ Encrypted file saved to: {encrypted_path}[/green]")
        return str(encrypted_path), key_blob
    except Exception as e:
        console.print(f"[red]❌ Encryption failed: {e}[/red]")
        raise


def _prompt_ipfs_upload() -> str | None:
    """Ask if user wants to upload to IPFS. Returns CID if yes, None if no."""
    use_ipfs = questionary.confirm(
        "Would you like to upload to IPFS? (optional)", default=False
    ).ask()

    if not use_ipfs:
        return None

    console.print("[yellow]IPFS upload not yet implemented[/yellow]")
    return None


def _run_verification_test(config: LazarusConfig) -> None:
    """
    Generate a dummy file, encrypt it, have the beneficiary decrypt it,
    confirm they can read it. Proves the key works before anything real happens.
    """
    console.print("\n[bold]🔍 Running verification test...[/bold]")
    console.print("[yellow]Verification test not yet implemented[/yellow]")


def _print_success_summary(config: LazarusConfig) -> None:
    """Print a Rich summary table showing vault is armed and ready."""
    table = Table(title="Lazarus Configuration Summary")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Owner", f"{config.owner_name} ({config.owner_email})")
    table.add_row(
        "Beneficiary", f"{config.beneficiary.name} ({config.beneficiary.email})"
    )
    table.add_row("Public Key", config.beneficiary.public_key_path)
    table.add_row("Secret File", config.vault.secret_file_path)
    table.add_row("Encrypted File", config.vault.encrypted_file_path)
    table.add_row("Check-in Interval", f"{config.checkin_interval_days} days")
    table.add_row("Telegram Alerts", config.telegram_chat_id or "Disabled")
    table.add_row("IPFS", config.vault.ipfs_cid or "Not uploaded")
    table.add_row(
        "Status",
        "[bold green]ARMED[/bold green]" if config.armed else "[red]DISARMED[/red]",
    )

    console.print(table)
    console.print("\n[bold green]✓ Lazarus is armed. Stay alive.[/bold green]")
    console.print("\n[dim]Run 'lazarus ping' to record your first check-in.[/dim]")
