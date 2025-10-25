"""Document chunking strategies for post-processing."""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

from docforge.preprocessing.schemas import StandardizedDocumentOutput, ContentElement, ContentType
from .schemas import (
    ChunkData,
    ChunkMetadata,
    ChunkType,
    ChunkingStrategy,
    create_chunk_data,
    create_chunk_metadata
)

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """Base class for document chunkers."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the chunker."""
        self.config = config or {}
        self.chunk_size = self.config.get('chunk_size', 300)
        self.chunk_overlap = self.config.get('chunk_overlap', 50)
        self.language = self.config.get('language', 'en')
        self.min_chunk_size = self.config.get('min_chunk_size', 50)
    
    @abstractmethod
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk the document according to the strategy."""
        pass
    
    def _create_chunk(
        self,
        chunk_id: str,
        content: str,
        chunk_type: ChunkType,
        source_elements: List[str],
        chunk_index: int,
        page_numbers: List[int] = None,
        **kwargs
    ) -> ChunkData:
        """Create a chunk with metadata."""
        if not content.strip():
            return None
        
        word_count = len(content.split())
        character_count = len(content)
        
        # Skip chunks that are too small (but be more lenient for testing)
        min_size = max(10, self.min_chunk_size)  # Allow smaller chunks for testing
        if word_count < min_size:
            return None
        
        metadata = create_chunk_metadata(
            chunk_id=chunk_id,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            source_elements=source_elements,
            word_count=word_count,
            character_count=character_count,
            page_numbers=page_numbers or [],
            language=self.language,
            **kwargs
        )
        
        return create_chunk_data(
            chunk_id=chunk_id,
            content=content.strip(),
            chunk_type=chunk_type,
            metadata=metadata
        )
    
    def _get_page_numbers(self, elements: List[ContentElement]) -> List[int]:
        """Extract page numbers from content elements."""
        pages = set()
        for element in elements:
            page = element.metadata.get('page', 1)
            if isinstance(page, int):
                pages.add(page)
        return sorted(list(pages))


class ParagraphChunker(BaseChunker):
    """Chunks documents by paragraphs."""
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document by paragraphs."""
        chunks = []
        chunk_index = 0
        
        # Group consecutive paragraphs up to chunk_size
        current_chunk_content = []
        current_chunk_elements = []
        current_word_count = 0
        
        for element in document.content_elements:
            if element.content_type in [ContentType.PARAGRAPH, ContentType.TEXT]:
                element_words = len(element.content.split())
                
                # If adding this element would exceed chunk size, finalize current chunk
                if (current_word_count + element_words > self.chunk_size and 
                    current_chunk_content):
                    
                    chunk = self._create_paragraph_chunk(
                        current_chunk_content,
                        current_chunk_elements,
                        chunk_index
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_content, overlap_elements = self._create_overlap(
                        current_chunk_content, current_chunk_elements
                    )
                    current_chunk_content = overlap_content
                    current_chunk_elements = overlap_elements
                    current_word_count = sum(len(content.split()) for content in current_chunk_content)
                
                current_chunk_content.append(element.content)
                current_chunk_elements.append(element)
                current_word_count += element_words
        
        # Add final chunk
        if current_chunk_content:
            chunk = self._create_paragraph_chunk(
                current_chunk_content,
                current_chunk_elements,
                chunk_index
            )
            if chunk:
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} paragraph chunks")
        return chunks
    
    def _create_paragraph_chunk(
        self,
        content_list: List[str],
        elements: List[ContentElement],
        chunk_index: int
    ) -> Optional[ChunkData]:
        """Create a paragraph chunk."""
        if not content_list:
            return None
        
        content = "\n\n".join(content_list)
        chunk_id = f"paragraph_chunk_{chunk_index}"
        source_elements = [elem.element_id for elem in elements]
        page_numbers = self._get_page_numbers(elements)
        
        return self._create_chunk(
            chunk_id=chunk_id,
            content=content,
            chunk_type=ChunkType.PARAGRAPH,
            source_elements=source_elements,
            chunk_index=chunk_index,
            page_numbers=page_numbers
        )
    
    def _create_overlap(
        self,
        content_list: List[str],
        elements: List[ContentElement]
    ) -> Tuple[List[str], List[ContentElement]]:
        """Create overlap content for next chunk."""
        if not content_list or self.chunk_overlap <= 0:
            return [], []
        
        # Take last few items for overlap
        overlap_words = 0
        overlap_content = []
        overlap_elements = []
        
        for i in range(len(content_list) - 1, -1, -1):
            content = content_list[i]
            words = len(content.split())
            
            if overlap_words + words <= self.chunk_overlap:
                overlap_content.insert(0, content)
                overlap_elements.insert(0, elements[i])
                overlap_words += words
            else:
                break
        
        return overlap_content, overlap_elements


