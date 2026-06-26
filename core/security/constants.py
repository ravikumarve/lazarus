"""
Security constants and configuration values.
"""

from pathlib import Path

API_KEY_ENV = "LAZARUS_API_KEY"
API_KEY_MIN_LENGTH = 32
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # seconds
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_PATHS = [
    Path.home() / ".lazarus",
    Path.cwd(),
]

# Key management constants
ENCRYPTION_SALT_ENV = "LAZARUS_ENCRYPTION_SALT"
PBKDF2_ITERATIONS = 100000
SESSION_KEY_EXPIRY = 3600  # 1 hour
KEY_ROTATION_INTERVAL = 86400  # 24 hours
DEVICE_BINDING_WINDOW = 2592000  # 30 days
