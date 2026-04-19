"""
cli/main.py — Lazarus Protocol CLI entry point.

Commands:
    lazarus init            Setup wizard
    lazarus ping            Manual check-in
    lazarus status          Show vault status
    lazarus agent start     Start heartbeat agent
    lazarus agent stop      Stop heartbeat agent
    lazarus freeze          Extend deadline by N days
    lazarus test-trigger    Dry-run delivery simulation
    lazarus update-secret   Replace the secret file

Run with: python -m lazarus <command>
"""

import math
import time
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

from core.config import load_config, save_config, record_checkin, days_remaining
from core.config import (
    ConfigCorruptedError,
    days_since_checkin,
    is_trigger_due,
    extend_deadline,
)
from core.encryption import encrypt_file, load_public_key_from_file
from core.storage import upload_to_ipfs, StorageError
from pathlib import Path

console = Console()


@click.group()
@click.version_option("0.1.0", prog_name="lazarus")
def cli():
    """⚰️  Lazarus Protocol — Self-hosted dead man's switch for crypto holders."""
    pass


# ---------------------------------------------------------------------------
# lazarus init
# ---------------------------------------------------------------------------


@cli.command()
def init():
    """
    Setup wizard — create and arm your vault.

    Walks you through:
      - Selecting your secret file
      - Entering beneficiary details + public key
      - Setting check-in interval
      - Encrypting and storing the vault
    """
    try:
        from cli.setup import run_setup_wizard

        run_setup_wizard()
        console.print("[green]✓ Setup wizard completed successfully[/green]")
    except ImportError:
        console.print("[red]❌ Setup wizard dependencies not installed[/red]")
        console.print("Run: pip install questionary rich")
        raise
    except Exception as e:
        console.print(f"[red]❌ Setup wizard failed: {e}[/red]")
        return


# ---------------------------------------------------------------------------
# lazarus status
# ---------------------------------------------------------------------------


@cli.command()
def status():
    """
    Show vault status: armed state, days remaining, last check-in.
    """
    try:
        config = load_config()

        # Calculate status metrics
        armed_state = "✅ Armed" if config.armed else "❌ Disarmed"
        days_since_last_ping = days_since_checkin(config)
        days_until_trigger = days_remaining(config)
        trigger_due = is_trigger_due(config)

        # Format last check-in timestamp
        if config.last_checkin_timestamp:
            last_checkin = time.strftime(
                "%Y-%m-%d %H:%M:%S UTC", time.gmtime(config.last_checkin_timestamp)
            )
        else:
            last_checkin = "Never"

        # Create status table
        table = Table(
            box=box.ROUNDED, show_header=False, title="[bold]Lazarus Status[/bold]"
        )
        table.add_column("Field", style="cyan", justify="right")
        table.add_column("Value", style="white")

        # Add status rows
        table.add_row("Armed State", armed_state)
        table.add_row("Owner", f"{config.owner_name} <{config.owner_email}>")
        table.add_row(
            "Beneficiary", f"{config.beneficiary.name} <{config.beneficiary.email}>"
        )
        table.add_row("Check-in Interval", f"{config.checkin_interval_days} days")

        # Handle days since last ping
        if math.isinf(days_since_last_ping):
            days_since_str = "Never checked in"
        else:
            days_since_str = f"{days_since_last_ping:.1f} days ago"
        table.add_row("Days Since Last Ping", days_since_str)

        # Handle days remaining with appropriate colors
        if math.isinf(days_until_trigger) and days_until_trigger > 0:
            days_remaining_str = "∞ days (never checked in)"
            days_remaining_style = "yellow"
        elif days_until_trigger > 0:
            days_remaining_str = f"{days_until_trigger:.1f} days"
            days_remaining_style = "green"
        elif days_until_trigger == 0:
            days_remaining_str = "Due now"
            days_remaining_style = "red"
        else:
            days_remaining_str = f"{-days_until_trigger:.1f} days overdue"
            days_remaining_style = "red bold"

        table.add_row(
            "Days Until Trigger", f"[{days_remaining_style}]{days_remaining_str}[/]"
        )
        table.add_row("Last Check-in", last_checkin)

        # Add trigger status warning if due
        if trigger_due:
            table.add_row("⚠️  Status", "[red bold]TRIGGER DUE - VAULT WILL RELEASE[/]")
        elif math.isinf(days_since_last_ping):
            table.add_row(
                "⚠️  Status", "[yellow]Never checked in - timer starts on first ping[/]"
            )

        console.print(table)

    except FileNotFoundError:
        console.print("[red]❌ Lazarus not initialized.[/red]")
        console.print("Run: python -m lazarus init")
        return
    except ConfigCorruptedError as e:
        console.print(f"[red]❌ Config file is corrupted: {e}[/red]")
        console.print("Run: python -m lazarus init to recreate configuration")
        return
    except Exception as e:
        console.print(f"[red]❌ Error loading status: {e}[/red]")
        return