class SentenceChunker(BaseChunker):
    """Chunks documents by sentences."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize sentence chunker."""
        super().__init__(config)
        self.sentence_patterns = self._get_sentence_patterns()
    
    def _get_sentence_patterns(self) -> List[re.Pattern]:
        """Get sentence boundary patterns for different languages."""
        if self.language == 'en':
            return [
                re.compile(r'(?<=[.!?])\s+(?=[A-Z])'),  # Basic sentence boundaries
                re.compile(r'(?<=[.!?])\s*\n+\s*(?=[A-Z])'),  # Sentences across lines
            ]
        else:
            # Default pattern for other languages
            return [re.compile(r'(?<=[.!?])\s+')]
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document by sentences."""
        chunks = []
        chunk_index = 0
        
        # Extract sentences from all text elements
        all_sentences = []
        sentence_to_elements = {}
        
        for element in document.content_elements:
            if element.content_type in [ContentType.PARAGRAPH, ContentType.TEXT]:
                sentences = self._split_into_sentences(element.content)
                for sentence in sentences:
                    if sentence.strip():
                        all_sentences.append(sentence.strip())
                        sentence_to_elements[sentence.strip()] = element
        
        # Group sentences into chunks
        current_chunk_sentences = []
        current_word_count = 0
        
        for sentence in all_sentences:
            sentence_words = len(sentence.split())
            
            # If adding this sentence would exceed chunk size, finalize current chunk
            if (current_word_count + sentence_words > self.chunk_size and 
                current_chunk_sentences):
                
                chunk = self._create_sentence_chunk(
                    current_chunk_sentences,
                    sentence_to_elements,
                    chunk_index
                )
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_sentences = self._create_sentence_overlap(current_chunk_sentences)
                current_chunk_sentences = overlap_sentences
                current_word_count = sum(len(s.split()) for s in current_chunk_sentences)
            
            current_chunk_sentences.append(sentence)
            current_word_count += sentence_words
        
        # Add final chunk
        if current_chunk_sentences:
            chunk = self._create_sentence_chunk(
                current_chunk_sentences,
                sentence_to_elements,
                chunk_index
            )
            if chunk:
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} sentence chunks")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = [text]  # Start with full text
        
        for pattern in self.sentence_patterns:
            new_sentences = []
            for sentence in sentences:
                new_sentences.extend(pattern.split(sentence))
            sentences = new_sentences
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_sentence_chunk(
        self,
        sentences: List[str],
        sentence_to_elements: Dict[str, ContentElement],
        chunk_index: int
    ) -> Optional[ChunkData]:
        """Create a sentence chunk."""
        if not sentences:
            return None
        
        content = " ".join(sentences)
        chunk_id = f"sentence_chunk_{chunk_index}"
        
        # Get source elements
        elements = []
        for sentence in sentences:
            if sentence in sentence_to_elements:
                elements.append(sentence_to_elements[sentence])
        
        source_elements = list(set(elem.element_id for elem in elements))
        page_numbers = self._get_page_numbers(elements)
        
        return self._create_chunk(
            chunk_id=chunk_id,
            content=content,
            chunk_type=ChunkType.TEXT,
            source_elements=source_elements,
            chunk_index=chunk_index,
            page_numbers=page_numbers
        )
    
    def _create_sentence_overlap(self, sentences: List[str]) -> List[str]:
        """Create overlap sentences for next chunk."""
        if not sentences or self.chunk_overlap <= 0:
            return []
        
        overlap_words = 0
        overlap_sentences = []
        
        for i in range(len(sentences) - 1, -1, -1):
            sentence = sentences[i]
            words = len(sentence.split())
            
            if overlap_words + words <= self.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_words += words
            else:
                break
        
        return overlap_sentences


class SectionChunker(BaseChunker):
    """Chunks documents by sections based on headings."""
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document by sections."""
        chunks = []
        chunk_index = 0
        
        # Find section boundaries based on headings
        sections = self._identify_sections(document.content_elements)
        
        for section in sections:
            # If section is too large, sub-chunk it
            if self._section_too_large(section['elements']):
                sub_chunks = self._sub_chunk_section(section, chunk_index)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
            else:
                chunk = self._create_section_chunk(section, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
        
        logger.info(f"Created {len(chunks)} section chunks")
        return chunks
    
    def _identify_sections(self, elements: List[ContentElement]) -> List[Dict[str, Any]]:
        """Identify sections based on headings."""
        sections = []
        current_section = {
            'title': None,
            'level': None,
            'elements': [],
            'start_index': 0
        }
        
        for i, element in enumerate(elements):
            if element.content_type == ContentType.HEADING:
                # Finalize current section if it has content
                if current_section['elements']:
                    current_section['end_index'] = i - 1
                    sections.append(current_section)
                
                # Start new section
                level = element.metadata.get('level', 1)
                current_section = {
                    'title': element.content,
                    'level': level,
                    'elements': [element],
                    'start_index': i
                }
            else:
                current_section['elements'].append(element)
        
        # Add final section
        if current_section['elements']:
            current_section['end_index'] = len(elements) - 1
            sections.append(current_section)
        
        return sections
    
    def _section_too_large(self, elements: List[ContentElement]) -> bool:
        """Check if section is too large and needs sub-chunking."""
        total_words = sum(len(elem.content.split()) for elem in elements)
        return total_words > self.chunk_size * 1.5  # 50% larger than target
    
    def _sub_chunk_section(self, section: Dict[str, Any], start_chunk_index: int) -> List[ChunkData]:
        """Sub-chunk a large section."""
        chunks = []
        elements = section['elements']
        
        # Use paragraph chunking within the section
        paragraph_chunker = ParagraphChunker(self.config)
        
        # Create a temporary document for the section
        from docforge.preprocessing.schemas import ProcessingMetadata, DocumentStructure, ProcessingStatus, create_processing_metadata, create_document_structure
        
        processing_metadata = create_processing_metadata(
            processor_name="SectionChunker",
            processor_version="1.0.0",
            processing_duration=0.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(elements),
            total_pages=1
        )
        
        temp_doc = StandardizedDocumentOutput(
            content_elements=elements,
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=" ".join(elem.content for elem in elements),
            markdown_text=" ".join(elem.content for elem in elements)
        )
        
        sub_chunks = paragraph_chunker.chunk_document(temp_doc)
        
        # Update chunk IDs and types for section context
        for i, chunk in enumerate(sub_chunks):
            chunk.chunk_id = f"section_chunk_{start_chunk_index + i}"
            chunk.chunk_type = ChunkType.SECTION
            chunk.metadata.chunk_id = chunk.chunk_id
            chunk.metadata.chunk_index = start_chunk_index + i
            chunk.metadata.chunk_type = ChunkType.SECTION
            
            # Add section context to position metadata
            if section['title']:
                chunk.position['section_title'] = section['title']
                chunk.position['section_level'] = section['level']
        
        return sub_chunks
    
    def _create_section_chunk(self, section: Dict[str, Any], chunk_index: int) -> Optional[ChunkData]:
        """Create a section chunk."""
        elements = section['elements']
        if not elements:
            return None
        
        # Combine all content in the section
        content_parts = []
        if section['title']:
            content_parts.append(section['title'])
        
        for element in elements:
            if element.content_type != ContentType.HEADING:  # Skip heading as it's already added
                content_parts.append(element.content)
        
        content = "\n\n".join(content_parts)
        chunk_id = f"section_chunk_{chunk_index}"
        source_elements = [elem.element_id for elem in elements]
        page_numbers = self._get_page_numbers(elements)
        
        chunk = self._create_chunk(
            chunk_id=chunk_id,
            content=content,
            chunk_type=ChunkType.SECTION,
            source_elements=source_elements,
            chunk_index=chunk_index,
            page_numbers=page_numbers
        )
        
        if chunk and section['title']:
            chunk.position['section_title'] = section['title']
            chunk.position['section_level'] = section['level']
        
        return chunk


class SemanticChunker(BaseChunker):
    """Chunks documents based on semantic similarity (simplified implementation)."""
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document based on semantic similarity."""
        # For MVP, use a simplified approach based on topic changes
        # In a full implementation, this would use embeddings and similarity measures
        
        chunks = []
        chunk_index = 0
        
        # Group elements by semantic similarity (simplified)
        semantic_groups = self._identify_semantic_groups(document.content_elements)
        
        for group in semantic_groups:
            chunk = self._create_semantic_chunk(group, chunk_index)
            if chunk:
                chunks.append(chunk)
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
    
    def _identify_semantic_groups(self, elements: List[ContentElement]) -> List[List[ContentElement]]:
        """Identify semantic groups (simplified implementation)."""
        groups = []
        current_group = []
        current_word_count = 0
        
        for element in elements:
            element_words = len(element.content.split())
            
            # Simple heuristic: group elements until we hit a heading or size limit
            if (element.content_type == ContentType.HEADING and current_group) or \
               (current_word_count + element_words > self.chunk_size and current_group):
                
                groups.append(current_group)
                current_group = [element]
                current_word_count = element_words
            else:
                current_group.append(element)
                current_word_count += element_words
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _create_semantic_chunk(self, elements: List[ContentElement], chunk_index: int) -> Optional[ChunkData]:
        """Create a semantic chunk."""
        if not elements:
            return None
        
        content = "\n\n".join(elem.content for elem in elements)
        chunk_id = f"semantic_chunk_{chunk_index}"
        source_elements = [elem.element_id for elem in elements]
        page_numbers = self._get_page_numbers(elements)
        
        # Determine chunk type based on dominant content type
        type_counts = {}
        for elem in elements:
            type_counts[elem.content_type] = type_counts.get(elem.content_type, 0) + 1
        
        dominant_type = max(type_counts, key=type_counts.get)
        chunk_type = ChunkType.MIXED if len(type_counts) > 2 else ChunkType.TEXT
        
        return self._create_chunk(
            chunk_id=chunk_id,
            content=content,
            chunk_type=chunk_type,
            source_elements=source_elements,
            chunk_index=chunk_index,
            page_numbers=page_numbers
        )


class DocumentChunker:
    """Main document chunker that supports multiple strategies."""
    
    def __init__(self, strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH, config: Dict[str, Any] = None):
        """Initialize the document chunker."""
        self.strategy = strategy
        self.config = config or {}
        self.chunker = self._create_chunker()
    
    def _create_chunker(self) -> BaseChunker:
        """Create the appropriate chunker based on strategy."""
        chunker_map = {
            ChunkingStrategy.PARAGRAPH: ParagraphChunker,
            ChunkingStrategy.SENTENCE: SentenceChunker,
            ChunkingStrategy.SECTION_BASED: SectionChunker,
            ChunkingStrategy.SEMANTIC: SemanticChunker,
        }
        
        chunker_class = chunker_map.get(self.strategy, ParagraphChunker)
        return chunker_class(self.config)
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk the document using the selected strategy."""
        try:
            chunks = self.chunker.chunk_document(document)
            
            # Post-process chunks
            chunks = self._post_process_chunks(chunks)
            
            strategy_name = self.strategy.value if hasattr(self.strategy, 'value') else str(self.strategy)
            logger.info(f"Successfully chunked document into {len(chunks)} chunks using {strategy_name} strategy")
            return chunks
            
        except Exception as e:
            strategy_name = self.strategy.value if hasattr(self.strategy, 'value') else str(self.strategy)
            logger.error(f"Error chunking document with {strategy_name} strategy: {e}")
            # Fallback to paragraph chunking
            if self.strategy != ChunkingStrategy.PARAGRAPH:
                logger.info("Falling back to paragraph chunking")
                fallback_chunker = ParagraphChunker(self.config)
                return fallback_chunker.chunk_document(document)
            raise
    
    def _post_process_chunks(self, chunks: List[ChunkData]) -> List[ChunkData]:
        """Post-process chunks for quality and consistency."""
        processed_chunks = []
        
        for chunk in chunks:
            if chunk is None:
                continue
            
            # Skip chunks that are too small
            if chunk.metadata.word_count < self.config.get('min_chunk_size', 50):
                continue
            
            # Clean up content
            chunk.content = self._clean_content(chunk.content)
            
            # Update relationships (simplified)
            if processed_chunks:
                # Link to previous chunk
                prev_chunk = processed_chunks[-1]
                chunk.relationships['previous'] = [prev_chunk.chunk_id]
                prev_chunk.relationships['next'] = [chunk.chunk_id]
            
            processed_chunks.append(chunk)
        
        return processed_chunks
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize chunk content."""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Ensure content ends with proper punctuation
        if content and not content[-1] in '.!?':
            content += '.'
        
        return content
    
    def get_chunking_statistics(self, chunks: List[ChunkData]) -> Dict[str, Any]:
        """Get statistics about the chunking results."""
        if not chunks:
            return {"total_chunks": 0}
        
        word_counts = [chunk.metadata.word_count for chunk in chunks]
        char_counts = [chunk.metadata.character_count for chunk in chunks]
        
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk.chunk_type.value
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        return {
            "total_chunks": len(chunks),
            "strategy_used": self.strategy.value,
            "average_word_count": sum(word_counts) / len(word_counts),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts),
            "average_char_count": sum(char_counts) / len(char_counts),
            "chunk_types": chunk_types,
            "total_words": sum(word_counts),
            "total_characters": sum(char_counts)
        }