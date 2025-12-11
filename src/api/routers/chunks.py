from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging
import os

from storage.chunk_storage import ChunkStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chunks", tags=["chunks"])


@router.get("/document/{doc_uuid}")
async def get_document_chunks(
    doc_uuid: str,
    include_enriched: bool = Query(default=True, description="Include enriched content")
):
    """Get all chunks for a specific document.
    
    Args:
        doc_uuid: Document UUID
        include_enriched: Whether to include enriched content
        
    Returns:
        Document chunks with metadata
    """
    try:
        storage = ChunkStorage(db_path=os.getenv('STORAGE__CHUNK_DB_PATH', 'data/brain_mvp.db'))
        chunks = storage.get_chunks_by_document(doc_uuid, include_enriched)
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No chunks found for document {doc_uuid}"
            )
        
        return {
            "doc_uuid": doc_uuid,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chunks for document {doc_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{chunk_id}")
async def get_chunk(chunk_id: str):
    """Get a specific chunk by ID.
    
    Args:
        chunk_id: Chunk identifier
        
    Returns:
        Chunk data with metadata
    """
    try:
        storage = ChunkStorage(db_path=os.getenv('STORAGE__CHUNK_DB_PATH', 'data/brain_mvp.db'))
        chunk = storage.get_chunk_by_id(chunk_id)
        
        if not chunk:
            raise HTTPException(
                status_code=404,
                detail=f"Chunk {chunk_id} not found"
            )
        
        return chunk
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chunk {chunk_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/strategy/{strategy}")
async def get_chunks_by_strategy(
    strategy: str,
    limit: int = Query(default=100, le=1000, description="Maximum chunks to return")
):
    """Get chunks using a specific chunking strategy.
    
    Args:
        strategy: Chunking strategy ('recursive', 'fixed_size', 'semantic')
        limit: Maximum number of chunks to return
        
    Returns:
        List of chunks using the specified strategy
    """
    try:
        storage = ChunkStorage(db_path=os.getenv('STORAGE__CHUNK_DB_PATH', 'data/brain_mvp.db'))
        chunks = storage.get_chunks_by_strategy(strategy)
        
        # Limit results
        chunks = chunks[:limit]
        
        return {
            "strategy": strategy,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
        
    except Exception as e:
        logger.error(f"Error retrieving chunks by strategy {strategy}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_chunk_statistics():
    """Get overall chunk storage statistics.
    
    Returns:
        Statistics about stored chunks
    """
    try:
        storage = ChunkStorage(db_path=os.getenv('STORAGE__CHUNK_DB_PATH', 'data/brain_mvp.db'))
        stats = storage.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving chunk statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/document/{doc_uuid}")
async def delete_document_chunks(doc_uuid: str):
    """Delete all chunks for a document.
    
    Args:
        doc_uuid: Document UUID
        
    Returns:
        Number of chunks deleted
    """
    try:
        storage = ChunkStorage(db_path=os.getenv('STORAGE__CHUNK_DB_PATH', 'data/brain_mvp.db'))
        deleted_count = storage.delete_chunks_by_document(doc_uuid)
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No chunks found for document {doc_uuid}"
            )
        
        return {
            "deleted_count": deleted_count,
            "doc_uuid": doc_uuid,
            "message": f"Successfully deleted {deleted_count} chunks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chunks for document {doc_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
