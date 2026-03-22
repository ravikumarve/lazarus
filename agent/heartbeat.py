"""
agent/heartbeat.py — Daily heartbeat scheduler for Lazarus Protocol.

Runs as a long-lived background process using APScheduler.

Escalation ladder (based on days without a check-in):
    Day 20  → reminder email to owner
    Day 25  → Telegram alert to owner
    Day 28  → final warning email + Telegram  (~48h before trigger)
    Day 30+ → TRIGGER: deliver secrets to beneficiary, disarm

Features:
    - Retry logic: alerts retry 3x with exponential backoff (2s, 4s, 8s)
    - Dead agent detection: resumes interrupted triggers on restart
    - Idempotent trigger: checks delivery.log before re-triggering
    - Event logging: all significant events logged to events.log
    - Delivery receipts: written to delivery.log for audit trail

Run with systemd or screen/tmux. Send SIGTERM or Ctrl-C to shut down.
"""

from __future__ import annotations

import logging
import os
import re
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

LAZARUS_DIR = Path.home() / ".lazarus"
EVENTS_LOG = LAZARUS_DIR / "events.log"
DELIVERY_LOG = LAZARUS_DIR / "delivery.log"
PID_FILE = LAZARUS_DIR / "agent.pid"


def _log_event(event_type: str, message: str) -> None:
    """Log an event to events.log with timestamp."""
    LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(EVENTS_LOG, "a") as f:
        f.write(f"[{timestamp}] {event_type}: {message}\n")


def _log_delivery(beneficiary_name: str, beneficiary_email: str, success: bool, error: str = None) -> None:
    """Log delivery attempt to delivery.log."""
    LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    status = "SUCCESS" if success else "FAILED"
    error_str = f" | Error: {error}" if error else ""
    with open(DELIVERY_LOG, "a") as f:
        f.write(f"[{timestamp}] {status} | Beneficiary: {beneficiary_name} <{beneficiary_email}>{error_str}\n")


def _check_trigger_completed() -> bool:
    """Check if trigger has already successfully completed (idempotency)."""
    if not DELIVERY_LOG.exists():
        return False
    try:
        content = DELIVERY_LOG.read_text()
        return "SUCCESS" in content
    except Exception:
        return False


def _check_trigger_in_progress() -> bool:
    """Check if trigger was started but not completed (dead agent detection)."""
    if not EVENTS_LOG.exists():
        return False
    try:
        content = EVENTS_LOG.read_text()
        trigger_started = "TRIGGER_STARTED" in content
        trigger_completed = "TRIGGER_COMPLETED" in content
        return trigger_started and not trigger_completed
    except Exception:
        return False


def _sanitize_config_for_logging(config) -> dict:
    """Return sanitized config dict for logging (strips key_blob)."""
    return {
        "owner_name": config.owner_name,
        "owner_email": config.owner_email,
        "armed": config.armed,
        "beneficiaries": [b.beneficiary_name for b in config.vault.beneficiaries],
    }


# Module-level imports for mocking in tests
from core.config import (
    load_config, save_config, config_exists,
    days_since_checkin, days_remaining, is_trigger_due,
    disarm, get_beneficiary_key_blob, LAZARUS_DIR as CONFIG_DIR,
    CONFIG_PATH,
)
from agent.alerts import (
    send_reminder_email, send_telegram_alert, send_final_warning,
    send_delivery_email, email_configured, telegram_configured, AlertError,
)


REMINDER_DAY   = 20
TELEGRAM_DAY   = 25
FINAL_WARN_DAY = 28
HEARTBEAT_INTERVAL_HOURS = 1
WATCHDOG_INTERVAL_HOURS = 6

_scheduler = None
_agent_config_path: Optional[Path] = None


def _write_pid_file() -> None:
    """Write PID file with secure permissions."""
    LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    if os.name == "posix":
        os.chmod(PID_FILE, 0o600)


def _remove_pid_file() -> None:
    """Remove PID file on shutdown."""
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Could not remove PID file: %s", exc)


@dataclass
class _AlertState:
    """Tracks which alerts have been sent for current countdown window."""
    reminder_sent:    bool = False
    telegram_sent:    bool = False
    final_warn_sent:  bool = False
    triggered:        bool = False


_alert_state = _AlertState()


def start_agent(config_path: Optional[Path] = None) -> None:
    """Start the APScheduler background scheduler and block until interrupted."""
    global _scheduler, _agent_config_path

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError as exc:
        logger.error("APScheduler not installed. Run: pip install APScheduler")
        raise

    check_path = Path(config_path) if config_path else CONFIG_PATH
    _agent_config_path = check_path

    if not config_exists(check_path):
        logger.error("Lazarus not initialised. Run: python -m lazarus init")
        sys.exit(1)

    _log_event("AGENT_START", f"Agent starting with config: {check_path}")
    logger.info("Lazarus heartbeat agent starting...")
    _write_pid_file()

    if _check_trigger_completed():
        logger.warning("Trigger already completed. Agent standing down.")
        _log_event("AGENT_STANDDOWN", "Trigger already completed, skipping.")
        sys.exit(0)

    if _check_trigger_in_progress():
        logger.warning("Previous trigger was interrupted. Resuming delivery...")
        _log_event("TRIGGER_RESUME", "Resuming interrupted trigger...")
        trigger_delivery(config_path=check_path, is_resume=True)

    _scheduler = BlockingScheduler(timezone="UTC")

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

    _scheduler.add_job(
        func=lambda: heartbeat_job(config_path=check_path),
        trigger="date",
        id="heartbeat_boot",
        name="Lazarus boot check",
    )

    signal.signal(signal.SIGTERM, _sigterm_handler)

    logger.info("Agent armed. Heartbeat every %dh.", HEARTBEAT_INTERVAL_HOURS)

    try:
        _scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agent shutting down.")
        stop_agent()


