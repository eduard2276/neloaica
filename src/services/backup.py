"""Database backup service."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple, List

from src.database.connection import DatabaseConnection


# Backup directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKUPS_DIR = PROJECT_ROOT / "backups"

# Maximum number of backups to keep
MAX_BACKUPS = 7


def ensure_backups_dir():
    """Ensure the backups directory exists."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def get_database_path() -> Path:
    """Get the current database file path."""
    db = DatabaseConnection()
    return db._db_path


def create_backup(backup_type: str = "manual") -> Tuple[str, bool]:
    """
    Create a database backup.
    
    Args:
        backup_type: Type of backup (manual, auto, startup, pre-receipt)
        
    Returns:
        Tuple of (backup_path, success)
    """
    try:
        ensure_backups_dir()
        
        # Get database path
        db_path = get_database_path()
        
        if not db_path.exists():
            return "", False
        
        # Generate backup filename with timestamp and type
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"neloaica_backup_{backup_type}_{timestamp}.db"
        backup_path = BACKUPS_DIR / backup_filename
        
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Clean up old backups
        cleanup_old_backups()
        
        return str(backup_path), True
        
    except Exception as e:
        print(f"[ERROR] Failed to create backup: {e}")
        return "", False


def cleanup_old_backups():
    """Remove old backups, keeping only the last MAX_BACKUPS files."""
    try:
        if not BACKUPS_DIR.exists():
            return
        
        # Get all backup files sorted by modification time (newest first)
        backup_files = sorted(
            BACKUPS_DIR.glob("neloaica_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove old backups beyond the limit
        for old_backup in backup_files[MAX_BACKUPS:]:
            old_backup.unlink()
            print(f"[INFO] Removed old backup: {old_backup.name}")
            
    except Exception as e:
        print(f"[ERROR] Failed to cleanup old backups: {e}")


def get_all_backups() -> List[dict]:
    """
    Get list of all backup files with metadata.
    
    Returns:
        List of dicts with backup info (name, path, size, date)
    """
    try:
        if not BACKUPS_DIR.exists():
            return []
        
        backups = []
        for backup_file in sorted(
            BACKUPS_DIR.glob("neloaica_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "date": datetime.fromtimestamp(stat.st_mtime),
            })
        
        return backups
        
    except Exception as e:
        print(f"[ERROR] Failed to get backup list: {e}")
        return []


def should_create_daily_backup() -> bool:
    """
    Check if a daily backup should be created (no backup today yet).
    
    Returns:
        True if no backup exists for today
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        if not BACKUPS_DIR.exists():
            return True
        
        # Check if any backup was created today
        for backup_file in BACKUPS_DIR.glob("neloaica_backup_*.db"):
            # Extract date from filename (format: neloaica_backup_TYPE_YYYY-MM-DD_HH-MM-SS.db)
            parts = backup_file.stem.split("_")
            if len(parts) >= 4:
                backup_date = parts[3]  # YYYY-MM-DD part
                if backup_date == today:
                    return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to check daily backup status: {e}")
        return False


def restore_backup(backup_path: str) -> bool:
    """
    Restore database from a backup file.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        True if restore was successful
    """
    try:
        backup_file = Path(backup_path)
        if not backup_file.exists():
            return False
        
        # Get current database path
        db_path = get_database_path()
        
        # Create a safety backup of current database before restoring
        safety_backup = db_path.parent / f"{db_path.stem}_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, safety_backup)
        
        # Restore the backup
        shutil.copy2(backup_file, db_path)
        
        print(f"[INFO] Database restored from {backup_file.name}")
        print(f"[INFO] Safety backup created at {safety_backup.name}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to restore backup: {e}")
        return False
