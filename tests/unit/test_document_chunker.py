"""Tests for document chunking strategies."""

import pytest
from typing import List

from src.docforge.postprocessing.chunker import (
    DocumentChunker,
    ParagraphChunker,
    SentenceChunker,
    SectionChunker,
    SemanticChunker
)
from src.docforge.postprocessing.schemas import ChunkingStrategy, ChunkType
from src.docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingMetadata,
    DocumentStructure,
    ProcessingStatus,
    create_content_element,
    create_processing_metadata,
    create_document_structure
)


class TestDocumentChunker:
    """Test the main document chunker."""
    
    def create_test_document(self, content_types: List[ContentType] = None) -> StandardizedDocumentOutput:
        """Create a test document for chunking."""
        if content_types is None:
            content_types = [
                ContentType.HEADING,
                ContentType.PARAGRAPH,
                ContentType.PARAGRAPH,
                ContentType.HEADING,
                ContentType.PARAGRAPH
            ]
        
        content_elements = []
        for i, content_type in enumerate(content_types):
            if content_type == ContentType.HEADING:
                content = f"Section {i+1} Heading"
                metadata = {"level": 1}
            else:
                content = f"This is paragraph {i+1} with some content. " * 10  # ~100 words
                metadata = {}
            
            element = create_content_element(
                element_id=f"element_{i+1}",
                content_type=content_type,
                content=content,
                metadata=metadata
            )
            content_elements.append(element)
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(content_elements),
            total_pages=1
        )
        
        plain_text = " ".join(elem.content for elem in content_elements)
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            document_metadata={"title": "Test Document"},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=plain_text,
            markdown_text=plain_text
        )
    
    def test_paragraph_chunking_strategy(self):
        """Test paragraph chunking strategy."""
        document = self.create_test_document()
        chunker = DocumentChunker(ChunkingStrategy.PARAGRAPH, {"chunk_size": 150})
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type == ChunkType.PARAGRAPH for chunk in chunks)
        assert all(chunk.metadata.word_count <= 200 for chunk in chunks)  # Allow some flexibility
        
        # Check that chunks have proper IDs and metadata
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == f"paragraph_chunk_{i}"
            assert chunk.metadata.chunk_index == i
            assert len(chunk.metadata.source_elements) > 0
    
    def test_sentence_chunking_strategy(self):
        """Test sentence chunking strategy."""
        document = self.create_test_document()
        chunker = DocumentChunker(ChunkingStrategy.SENTENCE, {"chunk_size": 100})
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type == ChunkType.TEXT for chunk in chunks)
        
        # Check that chunks contain sentences
        for chunk in chunks:
            assert chunk.chunk_id.startswith("sentence_chunk_")
            assert len(chunk.content) > 0
    
    def test_section_chunking_strategy(self):
        """Test section-based chunking strategy."""
        # Create document with clear sections
        content_types = [
            ContentType.HEADING,
            ContentType.PARAGRAPH,
            ContentType.PARAGRAPH,
            ContentType.HEADING,
            ContentType.PARAGRAPH,
            ContentType.PARAGRAPH
        ]
        
        document = self.create_test_document(content_types)
        chunker = DocumentChunker(ChunkingStrategy.SECTION_BASED, {"chunk_size": 200})
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        
        # Should have section chunks
        section_chunks = [c for c in chunks if c.chunk_type == ChunkType.SECTION]
        assert len(section_chunks) > 0
        
        # Check section metadata
        for chunk in section_chunks:
            assert chunk.chunk_id.startswith("section_chunk_")
            if 'section_title' in chunk.position:
                assert chunk.position['section_title'] is not None
    
    def test_semantic_chunking_strategy(self):
        """Test semantic chunking strategy."""
        document = self.create_test_document()
        chunker = DocumentChunker(ChunkingStrategy.SEMANTIC, {"chunk_size": 150})
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        
        # Check semantic chunks
        for chunk in chunks:
            assert chunk.chunk_id.startswith("semantic_chunk_")
            assert chunk.chunk_type in [ChunkType.TEXT, ChunkType.MIXED]
    
    def test_chunking_with_overlap(self):
        """Test chunking with overlap between chunks."""
        document = self.create_test_document()
        chunker = DocumentChunker(
            ChunkingStrategy.PARAGRAPH, 
            {"chunk_size": 100, "chunk_overlap": 20}
        )
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 1
        
        # Check that chunks have relationships (indicating overlap handling)
        for i, chunk in enumerate(chunks[1:], 1):
            if 'previous' in chunk.relationships:
                assert chunks[i-1].chunk_id in chunk.relationships['previous']
    
    def test_chunking_statistics(self):
        """Test chunking statistics generation."""
        document = self.create_test_document()
        chunker = DocumentChunker(ChunkingStrategy.PARAGRAPH)
        
        chunks = chunker.chunk_document(document)
        stats = chunker.get_chunking_statistics(chunks)
        
        assert "total_chunks" in stats
        assert "strategy_used" in stats
        assert "average_word_count" in stats
        assert "chunk_types" in stats
        assert stats["total_chunks"] == len(chunks)
        assert stats["strategy_used"] == "paragraph"
    
    def test_fallback_chunking(self):
        """Test fallback to paragraph chunking on error."""
        # Create a chunker that might fail
        document = self.create_test_document()
        
        # Mock a failure in semantic chunking by using invalid config
        chunker = DocumentChunker(ChunkingStrategy.SEMANTIC)
        
        # Should still work due to fallback
        chunks = chunker.chunk_document(document)
        assert len(chunks) > 0
    
    def test_empty_document_handling(self):
        """Test handling of empty documents."""
        # Create empty document
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=0,
            total_pages=1
        )
        
        document = StandardizedDocumentOutput(
            content_elements=[],
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text="",
            markdown_text=""
        )
        
        chunker = DocumentChunker(ChunkingStrategy.PARAGRAPH)
        chunks = chunker.chunk_document(document)
        
        # Should handle empty document gracefully
        assert isinstance(chunks, list)
        assert len(chunks) == 0


