"""
Hybrid Document Chunker

Main entry point for the hybrid structure-aware chunking pipeline.

Combines:
1. Document normalization (MinerU output → common model)
2. Length-based section routing (SHORT/MEDIUM/LONG)
3. Structure-aware recursive chunking (section → paragraph → sentence)
"""

import logging
from typing import List, Dict, Any, Optional

from docforge.preprocessing.schemas import StandardizedDocumentOutput
from docforge.postprocessing.schemas import ChunkData

from .config import HybridChunkingConfig
from .normalized_document import NormalizedDocument
from .normalizer import MinerUDocumentNormalizer
from .structure_aware_chunker import StructureAwareRecursiveChunker, HybridChunkResult
from .section_router import SectionRouter

logger = logging.getLogger(__name__)


class HybridDocumentChunker:
    """
    Main entry point for hybrid structure-aware chunking.

    This chunker provides a high-level interface that:
    1. Normalizes MinerU/processor output to a common document model
    2. Routes sections by length to appropriate chunking strategies
    3. Chunks respecting structural boundaries
    4. Flags long section chunks for semantic refinement

    Usage:
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(standardized_output)

        # Or with custom config:
        config = HybridChunkingConfig(
            short_section_threshold=100,
            long_section_threshold=600,
        )
        chunker = HybridDocumentChunker(config)
        results = chunker.chunk_document(standardized_output)
    """

    def __init__(self, config: HybridChunkingConfig = None):
        """
        Initialize hybrid chunker.

        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or HybridChunkingConfig()
        self.normalizer = MinerUDocumentNormalizer(language=self.config.language)
        self.chunker = StructureAwareRecursiveChunker(self.config)
        self.router = SectionRouter(self.config)

    def chunk_document(
        self,
        document: StandardizedDocumentOutput,
        document_id: str = None,
    ) -> List[HybridChunkResult]:
        """
        Chunk a document using hybrid structure-aware approach.

        Args:
            document: StandardizedDocumentOutput from MinerU or other processors
            document_id: Optional document identifier for tracking

        Returns:
            List of HybridChunkResult with chunks and routing metadata
        """
        logger.info(f"Starting hybrid chunking for document: {document_id}")

        # Step 1: Normalize to common document model
        normalized = self.normalizer.normalize(document, document_id)
        logger.debug(
            f"Normalized document: {normalized.section_count} sections, "
            f"{normalized.total_word_count} words"
        )

        # Step 2: Apply structure-aware chunking
        results = self.chunker.chunk_document(normalized)
        logger.info(
            f"Created {len(results)} chunks "
            f"({sum(1 for r in results if r.is_semantic_refinement_candidate)} flagged for semantic refinement)"
        )

        return results

    def chunk_to_chunk_data(
        self,
        document: StandardizedDocumentOutput,
        document_id: str = None,
    ) -> List[ChunkData]:
        """
        Chunk document and return only ChunkData objects (without routing metadata).

        Useful for compatibility with existing systems that expect List[ChunkData].

        Args:
            document: StandardizedDocumentOutput from processors
            document_id: Optional document identifier

        Returns:
            List of ChunkData objects
        """
        results = self.chunk_document(document, document_id)
        return [r.chunk_data for r in results]

    def get_semantic_refinement_candidates(
        self,
        results: List[HybridChunkResult],
    ) -> List[HybridChunkResult]:
        """
        Filter results to only those flagged for semantic refinement.

        Args:
            results: List of HybridChunkResult from chunk_document()

        Returns:
            Filtered list of chunks needing semantic refinement
        """
        return [r for r in results if r.is_semantic_refinement_candidate]

    def get_chunking_statistics(
        self,
        results: List[HybridChunkResult],
    ) -> Dict[str, Any]:
        """
        Get statistics about chunking results.

        Args:
            results: List of HybridChunkResult

        Returns:
            Dictionary with statistics
        """
        if not results:
            return {
                "total_chunks": 0,
                "by_category": {},
                "by_strategy": {},
                "by_boundary_type": {},
                "semantic_candidates": 0,
                "avg_word_count": 0,
                "avg_char_count": 0,
            }

        # Count by category
        by_category = {}
        for r in results:
            cat = r.size_category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by strategy
        by_strategy = {}
        for r in results:
            strat = r.chunking_strategy_used
            by_strategy[strat] = by_strategy.get(strat, 0) + 1

        # Count by boundary type
        by_boundary = {}
        for r in results:
            bt = r.boundary_type
            by_boundary[bt] = by_boundary.get(bt, 0) + 1

        # Calculate averages
        total_words = sum(r.chunk_data.metadata.word_count for r in results)
        total_chars = sum(r.chunk_data.metadata.character_count for r in results)

        return {
            "total_chunks": len(results),
            "by_category": by_category,
            "by_strategy": by_strategy,
            "by_boundary_type": by_boundary,
            "semantic_candidates": sum(
                1 for r in results if r.is_semantic_refinement_candidate
            ),
            "avg_word_count": total_words / len(results),
            "avg_char_count": total_chars / len(results),
            "min_word_count": min(r.chunk_data.metadata.word_count for r in results),
            "max_word_count": max(r.chunk_data.metadata.word_count for r in results),
        }

    def analyze_document(
        self,
        document: StandardizedDocumentOutput,
        document_id: str = None,
    ) -> Dict[str, Any]:
        """
        Analyze document without chunking - preview routing decisions.

        Args:
            document: StandardizedDocumentOutput
            document_id: Optional document identifier

        Returns:
            Dictionary with analysis results
        """
        normalized = self.normalizer.normalize(document, document_id)

        # Get routing analysis
        all_sections = normalized.get_all_sections_flat()
        routing_stats = self.router.analyze_document_sections(all_sections)

        # Get section details
        section_details = [
            self.router.get_routing_info(section) for section in all_sections
        ]

        return {
            "document_id": document_id,
            "title": normalized.title,
            "page_count": normalized.page_count,
            "total_word_count": normalized.total_word_count,
            "section_count": normalized.section_count,
            "routing_stats": routing_stats,
            "section_details": section_details,
            "config": {
                "short_threshold": self.config.short_section_threshold,
                "long_threshold": self.config.long_section_threshold,
                "target_chunk_size": self.config.target_chunk_size,
            },
        }


# Re-export for convenience
__all__ = [
    "HybridDocumentChunker",
    "HybridChunkResult",
    "HybridChunkingConfig",
]
