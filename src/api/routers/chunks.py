from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging
import os

from storage.chunk_storage import ChunkStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chunks", tags=["chunks"])


def _log_chunk_retrieval(chunk: dict, context: str = "") -> None:
    """Log chunk retrieval details for context quality inspection."""
    meta = chunk.get('metadata') or chunk.get('chunk_metadata') or {}
    logger.info(
        "Chunk retrieved%s | chunk_id=%s | doc_id=%s | section_path=%s | page_range=%s",
        f" ({context})" if context else "",
        chunk.get('chunk_id', '?'),
        meta.get('doc_id', meta.get('doc_uuid', '?')),
        meta.get('section_path', ''),
        meta.get('page_range', ''),
    )


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

        # Log retrieval details for context quality inspection
        logger.info("Retrieving %d chunks for document %s", len(chunks), doc_uuid)
        for chunk in chunks:
            _log_chunk_retrieval(chunk, context=f"doc={doc_uuid}")

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

        _log_chunk_retrieval(chunk, context="single")

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

        # Log retrieval details for context quality inspection
        logger.info("Retrieving %d chunks for strategy %s", len(chunks), strategy)
        for chunk in chunks:
            _log_chunk_retrieval(chunk, context=f"strategy={strategy}")

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


# ── Semantic search ───────────────────────────────────────────────────────────

class ChunkSearchRequest(BaseModel):
    """Semantic chunk search request.

    Tuning guidance
    ---------------
    top_k                Start at 10. Try 5 (fast/precise) → 8 → 10 → 20 (broad).
                         Quality typically plateaus around 10; above 15 adds noise.
    similarity_threshold Start at 0.0 (no filter). Raise to 0.3 to drop off-topic
                         chunks, 0.5 for high-precision retrieval.
    neighbor_window      1 = ±1 adjacent chunk (recommended). Prevents cliff-edge
                         context loss. Use 0 to isolate scored hits only.
    """
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(
        default=10, ge=1, le=50,
        description="Number of top-scored chunks to return. Try 5, 8, 10, 20."
    )
    similarity_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Minimum cosine similarity (0.0 = off, 0.3–0.5 typical)."
    )
    neighbor_window: int = Field(
        default=1, ge=0, le=3,
        description="±N adjacent chunks fetched per hit for context continuity."
    )
    doc_filter: Optional[List[str]] = Field(
        default=None,
        description="Restrict search to these doc_uuid values."
    )


@router.post("/search")
async def search_chunks(request: ChunkSearchRequest) -> Dict[str, Any]:
    """Semantic similarity search over all embedded chunks.

    Returns scored **hits** (top-k) plus a **context_chunks** list that
    includes each hit's ±neighbor_window adjacent chunks in document order —
    ready to pass directly to an LLM.

    Use `top_k_options`, `similarity_threshold_options`, and
    `neighbor_window_options` in the response to drive UI tuning controls.
    """
    try:
        from docforge.rag.retriever import get_retriever
        retriever = get_retriever(
            db_path=os.getenv("STORAGE__CHUNK_DB_PATH", "data/brain_mvp.db")
        )
        return retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            neighbor_window=request.neighbor_window,
            doc_filter=request.doc_filter,
        )
    except Exception as e:
        logger.error(f"Chunk search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
