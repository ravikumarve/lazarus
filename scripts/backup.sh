#!/bin/bash

# Lazarus Protocol - Automated Backup Script

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup process at ${TIMESTAMP}" | tee -a "${LOG_FILE}"

# Backup database
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backing up database..." | tee -a "${LOG_FILE}"
if docker-compose exec -T lazarus python -c "from core.database import get_database_manager; db = get_database_manager(); db.backup()" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database backup completed successfully" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Database backup failed" | tee -a "${LOG_FILE}"
    exit 1
fi

# Copy database backup to timestamped file
if [ -f "data/lazarus.db" ]; then
    cp "data/lazarus.db" "${BACKUP_DIR}/lazarus_${TIMESTAMP}.db"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database copied to ${BACKUP_DIR}/lazarus_${TIMESTAMP}.db" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Database file not found" | tee -a "${LOG_FILE}"
    exit 1
fi

# Backup configuration
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backing up configuration..." | tee -a "${LOG_FILE}"
if [ -f ".env.production" ]; then
    cp ".env.production" "${BACKUP_DIR}/env_${TIMESTAMP}.backup"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Configuration backed up" | tee -a "${LOG_FILE}"
fi

# Create latest symlink
ln -sf "${BACKUP_DIR}/lazarus_${TIMESTAMP}.db" "${BACKUP_DIR}/lazarus.db.latest"

# Clean up old backups
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up old backups..." | tee -a "${LOG_FILE}"
find "${BACKUP_DIR}" -name "lazarus_*.db" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "env_*.backup" -mtime +${RETENTION_DAYS} -delete

# Calculate backup size
BACKUP_SIZE=$(du -sh "${BACKUP_DIR} | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Total backup size: ${BACKUP_SIZE}" | tee -a "${LOG_FILE}"

# Verify backup integrity
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Verifying backup integrity..." | tee -a "${LOG_FILE}"
if sqlite3 "${BACKUP_DIR}/lazarus_${TIMESTAMP}.db" "PRAGMA integrity_check;" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup integrity check passed" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup integrity check failed" | tee -a "${LOG_FILE}"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed successfully" | tee -a "${LOG_FILE}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Latest backup: ${BACKUP_DIR}/lazarus.db.latest" | tee -a "${LOG_FILE}"

exit 0
