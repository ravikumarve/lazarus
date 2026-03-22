#!/usr/bin/env python3
"""
web/server.py — FastAPI server for Lazarus Protocol Dashboard

Run: uvicorn web.server:app --host 0.0.0.0 --port 6666
Access: http://localhost:6666
"""

import os
import sys
from pathlib import Path
from datetime import datetime, UTC

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import (
    load_config,
    save_config,
    record_checkin,
    days_since_checkin,
    days_remaining,
    extend_deadline,
    LAZARUS_DIR,
)

app = FastAPI(title="Lazarus Protocol Dashboard")

EVENTS_LOG = LAZARUS_DIR / "events.log"
DELIVERY_LOG = LAZARUS_DIR / "delivery.log"
PID_FILE = LAZARUS_DIR / "agent.pid"


class PingResponse(BaseModel):
    success: bool
    message: str
    days_remaining: float


class FreezeRequest(BaseModel):
    days: int = 30


class FreezeResponse(BaseModel):
    success: bool
    message: str
    new_days_remaining: float


def get_agent_status() -> dict:
    """Check if agent is running."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if os.path.exists(f"/proc/{pid}"):
                return {"running": True, "pid": pid}
        except (ValueError, IOError):
            pass
    return {"running": False, "pid": None}


def get_events(limit: int = 20) -> list[dict]:
    """Get recent events from events.log."""
    events = []
    if EVENTS_LOG.exists():
        try:
            lines = EVENTS_LOG.read_text().strip().split('\n')
            for line in lines[-limit:]:
                if line:
                    parts = line.split(']', 1)
                    if len(parts) == 2:
                        timestamp = parts[0].strip('[')
                        content = parts[1].strip()
                        events.append({
                            "timestamp": timestamp,
                            "content": content
                        })
        except Exception:
            pass
    return events


def get_deliveries(limit: int = 10) -> list[dict]:
    """Get recent deliveries from delivery.log."""
    deliveries = []
    if DELIVERY_LOG.exists():
        try:
            lines = DELIVERY_LOG.read_text().strip().split('\n')
            for line in lines[-limit:]:
                if line:
                    parts = line.split(']', 1)
                    if len(parts) == 2:
                        timestamp = parts[0].strip('[')
                        content = parts[1].strip()
                        success = "SUCCESS" in content
                        deliveries.append({
                            "timestamp": timestamp,
                            "content": content,
                            "success": success
                        })
        except Exception:
            pass
    return deliveries


@app.get("/")
def root():
    """Serve the dashboard HTML."""
    html_path = Path(__file__).parent / "dashboard.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/status")
def status():
    """Get current Lazarus status."""
    try:
        config = load_config()
        since = days_since_checkin(config)
        remaining = days_remaining(config)
        agent = get_agent_status()
        
        last_ping = None
        if config.last_checkin_timestamp:
            last_ping = datetime.fromtimestamp(
                config.last_checkin_timestamp, tz=UTC
            ).isoformat()
        
        return {
            "initialized": True,
            "armed": config.armed,
            "owner_name": config.owner_name,
            "owner_email": config.owner_email,
            "checkin_interval_days": config.checkin_interval_days,
            "days_since_ping": round(since, 1),
            "days_remaining": round(remaining, 1),
            "last_ping": last_ping,
            "beneficiaries": [
                {"name": b.beneficiary_name}
                for b in config.vault.beneficiaries
            ],
            "beneficiary_count": len(config.vault.beneficiaries),
            "agent": agent,
            "events": get_events(10),
            "deliveries": get_deliveries(5),
        }
    except FileNotFoundError:
        return {"initialized": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ping", response_model=PingResponse)
def ping():
    """Record a check-in."""
    try:
        config = load_config()
        updated = record_checkin(config)
        save_config(updated)
        remaining = days_remaining(updated)
        
        LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] CHECKIN: Owner {config.owner_name} checked in. {remaining:.1f} days remaining.\n")
        
        return PingResponse(
            success=True,
            message=f"Check-in recorded. {remaining:.1f} days until trigger.",
            days_remaining=round(remaining, 1)
        )
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/freeze", response_model=FreezeResponse)
def freeze(request: FreezeRequest):
    """Extend the deadline by N days."""
    try:
        config = load_config()
        updated = extend_deadline(config, request.days)
        save_config(updated)
        remaining = days_remaining(updated)
        
        LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] FREEZE: Owner {config.owner_name} extended deadline by {request.days} days. New days remaining: {remaining:.1f}.\n")
        
        return FreezeResponse(
            success=True,
            message=f"Deadline extended by {request.days} days. {remaining:.1f} days remaining.",
            new_days_remaining=round(remaining, 1)
        )
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
def events_endpoint(limit: int = 50):
    """Get recent events."""
    return {"events": get_events(limit)}


if __name__ == "__main__":
    import uvicorn
    print("⚰️  Starting Lazarus Dashboard on http://localhost:6666")
    uvicorn.run(app, host="0.0.0.0", port=6666)
