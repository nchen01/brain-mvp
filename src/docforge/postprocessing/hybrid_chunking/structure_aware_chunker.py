"""
Structure-Aware Recursive Chunker

Chunks documents respecting structural boundaries:
Section → Paragraph → Sentence

Implements length-based routing:
- SHORT sections: Keep as single chunk or merge
- MEDIUM sections: Recursive paragraph/sentence splitting
- LONG sections: Recursive split + semantic refinement flag
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

from docforge.postprocessing.schemas import (
    ChunkData,
    ChunkMetadata,
    ChunkType,
)
from .interfaces import IStructureAwareChunker
from .normalized_document import (
    NormalizedDocument,
    NormalizedSection,
    NormalizedParagraph,
)
from .config import HybridChunkingConfig, SectionSizeCategory
from .section_router import SectionRouter
from .boundary_detectors import BoundaryDetector, count_words

logger = logging.getLogger(__name__)


@dataclass
class HybridChunkResult:
    """Extended chunk result with routing metadata."""

    chunk_data: ChunkData

    # Routing metadata
    size_category: SectionSizeCategory
    chunking_strategy_used: str
    is_semantic_refinement_candidate: bool = False

    # Source tracking
    source_section_id: str = ""
    source_heading_path: List[str] = field(default_factory=list)

    # Boundary information
    boundary_type: str = "section"  # section, paragraph, sentence, character


class StructureAwareRecursiveChunker(IStructureAwareChunker):
    """
    Structure-aware chunker that respects document boundaries.

    This chunker:
    1. Routes sections by length (SHORT/MEDIUM/LONG)
    2. Merges adjacent short sections when appropriate
    3. Recursively splits at paragraph then sentence boundaries
    4. Flags long section chunks for semantic refinement
    5. Preserves heading context across chunks
    """

    def __init__(self, config: HybridChunkingConfig = None):
        """
        Initialize chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config or HybridChunkingConfig()
        self.router = SectionRouter(self.config)
        self.boundary_detector = BoundaryDetector(self.config.language)
        self._chunk_counter = 0

    def chunk_document(self, document: NormalizedDocument) -> List[HybridChunkResult]:
        """
        Chunk entire normalized document.

        Args:
            document: NormalizedDocument to chunk

        Returns:
            List of HybridChunkResult with routing metadata
        """
        self._chunk_counter = 0
        results: List[HybridChunkResult] = []

        # Get all leaf sections (sections without children, or sections with content)
        all_sections = self._get_sections_for_chunking(document)

        # Group sections for processing (merges adjacent short sections)
        section_groups = self.router.group_mergeable_sections(all_sections)

        for group in section_groups:
            if len(group) == 1:
                # Single section processing
                section = group[0]
                category = self.router.classify_section(section)
                heading_context = self._build_heading_context(section)
                chunks = self.chunk_section(section, category, heading_context)
                results.extend(chunks)
            else:
                # Merged short sections
                merged_chunks = self._process_merged_sections(group)
                results.extend(merged_chunks)

        # Add overlap between adjacent chunks
        if self.config.chunk_overlap > 0:
            results = self._add_chunk_overlap(results)

        # Link relationships
        self._link_chunk_relationships(results)

        return results

    def chunk_section(
        self,
        section: NormalizedSection,
        category: SectionSizeCategory,
        heading_context: str = "",
    ) -> List[HybridChunkResult]:
        """
        Chunk a single section based on its size category.

        Args:
            section: Section to chunk
            category: Size category (SHORT, MEDIUM, LONG)
            heading_context: Parent heading context

        Returns:
            List of HybridChunkResult
        """
        if category == SectionSizeCategory.SHORT:
            return self._handle_short_section(section, heading_context)
        elif category == SectionSizeCategory.MEDIUM:
            return self._recursive_split(section, heading_context, flag_semantic=False)
        else:  # LONG
            return self._recursive_split(section, heading_context, flag_semantic=True)

    def _get_sections_for_chunking(
        self, document: NormalizedDocument
    ) -> List[NormalizedSection]:
        """
        Get sections to chunk, handling hierarchy appropriately.

        For nested sections, we chunk at the leaf level (sections with paragraphs
        but no children, or sections where we want to preserve the heading).
        """
        result = []

        def collect(sections: List[NormalizedSection]):
            for section in sections:
                # If section has paragraphs, include it for chunking
                if section.paragraphs:
                    result.append(section)
                # Also process children
                if section.children:
                    collect(section.children)

        collect(document.sections)
        return result

    def _handle_short_section(
        self, section: NormalizedSection, heading_context: str
    ) -> List[HybridChunkResult]:
        """Handle a short section by keeping it as a single chunk."""
        content = section.full_text
        if not content.strip():
            return []

        chunk_data = self._create_chunk_data(
            content=content,
            chunk_type=ChunkType.SECTION,
            section=section,
            heading_context=heading_context,
        )

        return [
            HybridChunkResult(
                chunk_data=chunk_data,
                size_category=SectionSizeCategory.SHORT,
                chunking_strategy_used="keep_single",
                is_semantic_refinement_candidate=False,
                source_section_id=section.id,
                source_heading_path=section.heading_path,
                boundary_type="section",
            )
        ]

    def _process_merged_sections(
        self, sections: List[NormalizedSection]
    ) -> List[HybridChunkResult]:
        """Process and merge multiple short sections into one chunk."""
        if not sections:
            return []

        # Combine content from all sections
        content_parts = []
        all_page_numbers = []
        all_element_ids = []

        for section in sections:
            content_parts.append(section.full_text)
            all_page_numbers.extend(section.page_numbers)
            all_element_ids.extend(section.source_element_ids)

        content = "\n\n".join(content_parts)
        if not content.strip():
            return []

        # Use first section's heading for context
        first_section = sections[0]
        heading_context = self._build_heading_context(first_section)

        chunk_data = self._create_chunk_data(
            content=content,
            chunk_type=ChunkType.SECTION,
            section=first_section,
            heading_context=heading_context,
            page_numbers=sorted(set(all_page_numbers)),
            source_element_ids=all_element_ids,
        )

        return [
            HybridChunkResult(
                chunk_data=chunk_data,
                size_category=SectionSizeCategory.SHORT,
                chunking_strategy_used="merged_short",
                is_semantic_refinement_candidate=False,
                source_section_id=first_section.id,
                source_heading_path=first_section.heading_path,
                boundary_type="section",
            )
        ]

    def _recursive_split(
        self,
        section: NormalizedSection,
        heading_context: str,
        flag_semantic: bool,
    ) -> List[HybridChunkResult]:
        """
        Recursively split section at paragraph then sentence boundaries.

        Args:
            section: Section to split
            heading_context: Heading context for chunks
            flag_semantic: Whether to flag chunks for semantic refinement

        Returns:
            List of HybridChunkResult
        """
        results: List[HybridChunkResult] = []

        # Track current chunk content
        current_paragraphs: List[NormalizedParagraph] = []
        current_word_count = 0

        for paragraph in section.paragraphs:
            para_words = paragraph.word_count

            # Check if paragraph fits in current chunk
            if current_word_count + para_words <= self.config.target_chunk_size:
                current_paragraphs.append(paragraph)
                current_word_count += para_words
            else:
                # Check if single paragraph exceeds max size
                if para_words > self.config.max_chunk_size:
                    # Finalize current chunk first
                    if current_paragraphs:
                        chunk = self._create_paragraph_chunk(
                            current_paragraphs,
                            section,
                            heading_context,
                            flag_semantic,
                        )
                        results.append(chunk)
                        current_paragraphs = []
                        current_word_count = 0

                    # Split large paragraph at sentence level
                    sentence_chunks = self._split_paragraph_by_sentences(
                        paragraph, section, heading_context, flag_semantic
                    )
                    results.extend(sentence_chunks)
                else:
                    # Finalize current chunk, start new one
                    if current_paragraphs:
                        chunk = self._create_paragraph_chunk(
                            current_paragraphs,
                            section,
                            heading_context,
                            flag_semantic,
                        )
                        results.append(chunk)

                    current_paragraphs = [paragraph]
                    current_word_count = para_words

        # Finalize last chunk
        if current_paragraphs:
            chunk = self._create_paragraph_chunk(
                current_paragraphs,
                section,
                heading_context,
                flag_semantic,
            )
            results.append(chunk)

        return results

    def _split_paragraph_by_sentences(
        self,
        paragraph: NormalizedParagraph,
        section: NormalizedSection,
        heading_context: str,
        flag_semantic: bool,
    ) -> List[HybridChunkResult]:
        """Split a large paragraph at sentence boundaries."""
        results: List[HybridChunkResult] = []

        # Use pre-split sentences or split now
        sentences = paragraph.sentences
        if not sentences:
            sentences = self.boundary_detector.split_sentences(paragraph.text)

        current_sentences: List[str] = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = count_words(sentence)

            if current_word_count + sentence_words <= self.config.target_chunk_size:
                current_sentences.append(sentence)
                current_word_count += sentence_words
            else:
                # Finalize current chunk
                if current_sentences:
                    chunk = self._create_sentence_chunk(
                        current_sentences,
                        paragraph,
                        section,
                        heading_context,
                        flag_semantic,
                    )
                    results.append(chunk)

                current_sentences = [sentence]
                current_word_count = sentence_words

        # Finalize last chunk
        if current_sentences:
            chunk = self._create_sentence_chunk(
                current_sentences,
                paragraph,
                section,
                heading_context,
                flag_semantic,
            )
            results.append(chunk)

        return results

    def _create_paragraph_chunk(
        self,
        paragraphs: List[NormalizedParagraph],
        section: NormalizedSection,
        heading_context: str,
        flag_semantic: bool,
    ) -> HybridChunkResult:
        """Create a chunk from one or more paragraphs."""
        content = "\n\n".join(p.text for p in paragraphs)

        # Collect metadata from paragraphs
        page_numbers = []
        source_element_ids = []
        for p in paragraphs:
            if p.page_number not in page_numbers:
                page_numbers.append(p.page_number)
            source_element_ids.extend(p.source_element_ids)

        chunk_data = self._create_chunk_data(
            content=content,
            chunk_type=ChunkType.PARAGRAPH,
            section=section,
            heading_context=heading_context,
            page_numbers=page_numbers,
            source_element_ids=source_element_ids,
        )

        category = (
            SectionSizeCategory.LONG if flag_semantic else SectionSizeCategory.MEDIUM
        )

        return HybridChunkResult(
            chunk_data=chunk_data,
            size_category=category,
            chunking_strategy_used="recursive_paragraph",
            is_semantic_refinement_candidate=flag_semantic,
            source_section_id=section.id,
            source_heading_path=section.heading_path,
            boundary_type="paragraph",
        )

    def _create_sentence_chunk(
        self,
        sentences: List[str],
        paragraph: NormalizedParagraph,
        section: NormalizedSection,
        heading_context: str,
        flag_semantic: bool,
    ) -> HybridChunkResult:
        """Create a chunk from sentences."""
        content = " ".join(sentences)

        chunk_data = self._create_chunk_data(
            content=content,
            chunk_type=ChunkType.TEXT,
            section=section,
            heading_context=heading_context,
            page_numbers=[paragraph.page_number],
            source_element_ids=paragraph.source_element_ids,
        )

        category = (
            SectionSizeCategory.LONG if flag_semantic else SectionSizeCategory.MEDIUM
        )

        return HybridChunkResult(
            chunk_data=chunk_data,
            size_category=category,
            chunking_strategy_used="recursive_sentence",
            is_semantic_refinement_candidate=flag_semantic,
            source_section_id=section.id,
            source_heading_path=section.heading_path,
            boundary_type="sentence",
        )

    def _create_chunk_data(
        self,
        content: str,
        chunk_type: ChunkType,
        section: NormalizedSection,
        heading_context: str,
        page_numbers: List[int] = None,
        source_element_ids: List[str] = None,
    ) -> ChunkData:
        """Create ChunkData with metadata."""
        chunk_id = f"hybrid_chunk_{self._chunk_counter}"
        self._chunk_counter += 1

        word_count = count_words(content)
        char_count = len(content)

        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            chunk_index=self._chunk_counter - 1,
            chunk_type=chunk_type,
            source_elements=source_element_ids or section.source_element_ids,
            page_numbers=page_numbers or section.page_numbers,
            word_count=word_count,
            character_count=char_count,
            language=self.config.language,
            confidence_score=1.0,
            processing_timestamp=datetime.now(timezone.utc),
        )

        position = {
            "section_id": section.id,
            "section_title": section.heading_text,
            "section_level": section.heading_level,
            "heading_context": heading_context,
            "heading_path": section.heading_path,
        }

        return ChunkData(
            chunk_id=chunk_id,
            content=content,
            chunk_type=chunk_type,
            metadata=metadata,
            position=position,
            relationships={},
        )

    def _build_heading_context(self, section: NormalizedSection) -> str:
        """Build heading context string from section."""
        if section.heading_path:
            return " > ".join(section.heading_path)
        elif section.heading:
            return section.heading.text
        return ""

    def _add_chunk_overlap(
        self, results: List[HybridChunkResult]
    ) -> List[HybridChunkResult]:
        """Add overlap content to chunks for context continuity."""
        if len(results) < 2:
            return results

        overlap_words = self.config.chunk_overlap

        for i in range(1, len(results)):
            prev_chunk = results[i - 1].chunk_data
            curr_chunk = results[i].chunk_data

            # Get overlap from end of previous chunk
            prev_words = prev_chunk.content.split()
            if len(prev_words) > overlap_words:
                overlap_text = " ".join(prev_words[-overlap_words:])

                # Prepend to current chunk (with separator)
                curr_chunk.content = f"[...] {overlap_text}\n\n{curr_chunk.content}"

                # Update word count
                curr_chunk.metadata.word_count = count_words(curr_chunk.content)
                curr_chunk.metadata.character_count = len(curr_chunk.content)

        return results

    def _link_chunk_relationships(self, results: List[HybridChunkResult]):
        """Link chunks with previous/next relationships."""
        for i, result in enumerate(results):
            relationships = {}

            if i > 0:
                relationships["previous"] = [results[i - 1].chunk_data.chunk_id]

            if i < len(results) - 1:
                relationships["next"] = [results[i + 1].chunk_data.chunk_id]

            result.chunk_data.relationships = relationships
