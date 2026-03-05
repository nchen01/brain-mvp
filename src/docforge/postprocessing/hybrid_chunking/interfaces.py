"""
Abstract interfaces for hybrid chunking pipeline components.

These interfaces define the contracts for:
- Document normalization (MinerU output → common model)
- Section routing (length-based classification)
- Structure-aware chunking (respecting document boundaries)
"""

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from docforge.preprocessing.schemas import StandardizedDocumentOutput
    from docforge.postprocessing.schemas import ChunkData
    from .normalized_document import NormalizedDocument, NormalizedSection
    from .config import SectionSizeCategory


class IDocumentNormalizer(ABC):
    """Interface for normalizing raw document output to common model."""

    @abstractmethod
    def normalize(
        self,
        document: "StandardizedDocumentOutput",
        document_id: str = None,
    ) -> "NormalizedDocument":
        """
        Normalize MinerU/processor output to common document model.

        Args:
            document: StandardizedDocumentOutput from MinerU or other processors
            document_id: Optional document identifier

        Returns:
            NormalizedDocument with sections, headings, paragraphs, and metadata
        """
        pass


class ISectionRouter(ABC):
    """Interface for length-based section routing."""

    @abstractmethod
    def classify_section(self, section: "NormalizedSection") -> "SectionSizeCategory":
        """
        Classify section as SHORT, MEDIUM, or LONG based on word count.

        Args:
            section: NormalizedSection to classify

        Returns:
            SectionSizeCategory enum value
        """
        pass

    @abstractmethod
    def route_section(self, section: "NormalizedSection") -> str:
        """
        Determine chunking strategy for a section based on its classification.

        Args:
            section: NormalizedSection to route

        Returns:
            Strategy name string (e.g., "keep_or_merge", "recursive_split")
        """
        pass

    @abstractmethod
    def group_mergeable_sections(
        self, sections: List["NormalizedSection"]
    ) -> List[List["NormalizedSection"]]:
        """
        Group adjacent short sections that can be merged.

        Args:
            sections: List of sections to analyze

        Returns:
            List of section groups (each group may contain 1+ sections to merge)
        """
        pass


class IStructureAwareChunker(ABC):
    """Interface for structure-aware recursive chunking."""

    @abstractmethod
    def chunk_section(
        self,
        section: "NormalizedSection",
        category: "SectionSizeCategory",
        heading_context: str = "",
    ) -> List["ChunkData"]:
        """
        Chunk a single section using appropriate strategy for its size category.

        Args:
            section: NormalizedSection to chunk
            category: Size category (SHORT, MEDIUM, LONG)
            heading_context: Parent heading context for chunk metadata

        Returns:
            List of ChunkData objects
        """
        pass

    @abstractmethod
    def chunk_document(self, document: "NormalizedDocument") -> List["ChunkData"]:
        """
        Chunk entire normalized document respecting structure boundaries.

        Args:
            document: NormalizedDocument to chunk

        Returns:
            List of ChunkData objects with routing metadata
        """
        pass
