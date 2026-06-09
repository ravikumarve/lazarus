#!/bin/bash

# Lazarus Protocol - Automated Restore Script

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_FILE="${1:-${BACKUP_DIR}/lazarus.db.latest}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/restore_${TIMESTAMP}.log"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting restore process from ${BACKUP_FILE}" | tee -a "${LOG_FILE}"

# Stop application
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopping application..." | tee -a "${LOG_FILE}"
docker-compose stop lazarus

# Create backup of current database
if [ -f "data/lazarus.db" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Creating backup of current database..." | tee -a "${LOG_FILE}"
    cp "data/lazarus.db" "${BACKUP_DIR}/lazarus.db.before_restore_${TIMESTAMP}"
fi

# Restore database
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring database..." | tee -a "${LOG_FILE}"
cp "${BACKUP_FILE}" "data/lazarus.db"

# Verify restored database
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Verifying restored database..." | tee -a "${LOG_FILE}"
if sqlite3 "data/lazarus.db" "PRAGMA integrity_check;" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database integrity check passed" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Database integrity check failed" | tee -a "${LOG_FILE}"
    exit 1
fi

# Start application
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting application..." | tee -a "${LOG_FILE}"
docker-compose start lazarus

# Wait for application to start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting for application to start..." | tee -a "${LOG_FILE}"
sleep 10

# Verify application is running
if docker-compose ps lazarus | grep -q "Up"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Application started successfully" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Application failed to start" | tee -a "${LOG_FILE}"
    exit 1
fi

# Test database connection
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Testing database connection..." | tee -a "${LOG_FILE}"
if docker-compose exec -T lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); print(db.get_stats())" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database connection test passed" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Database connection test failed" | tee -a "${LOG_FILE}"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restore completed successfully" | tee -a "${LOG_FILE}"

exit 0
