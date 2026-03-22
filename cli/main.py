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
from datetime import datetime, UTC
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

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
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_entry = f"[{timestamp}] {event_type}: {message}"
    event_logger.info(log_entry)


@click.group()
@click.version_option("1.0.0", prog_name="lazarus")
def cli():
    """⚰️  Lazarus Protocol — Self-hosted dead man's switch for crypto holders."""
    pass


@cli.command()
def doctor():
    """Run system diagnostics to verify installation and configuration."""
    import os
    import sys

    console.print("\n[bold cyan]⚰️  Lazarus Protocol — System Diagnostic[/bold cyan]\n")

    all_passed = True

    def check(name: str, condition: bool, warn: bool = False):
        nonlocal all_passed
        if condition:
            console.print(f"  [green]✓[/green] [OK] {name}")
        elif warn:
            console.print(f"  [yellow]⚠[/yellow] [WARN] {name}")
            all_passed = False
        else:
            console.print(f"  [red]✗[/red] [FAIL] {name}")
            all_passed = False

    console.print("[bold]Environment:[/bold]")
    py_version = sys.version_info
    check(f"Python version >= 3.9 (current: {py_version.major}.{py_version.minor})", py_version >= (3, 9))

    console.print("\n[bold]Dependencies:[/bold]")
    deps = [
        ("cryptography", "cryptography"),
        ("APScheduler", "apscheduler"),
        ("click", "click"),
        ("rich", "rich"),
        ("requests", "requests"),
        ("sendgrid", "sendgrid"),
        ("python-telegram-bot", "telegram"),
    ]
    for display, import_name in deps:
        try:
            __import__(import_name)
            check(f"{display}", True)
        except ImportError:
            check(f"{display}", False)

    console.print("\n[bold]Directories:[/bold]")
    check(f"~/.lazarus directory exists", LAZARUS_DIR.exists())
    check(f"~/.lazarus/config.json exists", (LAZARUS_DIR / "config.json").exists())

    console.print("\n[bold]Configuration:[/bold]")
    try:
        config = load_config()
        check("config.json is valid and readable", True)
        check(f"Vault armed: {config.armed}", config.armed, warn=True)
        check(f"Beneficiaries configured: {len(config.vault.beneficiaries)}", len(config.vault.beneficiaries) > 0, warn=True)
        check(f"Encrypted file exists: {config.vault.encrypted_file_path[:30]}...", Path(config.vault.encrypted_file_path).exists(), warn=True)
    except FileNotFoundError:
        check("config.json exists", False)
        check("Lazarus initialized", False)
    except Exception as e:
        check(f"config.json valid: {e}", False)

    console.print("\n[bold]Agent Status:[/bold]")
    PID_FILE = LAZARUS_DIR / "agent.pid"
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if os.path.exists(f"/proc/{pid}"):
                check(f"Agent running (PID: {pid})", True)
            else:
                check(f"Agent PID file exists but process not running", False, warn=True)
        except (ValueError, IOError):
            check("Agent PID file readable", False)
    else:
        check("Agent running", False, warn=True)

    console.print("\n[bold]Environment Variables:[/bold]")
    check("SMTP_HOST set", bool(os.getenv("SMTP_HOST")), warn=True)
    check("SMTP_USER set", bool(os.getenv("SMTP_USER")), warn=True)
    check("SMTP_PASS set", bool(os.getenv("SMTP_PASS")), warn=True)
    check("TELEGRAM_BOT_TOKEN set", bool(os.getenv("TELEGRAM_BOT_TOKEN")), warn=True)

    console.print("\n")
    if all_passed:
        console.print("[bold green]✓ All checks passed![/bold green]")
    else:
        console.print("[yellow]⚠ Some checks failed or require attention.[/yellow]")
        console.print("[dim]Run 'lazarus init' to set up, or 'lazarus status' for details.[/dim]")
    console.print()


