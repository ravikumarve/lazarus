# Lazarus Protocol - Operations Runbook

## Overview

This runbook provides step-by-step procedures for common operational tasks and incident response.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Weekly Operations](#weekly-operations)
3. [Monthly Operations](#monthly-operations)
4. [Incident Response](#incident-response)
5. [Emergency Procedures](#emergency-procedures)
6. [Maintenance Windows](#maintenance-windows)

## Daily Operations

### Morning Checklist

**Time:** 09:00 UTC

**Tasks:**
1. Check system status
2. Review overnight logs
3. Verify backup completion
4. Check alert notifications

**Procedure:**
```bash
# Check service status
docker-compose ps

# Check overnight logs
docker-compose logs --since="24h" lazarus | grep -i error

# Verify backup completion
ls -lth backups/ | head -5

# Check Grafana alerts
curl -u admin:admin https://grafana.lazarusprotocol.com/api/alerts
```

### Evening Checklist

**Time:** 18:00 UTC

**Tasks:**
1. Review daily metrics
2. Check system resources
3. Verify data integrity
4. Document any issues

**Procedure:**
```bash
# Check system resources
docker stats --no-stream

# Verify database integrity
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"

# Check disk space
df -h

# Document issues
echo "$(date): Daily check completed" >> operations/daily.log
```

## Weekly Operations

### Monday: Security Review

**Tasks:**
1. Review security logs
2. Check for vulnerabilities
3. Audit user access
4. Review rate limiting

**Procedure:**
```bash
# Review security logs
docker-compose logs --since="7d" lazarus | grep -i "security\|auth\|login"

# Check for vulnerabilities
safety check

# Audit user access
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); users = db._query('SELECT * FROM users'); print(users)"

# Review rate limiting
docker-compose exec redis redis-cli KEYS "rate_limit:*"
```

### Wednesday: Performance Review

**Tasks:**
1. Review performance metrics
2. Check slow queries
3. Analyze response times
4. Review resource usage

**Procedure:**
```bash
# Check performance metrics
curl http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])

# Check slow queries
docker-compose logs --since="7d" lazarus | grep -i "slow\|timeout"

# Analyze response times
curl http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,http_request_duration_seconds)

# Review resource usage
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Friday: Backup Verification

**Tasks:**
1. Verify backup integrity
2. Test restore procedure
3. Review backup retention
4. Update backup strategy

**Procedure:**
```bash
# Verify backup integrity
for backup in backups/*.db; do
    echo "Checking $backup"
    sqlite3 "$backup" "PRAGMA integrity_check;"
done

# Test restore procedure
cp backups/lazarus.db.latest data/lazarus.test.db
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(DatabaseConfig(path='/data/lazarus.test.db')); print(db.get_stats())"
rm data/lazarus.test.db

# Review backup retention
ls -lth backups/ | wc -l

# Document findings
echo "$(date): Backup verification completed" >> operations/backup.log
```

## Monthly Operations

### First Monday: System Update

**Tasks:**
1. Update system packages
2. Update Python dependencies
3. Update Docker images
4. Test updates in staging

**Procedure:**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
pip list --outdated
pip install --upgrade -r requirements.txt

# Update Docker images
docker-compose pull

# Test in staging
git checkout staging
docker-compose -f docker-compose.staging.yml up -d
# Run smoke tests
docker-compose -f docker-compose.staging.yml down
git checkout main
```

### Third Monday: Security Audit

**Tasks:**
1. Run security scans
2. Review access logs
3. Audit API keys
4. Review encryption keys

**Procedure:**
```bash
# Run security scans
bandit -r . -f json > security/bandit-$(date +%Y%m%d).json
safety check --json > security/safety-$(date +%Y%m%d).json
semgrep --config=auto --json --output=security/semgrep-$(date +%Y%m%d).json .

# Review access logs
docker-compose logs --since="30d" lazarus | grep -i "access\|auth" > security/access-$(date +%Y%m%d).log

# Audit API keys
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); users = db._query('SELECT email, api_key FROM users'); print(users)"

# Document findings
echo "$(date): Security audit completed" >> operations/security.log
```

### Last Monday: Disaster Recovery Test

**Tasks:**
1. Test backup restore
2. Test failover procedures
3. Test monitoring alerts
4. Update documentation

**Procedure:**
```bash
# Test backup restore
docker-compose stop lazarus
cp backups/lazarus.db.latest data/lazarus.db
docker-compose start lazarus
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"

# Test monitoring alerts
# Trigger test alert and verify notification

# Update documentation
# Update this runbook with any changes

# Document test results
echo "$(date): Disaster recovery test completed" >> operations/dr-test.log
```

## Incident Response

### Severity Levels

**P1 - Critical:**
- System down
- Data loss
- Security breach
- Response time: < 15 minutes

**P2 - High:**
- Performance degradation
- Feature broken
- Data inconsistency
- Response time: < 1 hour

**P3 - Medium:**
- Minor issues
- Non-critical bugs
- Documentation issues
- Response time: < 4 hours

**P4 - Low:**
- Cosmetic issues
- Enhancement requests
- Questions
- Response time: < 24 hours

### Incident Response Procedure

#### 1. Detection

**How to detect:**
- Monitoring alerts
- User reports
- Automated checks
- Log analysis

**Actions:**
1. Acknowledge alert
2. Assess severity
3. Notify team
4. Create incident ticket

#### 2. Triage

**Questions to answer:**
1. What is the impact?
2. How many users affected?
3. Is there a workaround?
4. What is the root cause?

**Actions:**
1. Gather information
2. Check logs
3. Monitor metrics
4. Identify scope

#### 3. Mitigation

**Immediate actions:**
1. Stop the bleeding
2. Implement workaround
3. Communicate with users
4. Document actions

**Commands:**
```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f lazarus

# Restart service
docker-compose restart lazarus

# Scale up resources
docker-compose up -d --scale lazarus=2
```

#### 4. Resolution

**Actions:**
1. Implement fix
2. Test thoroughly
3. Deploy to production
4. Verify resolution

#### 5. Post-Incident

**Actions:**
1. Document incident
2. Root cause analysis
3. Implement improvements
4. Update runbooks

## Emergency Procedures

### System Down

**Symptoms:** All services unavailable

**Immediate Actions:**
```bash
# Check service status
docker-compose ps

# Check system resources
free -h
df -h
top

# Restart services
docker-compose restart

# If restart fails, check logs
docker-compose logs --tail=100 lazarus

# If still down, restore from backup
docker-compose down
cp backups/lazarus.db.latest data/lazarus.db
docker-compose up -d
```

### Database Corruption

**Symptoms:** Database errors, data loss

**Immediate Actions:**
```bash
# Stop application
docker-compose stop lazarus

# Check database integrity
sqlite3 data/lazarus.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp backups/lazarus.db.latest data/lazarus.db

# Start application
docker-compose start lazarus

# Verify
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"
```

### Security Breach

**Symptoms:** Unauthorized access, data exposure

**Immediate Actions:**
```bash
# Stop all services
docker-compose down

# Change all credentials
# Update API keys
# Rotate encryption keys

# Review logs
docker-compose logs --since="24h" | grep -i "auth\|login\|access"

# Scan for malware
# Check for backdoors

# Restore from clean backup
cp backups/lazarus.db.clean data/lazarus.db

# Start services
docker-compose up -d

# Monitor closely
docker-compose logs -f
```

### Performance Degradation

**Symptoms:** Slow response times, timeouts

**Immediate Actions:**
```bash
# Check system resources
docker stats

# Check database performance
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.analyze()"

# Clear caches
docker-compose exec redis redis-cli FLUSHALL

# Restart services
docker-compose restart

# If still slow, scale up
docker-compose up -d --scale lazarus=2
```

## Maintenance Windows

### Scheduled Maintenance

**Frequency:** Monthly

**Duration:** 2 hours

**Notification:** 48 hours in advance

**Procedure:**
1. Notify users
2. Create backup
3. Perform maintenance
4. Test systems
5. Notify completion

### Emergency Maintenance

**Frequency:** As needed

**Duration:** As needed

**Notification:** As soon as possible

**Procedure:**
1. Assess impact
2. Notify users
3. Perform maintenance
4. Test systems
5. Notify completion

## Communication Procedures

### Internal Communication

**Channels:**
- Slack: #lazarus-ops
- Email: ops@lazarusprotocol.com
- Phone: On-call rotation

**Escalation:**
1. Level 1: On-call engineer
2. Level 2: Engineering lead
3. Level 3: CTO
4. Level 4: CEO

### External Communication

**Channels:**
- Status page: https://status.lazarusprotocol.com
- Email: users@lazarusprotocol.com
- Twitter: @lazarusprotocol

**Templates:**

**Incident Notification:**
```
Subject: [INCIDENT] Service Degradation - [Severity]

We are currently experiencing [issue description].
Impact: [affected users/features]
Status: [investigating/mitigating/resolved]
ETA: [estimated resolution time]

Updates will be posted at https://status.lazarusprotocol.com
```

**Maintenance Notification:**
```
Subject: [MAINTENANCE] Scheduled Maintenance - [Date/Time]

We will be performing scheduled maintenance on [date/time].
Duration: [duration]
Impact: [affected services/features]

Updates will be posted at https://status.lazarusprotocol.com
```

## Documentation Updates

**When to update:**
- After any incident
- After procedure changes
- After system updates
- Monthly review

**How to update:**
1. Edit this runbook
2. Test new procedures
3. Get team approval
4. Commit to repository
5. Notify team

## Training and Onboarding

**New Engineer Onboarding:**
1. Review this runbook
2. Shadow on-call engineer
3. Practice procedures
4. Pass knowledge check

**Regular Training:**
- Monthly: Runbook review
- Quarterly: Incident simulation
- Annually: Full disaster recovery test

## Contact Information

**On-Call:**
- Primary: [phone number]
- Secondary: [phone number]

**Team:**
- Engineering Lead: [email]
- DevOps Engineer: [email]
- Security Engineer: [email]

**External:**
- Support: support@lazarusprotocol.com
- Security: security@lazarusprotocol.com

## Appendix

### Useful Commands

```bash
# Service management
docker-compose ps
docker-compose logs -f [service]
docker-compose restart [service]
docker-compose stop [service]
docker-compose start [service]

# Database operations
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())"
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.backup()"
docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.vacuum()"

# Redis operations
docker-compose exec redis redis-cli ping
docker-compose exec redis redis-cli INFO
docker-compose exec redis redis-cli KEYS "*"

# Monitoring
curl http://localhost:9090/api/v1/query?query=up
curl http://localhost:9090/api/v1/targets

# Logs
docker-compose logs --since="1h" lazarus
docker-compose logs --tail=100 lazarus
docker-compose logs --since="2024-01-01" lazarus | grep -i error
```

### Quick Reference

| Task | Command |
|------|---------|
| Check status | `docker-compose ps` |
| View logs | `docker-compose logs -f` |
| Restart service | `docker-compose restart` |
| Backup database | `docker-compose exec lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.backup()"` |
| Check health | `curl http://localhost:5555/health` |
| Clear cache | `docker-compose exec redis redis-cli FLUSHALL` |

---

**Last Updated:** 2026-05-08
**Version:** 1.0
**Maintained By:** Operations Team
