"""
Configuration for hybrid chunking pipeline.

Defines thresholds for section classification and chunking parameters.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SectionSizeCategory(str, Enum):
    """Section size categories for routing decisions."""

    SHORT = "short"  # Keep as single chunk or merge with adjacent
    MEDIUM = "medium"  # Recursive split at paragraph/sentence level
    LONG = "long"  # Recursive split + flag for semantic refinement


@dataclass
class HybridChunkingConfig:
    """Configuration for hybrid chunking pipeline."""

    # ===================
    # Size Thresholds (in words)
    # ===================

    # Sections below this are classified as SHORT
    short_section_threshold: int = 100

    # Sections above this are classified as LONG
    # (MEDIUM is between short and long thresholds)
    long_section_threshold: int = 600

    # ===================
    # Chunk Size Parameters
    # ===================

    # Target size for output chunks (words)
    # ~467 tokens at 0.75 words/token, midpoint of 300-600 token range
    target_chunk_size: int = 350

    # Maximum allowed chunk size (words)
    # ~667 tokens, hard cap near top of desired 300-600 token range
    max_chunk_size: int = 500

    # Minimum viable chunk size - chunks smaller than this may be merged
    min_chunk_size: int = 30

    # ===================
    # Overlap Settings
    # ===================

    # Number of words to overlap between adjacent chunks
    # 50/350 = ~14% overlap, within the 10-20% requirement
    chunk_overlap: int = 50

    # ===================
    # Short Section Handling
    # ===================

    # Whether to merge adjacent short sections
    merge_adjacent_short_sections: bool = True

    # Maximum combined word count for merging short sections
    short_section_merge_threshold: int = 300

    # ===================
    # Boundary Preferences
    # ===================

    # Respect section boundaries (don't split across sections)
    respect_section_boundaries: bool = True

    # Respect paragraph boundaries when possible
    respect_paragraph_boundaries: bool = True

    # Respect sentence boundaries as fallback
    respect_sentence_boundaries: bool = True

    # ===================
    # Semantic Refinement
    # ===================

    # Flag chunks from LONG sections as candidates for semantic refinement
    flag_long_sections_for_semantic: bool = True

    # ===================
    # Language Settings
    # ===================

    # Language for sentence splitting patterns
    language: str = "en"

    # ===================
    # Sentence Splitting Patterns
    # ===================

    # Regex patterns for sentence boundaries (by language)
    sentence_end_patterns: List[str] = field(
        default_factory=lambda: [
            r"(?<=[.!?])\s+(?=[A-Z])",  # Standard sentence end
            r"(?<=[.!?])\s*\n",  # Sentence end at line break
        ]
    )

    def __post_init__(self):
        """Validate configuration values."""
        if self.short_section_threshold >= self.long_section_threshold:
            raise ValueError(
                f"short_section_threshold ({self.short_section_threshold}) "
                f"must be less than long_section_threshold ({self.long_section_threshold})"
            )

        if self.min_chunk_size >= self.target_chunk_size:
            raise ValueError(
                f"min_chunk_size ({self.min_chunk_size}) "
                f"must be less than target_chunk_size ({self.target_chunk_size})"
            )

        if self.target_chunk_size > self.max_chunk_size:
            raise ValueError(
                f"target_chunk_size ({self.target_chunk_size}) "
                f"must not exceed max_chunk_size ({self.max_chunk_size})"
            )

    @classmethod
    def default(cls) -> "HybridChunkingConfig":
        """Create default configuration."""
        return cls()

    @classmethod
    def for_short_documents(cls) -> "HybridChunkingConfig":
        """Configuration optimized for short documents."""
        return cls(
            short_section_threshold=75,
            long_section_threshold=400,
            target_chunk_size=250,
            max_chunk_size=400,
            min_chunk_size=20,
        )

    @classmethod
    def for_long_documents(cls) -> "HybridChunkingConfig":
        """Configuration optimized for long documents."""
        return cls(
            short_section_threshold=150,
            long_section_threshold=800,
            target_chunk_size=450,
            max_chunk_size=650,
            min_chunk_size=50,
            chunk_overlap=65,
        )