# ---------------------------------------------------------------------------
# lazarus ping
# ---------------------------------------------------------------------------


@cli.command()
def ping():
    """Manual check-in — reset the countdown timer."""
    try:
        config = load_config()
        updated_config = record_checkin(config)
        save_config(updated_config)

        # Format timestamp and show success message
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        console.print(f"[green]✓ Check-in recorded at {timestamp}[/green]")

        # Show days remaining
        remaining = days_remaining(updated_config)
        if math.isinf(remaining) and remaining > 0:
            console.print("[yellow]Timer started - first check-in recorded[/yellow]")
        elif remaining > 0:
            console.print(
                f"[green]Timer reset - next check-in due in {remaining:.1f} days[/green]"
            )
        else:
            console.print(
                f"[red]WARNING: Timer is {abs(remaining):.1f} days overdue![/red]"
            )

    except FileNotFoundError:
        console.print("[red]❌ Lazarus not initialized.[/red]")
        console.print("Run: python -m lazarus init")
        return
    except ConfigCorruptedError as e:
        console.print(f"[red]❌ Config file is corrupted: {e}[/red]")
        console.print("Run: python -m lazarus init to recreate configuration")
        return
    except Exception as e:
        console.print(f"[red]❌ Error recording check-in: {e}[/red]")
        return


# ---------------------------------------------------------------------------
# lazarus agent (sub-group)
# ---------------------------------------------------------------------------


@cli.group()
def agent():
    """Manage the background heartbeat agent."""
    pass


@agent.command("start")
def agent_start():
    """
    Start the background heartbeat agent.
    """
    console.print("[green]Agent starting...[/green]")
    try:
        from agent.heartbeat import start_agent

        start_agent()
        console.print("[green]✓ Agent started successfully[/green]")
    except ImportError:
        console.print("[red]❌ Agent dependencies not installed[/red]")
        console.print("Run: pip install APScheduler")
        raise
    except FileNotFoundError:
        console.print("[red]❌ Lazarus not initialized.[/red]")
        console.print("Run: python -m lazarus init")
        return
    except Exception as e:
        console.print(f"[red]❌ Failed to start agent: {e}[/red]")
        return


@agent.command("stop")
def agent_stop():
    """
    Stop the background heartbeat agent.
    """
    console.print("[yellow]Agent stopping...[/yellow]")
    try:
        from agent.heartbeat import stop_agent

        stop_agent()
        console.print("[green]✓ Agent stopped successfully[/green]")
    except ImportError:
        console.print("[red]❌ Agent dependencies not installed[/red]")
        console.print("Run: pip install APScheduler")
        raise
    except Exception as e:
        console.print(f"[red]❌ Failed to stop agent: {e}[/red]")
        return


