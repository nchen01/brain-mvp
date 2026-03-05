"""Document chunking strategies for post-processing."""

import logging
import re
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

from docforge.preprocessing.schemas import StandardizedDocumentOutput, ContentElement, ContentType
from .schemas import (
    ChunkData,
    ChunkMetadata,
    ChunkType,
    ChunkingStrategy,
    DocumentSummaries,
    create_chunk_data,
    create_chunk_metadata
)
from .hybrid_chunking import HybridDocumentChunker, HybridChunkingConfig

logger = logging.getLogger(__name__)

# Placeholder for EnhancedSemanticChunker if it's not yet defined in the context
# In a real scenario, this would be imported or defined elsewhere.
class EnhancedSemanticChunker:
    def __init__(self, config: Dict[str, Any]):
        # Simulate initialization
        pass
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        # Simulate semantic chunking
        return []


class BaseChunker(ABC):
    """Base class for document chunkers."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the chunker.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.chunk_size = self.config.get('chunk_size', 800)
        self.chunk_overlap = self.config.get('chunk_overlap', 100)
        self.language = self.config.get('language', 'en')
        self.min_chunk_size = self.config.get('min_chunk_size', 5)
    
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
        min_size = self.min_chunk_size  # Use configured size directly
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


class RecursiveChunker(BaseChunker):
    """
    Recursive character text splitter inspired by LangChain.
    
    Splits text using hierarchical delimiters:
    1. Try to split by paragraphs (\\n\\n)
    2. If chunks too large, split by sentences (. )
    3. If still too large, split by words ( )
    4. As last resort, split by characters
    
    This preserves semantic boundaries as much as possible.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize recursive chunker."""
        super().__init__(config)
        # Hierarchical separators from largest to smallest semantic units
        self.separators = self.config.get('separators', [
            "\n\n",    # Paragraphs
            "\n",      # Lines
            ". ",      # Sentences
            "! ",      # Exclamations
            "? ",      # Questions
            "; ",      # Clauses
            ", ",      # Phrases
            " ",       # Words
            ""         # Characters (fallback)
        ])
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document using recursive splitting."""
        chunks = []
        chunk_index = 0
        
        # Combine all text content
        all_text = self._extract_full_text(document.content_elements)
        element_map = self._build_element_map(document.content_elements)
        
        # Recursively split the text
        text_chunks = self._split_text_recursively(all_text, self.separators)
        
        # No overlap for first chunk
        previous_chunk_text = ""
        
        for text_chunk in text_chunks:
            # Add overlap from previous chunk if configured
            if self.chunk_overlap > 0 and previous_chunk_text:
                overlap_text = self._get_overlap_text(previous_chunk_text)
                combined_text = overlap_text + text_chunk
            else:
                combined_text = text_chunk
            
            # Create chunk
            chunk_id = f"recursive_chunk_{chunk_index}"
            source_elements = self._find_source_elements(combined_text, element_map)
            page_numbers = self._estimate_page_numbers(source_elements, document.content_elements)
            
            chunk = self._create_chunk(
                chunk_id=chunk_id,
                content=combined_text,
                chunk_type=ChunkType.TEXT,
                source_elements=source_elements,
                chunk_index=chunk_index,
                page_numbers=page_numbers
            )
            
            if chunk:
                chunks.append(chunk)
                previous_chunk_text = text_chunk
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} recursive chunks")
        return chunks
    
    def _split_text_recursively(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using hierarchical separators."""
        if not separators or not text:
            return [text] if text else []
        
        # Try current separator
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator == "":
            # Character-level splitting (last resort)
            return self._split_by_characters(text)
        
        # Split by current separator
        splits = text.split(separator) if separator else [text]
        
        # Process each split
        final_chunks = []
        current_chunk = ""
        
        for i, split in enumerate(splits):
            # Add separator back except for last split
            if i < len(splits) - 1:
                split = split + separator
            
            # Check if adding this split would exceed chunk size
            test_chunk = current_chunk + split if current_chunk else split
            
            if len(test_chunk.split()) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Current chunk is full
                if current_chunk:
                    final_chunks.append(current_chunk.strip())
                
                # If split itself is too large, recursively split it further
                if len(split.split()) > self.chunk_size:
                    sub_chunks = self._split_text_recursively(split, remaining_separators)
                    final_chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split
        
        # Add final chunk
        if current_chunk:
            final_chunks.append(current_chunk.strip())
        
        return [c for c in final_chunks if c]
    
    def _split_by_characters(self, text: str) -> List[str]:
        """Split text by characters when all else fails."""
        chunks = []
        # Use character count approximation (avg 5 chars per word)
        max_chars = self.chunk_size * 5
        
        for i in range(0, len(text), max_chars):
            chunks.append(text[i:i+max_chars])
        
        return chunks
    
    def _extract_full_text(self, elements: List[ContentElement]) -> str:
        """Extract all text from content elements."""
        text_parts = []
        for element in elements:
            if element.content_type in [ContentType.PARAGRAPH, ContentType.TEXT, ContentType.HEADING]:
                text_parts.append(element.content)
        return "\n\n".join(text_parts)
    
    def _build_element_map(self, elements: List[ContentElement]) -> Dict[str, ContentElement]:
        """Build a map of element IDs to elements."""
        return {elem.element_id: elem for elem in elements}
    
    def _find_source_elements(self, chunk_text: str, element_map: Dict[str, ContentElement]) -> List[str]:
        """Find which elements contributed to this chunk (simplified)."""
        # For now, return all element IDs as we don't track exact boundaries
        return list(element_map.keys())[:5]  # Limit to avoid bloat
    
    def _estimate_page_numbers(self, source_elements: List[str], all_elements: List[ContentElement]) -> List[int]:
        """Estimate page numbers for chunk."""
        pages = set()
        for elem in all_elements[:3]:  # Sample first few elements
            page = elem.metadata.get('page', 1)
            if isinstance(page, int):
                pages.add(page)
        return sorted(list(pages))
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from previous chunk."""
        words = text.split()
        if len(words) <= self.chunk_overlap:
            return text + " "
        overlap_words = words[-self.chunk_overlap:]
        return " ".join(overlap_words) + " "


class FixedSizeChunker(BaseChunker):
    """
    Simple fixed-size chunking with sliding window overlap.
    
    This is the baseline/naive approach for comparison. Splits text
    into fixed-size chunks based purely on token count, with no regard
    for semantic boundaries. Uses overlap to prevent sentence truncation.
    """
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document into fixed-size pieces."""
        chunks = []
        chunk_index = 0
        
        # Extract all text
        all_text = self._extract_full_text(document.content_elements)
        words = all_text.split()
        
        # Sliding window chunking
        i = 0
        while i < len(words):
            # Take chunk_size words
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Create chunk
            chunk_id = f"fixed_chunk_{chunk_index}"
            
            chunk = self._create_chunk(
                chunk_id=chunk_id,
                content=chunk_text,
                chunk_type=ChunkType.TEXT,
                source_elements=[],  # Simplified: no element tracking
                chunk_index=chunk_index,
                page_numbers=[]
            )
            
            if chunk:
                chunks.append(chunk)
                chunk_index += 1
            
            # Move window forward, accounting for overlap
            i += (self.chunk_size - self.chunk_overlap)
        
        logger.info(f"Created {len(chunks)} fixed-size chunks")
        return chunks
    
    def _extract_full_text(self, elements: List[ContentElement]) -> str:
        """Extract all text from content elements."""
        text_parts = []
        for element in elements:
            if element.content_type in [ContentType.PARAGRAPH, ContentType.TEXT, ContentType.HEADING]:
                text_parts.append(element.content)
        return " ".join(text_parts)


class EnhancedSemanticChunker(BaseChunker):
    """
    Enhanced semantic chunking using embedding similarity.
    
    Chunks documents by calculating semantic similarity between
    adjacent sentences/paragraphs and merging similar ones while
    splitting on topic changes. This is the highest quality but
    most expensive strategy.
    
    Falls back to sentence-based chunking if embeddings unavailable.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize enhanced semantic chunker."""
        super().__init__(config)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.75)
        self.use_embeddings = self.config.get('use_embeddings', False)
        
        # Try to initialize embedding model
        self.embed_model = None
        if self.use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = self.config.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2')
                self.embed_model = SentenceTransformer(model_name)
                logger.info(f"Initialized semantic chunker with embeddings: {model_name}")
            except ImportError:
                logger.warning("sentence-transformers not available, falling back to heuristic semantic chunking")
                self.use_embeddings = False
    
    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document based on semantic similarity."""
        if self.use_embeddings and self.embed_model:
            return self._chunk_with_embeddings(document)
        else:
            return self._chunk_with_heuristics(document)
    
    def _chunk_with_embeddings(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk using actual embedding similarity."""
        chunks = []
        chunk_index = 0
        
        # Split into sentences
        sentences, sentence_elements = self._extract_sentences(document.content_elements)
        
        if not sentences:
            return chunks
        
        # Calculate embeddings
        embeddings = self.embed_model.encode(sentences)
        
        # Group sentences by similarity
        current_group = [sentences[0]]
        current_elements = [sentence_elements[0]]
        
        for i in range(1, len(sentences)):
            # Calculate cosine similarity with previous sentence
            similarity = self._cosine_similarity(embeddings[i-1], embeddings[i])
            
            # If similar enough, add to current group
            if similarity >= self.similarity_threshold and len(" ".join(current_group + [sentences[i]]).split()) <= self.chunk_size:
                current_group.append(sentences[i])
                current_elements.append(sentence_elements[i])
            else:
                # Create chunk from current group
                chunk = self._create_semantic_group_chunk(current_group, current_elements, chunk_index)
                if chunk:
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new group
                current_group = [sentences[i]]
                current_elements = [sentence_elements[i]]
        
        # Add final group
        if current_group:
            chunk = self._create_semantic_group_chunk(current_group, current_elements, chunk_index)
            if chunk:
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} semantic chunks using embeddings")
        return chunks
    
    def _chunk_with_heuristics(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Fallback: Use heuristic-based semantic grouping."""
        # Use the existing simplified semantic chunker logic
        chunks = []
        chunk_index = 0
        
        # Group elements by semantic similarity (simplified)
        semantic_groups = self._identify_semantic_groups_heuristic(document.content_elements)
        
        for group in semantic_groups:
            chunk = self._create_semantic_chunk_from_elements(group, chunk_index)
            if chunk:
                chunks.append(chunk)
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} semantic chunks using heuristics")
        return chunks
    
    def _extract_sentences(self, elements: List[ContentElement]) -> Tuple[List[str], List[ContentElement]]:
        """Extract sentences from content elements."""
        sentences = []
        sentence_elements = []
        
        for element in elements:
            if element.content_type in [ContentType.PARAGRAPH, ContentType.TEXT]:
                # Simple sentence splitting
                element_sentences = re.split(r'[.!?]+\s+', element.content)
                for sent in element_sentences:
                    if sent.strip():
                        sentences.append(sent.strip())
                        sentence_elements.append(element)
        
        return sentences, sentence_elements
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    
    def _create_semantic_group_chunk(self, sentences: List[str], elements: List[ContentElement], chunk_index: int) -> Optional[ChunkData]:
        """Create chunk from semantic sentence group."""
        if not sentences:
            return None
        
        content = " ".join(sentences)
        chunk_id = f"semantic_chunk_{chunk_index}"
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
    
    def _identify_semantic_groups_heuristic(self, elements: List[ContentElement]) -> List[List[ContentElement]]:
        """Identify semantic groups using heuristics."""
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
    
    def _create_semantic_chunk_from_elements(self, elements: List[ContentElement], chunk_index: int) -> Optional[ChunkData]:
        """Create semantic chunk from content elements."""
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


class HybridStructureAwareChunker(BaseChunker):
    """
    Adapter that bridges BaseChunker interface to HybridDocumentChunker.

    The hybrid chunker handles overlap, linking, and min-size filtering
    internally, so DocumentChunker's _post_process_chunks should be skipped.
    """

    skip_post_processing = True

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        hybrid_config = self._build_hybrid_config(config or {})
        self._hybrid_chunker = HybridDocumentChunker(hybrid_config)

    def _build_hybrid_config(self, config: Dict[str, Any]) -> HybridChunkingConfig:
        """Map BaseChunker-style flat config dict to HybridChunkingConfig."""
        kwargs = {}

        # Direct hybrid config keys take priority
        hybrid_fields = [
            'target_chunk_size', 'max_chunk_size', 'min_chunk_size',
            'chunk_overlap', 'short_section_threshold', 'long_section_threshold',
            'merge_adjacent_short_sections', 'short_section_merge_threshold',
            'respect_section_boundaries', 'respect_paragraph_boundaries',
            'respect_sentence_boundaries', 'flag_long_sections_for_semantic',
            'language',
        ]
        for key in hybrid_fields:
            if key in config:
                kwargs[key] = config[key]

        # Map standard BaseChunker key as fallback
        if 'target_chunk_size' not in kwargs and 'chunk_size' in config:
            kwargs['target_chunk_size'] = config['chunk_size']
        if 'chunk_overlap' not in kwargs and 'chunk_overlap' in config:
            kwargs['chunk_overlap'] = config['chunk_overlap']
        if 'min_chunk_size' not in kwargs and 'min_chunk_size' in config:
            kwargs['min_chunk_size'] = config['min_chunk_size']
        if 'language' not in kwargs and 'language' in config:
            kwargs['language'] = config['language']

        return HybridChunkingConfig(**kwargs)

    def chunk_document(self, document: StandardizedDocumentOutput) -> List[ChunkData]:
        """Chunk document using hybrid structure-aware approach."""
        return self._hybrid_chunker.chunk_to_chunk_data(document)


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
            ChunkingStrategy.RECURSIVE: RecursiveChunker,  # New: LangChain-style recursive splitting
            ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,  # New: Simple fixed-size baseline
            ChunkingStrategy.PARAGRAPH: ParagraphChunker,
            ChunkingStrategy.SENTENCE: SentenceChunker,
            ChunkingStrategy.SECTION_BASED: SectionChunker,
            ChunkingStrategy.SEMANTIC: EnhancedSemanticChunker,  # Updated: Enhanced with embeddings
            ChunkingStrategy.HYBRID_STRUCTURE_AWARE: HybridStructureAwareChunker,  # Structure-aware with routing
        }
        
        chunker_class = chunker_map.get(self.strategy, RecursiveChunker)  # Default to recursive
        return chunker_class(self.config)
    
    def chunk_document(
        self,
        document: StandardizedDocumentOutput,
        summaries: Optional[DocumentSummaries] = None,
    ) -> List[ChunkData]:
        """Chunk the document using the selected strategy.

        Args:
            document: Preprocessed document.
            summaries: Optional DocumentSummaries produced by SummarizationService.
                       When provided, doc_summary / section_summary / section_path
                       are attached to every chunk.

        Returns:
            List of ChunkData objects, enriched with summary fields when summaries
            are supplied.
        """
        try:
            chunks = self.chunker.chunk_document(document)

            # Some chunkers (e.g., hybrid) handle post-processing internally
            if not getattr(self.chunker, 'skip_post_processing', False):
                chunks = self._post_process_chunks(chunks)

            if summaries is not None:
                chunks = self._attach_summaries(chunks, document, summaries)

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
                chunks = fallback_chunker.chunk_document(document)
                if summaries is not None:
                    chunks = self._attach_summaries(chunks, document, summaries)
                return chunks
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
    
    def _attach_summaries(
        self,
        chunks: List[ChunkData],
        document: StandardizedDocumentOutput,
        summaries: DocumentSummaries,
    ) -> List[ChunkData]:
        """Attach doc/section summaries and section path to every chunk.

        Strategy:
          1. Build a map from each element_id to the nearest preceding heading
             element_id (gives the "owning section" for any element).
          2. For each chunk try to resolve its section_id in priority order:
             a. chunk.position["source_section_id"]  (hybrid chunker path)
             b. Lookup the first source_element in the element→heading map.
          3. Resolve section_path from chunk.position heading context fields.
        """
        # Build element_id → nearest-heading-id mapping
        element_to_heading: Dict[str, str] = {}
        current_heading_id = ""
        for element in document.content_elements:
            if element.content_type in ("heading", "HEADING"):
                current_heading_id = element.element_id
            element_to_heading[element.element_id] = current_heading_id

        for chunk in chunks:
            chunk.doc_summary = summaries.doc_summary

            # Resolve section_id
            section_id: str = chunk.position.get("source_section_id", "")
            if not section_id and chunk.metadata.source_elements:
                first_elem = chunk.metadata.source_elements[0]
                section_id = element_to_heading.get(first_elem, "")

            # Resolve section_path (human-readable heading breadcrumb)
            section_path: str = (
                chunk.position.get("heading_context")
                or chunk.position.get("section_path")
                or chunk.position.get("section_title")
                or ""
            )

            chunk.section_summary = summaries.section_summaries.get(section_id, "")
            chunk.section_path = section_path

        return chunks

    @staticmethod
    def build_enriched_text(chunk: ChunkData, title: str = "") -> str:
        """Build the enriched text string used for embedding.

        Format::

            Document: {title}. Overall summary: {doc_summary}.
            Section: {section_path}. Section summary: {section_summary}.
            Content: {raw_text}

        Empty parts are omitted to avoid padding noise.
        """
        parts: List[str] = []
        if title:
            parts.append(f"Document: {title}.")
        if chunk.doc_summary:
            parts.append(f"Overall summary: {chunk.doc_summary}.")
        if chunk.section_path:
            parts.append(f"Section: {chunk.section_path}.")
        if chunk.section_summary:
            parts.append(f"Section summary: {chunk.section_summary}.")
        parts.append(f"Content: {chunk.content}")
        return " ".join(parts)

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
    
    def enrich_chunks_with_context(
        self,
        chunks: List[ChunkData],
        full_document_text: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChunkData]:
        """Enrich chunks with document-level context using LLM.
        
        Args:
            chunks: List of chunks to enrich
            full_document_text: Full document text for context
            document_metadata: Optional metadata for structured prompts
            
        Returns:
            List of enriched chunks (or original if enrichment disabled/fails)
        """
        # Check if enrichment is enabled
        if not self.config.get('enrich_contexts', False):
            logger.debug("Context enrichment disabled in config")
            return chunks
        
        try:
            # Import here to avoid circular dependency
            from docforge.enrichment import ContextEnricher
            
            # Get API key from config
            api_key = self.config.get('openai_api_key')
            if not api_key:
                logger.warning("No OpenAI API key provided - skipping context enrichment")
                return chunks
            
            # Initialize enricher
            enricher = ContextEnricher(
                api_key=api_key,
                model=self.config.get('context_model', 'gpt-3.5-turbo'),
                prompt_style=self.config.get('context_prompt_style', 'default'),
                max_context_words=self.config.get('context_max_words', 100),
                temperature=self.config.get('context_temperature', 0.3)
            )
            
            if not enricher.is_enabled:
                logger.warning("Context enricher not enabled - skipping enrichment")
                return chunks
            
            # Enrich each chunk
            enriched_chunks = []
            for i, chunk in enumerate(chunks):
                logger.debug(f"Enriching chunk {i+1}/{len(chunks)}: {chunk.chunk_id}")
                
                # Generate enriched content
                enriched_content = enricher.enrich_chunk(
                    whole_document=full_document_text,
                    chunk_content=chunk.content,
                    metadata=document_metadata
                )
                
                # Update chunk with enriched content if different
                if enriched_content != chunk.content:
                    # Store original content in metadata
                    chunk.metadata.original_content = chunk.content
                    chunk.metadata.enriched = True
                    chunk.content = enriched_content
                    logger.debug(f"Chunk {chunk.chunk_id} enriched successfully")
                
                enriched_chunks.append(chunk)
            
            logger.info(f"Successfully enriched {len(enriched_chunks)} chunks")
            return enriched_chunks
            
        except ImportError as e:
            logger.error(f"Could not import ContextEnricher: {e}")
            return chunks
        except Exception as e:
            logger.error(f"Error enriching chunks: {e}")
            # Gracefully fallback to original chunks
            return chunks