def stop_agent() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
    _scheduler = None
    _remove_pid_file()


def _sigterm_handler(signum, frame):
    logger.info("Received SIGTERM — shutting down.")
    _log_event("AGENT_SHUTDOWN", "Agent received SIGTERM")
    stop_agent()
    sys.exit(0)


def heartbeat_job(config_path: Optional[Path] = None) -> None:
    """Main recurring job — runs every hour."""
    global _alert_state

    check_path = Path(config_path) if config_path else CONFIG_PATH

    try:
        config = load_config(config_path=check_path)
    except FileNotFoundError:
        logger.error("Config not found.")
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
        "Heartbeat | days elapsed: %.1f | days remaining: %.1f | armed: %s",
        since, remaining, config.armed,
    )

    if since < REMINDER_DAY:
        _alert_state.reminder_sent = False
    if since < TELEGRAM_DAY:
        _alert_state.telegram_sent = False
    if since < FINAL_WARN_DAY:
        _alert_state.final_warn_sent = False

    if is_trigger_due(config):
        if not _alert_state.triggered:
            logger.critical("TRIGGER: Firing.")
            _log_event("TRIGGER_CHECK", f"Trigger due: {since:.1f} days elapsed")
            trigger_delivery(config_path=check_path)
            _alert_state.triggered = True
        else:
            logger.warning("Trigger already fired.")
        return

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
    """Call alert function, logging but not re-raising on failure."""
    try:
        fn()
    except AlertError as exc:
        logger.error("Alert '%s' failed: %s", label, exc)
    except Exception as exc:
        logger.error("Unexpected error in alert '%s': %s", label, exc)


def trigger_delivery(config_path: Optional[Path] = None, is_resume: bool = False) -> None:
    """
    Fire the dead man's switch with idempotency and delivery logging.
    
    Args:
        config_path: Path to config file.
        is_resume: True if resuming an interrupted trigger.
    """
    check_path = Path(config_path) if config_path else CONFIG_PATH

    try:
        config = load_config(config_path=check_path)
    except Exception as exc:
        logger.critical("TRIGGER FAILED: cannot load config: %s", exc)
        _log_event("TRIGGER_FAILED", f"Cannot load config: {exc}")
        raise

    if not config.armed:
        logger.warning("Switch is already disarmed — skipping.")
        return

    _log_event("TRIGGER_STARTED", f"Trigger fired for {config.owner_name}")
    logger.critical("=" * 60)
    logger.critical("LAZARUS TRIGGER FIRED at %s UTC", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
    safe_config = _sanitize_config_for_logging(config)
    logger.critical("Config: %s", safe_config)
    logger.critical("=" * 60)

    delivery_success = False
    delivery_error: str | None = None

    try:
        if not email_configured():
            logger.critical("CRITICAL: email not configured!")
            delivery_error = "email not configured"
        else:
            for beneficiary in config.vault.beneficiaries:
                key_blob = beneficiary.key_blob
                try:
                    send_delivery_email(
                        beneficiary_name=beneficiary.beneficiary_name,
                        beneficiary_email=config.beneficiary.email,
                        owner_name=config.owner_name,
                        encrypted_file_path=Path(config.vault.encrypted_file_path),
                        key_blob_b64=key_blob,
                        ipfs_cid=config.vault.ipfs_cid,
                    )
                    _log_delivery(
                        beneficiary.beneficiary_name,
                        config.beneficiary.email,
                        success=True,
                    )
                    logger.critical("Delivery sent to %s.", beneficiary.beneficiary_name)
                except Exception as exc:
                    error_msg = str(exc)
                    _log_delivery(
                        beneficiary.beneficiary_name,
                        config.beneficiary.email,
                        success=False,
                        error=error_msg,
                    )
                    logger.critical("Delivery FAILED to %s: %s", beneficiary.beneficiary_name, exc)
                    delivery_error = error_msg

            delivery_success = True

    except Exception as exc:
        logger.critical("DELIVERY EXCEPTION: %s", exc)
        delivery_error = str(exc)
    finally:
        updated = disarm(config)
        save_config(updated, config_path=check_path)
        _log_event("TRIGGER_COMPLETED", f"Trigger completed. Success: {delivery_success}")

        if delivery_success:
            logger.critical("Switch disarmed. Vault delivery complete.")
        else:
            logger.critical("Switch disarmed with delivery error: %s", delivery_error)


def watchdog_job(scheduler=None) -> None:
    """Verify heartbeat job is registered and re-add if missing."""
    if scheduler is None:
        return

    job = scheduler.get_job("heartbeat")
    if job is None:
        logger.error("Watchdog: heartbeat job MISSING — re-registering.")
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
        logger.debug("Watchdog: heartbeat alive. Next: %s", job.next_run_time)
