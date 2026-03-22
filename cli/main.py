"""
cli/main.py — Lazarus Protocol CLI entry point.

Commands:
    lazarus init              Setup wizard
    lazarus ping              Manual check-in
    lazarus status            Show vault status (rich dashboard)
    lazarus agent start       Start heartbeat agent
    lazarus agent stop        Stop heartbeat agent
    lazarus freeze            Extend deadline by N days
    lazarus test-trigger      Dry-run delivery simulation
    lazarus update-secret     Replace the secret file
    lazarus add-beneficiary   Add a new beneficiary

Run with: python -m lazarus <command>
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from core.config import (
    LAZARUS_DIR,
    BeneficiaryConfig,
    BeneficiaryVault,
    VaultConfig,
    load_config,
    save_config,
    record_checkin,
    days_since_checkin,
    days_remaining,
    extend_deadline,
    get_vault_size,
    add_beneficiary_vault,
)
from core.encryption import load_public_key_from_file, encrypt_for_single_beneficiary

console = Console()

EVENTS_LOG = LAZARUS_DIR / "events.log"
LAZARUS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(EVENTS_LOG),
        logging.StreamHandler(),
    ],
)
event_logger = logging.getLogger("lazarus.events")


def _log_event(event_type: str, message: str) -> None:
    """Log an event to both file and console."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    log_entry = f"[{timestamp}] {event_type}: {message}"
    event_logger.info(log_entry)


@click.group()
@click.version_option("0.1.0", prog_name="lazarus")
def cli():
    """Lazarus Protocol — Self-hosted dead man's switch for crypto holders."""
    pass


@cli.command()
def init():
    """Setup wizard — create and arm your vault."""
    console.print("[bold yellow]Lazarus Init Wizard[/bold yellow]")
    raise NotImplementedError("init wizard not yet implemented")


@cli.command()
def ping():
    """Manual check-in — resets the countdown timer."""
    try:
        config = load_config()
        updated = record_checkin(config)
        save_config(updated)
        remaining = days_remaining(updated)
        _log_event("CHECKIN", f"Owner {config.owner_name} checked in. {remaining:.1f} days remaining.")
        console.print(f"[green]Check-in recorded.[/green]")
        console.print(f"[dim]Days until trigger: {remaining:.1f}[/dim]")
    except FileNotFoundError:
        console.print("[red]Lazarus not initialized. Run: lazarus init[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def status():
    """Show vault status with rich dashboard."""
    try:
        config = load_config()
        since = days_since_checkin(config)
        remaining = days_remaining(config)
        vault_size = get_vault_size(config)

        if remaining > 10:
            status_color = "green"
        elif remaining > 3:
            status_color = "yellow"
        elif remaining > 0:
            status_color = "bold red"
        else:
            status_color = "red"

        table = Table(title="Lazarus Protocol — Status Dashboard", show_header=True, header_style="bold cyan")
        table.add_column("Field", style="bold")
        table.add_column("Value", style="white")

        table.add_row("Status", f"[{status_color}]{'ARMED' if config.armed else 'DISARMED'}[/{status_color}]")
        table.add_row("Owner", config.owner_name)
        table.add_row("Owner Email", config.owner_email)
        table.add_row("Check-in Interval", f"{config.checkin_interval_days} days")
        table.add_row("Days Since Ping", f"{since:.1f} days")
        table.add_row("Days Until Trigger", f"[{status_color}]{remaining:.1f} days[/{status_color}]")
        table.add_row("Beneficiary Count", str(len(config.vault.beneficiaries)))
        table.add_row("Vault Size", _format_size(vault_size))
        table.add_row("Encrypted File", config.vault.encrypted_file_path)
        if config.vault.ipfs_cid:
            table.add_row("IPFS CID", config.vault.ipfs_cid[:20] + "...")

        console.print(table)

        console.print("\n[bold cyan]Beneficiaries:[/bold cyan]")
        for b in config.vault.beneficiaries:
            console.print(f"  - {b.beneficiary_name}")

    except FileNotFoundError:
        console.print("[red]Lazarus not initialized. Run: lazarus init[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@cli.group()
def agent():
    """Manage the background heartbeat agent."""
    pass


@agent.command("start")
def agent_start():
    """Start the background heartbeat agent."""
    console.print("[green]Agent starting...[/green]")
    raise NotImplementedError


@agent.command("stop")
def agent_stop():
    """Stop the background heartbeat agent."""
    console.print("[yellow]Agent stopping...[/yellow]")
    raise NotImplementedError


@cli.command()
@click.option("--days", default=30, show_default=True, help="Number of days to extend deadline.")
def freeze(days: int):
    """Panic button — extend the trigger deadline by N days."""
    try:
        config = load_config()
        remaining_before = days_remaining(config)

        console.print(f"[bold cyan]Extend deadline by {days} days?[/bold cyan]")
        confirm = click.confirm(f"Current deadline: {remaining_before:.1f} days. Extend by {days} days?", default=False)

        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            return

        updated = extend_deadline(config, days)
        save_config(updated)
        remaining_after = days_remaining(updated)

        _log_event("FREEZE", f"Owner {config.owner_name} extended deadline by {days} days. New days remaining: {remaining_after:.1f}")
        console.print(f"[bold green]Deadline extended by {days} days.[/bold green]")
        console.print(f"[dim]New days remaining: {remaining_after:.1f}[/dim]")

    except FileNotFoundError:
        console.print("[red]Lazarus not initialized. Run: lazarus init[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command("test-trigger")
def test_trigger():
    """Dry run — simulate delivery without actually sending anything."""
    console.print("[bold magenta]Test trigger (dry run)[/bold magenta]")
    raise NotImplementedError


@cli.command("update-secret")
@click.argument("new_secret_path", type=click.Path(exists=True))
def update_secret(new_secret_path: str):
    """Replace the encrypted secret file with a new one."""
    console.print(f"[green]Updating secret from: {new_secret_path}[/green]")
    raise NotImplementedError


@cli.command("add-beneficiary")
@click.option("--name", required=True, help="Beneficiary name")
@click.option("--email", required=True, help="Beneficiary email")
@click.option("--public-key", "public_key_path", required=True, type=click.Path(exists=True), help="Path to RSA public key PEM file")
def add_beneficiary(name: str, email: str, public_key_path: str):
    """Add a new beneficiary who can decrypt the vault."""
    try:
        config = load_config()

        for existing in config.vault.beneficiaries:
            if existing.beneficiary_name.lower() == name.lower():
                console.print(f"[red]Beneficiary '{name}' already exists.[/red]")
                return

        public_key_pem = load_public_key_from_file(Path(public_key_path))

        enc_path = Path(config.vault.encrypted_file_path)
        output_dir = enc_path.parent

        _, key_blob_entry = encrypt_for_single_beneficiary(
            plaintext_path=Path(config.vault.secret_file_path),
            beneficiary_name=name,
            recipient_public_key_pem=public_key_pem,
            output_dir=output_dir,
        )

        updated = add_beneficiary_vault(config, name, key_blob_entry.key_blob)
        save_config(updated)

        _log_event("BENEFICIARY_ADDED", f"Owner {config.owner_name} added beneficiary: {name} <{email}>")
        console.print(f"[green]Beneficiary '{name}' added successfully.[/green]")
        console.print(f"[dim]Email: {email}[/dim]")
        console.print(f"[dim]Key file: {public_key_path}[/dim]")
        console.print(f"\n[yellow]Note: You must securely deliver the new key_blob to {name}.[/yellow]")

    except FileNotFoundError:
        console.print("[red]Lazarus not initialized. Run: lazarus init[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    cli()
