"""
agent/heartbeat.py — Daily heartbeat scheduler for Lazarus Protocol.

Runs as a long-lived background process using APScheduler.

Escalation ladder (based on days without a check-in):
    Day 20  → reminder email to owner
    Day 25  → Telegram alert to owner
    Day 28  → final warning email + Telegram  (~48h before trigger)
    Day 30+ → TRIGGER: deliver secrets to beneficiary, disarm

The scheduler is designed to be run under systemd or screen/tmux.
`lazarus agent start` blocks the process; use `lazarus agent stop`
(sends SIGTERM) or Ctrl-C to shut down cleanly.

Concurrency model:
    - One APScheduler BackgroundScheduler with two jobs:
        • heartbeat_job  — interval: 1 hour  (checks the countdown every hour
                           so alerts fire on time, not up to 24h late)
        • watchdog_job   — interval: 6 hours (verifies heartbeat_job is still live)
    - A module-level _scheduler variable holds the single instance.
    - All jobs are idempotent: safe to fire multiple times in the same day.

Alert deduplication:
    - _AlertState tracks which alerts have been sent for the current
      elapsed-day window, so the owner doesn't get spammed on every heartbeat.
    - State resets when days_since_checkin drops back below each threshold
      (i.e. after the owner pings in).
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def _sanitize_config_for_logging(config) -> dict:
    """
    Return a sanitized dict of the config for logging.
    Strips key_blob and other sensitive fields to prevent exposure in logs.
    """
    return {
        "owner_name": config.owner_name,
        "owner_email": config.owner_email,
        "armed": config.armed,
        "checkin_interval_days": config.checkin_interval_days,
        "last_checkin_timestamp": config.last_checkin_timestamp,
        "beneficiary": {
            "name": config.beneficiary.name,
            "email": config.beneficiary.email,
        },
        "vault": {
            "encrypted_file_path": str(config.vault.encrypted_file_path),
            "key_blob": "[REDACTED]",
            "ipfs_cid": config.vault.ipfs_cid,
        },
    }


# Module-level imports so unittest.mock.patch() can intercept them in tests
from lazarus.core.config import (
    load_config, save_config, config_exists,
    days_since_checkin, days_remaining, is_trigger_due,
    disarm, CONFIG_PATH,
)
from lazarus.agent.alerts import (
    send_reminder_email, send_telegram_alert, send_final_warning,
    send_delivery_email, email_configured, telegram_configured, AlertError,
)

# Escalation thresholds — days without a check-in
REMINDER_DAY   = 20
TELEGRAM_DAY   = 25
FINAL_WARN_DAY = 28

# Heartbeat fires every hour so alerts are prompt (not up to 24h late)
HEARTBEAT_INTERVAL_HOURS = 1
WATCHDOG_INTERVAL_HOURS  = 6

# Module-level scheduler instance (one per process)
_scheduler = None

# Module-level config path for watchdog recovery
_agent_config_path: Optional[Path] = None

# PID file path — written on start, removed on clean shutdown
PID_FILE = Path.home() / ".lazarus" / "agent.pid"


def _write_pid_file() -> None:
    """Write current process PID to ~/.lazarus/agent.pid."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    # Lock down PID file permissions on POSIX (same as config.py)
    if os.name == "posix":
        os.chmod(PID_FILE, 0o600)
    logger.debug("PID file written: %s (pid=%d)", PID_FILE, os.getpid())


def _remove_pid_file() -> None:
    """Delete the PID file on clean shutdown."""
    try:
        PID_FILE.unlink(missing_ok=True)
        logger.debug("PID file removed.")
    except Exception as exc:
        logger.warning("Could not remove PID file: %s", exc)


# ---------------------------------------------------------------------------
# Alert deduplication state
# ---------------------------------------------------------------------------

@dataclass
class _AlertState:
    """
    Tracks which alerts have already been sent for the current countdown.
    Reset whenever days_since_checkin drops below a threshold (owner pinged in).
    """
    reminder_sent:    bool = False
    telegram_sent:    bool = False
    final_warn_sent:  bool = False
    triggered:        bool = False


_alert_state = _AlertState()


# ---------------------------------------------------------------------------
# Agent lifecycle
# ---------------------------------------------------------------------------

