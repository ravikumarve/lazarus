"""
Input validation utilities: email, path, file size, sanitization, filename safety.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.security.constants import ALLOWED_PATHS, MAX_FILE_SIZE


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not email or len(email) > 254:
        return False
    pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    return bool(re.match(pattern, email))


def validate_safe_path(path: Path, allowed_paths: Optional[list[Path]] = None) -> Path:
    """
    Validate that a path is safe and within allowed directories.

    Args:
        path: Path to validate.
        allowed_paths: List of allowed base paths. Defaults to ALLOWED_PATHS.

    Returns:
        Resolved absolute path.

    Raises:
        ValueError: If path is unsafe or outside allowed directories.
    """
    if allowed_paths is None:
        allowed_paths = ALLOWED_PATHS
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")

    if ".." in str(path):
        raise ValueError("Path traversal detected")

    is_allowed = False
    for allowed in allowed_paths:
        try:
            allowed_resolved = allowed.resolve()
            if resolved == allowed_resolved or str(resolved).startswith(str(allowed_resolved)):
                is_allowed = True
                break
        except (OSError, RuntimeError):
            continue

    if not is_allowed:
        raise ValueError(f"Path not in allowed directories: {resolved}")
    return resolved


def validate_file_size(file_path: Path, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Validate file size is within limits.

    Args:
        file_path: Path to file.
        max_size: Maximum allowed size in bytes.

    Raises:
        ValueError: If file is too large.
    """
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    size = file_path.stat().st_size
    if size > max_size:
        raise ValueError(f"File too large: {size} bytes (max {max_size} bytes)")


def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize user input string.

    Args:
        input_str: Input string to sanitize.
        max_length: Maximum allowed length.

    Returns:
        Sanitized string.

    Raises:
        ValueError: If input is too long.
    """
    if not input_str:
        return ""
    if len(input_str) > max_length:
        raise ValueError(f"Input too long: {len(input_str)} characters (max {max_length})")
    sanitized = input_str.replace("\x00", "")
    sanitized = sanitized.strip()
    return sanitized


def validate_filename(filename: str) -> bool:
    """
    Validate filename is safe.

    Args:
        filename: Filename to validate.

    Returns:
        True if safe, False otherwise.
    """
    if not filename or len(filename) > 255:
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    if "\x00" in filename:
        return False
    if any(ord(c) < 32 for c in filename):
        return False
    safe_pattern = r"^[a-zA-Z0-9._-]+$"
    return bool(re.match(safe_pattern, filename))
