"""
core/migrations.py — Database migration system for Lazarus Protocol.

Provides:
- Database version tracking
- Migration execution and rollback
- Migration history management
- Safe schema evolution
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Dict, Any

from core.database import DatabaseManager


# ---------------------------------------------------------------------------
# Migration Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Migration:
    """Database migration definition"""
    version: int
    description: str
    up: Callable[[sqlite3.Connection], None]
    down: Callable[[sqlite3.Connection], None]


# ---------------------------------------------------------------------------
# Migration Manager
# ---------------------------------------------------------------------------

class MigrationManager:
    """
    Database migration manager.
    
    This class provides:
    - Migration version tracking
    - Safe migration execution
    - Rollback support
    - Migration history
    """

    def __init__(self, db: DatabaseManager):
        """
        Initialize migration manager.
        
        Args:
            db: Database manager instance
        """
        self.db = db
        self._logger = logging.getLogger("lazarus.migrations")
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Ensure migrations tracking table exists"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rollback_available BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()
            self._logger.debug("Migrations table ensured")

    def get_applied_migrations(self) -> List[int]:
        """
        Get list of applied migration versions.
        
        Returns:
            List of applied migration versions
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] for row in cursor.fetchall()]

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history.
        
        Returns:
            List of migration history entries
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version, description, applied_at, rollback_available
                FROM schema_migrations
                ORDER BY version DESC
            """)
            return [
                {
                    "version": row[0],
                    "description": row[1],
                    "applied_at": row[2].isoformat() if row[2] else None,
                    "rollback_available": bool(row[3])
                }
                for row in cursor.fetchall()
            ]

    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a migration.
        
        Args:
            migration: Migration to apply
            
        Returns:
            True if successful, False otherwise
        """
        applied = self.get_applied_migrations()
        
        if migration.version in applied:
            self._logger.info(f"Migration {migration.version} already applied")
            return True
        
        self._logger.info(f"Applying migration {migration.version}: {migration.description}")
        
        try:
            with self.db.transaction() as conn:
                # Execute migration
                migration.up(conn)
                
                # Record migration
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, description, rollback_available)
                    VALUES (?, ?, ?)
                    """,
                    (migration.version, migration.description, 1)
                )
            
            self._logger.info(f"Migration {migration.version} applied successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to apply migration {migration.version}: {e}")
            return False

    def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a migration.
        
        Args:
            migration: Migration to rollback
            
        Returns:
            True if successful, False otherwise
        """
        applied = self.get_applied_migrations()
        
        if migration.version not in applied:
            self._logger.warning(f"Migration {migration.version} not applied, cannot rollback")
            return False
        
        self._logger.info(f"Rolling back migration {migration.version}: {migration.description}")
        
        try:
            with self.db.transaction() as conn:
                # Execute rollback
                migration.down(conn)
                
                # Remove migration record
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )
            
            self._logger.info(f"Migration {migration.version} rolled back successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to rollback migration {migration.version}: {e}")
            return False

    def migrate_to_version(self, target_version: int, migrations: List[Migration]) -> bool:
        """
        Migrate database to specific version.
        
        Args:
            target_version: Target migration version
            migrations: List of available migrations
            
        Returns:
            True if successful, False otherwise
        """
        applied = self.get_applied_migrations()
        current_version = max(applied) if applied else 0
        
        if target_version == current_version:
            self._logger.info(f"Already at version {target_version}")
            return True
        
        if target_version > current_version:
            # Migrate up
            for migration in migrations:
                if migration.version > current_version and migration.version <= target_version:
                    if not self.apply_migration(migration):
                        return False
        else:
            # Migrate down
            for migration in reversed(migrations):
                if migration.version <= current_version and migration.version > target_version:
                    if not self.rollback_migration(migration):
                        return False
        
        return True

    def migrate_to_latest(self, migrations: List[Migration]) -> bool:
        """
        Migrate database to latest version.
        
        Args:
            migrations: List of available migrations
            
        Returns:
            True if successful, False otherwise
        """
        if not migrations:
            self._logger.info("No migrations available")
            return True
        
        latest_version = max(m.version for m in migrations)
        return self.migrate_to_version(latest_version, migrations)


