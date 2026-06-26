#!/usr/bin/env python3
"""
web/server.py — FastAPI server for Lazarus Protocol Dashboard

Run: uvicorn web.server:app --host 0.0.0.0 --port 5555
Access: http://localhost:5555
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

# Load .env file if present (before any other imports that need it)
_env_path = Path(__file__).parent.parent / '.env'
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass  # dotenv not installed, env must be set manually

from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import threading

import psutil

from core.config import (
    LAZARUS_DIR,
    days_remaining,
    days_since_checkin,
    extend_deadline,
    load_config,
    record_checkin,
    save_config,
)
from core.rate_limiter import get_distributed_rate_limiter
from core.security import (
    get_security_headers,
    key_manager,
    log_security_event,
    sanitize_input,
    security,
    validate_file_size,
    validate_filename,
    validate_safe_path,
    verify_api_key,
)

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

_cleanup_interval = 300  # 5 minutes
_memory_threshold = 1024 * 1024 * 1024  # 1GB
_stop_event = threading.Event()


async def periodic_cleanup():
    """Periodic cleanup task for rate limiter and memory monitoring."""
    while not _stop_event.is_set():
        try:
            # Cleanup rate limiter
            distributed_limiter.cleanup()

            # Check memory usage
            check_memory_usage()

            # Wait for next interval
            await asyncio.sleep(_cleanup_interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log_security_event(
                "CLEANUP_ERROR",
                "system",
                f"Error during periodic cleanup: {str(e)}",
                level=40
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    # ── Startup ─────────────────────────────────────────────────
    cleanup_task = asyncio.create_task(periodic_cleanup())

    log_security_event(
        "SERVER_STARTUP",
        "system",
        "Lazarus Protocol server started",
        level=20
    )

    yield  # ── App runs here ────────────────────────────────────

    # ── Shutdown ─────────────────────────────────────────────────
    _stop_event.set()
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    distributed_limiter.cleanup()
    key_manager.stop()

    log_security_event(
        "SERVER_SHUTDOWN",
        "system",
        "Lazarus Protocol server stopped",
        level=20
    )


app = FastAPI(title="Lazarus Protocol Dashboard", lifespan=lifespan)

# Initialize distributed rate limiter
distributed_limiter = get_distributed_rate_limiter()

# Add security middleware
# Static file extensions that bypass rate limiting
_STATIC_EXTENSIONS = {".css", ".svg", ".ico", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Apply security headers and distributed rate limiting to all requests."""
    # Check distributed rate limit (skip for static files)
    path = request.url.path
    is_static = any(path.endswith(ext) for ext in _STATIC_EXTENSIONS)

    rate_result = None
    if not is_static:
        try:
            ip_address = request.client.host if request.client else "unknown"
            rate_result = distributed_limiter.is_allowed(ip_address)

            if not rate_result.allowed:
                log_security_event(
                    "RATE_LIMIT",
                    ip_address,
                    f"Path: {path}, Reason: {rate_result.reason}",
                    level=30
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": f"Rate limit exceeded. {rate_result.reason}"},
                    headers={"Retry-After": str(rate_result.retry_after)}
                )
        except Exception as e:
            # Log error but allow request if rate limiting fails
            log_security_event(
                "RATE_LIMIT_ERROR",
                request.client.host if request.client else "unknown",
                f"Error: {str(e)}",
                level=40
            )

    # Process request
    response = await call_next(request)

    # Add security headers
    for key, value in get_security_headers().items():
        response.headers[key] = value

    # Add rate limit headers (skip for static files — reuse rate_result from first call)
    if not is_static and rate_result is not None:
        if rate_result.remaining is not None:
            response.headers["X-RateLimit-Limit"] = str(rate_result.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
            if rate_result.reset_at:
                response.headers["X-RateLimit-Reset"] = str(int(rate_result.reset_at.timestamp()))

    return response

# Add CORS middleware (restrictive)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5555", "http://127.0.0.1:5555"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

# ---------------------------------------------------------------------------
# Startup / Shutdown — handled by lifespan() above
# ---------------------------------------------------------------------------


def check_memory_usage():
    """Check memory usage and alert if threshold exceeded."""
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        if memory_mb > _memory_threshold / 1024 / 1024:
            log_security_event(
                "MEMORY_WARNING",
                "system",
                f"Memory usage {memory_mb:.2f}MB exceeds threshold",
                level=30
            )

            # Trigger aggressive cleanup
            aggressive_cleanup()
    except Exception as e:
        log_security_event(
            "MEMORY_CHECK_ERROR",
            "system",
            f"Error checking memory usage: {str(e)}",
            level=40
        )


def aggressive_cleanup():
    """Perform aggressive memory cleanup."""
    try:
        # Force Python garbage collection
        import gc
        gc.collect()

        # Cleanup rate limiter aggressively
        distributed_limiter.cleanup()

        log_security_event(
            "AGGRESSIVE_CLEANUP",
            "system",
            "Aggressive cleanup completed",
            level=20
        )
    except Exception as e:
        log_security_event(
            "AGGRESSIVE_CLEANUP_ERROR",
            "system",
            f"Error during aggressive cleanup: {str(e)}",
            level=40
        )


# ---------------------------------------------------------------------------
# Configuration and Logging
# ---------------------------------------------------------------------------

EVENTS_LOG = LAZARUS_DIR / "events.log"
DELIVERY_LOG = LAZARUS_DIR / "delivery.log"
PID_FILE = LAZARUS_DIR / "agent.pid"


class PingRequest(BaseModel):
    pin: str | None = Field(None, max_length=100, description="Optional PIN for duress mode")


class PingResponse(BaseModel):
    success: bool
    message: str
    days_remaining: float


class FreezeRequest(BaseModel):
    days: int = Field(30, ge=1, le=365, description="Days to extend deadline")


class FreezeResponse(BaseModel):
    success: bool
    message: str
    new_days_remaining: float


class AddDocumentRequest(BaseModel):
    file_path: str = Field(..., max_length=500, description="Path to document file")
    document_type: str | None = Field(None, max_length=50, description="Document type")


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
            lines = EVENTS_LOG.read_text().strip().split("\n")
            for line in lines[-limit:]:
                if line:
                    parts = line.split("]", 1)
                    if len(parts) == 2:
                        timestamp = parts[0].strip("[")
                        content = parts[1].strip()
                        events.append({"timestamp": timestamp, "content": content})
        except Exception:
            pass
    return events


def get_deliveries(limit: int = 10) -> list[dict]:
    """Get recent deliveries from delivery.log."""
    deliveries = []
    if DELIVERY_LOG.exists():
        try:
            lines = DELIVERY_LOG.read_text().strip().split("\n")
            for line in lines[-limit:]:
                if line:
                    parts = line.split("]", 1)
                    if len(parts) == 2:
                        timestamp = parts[0].strip("[")
                        content = parts[1].strip()
                        success = "SUCCESS" in content
                        deliveries.append(
                            {
                                "timestamp": timestamp,
                                "content": content,
                                "success": success,
                            }
                        )
        except Exception:
            pass
    return deliveries


@app.get("/")
@app.get("/dashboard")
def root():
    """Serve the dashboard HTML."""
    html_path = Path(__file__).parent / "dashboard.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/lazarus-logo.svg")
