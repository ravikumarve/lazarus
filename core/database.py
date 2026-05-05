"""
core/database.py — SQLite database layer for Lazarus Protocol.

Provides:
- SQLite database management with ACID guarantees
- Connection pooling for thread safety
- Transaction support
- Data validation and constraints
- Backup and recovery strategy
- Migration support

Replaces file-based JSON storage with proper database layer.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator

from core.config import (
    LazarusConfig,
    BeneficiaryConfig,
    VaultConfig,
    StorageProviderConfig,
    _config_to_dict,
    _config_from_dict,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = Path.home() / ".lazarus" / "lazarus.db"
DEFAULT_BACKUP_INTERVAL = 3600  # 1 hour
DEFAULT_MAX_BACKUPS = 10


# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------

@dataclass
class DatabaseConfig:
    """Configuration for database manager"""
    path: Path = DEFAULT_DB_PATH
    backup_interval: int = DEFAULT_BACKUP_INTERVAL
    max_backups: int = DEFAULT_MAX_BACKUPS
    enable_wal_mode: bool = True  # Write-Ahead Logging for better concurrency
    enable_foreign_keys: bool = True  # Foreign key constraints


# ---------------------------------------------------------------------------
# Database Manager
# ---------------------------------------------------------------------------

class DatabaseManager:
    """
    SQLite database manager with ACID guarantees and thread safety.
    
    This class provides:
    - Thread-safe connection pooling
    - ACID transaction support
    - Automatic schema management
    - Backup and recovery
    - Data validation
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager.
        
        Args:
            config: Database configuration (uses defaults if not provided)
        """
        self.config = config or DatabaseConfig()
        self._connection_pool: Dict[int, sqlite3.Connection] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("lazarus.database")
        
        # Ensure database directory exists
        self.config.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._ensure_schema()
        
        self._logger.info(f"Database initialized: {self.config.path}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection from pool.
        
        Yields:
            SQLite connection with row factory enabled
        """
        thread_id = threading.current_thread().ident
        
        with self._lock:
            if thread_id not in self._connection_pool:
                self._connection_pool[thread_id] = self._create_connection()
            
            conn = self._connection_pool[thread_id]
        
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings"""
        conn = sqlite3.connect(
            self.config.path,
            check_same_thread=False,
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        if self.config.enable_wal_mode:
            conn.execute("PRAGMA journal_mode=WAL")
        
        # Enable foreign key constraints
        if self.config.enable_foreign_keys:
            conn.execute("PRAGMA foreign_keys=ON")
        
        # Set busy timeout for concurrent access
        conn.execute("PRAGMA busy_timeout=5000")
        
        return conn

    def _ensure_schema(self) -> None:
        """Ensure database schema exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    owner_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    owner_email TEXT NOT NULL,
                    beneficiary_name TEXT NOT NULL,
                    beneficiary_email TEXT NOT NULL,
                    beneficiary_public_key_path TEXT NOT NULL,
                    check_in_interval_days INTEGER NOT NULL,
                    last_checkin_timestamp TIMESTAMP,
                    deadline_timestamp TIMESTAMP,
                    armed BOOLEAN DEFAULT 1,
                    telegram_chat_id TEXT,
                    license_key TEXT,
                    subscription_tier TEXT DEFAULT 'free',
                    wallet_limit INTEGER DEFAULT 1,
                    license_valid_until TIMESTAMP,
                    storage_config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Vault metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vaults (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id INTEGER NOT NULL,
                    secret_file_path TEXT NOT NULL,
                    encrypted_file_path TEXT NOT NULL,
                    key_blob TEXT NOT NULL,
                    ipfs_cid TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
                )
            """)
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
                )
            """)
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    configuration_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    storage_provider TEXT NOT NULL,
                    cid TEXT,
                    encrypted_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
                )
            """)
            
            # Rate limits table (for persistence)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    request_count INTEGER NOT NULL,
                    window_start TIMESTAMP NOT NULL,
                    backoff_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identifier, window_start)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_config ON events(configuration_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_config ON documents(configuration_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_configurations_user ON configurations(user_id)")
            
            conn.commit()
            
            self._logger.info("Database schema ensured")

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Execute operations in a transaction.
        
        Yields:
            SQLite connection with transaction context
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # ---------------------------------------------------------------------------
    # User Operations
    # ---------------------------------------------------------------------------

    def create_user(self, email: str, api_key: str, owner_name: str) -> int:
        """
        Create new user.
        
        Args:
            email: User email address
            api_key: API key for authentication
            owner_name: Owner's name
            
        Returns:
            User ID
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (email, api_key, owner_name)
                VALUES (?, ?, ?)
                """,
                (email, api_key, owner_name)
            )
            user_id = cursor.lastrowid
            self._logger.info(f"Created user: {email} (ID: {user_id})")
            return user_id

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User data or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Get user by API key.
        
        Args:
            api_key: API key
            
        Returns:
            User data or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE api_key = ?",
                (api_key,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update user information.
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['email', 'api_key', 'owner_name']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(user_id)
            
            cursor.execute(
                f"UPDATE users SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            
            success = cursor.rowcount > 0
            if success:
                self._logger.info(f"Updated user: {user_id}")
            return success

    # ---------------------------------------------------------------------------
    # Configuration Operations
    # ---------------------------------------------------------------------------

    def create_configuration(self, user_id: int, config: LazarusConfig) -> int:
        """
        Create configuration for user.
        
        Args:
            user_id: User ID
            config: Lazarus configuration object
            
        Returns:
            Configuration ID
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # Serialize storage config
            storage_config_json = json.dumps(asdict(config.storage_config)) if config.storage_config else None
            
            cursor.execute(
                """
                INSERT INTO configurations (
                    user_id, owner_email, beneficiary_name, beneficiary_email,
                    beneficiary_public_key_path, check_in_interval_days,
                    last_checkin_timestamp, armed, telegram_chat_id,
                    license_key, subscription_tier, wallet_limit,
                    license_valid_until, storage_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    config.owner_email,
                    config.beneficiary.name,
                    config.beneficiary.email,
                    config.beneficiary.public_key_path,
                    config.checkin_interval_days,
                    datetime.fromtimestamp(config.last_checkin_timestamp) if config.last_checkin_timestamp else None,
                    config.armed,
                    config.telegram_chat_id,
                    config.license_key,
                    config.subscription_tier,
                    config.wallet_limit,
                    datetime.fromtimestamp(config.license_valid_until) if config.license_valid_until else None,
                    storage_config_json
                )
            )
            
            config_id = cursor.lastrowid
            
            # Create vault entry
            cursor.execute(
                """
                INSERT INTO vaults (
                    configuration_id, secret_file_path, encrypted_file_path,
                    key_blob, ipfs_cid
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    config_id,
                    config.vault.secret_file_path,
                    config.vault.encrypted_file_path,
                    config.vault.key_blob,
                    config.vault.ipfs_cid
                )
            )
            
            self._logger.info(f"Created configuration: {config_id} for user: {user_id}")
            return config_id

    def get_configuration(self, config_id: int) -> Optional[LazarusConfig]:
        """
        Get configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            LazarusConfig object or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get configuration
            cursor.execute(
                """
                SELECT * FROM configurations WHERE id = ?
                """,
                (config_id,)
            )
            config_row = cursor.fetchone()
            
            if not config_row:
                return None
            
            # Get vault
            cursor.execute(
                """
                SELECT * FROM vaults WHERE configuration_id = ?
                """,
                (config_id,)
            )
            vault_row = cursor.fetchone()
            
            # Reconstruct configuration
            config_dict = dict(config_row)
            
            # Parse storage config
            storage_config = None
            if config_dict['storage_config']:
                storage_config = StorageProviderConfig(**json.loads(config_dict['storage_config']))
            
            # Parse vault
            vault = VaultConfig(
                secret_file_path=vault_row['secret_file_path'],
                encrypted_file_path=vault_row['encrypted_file_path'],
                key_blob=vault_row['key_blob'],
                ipfs_cid=vault_row['ipfs_cid']
            )
            
            # Parse beneficiary
            beneficiary = BeneficiaryConfig(
                name=config_dict['beneficiary_name'],
                email=config_dict['beneficiary_email'],
                public_key_path=config_dict['beneficiary_public_key_path']
            )
            
            # Convert timestamps
            last_checkin = config_dict['last_checkin_timestamp']
            if last_checkin:
                last_checkin = last_checkin.timestamp()
            
            license_valid = config_dict['license_valid_until']
            if license_valid:
                license_valid = license_valid.timestamp()
            
            return LazarusConfig(
                owner_name=config_dict['owner_email'],  # Using email as name for now
                owner_email=config_dict['owner_email'],
                beneficiary=beneficiary,
                vault=vault,
                checkin_interval_days=config_dict['check_in_interval_days'],
                last_checkin_timestamp=last_checkin,
                telegram_chat_id=config_dict['telegram_chat_id'],
                armed=bool(config_dict['armed']),
                storage_config=storage_config,
                license_key=config_dict['license_key'],
                subscription_tier=config_dict['subscription_tier'],
                wallet_limit=config_dict['wallet_limit'],
                license_valid_until=license_valid
            )

    def update_configuration(self, config_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update configuration.
        
        Args:
            config_id: Configuration ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['owner_email', 'beneficiary_name', 'beneficiary_email',
                          'beneficiary_public_key_path', 'check_in_interval_days',
                          'armed', 'telegram_chat_id', 'license_key',
                          'subscription_tier', 'wallet_limit']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
                elif key == 'last_checkin_timestamp':
                    set_clauses.append("last_checkin_timestamp = ?")
                    values.append(datetime.fromtimestamp(value))
                elif key == 'license_valid_until':
                    set_clauses.append("license_valid_until = ?")
                    values.append(datetime.fromtimestamp(value))
                elif key == 'storage_config' and value is not None:
                    set_clauses.append("storage_config = ?")
                    values.append(json.dumps(asdict(value)))
            
            if not set_clauses:
                return False
            
            values.append(config_id)
            
            cursor.execute(
                f"UPDATE configurations SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            
            success = cursor.rowcount > 0
            if success:
                self._logger.info(f"Updated configuration: {config_id}")
            return success

    def get_user_configurations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all configurations for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of configuration dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, owner_email, beneficiary_name, beneficiary_email,
                       check_in_interval_days, last_checkin_timestamp,
                       deadline_timestamp, armed, created_at, updated_at
                FROM configurations
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ---------------------------------------------------------------------------
    # Event Operations
    # ---------------------------------------------------------------------------

    def log_event(self, configuration_id: int, event_type: str, content: str) -> int:
        """
        Log event for configuration.
        
        Args:
            configuration_id: Configuration ID
            event_type: Type of event
            content: Event content
            
        Returns:
            Event ID
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (configuration_id, event_type, content)
                VALUES (?, ?, ?)
                """,
                (configuration_id, event_type, content)
            )
            event_id = cursor.lastrowid
            self._logger.debug(f"Logged event: {event_type} for config: {configuration_id}")
            return event_id

    def get_events(self, configuration_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events for configuration.
        
        Args:
            configuration_id: Configuration ID
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM events
                WHERE configuration_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (configuration_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ---------------------------------------------------------------------------
    # Document Operations
    # ---------------------------------------------------------------------------

    def add_document(self, configuration_id: int, document: Dict[str, Any]) -> int:
        """
        Add document to configuration.
        
        Args:
            configuration_id: Configuration ID
            document: Document dictionary
            
        Returns:
            Document ID
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO documents (
                    configuration_id, filename, file_type, file_size,
                    storage_provider, cid, encrypted_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    configuration_id,
                    document['filename'],
                    document['file_type'],
                    document['file_size'],
                    document['storage_provider'],
                    document.get('cid'),
                    document['encrypted_path']
                )
            )
            doc_id = cursor.lastrowid
            self._logger.info(f"Added document: {document['filename']} to config: {configuration_id}")
            return doc_id

    def get_documents(self, configuration_id: int) -> List[Dict[str, Any]]:
        """
        Get documents for configuration.
        
        Args:
            configuration_id: Configuration ID
            
        Returns:
            List of document dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM documents
                WHERE configuration_id = ?
                ORDER BY created_at DESC
                """,
                (configuration_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def remove_document(self, document_id: int) -> bool:
        """
        Remove document.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,)
            )
            success = cursor.rowcount > 0
            if success:
                self._logger.info(f"Removed document: {document_id}")
            return success

    # ---------------------------------------------------------------------------
    # Backup and Recovery
    # ---------------------------------------------------------------------------

    def backup(self) -> Path:
        """
        Create database backup.
        
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config.path.parent / f"backup_{timestamp}.db"
        
        # Close all connections before backup
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
        
        # Copy database file
        shutil.copy2(self.config.path, backup_path)
        
        # Clean up old backups
        self._cleanup_old_backups()
        
        self._logger.info(f"Created backup: {backup_path}")
        return backup_path

    def _cleanup_old_backups(self) -> None:
        """Remove old backups exceeding max_backups"""
        backups = sorted(
            self.config.path.parent.glob("backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for backup in backups[self.config.max_backups:]:
            backup.unlink()
            self._logger.debug(f"Removed old backup: {backup}")

    def restore(self, backup_path: Path) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        if not backup_path.exists():
            self._logger.error(f"Backup file not found: {backup_path}")
            return False
        
        # Close all connections
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
        
        # Restore from backup
        shutil.copy2(backup_path, self.config.path)
        
        self._logger.info(f"Restored from backup: {backup_path}")
        return True

    # ---------------------------------------------------------------------------
    # Statistics and Maintenance
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {
                "database_size": self.config.path.stat().st_size,
                "database_path": str(self.config.path),
                "tables": {}
            }
            
            # Get table counts
            tables = ['users', 'configurations', 'vaults', 'events', 'documents', 'rate_limits']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats["tables"][table] = cursor.fetchone()[0]
            
            return stats

    def vacuum(self) -> None:
        """Run VACUUM to optimize database"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
            self._logger.info("Database VACUUM completed")

    def analyze(self) -> None:
        """Run ANALYZE to update statistics"""
        with self.get_connection() as conn:
            conn.execute("ANALYZE")
            conn.commit()
            self._logger.info("Database ANALYZE completed")

    # ---------------------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------------------

    def close(self) -> None:
        """Close all connections"""
        with self._lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
            self._logger.info("Database connections closed")

    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# ---------------------------------------------------------------------------
# Global Database Manager
# ---------------------------------------------------------------------------

_database_manager: Optional[DatabaseManager] = None


def get_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """
    Get or create global database manager instance.
    
    Args:
        config: Database configuration (optional)
        
    Returns:
        DatabaseManager instance
    """
    global _database_manager
    
    if _database_manager is None:
        _database_manager = DatabaseManager(config)
    
    return _database_manager