@cli.command()
def init():
    """Setup wizard — create and arm your vault."""
    from cli.setup import run_setup_wizard
    run_setup_wizard()


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
    import os
    from datetime import datetime, timedelta, UTC

    try:
        config = load_config()
        since = days_since_checkin(config)
        remaining = days_remaining(config)
        vault_size = get_vault_size(config)

        PID_FILE = LAZARUS_DIR / "agent.pid"
        agent_running = False
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                if os.path.exists(f"/proc/{pid}"):
                    agent_running = True
            except (ValueError, IOError):
                pass

        since_color = "green" if since < 10 else "yellow" if since < 20 else "red"
        remaining_color = "green" if remaining > 10 else "yellow" if remaining >= 3 else "red"
        armed_color = "green" if config.armed else "red"
        agent_color = "green" if agent_running else "red"

        last_ping = "Never"
        if config.last_checkin_timestamp:
            ping_dt = datetime.fromtimestamp(config.last_checkin_timestamp, tz=UTC)
            last_ping = ping_dt.strftime("%Y-%m-%d %H:%M UTC")

        next_trigger = "N/A"
        if remaining > 0:
            trigger_dt = datetime.now(UTC) + timedelta(days=remaining)
            next_trigger = trigger_dt.strftime("%Y-%m-%d")

        main_table = Table(show_header=False, box=None, padding=(0, 2))
        main_table.add_column(style="bold", width=20)
        main_table.add_column(width=40)

        main_table.add_row(
            "[bold]⚰️ Status[/bold]",
            f"[{armed_color}]{'🟢 ARMED' if config.armed else '🔴 DISARMED'}[/{armed_color}]"
        )
        main_table.add_row(
            "[bold]⏰ Agent[/bold]",
            f"[{agent_color}]{'● RUNNING' if agent_running else '○ STOPPED'}[/{agent_color}]"
        )

        details_table = Table(show_header=False, box=None, padding=(0, 2))
        details_table.add_column(style="dim", width=22)
        details_table.add_column(width=35)

        details_table.add_row("[dim]Owner[/dim]", config.owner_name)
        details_table.add_row("[dim]Email[/dim]", config.owner_email)
        details_table.add_row("[dim]Check-in Interval[/dim]", f"{config.checkin_interval_days} days")
        details_table.add_row(
            "[dim]Days Since Ping[/dim]",
            f"[{since_color}]{since:.1f} days[/{since_color}]"
        )
        details_table.add_row(
            "[dim]Days Until Trigger[/dim]",
            f"[{remaining_color}]{remaining:.1f} days[/{remaining_color}]"
        )
        details_table.add_row("[dim]Next Trigger Date[/dim]", f"[yellow]{next_trigger}[/yellow]")
        details_table.add_row("[dim]Last Ping[/dim]", f"[dim]{last_ping}[/dim]")

        vault_table = Table(show_header=False, box=None, padding=(0, 2))
        vault_table.add_column(style="dim", width=22)
        vault_table.add_column(width=35)

        vault_table.add_row("[dim]Beneficiaries[/dim]", str(len(config.vault.beneficiaries)))
        vault_table.add_row("[dim]Vault Size[/dim]", _format_size(vault_size))
        vault_table.add_row("[dim]Encrypted File[/dim]", Path(config.vault.encrypted_file_path).name)

        console.print()
        console.print(Panel(
            main_table,
            title="[bold]⚰️ Lazarus Protocol[/bold]",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print()

        console.print(Panel(
            details_table,
            title="[bold cyan]📊 Details[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print()

        console.print(Panel(
            vault_table,
            title="[bold cyan]🔐 Vault[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print()

        console.print("[bold cyan]👥 Beneficiaries:[/bold cyan]")
        for i, b in enumerate(config.vault.beneficiaries, 1):
            console.print(f"  {i}. {b.beneficiary_name}")
        console.print()

    except FileNotFoundError:
        console.print("\n[bold red]⚠️  Lazarus not initialized[/bold red]")
        console.print("[dim]Run: python -m lazarus init[/dim]\n")
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
    """Start the background heartbeat agent via systemd."""
    import shutil
    import subprocess
    import os

    if shutil.which("systemctl") is None:
        console.print("[red]systemd not found. Please install and configure the agent manually.[/red]")
        console.print("See: https://github.com/ravikumarve/lazarus#running-the-agent")
        return

    service_path = Path("/etc/systemd/system/lazarus.service")
    if not service_path.exists():
        console.print("[yellow]Lazarus systemd service not installed.[/yellow]")
        install = click.confirm("Install the systemd service now?", default=True)
        if not install:
            console.print("[yellow]Cannot start agent without systemd service.[/yellow]")
            return

        src_service = Path(__file__).parent.parent / "lazarus.service"
        if not src_service.exists():
            console.print("[red]lazarus.service not found in package.[/red]")
            return

        try:
            with open(src_service) as f:
                content = f.read()

            content = content.replace("YOUR_USERNAME", os.environ.get("USER", "root"))
            content = content.replace("/home/YOUR_USERNAME/lazarus", str(Path(__file__).parent.parent.parent))
            venv_python = shutil.which("python") or shutil.which("python3") or ""
            content = content.replace(
                "/home/YOUR_USERNAME/lazarus/venv/bin/python",
                venv_python
            )

            with open("/etc/systemd/system/lazarus.service", "w") as f:
                f.write(content)

            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            console.print("[green]Systemd service installed.[/green]")
        except PermissionError:
            console.print("[red]Permission denied. Run: sudo lazarus agent start[/red]")
            return
        except Exception as e:
            console.print(f"[red]Failed to install service: {e}[/red]")
            return

    try:
        subprocess.run(["sudo", "systemctl", "enable", "lazarus.service"], check=True, capture_output=True)
        result = subprocess.run(["sudo", "systemctl", "start", "lazarus.service"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✔ Agent started successfully.[/green]")
            _log_event("AGENT", "Heartbeat agent started via systemd")
        else:
            console.print(f"[red]Failed to start agent: {result.stderr}[/red]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]systemctl error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@agent.command("stop")
def agent_stop():
    """Stop the background heartbeat agent via systemd."""
    import shutil
    import subprocess

    if shutil.which("systemctl") is None:
        console.print("[red]systemd not found.[/red]")
        return

    try:
        result = subprocess.run(["sudo", "systemctl", "stop", "lazarus.service"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✔ Agent stopped.[/green]")
            _log_event("AGENT", "Heartbeat agent stopped via systemd")
        else:
            console.print(f"[red]Failed to stop agent: {result.stderr}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@agent.command("status")
def agent_status():
    """Show agent health status: running/stopped, PID, last heartbeat, next check."""
    from datetime import datetime

    PID_FILE = LAZARUS_DIR / "agent.pid"
    EVENTS_LOG = LAZARUS_DIR / "events.log"
    DELIVERY_LOG = LAZARUS_DIR / "delivery.log"

    table = Table(title="Lazarus Agent Health Status", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value", style="white")

    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            import os
            if os.path.exists(f"/proc/{pid}"):
                status = "[green]RUNNING[/green]"
                status_value = f"RUNNING (PID: {pid})"
            else:
                status = "[yellow]STOPPED (stale PID file)[/yellow]"
                status_value = f"STOPPED (stale PID: {pid})"
        except (ValueError, IOError):
            status = "[yellow]STOPPED[/yellow]"
            status_value = "STOPPED"
    else:
        status = "[yellow]STOPPED[/yellow]"
        status_value = "STOPPED"

    table.add_row("Agent Status", status)

    if EVENTS_LOG.exists():
        try:
            lines = EVENTS_LOG.read_text().strip().split('\n')
            if lines:
                last_event = lines[-1]
                table.add_row("Last Event", last_event[:100])
        except IOError:
            pass

    if DELIVERY_LOG.exists():
        try:
            delivery_lines = DELIVERY_LOG.read_text().strip().split('\n')
            if delivery_lines:
                last_delivery = delivery_lines[-1]
                if "SUCCESS" in last_delivery:
                    table.add_row("Last Delivery", "[green]SUCCESS[/green]")
                else:
                    table.add_row("Last Delivery", "[red]FAILED[/red]")
        except IOError:
            pass

    try:
        config = load_config()
        since = days_since_checkin(config)
        remaining = days_remaining(config)
        table.add_row("Days Since Checkin", f"{since:.1f}")
        table.add_row("Days Until Trigger", f"{remaining:.1f}")
    except FileNotFoundError:
        table.add_row("Config", "[yellow]Not initialized[/yellow]")
    except Exception:
        pass

    console.print(table)


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
    from core.encryption import load_public_key_from_file, encrypt_for_multiple_beneficiaries
    from pathlib import Path
    import os

    console.print("\n[bold magenta]Lazarus Protocol — Test Trigger (Dry Run)[/bold magenta]\n")
    console.print("[yellow]This is a simulation. No emails will be sent.[/yellow]\n")

    try:
        config = load_config()
    except FileNotFoundError:
        console.print("[red]Lazarus not initialized. Run: lazarus init[/red]")
        return

    days_since = days_since_checkin(config)
    days_rem = days_remaining(config)

    console.print(f"[cyan]Owner:[/cyan] {config.owner_name}")
    console.print(f"[cyan]Email:[/cyan] {config.owner_email}")
    console.print(f"[cyan]Days since check-in:[/cyan] {days_since:.1f}")
    console.print(f"[cyan]Days remaining:[/cyan] {days_rem:.1f}")
    console.print()

    if days_rem > 0:
        console.print("[green]✓ Vault is healthy — would NOT trigger delivery[/green]\n")
        console.print("[yellow]To test delivery, run:[/yellow]")
        console.print("[dim]  touch ~/.lazarus/.force_trigger[/dim]")
        console.print("[dim]  lazarus agent check[/dim]\n")
        return

    console.print("[red]⚠ Vault has expired — delivery would be triggered![/red]\n")

    table = Table(title="Beneficiaries (Delivery Targets)", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan")
    table.add_column("Email", style="white")
    table.add_column("Status", style="green")

    for vault in config.vault.beneficiaries:
        beneficiary_config = None
        for b in [config.beneficiary] if hasattr(config, 'beneficiary') else []:
            if hasattr(b, 'name') and b.name == vault.beneficiary_name:
                beneficiary_config = b
                break

        email = getattr(beneficiary_config, 'email', 'unknown') if beneficiary_config else 'unknown'
        table.add_row(vault.beneficiary_name, email, "[yellow]WOULD SEND[/yellow]")

    console.print(table)
    console.print()

    console.print("[bold cyan]Email Content (Simulated):[/bold cyan]\n")
    console.print("[dim]Subject:[/dim] [Lazarus] You have received an inheritance from {}\n".format(config.owner_name))
    console.print("[dim]Attachments:[/dim]")
    console.print("  - encrypted_secrets.bin (vault payload)")
    console.print("  - decryption_kit.zip (decrypt.py + key_blob.txt + INSTRUCTIONS.txt)\n")
    console.print("[yellow]To actually trigger, run: lazarus agent check --force[/yellow]")


@cli.command("update-secret")
@click.argument("new_secret_path", type=click.Path(exists=True))
def update_secret(new_secret_path: str):
    """Replace the encrypted secret file with a new one (re-encrypts for all beneficiaries)."""
    from core.encryption import load_public_key_from_file, encrypt_for_multiple_beneficiaries
    from pathlib import Path
    import os

    new_path = Path(new_secret_path).resolve()
    console.print(f"\n[bold cyan]Lazarus Protocol — Update Secret[/bold cyan]\n")
    console.print(f"[yellow]New secret file:[/yellow] {new_path}\n")

    if not new_path.exists():
        console.print(f"[red]Error: File not found: {new_path}[/red]")
        return

    try:
        config = load_config()
    except FileNotFoundError:
        console.print("[red]Lazarus not initialized. Run: lazarus init[/red]")
        return

    if not new_path.is_file():
        console.print("[red]Error: Not a file.[/red]")
        return

    confirm = click.confirm(
        f"Replace existing vault and re-encrypt for {len(config.vault.beneficiaries)} beneficiary(ies)?",
        default=False
    )
    if not confirm:
        console.print("[yellow]Cancelled.[/yellow]")
        return

    output_dir = Path(config.vault.encrypted_file_path).parent

    try:
        beneficiary_configs = []
        for vault in config.vault.beneficiaries:
            if hasattr(config, 'beneficiary') and config.beneficiary.name == vault.beneficiary_name:
                pub_key = load_public_key_from_file(Path(config.beneficiary.public_key_path))
                beneficiary_configs.append({
                    'name': vault.beneficiary_name,
                    'email': config.beneficiary.email,
                    'public_key_pem': pub_key,
                })

        if not beneficiary_configs:
            console.print("[red]No beneficiary configurations found.[/red]")
            console.print("[yellow]Use 'lazarus add-beneficiary' to add beneficiaries first.[/yellow]")
            return

        all_key_blobs, new_encrypted_path = encrypt_for_multiple_beneficiaries(
            plaintext_path=new_path,
            beneficiaries=beneficiary_configs,
            output_dir=output_dir,
        )

        config.vault.encrypted_file_path = str(new_encrypted_path)
        config.vault.secret_file_path = str(new_path)

        for vault, blob in zip(config.vault.beneficiaries, all_key_blobs):
            vault.key_blob = blob.key_blob

        save_config(config)

        _log_event("SECRET_UPDATED", f"Owner {config.owner_name} updated secret file to: {new_path}")
        console.print(f"[green]✔ Secret updated successfully![/green]\n")
        console.print(f"[cyan]New encrypted file:[/cyan] {new_encrypted_path.name}")
        console.print(f"[cyan]Beneficiaries re-encrypted:[/cyan] {len(all_key_blobs)}")
        console.print(f"\n[yellow]Note: Each beneficiary will receive their updated key_blob upon next delivery.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error updating secret: {e}[/red]")


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