# ---------------------------------------------------------------------------
# lazarus freeze
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--days", default=30, show_default=True, help="Number of days to extend deadline."
)
def freeze(days: int):
    """
    Panic button — extend the trigger deadline by N days.
    """
    try:
        config = load_config()
        updated_config = extend_deadline(config, days)
        save_config(updated_config)

        # Show confirmation with new deadline information
        console.print(f"[bold green]✓ Deadline extended by {days} days[/bold green]")

        # Show the new interval and days remaining
        remaining = days_remaining(updated_config)
        if math.isinf(remaining) and remaining > 0:
            console.print(
                f"[yellow]New check-in interval: {updated_config.checkin_interval_days} days[/yellow]"
            )
            console.print("[yellow]Timer starts on first check-in[/yellow]")
        elif remaining > 0:
            console.print(
                f"[green]New check-in interval: {updated_config.checkin_interval_days} days[/green]"
            )
            console.print(f"[green]Next check-in due in {remaining:.1f} days[/green]")
        else:
            console.print(
                f"[yellow]New check-in interval: {updated_config.checkin_interval_days} days[/yellow]"
            )
            console.print(
                f"[red]WARNING: Timer is {abs(remaining):.1f} days overdue![/red]"
            )
            console.print("[red]Run 'lazarus ping' to reset the timer[/red]")

    except FileNotFoundError:
        console.print("[red]❌ Lazarus not initialized.[/red]")
        console.print("Run: python -m lazarus init")
        return
    except ConfigCorruptedError as e:
        console.print(f"[red]❌ Config file is corrupted: {e}[/red]")
        console.print("Run: python -m lazarus init to recreate configuration")
        return
    except Exception as e:
        console.print(f"[red]❌ Error extending deadline: {e}[/red]")
        return


# ---------------------------------------------------------------------------
# lazarus test-trigger
# ---------------------------------------------------------------------------