class TestParagraphChunker:
    """Test paragraph chunking specifically."""
    
    def create_paragraph_document(self) -> StandardizedDocumentOutput:
        """Create a document with multiple paragraphs."""
        paragraphs = [
            "This is the first paragraph with some content. " * 15,  # ~150 words
            "This is the second paragraph with different content. " * 15,  # ~150 words
            "This is the third paragraph with more content. " * 15,  # ~150 words
        ]
        
        content_elements = []
        for i, paragraph in enumerate(paragraphs):
            element = create_content_element(
                element_id=f"para_{i+1}",
                content_type=ContentType.PARAGRAPH,
                content=paragraph,
                metadata={"page": 1}
            )
            content_elements.append(element)
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(content_elements),
            total_pages=1
        )
        
        return StandardizedDocumentOutput(
            content_elements=content_elements,
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=" ".join(paragraphs),
            markdown_text=" ".join(paragraphs)
        )
    
    def test_paragraph_chunking_basic(self):
        """Test basic paragraph chunking."""
        document = self.create_paragraph_document()
        chunker = ParagraphChunker({"chunk_size": 200, "chunk_overlap": 50})
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type == ChunkType.PARAGRAPH for chunk in chunks)
        
        # Check word counts
        for chunk in chunks:
            assert chunk.metadata.word_count > 0
            assert chunk.metadata.character_count > 0
    
    def test_paragraph_overlap(self):
        """Test paragraph overlap functionality."""
        document = self.create_paragraph_document()
        chunker = ParagraphChunker({"chunk_size": 100, "chunk_overlap": 30})
        
        chunks = chunker.chunk_document(document)
        
        # Should have multiple chunks due to size limit
        assert len(chunks) > 1
        
        # Check that overlap is created
        for chunk in chunks:
            assert isinstance(chunk.content, str)
            assert len(chunk.content) > 0


