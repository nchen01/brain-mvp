"""
Normalized Document Model

Common document representation that serves as input to the structure-aware chunker.
Normalizes MinerU output into a hierarchical structure with:
- Document title
- Section headings with levels (H1-H6)
- Paragraphs with pre-split sentences
- Page number tracking
- Element ID traceability
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import IntEnum
from datetime import datetime
import uuid


class HeadingLevel(IntEnum):
    """Heading levels for document hierarchy."""

    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    H6 = 6

    @classmethod
    def from_int(cls, level: int) -> "HeadingLevel":
        """Convert integer to HeadingLevel, clamping to valid range."""
        clamped = max(1, min(6, level))
        return cls(clamped)


@dataclass
class NormalizedHeading:
    """Normalized heading with hierarchy information."""

    id: str
    text: str
    level: HeadingLevel
    page_number: int

    # Parent heading ID for hierarchy tracking
    parent_id: Optional[str] = None

    # Original source element IDs from MinerU output
    source_element_ids: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        text: str,
        level: int,
        page_number: int,
        parent_id: str = None,
        source_element_ids: List[str] = None,
    ) -> "NormalizedHeading":
        """Factory method to create a heading with auto-generated ID."""
        return cls(
            id=f"heading_{uuid.uuid4().hex[:8]}",
            text=text.strip(),
            level=HeadingLevel.from_int(level),
            page_number=page_number,
            parent_id=parent_id,
            source_element_ids=source_element_ids or [],
        )


@dataclass
class NormalizedParagraph:
    """Normalized paragraph within a section."""

    id: str
    text: str
    page_number: int

    # Pre-split sentences for efficient sentence-level chunking
    sentences: List[str] = field(default_factory=list)

    # Original source element IDs
    source_element_ids: List[str] = field(default_factory=list)

    # Computed word count
    word_count: int = 0

    def __post_init__(self):
        """Calculate word count if not provided."""
        if not self.word_count and self.text:
            self.word_count = len(self.text.split())

    @classmethod
    def create(
        cls,
        text: str,
        page_number: int,
        sentences: List[str] = None,
        source_element_ids: List[str] = None,
    ) -> "NormalizedParagraph":
        """Factory method to create a paragraph with auto-generated ID."""
        return cls(
            id=f"para_{uuid.uuid4().hex[:8]}",
            text=text.strip(),
            page_number=page_number,
            sentences=sentences or [],
            source_element_ids=source_element_ids or [],
        )


@dataclass
class NormalizedSection:
    """
    Normalized section containing a heading and content.

    Sections form a hierarchy matching the document's heading structure.
    Each section contains paragraphs and may have child subsections.
    """

    id: str

    # Optional heading (root sections may not have headings)
    heading: Optional[NormalizedHeading]

    # Paragraphs in this section (not including subsections)
    paragraphs: List[NormalizedParagraph]

    # Child subsections (for hierarchical structure)
    children: List["NormalizedSection"] = field(default_factory=list)

    # Page numbers spanned by this section
    page_numbers: List[int] = field(default_factory=list)

    # Original source element IDs
    source_element_ids: List[str] = field(default_factory=list)

    # Heading path from root (populated during normalization)
    _heading_path: List[str] = field(default_factory=list, repr=False)

    @property
    def word_count(self) -> int:
        """Total word count of section content (excluding children)."""
        count = sum(p.word_count for p in self.paragraphs)
        if self.heading:
            count += len(self.heading.text.split())
        return count

    @property
    def total_word_count(self) -> int:
        """Total word count including all children recursively."""
        count = self.word_count
        for child in self.children:
            count += child.total_word_count
        return count

    @property
    def full_text(self) -> str:
        """Get full text of section (heading + paragraphs)."""
        parts = []
        if self.heading:
            parts.append(self.heading.text)
        parts.extend(p.text for p in self.paragraphs)
        return "\n\n".join(parts)

    @property
    def heading_path(self) -> List[str]:
        """Get hierarchical heading path (breadcrumb)."""
        return self._heading_path

    @heading_path.setter
    def heading_path(self, path: List[str]):
        """Set heading path."""
        self._heading_path = path

    @property
    def heading_text(self) -> str:
        """Get heading text or empty string if no heading."""
        return self.heading.text if self.heading else ""

    @property
    def heading_level(self) -> Optional[int]:
        """Get heading level or None if no heading."""
        return self.heading.level.value if self.heading else None

    def get_all_paragraphs(self) -> List[NormalizedParagraph]:
        """Get all paragraphs including from children recursively."""
        paragraphs = list(self.paragraphs)
        for child in self.children:
            paragraphs.extend(child.get_all_paragraphs())
        return paragraphs

    @classmethod
    def create(
        cls,
        heading: NormalizedHeading = None,
        paragraphs: List[NormalizedParagraph] = None,
        children: List["NormalizedSection"] = None,
        page_numbers: List[int] = None,
        source_element_ids: List[str] = None,
    ) -> "NormalizedSection":
        """Factory method to create a section with auto-generated ID."""
        return cls(
            id=f"section_{uuid.uuid4().hex[:8]}",
            heading=heading,
            paragraphs=paragraphs or [],
            children=children or [],
            page_numbers=page_numbers or [],
            source_element_ids=source_element_ids or [],
        )


@dataclass
class NormalizedDocument:
    """
    Normalized document model - common input format for hybrid chunker.

    This is the canonical representation of a document after normalization
    from MinerU or other processor outputs. It provides:
    - Hierarchical section structure
    - Heading hierarchy tracking
    - Page number preservation
    - Element ID traceability
    """

    id: str

    # Document title (may be extracted from first H1 or filename)
    title: Optional[str]

    # Top-level sections (may contain nested children)
    sections: List[NormalizedSection]

    # Document statistics
    page_count: int
    total_word_count: int

    # Source document reference
    source_document_id: str

    # Heading lookup table for quick access
    heading_hierarchy: Dict[str, NormalizedHeading] = field(default_factory=dict)

    # Original source metadata
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    # Processing timestamp
    normalized_at: datetime = field(default_factory=datetime.utcnow)

    def get_all_sections_flat(self) -> List[NormalizedSection]:
        """Get all sections including nested ones as flat list (depth-first)."""
        result = []

        def collect(sections: List[NormalizedSection]):
            for section in sections:
                result.append(section)
                collect(section.children)

        collect(self.sections)
        return result

    def get_sections_at_level(self, level: int) -> List[NormalizedSection]:
        """Get all sections at a specific heading level."""
        return [
            s
            for s in self.get_all_sections_flat()
            if s.heading and s.heading.level.value == level
        ]

    def get_leaf_sections(self) -> List[NormalizedSection]:
        """Get sections that have no children (leaf nodes)."""
        return [s for s in self.get_all_sections_flat() if not s.children]

    @property
    def section_count(self) -> int:
        """Total number of sections at all levels."""
        return len(self.get_all_sections_flat())

    @classmethod
    def create(
        cls,
        title: str = None,
        sections: List[NormalizedSection] = None,
        page_count: int = 1,
        source_document_id: str = None,
        source_metadata: Dict[str, Any] = None,
    ) -> "NormalizedDocument":
        """Factory method to create a document with auto-generated ID."""
        sections = sections or []
        total_words = sum(s.total_word_count for s in sections)

        return cls(
            id=f"doc_{uuid.uuid4().hex[:8]}",
            title=title,
            sections=sections,
            page_count=page_count,
            total_word_count=total_words,
            source_document_id=source_document_id or f"unknown_{uuid.uuid4().hex[:8]}",
            source_metadata=source_metadata or {},
        )
