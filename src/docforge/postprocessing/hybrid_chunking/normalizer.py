"""
MinerU Document Normalizer

Transforms StandardizedDocumentOutput (from MinerU/processors) into
NormalizedDocument with hierarchical section structure.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
)
from .interfaces import IDocumentNormalizer
from .normalized_document import (
    NormalizedDocument,
    NormalizedSection,
    NormalizedParagraph,
    NormalizedHeading,
    HeadingLevel,
)

logger = logging.getLogger(__name__)


class MinerUDocumentNormalizer(IDocumentNormalizer):
    """
    Normalizes MinerU/processor output into common document model.

    This normalizer:
    1. Extracts document title from first H1 or document metadata
    2. Builds section hierarchy based on heading levels
    3. Groups paragraphs under their respective sections
    4. Pre-splits sentences for efficient sentence-level chunking
    5. Preserves page numbers and element IDs for traceability
    """

    # Sentence splitting patterns
    SENTENCE_END_PATTERN = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z])|'  # Standard sentence end
        r'(?<=[.!?])\s*$|'  # End of text
        r'(?<=[.!?])\s*\n'  # Sentence end at newline
    )

    def __init__(self, language: str = "en"):
        """
        Initialize normalizer.

        Args:
            language: Language code for sentence splitting (default: "en")
        """
        self.language = language

    def normalize(
        self,
        document: StandardizedDocumentOutput,
        document_id: str = None,
    ) -> NormalizedDocument:
        """
        Normalize MinerU output to common document model.

        Args:
            document: StandardizedDocumentOutput from processor
            document_id: Optional document identifier

        Returns:
            NormalizedDocument with hierarchical section structure
        """
        # Extract title
        title = self._extract_title(document)

        # Build section hierarchy
        sections, heading_hierarchy = self._build_section_hierarchy(document)

        # Calculate statistics
        page_count = document.document_structure.total_pages or 1
        total_words = sum(s.total_word_count for s in sections)

        # Build source metadata
        source_metadata = {
            "processor_name": document.processing_metadata.processor_name,
            "processor_version": document.processing_metadata.processor_version,
            "processing_timestamp": document.processing_metadata.processing_timestamp.isoformat()
            if document.processing_metadata.processing_timestamp
            else None,
            "original_element_count": len(document.content_elements),
            **document.document_metadata,
        }

        return NormalizedDocument.create(
            title=title,
            sections=sections,
            page_count=page_count,
            source_document_id=document_id,
            source_metadata=source_metadata,
        )

    def _extract_title(self, document: StandardizedDocumentOutput) -> Optional[str]:
        """Extract document title from first H1 or metadata."""
        # Try document metadata first
        if document.document_metadata.get("title"):
            return document.document_metadata["title"]

        # Look for first H1 heading
        for element in document.content_elements:
            if self._is_heading(element):
                level = element.metadata.get("level", 1)
                if level == 1:
                    return element.content.strip()

        # Fall back to filename if available
        return document.document_metadata.get("filename")

    def _build_section_hierarchy(
        self, document: StandardizedDocumentOutput
    ) -> Tuple[List[NormalizedSection], Dict[str, NormalizedHeading]]:
        """
        Build hierarchical section structure from content elements.

        Returns:
            Tuple of (top-level sections, heading lookup dictionary)
        """
        heading_hierarchy: Dict[str, NormalizedHeading] = {}
        sections: List[NormalizedSection] = []

        # Stack for tracking section hierarchy
        # Each entry: (level, section)
        section_stack: List[Tuple[int, NormalizedSection]] = []

        # Current accumulated paragraphs (before first heading or between headings)
        current_paragraphs: List[NormalizedParagraph] = []
        current_page_numbers: List[int] = []
        current_element_ids: List[str] = []

        # Track heading path for breadcrumb
        heading_path_stack: List[str] = []

        for element in document.content_elements:
            page_num = self._get_page_number(element)

            if self._is_heading(element):
                # Finalize any pending paragraphs into current section
                if current_paragraphs:
                    self._add_paragraphs_to_section(
                        section_stack,
                        sections,
                        current_paragraphs,
                        current_page_numbers,
                        current_element_ids,
                    )
                    current_paragraphs = []
                    current_page_numbers = []
                    current_element_ids = []

                # Create heading
                level = element.metadata.get("level", 1)
                heading = NormalizedHeading.create(
                    text=element.content,
                    level=level,
                    page_number=page_num,
                    source_element_ids=[element.element_id],
                )
                heading_hierarchy[heading.id] = heading

                # Update heading path stack
                while heading_path_stack and len(heading_path_stack) >= level:
                    heading_path_stack.pop()
                heading_path_stack.append(heading.text)

                # Create new section
                section = NormalizedSection.create(
                    heading=heading,
                    paragraphs=[],
                    page_numbers=[page_num],
                    source_element_ids=[element.element_id],
                )
                section.heading_path = list(heading_path_stack)

                # Integrate into hierarchy
                self._integrate_section(section_stack, sections, section, level)

            elif self._is_paragraph(element):
                # Create paragraph with sentence splitting
                sentences = self._split_sentences(element.content)
                paragraph = NormalizedParagraph.create(
                    text=element.content,
                    page_number=page_num,
                    sentences=sentences,
                    source_element_ids=[element.element_id],
                )
                current_paragraphs.append(paragraph)
                if page_num not in current_page_numbers:
                    current_page_numbers.append(page_num)
                current_element_ids.append(element.element_id)

        # Finalize any remaining paragraphs
        if current_paragraphs:
            self._add_paragraphs_to_section(
                section_stack,
                sections,
                current_paragraphs,
                current_page_numbers,
                current_element_ids,
            )

        return sections, heading_hierarchy

    def _integrate_section(
        self,
        section_stack: List[Tuple[int, NormalizedSection]],
        sections: List[NormalizedSection],
        new_section: NormalizedSection,
        level: int,
    ):
        """Integrate a new section into the hierarchy based on heading level."""
        # Pop sections from stack that are at same or deeper level
        while section_stack and section_stack[-1][0] >= level:
            section_stack.pop()

        if section_stack:
            # Add as child to parent section
            parent = section_stack[-1][1]
            parent.children.append(new_section)
            if new_section.heading:
                new_section.heading.parent_id = (
                    parent.heading.id if parent.heading else None
                )
        else:
            # Top-level section
            sections.append(new_section)

        # Push new section onto stack
        section_stack.append((level, new_section))

    def _add_paragraphs_to_section(
        self,
        section_stack: List[Tuple[int, NormalizedSection]],
        sections: List[NormalizedSection],
        paragraphs: List[NormalizedParagraph],
        page_numbers: List[int],
        element_ids: List[str],
    ):
        """Add accumulated paragraphs to current section or create root section."""
        if section_stack:
            # Add to current section
            current_section = section_stack[-1][1]
            current_section.paragraphs.extend(paragraphs)
            for page in page_numbers:
                if page not in current_section.page_numbers:
                    current_section.page_numbers.append(page)
            current_section.source_element_ids.extend(element_ids)
        else:
            # Create root section without heading
            root_section = NormalizedSection.create(
                heading=None,
                paragraphs=paragraphs,
                page_numbers=page_numbers,
                source_element_ids=element_ids,
            )
            sections.append(root_section)
            section_stack.append((0, root_section))

    def _is_heading(self, element: ContentElement) -> bool:
        """Check if element is a heading."""
        content_type = element.content_type
        if isinstance(content_type, str):
            return content_type.lower() == "heading"
        return content_type == ContentType.HEADING

    def _is_paragraph(self, element: ContentElement) -> bool:
        """Check if element is paragraph or text content."""
        content_type = element.content_type
        if isinstance(content_type, str):
            return content_type.lower() in ("paragraph", "text")
        return content_type in (ContentType.PARAGRAPH, ContentType.TEXT)

    def _get_page_number(self, element: ContentElement) -> int:
        """Extract page number from element, defaulting to 1."""
        # Check position dict first
        if element.position and "page" in element.position:
            return int(element.position["page"])

        # Check metadata
        if element.metadata and "page" in element.metadata:
            return int(element.metadata["page"])

        return 1

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        if not text:
            return []

        # Use regex to split on sentence boundaries
        sentences = self.SENTENCE_END_PATTERN.split(text)

        # Clean up and filter empty
        result = []
        for s in sentences:
            s = s.strip()
            if s:
                result.append(s)

        # If no splits found, return whole text as single sentence
        if not result:
            return [text.strip()]

        return result