# ---------------------------------------------------------------------------
# Migration Definitions
# ---------------------------------------------------------------------------

def create_initial_schema(conn: sqlite3.Connection) -> None:
    """Create initial database schema (already done in DatabaseManager)"""
    # This is a no-op as schema is created in DatabaseManager._ensure_schema()
    pass


def drop_initial_schema(conn: sqlite3.Connection) -> None:
    """Drop initial database schema"""
    tables = [
        'documents', 'events', 'rate_limits', 'vaults',
        'configurations', 'users', 'schema_migrations'
    ]
    
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")


def add_user_preferences_table(conn: sqlite3.Connection) -> None:
    """Add user preferences table"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preference_key TEXT NOT NULL,
            preference_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, preference_key)
        )
    """)
    
    # Create index
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id)")


def drop_user_preferences_table(conn: sqlite3.Connection) -> None:
    """Drop user preferences table"""
    conn.execute("DROP TABLE IF EXISTS user_preferences")


def add_audit_log_table(conn: sqlite3.Connection) -> None:
    """Add audit log table for security events"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            configuration_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE SET NULL
        )
    """)
    
    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_config ON audit_log(configuration_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)")


def drop_audit_log_table(conn: sqlite3.Connection) -> None:
    """Drop audit log table"""
    conn.execute("DROP TABLE IF EXISTS audit_log")


def add_api_keys_table(conn: sqlite3.Connection) -> None:
    """Add separate API keys table for better key management"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key_hash TEXT NOT NULL,
            key_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            last_used_at TIMESTAMP,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(key_hash)
        )
    """)
    
    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")


def drop_api_keys_table(conn: sqlite3.Connection) -> None:
    """Drop API keys table"""
    conn.execute("DROP TABLE IF EXISTS api_keys")


# ---------------------------------------------------------------------------
# Migration Registry
# ---------------------------------------------------------------------------

MIGRATIONS: List[Migration] = [
    Migration(
        version=1,
        description="Initial schema",
        up=create_initial_schema,
        down=drop_initial_schema
    ),
    Migration(
        version=2,
        description="Add user preferences table",
        up=add_user_preferences_table,
        down=drop_user_preferences_table
    ),
    Migration(
        version=3,
        description="Add audit log table",
        up=add_audit_log_table,
        down=drop_audit_log_table
    ),
    Migration(
        version=4,
        description="Add API keys table",
        up=add_api_keys_table,
        down=drop_api_keys_table
    ),
]


# ---------------------------------------------------------------------------
# Migration Utilities
# ---------------------------------------------------------------------------

def get_migration_manager(db: DatabaseManager) -> MigrationManager:
    """
    Get migration manager for database.
    
    Args:
        db: Database manager instance
        
    Returns:
        MigrationManager instance
    """
    return MigrationManager(db)


def run_migrations(db: DatabaseManager, target_version: Optional[int] = None) -> bool:
    """
    Run database migrations.
    
    Args:
        db: Database manager instance
        target_version: Target version (migrates to latest if None)
        
    Returns:
        True if successful, False otherwise
    """
    manager = get_migration_manager(db)
    
    if target_version is None:
        return manager.migrate_to_latest(MIGRATIONS)
    else:
        return manager.migrate_to_version(target_version, MIGRATIONS)


def get_migration_status(db: DatabaseManager) -> Dict[str, Any]:
    """
    Get migration status.
    
    Args:
        db: Database manager instance
        
    Returns:
        Dictionary with migration status
    """
    manager = get_migration_manager(db)
    applied = manager.get_applied_migrations()
    history = manager.get_migration_history()
    
    current_version = max(applied) if applied else 0
    latest_version = max(m.version for m in MIGRATIONS) if MIGRATIONS else 0
    
    return {
        "current_version": current_version,
        "latest_version": latest_version,
        "up_to_date": current_version == latest_version,
        "pending_migrations": latest_version - current_version,
        "applied_count": len(applied),
        "history": history
    }
