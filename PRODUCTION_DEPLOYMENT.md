# 🚀 Lazarus Protocol - Production Deployment Guide

## Overview

This guide covers deploying Lazarus Protocol in production environments with security best practices.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- **Python**: 3.10+
- **Memory**: 2GB+ RAM
- **Storage**: 10GB+ free space
- **Network**: Static IP recommended

### Security Requirements
- Firewall configured
- Non-root user setup
- SSL/TLS certificates
- Regular backup strategy

## 🏗️ Deployment Options

### Option 1: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t lazarus .
docker run -d \
  -p 8000:8000 \
  -p 8080:8080 \
  -v lazarus_data:/app/data \
  -v lazarus_config:/app/config \
  -v lazarus_logs:/app/logs \
  --name lazarus \
  lazarus
```

### Option 2: Systemd Service

```bash
# Install systemd service
sudo cp lazarus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lazarus
sudo systemctl start lazarus

# Check status
sudo systemctl status lazarus
```

### Option 3: Manual Installation

```bash
# Create dedicated user
sudo useradd -r -s /bin/false lazarus

# Create directories
sudo mkdir -p /opt/lazarus/{data,config,logs}
sudo chown -R lazarus:lazarus /opt/lazarus

# Install Python dependencies
python -m venv /opt/lazarus/venv
source /opt/lazarus/venv/bin/activate
pip install -r requirements.txt

# Start manually
/opt/lazarus/venv/bin/python -m web.server
```

## 🔒 Security Configuration

### Firewall Setup

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### SSL/TLS Configuration

#### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Set environment variables
export LAZARUS_SSL_CERT_FILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
export LAZARUS_SSL_KEY_FILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

#### Using Self-Signed Certificate (Development)

```bash
# Generate self-signed cert
./ssl/generate-self-signed.sh

# Set environment variables
export LAZARUS_SSL_CERT_FILE=ssl/cert.pem
export LAZARUS_SSL_KEY_FILE=ssl/key.pem
```

### File Permissions

```bash
# Secure configuration directory
chmod 700 ~/.lazarus
chmod 600 ~/.lazarus/config.json

# Secure SSL certificates
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

## 📊 Monitoring & Logging

### Log Management

```bash
# View logs
tail -f /app/logs/lazarus.log

# Log rotation (logrotate)
sudo nano /etc/logrotate.d/lazarus

# Logrotate configuration
/var/log/lazarus/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 640 lazarus lazarus
    sharedscripts
    postrotate
        systemctl reload lazarus > /dev/null 2>/dev/null || true
    endscript
}
```

### Health Monitoring

```bash
# Health check endpoint
curl http://localhost:8000/status

# System monitoring
sudo apt install htop
htop

# Process monitoring
ps aux | grep lazarus
```

## 🔄 Backup Strategy

### Configuration Backup

```bash
# Backup config directory
tar -czf lazarus-backup-$(date +%Y%m%d).tar.gz ~/.lazarus/

# Backup Docker volumes
docker run --rm -v lazarus_data:/data -v $(pwd):/backup \
  alpine tar -czf /backup/lazarus-data-$(date +%Y%m%d).tar.gz /data
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * tar -czf /backups/lazarus-$(date +\%Y\%m\%d).tar.gz ~/.lazarus/

# Or use systemd timer
sudo nano /etc/systemd/system/lazarus-backup.timer

[Unit]
Description=Daily Lazarus backup

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

## 🚨 Incident Response

### Service Recovery

```bash
# Restart service
sudo systemctl restart lazarus

# Check logs
journalctl -u lazarus -f

# Emergency stop
sudo systemctl stop lazarus

# Manual recovery
python -m cli.main status
python -m cli.main ping
```

### Data Recovery

```bash
# Restore from backup
tar -xzf lazarus-backup-20231201.tar.gz -C ~/

# Verify config
python -m cli.main validate
```

## 📈 Performance Tuning

### Resource Limits

```bash
# Systemd resource limits
sudo nano /etc/systemd/system/lazarus.service

[Service]
MemoryMax=2G
CPUQuota=100%
```

### Database Optimization

```bash
# For large deployments, consider:
# - Redis for caching
# - PostgreSQL for persistent storage
# - Monitoring with Prometheus/Grafana
```

## 🌐 Network Configuration

### Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/lazarus
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # SSL redirect
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Load Balancer Setup

```bash
# For high availability
# - Multiple Lazarus instances
# - Load balancer (nginx/haproxy)
# - Database replication
```

## 🔍 Troubleshooting

### Common Issues

```bash
# Port already in use
sudo lsof -i :8000
sudo kill -9 <PID>

# Permission denied
sudo chown -R lazarus:lazarus /opt/lazarus

# Dependency issues
pip install -r requirements.txt --upgrade

# Disk space
df -h
sudo du -sh /opt/lazarus/
```

### Debug Mode

```bash
# Enable debug logging
export LAZARUS_LOG_LEVEL=DEBUG
python -m web.server

# Or via CLI
lazarus --verbose run
```

## 📚 Maintenance

### Regular Tasks

```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Rotate logs
logrotate -f /etc/logrotate.d/lazarus

# Check certificate expiry
openssl x509 -in cert.pem -noout -enddate

# Backup configuration
tar -czf backup-$(date +%Y%m%d).tar.gz ~/.lazarus/
```

### Version Upgrades

```bash
# Backup first!
tar -czf backup-pre-upgrade.tar.gz ~/.lazarus/

# Update code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart lazarus

# Verify
curl http://localhost:8000/status
```

## 🎯 Production Checklist

- [ ] Firewall configured
- [ ] SSL/TLS enabled
- [ ] Non-root user setup
- [ ] Backup strategy implemented
- [ ] Monitoring configured
- [ ] Log rotation enabled
- [ ] Regular update schedule
- [ ] Disaster recovery plan
- [ ] Documentation updated
- [ ] Team training completed

## 📞 Support

### Emergency Contacts
- **System Admin**: [Contact Info]
- **Security Team**: [Contact Info]
- **Development Team**: [Contact Info]

### Escalation Procedures
1. Check service status: `systemctl status lazarus`
2. Check logs: `journalctl -u lazarus`
3. Restart service: `systemctl restart lazarus`
4. Contact on-call engineer
5. Escalate to security team if breach suspected

## 📊 Performance Metrics

### Key Metrics to Monitor
- **Uptime**: Service availability
- **Response Time**: API response latency
- **Memory Usage**: Process memory consumption
- **Disk Space**: Storage utilization
- **Network Traffic**: Bandwidth usage
- **Error Rate**: HTTP error rates

### Alert Thresholds
- **Critical**: >5% error rate, >90% memory usage
- **Warning**: >2% error rate, >80% memory usage
- **Info**: Service restart, configuration changes

---

**Note**: Always test deployment procedures in a staging environment before production deployment.