"""Post Document Register Table for tracking processed document metadata."""

import logging
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from .schemas import DocumentMetadata, ProcessingStatus

logger = logging.getLogger(__name__)


class PostDocumentRegister:
    """Register table for tracking processed document metadata and relationships."""
    
    def __init__(self, db_path: str = "data/post_document_register.db"):
        """Initialize the Post Document Register."""
        self.db_path = db_path
        self._ensure_database_exists()
        self._create_tables()
        self._create_indexes()
    
    def _ensure_database_exists(self):
        """Ensure the database directory exists."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.Connection(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def _create_tables(self):
        """Create the necessary tables for the document register."""
        with self._get_connection() as conn:
            # Main document register table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_register (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_uuid TEXT UNIQUE NOT NULL,
                    file_uuid TEXT NOT NULL,
                    source_file_path TEXT NOT NULL,
                    original_filename TEXT,
                    file_size_bytes INTEGER,
                    file_hash TEXT,
                    mime_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    
                    -- Document metadata
                    title TEXT,
                    author TEXT,
                    file_type TEXT,
                    page_count INTEGER,
                    word_count INTEGER,
                    language TEXT DEFAULT 'en',
                    
                    -- Processing status
                    processing_status TEXT DEFAULT 'pending',
                    last_processed_at TIMESTAMP,
                    processing_error TEXT,
                    
                    -- Custom metadata as JSON
                    custom_metadata TEXT,
                    
                    -- Indexing status
                    is_indexed BOOLEAN DEFAULT FALSE,
                    index_version TEXT,
                    indexed_at TIMESTAMP,
                    
                    -- Retention and cleanup
                    retention_policy TEXT,
                    expires_at TIMESTAMP
                )
            """)
            
            # Processing versions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id TEXT UNIQUE NOT NULL,
                    doc_uuid TEXT NOT NULL,
                    set_uuid TEXT NOT NULL,
                    processing_method TEXT NOT NULL,
                    processor_version TEXT NOT NULL,
                    processing_config TEXT,  -- JSON
                    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_duration REAL,
                    status TEXT DEFAULT 'pending',
                    chunk_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    warnings TEXT,  -- JSON array
                    
                    -- Vector storage references
                    vector_index_id TEXT,
                    embeddings_path TEXT,
                    
                    FOREIGN KEY (doc_uuid) REFERENCES document_register (doc_uuid)
                        ON DELETE CASCADE
                )
            """)
            
            # File relationships table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_file_uuid TEXT NOT NULL,
                    child_doc_uuid TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,  -- 'processed_from', 'derived_from', etc.
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,  -- JSON
                    
                    FOREIGN KEY (child_doc_uuid) REFERENCES document_register (doc_uuid)
                        ON DELETE CASCADE,
                    UNIQUE(parent_file_uuid, child_doc_uuid, relationship_type)
                )
            """)
            
            # Processing queue table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_uuid TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    requested_methods TEXT,  -- JSON array
                    requested_config TEXT,   -- JSON
                    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'queued',
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    
                    FOREIGN KEY (doc_uuid) REFERENCES document_register (doc_uuid)
                        ON DELETE CASCADE
                )
            """)
            
            conn.commit()
    
    def _create_indexes(self):
        """Create indexes for efficient querying."""
        with self._get_connection() as conn:
            # Primary lookup indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_uuid ON document_register (doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_uuid ON document_register (file_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_path ON document_register (source_file_path)")
            
            # Status and processing indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_status ON document_register (processing_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_is_indexed ON document_register (is_indexed)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON document_register (created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_processed ON document_register (last_processed_at)")
            
            # Processing versions indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_doc_uuid ON processing_versions (doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_set_uuid ON processing_versions (set_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_version_id ON processing_versions (version_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_status ON processing_versions (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_timestamp ON processing_versions (processing_timestamp)")
            
            # File relationships indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fr_parent ON file_relationships (parent_file_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fr_child ON file_relationships (child_doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fr_type ON file_relationships (relationship_type)")
            
            # Processing queue indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pq_doc_uuid ON processing_queue (doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pq_status ON processing_queue (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pq_priority ON processing_queue (priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pq_queued_at ON processing_queue (queued_at)")
            
            conn.commit()
    
    def register_document(
        self,
        doc_uuid: str,
        file_uuid: str,
        source_file_path: str,
        metadata: Optional[DocumentMetadata] = None,
        file_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new document in the register."""
        with self._get_connection() as conn:
            # Prepare document data
            doc_data = {
                'doc_uuid': doc_uuid,
                'file_uuid': file_uuid,
                'source_file_path': source_file_path,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add file information if provided
            if file_info:
                doc_data.update({
                    'original_filename': file_info.get('filename'),
                    'file_size_bytes': file_info.get('size'),
                    'file_hash': file_info.get('hash'),
                    'mime_type': file_info.get('mime_type')
                })
            
            # Add metadata if provided
            if metadata:
                doc_data.update({
                    'title': metadata.title,
                    'author': metadata.author,
                    'file_type': metadata.file_type,
                    'page_count': metadata.page_count,
                    'word_count': metadata.word_count,
                    'language': metadata.language,
                    'custom_metadata': json.dumps(metadata.custom_metadata) if metadata.custom_metadata else None
                })
            
            # Insert document
            columns = ', '.join(doc_data.keys())
            placeholders = ', '.join(['?' for _ in doc_data])
            
            conn.execute(
                f"INSERT OR REPLACE INTO document_register ({columns}) VALUES ({placeholders})",
                list(doc_data.values())
            )
            
            # Create file relationship
            conn.execute("""
                INSERT OR IGNORE INTO file_relationships 
                (parent_file_uuid, child_doc_uuid, relationship_type, created_at)
                VALUES (?, ?, 'processed_from', ?)
            """, (file_uuid, doc_uuid, datetime.now(timezone.utc).isoformat()))
            
            conn.commit()
            
        logger.info(f"Registered document {doc_uuid} from file {file_uuid}")
        return doc_uuid
    
    def get_document(self, doc_uuid: str) -> Optional[Dict[str, Any]]:
        """Get document information by UUID."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM document_register 
                WHERE doc_uuid = ? AND is_active = TRUE
            """, (doc_uuid,))
            
            row = cursor.fetchone()
            if row:
                doc = dict(row)
                # Parse JSON fields
                if doc['custom_metadata']:
                    doc['custom_metadata'] = json.loads(doc['custom_metadata'])
                return doc
            
        return None
    
    def get_documents_by_file_uuid(self, file_uuid: str) -> List[Dict[str, Any]]:
        """Get all documents processed from a specific file."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM document_register 
                WHERE file_uuid = ? AND is_active = TRUE
                ORDER BY created_at DESC
            """, (file_uuid,))
            
            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc['custom_metadata']:
                    doc['custom_metadata'] = json.loads(doc['custom_metadata'])
                documents.append(doc)
            
        return documents
    
    def update_processing_status(
        self,
        doc_uuid: str,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ):
        """Update the processing status of a document."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE document_register 
                SET processing_status = ?, 
                    processing_error = ?,
                    last_processed_at = ?,
                    updated_at = ?
                WHERE doc_uuid = ?
            """, (
                status.value,
                error_message,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                doc_uuid
            ))
            conn.commit()
    
    def add_processing_version(
        self,
        doc_uuid: str,
        set_uuid: str,
        processing_method: str,
        processor_version: str,
        processing_config: Optional[Dict[str, Any]] = None,
        processing_duration: Optional[float] = None,
        status: ProcessingStatus = ProcessingStatus.COMPLETED,
        chunk_count: int = 0,
        error_message: Optional[str] = None,
        warnings: Optional[List[str]] = None
    ) -> str:
        """Add a processing version record."""
        version_id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO processing_versions (
                    version_id, doc_uuid, set_uuid, processing_method,
                    processor_version, processing_config, processing_duration,
                    status, chunk_count, error_message, warnings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id,
                doc_uuid,
                set_uuid,
                processing_method,
                processor_version,
                json.dumps(processing_config) if processing_config else None,
                processing_duration,
                status.value,
                chunk_count,
                error_message,
                json.dumps(warnings) if warnings else None
            ))
            conn.commit()
        
        return version_id
    
    def get_processing_versions(self, doc_uuid: str) -> List[Dict[str, Any]]:
        """Get all processing versions for a document."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_versions 
                WHERE doc_uuid = ?
                ORDER BY processing_timestamp DESC
            """, (doc_uuid,))
            
            versions = []
            for row in cursor.fetchall():
                version = dict(row)
                # Parse JSON fields
                if version['processing_config']:
                    version['processing_config'] = json.loads(version['processing_config'])
                if version['warnings']:
                    version['warnings'] = json.loads(version['warnings'])
                versions.append(version)
            
        return versions
    
    def update_indexing_status(
        self,
        doc_uuid: str,
        is_indexed: bool,
        index_version: Optional[str] = None
    ):
        """Update the indexing status of a document."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE document_register 
                SET is_indexed = ?,
                    index_version = ?,
                    indexed_at = ?,
                    updated_at = ?
                WHERE doc_uuid = ?
            """, (
                is_indexed,
                index_version,
                datetime.now(timezone.utc).isoformat() if is_indexed else None,
                datetime.now(timezone.utc).isoformat(),
                doc_uuid
            ))
            conn.commit()
    
    def update_vector_references(
        self,
        version_id: str,
        vector_index_id: str,
        embeddings_path: Optional[str] = None
    ):
        """Update vector storage references for a processing version."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE processing_versions 
                SET vector_index_id = ?, embeddings_path = ?
                WHERE version_id = ?
            """, (vector_index_id, embeddings_path, version_id))
            conn.commit()
    
    def query_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> List[Dict[str, Any]]:
        """Query documents with filters."""
        query = "SELECT * FROM document_register WHERE is_active = TRUE"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == 'processing_status':
                    conditions.append("processing_status = ?")
                    params.append(value)
                elif key == 'file_type':
                    conditions.append("file_type = ?")
                    params.append(value)
                elif key == 'is_indexed':
                    conditions.append("is_indexed = ?")
                    params.append(value)
                elif key == 'language':
                    conditions.append("language = ?")
                    params.append(value)
                elif key == 'created_after':
                    conditions.append("created_at > ?")
                    params.append(value)
                elif key == 'created_before':
                    conditions.append("created_at < ?")
                    params.append(value)
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
        
        query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc['custom_metadata']:
                    doc['custom_metadata'] = json.loads(doc['custom_metadata'])
                documents.append(doc)
        
        return documents
    
    def get_unindexed_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get documents that haven't been indexed yet."""
        return self.query_documents(
            filters={'is_indexed': False},
            limit=limit,
            order_by="created_at ASC"
        )
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics from the register."""
        with self._get_connection() as conn:
            # Document counts by status
            cursor = conn.execute("""
                SELECT processing_status, COUNT(*) as count
                FROM document_register 
                WHERE is_active = TRUE
                GROUP BY processing_status
            """)
            status_counts = {row['processing_status']: row['count'] for row in cursor.fetchall()}
            
            # Total documents
            cursor = conn.execute("SELECT COUNT(*) as total FROM document_register WHERE is_active = TRUE")
            total_docs = cursor.fetchone()['total']
            
            # Indexed documents
            cursor = conn.execute("SELECT COUNT(*) as indexed FROM document_register WHERE is_indexed = TRUE AND is_active = TRUE")
            indexed_docs = cursor.fetchone()['indexed']
            
            # Processing versions count
            cursor = conn.execute("SELECT COUNT(*) as versions FROM processing_versions")
            total_versions = cursor.fetchone()['versions']
            
            # File types distribution
            cursor = conn.execute("""
                SELECT file_type, COUNT(*) as count
                FROM document_register 
                WHERE is_active = TRUE AND file_type IS NOT NULL
                GROUP BY file_type
            """)
            file_types = {row['file_type']: row['count'] for row in cursor.fetchall()}
            
            # Languages distribution
            cursor = conn.execute("""
                SELECT language, COUNT(*) as count
                FROM document_register 
                WHERE is_active = TRUE
                GROUP BY language
            """)
            languages = {row['language']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total_documents': total_docs,
            'indexed_documents': indexed_docs,
            'total_processing_versions': total_versions,
            'status_distribution': status_counts,
            'file_type_distribution': file_types,
            'language_distribution': languages,
            'indexing_rate': indexed_docs / total_docs if total_docs > 0 else 0
        }
    
    def cleanup_old_documents(self, retention_days: int) -> int:
        """Clean up old documents based on retention policy."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        with self._get_connection() as conn:
            # Mark documents as inactive instead of deleting
            cursor = conn.execute("""
                UPDATE document_register 
                SET is_active = FALSE, updated_at = ?
                WHERE created_at < ? AND (expires_at IS NULL OR expires_at < ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                cutoff_date.isoformat(),
                datetime.now(timezone.utc).isoformat()
            ))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Marked {deleted_count} documents as inactive during cleanup")
        return deleted_count
    
    def add_to_processing_queue(
        self,
        doc_uuid: str,
        requested_methods: List[str],
        requested_config: Optional[Dict[str, Any]] = None,
        priority: int = 5
    ) -> int:
        """Add a document to the processing queue."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO processing_queue (
                    doc_uuid, priority, requested_methods, requested_config
                ) VALUES (?, ?, ?, ?)
            """, (
                doc_uuid,
                priority,
                json.dumps(requested_methods),
                json.dumps(requested_config) if requested_config else None
            ))
            
            queue_id = cursor.lastrowid
            conn.commit()
        
        return queue_id
    
    def get_next_queued_document(self) -> Optional[Dict[str, Any]]:
        """Get the next document from the processing queue."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_queue 
                WHERE status = 'queued'
                ORDER BY priority DESC, queued_at ASC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                queue_item = dict(row)
                # Parse JSON fields
                if queue_item['requested_methods']:
                    queue_item['requested_methods'] = json.loads(queue_item['requested_methods'])
                if queue_item['requested_config']:
                    queue_item['requested_config'] = json.loads(queue_item['requested_config'])
                return queue_item
        
        return None
    
    def update_queue_status(
        self,
        queue_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update the status of a queue item."""
        with self._get_connection() as conn:
            update_fields = {'status': status}
            
            if status == 'processing':
                update_fields['started_at'] = datetime.now(timezone.utc).isoformat()
            elif status in ['completed', 'failed']:
                update_fields['completed_at'] = datetime.now(timezone.utc).isoformat()
                if error_message:
                    update_fields['error_message'] = error_message
            
            set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
            values = list(update_fields.values()) + [queue_id]
            
            conn.execute(f"UPDATE processing_queue SET {set_clause} WHERE id = ?", values)
            conn.commit()
    
    def get_document_relationships(self, doc_uuid: str) -> List[Dict[str, Any]]:
        """Get file relationships for a document."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM file_relationships 
                WHERE child_doc_uuid = ?
                ORDER BY created_at DESC
            """, (doc_uuid,))
            
            relationships = []
            for row in cursor.fetchall():
                rel = dict(row)
                if rel['metadata']:
                    rel['metadata'] = json.loads(rel['metadata'])
                relationships.append(rel)
            
        return relationships
    
    def deactivate_document(self, doc_uuid: str):
        """Deactivate a document (soft delete)."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE document_register 
                SET is_active = FALSE, updated_at = ?
                WHERE doc_uuid = ?
            """, (datetime.now(timezone.utc).isoformat(), doc_uuid))
            conn.commit()
        
        logger.info(f"Deactivated document {doc_uuid}")
    
    def reactivate_document(self, doc_uuid: str):
        """Reactivate a previously deactivated document."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE document_register 
                SET is_active = TRUE, updated_at = ?
                WHERE doc_uuid = ?
            """, (datetime.now(timezone.utc).isoformat(), doc_uuid))
            conn.commit()
        
        logger.info(f"Reactivated document {doc_uuid}")


# Import required for cleanup_old_documents
from datetime import timedelta