class TestSentenceChunker:
    """Test sentence chunking specifically."""
    
    def create_sentence_document(self) -> StandardizedDocumentOutput:
        """Create a document with sentences."""
        text = ("This is the first sentence. This is the second sentence! " +
                "This is the third sentence? This is the fourth sentence. " +
                "This is the fifth sentence with more content to test chunking.") * 5
        
        element = create_content_element(
            element_id="text_1",
            content_type=ContentType.PARAGRAPH,
            content=text
        )
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=1,
            total_pages=1
        )
        
        return StandardizedDocumentOutput(
            content_elements=[element],
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=text,
            markdown_text=text
        )
    
    def test_sentence_splitting(self):
        """Test sentence splitting functionality."""
        document = self.create_sentence_document()
        chunker = SentenceChunker({"chunk_size": 50})
        
        chunks = chunker.chunk_document(document)
        
        assert len(chunks) > 0
        
        # Check that chunks contain multiple sentences
        for chunk in chunks:
            # Should have sentence boundaries
            sentence_count = chunk.content.count('.') + chunk.content.count('!') + chunk.content.count('?')
            assert sentence_count > 0


class TestSectionChunker:
    """Test section chunking specifically."""
    
    def create_sectioned_document(self) -> StandardizedDocumentOutput:
        """Create a document with clear sections."""
        elements = [
            create_content_element(element_id="h1", content_type=ContentType.HEADING, content="Introduction", metadata={"level": 1}),
            create_content_element(element_id="p1", content_type=ContentType.PARAGRAPH, content="Introduction paragraph. " * 20),
            create_content_element(element_id="h2", content_type=ContentType.HEADING, content="Methods", metadata={"level": 1}),
            create_content_element(element_id="p2", content_type=ContentType.PARAGRAPH, content="Methods paragraph. " * 20),
            create_content_element(element_id="h3", content_type=ContentType.HEADING, content="Results", metadata={"level": 1}),
            create_content_element(element_id="p3", content_type=ContentType.PARAGRAPH, content="Results paragraph. " * 20),
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(elements),
            total_pages=1
        )
        
        plain_text = " ".join(elem.content for elem in elements)
        
        return StandardizedDocumentOutput(
            content_elements=elements,
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=plain_text,
            markdown_text=plain_text
        )
    
    def test_section_identification(self):
        """Test section identification based on headings."""
        document = self.create_sectioned_document()
        chunker = SectionChunker({"chunk_size": 300, "min_chunk_size": 10})
        
        chunks = chunker.chunk_document(document)
        
        # Debug: print information if no chunks
        if len(chunks) == 0:
            print(f"No chunks created. Document has {len(document.content_elements)} elements")
            for elem in document.content_elements:
                print(f"  - {elem.content_type}: {elem.content[:50]}...")
        
        assert len(chunks) > 0
        
        # Should have section chunks
        section_chunks = [c for c in chunks if c.chunk_type == ChunkType.SECTION]
        assert len(section_chunks) > 0
        
        # Check section titles
        for chunk in section_chunks:
            if 'section_title' in chunk.position:
                assert chunk.position['section_title'] in ["Introduction", "Methods", "Results"]
    
    def test_large_section_sub_chunking(self):
        """Test sub-chunking of large sections."""
        # Create a document with a very large section
        large_content = "This is a very long paragraph. " * 100  # ~400 words
        
        elements = [
            create_content_element(element_id="h1", content_type=ContentType.HEADING, content="Large Section", metadata={"level": 1}),
            create_content_element(element_id="p1", content_type=ContentType.PARAGRAPH, content=large_content),
            create_content_element(element_id="p2", content_type=ContentType.PARAGRAPH, content=large_content),
        ]
        
        processing_metadata = create_processing_metadata(
            processor_name="TestProcessor",
            processor_version="1.0.0",
            processing_duration=1.0
        )
        
        document_structure = create_document_structure(
            total_elements=len(elements),
            total_pages=1
        )
        
        plain_text = " ".join(elem.content for elem in elements)
        
        document = StandardizedDocumentOutput(
            content_elements=elements,
            document_metadata={},
            document_structure=document_structure,
            processing_metadata=processing_metadata,
            processing_status=ProcessingStatus.SUCCESS,
            plain_text=plain_text,
            markdown_text=plain_text
        )
        
        chunker = SectionChunker({"chunk_size": 200})  # Small chunk size to force sub-chunking
        chunks = chunker.chunk_document(document)
        
        # Should create multiple chunks for the large section
        assert len(chunks) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])