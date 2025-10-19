"""Meta Document Database for final processed document components and RAG preparation."""

import logging
import sqlite3
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

from .schemas import ProcessingStatus

logger = logging.getLogger(__name__)


@dataclass
class MetaDocumentComponent:
    """Represents a component of a meta document."""
    component_id: str
    component_type: str  # 'chunk', 'summary', 'metadata', 'embedding'
    content: str
    metadata: Dict[str, Any]
    vector_embedding: Optional[List[float]] = None
    parent_component_id: Optional[str] = None
    order_index: int = 0
    confidence_score: float = 1.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class MetaDocumentRecord:
    """Complete meta document record."""
    meta_doc_uuid: str
    doc_uuid: str  # Reference to PostDocumentDatabase
    set_uuid: str  # Reference to specific processing version
    title: str
    summary: str
    components: List[MetaDocumentComponent]
    processing_history: List[Dict[str, Any]]
    rag_ready: bool = False
    vector_index_id: Optional[str] = None
    knowledge_graph_id: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


class MetaDocumentDatabase:
    """Database for storing final processed document components ready for RAG."""
    
    def __init__(self, db_path: str = "data/meta_document.db"):
        """Initialize the Meta Document Database."""
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
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables(self):
        """Create the necessary tables for meta document storage."""
        with self._get_connection() as conn:
            # Meta documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meta_doc_uuid TEXT UNIQUE NOT NULL,
                    doc_uuid TEXT NOT NULL,
                    set_uuid TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    processing_history TEXT,  -- JSON
                    rag_ready BOOLEAN DEFAULT FALSE,
                    vector_index_id TEXT,
                    knowledge_graph_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Ensure unique combination of doc_uuid and set_uuid
                    UNIQUE(doc_uuid, set_uuid)
                )
            """)
            
            # Meta document components table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_document_components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT UNIQUE NOT NULL,
                    meta_doc_uuid TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,  -- JSON
                    vector_embedding TEXT,  -- JSON array of floats
                    parent_component_id TEXT,
                    order_index INTEGER DEFAULT 0,
                    confidence_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (meta_doc_uuid) REFERENCES meta_documents (meta_doc_uuid)
                        ON DELETE CASCADE,
                    FOREIGN KEY (parent_component_id) REFERENCES meta_document_components (component_id)
                        ON DELETE SET NULL
                )
            """)
            
            # RAG preparation status table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_preparation_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meta_doc_uuid TEXT NOT NULL,
                    preparation_stage TEXT NOT NULL,  -- 'embedding', 'indexing', 'graph_creation', 'completed'
                    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'failed'
                    progress_percentage REAL DEFAULT 0.0,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (meta_doc_uuid) REFERENCES meta_documents (meta_doc_uuid)
                        ON DELETE CASCADE,
                    UNIQUE(meta_doc_uuid, preparation_stage)
                )
            """)
            
            # Document relationships for knowledge graph
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_meta_doc_uuid TEXT NOT NULL,
                    target_meta_doc_uuid TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,  -- 'similar', 'references', 'follows', 'contradicts'
                    relationship_strength REAL DEFAULT 1.0,
                    metadata TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (source_meta_doc_uuid) REFERENCES meta_documents (meta_doc_uuid)
                        ON DELETE CASCADE,
                    FOREIGN KEY (target_meta_doc_uuid) REFERENCES meta_documents (meta_doc_uuid)
                        ON DELETE CASCADE,
                    UNIQUE(source_meta_doc_uuid, target_meta_doc_uuid, relationship_type)
                )
            """)
            
            conn.commit()
    
    def _create_indexes(self):
        """Create indexes for efficient querying."""
        with self._get_connection() as conn:
            # Meta documents indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_doc_uuid ON meta_documents (meta_doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_uuid ON meta_documents (doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_set_uuid ON meta_documents (set_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_ready ON meta_documents (rag_ready)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vector_index_id ON meta_documents (vector_index_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_created_at ON meta_documents (created_at)")
            
            # Components indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_component_id ON meta_document_components (component_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_component_meta_doc ON meta_document_components (meta_doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_component_type ON meta_document_components (component_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_component_parent ON meta_document_components (parent_component_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_component_order ON meta_document_components (order_index)")
            
            # RAG preparation indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_prep_meta_doc ON rag_preparation_status (meta_doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_prep_stage ON rag_preparation_status (preparation_stage)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_prep_status ON rag_preparation_status (status)")
            
            # Relationships indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON document_relationships (source_meta_doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON document_relationships (target_meta_doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON document_relationships (relationship_type)")
            
            conn.commit()
    
    def create_meta_document(
        self,
        doc_uuid: str,
        set_uuid: str,
        title: str,
        summary: str,
        components: List[MetaDocumentComponent],
        processing_history: List[Dict[str, Any]] = None
    ) -> str:
        """Create a new meta document."""
        meta_doc_uuid = str(uuid.uuid4())
        processing_history = processing_history or []
        
        with self._get_connection() as conn:
            # Insert meta document
            conn.execute("""
                INSERT INTO meta_documents (
                    meta_doc_uuid, doc_uuid, set_uuid, title, summary, processing_history
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                meta_doc_uuid,
                doc_uuid,
                set_uuid,
                title,
                summary,
                json.dumps(processing_history)
            ))
            
            # Insert components
            for component in components:
                self._insert_component(conn, meta_doc_uuid, component)
            
            conn.commit()
        
        logger.info(f"Created meta document {meta_doc_uuid} for doc {doc_uuid}, set {set_uuid}")
        return meta_doc_uuid
    
    def _insert_component(
        self,
        conn: sqlite3.Connection,
        meta_doc_uuid: str,
        component: MetaDocumentComponent
    ):
        """Insert a component into the database."""
        conn.execute("""
            INSERT INTO meta_document_components (
                component_id, meta_doc_uuid, component_type, content, metadata,
                vector_embedding, parent_component_id, order_index, confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            component.component_id,
            meta_doc_uuid,
            component.component_type,
            component.content,
            json.dumps(component.metadata),
            json.dumps(component.vector_embedding) if component.vector_embedding else None,
            component.parent_component_id,
            component.order_index,
            component.confidence_score
        ))
    
    def get_meta_document(self, meta_doc_uuid: str) -> Optional[MetaDocumentRecord]:
        """Get a meta document by UUID."""
        with self._get_connection() as conn:
            # Get meta document
            cursor = conn.execute("""
                SELECT * FROM meta_documents WHERE meta_doc_uuid = ?
            """, (meta_doc_uuid,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get components
            components_cursor = conn.execute("""
                SELECT * FROM meta_document_components 
                WHERE meta_doc_uuid = ?
                ORDER BY order_index, created_at
            """, (meta_doc_uuid,))
            
            components = []
            for comp_row in components_cursor.fetchall():
                component = MetaDocumentComponent(
                    component_id=comp_row['component_id'],
                    component_type=comp_row['component_type'],
                    content=comp_row['content'],
                    metadata=json.loads(comp_row['metadata']) if comp_row['metadata'] else {},
                    vector_embedding=json.loads(comp_row['vector_embedding']) if comp_row['vector_embedding'] else None,
                    parent_component_id=comp_row['parent_component_id'],
                    order_index=comp_row['order_index'],
                    confidence_score=comp_row['confidence_score'],
                    created_at=datetime.fromisoformat(comp_row['created_at'].replace('Z', '+00:00'))
                )
                components.append(component)
            
            # Create meta document record
            meta_doc = MetaDocumentRecord(
                meta_doc_uuid=row['meta_doc_uuid'],
                doc_uuid=row['doc_uuid'],
                set_uuid=row['set_uuid'],
                title=row['title'],
                summary=row['summary'],
                components=components,
                processing_history=json.loads(row['processing_history']) if row['processing_history'] else [],
                rag_ready=bool(row['rag_ready']),
                vector_index_id=row['vector_index_id'],
                knowledge_graph_id=row['knowledge_graph_id'],
                created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
            )
            
            return meta_doc
    
    def get_meta_documents_by_doc_uuid(self, doc_uuid: str) -> List[MetaDocumentRecord]:
        """Get all meta documents for a specific document UUID."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT meta_doc_uuid FROM meta_documents 
                WHERE doc_uuid = ?
                ORDER BY created_at DESC
            """, (doc_uuid,))
            
            meta_docs = []
            for row in cursor.fetchall():
                meta_doc = self.get_meta_document(row['meta_doc_uuid'])
                if meta_doc:
                    meta_docs.append(meta_doc)
            
            return meta_docs
    
    def get_meta_documents_by_set_uuid(self, set_uuid: str) -> List[MetaDocumentRecord]:
        """Get all meta documents for a specific processing set UUID."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT meta_doc_uuid FROM meta_documents 
                WHERE set_uuid = ?
                ORDER BY created_at DESC
            """, (set_uuid,))
            
            meta_docs = []
            for row in cursor.fetchall():
                meta_doc = self.get_meta_document(row['meta_doc_uuid'])
                if meta_doc:
                    meta_docs.append(meta_doc)
            
            return meta_docs
    
    def update_rag_ready_status(
        self,
        meta_doc_uuid: str,
        rag_ready: bool,
        vector_index_id: Optional[str] = None,
        knowledge_graph_id: Optional[str] = None
    ):
        """Update RAG ready status for a meta document."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE meta_documents 
                SET rag_ready = ?, vector_index_id = ?, knowledge_graph_id = ?, updated_at = ?
                WHERE meta_doc_uuid = ?
            """, (
                rag_ready,
                vector_index_id,
                knowledge_graph_id,
                datetime.now(timezone.utc).isoformat(),
                meta_doc_uuid
            ))
            conn.commit()
    
    def add_component(
        self,
        meta_doc_uuid: str,
        component: MetaDocumentComponent
    ) -> str:
        """Add a component to an existing meta document."""
        with self._get_connection() as conn:
            self._insert_component(conn, meta_doc_uuid, component)
            
            # Update meta document timestamp
            conn.execute("""
                UPDATE meta_documents 
                SET updated_at = ?
                WHERE meta_doc_uuid = ?
            """, (datetime.now(timezone.utc).isoformat(), meta_doc_uuid))
            
            conn.commit()
        
        return component.component_id
    
    def update_component_embedding(
        self,
        component_id: str,
        vector_embedding: List[float]
    ):
        """Update the vector embedding for a component."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE meta_document_components 
                SET vector_embedding = ?
                WHERE component_id = ?
            """, (json.dumps(vector_embedding), component_id))
            conn.commit()
    
    def get_components_by_type(
        self,
        meta_doc_uuid: str,
        component_type: str
    ) -> List[MetaDocumentComponent]:
        """Get components of a specific type from a meta document."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM meta_document_components 
                WHERE meta_doc_uuid = ? AND component_type = ?
                ORDER BY order_index, created_at
            """, (meta_doc_uuid, component_type))
            
            components = []
            for row in cursor.fetchall():
                component = MetaDocumentComponent(
                    component_id=row['component_id'],
                    component_type=row['component_type'],
                    content=row['content'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    vector_embedding=json.loads(row['vector_embedding']) if row['vector_embedding'] else None,
                    parent_component_id=row['parent_component_id'],
                    order_index=row['order_index'],
                    confidence_score=row['confidence_score'],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
                )
                components.append(component)
            
            return components
    
    def update_rag_preparation_status(
        self,
        meta_doc_uuid: str,
        preparation_stage: str,
        status: str,
        progress_percentage: float = 0.0,
        error_message: Optional[str] = None
    ):
        """Update RAG preparation status for a specific stage."""
        with self._get_connection() as conn:
            # Update or insert preparation status
            conn.execute("""
                INSERT OR REPLACE INTO rag_preparation_status (
                    meta_doc_uuid, preparation_stage, status, progress_percentage, 
                    error_message, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                meta_doc_uuid,
                preparation_stage,
                status,
                progress_percentage,
                error_message,
                datetime.now(timezone.utc).isoformat() if status == 'in_progress' else None,
                datetime.now(timezone.utc).isoformat() if status == 'completed' else None
            ))
            conn.commit()
    
    def get_rag_preparation_status(self, meta_doc_uuid: str) -> Dict[str, Dict[str, Any]]:
        """Get RAG preparation status for all stages."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM rag_preparation_status 
                WHERE meta_doc_uuid = ?
                ORDER BY created_at
            """, (meta_doc_uuid,))
            
            status_dict = {}
            for row in cursor.fetchall():
                status_dict[row['preparation_stage']] = {
                    'status': row['status'],
                    'progress_percentage': row['progress_percentage'],
                    'error_message': row['error_message'],
                    'started_at': row['started_at'],
                    'completed_at': row['completed_at']
                }
            
            return status_dict
    
    def add_document_relationship(
        self,
        source_meta_doc_uuid: str,
        target_meta_doc_uuid: str,
        relationship_type: str,
        relationship_strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a relationship between two meta documents."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO document_relationships (
                    source_meta_doc_uuid, target_meta_doc_uuid, relationship_type,
                    relationship_strength, metadata
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                source_meta_doc_uuid,
                target_meta_doc_uuid,
                relationship_type,
                relationship_strength,
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()
    
    def get_document_relationships(
        self,
        meta_doc_uuid: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships for a meta document."""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM document_relationships 
                WHERE source_meta_doc_uuid = ? OR target_meta_doc_uuid = ?
            """
            params = [meta_doc_uuid, meta_doc_uuid]
            
            if relationship_type:
                query += " AND relationship_type = ?"
                params.append(relationship_type)
            
            query += " ORDER BY relationship_strength DESC"
            
            cursor = conn.execute(query, params)
            
            relationships = []
            for row in cursor.fetchall():
                relationships.append({
                    'source_meta_doc_uuid': row['source_meta_doc_uuid'],
                    'target_meta_doc_uuid': row['target_meta_doc_uuid'],
                    'relationship_type': row['relationship_type'],
                    'relationship_strength': row['relationship_strength'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at']
                })
            
            return relationships
    
    def get_rag_ready_documents(self, limit: Optional[int] = None) -> List[MetaDocumentRecord]:
        """Get all RAG-ready meta documents."""
        with self._get_connection() as conn:
            query = """
                SELECT meta_doc_uuid FROM meta_documents 
                WHERE rag_ready = TRUE
                ORDER BY updated_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            
            meta_docs = []
            for row in cursor.fetchall():
                meta_doc = self.get_meta_document(row['meta_doc_uuid'])
                if meta_doc:
                    meta_docs.append(meta_doc)
            
            return meta_docs
    
    def get_pending_rag_documents(self, limit: Optional[int] = None) -> List[MetaDocumentRecord]:
        """Get meta documents that are not yet RAG-ready."""
        with self._get_connection() as conn:
            query = """
                SELECT meta_doc_uuid FROM meta_documents 
                WHERE rag_ready = FALSE
                ORDER BY created_at ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            
            meta_docs = []
            for row in cursor.fetchall():
                meta_doc = self.get_meta_document(row['meta_doc_uuid'])
                if meta_doc:
                    meta_docs.append(meta_doc)
            
            return meta_docs
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics for the meta document database."""
        with self._get_connection() as conn:
            # Total meta documents
            cursor = conn.execute("SELECT COUNT(*) as total FROM meta_documents")
            total_docs = cursor.fetchone()['total']
            
            # RAG ready documents
            cursor = conn.execute("SELECT COUNT(*) as rag_ready FROM meta_documents WHERE rag_ready = TRUE")
            rag_ready_docs = cursor.fetchone()['rag_ready']
            
            # Components by type
            cursor = conn.execute("""
                SELECT component_type, COUNT(*) as count 
                FROM meta_document_components 
                GROUP BY component_type
            """)
            components_by_type = {row['component_type']: row['count'] for row in cursor.fetchall()}
            
            # Relationships count
            cursor = conn.execute("SELECT COUNT(*) as total FROM document_relationships")
            total_relationships = cursor.fetchone()['total']
            
            # RAG preparation stages
            cursor = conn.execute("""
                SELECT preparation_stage, status, COUNT(*) as count
                FROM rag_preparation_status
                GROUP BY preparation_stage, status
            """)
            rag_prep_status = {}
            for row in cursor.fetchall():
                stage = row['preparation_stage']
                if stage not in rag_prep_status:
                    rag_prep_status[stage] = {}
                rag_prep_status[stage][row['status']] = row['count']
            
            return {
                'total_meta_documents': total_docs,
                'rag_ready_documents': rag_ready_docs,
                'pending_rag_documents': total_docs - rag_ready_docs,
                'rag_ready_percentage': (rag_ready_docs / total_docs * 100) if total_docs > 0 else 0,
                'components_by_type': components_by_type,
                'total_relationships': total_relationships,
                'rag_preparation_status': rag_prep_status
            }
    
    def cleanup_old_documents(self, retention_days: int) -> int:
        """Clean up old meta documents based on retention policy."""
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM meta_documents 
                WHERE created_at < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Cleaned up {deleted_count} old meta documents")
        return deleted_count