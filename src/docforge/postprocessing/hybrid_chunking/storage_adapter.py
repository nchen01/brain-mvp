"""
Storage Adapter for Hybrid Chunking

Integrates hybrid chunking results with existing ChunkStorage.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from storage.chunk_storage import ChunkStorage
from .structure_aware_chunker import HybridChunkResult

logger = logging.getLogger(__name__)


class HybridChunkStorageAdapter:
    """
    Adapter to integrate hybrid chunking with existing ChunkStorage.

    Converts HybridChunkResult objects to the format expected by ChunkStorage
    and handles the storage operations.
    """

    def __init__(self, chunk_storage: ChunkStorage = None, db_path: str = None):
        """
        Initialize storage adapter.

        Args:
            chunk_storage: Existing ChunkStorage instance to use
            db_path: Path to database (used if chunk_storage not provided)
        """
        if chunk_storage:
            self.storage = chunk_storage
        else:
            db_path = db_path or "data/brain_mvp.db"
            self.storage = ChunkStorage(db_path=db_path)

    def store_hybrid_chunks(
        self,
        doc_uuid: str,
        lineage_uuid: str,
        version_number: int,
        hybrid_results: List[HybridChunkResult],
    ) -> List[str]:
        """
        Store hybrid chunk results using existing ChunkStorage.

        Args:
            doc_uuid: Document UUID
            lineage_uuid: Document lineage UUID
            version_number: Document version number
            hybrid_results: List of HybridChunkResult from hybrid chunker

        Returns:
            List of stored chunk IDs
        """
        if not hybrid_results:
            logger.warning(f"No chunks to store for document {doc_uuid}")
            return []

        # Convert HybridChunkResult to storage format
        chunk_dicts = []
        for result in hybrid_results:
            chunk_dict = self._convert_to_storage_format(result)
            chunk_dicts.append(chunk_dict)

        # Store using existing ChunkStorage
        chunk_ids = self.storage.store_chunks(
            doc_uuid=doc_uuid,
            lineage_uuid=lineage_uuid,
            version_number=version_number,
            chunks=chunk_dicts,
            chunking_strategy="hybrid_structure_aware",
        )

        logger.info(
            f"Stored {len(chunk_ids)} hybrid chunks for document {doc_uuid}"
        )

        return chunk_ids

    def _convert_to_storage_format(self, result: HybridChunkResult) -> dict:
        """
        Convert HybridChunkResult to dictionary format for ChunkStorage.

        Args:
            result: HybridChunkResult to convert

        Returns:
            Dictionary in ChunkStorage format
        """
        chunk_data = result.chunk_data

        return {
            "content": chunk_data.content,
            "metadata": {
                "word_count": chunk_data.metadata.word_count,
                "character_count": chunk_data.metadata.character_count,
                "chunk_type": chunk_data.chunk_type.value
                if hasattr(chunk_data.chunk_type, "value")
                else str(chunk_data.chunk_type),
                "page_numbers": chunk_data.metadata.page_numbers,
                "source_elements": chunk_data.metadata.source_elements,
                "language": chunk_data.metadata.language,
                "confidence_score": chunk_data.metadata.confidence_score,
                # Hybrid-specific metadata
                "size_category": result.size_category.value,
                "chunking_strategy": result.chunking_strategy_used,
                "is_semantic_candidate": result.is_semantic_refinement_candidate,
                "source_section_id": result.source_section_id,
                "heading_path": result.source_heading_path,
                "boundary_type": result.boundary_type,
                # Position information
                "section_title": chunk_data.position.get("section_title", ""),
                "section_level": chunk_data.position.get("section_level"),
                "heading_context": chunk_data.position.get("heading_context", ""),
                # Standardised metadata for retrieval quality inspection
                "doc_id": "",  # Populated by caller (documents.py) at store time
                "title": chunk_data.position.get("section_title", ""),
                "section_path": result.source_heading_path,
                "page_range": self._format_page_range(chunk_data.metadata.page_numbers),
                "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "relationships": chunk_data.relationships,
        }

    @staticmethod
    def _format_page_range(page_numbers: list) -> str:
        """Format a list of page numbers into a human-readable range string."""
        if not page_numbers:
            return ""
        pages = sorted(set(int(p) for p in page_numbers))
        if len(pages) == 1:
            return str(pages[0])
        ranges = []
        start = pages[0]
        prev = pages[0]
        for p in pages[1:]:
            if p == prev + 1:
                prev = p
            else:
                ranges.append(f"{start}-{prev}" if start != prev else str(start))
                start = prev = p
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        return ", ".join(ranges)

    def get_semantic_candidates(
        self,
        doc_uuid: str,
        include_enriched: bool = False,
    ) -> List[dict]:
        """
        Retrieve chunks that are flagged for semantic refinement.

        Args:
            doc_uuid: Document UUID
            include_enriched: Whether to include enriched content

        Returns:
            List of chunk dictionaries that are semantic candidates
        """
        all_chunks = self.storage.get_chunks_by_document(
            doc_uuid=doc_uuid,
            include_enriched=include_enriched,
        )

        candidates = []
        for chunk in all_chunks:
            metadata = chunk.get("chunk_metadata", {})
            if metadata.get("is_semantic_candidate", False):
                candidates.append(chunk)

        return candidates

    def get_chunks_by_boundary_type(
        self,
        doc_uuid: str,
        boundary_type: str,
    ) -> List[dict]:
        """
        Retrieve chunks by their boundary type.

        Args:
            doc_uuid: Document UUID
            boundary_type: Boundary type ("section", "paragraph", "sentence")

        Returns:
            List of matching chunk dictionaries
        """
        all_chunks = self.storage.get_chunks_by_document(doc_uuid=doc_uuid)

        matching = []
        for chunk in all_chunks:
            metadata = chunk.get("chunk_metadata", {})
            if metadata.get("boundary_type") == boundary_type:
                matching.append(chunk)

        return matching

    def get_chunks_with_heading_context(
        self,
        doc_uuid: str,
    ) -> List[dict]:
        """
        Retrieve chunks with their heading context path.

        Args:
            doc_uuid: Document UUID

        Returns:
            List of chunks with heading_path populated
        """
        all_chunks = self.storage.get_chunks_by_document(doc_uuid=doc_uuid)

        # Add heading context to each chunk for easy access
        for chunk in all_chunks:
            metadata = chunk.get("chunk_metadata", {})
            chunk["heading_path"] = metadata.get("heading_path", [])
            chunk["heading_context"] = metadata.get("heading_context", "")

        return all_chunks

    def get_storage_statistics(self) -> dict:
        """
        Get statistics about stored hybrid chunks.

        Returns:
            Dictionary with storage statistics
        """
        base_stats = self.storage.get_statistics()

        # Add hybrid-specific stats
        base_stats["hybrid_chunks"] = base_stats.get("by_strategy", {}).get(
            "hybrid_structure_aware", 0
        )

        return base_stats
