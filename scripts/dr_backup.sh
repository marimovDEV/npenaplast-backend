#!/bin/bash
# FINAL ENTERPRISE HARDENING: Disaster Recovery & Backup Script
# Ushbu skript har kuni CRON orqali ishga tushadi.

BACKUP_DIR="/var/backups/penaplast_erp"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_FILE="../db_v2.sqlite3"  # Yoki PostgreSQL uchun pg_dump
ARCHIVE_NAME="erp_backup_$TIMESTAMP.tar.gz"

echo "========================================"
echo "STARTING BACKUP: $TIMESTAMP"
echo "========================================"

mkdir -p "$BACKUP_DIR"

# 1. Baza nusxasi
if [ -f "$DB_FILE" ]; then
    echo "1. SQLite db backup in progress..."
    cp "$DB_FILE" "$BACKUP_DIR/db_backup_$TIMESTAMP.sqlite3"
    
    # Compress
    tar -czf "$BACKUP_DIR/$ARCHIVE_NAME" -C "$BACKUP_DIR" "db_backup_$TIMESTAMP.sqlite3"
    
    # Remove raw DB backup
    rm "$BACKUP_DIR/db_backup_$TIMESTAMP.sqlite3"
    
    echo "Backup archived successfully: $ARCHIVE_NAME"
else
    echo "ERROR: DB file not found!"
    exit 1
fi

# 2. Eskilarni o'chirish (Log retention: 7 kun)
echo "2. Cleaning up old backups (older than 7 days)..."
find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +7 -exec rm {} \;

# 3. Offsite Sync (Masalan, AWS S3 yoki FTP)
# echo "3. Syncing to S3..."
# aws s3 cp "$BACKUP_DIR/$ARCHIVE_NAME" s3://penaplast-erp-backups/ --quiet

echo "========================================"
echo "BACKUP COMPLETED LOGGED AT $TIMESTAMP"
echo "========================================"
exit 0
