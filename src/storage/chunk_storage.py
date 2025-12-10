"""Chunk storage service for database operations.

Handles storing and retrieving document chunks with metadata.
"""

import logging
import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

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
    
    def _ensure_database(self):
        """Ensure database and tables exist."""
        db_file = Path(self.db_path)
        if not db_file.exists():
            logger.warning(f"Database not found at {self.db_path}")
    
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
                original_content = chunk.get('content', chunk.get('original_content', ''))
                enriched_content = chunk.get('enriched_content')
                
                # Prepare metadata
                chunk_metadata = json.dumps(chunk.get('metadata', {}))
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
            
            chunks = []
            for row in rows:
                chunk = {
                    'chunk_id': row['chunk_id'],
                    'doc_uuid': row['doc_uuid'],
                    'lineage_uuid': row['lineage_uuid'],
                    'version_number': row['version_number'],
                    'chunk_index': row['chunk_index'],
                    'chunking_strategy': row['chunking_strategy'],
                    'original_content': row['original_content'],
                    'metadata': json.loads(row['chunk_metadata']),
                    'relationships': json.loads(row['chunk_relationships']),
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                
                # Add enriched content if requested and available
                if include_enriched and row['enriched_content']:
                    chunk['enriched_content'] = row['enriched_content']
                    chunk['enrichment_metadata'] = json.loads(row['enrichment_metadata'])
                
                chunks.append(chunk)
            
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
            
            chunk = {
                'chunk_id': row['chunk_id'],
                'doc_uuid': row['doc_uuid'],
                'lineage_uuid': row['lineage_uuid'],
                'version_number': row['version_number'],
                'chunk_index': row['chunk_index'],
                'chunking_strategy': row['chunking_strategy'],
                'original_content': row['original_content'],
                'enriched_content': row['enriched_content'],
                'metadata': json.loads(row['chunk_metadata']),
                'enrichment_metadata': json.loads(row['enrichment_metadata']),
                'relationships': json.loads(row['chunk_relationships']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            
            return chunk
            
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
            
            chunks = []
            for row in rows:
                chunk = {
                    'chunk_id': row['chunk_id'],
                    'doc_uuid': row['doc_uuid'],
                    'chunking_strategy': row['chunking_strategy'],
                    'chunk_index': row['chunk_index'],
                    'created_at': row['created_at']
                }
                chunks.append(chunk)
            
            return chunks
            
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
