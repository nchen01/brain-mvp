"""DocForge preprocessing package.

This package provides document processing capabilities with standardized output formats,
validation, and quality assurance.
"""

from .base_processor import BaseDocumentProcessor
from .mineru_processor import MinerUProcessor
from .markitdown_processor import MarkItDownProcessor
from .text_processor import TextDocumentProcessor
from .processor_factory import ProcessorFactory
from .router import DocumentPreprocessingRouter
from .schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingStatus,
    TableData,
    ImageData,
    ProcessingMetadata,
    DocumentStructure,
    ProcessorError,
    ProcessingResult
)
from .output_validator import (
    OutputFormatValidator,
    OutputFormatStandardizer,
    FormatConverter,
    QualityAssuranceChecker,
    validate_and_standardize_output,
    compare_processor_outputs,
    convert_output_format
)
from .format_utils import (
    FormatConsistencyManager,
    OutputFormatConverter,
    create_format_consistency_report,
    validate_processor_output_quality,
    ensure_format_consistency
)

__all__ = [
    # Core processors
    'BaseDocumentProcessor',
    'MinerUProcessor', 
    'MarkItDownProcessor',
    'TextDocumentProcessor',
    'ProcessorFactory',
    'DocumentPreprocessingRouter',
    
    # Schemas
    'StandardizedDocumentOutput',
    'ContentElement',
    'ContentType',
    'ProcessingStatus',
    'TableData',
    'ImageData',
    'ProcessingMetadata',
    'DocumentStructure',
    'ProcessorError',
    'ProcessingResult',
    
    # Validation and standardization
    'OutputFormatValidator',
    'OutputFormatStandardizer',
    'FormatConverter',
    'QualityAssuranceChecker',
    'validate_and_standardize_output',
    'compare_processor_outputs',
    'convert_output_format',
    
    # Format utilities
    'FormatConsistencyManager',
    'OutputFormatConverter',
    'create_format_consistency_report',
    'validate_processor_output_quality',
    'ensure_format_consistency'
]