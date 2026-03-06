"""Chunk storage service for database operations.

Handles storing and retrieving document chunks with metadata.
"""

import logging
import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from utils.token_counter import get_token_counter

logger = logging.getLogger(__name__)


class ChunkStorage:
    """Service for storing and retrieving document chunks."""
    
    def __init__(self, db_path: str = "data/brain_mvp.db"):
        """Initialize chunk storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database()
        self._init_db()
        self.token_counter = get_token_counter()
    
    def _ensure_database(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_uuid TEXT NOT NULL,
                    lineage_uuid TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunking_strategy TEXT NOT NULL,
                    original_content TEXT NOT NULL,
                    enriched_content TEXT,
                    chunk_metadata TEXT NOT NULL, -- JSON
                    enrichment_metadata TEXT, -- JSON
                    chunk_relationships TEXT, -- JSON
                    embedding TEXT,            -- JSON float array (sentence-transformers)
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Migrate existing databases that predate the embedding column
            try:
                conn.execute("ALTER TABLE document_chunks ADD COLUMN embedding TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_uuid ON document_chunks(doc_uuid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_strategy ON document_chunks(chunking_strategy)")

            conn.commit()
        finally:
            conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def store_chunks(
        self,
        doc_uuid: str,
        lineage_uuid: str,
        version_number: int,
        chunks: List[Dict[str, Any]],
        chunking_strategy: str
    ) -> List[str]:
        """Store chunks for a document.
        
        Args:
            doc_uuid: Document UUID
            lineage_uuid: Document lineage UUID
            version_number: Document version number
            chunks: List of chunk dictionaries with content and metadata
            chunking_strategy: Strategy used ('recursive', 'fixed_size', 'semantic')
            
        Returns:
            List of created chunk_ids
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        chunk_ids = []
        
        try:
            for idx, chunk in enumerate(chunks):
                chunk_id = f"chunk_{doc_uuid}_{idx}"
                
                # Extract content
                original_content = chunk.get('content') or chunk.get('original_content') or ''
                enriched_content = chunk.get('enriched_content')
                
                # Prepare metadata
                metadata = dict(chunk.get('metadata', {}))
                if 'token_count' not in metadata:
                    metadata['token_count'] = self.token_counter.count(original_content)
                chunk_metadata = json.dumps(metadata)
                enrichment_metadata = json.dumps(chunk.get('enrichment_metadata', {}))
                chunk_relationships = json.dumps(chunk.get('relationships', {}))
                
                # Insert chunk
                cursor.execute("""
                    INSERT INTO document_chunks (
                        chunk_id, doc_uuid, lineage_uuid, version_number,
                        chunk_index, chunking_strategy,
                        original_content, enriched_content,
                        chunk_metadata, enrichment_metadata, chunk_relationships,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id, doc_uuid, lineage_uuid, version_number,
                    idx, chunking_strategy,
                    original_content, enriched_content,
                    chunk_metadata, enrichment_metadata, chunk_relationships,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                
                chunk_ids.append(chunk_id)
            
            conn.commit()
            logger.info(f"Stored {len(chunk_ids)} chunks for document {doc_uuid}")
            return chunk_ids
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error storing chunks: {e}")
            raise
        finally:
            conn.close()
    
    def _row_to_chunk_dict(
        self,
        row: sqlite3.Row,
        include_enriched: bool = True
    ) -> Dict[str, Any]:
        """Convert a database row into an API-friendly chunk dictionary."""
        metadata = json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {}
        enrichment_metadata = json.loads(row['enrichment_metadata']) if row['enrichment_metadata'] else {}
        relationships = json.loads(row['chunk_relationships']) if row['chunk_relationships'] else {}
        chunk_type = metadata.get('chunk_type', 'unknown')
        token_count = metadata.get('token_count')
        if token_count is None:
            token_count = self.token_counter.count(row['original_content'])
            metadata['token_count'] = token_count
        
        chunk = {
            'chunk_id': row['chunk_id'],
            'doc_uuid': row['doc_uuid'],
            'lineage_uuid': row['lineage_uuid'],
            'version_number': row['version_number'],
            'chunk_index': row['chunk_index'],
            'chunking_strategy': row['chunking_strategy'],
            # Provide both original_content and a content alias for UI/API consumers
            'original_content': row['original_content'],
            'content': row['original_content'],
            'metadata': metadata,
            'relationships': relationships,
            'chunk_type': chunk_type,
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'token_count': token_count
        }
        
        if include_enriched and row['enriched_content']:
            chunk['enriched_content'] = row['enriched_content']
            chunk['content'] = row['enriched_content']
            if enrichment_metadata:
                chunk['enrichment_metadata'] = enrichment_metadata
        
        return chunk
    
    def get_chunks_by_document(
        self,
        doc_uuid: str,
        include_enriched: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a document.
        
        Args:
            doc_uuid: Document UUID
            include_enriched: Whether to include enriched content (default: True)
            
        Returns:
            List of chunk dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM document_chunks
                WHERE doc_uuid = ?
                ORDER BY chunk_index
            """, (doc_uuid,))
            
            rows = cursor.fetchall()
            chunks = [self._row_to_chunk_dict(row, include_enriched) for row in rows]
            
            logger.debug(f"Retrieved {len(chunks)} chunks for document {doc_uuid}")
            return chunks
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
        finally:
            conn.close()
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific chunk by ID.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk dictionary or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM document_chunks
                WHERE chunk_id = ?
            """, (chunk_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_chunk_dict(row, include_enriched=True)
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving chunk {chunk_id}: {e}")
            return None
        finally:
            conn.close()
    
    def delete_chunks_by_document(self, doc_uuid: str) -> int:
        """Delete all chunks for a document.
        
        Args:
            doc_uuid: Document UUID
            
        Returns:
            Number of chunks deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM document_chunks
                WHERE doc_uuid = ?
            """, (doc_uuid,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Deleted {deleted_count} chunks for document {doc_uuid}")
            return deleted_count
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error deleting chunks: {e}")
            return 0
        finally:
            conn.close()
    
    def get_chunks_by_strategy(self, chunking_strategy: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks using a specific strategy.
        
        Args:
            chunking_strategy: Strategy name ('recursive', 'fixed_size', 'semantic')
            
        Returns:
            List of chunk dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM document_chunks
                WHERE chunking_strategy = ?
                ORDER BY created_at DESC
            """, (chunking_strategy,))
            
            rows = cursor.fetchall()
            return [self._row_to_chunk_dict(row, include_enriched=False) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving chunks by strategy: {e}")
            return []
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Total chunks
            cursor.execute("SELECT COUNT(*) as total FROM document_chunks")
            total_chunks = cursor.fetchone()['total']
            
            # Chunks by strategy
            cursor.execute("""
                SELECT chunking_strategy, COUNT(*) as count
                FROM document_chunks
                GROUP BY chunking_strategy
            """)
            by_strategy = {row['chunking_strategy']: row['count'] for row in cursor.fetchall()}
            
            # Enriched chunks
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM document_chunks
                WHERE enriched_content IS NOT NULL
            """)
            enriched_count = cursor.fetchone()['count']
            
            return {
                'total_chunks': total_chunks,
                'by_strategy': by_strategy,
                'enriched_chunks': enriched_count,
                'enrichment_rate': enriched_count / total_chunks if total_chunks > 0 else 0
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {'total_chunks': 0, 'by_strategy': {}, 'enriched_chunks': 0}
        finally:
            conn.close()

    # ===== Embedding Storage Methods =====

    def store_embeddings(self, embeddings_by_chunk_id: Dict[str, List[float]]) -> int:
        """Persist embedding vectors for a batch of chunks. Returns count updated."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            count = 0
            for chunk_id, embedding in embeddings_by_chunk_id.items():
                cursor.execute(
                    "UPDATE document_chunks SET embedding = ?, updated_at = ? WHERE chunk_id = ?",
                    (json.dumps(embedding), datetime.now().isoformat(), chunk_id)
                )
                count += cursor.rowcount
            conn.commit()
            logger.info(f"Stored embeddings for {count} chunks")
            return count
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error storing embeddings: {e}")
            return 0
        finally:
            conn.close()

    def get_embeddings_for_search(
        self,
        doc_uuids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Return (chunk_id, doc_uuid, chunk_index, embedding) for all embedded chunks.

        Optionally restricted to a list of doc_uuids for scoped search.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if doc_uuids:
                placeholders = ','.join('?' * len(doc_uuids))
                cursor.execute(
                    f"SELECT chunk_id, doc_uuid, chunk_index, embedding "
                    f"FROM document_chunks "
                    f"WHERE embedding IS NOT NULL AND doc_uuid IN ({placeholders})",
                    doc_uuids
                )
            else:
                cursor.execute(
                    "SELECT chunk_id, doc_uuid, chunk_index, embedding "
                    "FROM document_chunks WHERE embedding IS NOT NULL"
                )
            rows = cursor.fetchall()
            return [
                {
                    'chunk_id': row['chunk_id'],
                    'doc_uuid': row['doc_uuid'],
                    'chunk_index': row['chunk_index'],
                    'embedding': json.loads(row['embedding']),
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            logger.error(f"Error loading embeddings for search: {e}")
            return []
        finally:
            conn.close()

    def get_neighbor_chunks(
        self,
        doc_uuid: str,
        chunk_index: int,
        window: int = 1
    ) -> List[Dict[str, Any]]:
        """Return chunks adjacent to chunk_index within the same document.

        Fetches chunk_index in [chunk_index - window, chunk_index + window].
        Callers deduplicate by chunk_id since this range includes the hit itself.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM document_chunks "
                "WHERE doc_uuid = ? AND chunk_index BETWEEN ? AND ? "
                "ORDER BY chunk_index",
                (doc_uuid, chunk_index - window, chunk_index + window)
            )
            rows = cursor.fetchall()
            return [self._row_to_chunk_dict(row, include_enriched=True) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error fetching neighbor chunks: {e}")
            return []
        finally:
            conn.close()

    # ===== Abbreviation Storage Methods =====

    def _ensure_abbreviation_table(self):
        """Ensure abbreviation_expansions table exists."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS abbreviation_expansions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_uuid TEXT NOT NULL UNIQUE,
                    filename TEXT,
                    expansion_count INTEGER DEFAULT 0,
                    expansions_json TEXT,
                    expanded_text TEXT,
                    original_text TEXT,
                    processed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_abbrev_doc_uuid ON abbreviation_expansions(doc_uuid)")
            conn.commit()
        finally:
            conn.close()

    def store_abbreviation_data(
        self,
        doc_uuid: str,
        filename: str,
        expansions: list,
        expanded_text: str,
        original_text: str
    ) -> bool:
        """Store abbreviation expansion data for a document.

        Args:
            doc_uuid: Document UUID
            filename: Original filename
            expansions: List of expansion dictionaries
            expanded_text: Text with abbreviations expanded
            original_text: Original text before expansion

        Returns:
            True if stored successfully
        """
        self._ensure_abbreviation_table()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Delete existing data for this document
            cursor.execute("DELETE FROM abbreviation_expansions WHERE doc_uuid = ?", (doc_uuid,))

            # Insert new data
            cursor.execute("""
                INSERT INTO abbreviation_expansions (
                    doc_uuid, filename, expansion_count, expansions_json,
                    expanded_text, original_text, processed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_uuid,
                filename,
                len(expansions),
                json.dumps(expansions),
                expanded_text,
                original_text,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            conn.commit()
            logger.info(f"Stored {len(expansions)} abbreviation expansions for document {doc_uuid}")
            return True

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error storing abbreviation data: {e}")
            return False
        finally:
            conn.close()

    def get_abbreviation_data(self, doc_uuid: str) -> Optional[Dict[str, Any]]:
        """Retrieve abbreviation expansion data for a document.

        Args:
            doc_uuid: Document UUID

        Returns:
            Dictionary with abbreviation data or None if not found
        """
        self._ensure_abbreviation_table()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM abbreviation_expansions
                WHERE doc_uuid = ?
            """, (doc_uuid,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'document_id': row['doc_uuid'],
                'filename': row['filename'],
                'expansion_count': row['expansion_count'],
                'expansions': json.loads(row['expansions_json']) if row['expansions_json'] else [],
                'expanded_text': row['expanded_text'],
                'original_text': row['original_text'],
                'processed_at': row['processed_at']
            }

        except sqlite3.Error as e:
            logger.error(f"Error retrieving abbreviation data: {e}")
            return None
        finally:
            conn.close()

    def delete_abbreviation_data(self, doc_uuid: str) -> bool:
        """Delete abbreviation data for a document.

        Args:
            doc_uuid: Document UUID

        Returns:
            True if deleted successfully
        """
        self._ensure_abbreviation_table()
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM abbreviation_expansions WHERE doc_uuid = ?", (doc_uuid,))
            conn.commit()
            logger.info(f"Deleted abbreviation data for document {doc_uuid}")
            return True

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error deleting abbreviation data: {e}")
            return False
        finally:
            conn.close()