def logo():
    """Serve the Lazarus Protocol SVG logo."""
    svg_path = Path(__file__).parent.parent / "lazarus-logo.svg"
    if svg_path.exists():
        return FileResponse(svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.get("/favicon.ico")
def favicon():
    """Serve favicon.ico (redirect to SVG logo)."""
    svg_path = Path(__file__).parent.parent / "lazarus-logo.svg"
    if svg_path.exists():
        return FileResponse(svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/landing")
def landing():
    """Serve the landing/marketing page (index.html)."""
    html_path = Path(__file__).parent / "index.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/pricing")
def pricing():
    """Serve the pricing HTML page."""
    html_path = Path(__file__).parent / "pricing.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/secure")
@app.get("/dashboard-secure")
def secure_dashboard():
    """Serve the JWT-secured dashboard HTML."""
    html_path = Path(__file__).parent / "dashboard-secure.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/login")
def login_page():
    """Serve the login HTML page."""
    html_path = Path(__file__).parent / "login.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/settings")
def settings_page():
    """Serve the settings HTML page."""
    html_path = Path(__file__).parent / "settings.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/beneficiaries")
def beneficiaries_page():
    """Serve the beneficiaries HTML page."""
    html_path = Path(__file__).parent / "beneficiaries.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/wallets")