def start_agent(config_path: Optional[Path] = None) -> None:
    """
    Start the APScheduler background scheduler and block until interrupted.

    Args:
        config_path: Override config path (for testing). Uses default if None.

    The agent registers two jobs then blocks, printing status to stdout.
    Send SIGTERM or press Ctrl-C to shut down cleanly.
    """
    global _scheduler, _agent_config_path

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError as exc:
        logger.error("APScheduler not installed. Run: pip install APScheduler")
        raise

    from lazarus.core.config import load_config, config_exists, CONFIG_PATH

    check_path = Path(config_path) if config_path else CONFIG_PATH
    _agent_config_path = check_path  # Store for watchdog recovery

    if not config_exists(check_path):
        logger.error("Lazarus not initialised. Run: python -m lazarus init")
        sys.exit(1)

    logger.info("⚰️  Lazarus heartbeat agent starting...")
    _write_pid_file()

    _scheduler = BlockingScheduler(timezone="UTC")

    # heartbeat every hour
    _scheduler.add_job(
        func=lambda: heartbeat_job(config_path=check_path),
        trigger="interval",
        hours=HEARTBEAT_INTERVAL_HOURS,
        id="heartbeat",
        name="Lazarus heartbeat",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # watchdog every 6 hours
    _scheduler.add_job(
        func=lambda: watchdog_job(scheduler=_scheduler),
        trigger="interval",
        hours=WATCHDOG_INTERVAL_HOURS,
        id="watchdog",
        name="Lazarus watchdog",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Fire heartbeat immediately on startup so we don't wait up to 1h
    _scheduler.add_job(
        func=lambda: heartbeat_job(config_path=check_path),
        trigger="date",           # fire once, right now
        id="heartbeat_boot",
        name="Lazarus boot check",
    )

    # Graceful shutdown on SIGTERM (systemd sends this)
    signal.signal(signal.SIGTERM, _sigterm_handler)

    logger.info("Agent armed. Heartbeat every %dh. Press Ctrl-C to stop.", HEARTBEAT_INTERVAL_HOURS)

    try:
        _scheduler.start()   # blocks until shutdown() is called or KeyboardInterrupt
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agent shutting down.")
        stop_agent()


def stop_agent() -> None:
    """Gracefully shut down the scheduler if it is running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
    _scheduler = None
    _remove_pid_file()


def _sigterm_handler(signum, frame):
    logger.info("Received SIGTERM — shutting down.")
    stop_agent()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Heartbeat job
# ---------------------------------------------------------------------------

def heartbeat_job(config_path: Optional[Path] = None) -> None:
    """
    Main recurring job — runs every hour.

    Logic:
        1. Load config
        2. Skip if disarmed
        3. Calculate days since last check-in
        4. Log current status
        5. Walk the escalation ladder (deduped via _alert_state)
        6. Fire trigger if overdue
    """
    global _alert_state

    check_path = Path(config_path) if config_path else CONFIG_PATH

    try:
        config = load_config(config_path=check_path)
    except FileNotFoundError:
        logger.error("Config not found — agent cannot run without initialisation.")
        return
    except Exception as exc:
        logger.error("Failed to load config: %s", exc)
        return

    if not config.armed:
        logger.info("Switch is disarmed — nothing to do.")
        return

    since     = days_since_checkin(config)
    remaining = days_remaining(config)

    logger.info(
        "Heartbeat ✓ | days elapsed: %.1f | days remaining: %.1f | armed: %s",
        since, remaining, config.armed,
    )

    # Reset dedup state if the owner has recently checked in below each threshold
    if since < REMINDER_DAY:
        _alert_state.reminder_sent   = False
    if since < TELEGRAM_DAY:
        _alert_state.telegram_sent   = False
    if since < FINAL_WARN_DAY:
        _alert_state.final_warn_sent = False

    # --- Trigger check (highest priority) ---
    if is_trigger_due(config):
        if not _alert_state.triggered:
            logger.critical("TRIGGER: days elapsed %.1f >= interval %d. Firing.", since, config.checkin_interval_days)
            trigger_delivery(config_path=check_path)
            _alert_state.triggered = True
        else:
            logger.warning("Trigger already fired and disarmed — no action.")
        return

    # --- Escalation ladder ---
    if since >= FINAL_WARN_DAY and not _alert_state.final_warn_sent:
        logger.warning("Day %.1f: sending final warning.", since)
        _fire_alert(
            lambda: send_final_warning(
                owner_email=config.owner_email,
                days_remaining=remaining,
                chat_id=config.telegram_chat_id,
            ),
            label="final warning",
        )
        _alert_state.final_warn_sent = True

    elif since >= TELEGRAM_DAY and not _alert_state.telegram_sent:
        if config.telegram_chat_id and telegram_configured():
            logger.info("Day %.1f: sending Telegram alert.", since)
            _fire_alert(
                lambda: send_telegram_alert(
                    chat_id=config.telegram_chat_id,
                    days_remaining=remaining,
                ),
                label="Telegram alert",
            )
        _alert_state.telegram_sent = True

    elif since >= REMINDER_DAY and not _alert_state.reminder_sent:
        if email_configured():
            logger.info("Day %.1f: sending reminder email.", since)
            _fire_alert(
                lambda: send_reminder_email(
                    owner_email=config.owner_email,
                    days_remaining=remaining,
                ),
                label="reminder email",
            )
        _alert_state.reminder_sent = True


def _fire_alert(fn, label: str) -> None:
    """Call an alert function, logging but not re-raising on failure."""
    from lazarus.agent.alerts import AlertError
    try:
        fn()
    except AlertError as exc:
        logger.error("Alert '%s' failed: %s", label, exc)
    except Exception as exc:
        logger.error("Unexpected error in alert '%s': %s", label, exc)


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------

def trigger_delivery(config_path: Optional[Path] = None) -> None:
    """
    Fire the dead man's switch.

    Steps:
        1. Load config
        2. Send delivery email to beneficiary (encrypted file + decryption kit)
        3. Send Telegram notification to owner's chat if configured
        4. Disarm and save config (prevents re-triggering)
        5. Log everything with UTC timestamp

    This function is the most critical in the codebase.
    It is designed to be safe to call multiple times (idempotent via armed flag).
    The disarm always runs in finally to prevent re-trigger loops.
    """
    check_path = Path(config_path) if config_path else CONFIG_PATH

    delivery_success = False
    delivery_error: str | None = None

    try:
        config = load_config(config_path=check_path)
    except Exception as exc:
        logger.critical("TRIGGER FAILED: cannot load config: %s", exc)
        raise

    if not config.armed:
        logger.warning("trigger_delivery called but switch is already disarmed — skipping.")
        return

    logger.critical("=" * 60)
    logger.critical("LAZARUS TRIGGER FIRED at %s UTC", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    safe_config = _sanitize_config_for_logging(config)
    logger.critical("Config: %s", safe_config)
    logger.critical("=" * 60)

    try:
        if not email_configured():
            logger.critical("CRITICAL: email not configured — cannot deliver vault!")
            delivery_error = "email not configured"
        else:
            enc_path = Path(config.vault.encrypted_file_path)
            send_delivery_email(
                beneficiary_name=config.beneficiary.name,
                beneficiary_email=config.beneficiary.email,
                owner_name=config.owner_name,
                encrypted_file_path=enc_path,
                key_blob_b64=config.vault.key_blob,
                ipfs_cid=config.vault.ipfs_cid,
            )
            logger.critical("Delivery email sent successfully to %s.", config.beneficiary.email)
            delivery_success = True
    except Exception as exc:
        logger.critical("DELIVERY EMAIL FAILED: %s", exc)
        delivery_error = str(exc)
    finally:
        # Always disarm to prevent re-trigger loops
        updated = disarm(config)
        save_config(updated, config_path=check_path)
        if delivery_success:
            logger.critical("Switch disarmed. Vault delivery complete.")
        else:
            logger.critical("Switch disarmed with delivery error: %s", delivery_error)


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

def watchdog_job(scheduler=None) -> None:
    """
    Runs every 6 hours. Verifies the heartbeat job is still registered
    in the scheduler and re-adds it if missing (e.g. after an unhandled exception).
    """
    if scheduler is None:
        logger.debug("Watchdog: no scheduler reference — skipping.")
        return

    job = scheduler.get_job("heartbeat")
    if job is None:
        logger.error("Watchdog: heartbeat job is MISSING — re-registering.")
        recovery_path = _agent_config_path if _agent_config_path else CONFIG_PATH
        scheduler.add_job(
            func=lambda: heartbeat_job(config_path=recovery_path),
            trigger="interval",
            hours=HEARTBEAT_INTERVAL_HOURS,
            id="heartbeat",
            name="Lazarus heartbeat (recovered)",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    else:
        logger.debug("Watchdog: heartbeat job is alive. Next run: %s", job.next_run_time)
