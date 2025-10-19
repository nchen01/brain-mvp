"""DocForge post-processing module.

This module handles post-processing of documents after initial processing,
including chunking, abbreviation expansion, and content enhancement.
"""

from .router import PostProcessingRouter
from .chunker import DocumentChunker
from .schemas import (
    ChunkData,
    ChunkMetadata,
    PostProcessingResult,
    PostProcessingConfig,
    ProcessingMethod,
    ChunkingStrategy
)

__all__ = [
    'PostProcessingRouter',
    'DocumentChunker',
    'ChunkData',
    'ChunkMetadata',
    'PostProcessingResult',
    'PostProcessingConfig',
    'ProcessingMethod',
    'ChunkingStrategy'
]