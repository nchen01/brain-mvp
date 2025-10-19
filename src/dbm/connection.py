"""Basic database connection management for dummy DBM."""

import sqlite3
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DummyDBConnection:
    """Dummy database connection using SQLite for MVP."""
    
    def __init__(self, db_path: str = "./data/brain_mvp.db"):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._setup_database()
    
    def _setup_database(self) -> None:
        """Set up the database and create tables."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create connection and tables
        self.connect()
        self._create_tables()
    
    def connect(self) -> sqlite3.Connection:
        """Create database connection."""
        try:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row  # Enable dict-like access
            logger.info(f"Connected to database: {self.db_path}")
            return self._connection
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get current connection or create new one."""
        if not self._connection:
            self.connect()
        return self._connection
    
    def _create_tables(self) -> None:
        """Create necessary tables for the MVP."""
        cursor = self._connection.cursor()
        
        # Document Lineage Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_lineage (
                lineage_uuid TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_version INTEGER DEFAULT 1,
                total_versions INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Raw Document Register Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_document_register (
                doc_uuid TEXT PRIMARY KEY,
                lineage_uuid TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                parent_version INTEGER NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                labels TEXT,  -- JSON string for simplicity
                is_current BOOLEAN DEFAULT TRUE,
                status TEXT DEFAULT 'active',  -- active, deleted, archived
                deletion_reason TEXT NULL,
                edit_source_version INTEGER NULL,
                metadata TEXT,  -- JSON string for additional metadata
                FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid),
                UNIQUE(lineage_uuid, version_number)
            )
        """)
        
        # Post Document Register Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_document_register (
                doc_uuid TEXT NOT NULL,
                set_uuid TEXT NOT NULL,
                file_uuid TEXT PRIMARY KEY,
                lineage_uuid TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                processing_method TEXT NOT NULL,
                processing_version TEXT NOT NULL,
                metadata_record TEXT,  -- JSON string
                is_deleted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_uuid) REFERENCES raw_document_register (doc_uuid),
                FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid)
            )
        """)
        
        # Meta Document Register Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta_document_register (
                meta_file_uuid TEXT PRIMARY KEY,
                doc_uuid TEXT NOT NULL,
                lineage_uuid TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                component_type TEXT NOT NULL,
                metadata_record TEXT,  -- JSON string
                processing_status TEXT NOT NULL,
                chunking_strategy TEXT,
                post_processing_applied TEXT,  -- JSON string
                is_deleted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_uuid) REFERENCES raw_document_register (doc_uuid),
                FOREIGN KEY (lineage_uuid) REFERENCES document_lineage (lineage_uuid)
            )
        """)
        
        # Users table for dummy authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                roles TEXT,  -- JSON string
                permissions TEXT,  -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Sessions table for dummy session management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        self._connection.commit()
        logger.info("Database tables created successfully")


# Global connection instance
_db_connection: Optional[DummyDBConnection] = None


def get_db_connection() -> DummyDBConnection:
    """Get global database connection instance."""
    global _db_connection
    if not _db_connection:
        _db_connection = DummyDBConnection()
    return _db_connection