"""
cli/setup.py — Interactive setup wizard for Lazarus Protocol.

Called by `lazarus init`. Uses questionary for prompts and Rich for display.

TODO: implement run_setup_wizard() end-to-end.
"""

from __future__ import annotations

import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from core.config import BeneficiaryConfig

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

    TODO: implement each step.
    """
    _print_banner()

    # Step 2 — Owner info
    owner_name  = _prompt_owner_name()
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
    # TODO: call core.encryption.encrypt_file(...)

    # Step 8 — IPFS (optional)
    # TODO: offer IPFS upload if available

    # Step 9 — Save config
    # TODO: build LazarusConfig and call core.config.save_config(...)

    # Step 10 — Verification test
    _run_verification_test()

    # Step 11 — Done
    _print_success_summary()


# ---------------------------------------------------------------------------
# Individual prompt helpers (each returns validated user input)
# ---------------------------------------------------------------------------

def _print_banner() -> None:
    console.print(Panel.fit(
        "[bold red]⚰️  Lazarus Protocol — Setup Wizard[/bold red]\n"
        "[dim]Your secrets survive you.[/dim]",
        border_style="red",
    ))


def _prompt_owner_name() -> str:
    """Ask for the owner's full name. TODO: use questionary.text()"""
    raise NotImplementedError


def _prompt_owner_email() -> str:
    """Ask for the owner's email for alerts. Validates format."""
    raise NotImplementedError


def _validate_email(email: str) -> bool:
    """Validate email format using regex pattern."""
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email))


def _prompt_beneficiary() -> BeneficiaryConfig:
    """
    Ask for beneficiary name, email, and path to their RSA public key PEM.
    Returns BeneficiaryConfig dataclass matching core.config.BeneficiaryConfig.
    TODO: validate that the key file exists and is a valid RSA public key.
    Email validation uses _validate_email() regex pattern.
    """
    raise NotImplementedError


def _prompt_secret_file() -> Path:
    """
    Ask for the path to the secret file to encrypt.
    Validates: file exists, readable, reasonable size (<50MB).
    TODO: implement with questionary.path().
    """
    raise NotImplementedError


def _prompt_checkin_interval() -> int:
    """
    Ask how many days before the switch triggers (default: 30).
    TODO: validate 7 <= interval <= 365.
    """
    raise NotImplementedError


def _prompt_telegram() -> str | None:
    """
    Ask if user wants Telegram alerts. If yes, return chat ID string.
    Returns None if skipped.
    TODO: implement.
    """
    raise NotImplementedError


def _run_verification_test() -> None:
    """
    Generate a dummy file, encrypt it, have the beneficiary decrypt it,
    confirm they can read it. Proves the key works before anything real happens.
    TODO: implement.
    """
    raise NotImplementedError


def _print_success_summary() -> None:
    """Print a Rich summary table showing vault is armed and ready."""
    # TODO: display owner, beneficiary, interval, IPFS status
    console.print("\n[bold green]✔ Lazarus is armed. Stay alive.[/bold green]")