def wallets_page():
    """Serve the wallets HTML page."""
    html_path = Path(__file__).parent / "wallets.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/activity")
def activity_page():
    """Serve the activity log HTML page."""
    html_path = Path(__file__).parent / "activity.html"
    return FileResponse(html_path, media_type="text/html")


@app.get("/forgot-password")
def forgot_password():
    """Serve a simple forgot-password placeholder page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lazarus Protocol — Password Reset</title>
    <link rel="icon" type="image/svg+xml" href="/lazarus-logo.svg" />
    <link rel="stylesheet" href="/css/base.css">
    <link rel="stylesheet" href="/css/login.css">
    <script src="https://unpkg.com/lucide@latest" defer></script>
</head>
<body>
    <div class="film-grain"></div>
    <div class="login-container">
        <div class="login-card fade-in">
            <div class="login-header">
                <div class="logo"><img src="/lazarus-logo.svg" alt=""></div>
                <h1>Password Reset</h1>
                <p>Self-hosted instances manage passwords locally</p>
            </div>
            <div class="info">
                Password reset is handled by your local instance administrator.
                Check your server configuration or contact your admin.
            </div>
            <div class="footer" style="margin-top: 20px;">
                <p><a href="/login">Back to Login</a></p>
            </div>
        </div>
    </div>
    <script>document.addEventListener('DOMContentLoaded', () => { lucide.createIcons(); });</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# Static CSS files
CSS_FILES = {
    "base.css": "base.css",
    "dashboard.css": "dashboard.css",
    "pricing.css": "pricing.css",
    "login.css": "login.css",
    "settings.css": "settings.css",
    "beneficiaries.css": "beneficiaries.css",
    "wallets.css": "wallets.css",
    "activity.css": "activity.css",
}


@app.get("/css/{css_name}")
def serve_css(css_name: str):
    """Serve CSS files from web/css directory."""
    if css_name not in CSS_FILES:
        raise HTTPException(status_code=404, detail=f"CSS not found: {css_name}")
    css_path = Path(__file__).parent / "css" / CSS_FILES[css_name]
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail=f"CSS not found: {css_name}")


# Static JS files
JS_FILES = {
    "security.js": "security.js",
}


@app.get("/js/{js_name}")
def serve_js(js_name: str):
    """Serve JS files from web/js directory."""
    if js_name not in JS_FILES:
        raise HTTPException(status_code=404, detail=f"JS not found: {js_name}")
    js_path = Path(__file__).parent / "js" / JS_FILES[js_name]
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail=f"JS not found: {js_name}")


@app.get("/status")
async def get_status(request: Request):
    """Get current Lazarus status. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    try:
        config = load_config()
        since = days_since_checkin(config)
        remaining = days_remaining(config)

        import math

        if math.isinf(since):
            since = None
        if math.isinf(remaining):
            remaining = None
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
            "days_since_ping": round(since, 1) if since is not None else None,
            "days_remaining": round(remaining, 1) if remaining is not None else None,
            "last_ping": last_ping,
            "beneficiaries": [{"name": config.beneficiary.name}],
            "beneficiary_count": 1,
            "agent": agent,
            "events": get_events(10),
            "deliveries": get_deliveries(5),
        }
    except FileNotFoundError:
        return {"initialized": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ping", response_model=PingResponse)
async def ping(request: Request, ping_request: PingRequest = None):
    """Record a check-in. Optional PIN for duress mode. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    try:
        config = load_config()
        pin = ping_request.pin if ping_request else None

        # Sanitize PIN if provided
        if pin:
            pin = sanitize_input(pin, max_length=100)

            from core.duress import is_duress_pin, trigger_duress_alert

            if is_duress_pin(config, pin):
                trigger_duress_alert(config)
                log_security_event(
                    "DURESS_TRIGGER",
                    request.client.host if request.client else "unknown",
                    f"Owner: {config.owner_name}",
                    level=30
                )

        updated = record_checkin(config)
        save_config(updated)
        remaining = days_remaining(updated)

        LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(
                f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] CHECKIN: Owner {config.owner_name} checked in. {remaining:.1f} days remaining.\n"
            )

        return PingResponse(
            success=True,
            message=f"Check-in recorded. {remaining:.1f} days until trigger.",
            days_remaining=round(remaining, 1),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/freeze", response_model=FreezeResponse)
async def freeze(request: Request, freeze_request: FreezeRequest):
    """Extend the deadline by N days. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    try:
        config = load_config()
        updated = extend_deadline(config, freeze_request.days)
        save_config(updated)
        remaining = days_remaining(updated)

        LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(
                f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] FREEZE: Owner {config.owner_name} extended deadline by {freeze_request.days} days. New days remaining: {remaining:.1f}.\n"
            )

        return FreezeResponse(
            success=True,
            message=f"Deadline extended by {freeze_request.days} days. {remaining:.1f} days remaining.",
            new_days_remaining=round(remaining, 1),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
async def events_endpoint(request: Request, limit: int = 50):
    """Get recent events. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    # Validate limit
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")

    return {"events": get_events(limit)}


@app.get("/bundle")
async def get_bundle(request: Request):
    """Get bundle manifest and document list. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    try:
        from core.storage import get_bundle_manifest

        manifest = get_bundle_manifest()
        return {"success": True, "manifest": manifest}
    except FileNotFoundError:
        return {"success": False, "manifest": [], "message": "No bundle found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bundle/add")
async def add_document(request: Request, add_request: AddDocumentRequest):
    """Add a document to the bundle. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    try:
        from core.storage import add_document_to_bundle

        # Sanitize and validate file path
        file_path_str = sanitize_input(add_request.file_path, max_length=500)
        file_path = Path(file_path_str)

        # Validate path is safe
        try:
            safe_path = validate_safe_path(file_path)
        except ValueError as e:
            log_security_event(
                "PATH_TRAVERSAL_ATTEMPT",
                request.client.host if request.client else "unknown",
                f"Path: {file_path_str}",
                level=30
            )
            raise HTTPException(status_code=400, detail=str(e))

        # Validate file size
        try:
            validate_file_size(safe_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Sanitize document type
        doc_type = sanitize_input(add_request.document_type or "OTHER", max_length=50)

        doc_info = add_document_to_bundle(safe_path, doc_type)
        return {"success": True, "document": doc_info}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/bundle/{filename}")
async def remove_document(request: Request, filename: str):
    """Remove a document from the bundle. Requires authentication."""
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    # Validate filename
    if not validate_filename(filename):
        log_security_event(
            "INVALID_FILENAME",
            request.client.host if request.client else "unknown",
            f"Filename: {filename}",
            level=30
        )
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        from core.storage import remove_document_from_bundle

        remove_document_from_bundle(filename)
        return {"success": True, "message": f"Removed {filename}"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Session Key Management Endpoints
# ---------------------------------------------------------------------------

class SessionKeyRequest(BaseModel):
    """Request model for session key generation"""
    session_id: str = Field(..., description="Unique session identifier")
    user_agent: str = Field(default="", description="User agent string")
    device_fingerprint: Optional[str] = Field(None, description="Optional device fingerprint")


class SessionKeyResponse(BaseModel):
    """Response model for session key"""
    key_id: str = Field(..., description="Unique key identifier")
    key: str = Field(..., description="Encryption key (hex encoded)")
    expires_at: str = Field(..., description="Key expiration timestamp (ISO 8601)")


class SettingsUpdate(BaseModel):
    """Request model for updating settings"""
    owner_name: str | None = Field(None, max_length=100)
    owner_email: str | None = Field(None, max_length=200)
    checkin_interval_days: int | None = Field(None, ge=1, le=365)
    telegram_chat_id: str | None = Field(None, max_length=100)
    armed: bool | None = None


class BeneficiaryUpdate(BaseModel):
    """Request model for updating beneficiary"""
    name: str = Field(..., max_length=100, description="Beneficiary name")
    email: str = Field(..., max_length=200, description="Beneficiary email")
    public_key_path: str | None = Field(None, max_length=500, description="Path to RSA public key PEM")


class WalletCreate(BaseModel):
    """Request model for creating/importing a wallet"""
    label: str = Field(..., max_length=100, description="Human-readable label")
    description: str | None = Field(None, max_length=500)
    private_key: str | None = Field(None, max_length=200, description="Import from private key (hex)")


class KeyRotationRequest(BaseModel):
    """Request model for key rotation"""
    key_id: str = Field(..., description="Key ID to rotate")


class KeyRotationResponse(BaseModel):
    """Response model for key rotation"""
    key_id: str = Field(..., description="New key identifier")
    key: str = Field(..., description="New encryption key (hex encoded)")
    expires_at: str = Field(..., description="New key expiration timestamp (ISO 8601)")


@app.post("/api/session/key", response_model=SessionKeyResponse)
async def create_session_key(
    request: Request,
    key_request: SessionKeyRequest
) -> SessionKeyResponse:
    """
    Create a new session-specific encryption key.
    
    This endpoint provides server-generated encryption keys with PBKDF2 derivation,
    addressing the LocalStorage encryption key vulnerability (CVSS 8.9).
    
    Args:
        request: FastAPI request object
        key_request: Session key request with session_id and user_agent

    Returns:
        SessionKeyResponse with key_id, key, and expires_at
    """
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    # Get client information
    user_agent = key_request.user_agent or request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else "unknown"

    # Generate session key
    session_key = key_manager.generate_session_key(
        session_id=key_request.session_id,
        user_agent=user_agent,
        ip_address=ip_address,
        device_fingerprint=key_request.device_fingerprint
    )

    # Log security event
    log_security_event(
        "SESSION_KEY_CREATED",
        ip_address,
        f"Session ID: {key_request.session_id}, Key ID: {session_key.key_id}"
    )

    return SessionKeyResponse(
        key_id=session_key.key_id,
        key=session_key.key,
        expires_at=session_key.expires_at.isoformat()
    )


@app.post("/api/session/key/rotate", response_model=KeyRotationResponse)
async def rotate_session_key(
    request: Request,
    rotation_request: KeyRotationRequest
) -> KeyRotationResponse:
    """
    Rotate an existing session key for enhanced security.
    
    This endpoint implements key rotation to limit the impact of potential key compromises.
    
    Args:
        request: FastAPI request object
        rotation_request: Key rotation request with key_id

    Returns:
        KeyRotationResponse with new key_id, key, and expires_at
    """
    # Verify API key
    credentials = await security(request)
    verify_api_key(credentials)

    # Get client information
    ip_address = request.client.host if request.client else "unknown"

    # Rotate key
    new_session_key = key_manager.rotate_key(rotation_request.key_id)

    if not new_session_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found or already expired"
        )

    # Log security event
    log_security_event(
        "SESSION_KEY_ROTATED",
        ip_address,
        f"Old Key ID: {rotation_request.key_id}, New Key ID: {new_session_key.key_id}"
    )

    return KeyRotationResponse(
        key_id=new_session_key.key_id,
        key=new_session_key.key,
        expires_at=new_session_key.expires_at.isoformat()
    )


@app.get("/api/session/key/validate/{key_id}")
async def validate_session_key(
    request: Request,
    key_id: str
) -> dict:
    """
    Validate a session key and check device binding.
    
    This endpoint validates session keys and ensures device binding is maintained.
    
    Args:
        request: FastAPI request object
        key_id: Key ID to validate

    Returns:
        Dictionary with validation status and key metadata
    """
    # Get client information
    user_agent = request.headers.get("user-agent", "")
    ip_address = request.client.host if request.client else "unknown"

    # Validate session key
    session_key = key_manager.validate_session_key(key_id, user_agent, ip_address)

    if not session_key:
        return {
            "valid": False,
            "reason": "Key not found, expired, or device binding mismatch"
        }

    return {
        "valid": True,
        "key_id": session_key.key_id,
        "expires_at": session_key.expires_at.isoformat(),
        "device_binding": {
            "user_agent_match": session_key.user_agent == user_agent,
            "ip_address": session_key.ip_address
        }
    }


# ---------------------------------------------------------------------------
# Settings API
# ---------------------------------------------------------------------------


@app.get("/api/settings")
async def get_settings(request: Request):
    """Get current protocol settings. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        config = load_config()
        return {
            "owner_name": config.owner_name,
            "owner_email": config.owner_email,
            "checkin_interval_days": config.checkin_interval_days,
            "telegram_chat_id": config.telegram_chat_id or "",
            "armed": config.armed,
            "subscription_tier": config.subscription_tier,
            "wallet_limit": config.wallet_limit,
            "license_key": config.license_key or "",
        }
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/settings")
async def update_settings(request: Request, settings: SettingsUpdate):
    """Update protocol settings. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        config = load_config()
        dirty = False
        if settings.owner_name is not None:
            config.owner_name = sanitize_input(settings.owner_name, 100)
            dirty = True
        if settings.owner_email is not None:
            config.owner_email = sanitize_input(settings.owner_email, 200)
            dirty = True
        if settings.checkin_interval_days is not None:
            config.checkin_interval_days = settings.checkin_interval_days
            dirty = True
        if settings.telegram_chat_id is not None:
            config.telegram_chat_id = sanitize_input(settings.telegram_chat_id, 100) or None
            dirty = True
        if settings.armed is not None:
            config.armed = settings.armed
            dirty = True
        if dirty:
            save_config(config)
            LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
            with open(EVENTS_LOG, "a") as f:
                f.write(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] SETTINGS: Updated by {config.owner_name}.\n")
        return {"success": True, "message": "Settings updated"}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Beneficiaries API
# ---------------------------------------------------------------------------


@app.get("/api/beneficiaries")
async def get_beneficiaries(request: Request):
    """Get list of beneficiaries. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        config = load_config()
        return {
            "beneficiaries": [
                {
                    "id": 1,
                    "name": config.beneficiary.name,
                    "email": config.beneficiary.email,
                    "public_key_path": config.beneficiary.public_key_path,
                }
            ]
        }
    except FileNotFoundError:
        return {"beneficiaries": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/beneficiaries")
async def update_beneficiary(request: Request, ben: BeneficiaryUpdate):
    """Update the primary beneficiary. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        config = load_config()
        from core.config import BeneficiaryConfig
        config.beneficiary = BeneficiaryConfig(
            name=sanitize_input(ben.name, 100),
            email=sanitize_input(ben.email, 200),
            public_key_path=ben.public_key_path or config.beneficiary.public_key_path,
        )
        save_config(config)
        LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] BENEFICIARY: Updated by {config.owner_name}.\n")
        return {"success": True, "message": "Beneficiary updated"}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Lazarus not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Wallets API
# ---------------------------------------------------------------------------


def _get_blockchain_manager():
    """Get or create blockchain manager instance."""
    from core.blockchain import BlockchainManager
    return BlockchainManager()


@app.get("/api/wallets")
async def list_wallets(request: Request):
    """List all crypto wallets. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        bm = _get_blockchain_manager()
        wallets = []
        for w in bm.list_wallets():
            wallets.append({
                "address": w.address,
                "network": w.network,
                "wallet_type": w.wallet_type.value if hasattr(w.wallet_type, 'value') else str(w.wallet_type),
                "label": w.label,
                "description": w.description,
                "balance": str(w.balance) if w.balance else "0",
                "last_sync": w.last_sync.isoformat() if w.last_sync else None,
            })
        return {"wallets": wallets}
    except ImportError:
        return {"wallets": [], "message": "Web3 library not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wallets")
async def create_wallet(request: Request, wallet_data: WalletCreate):
    """Create or import a wallet. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        bm = _get_blockchain_manager()
        label = sanitize_input(wallet_data.label, 100)
        description = sanitize_input(wallet_data.description or "", 500)
        if wallet_data.private_key:
            w = bm.import_wallet(wallet_data.private_key, label, description)
        else:
            w = bm.create_wallet(label, description)
        LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_LOG, "a") as f:
            f.write(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] WALLET: {'Imported' if wallet_data.private_key else 'Created'} {w.label} ({w.address[:10]}...).\n")
        return {
            "success": True,
            "wallet": {
                "address": w.address,
                "label": w.label,
                "network": w.network,
                "wallet_type": w.wallet_type.value if hasattr(w.wallet_type, 'value') else str(w.wallet_type),
            }
        }
    except ImportError:
        raise HTTPException(status_code=400, detail="Web3 library not available — cannot manage wallets")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/wallets/{address}")
async def delete_wallet(request: Request, address: str):
    """Delete a wallet. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        bm = _get_blockchain_manager()
        from core.blockchain import WalletConfig
        # Find and remove wallet by address
        for w in bm.list_wallets():
            if w.address == address:
                bm._wallets.pop(address, None)
                LAZARUS_DIR.mkdir(parents=True, exist_ok=True)
                with open(EVENTS_LOG, "a") as f:
                    f.write(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}] WALLET: Removed {w.label} ({address[:10]}...).\n")
                return {"success": True, "message": f"Wallet {w.label} removed"}
        raise HTTPException(status_code=404, detail="Wallet not found")
    except ImportError:
        raise HTTPException(status_code=400, detail="Web3 library not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/wallets/balances")
async def wallet_balances(request: Request):
    """Get balances for all wallets. Requires authentication."""
    credentials = await security(request)
    verify_api_key(credentials)
    try:
        bm = _get_blockchain_manager()
        balances = []
        for w in bm.list_wallets():
            try:
                bal = bm.get_balance(w.address)
            except Exception:
                bal = None
            balances.append({
                "address": w.address,
                "label": w.label,
                "balance": str(bal) if bal else "unknown",
            })
        return {"balances": balances}
    except ImportError:
        return {"balances": [], "message": "Web3 library not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Settings helper — update_config uses lazarus_dir / export logic
# ---------------------------------------------------------------------------


@app.get("/{full_path:path}")
def catch_all(full_path: str):
    """Catch-all route to handle undefined URLs and redirect to dashboard."""
    # Special case: dashboard.html should redirect to dashboard
    if full_path == "dashboard.html":
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/")

    # If it looks like a file request (has extension), return 404
    if "." in full_path and len(full_path.split(".")[-1]) <= 5:
        raise HTTPException(status_code=404, detail=f"Not found: {full_path}")

    # Otherwise redirect to dashboard
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/")


if __name__ == "__main__":
    import os
    from pathlib import Path

    import uvicorn

    # Get configuration from environment variables
    port = int(os.environ.get("LAZARUS_PORT", 5555))
    host = os.environ.get("LAZARUS_HOST", "0.0.0.0")
    ssl_cert_file = os.environ.get("LAZARUS_SSL_CERT_FILE")
    ssl_key_file = os.environ.get("LAZARUS_SSL_KEY_FILE")

    # Configure SSL if cert and key are provided
    ssl_config = {}
    if ssl_cert_file and ssl_key_file:
        if Path(ssl_cert_file).exists() and Path(ssl_key_file).exists():
            ssl_config = {
                "ssl_certfile": ssl_cert_file,
                "ssl_keyfile": ssl_key_file,
            }
            print(f"🔒 SSL/TLS enabled with certificate: {ssl_cert_file}")
            protocol = "https"
        else:
            print(f"⚠️  SSL files not found: cert={ssl_cert_file}, key={ssl_key_file}")
            print("⚠️  Falling back to HTTP")
            protocol = "http"
    else:
        protocol = "http"

    print(f"⚰️  Starting Lazarus Dashboard on {protocol}://{host}:{port}")
    print("   - Change port: export LAZARUS_PORT=8000")
    print("   - Change host: export LAZARUS_HOST=127.0.0.1")
    if not ssl_config:
        print("   - Enable HTTPS: export LAZARUS_SSL_CERT_FILE=/path/to/cert.pem")
        print("   - Enable HTTPS: export LAZARUS_SSL_KEY_FILE=/path/to/key.pem")
    print(f"   - Access dashboard: {protocol}://{host}:{port}")

    uvicorn.run(app, host=host, port=port, **ssl_config)
