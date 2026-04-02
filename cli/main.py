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
from rich.console import Console
from rich.table import Table
from rich import box

from core.config import load_config, save_config, record_checkin, days_remaining
from core.config import ConfigCorruptedError, days_since_checkin, is_trigger_due

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
    except ConfigCorruptedError as e:
        console.print(f"[red]❌ Config file is corrupted: {e}[/red]")
        console.print("Run: python -m lazarus init to recreate configuration")
        return
    except Exception as e:
        console.print(f"[red]❌ Error recording check-in: {e}[/red]")
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

    TODO:
        1. Load config
        2. Add 'days' to last_checkin_timestamp equivalent
        3. Save config + print confirmation
    """
    console.print(f"[bold cyan]🧊 Deadline extended by {days} days.[/bold cyan]")
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# lazarus test-trigger
# ---------------------------------------------------------------------------


@cli.command("test-trigger")
def test_trigger():
    """
    Dry run — simulate delivery without actually sending anything.

    TODO:
        1. Load config
        2. Build the delivery payload
        3. Print what would be sent, to whom, and how
        4. Do NOT call the real send functions
    """
    console.print("[bold magenta]🔬 Test trigger (dry run)[/bold magenta]")
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# lazarus update-secret
# ---------------------------------------------------------------------------


@cli.command("update-secret")
@click.argument("new_secret_path", type=click.Path(exists=True))
def update_secret(new_secret_path: str):
    """
    Replace the encrypted secret file with a new one.

    TODO:
        1. Load config
        2. Re-encrypt new file
        3. Update vault + upload to IPFS if configured
        4. Save config
    """
    console.print(f"[green]Updating secret from: {new_secret_path}[/green]")
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
