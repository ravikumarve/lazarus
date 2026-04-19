# Lazarus Protocol Systemd Service Setup

## 🚀 Production-Ready Service Configuration

This document describes the updated systemd service configuration for running Lazarus Protocol as a reliable background service.

### Updated Service File Features

The `lazarus.service` file has been updated with production-grade configuration:

1. **Absolute Paths**: Uses full absolute paths instead of relative paths
2. **Python Path Handling**: Uses the improved `run_lazarus.py` launcher script
3. **Environment Configuration**: Loads environment variables from `.env` file
4. **Proper Logging**: Configures journald logging for systemd integration
5. **Robust Restart**: Exponential backoff restart policy
6. **User Context**: Runs under the appropriate user account

### Installation Steps

#### Method 1: Automated Installation

```bash
# Make the installation script executable
chmod +x install_service.sh

# Run the installation script
./install_service.sh
```

#### Method 2: Manual Installation

```bash
# Copy service file to user systemd directory
cp lazarus.service ~/.config/systemd/user/

# Reload systemd configuration
systemctl --user daemon-reload

# Enable the service to start on boot
systemctl --user enable lazarus

# Start the service immediately
systemctl --user start lazarus
```

### Service Management Commands

```bash
# Check service status
systemctl --user status lazarus

# View service logs
journalctl --user -u lazarus -f

# Restart the service
systemctl --user restart lazarus

# Stop the service
systemctl --user stop lazarus

# Disable automatic startup
systemctl --user disable lazarus
```

### Environment Configuration

The service loads environment variables from `/home/matrix/Desktop/lazarus/.env`. Key variables:

- `SENDGRID_API_KEY`: SendGrid API key for email alerts
- `ALERT_FROM_EMAIL`: Sender email address
- `ALERT_TO_EMAIL`: Recipient email address
- `TELEGRAM_BOT_TOKEN`: Telegram bot token (optional)
- `TELEGRAM_CHAT_ID`: Telegram chat ID (optional)
- `VAULT_PATH`: Path to vault configuration file
- `CHECKIN_INTERVAL_DAYS`: Heartbeat check-in interval

### Logging and Monitoring

- **Logs**: Available via `journalctl --user -u lazarus`
- **Log Rotation**: Handled automatically by systemd/journald
- **Monitoring**: Service status available through systemd

### Troubleshooting

#### Common Issues

1. **Service fails to start**:
   ```bash
   # Check detailed error information
   journalctl --user -u lazarus --since "5 minutes ago"
   ```

2. **Python import errors**:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Verify Python path in `run_lazarus.py`

3. **Environment variables not loading**:
   - Check `.env` file exists and is readable
   - Verify path in `EnvironmentFile=` directive

4. **Permission issues**:
   - Ensure service user has read/write access to Lazarus directory
   - Check vault file permissions

#### Validation Script

Use the validation script to check your configuration:

```bash
python3 validate_service.py
```

### Security Considerations

1. **File Permissions**:
   - `.env` file should be readable only by the service user
   - Vault file should have restrictive permissions

2. **Service Isolation**:
   - Runs under user context, not root
   - Limited system access

3. **Network Security**:
   - Only outbound connections to configured services
   - No inbound ports opened

### Backup and Recovery

1. **Configuration Backup**:
   - Backup `.env` file and vault file regularly
   - Store backups in secure location

2. **Service Recovery**:
   - Systemd automatically restarts failed service
   - Manual intervention only required for configuration issues

### Performance Optimization

- **Memory Usage**: Lightweight Python process
- **CPU Usage**: Minimal overhead (periodic heartbeats only)
- **Disk I/O**: Infrequent vault file updates
- **Network**: Only during check-ins and alert conditions

### Support

For issues with the systemd service:

1. Check service logs: `journalctl --user -u lazarus`
2. Validate configuration: `python3 validate_service.py`
3. Review this documentation for common solutions

---

**Last Updated**: $(date +%Y-%m-%d)
**Service Version**: 2.0.0
**Compatibility**: Systemd 240+ (Ubuntu 18.04+, CentOS 7+, etc.)