"""Database migrations for versioning system."""

import logging
from typing import List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dbm.operations import get_db_operations

logger = logging.getLogger(__name__)


class VersioningMigrations:
    """Handles database migrations for the versioning system."""
    
    def __init__(self):
        self.db = get_db_operations()
    
    def get_current_schema_version(self) -> int:
        """Get the current schema version."""
        try:
            # Check if schema_version table exists
            results = self.db.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'",
                fetch=True
            )
            
            if not results:
                # Create schema_version table
                self.db.execute_query("""
                    CREATE TABLE schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """)
                
                # Insert initial version
                self.db.execute_query(
                    "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                    (0, "Initial schema")
                )
                return 0
            
            # Get latest version
            version_results = self.db.execute_query(
                "SELECT MAX(version) as version FROM schema_version",
                fetch=True
            )
            
            return version_results[0]['version'] if version_results else 0
            
        except Exception as e:
            logger.error(f"Error getting schema version: {e}")
            return 0
    
    def apply_migration(self, version: int, description: str, sql_commands: List[str]) -> bool:
        """Apply a migration."""
        try:
            logger.info(f"Applying migration {version}: {description}")
            
            # Execute all SQL commands
            for sql in sql_commands:
                self.db.execute_query(sql)
            
            # Record migration
            self.db.execute_query(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description)
            )
            
            logger.info(f"Successfully applied migration {version}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migration {version}: {e}")
            return False
    
    def migrate_to_latest(self) -> bool:
        """Migrate database to the latest schema version."""
        try:
            current_version = self.get_current_schema_version()
            logger.info(f"Current schema version: {current_version}")
            
            migrations = self._get_migrations()
            
            for version, description, sql_commands in migrations:
                if version > current_version:
                    success = self.apply_migration(version, description, sql_commands)
                    if not success:
                        logger.error(f"Failed to apply migration {version}")
                        return False
            
            final_version = self.get_current_schema_version()
            logger.info(f"Schema updated to version: {final_version}")
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False
    
    def _get_migrations(self) -> List[tuple]:
        """Get list of migrations to apply."""
        return [
            (1, "Add file_size and status columns to raw_document_register", [
                "ALTER TABLE raw_document_register ADD COLUMN file_size INTEGER DEFAULT 0",
                "ALTER TABLE raw_document_register ADD COLUMN status TEXT DEFAULT 'active'",
                "ALTER TABLE raw_document_register ADD COLUMN metadata TEXT DEFAULT '{}'",
                "UPDATE raw_document_register SET status = CASE WHEN is_deleted = 1 THEN 'deleted' ELSE 'active' END"
            ]),
            
            (2, "Create indexes for better performance", [
                "CREATE INDEX IF NOT EXISTS idx_raw_doc_lineage ON raw_document_register(lineage_uuid)",
                "CREATE INDEX IF NOT EXISTS idx_raw_doc_status ON raw_document_register(status)",
                "CREATE INDEX IF NOT EXISTS idx_raw_doc_hash ON raw_document_register(file_hash)",
                "CREATE INDEX IF NOT EXISTS idx_raw_doc_user ON raw_document_register(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_lineage_active ON document_lineage(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)"
            ]),
            
            (3, "Add audit log table for deletion tracking", [
                """CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,  -- JSON string
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)"
            ])
        ]
    
    def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        try:
            results = self.db.execute_query(
                f"PRAGMA table_info({table_name})",
                fetch=True
            )
            
            column_names = [row['name'] for row in results]
            return column_name in column_names
            
        except Exception as e:
            logger.error(f"Error checking column {column_name} in table {table_name}: {e}")
            return False
    
    def backup_table(self, table_name: str) -> bool:
        """Create a backup of a table before migration."""
        try:
            backup_name = f"{table_name}_backup_{int(datetime.utcnow().timestamp())}"
            
            self.db.execute_query(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
            
            logger.info(f"Created backup table: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup for table {table_name}: {e}")
            return False


def run_migrations() -> bool:
    """Run database migrations."""
    try:
        migrations = VersioningMigrations()
        return migrations.migrate_to_latest()
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False