@cli.command("test-trigger")
def test_trigger():
    """
    Dry run — simulate delivery without actually sending anything.

    Steps:
        1. Load config
        2. Build the delivery payload
        3. Print what would be sent, to whom, and how
        4. Do NOT call the real send functions
    """
    console.print("[bold magenta]🔬 Test trigger (dry run)[/bold magenta]")

    try:
        # Load configuration
        config = load_config()

        # Check if vault is armed
        if not config.armed:
            console.print(
                "[yellow]⚠️  Switch is disarmed - trigger would not fire[/yellow]"
            )
            return

        # Check if encrypted file exists
        encrypted_path = Path(config.vault.encrypted_file_path)
        if not encrypted_path.exists():
            console.print("[red]❌ Encrypted vault file not found:[/red]")
            console.print(f"   {encrypted_path}")
            console.print("[yellow]⚠️  Trigger would fail - vault file missing[/yellow]")
            return

        # Check if beneficiary public key exists
        pub_key_path = Path(config.beneficiary.public_key_path)
        if not pub_key_path.exists():
            console.print("[yellow]⚠️  Beneficiary public key not found:[/yellow]")
            console.print(f"   {pub_key_path}")
            console.print(
                "[yellow]   Trigger would proceed but decryption may fail[/yellow]"
            )

        # Display simulation details
        console.print("\n[bold cyan]📋 SIMULATION DETAILS[/bold cyan]")
        console.print("=" * 60)

        # Beneficiary information
        console.print("[bold]👤 Beneficiary:[/bold]")
        console.print(f"   Name:  {config.beneficiary.name}")
        console.print(f"   Email: {config.beneficiary.email}")
        console.print(f"   Public Key: {config.beneficiary.public_key_path}")

        # Owner information
        console.print("\n[bold]👤 Owner:[/bold]")
        console.print(f"   Name:  {config.owner_name}")
        console.print(f"   Email: {config.owner_email}")

        # Vault information
        console.print("\n[bold]🔒 Vault:[/bold]")
        console.print(f"   Encrypted file: {config.vault.encrypted_file_path}")
        console.print(f"   File size: {encrypted_path.stat().st_size:,} bytes")
        console.print(f"   Key blob present: {'✅' if config.vault.key_blob else '❌'}")
        console.print(f"   IPFS CID: {config.vault.ipfs_cid or 'None'}")
        console.print(f"   Check-in interval: {config.checkin_interval_days} days")

        # Show current trigger status
        from core.config import days_remaining, is_trigger_due

        remaining = days_remaining(config)
        trigger_due = is_trigger_due(config)

        console.print("\n[bold]⏰ Trigger Status:[/bold]")
        if trigger_due:
            console.print(
                f"   [red]🔴 TRIGGER DUE - {abs(remaining):.1f} days overdue[/red]"
            )
        elif math.isinf(remaining) and remaining > 0:
            console.print(
                "   [yellow]🟡 Never checked in - timer starts on first ping[/yellow]"
            )
        elif remaining > 0:
            console.print(f"   [green]🟢 OK - {remaining:.1f} days remaining[/green]")
        else:
            console.print(
                f"   [red]🔴 OVERDUE - {abs(remaining):.1f} days overdue[/red]"
            )

        # Email configuration check
        console.print("\n[bold]📧 Email Configuration:[/bold]")
        from agent.alerts import email_configured

        if email_configured():
            console.print("   ✅ SendGrid configured")
        else:
            console.print("   ❌ SendGrid not configured")
            console.print(
                "      [yellow]Trigger would fail - email delivery unavailable[/yellow]"
            )

        # Telegram configuration check
        console.print("\n[bold]📱 Telegram Configuration:[/bold]")
        from agent.alerts import telegram_configured

        if config.telegram_chat_id:
            if telegram_configured():
                console.print("   ✅ Telegram configured")
            else:
                console.print("   ❌ Telegram not configured")
                console.print("      [yellow]Telegram alerts would fail[/yellow]")
        else:
            console.print("   ⚪ Telegram not enabled")

        # Show what would be sent
        console.print("\n[bold]📦 What would be sent:[/bold]")
        console.print("   1. Email to beneficiary with subject:")
        console.print(
            f"      '[Lazarus] You have received an inheritance from {config.owner_name}'"
        )

        console.print("   2. Attachments:")
        console.print(
            f"      • encrypted_secrets.bin ({encrypted_path.stat().st_size:,} bytes)"
        )
        console.print(
            "      • decryption_kit.zip (standalone decrypt.py + instructions)"
        )

        # Show email content preview
        console.print("\n[bold]📄 Email content preview:[/bold]")
        from agent.alerts import _delivery_email_body

        email_body = _delivery_email_body(
            beneficiary_name=config.beneficiary.name,
            owner_name=config.owner_name,
            ipfs_cid=config.vault.ipfs_cid,
        )
        # Extract first few lines for preview
        preview_lines = email_body.split("\n")[:10]
        for line in preview_lines:
            if line.strip():
                console.print(f"   {line.strip()}")
        console.print("   [...]")

        # Show decryption kit contents
        console.print("\n[bold]🔧 Decryption kit contents:[/bold]")
        console.print("   • decrypt.py - standalone Python script")
        console.print("   • key_blob.txt - encrypted AES key")
        console.print("   • INSTRUCTIONS.txt - step-by-step guide")

        # Show IPFS details if configured
        if config.vault.ipfs_cid:
            console.print("\n[bold]🌐 IPFS Configuration:[/bold]")
            console.print(f"   CID: {config.vault.ipfs_cid}")
            console.print("   File would be available via IPFS as backup")

        # Show what would NOT happen
        console.print("\n[bold]🚫 What would NOT happen:[/bold]")
        console.print("   • No actual emails would be sent")
        console.print("   • No Telegram messages would be sent")
        console.print("   • Switch would NOT be disarmed")
        console.print("   • Config would NOT be modified")

        console.print("\n[green]✅ Dry run completed successfully[/green]")
        console.print(
            "[yellow]⚠️  This was only a simulation - no actual delivery occurred[/yellow]"
        )

    except FileNotFoundError:
        console.print("[red]❌ Lazarus not initialized.[/red]")
        console.print("Run: python -m lazarus init")
        return
    except ConfigCorruptedError as e:
        console.print(f"[red]❌ Config file is corrupted: {e}[/red]")
        console.print("Run: python -m lazarus init to recreate configuration")
        return
    except Exception as e:
        console.print(f"[red]❌ Error during test trigger: {e}[/red]")


# ---------------------------------------------------------------------------
# lazarus update-secret
# ---------------------------------------------------------------------------


