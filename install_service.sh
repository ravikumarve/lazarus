#!/bin/bash
# Lazarus Protocol systemd service installation script

set -e

# Configuration
SERVICE_NAME="lazarus"
SERVICE_FILE="lazarus.service"
USERNAME="$(whoami)"
INSTALL_DIR="$(pwd)"

echo "🧟 Installing Lazarus Protocol systemd service..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Do not run this script as root. Run as the user who will own the service."
    exit 1
fi

# Validate Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Validate working directory
if [ ! -f "run_lazarus.py" ]; then
    echo "❌ run_lazarus.py not found. Run this script from the Lazarus directory."
    exit 1
fi

# Update service file with correct paths
sed -i "s|/home/matrix/Desktop/lazarus|$INSTALL_DIR|g" "$SERVICE_FILE"

# Copy service file to systemd directory
if [ ! -d "~/.config/systemd/user" ]; then
    mkdir -p ~/.config/systemd/user
fi

cp "$SERVICE_FILE" "~/.config/systemd/user/"

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    cp ".env.example" ".env"
    echo "⚠️  Please edit .env file with your actual configuration values"
fi

# Enable and start the service
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"

# Check service status
if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Lazarus service installed and started successfully"
    echo "📋 Service status:"
    systemctl --user status "$SERVICE_NAME" --no-pager
    echo ""
    echo "📝 View logs with: journalctl --user -u $SERVICE_NAME -f"
else
    echo "❌ Service failed to start. Check logs with:"
    echo "   journalctl --user -u $SERVICE_NAME -f"
    exit 1
fi