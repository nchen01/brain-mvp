"""Text document processor for plain text files."""

import logging
from typing import List, Dict, Any
from pathlib import Path

from .base_processor import BaseDocumentProcessor
from .schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingMetadata,
    ProcessingStatus,
    create_content_element,
    create_processing_metadata,
    create_document_structure
)

logger = logging.getLogger(__name__)


class TextDocumentProcessor(BaseDocumentProcessor):
    """Processor for plain text documents."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the text processor."""
        super().__init__(config)
        self.processor_name = "TextDocumentProcessor"
        self.processor_version = "1.0.0"
        
        # Default configuration
        self.encoding = self.config.get("encoding", "utf-8")
        self.preserve_whitespace = self.config.get("preserve_whitespace", True)
        self.detect_structure = self.config.get("detect_structure", True)
        self.max_line_length = self.config.get("max_line_length", 1000)
    
    def get_supported_formats(self) -> List[str]:
        """Get supported text file formats."""
        return ['.txt', '.md', '.markdown', '.rst', '.rtf']
    
    def _process_document(
        self,
        file_path: str,
        file_content: bytes,
        **kwargs
    ) -> StandardizedDocumentOutput:
        """Process a text document."""
        try:
            # Decode text content
            text_content = self._decode_content(file_content)
            
            # Extract metadata
            file_metadata = self._extract_metadata_from_path(file_path)
            
            # Process content into elements
            content_elements = self._extract_content_elements(text_content, file_path)
            
            # Create processing metadata
            processing_metadata = create_processing_metadata(
                processor_name=self.processor_name,
                processor_version=self.processor_version,
                processing_duration=0.0,  # Will be set by base class
                input_file_info=file_metadata,
                processing_parameters={
                    "encoding": self.encoding,
                    "preserve_whitespace": self.preserve_whitespace,
                    "detect_structure": self.detect_structure
                }
            )
            
            # Create document structure
            element_counts = {}
            for element in content_elements:
                element_type = element.content_type.value if hasattr(element.content_type, 'value') else str(element.content_type)
                element_counts[element_type] = element_counts.get(element_type, 0) + 1
            
            document_structure = create_document_structure(
                total_elements=len(content_elements),
                element_counts=element_counts,
                has_tables=False,
                has_images=False,
                language=self._detect_language(text_content),
                encoding=self.encoding,
                total_pages=1  # Text files are considered single page
            )
            
            # Generate plain text and markdown
            plain_text = self._generate_plain_text(content_elements)
            markdown_text = self._generate_markdown(content_elements, file_path)
            
            return StandardizedDocumentOutput(
                content_elements=content_elements,
                tables=[],  # Text files don't have structured tables
                images=[],  # Text files don't have images
                document_metadata=file_metadata,
                document_structure=document_structure,
                processing_metadata=processing_metadata,
                processing_status=ProcessingStatus.SUCCESS,
                plain_text=plain_text,
                markdown_text=markdown_text
            )
            
        except Exception as e:
            logger.error(f"Error processing text document {file_path}: {e}")
            raise
    
    def _decode_content(self, file_content: bytes) -> str:
        """Decode file content to text."""
        try:
            # Try specified encoding first
            return file_content.decode(self.encoding)
        except UnicodeDecodeError:
            # Try common encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
            
            for encoding in encodings:
                try:
                    decoded = file_content.decode(encoding)
                    logger.warning(f"Used fallback encoding {encoding} instead of {self.encoding}")
                    return decoded
                except UnicodeDecodeError:
                    continue
            
            # Last resort: decode with errors ignored
            logger.warning("Using error-tolerant decoding")
            return file_content.decode(self.encoding, errors='ignore')
    
    def _extract_content_elements(self, text_content: str, file_path: str) -> List[ContentElement]:
        """Extract content elements from text."""
        elements = []
        lines = text_content.splitlines()
        
        file_extension = Path(file_path).suffix.lower()
        
        for i, line in enumerate(lines):
            # Skip empty lines unless preserving whitespace
            if not line.strip() and not self.preserve_whitespace:
                continue
            
            # Truncate very long lines
            if len(line) > self.max_line_length:
                line = line[:self.max_line_length] + "..."
                logger.warning(f"Truncated long line {i+1} in {file_path}")
            
            element_id = f"line_{i+1}"
            content_type = self._detect_content_type(line, file_extension)
            
            element = create_content_element(
                element_id=element_id,
                content_type=content_type,
                content=line,
                metadata={
                    "line_number": i + 1,
                    "original_length": len(lines[i]) if i < len(lines) else 0
                },
                position={
                    "line": i + 1,
                    "start_char": sum(len(l) + 1 for l in lines[:i]),
                    "end_char": sum(len(l) + 1 for l in lines[:i+1]) - 1
                }
            )
            
            elements.append(element)
        
        return elements
    
    def _detect_content_type(self, line: str, file_extension: str) -> ContentType:
        """Detect the type of content for a line."""
        stripped_line = line.strip()
        
        if not stripped_line:
            return ContentType.TEXT
        
        # Markdown-specific detection
        if file_extension in ['.md', '.markdown']:
            # Headers
            if stripped_line.startswith('#'):
                return ContentType.HEADING
            
            # Lists
            if stripped_line.startswith(('- ', '* ', '+ ')) or \
               (len(stripped_line) > 2 and stripped_line[0].isdigit() and stripped_line[1:3] == '. '):
                return ContentType.LIST
            
            # Code blocks
            if stripped_line.startswith('```') or stripped_line.startswith('    '):
                return ContentType.CODE
            
            # Quotes
            if stripped_line.startswith('>'):
                return ContentType.QUOTE
        
        # RST-specific detection
        elif file_extension == '.rst':
            # Headers (underlined)
            if len(stripped_line) > 0 and all(c in '=-~^"' for c in stripped_line):
                return ContentType.HEADING
            
            # Code blocks
            if stripped_line.startswith('::') or line.startswith('    '):
                return ContentType.CODE
        
        # General detection
        # All caps might be a heading
        if stripped_line.isupper() and len(stripped_line) > 2:
            return ContentType.HEADING
        
        # Lines that look like lists
        if stripped_line.startswith(('• ', '◦ ', '▪ ', '▫ ')):
            return ContentType.LIST
        
        # Default to paragraph for substantial content
        if len(stripped_line) > 10:
            return ContentType.PARAGRAPH
        
        return ContentType.TEXT
    
    def _detect_language(self, text_content: str) -> str:
        """Basic language detection."""
        # Very simple language detection based on common words
        # In a real implementation, you might use a proper language detection library
        
        sample_text = text_content[:1000].lower()
        
        # English indicators
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        english_count = sum(1 for word in english_words if word in sample_text)
        
        if english_count >= 3:
            return "en"
        
        return "unknown"
    
    def _generate_plain_text(self, content_elements: List[ContentElement]) -> str:
        """Generate plain text from content elements."""
        lines = []
        
        for element in content_elements:
            if element.content_type in [ContentType.TEXT, ContentType.PARAGRAPH, ContentType.HEADING]:
                lines.append(element.content)
            elif element.content_type == ContentType.LIST:
                lines.append(f"• {element.content.lstrip('- * + ')}")
            else:
                lines.append(element.content)
        
        return '\n'.join(lines)
    
    def _generate_markdown(self, content_elements: List[ContentElement], file_path: str) -> str:
        """Generate markdown from content elements."""
        file_extension = Path(file_path).suffix.lower()
        
        # If it's already markdown, return as-is
        if file_extension in ['.md', '.markdown']:
            return '\n'.join(element.content for element in content_elements)
        
        # Convert other formats to markdown
        lines = []
        
        for element in content_elements:
            if element.content_type == ContentType.HEADING:
                # Convert to markdown heading
                lines.append(f"# {element.content}")
            elif element.content_type == ContentType.LIST:
                # Ensure proper markdown list format
                content = element.content.lstrip('- * + •◦▪▫ ')
                lines.append(f"- {content}")
            elif element.content_type == ContentType.CODE:
                # Wrap in code block
                lines.append(f"```\n{element.content}\n```")
            elif element.content_type == ContentType.QUOTE:
                # Ensure proper markdown quote format
                content = element.content.lstrip('> ')
                lines.append(f"> {content}")
            else:
                lines.append(element.content)
        
        return '\n\n'.join(lines)