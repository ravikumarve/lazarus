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
import click
from rich.console import Console

from core.config import load_config, save_config, record_checkin, days_remaining
from core.config import ConfigCorruptedError

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
    except ImportError:
        console.print("[red]Setup wizard dependencies not installed[/red]")
        console.print("Run: pip install questionary")
        raise


# ---------------------------------------------------------------------------
# lazarus ping
# ---------------------------------------------------------------------------


@cli.command()
def ping():
    """
    Manual check-in — resets the countdown timer.

    Loads the current config, records a check-in with the current timestamp,
    saves the updated config, and displays the days remaining until trigger.
    """
    try:
        config = load_config()
        config = record_checkin(config)
        save_config(config)

        remaining = days_remaining(config)

        if math.isinf(remaining):
            console.print("[green]✔ Check-in recorded.[/green]")
            console.print(
                "[yellow]⚠  No previous check-in found. Starting timer now.[/yellow]"
            )
        elif remaining > 0:
            console.print(
                f"[green]✔ Check-in recorded. {remaining:.1f} days remaining.[/green]"
            )
        else:
            console.print(
                f"[red]⚠  Check-in recorded but trigger is overdue by {-remaining:.1f} days.[/red]"
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
# lazarus status
# ---------------------------------------------------------------------------


@cli.command()
def status():
    """
    Show vault status: armed state, days remaining, last check-in.

    TODO:
        1. Load config
        2. Display table with Rich
    """
    console.print("[bold]Lazarus Status[/bold]")
    # TODO: implement
    raise NotImplementedError


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

    TODO: delegate to agent/heartbeat.py::start_agent()
    """
    console.print("[green]Agent starting...[/green]")
    # TODO: from lazarus.agent.heartbeat import start_agent; start_agent()
    raise NotImplementedError


@agent.command("stop")
def agent_stop():
    """
    Stop the background heartbeat agent.

    TODO: delegate to agent/heartbeat.py::stop_agent()
    """
    console.print("[yellow]Agent stopping...[/yellow]")
    # TODO: implement
    raise NotImplementedError


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
