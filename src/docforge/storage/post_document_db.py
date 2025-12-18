"""Post Document Database for storing processed documents with multiple versions."""

import logging
import sqlite3
import json
import hashlib
import gzip
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timezone, timedelta
from pathlib import Path
from contextlib import contextmanager

from .schemas import (
    PostDocumentRecord,
    ProcessingVersionRecord,
    ChunkStorageRecord,
    DocumentMetadata,
    StorageConfig,
    QueryFilter,
    StorageStats,
    ProcessingStatus
)
from docforge.postprocessing.schemas import ChunkData

logger = logging.getLogger(__name__)


class PostDocumentDatabase:
    """Database for storing processed documents with multiple processing versions."""
    
    def __init__(self, config: StorageConfig):
        """Initialize the post document database."""
        self.config = config
        self.db_path = self._parse_database_url(config.database_url)
        self._init_database()
    
    def _parse_database_url(self, url: str) -> str:
        """Parse database URL to get file path."""
        if url.startswith('sqlite:///'):
            return url[10:]  # Remove 'sqlite:///'
        elif url.startswith('sqlite://'):
            return url[9:]   # Remove 'sqlite://'
        else:
            return url
    
    def _init_database(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            # Create documents table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    doc_uuid TEXT PRIMARY KEY,
                    file_uuid TEXT NOT NULL,
                    source_file_path TEXT NOT NULL,
                    source_file_hash TEXT NOT NULL,
                    metadata TEXT,  -- JSON
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    accessed_at TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_indexed BOOLEAN DEFAULT 0,
                    is_compressed BOOLEAN DEFAULT 0,
                    is_encrypted BOOLEAN DEFAULT 0,
                    parent_doc_uuid TEXT,
                    child_doc_uuids TEXT,  -- JSON array
                    related_doc_uuids TEXT  -- JSON array
                )
            ''')
            
            # Create processing_versions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processing_versions (
                    version_id TEXT PRIMARY KEY,
                    doc_uuid TEXT NOT NULL,
                    set_uuid TEXT NOT NULL,
                    processing_method TEXT NOT NULL,
                    processing_config TEXT,  -- JSON
                    processor_version TEXT NOT NULL,
                    processing_timestamp TEXT NOT NULL,
                    processing_duration REAL NOT NULL,
                    status TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    warnings TEXT,  -- JSON array
                    chunks_storage_path TEXT,
                    embeddings_storage_path TEXT,
                    vector_index_id TEXT,
                    FOREIGN KEY (doc_uuid) REFERENCES documents (doc_uuid)
                )
            ''')
            
            # Create chunks table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_uuid TEXT NOT NULL,
                    set_uuid TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    word_count INTEGER DEFAULT 0,
                    character_count INTEGER DEFAULT 0,
                    language TEXT,
                    confidence_score REAL DEFAULT 1.0,
                    source_elements TEXT,  -- JSON array
                    page_numbers TEXT,  -- JSON array
                    position_metadata TEXT,  -- JSON
                    relationships TEXT,  -- JSON
                    created_at TEXT NOT NULL,
                    embedding_vector TEXT,  -- JSON array of floats
                    vector_index_id TEXT,
                    FOREIGN KEY (doc_uuid) REFERENCES documents (doc_uuid),
                    FOREIGN KEY (version_id) REFERENCES processing_versions (version_id)
                )
            ''')
            
            # Create indexes for efficient querying
            self._create_indexes(conn)
            
            conn.commit()
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """Create database indexes for efficient querying."""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_documents_file_uuid ON documents (file_uuid)',
            'CREATE INDEX IF NOT EXISTS idx_documents_source_hash ON documents (source_file_hash)',
            'CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at)',
            'CREATE INDEX IF NOT EXISTS idx_documents_is_active ON documents (is_active)',
            
            'CREATE INDEX IF NOT EXISTS idx_versions_doc_uuid ON processing_versions (doc_uuid)',
            'CREATE INDEX IF NOT EXISTS idx_versions_set_uuid ON processing_versions (set_uuid)',
            'CREATE INDEX IF NOT EXISTS idx_versions_method ON processing_versions (processing_method)',
            'CREATE INDEX IF NOT EXISTS idx_versions_status ON processing_versions (status)',
            'CREATE INDEX IF NOT EXISTS idx_versions_timestamp ON processing_versions (processing_timestamp)',
            
            'CREATE INDEX IF NOT EXISTS idx_chunks_doc_uuid ON chunks (doc_uuid)',
            'CREATE INDEX IF NOT EXISTS idx_chunks_set_uuid ON chunks (set_uuid)',
            'CREATE INDEX IF NOT EXISTS idx_chunks_version_id ON chunks (version_id)',
            'CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks (chunk_type)',
            'CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks (content_hash)',
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            # Ensure directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.config.connection_timeout,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _compress_content(self, content: str) -> bytes:
        """Compress content if compression is enabled."""
        if self.config.enable_compression:
            return gzip.compress(content.encode('utf-8'))
        return content.encode('utf-8')
    
    def _decompress_content(self, data: bytes, is_compressed: bool) -> str:
        """Decompress content if it was compressed."""
        if is_compressed:
            return gzip.decompress(data).decode('utf-8')
        return data.decode('utf-8')
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def store_document(
        self,
        file_uuid: str,
        source_file_path: str,
        source_content: str,
        metadata: Optional[DocumentMetadata] = None
    ) -> str:
        """Store a new document record."""
        doc_record = PostDocumentRecord(
            doc_uuid=file_uuid,  # Use file_uuid as doc_uuid for consistency
            file_uuid=file_uuid,
            source_file_path=source_file_path,
            source_file_hash=self._calculate_hash(source_content),
            metadata=metadata or DocumentMetadata()
        )
        
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO documents (
                    doc_uuid, file_uuid, source_file_path, source_file_hash,
                    metadata, created_at, updated_at, accessed_at,
                    is_active, is_indexed, is_compressed, is_encrypted,
                    parent_doc_uuid, child_doc_uuids, related_doc_uuids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_record.doc_uuid,
                doc_record.file_uuid,
                doc_record.source_file_path,
                doc_record.source_file_hash,
                doc_record.metadata.model_dump_json(),
                doc_record.created_at.isoformat(),
                doc_record.updated_at.isoformat(),
                doc_record.accessed_at.isoformat() if doc_record.accessed_at else None,
                doc_record.is_active,
                doc_record.is_indexed,
                doc_record.is_compressed,
                doc_record.is_encrypted,
                doc_record.parent_doc_uuid,
                json.dumps(doc_record.child_doc_uuids),
                json.dumps(doc_record.related_doc_uuids)
            ))
            conn.commit()
        
        logger.info(f"Stored document {doc_record.doc_uuid} for file {file_uuid}")
        return doc_record.doc_uuid
    
    def add_processing_version(
        self,
        doc_uuid: str,
        set_uuid: str,
        processing_method: str,
        processing_config: Dict[str, Any],
        processor_version: str,
        processing_duration: float,
        chunks: List[ChunkData],
        status: ProcessingStatus = ProcessingStatus.COMPLETED,
        error_message: Optional[str] = None,
        warnings: List[str] = None
    ) -> str:
        """Add a processing version to a document."""
        version_record = ProcessingVersionRecord(
            set_uuid=set_uuid,
            processing_method=processing_method,
            processing_config=processing_config,
            processor_version=processor_version,
            processing_duration=processing_duration,
            status=status,
            chunk_count=len(chunks),
            error_message=error_message,
            warnings=warnings or []
        )
        
        with self._get_connection() as conn:
            # Insert processing version
            conn.execute('''
                INSERT INTO processing_versions (
                    version_id, doc_uuid, set_uuid, processing_method,
                    processing_config, processor_version, processing_timestamp,
                    processing_duration, status, chunk_count, error_message,
                    warnings, chunks_storage_path, embeddings_storage_path,
                    vector_index_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version_record.version_id,
                doc_uuid,
                version_record.set_uuid,
                version_record.processing_method,
                json.dumps(version_record.processing_config),
                version_record.processor_version,
                version_record.processing_timestamp.isoformat(),
                version_record.processing_duration,
                version_record.status.value if hasattr(version_record.status, 'value') else version_record.status,
                version_record.chunk_count,
                version_record.error_message,
                json.dumps(version_record.warnings),
                version_record.chunks_storage_path,
                version_record.embeddings_storage_path,
                version_record.vector_index_id
            ))
            
            # Store chunks
            for chunk in chunks:
                chunk_record = ChunkStorageRecord(
                    chunk_id=chunk.chunk_id,
                    doc_uuid=doc_uuid,
                    set_uuid=set_uuid,
                    version_id=version_record.version_id,
                    content=chunk.content,
                    content_hash=self._calculate_hash(chunk.content),
                    chunk_type=chunk.chunk_type.value,
                    chunk_index=chunk.metadata.chunk_index,
                    word_count=chunk.metadata.word_count,
                    character_count=chunk.metadata.character_count,
                    language=chunk.metadata.language,
                    confidence_score=chunk.metadata.confidence_score,
                    source_elements=chunk.metadata.source_elements,
                    page_numbers=chunk.metadata.page_numbers,
                    position_metadata=chunk.position,
                    relationships=chunk.relationships
                )
                
                conn.execute('''
                    INSERT INTO chunks (
                        chunk_id, doc_uuid, set_uuid, version_id, content,
                        content_hash, chunk_type, chunk_index, word_count,
                        character_count, language, confidence_score,
                        source_elements, page_numbers, position_metadata,
                        relationships, created_at, embedding_vector, vector_index_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_record.chunk_id,
                    chunk_record.doc_uuid,
                    chunk_record.set_uuid,
                    chunk_record.version_id,
                    chunk_record.content,
                    chunk_record.content_hash,
                    chunk_record.chunk_type,
                    chunk_record.chunk_index,
                    chunk_record.word_count,
                    chunk_record.character_count,
                    chunk_record.language,
                    chunk_record.confidence_score,
                    json.dumps(chunk_record.source_elements),
                    json.dumps(chunk_record.page_numbers),
                    json.dumps(chunk_record.position_metadata),
                    json.dumps(chunk_record.relationships),
                    chunk_record.created_at.isoformat(),
                    json.dumps(chunk_record.embedding_vector) if chunk_record.embedding_vector else None,
                    chunk_record.vector_index_id
                ))
            
            # Update document updated_at timestamp
            conn.execute('''
                UPDATE documents SET updated_at = ? WHERE doc_uuid = ?
            ''', (datetime.now(timezone.utc).isoformat(), doc_uuid))
            
            conn.commit()
        
        logger.info(f"Added processing version {version_record.version_id} to document {doc_uuid}")
        return version_record.version_id
    
    def get_document(self, doc_uuid: str) -> Optional[PostDocumentRecord]:
        """Retrieve a document by UUID."""
        with self._get_connection() as conn:
            # Get document record
            doc_row = conn.execute('''
                SELECT * FROM documents WHERE doc_uuid = ?
            ''', (doc_uuid,)).fetchone()
            
            if not doc_row:
                return None
            
            # Get processing versions
            version_rows = conn.execute('''
                SELECT * FROM processing_versions WHERE doc_uuid = ?
                ORDER BY processing_timestamp DESC
            ''', (doc_uuid,)).fetchall()
            
            # Build document record
            doc_record = PostDocumentRecord(
                doc_uuid=doc_row['doc_uuid'],
                file_uuid=doc_row['file_uuid'],
                source_file_path=doc_row['source_file_path'],
                source_file_hash=doc_row['source_file_hash'],
                metadata=DocumentMetadata.model_validate_json(doc_row['metadata']),
                created_at=datetime.fromisoformat(doc_row['created_at']),
                updated_at=datetime.fromisoformat(doc_row['updated_at']),
                accessed_at=datetime.fromisoformat(doc_row['accessed_at']) if doc_row['accessed_at'] else None,
                is_active=bool(doc_row['is_active']),
                is_indexed=bool(doc_row['is_indexed']),
                is_compressed=bool(doc_row['is_compressed']),
                is_encrypted=bool(doc_row['is_encrypted']),
                parent_doc_uuid=doc_row['parent_doc_uuid'],
                child_doc_uuids=json.loads(doc_row['child_doc_uuids']),
                related_doc_uuids=json.loads(doc_row['related_doc_uuids'])
            )
            
            # Add processing versions
            for version_row in version_rows:
                version_record = ProcessingVersionRecord(
                    version_id=version_row['version_id'],
                    set_uuid=version_row['set_uuid'],
                    processing_method=version_row['processing_method'],
                    processing_config=json.loads(version_row['processing_config']) if version_row['processing_config'] else {},
                    processor_version=version_row['processor_version'],
                    processing_timestamp=datetime.fromisoformat(version_row['processing_timestamp']),
                    processing_duration=version_row['processing_duration'],
                    status=ProcessingStatus(version_row['status']),
                    chunk_count=version_row['chunk_count'],
                    error_message=version_row['error_message'],
                    warnings=json.loads(version_row['warnings']) if version_row['warnings'] else [],
                    chunks_storage_path=version_row['chunks_storage_path'],
                    embeddings_storage_path=version_row['embeddings_storage_path'],
                    vector_index_id=version_row['vector_index_id']
                )
                doc_record.processing_versions.append(version_record)
            
            # Update accessed timestamp
            conn.execute('''
                UPDATE documents SET accessed_at = ? WHERE doc_uuid = ?
            ''', (datetime.now(timezone.utc).isoformat(), doc_uuid))
            conn.commit()
            
            return doc_record
    
    def get_chunks(self, doc_uuid: str, set_uuid: Optional[str] = None) -> List[ChunkStorageRecord]:
        """Retrieve chunks for a document, optionally filtered by set UUID."""
        with self._get_connection() as conn:
            if set_uuid:
                chunk_rows = conn.execute('''
                    SELECT * FROM chunks WHERE doc_uuid = ? AND set_uuid = ?
                    ORDER BY chunk_index
                ''', (doc_uuid, set_uuid)).fetchall()
            else:
                chunk_rows = conn.execute('''
                    SELECT * FROM chunks WHERE doc_uuid = ?
                    ORDER BY set_uuid, chunk_index
                ''', (doc_uuid,)).fetchall()
            
            chunks = []
            for row in chunk_rows:
                chunk = ChunkStorageRecord(
                    chunk_id=row['chunk_id'],
                    doc_uuid=row['doc_uuid'],
                    set_uuid=row['set_uuid'],
                    version_id=row['version_id'],
                    content=row['content'],
                    content_hash=row['content_hash'],
                    chunk_type=row['chunk_type'],
                    chunk_index=row['chunk_index'],
                    word_count=row['word_count'],
                    character_count=row['character_count'],
                    language=row['language'],
                    confidence_score=row['confidence_score'],
                    source_elements=json.loads(row['source_elements']) if row['source_elements'] else [],
                    page_numbers=json.loads(row['page_numbers']) if row['page_numbers'] else [],
                    position_metadata=json.loads(row['position_metadata']) if row['position_metadata'] else {},
                    relationships=json.loads(row['relationships']) if row['relationships'] else {},
                    created_at=datetime.fromisoformat(row['created_at']),
                    embedding_vector=json.loads(row['embedding_vector']) if row['embedding_vector'] else None,
                    vector_index_id=row['vector_index_id']
                )
                chunks.append(chunk)
            
            return chunks
    
    def query_documents(self, filters: QueryFilter) -> List[PostDocumentRecord]:
        """Query documents with filters."""
        with self._get_connection() as conn:
            # Build query
            where_clauses = []
            params = []
            
            if filters.doc_uuids:
                placeholders = ','.join('?' * len(filters.doc_uuids))
                where_clauses.append(f'doc_uuid IN ({placeholders})')
                params.extend(filters.doc_uuids)
            
            if filters.file_uuids:
                placeholders = ','.join('?' * len(filters.file_uuids))
                where_clauses.append(f'file_uuid IN ({placeholders})')
                params.extend(filters.file_uuids)
            
            if filters.date_range:
                if 'start' in filters.date_range:
                    where_clauses.append('created_at >= ?')
                    params.append(filters.date_range['start'].isoformat())
                if 'end' in filters.date_range:
                    where_clauses.append('created_at <= ?')
                    params.append(filters.date_range['end'].isoformat())
            
            where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
            
            # Execute query
            doc_rows = conn.execute(f'''
                SELECT doc_uuid FROM documents WHERE {where_sql}
                ORDER BY created_at DESC
            ''', params).fetchall()
            
            # Get full document records
            documents = []
            for row in doc_rows:
                doc = self.get_document(row['doc_uuid'])
                if doc:
                    documents.append(doc)
            
            return documents
    
    def get_storage_stats(self) -> StorageStats:
        """Get storage statistics."""
        with self._get_connection() as conn:
            # Basic counts
            doc_count = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
            version_count = conn.execute('SELECT COUNT(*) FROM processing_versions').fetchone()[0]
            chunk_count = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
            
            # Status breakdown
            status_rows = conn.execute('''
                SELECT status, COUNT(*) as count FROM processing_versions
                GROUP BY status
            ''').fetchall()
            status_counts = {row['status']: row['count'] for row in status_rows}
            
            # Method breakdown
            method_rows = conn.execute('''
                SELECT processing_method, COUNT(*) as count FROM processing_versions
                GROUP BY processing_method
            ''').fetchall()
            method_counts = {row['processing_method']: row['count'] for row in method_rows}
            
            # Performance stats
            avg_processing_time = conn.execute('''
                SELECT AVG(processing_duration) FROM processing_versions
                WHERE status = 'completed'
            ''').fetchone()[0] or 0.0
            
            avg_chunk_count = conn.execute('''
                SELECT AVG(chunk_count) FROM processing_versions
                WHERE status = 'completed'
            ''').fetchone()[0] or 0.0
            
            return StorageStats(
                total_documents=doc_count,
                total_processing_versions=version_count,
                total_chunks=chunk_count,
                status_counts=status_counts,
                method_counts=method_counts,
                average_processing_time=avg_processing_time,
                average_chunk_count=avg_chunk_count
            )
    
    def delete_document(self, doc_uuid: str) -> bool:
        """Delete a document and all its associated data."""
        with self._get_connection() as conn:
            # Delete chunks first (foreign key constraint)
            conn.execute('DELETE FROM chunks WHERE doc_uuid = ?', (doc_uuid,))
            
            # Delete processing versions
            conn.execute('DELETE FROM processing_versions WHERE doc_uuid = ?', (doc_uuid,))
            
            # Delete document
            result = conn.execute('DELETE FROM documents WHERE doc_uuid = ?', (doc_uuid,))
            
            conn.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted document {doc_uuid}")
            
            return deleted
    
    def update_vector_references(self, version_id: str, vector_index_id: str, embeddings_path: Optional[str] = None):
        """Update vector storage references for a processing version."""
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE processing_versions 
                SET vector_index_id = ?, embeddings_storage_path = ?
                WHERE version_id = ?
            ''', (vector_index_id, embeddings_path, version_id))
            
            conn.commit()
            
        logger.info(f"Updated vector references for version {version_id}")
    
    def cleanup_old_documents(self, retention_days: int) -> int:
        """Clean up documents older than retention period."""
        if not retention_days:
            return 0
        
        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=retention_days)
        
        with self._get_connection() as conn:
            # Find old documents
            old_docs = conn.execute('''
                SELECT doc_uuid FROM documents 
                WHERE created_at < ? AND is_active = 1
            ''', (cutoff_date.isoformat(),)).fetchall()
            
            deleted_count = 0
            for row in old_docs:
                if self.delete_document(row['doc_uuid']):
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old documents")
            return deleted_count