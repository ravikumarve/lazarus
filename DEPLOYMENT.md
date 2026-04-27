# 🚀 Lazarus Protocol - Deployment Guide

Comprehensive deployment guide for Lazarus Protocol in production environments.

## 📋 Table of Contents

- [Deployment Overview](#deployment-overview)
- [Deployment Options](#deployment-options)
- [System Requirements](#system-requirements)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Docker Deployment](#docker-deployment)
- [Systemd Deployment](#systemd-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Security Hardening](#security-hardening)
- [Performance Tuning](#performance-tuning)
- [Post-Deployment Checklist](#post-deployment-checklist)

---

## 🎯 Deployment Overview

### Deployment Goals

- **Reliability**: 24/7 operation with minimal downtime
- **Security**: Military-grade encryption and secure communications
- **Scalability**: Handle multiple users and vaults
- **Maintainability**: Easy updates and monitoring
- **Recoverability**: Quick recovery from failures

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Deployment Architecture                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Lazarus Protocol (xN)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Instance 1  │  │  Instance 2  │  │  Instance 3  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Local      │  │    IPFS      │  │   Backup     │      │
│  │   Storage    │  │   Storage    │  │   Storage    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Deployment Options

### Option Comparison

| Option | Difficulty | Scalability | Maintenance | Best For |
|--------|-----------|-------------|--------------|----------|
| **Docker** | ⭐⭐ Medium | ⭐⭐⭐ High | ⭐⭐ Easy | Production, containerized environments |
| **Systemd** | ⭐⭐⭐ Hard | ⭐⭐ Medium | ⭐⭐⭐ Hard | Single-server deployments |
| **Kubernetes** | ⭐⭐⭐⭐ Very Hard | ⭐⭐⭐⭐ Very High | ⭐⭐⭐⭐ Very Hard | Large-scale, multi-server deployments |

### Recommendation

**For most users**: Docker deployment
**For advanced users**: Kubernetes deployment
**For simple setups**: Systemd deployment

---

## 💻 System Requirements

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 1 core | 2+ cores |
| **RAM** | 512 MB | 2 GB |
| **Disk** | 10 GB | 50 GB |
| **Network** | 1 Mbps | 100 Mbps |
| **OS** | Linux 3.10+ | Linux 5.0+ |

### Software Requirements

| Software | Version | Notes |
|----------|---------|-------|
| **Python** | 3.10+ | Required for all deployments |
| **Docker** | 20.10+ | For Docker deployment |
| **Docker Compose** | 2.0+ | For Docker deployment |
| **Kubernetes** | 1.20+ | For Kubernetes deployment |
| **Nginx** | 1.18+ | For reverse proxy |

### Network Requirements

| Port | Protocol | Purpose | Required |
|------|----------|---------|----------|
| **8000** | HTTP | Web API | Yes |
| **8080** | HTTP | Web Dashboard | Yes |
| **443** | HTTPS | SSL/TLS | Recommended |
| **5001** | HTTP | IPFS API | Optional |

---

## ✅ Pre-Deployment Checklist

### Planning

- [ ] Define deployment goals and requirements
- [ ] Choose deployment method (Docker/Systemd/Kubernetes)
- [ ] Plan network architecture
- [ ] Define backup strategy
- [ ] Plan monitoring and alerting

### Infrastructure

- [ ] Provision server(s)
- [ ] Configure network settings
- [ ] Set up DNS records
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificates

### Security

- [ ] Create dedicated user account
- [ ] Configure file permissions
- [ ] Set up authentication
- [ ] Configure encryption keys
- [ ] Review security settings

### Testing

- [ ] Test deployment in staging environment
- [ ] Verify all functionality
- [ ] Test backup and recovery
- [ ] Perform load testing
- [ ] Test failover procedures

---

## 🐳 Docker Deployment

### Prerequisites

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Deployment Steps

#### Step 1: Clone Repository

```bash
# Clone repository
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus
```

#### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment file
nano .env
```

**Add to `.env`:**
```bash
# Email Configuration
SENDGRID_API_KEY=your_sendgrid_api_key
ALERT_FROM_EMAIL=lazarus@yourdomain.com
ALERT_TO_EMAIL=your_email@example.com

# Telegram Configuration (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# IPFS Configuration (optional)
IPFS_API_URL=http://127.0.0.1:5001
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_KEY=your_pinata_secret

# SSL/TLS Configuration
LAZARUS_SSL_CERT_FILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
LAZARUS_SSL_KEY_FILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# System Configuration
LAZARUS_HOME=/app/.lazarus
LAZARUS_HOST=0.0.0.0
LAZARUS_PORT=8000
```

#### Step 3: Create Docker Compose File

```yaml
# docker-compose.yml
version: '3.8'

services:
  lazarus:
    image: ghcr.io/ravikumarve/lazarus:latest
    container_name: lazarus
    restart: unless-stopped
    ports:
      - "8000:8000"
      - "8080:8080"
    volumes:
      - lazarus_data:/app/.lazarus
      - ./ssl:/app/ssl:ro
      - ./.env:/app/.env:ro
    environment:
      - LAZARUS_SSL_CERT_FILE=/app/ssl/cert.pem
      - LAZARUS_SSL_KEY_FILE=/app/ssl/key.pem
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - ALERT_FROM_EMAIL=${ALERT_FROM_EMAIL}
      - ALERT_TO_EMAIL=${ALERT_TO_EMAIL}
    networks:
      - lazarus_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: IPFS sidecar
  ipfs:
    image: ipfs/kubo:latest
    container_name: lazarus_ipfs
    restart: unless-stopped
    ports:
      - "5001:5001"
      - "8080:8080"
    volumes:
      - ipfs_data:/data/ipfs
    networks:
      - lazarus_network

volumes:
  lazarus_data:
    driver: local
  ipfs_data:
    driver: local

networks:
  lazarus_network:
    driver: bridge
```

#### Step 4: Deploy

```bash
# Build and start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Step 5: Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Check status
curl http://localhost:8000/api/v1/status

# Access web dashboard
# Open http://localhost:8080 in browser
```

### Docker Management

#### Starting/Stopping

```bash
# Start services
docker-compose start

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# Stop and remove containers
docker-compose down
```

#### Updating

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Or update specific service
docker-compose up -d --no-deps --build lazarus
```

#### Backup

```bash
# Backup volumes
docker run --rm \
  -v lazarus_data:/data \
  -v $(pwd):/backup \
  alpine tar -czf /backup/lazarus-backup-$(date +%Y%m%d).tar.gz /data

# Backup configuration
tar -czf lazarus-config-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

#### Restore

```bash
# Restore volumes
docker run --rm \
  -v lazarus_data:/data \
  -v $(pwd):/backup \
  alpine tar -xzf /backup/lazarus-backup-YYYYMMDD.tar.gz -C /

# Restore configuration
tar -xzf lazarus-config-backup-YYYYMMDD.tar.gz
```

---

## ⚙️ Systemd Deployment

### Prerequisites

```bash
# Install Python 3.10+
sudo apt update
sudo apt install python3.11 python3-pip python3-venv

# Install system dependencies
sudo apt install git build-essential python3-dev
```

### Deployment Steps

#### Step 1: Create Dedicated User

```bash
# Create user
sudo useradd -r -s /bin/false lazarus

# Create directories
sudo mkdir -p /opt/lazarus/{data,logs,ssl}
sudo chown -R lazarus:lazarus /opt/lazarus
```

#### Step 2: Install Lazarus

```bash
# Clone repository
sudo -u lazarus git clone https://github.com/ravikumarve/lazarus.git /opt/lazarus/app
cd /opt/lazarus/app

# Create virtual environment
sudo -u lazarus python3 -m venv /opt/lazarus/venv
source /opt/lazarus/venv/bin/activate

# Install dependencies
pip install -e .[dev]

# Verify installation
lazarus --version
```

#### Step 3: Configure Environment

```bash
# Create environment file
sudo -u lazarus nano /opt/lazarus/.env

# Add environment variables (see Docker section)
```

#### Step 4: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/lazarus.service
```

**Add to service file:**
```ini
[Unit]
Description=Lazarus Protocol Dead Man's Switch
After=network.target

[Service]
Type=simple
User=lazarus
Group=lazarus
WorkingDirectory=/opt/lazarus/app
Environment="PATH=/opt/lazarus/venv/bin"
EnvironmentFile=/opt/lazarus/.env
ExecStart=/opt/lazarus/venv/bin/python -m web.server
Restart=always
RestartSec=10
StandardOutput=append:/opt/lazarus/logs/lazarus.log
StandardError=append:/opt/lazarus/logs/lazarus.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/lazarus/data

[Install]
WantedBy=multi-user.target
```

#### Step 5: Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable lazarus

# Start service
sudo systemctl start lazarus

# Check status
sudo systemctl status lazarus
```

#### Step 6: Verify Deployment

```bash
# Check logs
sudo journalctl -u lazarus -f

# Check health
curl http://localhost:8000/api/v1/health

# Check status
curl http://localhost:8000/api/v1/status
```

### Systemd Management

#### Service Control

```bash
# Start service
sudo systemctl start lazarus

# Stop service
sudo systemctl stop lazarus

# Restart service
sudo systemctl restart lazarus

# Reload service
sudo systemctl reload lazarus

# Check status
sudo systemctl status lazarus
```

#### Log Management

```bash
# View logs
sudo journalctl -u lazarus -f

# View last 100 lines
sudo journalctl -u lazarus -n 100

# View logs since yesterday
sudo journalctl -u lazarus --since yesterday

# View logs with specific priority
sudo journalctl -u lazarus -p err
```

#### Service Configuration

```bash
# Edit service file
sudo systemctl edit lazarus

# View service configuration
sudo systemctl cat lazarus

# Reset service configuration
sudo systemctl revert lazarus
```

---

## ☸️ Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify installation
kubectl version --client
```

### Deployment Steps

#### Step 1: Create Namespace

```bash
# Create namespace
kubectl create namespace lazarus

# Set default namespace
kubectl config set-context --current --namespace=lazarus
```

#### Step 2: Create ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lazarus-config
  namespace: lazarus
data:
  SENDGRID_API_KEY: "your_sendgrid_api_key"
  ALERT_FROM_EMAIL: "lazarus@yourdomain.com"
  ALERT_TO_EMAIL: "your_email@example.com"
  LAZARUS_HOST: "0.0.0.0"
  LAZARUS_PORT: "8000"
```

```bash
# Apply ConfigMap
kubectl apply -f configmap.yaml
```

#### Step 3: Create Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: lazarus-secret
  namespace: lazarus
type: Opaque
stringData:
  TELEGRAM_BOT_TOKEN: "your_telegram_bot_token"
  TELEGRAM_CHAT_ID: "your_chat_id"
```

```bash
# Apply Secret
kubectl apply -f secret.yaml
```

#### Step 4: Create Persistent Volume

```yaml
# pv.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: lazarus-pv
  namespace: lazarus
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /mnt/lazarus-data
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - your-node-name
```

```bash
# Apply PersistentVolume
kubectl apply -f pv.yaml
```

#### Step 5: Create Persistent Volume Claim

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lazarus-pvc
  namespace: lazarus
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: local-storage
```

```bash
# Apply PersistentVolumeClaim
kubectl apply -f pvc.yaml
```

#### Step 6: Create Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lazarus
  namespace: lazarus
  labels:
    app: lazarus
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lazarus
  template:
    metadata:
      labels:
        app: lazarus
    spec:
      containers:
      - name: lazarus
        image: ghcr.io/ravikumarve/lazarus:latest
        ports:
        - containerPort: 8000
        - containerPort: 8080
        env:
        - name: SENDGRID_API_KEY
          valueFrom:
            configMapKeyRef:
              name: lazarus-config
              key: SENDGRID_API_KEY
        - name: ALERT_FROM_EMAIL
          valueFrom:
            configMapKeyRef:
              name: lazarus-config
              key: ALERT_FROM_EMAIL
        - name: ALERT_TO_EMAIL
          valueFrom:
            configMapKeyRef:
              name: lazarus-config
              key: ALERT_TO_EMAIL
        - name: TELEGRAM_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: lazarus-secret
              key: TELEGRAM_BOT_TOKEN
        - name: TELEGRAM_CHAT_ID
          valueFrom:
            secretKeyRef:
              name: lazarus-secret
              key: TELEGRAM_CHAT_ID
        volumeMounts:
        - name: lazarus-data
          mountPath: /app/.lazarus
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: lazarus-data
        persistentVolumeClaim:
          claimName: lazarus-pvc
```

```bash
# Apply Deployment
kubectl apply -f deployment.yaml
```

#### Step 7: Create Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: lazarus-service
  namespace: lazarus
spec:
  selector:
    app: lazarus
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: dashboard
    port: 8080
    targetPort: 8080
  type: LoadBalancer
```

```bash
# Apply Service
kubectl apply -f service.yaml
```

#### Step 8: Create Ingress (Optional)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lazarus-ingress
  namespace: lazarus
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - lazarus.yourdomain.com
    secretName: lazarus-tls
  rules:
  - host: lazarus.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lazarus-service
            port:
              number: 80
```

```bash
# Apply Ingress
kubectl apply -f ingress.yaml
```

#### Step 9: Verify Deployment

```bash
# Check pods
kubectl get pods -n lazarus

# Check services
kubectl get services -n lazarus

# Check logs
kubectl logs -f deployment/lazarus -n lazarus

# Check health
kubectl exec -it deployment/lazarus -n lazarus -- curl http://localhost:8000/api/v1/health
```

### Kubernetes Management

#### Scaling

```bash
# Scale deployment
kubectl scale deployment lazarus --replicas=5 -n lazarus

# Check scale status
kubectl get pods -n lazarus
```

#### Rolling Updates

```bash
# Update image
kubectl set image deployment/lazarus lazarus=ghcr.io/ravikumarve/lazarus:v1.1.0 -n lazarus

# Check rollout status
kubectl rollout status deployment/lazarus -n lazarus

# Rollback if needed
kubectl rollout undo deployment/lazarus -n lazarus
```

#### Debugging

```bash
# Get pod logs
kubectl logs -f deployment/lazararus -n lazarus

# Exec into pod
kubectl exec -it deployment/lazararus -n lazarus -- /bin/bash

# Describe pod
kubectl describe pod <pod-name> -n lazarus
```

---

## 🔒 SSL/TLS Configuration

### Let's Encrypt (Recommended)

#### Installation

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Or for standalone mode
sudo apt install certbot
```

#### Certificate Generation

```bash
# Generate certificate (standalone)
sudo certbot certonly --standalone -d lazarus.yourdomain.com

# Or with nginx
sudo certbot --nginx -d lazarus.yourdomain.com
```

#### Certificate Paths

```bash
# Certificate locations
/etc/letsencrypt/live/lazarus.yourdomain.com/fullchain.pem
/etc/letsencrypt/live/lazarus.yourdomain.com/privkey.pem
```

#### Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up cron job for renewal
# Verify cron job
sudo systemctl status certbot.timer
```

### Self-Signed Certificate (Development)

#### Generation

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=lazarus.local"

# Set permissions
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

#### Configuration

```bash
# Add to environment
export LAZARUS_SSL_CERT_FILE=/path/to/ssl/cert.pem
export LAZARUS_SSL_KEY_FILE=/path/to/ssl/key.pem
```

### Nginx Reverse Proxy

#### Configuration

```nginx
# /etc/nginx/sites-available/lazarus
server {
    listen 80;
    server_name lazarus.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name lazarus.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/lazarus.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lazarus.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Proxy to Lazarus
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy to dashboard
    location /dashboard {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Enable Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/lazarus /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 📊 Monitoring and Logging

### Log Management

#### Log Rotation

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/lazarus

# Add:
/opt/lazarus/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 lazarus lazarus
    sharedscripts
    postrotate
        systemctl reload lazarus > /dev/null 2>&1 || true
    endscript
}
```

#### Log Aggregation

```bash
# View logs
tail -f /opt/lazarus/logs/lazarus.log

# Search for errors
grep ERROR /opt/lazarus/logs/lazarus.log

# View recent logs
tail -100 /opt/lazarus/logs/lazarus.log
```

### Health Monitoring

#### Health Checks

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": 1714234567.123,
  "uptime": 86400.0
}
```

#### Monitoring Tools

**Prometheus + Grafana**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'lazarus'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**Uptime Monitoring**

```bash
# Use uptime monitoring service
# - UptimeRobot
# - Pingdom
# - StatusCake
```

### Alerting

#### Email Alerts

```bash
# Configure email alerts for:
# - Service down
# - High error rate
# - Disk space low
# - CPU/memory high
```

#### Slack Alerts

```bash
# Configure Slack webhook for alerts
# Send alerts to Slack channel
```

---

## 💾 Backup and Recovery

### Backup Strategy

#### Automated Backups

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/lazarus/scripts/backup.sh

# Weekly backup on Sunday at 3 AM
0 3 * * 0 /opt/lazarus/scripts/weekly-backup.sh
```

#### Backup Script

```bash
#!/bin/bash
# /opt/lazarus/scripts/backup.sh

BACKUP_DIR="/backups/lazarus"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/lazarus-backup-$DATE.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration and data
tar -czf "$BACKUP_FILE" \
  /opt/lazarus/.lazarus \
  /opt/lazarus/.env \
  /opt/lazarus/docker-compose.yml

# Keep last 30 days of backups
find "$BACKUP_DIR" -name "lazarus-backup-*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

#### Backup Verification

```bash
# Test backup integrity
tar -tzf /backups/lazarus/lazarus-backup-YYYYMMDD-HHMMSS.tar.gz

# Test restore to temporary location
tar -xzf /backups/lazarus/lazarus-backup-YYYYMMDD-HHMMSS.tar.gz -C /tmp/test
```

### Recovery Procedures

#### Restore from Backup

```bash
#!/bin/bash
# /opt/lazarus/scripts/restore.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

# Stop service
sudo systemctl stop lazarus

# Restore from backup
tar -xzf "$BACKUP_FILE" -C /

# Start service
sudo systemctl start lazarus

echo "Restore completed from: $BACKUP_FILE"
```

#### Disaster Recovery

```bash
# 1. Provision new server
# 2. Install dependencies
# 3. Restore from backup
# 4. Verify functionality
# 5. Update DNS if needed
```

---

## 🔐 Security Hardening

### System Security

#### Firewall Configuration

```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

#### User Security

```bash
# Create dedicated user
sudo useradd -r -s /bin/false lazarus

# Set up sudo rules
sudo visudo

# Add:
lazarus ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart lazarus
```

### Application Security

#### File Permissions

```bash
# Secure configuration directory
chmod 700 /opt/lazarus/.lazarus
chmod 600 /opt/lazarus/.lazarus/config.json
chmod 600 /opt/lazarus/.lazarus/encrypted_secrets.bin

# Secure SSL certificates
chmod 600 /opt/lazarus/ssl/key.pem
chmod 644 /opt/lazarus/ssl/cert.pem
```

#### Environment Variables

```bash
# Secure environment file
chmod 600 /opt/lazarus/.env

# Never commit .env to git
echo ".env" >> .gitignore
```

### Network Security

#### SSL/TLS

```bash
# Use strong SSL/TLS configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
```

#### Rate Limiting

```nginx
# Add to nginx configuration
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20;
    proxy_pass http://localhost:8000;
}
```

---

## ⚡ Performance Tuning

### Resource Optimization

#### Memory Limits

```bash
# Set memory limits in Docker
# docker-compose.yml
services:
  lazarus:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

#### CPU Limits

```bash
# Set CPU limits in Kubernetes
# deployment.yaml
resources:
  requests:
    cpu: "500m"
  limits:
    cpu: "1000m"
```

### Database Optimization

#### Connection Pooling

```python
# Configure connection pool
# (if using database backend)
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
```

#### Caching

```bash
# Enable caching
# (if using Redis)
export LAZARUS_CACHE_ENABLED=true
export LAZARUS_CACHE_REDIS_URL=redis://localhost:6379/0
```

### Network Optimization

#### Keep-Alive

```nginx
# Enable keep-alive in nginx
keepalive_timeout 65;
keepalive_requests 100;
```

#### Compression

```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript;
```

---

## ✅ Post-Deployment Checklist

### Verification

- [ ] Service is running
- [ ] Health endpoint responds
- [ ] Web dashboard accessible
- [ ] SSL/TLS working
- [ ] Email alerts configured
- [ ] Backup system working
- [ ] Monitoring configured
- [ ] Logs being collected

### Testing

- [ ] Test check-in functionality
- [ ] Test email alerts
- [ ] Test Telegram alerts (if configured)
- [ ] Test trigger simulation
- [ ] Test backup/restore
- [ ] Load testing
- [ ] Failover testing

### Documentation

- [ ] Update deployment documentation
- [ ] Document configuration
- [ ] Create runbook
- [ ] Document procedures
- [ ] Update contact information

### Handoff

- [ ] Train operations team
- [ ] Provide access credentials
- [ ] Share documentation
- [ ] Schedule knowledge transfer
- [ ] Establish support channels

---

## 📚 Additional Resources

### Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 15 minutes
- [Installation Guide](INSTALLATION.md) - Installation instructions
- [Security Guide](SECURITY.md) - Security best practices
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md) - Detailed production deployment

### Support

- [GitHub Issues](https://github.com/ravikumarve/lazarus/issues) - Report bugs
- [GitHub Discussions](https://github.com/ravikumarve/lazarus/discussions) - Ask questions
- Email: ravikumarve@protonmail.com

---

## 🎯 Conclusion

Deploying Lazarus Protocol in production requires careful planning and execution. By following this deployment guide, you can ensure a reliable, secure, and maintainable deployment.

**Remember:**
- Test thoroughly in staging before production
- Monitor system health continuously
- Keep regular backups
- Plan for disaster recovery
- Document all procedures

---

**Built with paranoia and love. For the people who hold their own keys.** 🔐
