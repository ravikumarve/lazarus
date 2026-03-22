"""
cli/setup.py — Interactive setup wizard for Lazarus Protocol.

Called by `lazarus init`. Uses Rich for prompts and display.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt, PromptType

from core.config import (
    BeneficiaryConfig,
    BeneficiaryVault,
    VaultConfig,
    LazarusConfig,
    save_config,
    load_config,
    config_exists,
    LAZARUS_DIR,
)
from core.encryption import (
    generate_rsa_keypair,
    load_public_key_from_file,
    encrypt_for_single_beneficiary,
    decrypt_file,
)

console = Console()


def run_setup_wizard() -> None:
    """
    Full interactive setup wizard. Steps:

    1. Welcome banner + check for existing config
    2. Collect owner info (name, email)
    3. Collect beneficiary info (name, email, generate or import keypair)
    4. Locate secret file
    5. Set check-in interval (default 30 days)
    6. Optional: Telegram chat ID
    7. Encrypt the secret file
    8. Save config to ~/.lazarus/config.json
    9. Run beneficiary verification test
    10. Confirm armed + show status summary
    """
    _print_banner()

    if config_exists():
        console.print("\n[yellow]⚠️  Lazarus is already initialized.[/yellow]")
        if not Confirm.ask("Do you want to re-initialize? This will overwrite existing config."):
            console.print("[dim]Aborted.[/dim]")
            return
        console.print()

    console.print("[bold cyan]Step 1:[/bold cyan] Let's set up your information.\n")

    owner_name = _prompt_owner_name()
    owner_email = _prompt_owner_email()

    console.print(f"\n[bold cyan]Step 2:[/bold cyan] Now let's set up your beneficiary.\n")
    beneficiary = _prompt_beneficiary()

    console.print(f"\n[bold cyan]Step 3:[/bold cyan] Choose the file you want to protect.\n")
    secret_path = _prompt_secret_file()

    console.print(f"\n[bold cyan]Step 4:[/bold cyan] Set your check-in schedule.\n")
    interval = _prompt_checkin_interval()

    console.print(f"\n[bold cyan]Step 5:[/bold cyan] Telegram alerts (optional).\n")
    telegram_chat_id = _prompt_telegram()

    console.print("\n[bold cyan]Step 6:[/bold cyan] Encrypting your vault...\n")

    vault_data = _encrypt_vault(
        secret_path=secret_path,
        beneficiary_name=beneficiary.name,
        beneficiary_public_key_pem=beneficiary.public_key_path,
    )

    console.print("\n[bold cyan]Step 7:[/bold cyan] Saving configuration...\n")

    config = LazarusConfig(
        owner_name=owner_name,
        owner_email=owner_email,
        beneficiary=beneficiary,
        vault=vault_data,
        checkin_interval_days=interval,
        last_checkin_timestamp=None,
        telegram_chat_id=telegram_chat_id,
        armed=True,
    )

    save_config(config)
    console.print("[green]✓ Configuration saved.[/green]")

    console.print("\n[bold cyan]Step 8:[/bold cyan] Verifying beneficiary can decrypt...\n")
    _run_verification_test(beneficiary.name, vault_data.encrypted_file_path, vault_data.beneficiaries[0].key_blob)

    _print_success_summary(config)


def _encrypt_vault(
    secret_path: Path,
    beneficiary_name: str,
    beneficiary_public_key_pem: str,
) -> VaultConfig:
    """Encrypt the secret file and return vault config."""
    vault_dir = LAZARUS_DIR / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    public_key_pem = load_public_key_from_file(Path(beneficiary_public_key_pem))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Encrypting...", total=None)
        encrypted_path, key_blob = encrypt_for_single_beneficiary(
            plaintext_path=secret_path,
            beneficiary_name=beneficiary_name,
            recipient_public_key_pem=public_key_pem,
            output_dir=vault_dir,
        )

    vault_config = VaultConfig(
        secret_file_path=str(secret_path),
        encrypted_file_path=str(encrypted_path),
        beneficiaries=[
            BeneficiaryVault(beneficiary_name=beneficiary_name, key_blob=key_blob.key_blob)
        ],
        ipfs_cid=None,
    )

    return vault_config


def _prompt_owner_name() -> str:
    """Ask for the owner's full name."""
    while True:
        name = Prompt.ask("[cyan]Your full name[/cyan]")
        if name and name.strip():
            return name.strip()
        console.print("[red]Name cannot be empty.[/red]")


