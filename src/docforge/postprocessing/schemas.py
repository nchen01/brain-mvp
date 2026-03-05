"""Schemas for post-processing components."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict

from docforge.preprocessing.schemas import StandardizedDocumentOutput


class DocumentSummaries(BaseModel):
    """Summaries generated for a document and its sections.

    Produced by SummarizationService and threaded through chunking so that
    every Chunk carries the doc-level and section-level context strings used
    to build enriched embedding inputs.
    """

    doc_summary: str = Field(default="", description="2-3 sentence document overview")
    section_summaries: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps heading element_id to 1-2 sentence section summary",
    )


class ProcessingMethod(str, Enum):
    """Available post-processing methods."""
    PARAGRAPH_CHUNKING = "paragraph_chunking"
    SECTION_CHUNKING = "section_chunking"
    SENTENCE_CHUNKING = "sentence_chunking"
    SEMANTIC_CHUNKING = "semantic_chunking"
    ABBREVIATION_EXPANSION = "abbreviation_expansion"
    CONTENT_ENHANCEMENT = "content_enhancement"


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    SEMANTIC = "semantic"
    FIXED_SIZE = "fixed_size"
    RECURSIVE = "recursive"  # LangChain-style recursive text splitting
    SLIDING_WINDOW = "sliding_window"
    HIERARCHICAL = "hierarchical"
    SECTION_BASED = "section_based"
    HYBRID_STRUCTURE_AWARE = "hybrid_structure_aware"  # Structure-aware with length-based routing


class ChunkType(str, Enum):
    """Types of content chunks."""
    TEXT = "text"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    LIST = "list"
    TABLE = "table"
    CODE = "code"
    QUOTE = "quote"
    MIXED = "mixed"


class ChunkMetadata(BaseModel):
    """Metadata for a content chunk."""
    chunk_id: str
    chunk_index: int
    chunk_type: ChunkType
    source_elements: List[str]  # IDs of source content elements
    page_numbers: List[int] = Field(default_factory=list)
    word_count: int
    character_count: int
    language: str = "en"
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    processing_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ChunkData(BaseModel):
    """Individual chunk of processed content."""
    chunk_id: str
    content: str
    chunk_type: ChunkType
    metadata: ChunkMetadata
    position: Dict[str, Any] = Field(default_factory=dict)
    relationships: Dict[str, List[str]] = Field(default_factory=dict)  # Related chunks

    # Summary fields populated by SummarizationService + DocumentChunker
    doc_summary: str = Field(default="", description="Document-level summary shared by all chunks")
    section_summary: str = Field(default="", description="Section-level summary for this chunk's section")
    section_path: str = Field(default="", description="Human-readable heading path (e.g. 'Intro > Background')")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class AbbreviationMapping(BaseModel):
    """Mapping for abbreviation expansion."""
    abbreviation: str
    expansion: str
    context: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    domain: Optional[str] = None
    source: Optional[str] = None


class PostProcessingConfig(BaseModel):
    """Configuration for post-processing operations."""
    methods: List[ProcessingMethod]
    chunking_strategy: Optional[ChunkingStrategy] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    enable_abbreviation_expansion: bool = False
    abbreviation_domains: List[str] = Field(default_factory=list)
    language: str = "en"
    quality_threshold: float = Field(ge=0.0, le=1.0, default=0.8)
    
    model_config = ConfigDict(use_enum_values=True)


class PostProcessingResult(BaseModel):
    """Result of post-processing operations."""
    success: bool
    chunks: List[ChunkData] = Field(default_factory=list)
    abbreviations_expanded: List[AbbreviationMapping] = Field(default_factory=list)
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class KnowledgeManagementRule(BaseModel):
    """Rule for post-processing routing decisions."""
    rule_id: str
    name: str
    description: str
    conditions: Dict[str, Any]  # Conditions for applying this rule
    actions: List[ProcessingMethod]  # Methods to apply
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class RoutingDecision(BaseModel):
    """Decision made by the post-processing router."""
    document_id: str
    selected_methods: List[ProcessingMethod]
    applied_rules: List[str]  # Rule IDs that were applied
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


def create_chunk_metadata(
    chunk_id: str,
    chunk_index: int,
    chunk_type: ChunkType,
    source_elements: List[str],
    word_count: int,
    character_count: int,
    **kwargs
) -> ChunkMetadata:
    """Helper function to create chunk metadata."""
    return ChunkMetadata(
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        chunk_type=chunk_type,
        source_elements=source_elements,
        word_count=word_count,
        character_count=character_count,
        **kwargs
    )


def create_chunk_data(
    chunk_id: str,
    content: str,
    chunk_type: ChunkType,
    metadata: ChunkMetadata,
    **kwargs
) -> ChunkData:
    """Helper function to create chunk data."""
    return ChunkData(
        chunk_id=chunk_id,
        content=content,
        chunk_type=chunk_type,
        metadata=metadata,
        **kwargs
    )