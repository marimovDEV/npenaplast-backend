import os
import subprocess
from datetime import datetime
from django.conf import settings
from celery import shared_task
from django.core.management import call_command

import time

@shared_task
def backup_database_task():
    """
    Automated Daily Backup Task (Phase 7).
    Backs up SQLite db_v2.sqlite3 (if used) or triggers PG dump.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    # 1. DB Backup
    db_backup_path = os.path.join(backup_dir, f'db_dump_{timestamp}.json')
    try:
        with open(db_backup_path, 'w') as f:
            call_command('dumpdata', indent=2, exclude=['contenttypes', 'auth.Permission'], stdout=f)
        print(f"Backup completed: {db_backup_path}")
        return db_backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return str(e)

@shared_task
def cleanup_old_backups():
    """Removes backups older than 30 days (Phase 8)."""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    if not os.path.exists(backup_dir):
        return "No backup directory found."
        
    now = time.time()
    deleted_count = 0
    
    for f in os.listdir(backup_dir):
        file_path = os.path.join(backup_dir, f)
        if os.stat(file_path).st_mtime < now - (30 * 86400):
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_count += 1
                
    return f"Cleaned up {deleted_count} old backups."
