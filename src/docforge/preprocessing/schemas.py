"""Standardized output format schemas for document processors."""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from enum import Enum


class ContentType(str, Enum):
    """Types of content elements."""
    TEXT = "text"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    QUOTE = "quote"
    LINK = "link"
    METADATA = "metadata"


class ProcessingStatus(str, Enum):
    """Processing status values."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ContentElement(BaseModel):
    """Individual content element in the processed document."""
    model_config = ConfigDict(use_enum_values=True)
    
    element_id: str = Field(..., description="Unique identifier for this element")
    content_type: ContentType = Field(..., description="Type of content element")
    content: str = Field(..., description="The actual content text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Element-specific metadata")
    position: Dict[str, Any] = Field(default_factory=dict, description="Position information (page, coordinates, etc.)")
    formatting: Dict[str, Any] = Field(default_factory=dict, description="Formatting information (font, style, etc.)")
    confidence: float = Field(default=1.0, description="Confidence score for extraction (0-1)")


class TableData(BaseModel):
    """Structured table data."""
    
    headers: List[str] = Field(default_factory=list, description="Table column headers")
    rows: List[List[str]] = Field(default_factory=list, description="Table row data")
    caption: Optional[str] = Field(None, description="Table caption if available")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Table-specific metadata")


class ImageData(BaseModel):
    """Image data and metadata."""
    
    image_id: str = Field(..., description="Unique identifier for the image")
    file_path: Optional[str] = Field(None, description="Path to extracted image file")
    base64_data: Optional[str] = Field(None, description="Base64 encoded image data")
    alt_text: Optional[str] = Field(None, description="Alternative text description")
    caption: Optional[str] = Field(None, description="Image caption if available")
    dimensions: Dict[str, int] = Field(default_factory=dict, description="Image dimensions (width, height)")
    format: Optional[str] = Field(None, description="Image format (png, jpg, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Image-specific metadata")


class ProcessingMetadata(BaseModel):
    """Metadata about the processing operation."""
    
    processor_name: str = Field(..., description="Name of the processor used")
    processor_version: str = Field(..., description="Version of the processor")
    processing_timestamp: datetime = Field(..., description="When processing occurred")
    processing_duration: float = Field(..., description="Processing time in seconds")
    input_file_info: Dict[str, Any] = Field(default_factory=dict, description="Information about input file")
    processing_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters used for processing")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    errors: List[str] = Field(default_factory=list, description="Processing errors")


class DocumentStructure(BaseModel):
    """Document structure information."""
    
    total_pages: Optional[int] = Field(None, description="Total number of pages")
    total_elements: int = Field(..., description="Total number of content elements")
    element_counts: Dict[str, int] = Field(default_factory=dict, description="Count of each element type")
    has_tables: bool = Field(default=False, description="Whether document contains tables")
    has_images: bool = Field(default=False, description="Whether document contains images")
    language: Optional[str] = Field(None, description="Detected document language")
    encoding: Optional[str] = Field(None, description="Document encoding")


class StandardizedDocumentOutput(BaseModel):
    """Standardized output format for all document processors."""
    
    # Core content
    content_elements: List[ContentElement] = Field(default_factory=list, description="Ordered list of content elements")
    
    # Structured data
    tables: List[TableData] = Field(default_factory=list, description="Extracted tables")
    images: List[ImageData] = Field(default_factory=list, description="Extracted images")
    
    # Document metadata
    document_metadata: Dict[str, Any] = Field(default_factory=dict, description="Document-level metadata")
    document_structure: DocumentStructure = Field(..., description="Document structure information")
    
    # Processing information
    processing_metadata: ProcessingMetadata = Field(..., description="Processing metadata")
    processing_status: ProcessingStatus = Field(..., description="Overall processing status")
    
    # Full text representations
    plain_text: str = Field(default="", description="Plain text version of the document")
    markdown_text: str = Field(default="", description="Markdown version of the document")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ProcessorError(BaseModel):
    """Error information from processor."""
    
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code if available")
    stack_trace: Optional[str] = Field(None, description="Stack trace for debugging")
    timestamp: datetime = Field(..., description="When error occurred")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ProcessingResult(BaseModel):
    """Result of document processing operation."""
    
    success: bool = Field(..., description="Whether processing was successful")
    output: Optional[StandardizedDocumentOutput] = Field(None, description="Processed document output")
    error: Optional[ProcessorError] = Field(None, description="Error information if processing failed")
    processing_time: float = Field(..., description="Total processing time in seconds")
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


def create_content_element(
    element_id: str,
    content_type: ContentType,
    content: str,
    **kwargs
) -> ContentElement:
    """Helper function to create a content element."""
    return ContentElement(
        element_id=element_id,
        content_type=content_type,
        content=content,
        **kwargs
    )


def create_table_data(
    headers: List[str],
    rows: List[List[str]],
    **kwargs
) -> TableData:
    """Helper function to create table data."""
    return TableData(
        headers=headers,
        rows=rows,
        **kwargs
    )


def create_image_data(
    image_id: str,
    **kwargs
) -> ImageData:
    """Helper function to create image data."""
    return ImageData(
        image_id=image_id,
        **kwargs
    )


def create_processing_metadata(
    processor_name: str,
    processor_version: str,
    processing_duration: float,
    **kwargs
) -> ProcessingMetadata:
    """Helper function to create processing metadata."""
    return ProcessingMetadata(
        processor_name=processor_name,
        processor_version=processor_version,
        processing_timestamp=datetime.now(timezone.utc),
        processing_duration=processing_duration,
        **kwargs
    )


def create_document_structure(
    total_elements: int,
    **kwargs
) -> DocumentStructure:
    """Helper function to create document structure."""
    return DocumentStructure(
        total_elements=total_elements,
        **kwargs
    )


def create_standardized_output(
    content_elements: List[ContentElement],
    processing_metadata: ProcessingMetadata,
    processing_status: ProcessingStatus = ProcessingStatus.SUCCESS,
    total_pages: Optional[int] = None,
    **kwargs
) -> StandardizedDocumentOutput:
    """Helper function to create standardized document output."""
    
    # Calculate document structure
    element_counts = {}
    for element in content_elements:
        # content_type is already a string due to use_enum_values=True
        element_type = element.content_type if isinstance(element.content_type, str) else element.content_type.value
        element_counts[element_type] = element_counts.get(element_type, 0) + 1
    
    document_structure = DocumentStructure(
        total_pages=total_pages,
        total_elements=len(content_elements),
        element_counts=element_counts,
        has_tables="table" in element_counts,
        has_images="image" in element_counts
    )
    
    # Generate plain text
    plain_text = "\n".join([
        element.content for element in content_elements
        if element.content_type in [ContentType.TEXT.value, ContentType.PARAGRAPH.value, ContentType.HEADING.value]
    ])
    
    # Generate markdown text (basic implementation)
    markdown_lines = []
    for element in content_elements:
        # Element content_type is already a string value due to use_enum_values=True
        content_type = element.content_type
        
        if content_type == ContentType.HEADING.value or content_type == "heading":
            level = element.metadata.get("level", 1)
            markdown_lines.append(f"{'#' * level} {element.content}")
        elif content_type == ContentType.PARAGRAPH.value or content_type == "paragraph":
            markdown_lines.append(element.content)
        elif content_type == ContentType.LIST.value or content_type == "list":
            markdown_lines.append(f"- {element.content}")
        elif content_type == ContentType.CODE.value or content_type == "code":
            markdown_lines.append(f"```\n{element.content}\n```")
        elif content_type == ContentType.QUOTE.value or content_type == "quote":
            markdown_lines.append(f"> {element.content}")
        else:
            markdown_lines.append(element.content)
    
    markdown_text = "\n\n".join(markdown_lines)
    
    return StandardizedDocumentOutput(
        content_elements=content_elements,
        document_structure=document_structure,
        processing_metadata=processing_metadata,
        processing_status=processing_status,
        plain_text=plain_text,
        markdown_text=markdown_text,
        **kwargs
    )