@cli.command("update-secret")
@click.argument("new_secret_path", type=click.Path(exists=True))
def update_secret(new_secret_path: str):
    """
    Replace the encrypted secret file with a new one.

    Steps:
        1. Load config
        2. Re-encrypt new file using existing beneficiary public key
        3. Update vault configuration with new encrypted file and key blob
        4. Upload to IPFS if previously configured
        5. Save config
    """
    console.print(f"[green]Updating secret from: {new_secret_path}[/green]")

    try:
        # 1. Load current configuration
        config = load_config()

        # 2. Validate the new secret file exists and is readable
        new_secret_path_obj = Path(new_secret_path)
        if not new_secret_path_obj.exists():
            console.print(f"[red]❌ Secret file not found: {new_secret_path}[/red]")
            return

        if new_secret_path_obj.stat().st_size == 0:
            console.print(f"[red]❌ Secret file is empty: {new_secret_path}[/red]")
            console.print(
                "[yellow]Use a file with content or remove the --empty-file check to proceed[/yellow]"
            )
            return

        # 3. Load beneficiary public key
        beneficiary_pub_key_path = Path(config.beneficiary.public_key_path)
        if not beneficiary_pub_key_path.exists():
            console.print(
                f"[red]❌ Beneficiary public key not found: {beneficiary_pub_key_path}[/red]"
            )
            console.print(
                "[yellow]Please ensure the beneficiary's public key file still exists[/yellow]"
            )
            return

        try:
            beneficiary_pub_key = load_public_key_from_file(beneficiary_pub_key_path)
        except ValueError as e:
            console.print(f"[red]❌ Invalid beneficiary public key: {e}[/red]")
            return

        # 4. Determine output directory (use same directory as current encrypted file)
        current_encrypted_path = Path(config.vault.encrypted_file_path)
        output_dir = current_encrypted_path.parent

        # 5. Re-encrypt the new file
        console.print(
            f"[cyan]Re-encrypting file with beneficiary's public key...[/cyan]"
        )
        try:
            encrypted_file_path, key_blob_b64 = encrypt_file(
                new_secret_path_obj, beneficiary_pub_key, output_dir
            )
        except Exception as e:
            console.print(f"[red]❌ Encryption failed: {e}[/red]")
            return

        # 6. Handle IPFS upload if previously configured
        new_ipfs_cid = None
        if config.vault.ipfs_cid:
            console.print(
                "[cyan]Previous IPFS upload detected - re-uploading to IPFS...[/cyan]"
            )
            try:
                new_ipfs_cid = upload_to_ipfs(encrypted_file_path)
                console.print(
                    f"[green]✓ Uploaded to IPFS with CID: {new_ipfs_cid}[/green]"
                )
            except StorageError as e:
                console.print(f"[yellow]⚠️  IPFS upload failed: {e}[/yellow]")
                console.print("[yellow]Continuing with local storage only[/yellow]")
            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Unexpected error during IPFS upload: {e}[/yellow]"
                )
                console.print("[yellow]Continuing with local storage only[/yellow]")

        # 7. Update vault configuration
        from dataclasses import replace

        updated_vault = replace(
            config.vault,
            secret_file_path=str(new_secret_path_obj),
            encrypted_file_path=str(encrypted_file_path),
            key_blob=key_blob_b64,
            ipfs_cid=new_ipfs_cid or config.vault.ipfs_cid,
        )

        updated_config = replace(config, vault=updated_vault)

        # 8. Save updated configuration
        save_config(updated_config)

        # 9. Provide user feedback
        console.print(f"[bold green]✓ Secret file updated successfully![/bold green]")
        console.print(f"   Original file: {new_secret_path_obj}")
        console.print(f"   Encrypted file: {encrypted_file_path}")
        console.print(f"   File size: {encrypted_file_path.stat().st_size:,} bytes")
        if new_ipfs_cid:
            console.print(f"   IPFS CID: {new_ipfs_cid}")
        elif config.vault.ipfs_cid:
            console.print(f"   IPFS CID: {config.vault.ipfs_cid} (unchanged)")

        console.print(
            "\n[yellow]⚠️  Important: The agent will continue using the new encrypted file.[/yellow]"
        )
        console.print("[yellow]    No restart of the agent is required.[/yellow]")

    except FileNotFoundError:
        console.print("[red]❌ Lazarus not initialized.[/red]")
        console.print("Run: python -m lazarus init")
        return
    except ConfigCorruptedError as e:
        console.print(f"[red]❌ Config file is corrupted: {e}[/red]")
        console.print("Run: python -m lazarus init to recreate configuration")
        return
    except Exception as e:
        console.print(f"[red]❌ Error updating secret: {e}[/red]")
        return


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
