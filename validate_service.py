#!/usr/bin/env python3
"""
Validate Lazarus systemd service configuration
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_path():
    """Check if Python can import Lazarus modules"""
    try:
        # Add current directory to Python path
        sys.path.insert(0, str(Path.cwd()))

        # Try importing key modules
        from cli.main import cli
        from core.config import load_config

        print("✅ Python path configuration is correct")
        return True
    except ImportError as e:
        print(f"❌ Python import error: {e}")
        return False


def check_env_file():
    """Check if .env file exists and is readable"""
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  .env file does not exist (copy from .env.example)")
        return False

    try:
        env_path.read_text()
        print("✅ .env file exists and is readable")
        return True
    except Exception as e:
        print(f"❌ Cannot read .env file: {e}")
        return False


def check_service_file():
    """Check systemd service file configuration"""
    service_path = Path("lazarus.service")
    if not service_path.exists():
        print("❌ lazarus.service file not found")
        return False

    content = service_path.read_text()

    # Check for required configurations
    checks = [
        ("WorkingDirectory=", "Working directory configured"),
        ("ExecStart=", "ExecStart configured"),
        ("EnvironmentFile=", "Environment file configured"),
        ("Restart=always", "Restart policy configured"),
    ]

    all_good = True
    for check, message in checks:
        if check in content:
            print(f"✅ {message}")
        else:
            print(f"❌ Missing: {message}")
            all_good = False

    return all_good


def check_systemd_available():
    """Check if systemd user services are available"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("✅ systemd user services available")
            return True
        else:
            print("❌ systemd user services not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ systemctl command not available or timed out")
        return False


def main():
    """Run all validation checks"""
    print("🔍 Validating Lazarus systemd service configuration...\n")

    checks = [
        ("Python Path", check_python_path),
        ("Environment File", check_env_file),
        ("Service File", check_service_file),
        ("Systemd Availability", check_systemd_available),
    ]

    results = []
    for name, check_func in checks:
        print(f"{name}:")
        result = check_func()
        results.append(result)
        print()

    # Summary
    if all(results):
        print("🎉 All checks passed! Service should work correctly.")
        print("\n📋 Next steps:")
        print("1. Edit .env file with your actual configuration")
        print("2. Run: systemctl --user daemon-reload")
        print("3. Run: systemctl --user enable lazarus")
        print("4. Run: systemctl --user start lazarus")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