def _prompt_owner_email() -> str:
    """Ask for the owner's email for alerts with validation."""
    while True:
        email = Prompt.ask("[cyan]Your email address[/cyan]")
        if email and _validate_email(email):
            return email.strip()
        console.print("[red]Please enter a valid email address.[/red]")


def _validate_email(email: str) -> bool:
    """Validate email format using regex pattern."""
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))


def _prompt_beneficiary() -> BeneficiaryConfig:
    """
    Ask for beneficiary name, email, and path to their RSA public key PEM.
    Offer to generate a keypair if they don't have one.
    """
    console.print("[dim]Your beneficiary will receive your secrets if the switch triggers.[/dim]\n")

    while True:
        name = Prompt.ask("[cyan]Beneficiary's full name[/cyan]")
        if name and name.strip():
            name = name.strip()
            break
        console.print("[red]Name cannot be empty.[/red]")

    while True:
        email = Prompt.ask("[cyan]Beneficiary's email address[/cyan]")
        if email and _validate_email(email):
            email = email.strip()
            break
        console.print("[red]Please enter a valid email address.[/red]")

    console.print()
    has_key = Confirm.ask("Does the beneficiary have an RSA public key?", default=True)

    if has_key:
        public_key_path = _prompt_public_key_path()
        return BeneficiaryConfig(name=name, email=email, public_key_path=str(public_key_path))

    console.print("\n[yellow]Generating RSA-4096 keypair for beneficiary...[/yellow]")
    private_path, public_path = _generate_keypair_for_beneficiary(name)
    console.print(f"[green]✓ Keypair generated![/green]")
    console.print(f"[dim]  Private key (give to beneficiary): {private_path}[/dim]")
    console.print(f"[dim]  Public key (stored in config): {public_path}[/dim]")

    _warn_about_private_key(private_path)

    return BeneficiaryConfig(name=name, email=email, public_key_path=str(public_path))


def _prompt_public_key_path() -> Path:
    """Prompt for existing public key path with validation."""
    while True:
        key_path = Path(Prompt.ask("[cyan]Path to beneficiary's public key (.pem)[/cyan]"))
        if key_path.exists() and key_path.is_file():
            try:
                load_public_key_from_file(key_path)
                return key_path
            except ValueError:
                console.print("[red]Invalid RSA public key file.[/red]")
        else:
            console.print("[red]File not found. Please provide a valid path.[/red]")


def _generate_keypair_for_beneficiary(name: str) -> tuple[Path, Path]:
    """Generate RSA-4096 keypair and save to files."""
    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", name)[:20]
    keys_dir = LAZARUS_DIR / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    timestamp = Path(LAZARUS_DIR / "config.json").stat().st_mtime if (LAZARUS_DIR / "config.json").exists() else 0
    private_path = keys_dir / f"{safe_name}_private_{int(timestamp)}.pem"
    public_path = keys_dir / f"{safe_name}_public_{int(timestamp)}.pem"

    private_pem, public_pem = generate_rsa_keypair()
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    if os.name == "posix":
        os.chmod(private_path, 0o600)

    return private_path, public_path


def _warn_about_private_key(private_key_path: Path) -> None:
    """Display warning about the private key."""
    console.print(Panel.fit(
        "[bold yellow]⚠️  IMPORTANT SECURITY WARNING[/bold yellow]\n\n"
        f"The private key file was saved to:\n"
        f"  [red]{private_key_path}[/red]\n\n"
        "You MUST:\n"
        "1. Transfer this file to your beneficiary securely\n"
        "2. Delete the local copy after transfer\n"
        "3. Never email or share this file unencrypted\n\n"
        "[dim]Without this private key, your beneficiary cannot decrypt your secrets.[/dim]",
        border_style="yellow",
    ))


def _prompt_secret_file() -> Path:
    """Ask for the path to the secret file to encrypt."""
    while True:
        path_input = Prompt.ask("[cyan]Path to secret file (PDF, TXT, etc.)[/cyan]")
        if path_input:
            secret_path = Path(path_input.strip())
            if secret_path.exists() and secret_path.is_file():
                size_mb = secret_path.stat().st_size / (1024 * 1024)
                if size_mb > 50:
                    console.print(f"[red]File too large ({size_mb:.1f}MB). Maximum is 50MB.[/red]")
                    continue
                console.print(f"[green]✓ Selected: {secret_path.name} ({size_mb:.2f}MB)[/green]")
                return secret_path
            else:
                console.print("[red]File not found. Please provide a valid path.[/red]")
        else:
            console.print("[red]Path cannot be empty.[/red]")


