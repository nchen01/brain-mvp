"""
Hybrid Chunking Module

Structure-aware chunking pipeline that normalizes documents and applies
length-based routing for intelligent section chunking.

Sprint 1: Baseline hybrid chunking with section/paragraph/sentence boundaries
"""

from .config import HybridChunkingConfig, SectionSizeCategory
from .normalized_document import (
    NormalizedDocument,
    NormalizedSection,
    NormalizedParagraph,
    NormalizedHeading,
    HeadingLevel,
)
from .interfaces import (
    IDocumentNormalizer,
    ISectionRouter,
    IStructureAwareChunker,
)
from .hybrid_chunker import HybridDocumentChunker, HybridChunkResult

__all__ = [
    # Config
    "HybridChunkingConfig",
    "SectionSizeCategory",
    # Models
    "NormalizedDocument",
    "NormalizedSection",
    "NormalizedParagraph",
    "NormalizedHeading",
    "HeadingLevel",
    # Interfaces
    "IDocumentNormalizer",
    "ISectionRouter",
    "IStructureAwareChunker",
    # Main entry point
    "HybridDocumentChunker",
    "HybridChunkResult",
]
