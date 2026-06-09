# Lazarus Protocol - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying Lazarus Protocol to staging and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Software

- Docker 24.0+
- Docker Compose 2.0+
- Git
- Python 3.10+ (for local development)
- kubectl (if using Kubernetes)
- helm (if using Helm charts)

### Required Accounts

- GitHub account with repository access
- Container registry access (GitHub Container Registry or Docker Hub)
- SendGrid account (for email notifications)
- Telegram Bot account (for Telegram notifications)
- Pinata account (for IPFS pinning)
- Web3.Storage account (for IPFS storage)

### Infrastructure Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 2GB
- Storage: 20GB

**Recommended Requirements:**
- CPU: 4 cores
- RAM: 4GB
- Storage: 50GB

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/ravikumarve/lazarus.git
cd lazarus
```

### 2. Configure Environment Variables

```bash
# For staging
cp .env.staging.example .env.staging
nano .env.staging

# For production
cp .env.production.example .env.production
nano .env.production
```

### 3. Generate Encryption Keys

```bash
# Generate encryption salt
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Create Required Directories

```bash
mkdir -p data logs backups monitoring nginx/ssl
```

## Staging Deployment

### Automated Deployment via CI/CD

1. **Push to staging branch:**
   ```bash
   git checkout -b staging
   git push origin staging
   ```

2. **Monitor deployment:**
   - Go to GitHub Actions tab
   - Watch the "Deploy to Staging" job
   - Check staging environment: https://staging.lazarusprotocol.com

### Manual Deployment

1. **Build and start services:**
   ```bash
   docker-compose -f docker-compose.staging.yml up -d --build
   ```

2. **Verify deployment:**
   ```bash
   # Check service status
   docker-compose -f docker-compose.staging.yml ps
   
   # Check logs
   docker-compose -f docker-compose.staging.yml logs -f lazarus
   
   # Health check
   curl http://localhost:5555/health
   ```

3. **Run smoke tests:**
   ```bash
   # Test API endpoint
   curl -H "Authorization: Bearer $LAZARUS_API_KEY" http://localhost:5555/api/status
   
   # Test database connection
   docker-compose -f docker-compose.staging.yml exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"
   ```

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing in CI/CD
- [ ] Security scan completed with no critical issues
- [ ] Environment variables configured
- [ ] SSL/TLS certificates obtained
- [ ] Backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] Rollback plan documented

### Automated Deployment via CI/CD

1. **Create release tag:**
   ```bash
   git tag -a v1.0.0 -m "Production release v1.0.0"
   git push origin v1.0.0
   ```

2. **Monitor deployment:**
   - Go to GitHub Actions tab
   - Watch the "Deploy to Production" job
   - Check production environment: https://lazarusprotocol.com

### Manual Deployment

1. **Build and start services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

2. **Verify deployment:**
   ```bash
   # Check service status
   docker-compose -f docker-compose.prod.yml ps
   
   # Check logs
   docker-compose -f docker-compose.prod.yml logs -f lazarus
   
   # Health check
   curl https://lazarusprotocol.com/health
   ```

3. **Run smoke tests:**
   ```bash
   # Test API endpoint
   curl -H "Authorization: Bearer $LAZARUS_API_KEY" https://lazarusprotocol.com/api/status
   
   # Test database connection
   docker-compose -f docker-compose.prod.yml exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"
   ```

## Monitoring and Maintenance

### Access Monitoring Dashboards

- **Grafana:** https://grafana.lazarusprotocol.com (default: admin/admin)
- **Prometheus:** https://prometheus.lazarusprotocol.com
- **Alertmanager:** https://alertmanager.lazarusprotocol.com

### Key Metrics to Monitor

1. **Application Metrics:**
   - Request rate and response time
   - Error rate
   - Active configurations
   - Check-in frequency

2. **Database Metrics:**
   - Connection pool usage
   - Query performance
   - Database size
   - Backup status

3. **System Metrics:**
   - CPU usage
   - Memory usage
   - Disk usage
   - Network traffic

### Regular Maintenance Tasks

**Daily:**
- Check application logs for errors
- Verify backup completion
- Review alert notifications

**Weekly:**
- Review performance metrics
- Check disk space usage
- Update security patches

**Monthly:**
- Review and update documentation
- Test disaster recovery procedures
- Audit access controls

## Troubleshooting

### Common Issues

#### 1. Application won't start

**Symptoms:** Container exits immediately

**Solutions:**
```bash
# Check logs
docker-compose logs lazarus

# Check environment variables
docker-compose config

# Verify database permissions
ls -la data/
```

#### 2. High memory usage

**Symptoms:** OOM kills or slow performance

**Solutions:**
```bash
# Check memory usage
docker stats

# Restart services
docker-compose restart lazarus

# Adjust resource limits in docker-compose.prod.yml
```

#### 3. Database connection errors

**Symptoms:** Connection refused or timeout

**Solutions:**
```bash
# Check database file
ls -la data/lazarus.db

# Verify database integrity
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"

# Restart database
docker-compose restart lazarus
```

#### 4. Rate limiting not working

**Symptoms:** Too many requests allowed

**Solutions:**
```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Verify rate limit configuration
docker-compose exec lazarus env | grep RATE_LIMIT

# Restart Redis
docker-compose restart redis
```

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Review monitoring dashboards
3. Check GitHub Issues
4. Contact support team

## Rollback Procedures

### Automatic Rollback

If deployment fails, CI/CD will automatically rollback to previous version.

### Manual Rollback

1. **Stop current deployment:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore previous version:**
   ```bash
   git checkout v1.0.0
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Verify rollback:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   curl https://lazarusprotocol.com/health
   ```

### Database Rollback

1. **Stop application:**
   ```bash
   docker-compose stop lazarus
   ```

2. **Restore database backup:**
   ```bash
   cp backups/lazarus.db.backup data/lazarus.db
   ```

3. **Start application:**
   ```bash
   docker-compose start lazarus
   ```

## Security Best Practices

1. **Never commit secrets to version control**
2. **Use strong, unique passwords**
3. **Enable SSL/TLS in production**
4. **Regularly update dependencies**
5. **Monitor for security vulnerabilities**
6. **Implement proper access controls**
7. **Enable audit logging**
8. **Regular security audits**

## Backup and Recovery

### Automated Backups

Backups are automatically created every hour and retained for 30 days.

### Manual Backup

```bash
# Backup database
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.backup()"

# Backup configuration
cp .env.production backups/env.production.backup
```

### Restore from Backup

```bash
# Restore database
cp backups/lazarus.db.backup data/lazarus.db

# Restore configuration
cp backups/env.production.backup .env.production

# Restart services
docker-compose restart
```

## Performance Optimization

### Database Optimization

```bash
# Run VACUUM
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.vacuum()"

# Run ANALYZE
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.analyze()"
```

### Cache Optimization

```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Monitor Redis performance
docker-compose exec redis redis-cli INFO
```

## Support and Documentation

- **Documentation:** https://docs.lazarusprotocol.com
- **GitHub Issues:** https://github.com/ravikumarve/lazarus/issues
- **Support Email:** support@lazarusprotocol.com

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