def _prompt_checkin_interval() -> int:
    """Ask how many days before the switch triggers."""
    while True:
        interval_str = Prompt.ask("[cyan]Check-in interval (days, default: 30)[/cyan]", default="30")
        try:
            interval = int(interval_str or "30")
            if 7 <= interval <= 365:
                return interval
            console.print("[red]Interval must be between 7 and 365 days.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")


def _prompt_telegram() -> str | None:
    """Ask if user wants Telegram alerts. If yes, return chat ID."""
    if not Confirm.ask("Enable Telegram alerts?", default=False):
        return None

    console.print("[dim]Get your Chat ID from @userinfobot on Telegram.[/dim]")
    while True:
        chat_id = Prompt.ask("[cyan]Telegram Chat ID[/cyan]")
        if chat_id and chat_id.strip():
            return chat_id.strip()
        console.print("[red]Chat ID cannot be empty.[/red]")


def _run_verification_test(
    beneficiary_name: str,
    encrypted_path: str,
    key_blob: str,
) -> None:
    """
    Create a test file, encrypt it, decrypt it, and verify.
    Proves the beneficiary's key works before real data.
    """
    console.print("[dim]Running verification test...[/dim]")

    test_message = b"LAZARUS_VERIFICATION_TEST"
    test_file = Path(tempfile.mktemp(suffix=".bin"))
    test_file.write_bytes(test_message)

    output_dir = Path(tempfile.mkdtemp())
    try:
        test_public_path = output_dir / "test_public.pem"
        test_private_path = output_dir / "test_private.pem"

        private_pem, public_pem = generate_rsa_keypair()
        test_public_path.write_bytes(public_pem)
        test_private_path.write_bytes(private_pem)

        if os.name == "posix":
            os.chmod(test_private_path, 0o600)

        encrypted_test, key_blob_test = encrypt_for_single_beneficiary(
            plaintext_path=test_file,
            beneficiary_name=beneficiary_name,
            recipient_public_key_pem=public_pem,
            output_dir=output_dir,
        )

        decrypted_test_path = output_dir / "decrypted.bin"
        decrypt_file(
            encrypted_path=encrypted_test,
            key_blob_b64=key_blob_test.key_blob,
            private_key_pem=private_pem,
            output_path=decrypted_test_path,
        )

        if decrypted_test_path.read_bytes() == test_message:
            console.print("[green]✓ Verification test PASSED![/green]")
            console.print("[dim]  Your beneficiary's key is working correctly.[/dim]")
        else:
            console.print("[red]✗ Verification test FAILED![/red]")
            console.print("[yellow]  The decrypted content doesn't match.[/yellow]")

    except Exception as e:
        console.print(f"[yellow]⚠ Verification test skipped: {e}[/yellow]")
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        test_file.unlink(missing_ok=True)


def _print_success_summary(config: LazarusConfig) -> None:
    """Print a Rich summary table showing vault is armed and ready."""
    from rich.table import Table

    table = Table(title="⚰️  Lazarus Protocol — Setup Complete", show_header=False)
    table.add_column(style="bold cyan")
    table.add_column()

    table.add_row("Owner", config.owner_name)
    table.add_row("Email", config.owner_email)
    table.add_row("Beneficiary", config.beneficiary.name)
    table.add_row("Beneficiary Email", config.beneficiary.email)
    table.add_row("Check-in Interval", f"{config.checkin_interval_days} days")
    table.add_row("Encrypted File", Path(config.vault.encrypted_file_path).name)
    table.add_row("Status", "[green]ARMED[/green]")

    console.print()
    console.print(table)
    console.print()

    console.print(Panel.fit(
        "[bold green]✔ Lazarus is armed and ready![/bold green]\n\n"
        "Next steps:\n"
        "1. Run [cyan]lazarus agent start[/cyan] to start the heartbeat agent\n"
        "2. Run [cyan]lazarus ping[/cyan] daily (or automate with crontab)\n"
        "3. Run [cyan]lazarus status[/cyan] to check your vault\n"
        "4. Visit [cyan]http://localhost:7777[/cyan] for the web dashboard\n\n"
        "[dim]Stay alive.[/dim]",
        border_style="green",
    ))


def _print_banner() -> None:
    """Print welcome banner."""
    console.print(Panel.fit(
        "[bold red]⚰️  Lazarus Protocol — Setup Wizard[/bold red]\n"
        "[dim]Your secrets survive you.[/dim]",
        border_style="red",
    ))
