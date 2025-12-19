#!/usr/bin/env python3
"""
Test script for comparing chunking strategies.

This script demonstrates the new chunking strategies and compares their performance:
- RecursiveChunker (primary, recommended)
- FixedSizeChunker (baseline)
- EnhancedSemanticChunker (quality benchmark)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    create_processing_metadata,
    create_document_structure,
    ProcessingStatus
)
from docforge.postprocessing.chunker import DocumentChunker
from docforge.postprocessing.schemas import ChunkingStrategy


def create_sample_document() -> StandardizedDocumentOutput:
    """Create a sample document for testing."""
    
    # Sample text content
    sample_text = """
    Retrieval-Augmented Generation (RAG) is a powerful technique for enhancing Large Language Models.
    It combines the benefits of retrieval-based and generation-based approaches.
    
    Traditional RAG systems often suffer from semantic deficits during the chunking process.
    When documents are split into fixed-size tokens, important context can be lost.
    This leads to poor retrieval performance and inaccurate responses.
    
    Advanced chunking strategies can significantly improve RAG performance.
    Recursive chunking preserves semantic boundaries by using hierarchical delimiters.
    It first tries to split by paragraphs, then sentences, then words, and finally characters.
    
    Semantic chunking uses embedding similarity to group related content.
    This approach is more expensive but produces the highest quality chunks.
    It merges similar sentences while splitting on topic changes.
    
    Fixed-size chunking is the simplest baseline approach.
    It splits text purely by token count with sliding window overlap.
    While fast, it often breaks semantic boundaries and scatters information.
    
    Context enrichment further enhances chunk quality.
    By adding LLM-generated situational context to each chunk, we can improve retrieval accuracy by up to 67%.
    This bridges the gap between local detail and global document context.
    """
    
    # Create content elements
    elements = []
    paragraphs = [p.strip() for p in sample_text.strip().split('\n\n') if p.strip()]
    
    for i, para in enumerate(paragraphs):
        element = ContentElement(
            element_id=f"elem_{i}",
            content=para,
            content_type=ContentType.PARAGRAPH,
            metadata={"page": 1, "order": i}
        )
        elements.append(element)
    
    # Create document
    processing_metadata = create_processing_metadata(
        processor_name="TestProcessor",
        processor_version="1.0.0",
        processing_duration=0.1
    )
    
    document_structure = create_document_structure(
        total_elements=len(elements),
        total_pages=1
    )
    
    return StandardizedDocumentOutput(
        content_elements=elements,
        document_metadata={"title": "RAG Chunking Test Document"},
        document_structure=document_structure,
        processing_metadata=processing_metadata,
        processing_status=ProcessingStatus.SUCCESS,
        plain_text=sample_text,
        markdown_text=sample_text
    )


def test_chunking_strategy(strategy: ChunkingStrategy, config: dict = None):
    """Test a specific chunking strategy."""
    print(f"\n{'='*80}")
    print(f"Testing: {strategy.value.upper()} CHUNKING")
    print(f"{'='*80}")
    
    # Create document
    document = create_sample_document()
    
    # Create chunker
    chunker = DocumentChunker(strategy=strategy, config=config or {})
    
    # Chunk document
    chunks = chunker.chunk_document(document)
    
    # Print results
    print(f"\nTotal chunks created: {len(chunks)}")
    print(f"\nChunk Details:")
    print("-" * 80)
    
    for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
        print(f"\nChunk {i + 1} ({chunk.chunk_id}):")
        print(f"  Type: {chunk.chunk_type.value}")
        print(f"  Words: {chunk.metadata.word_count}")
        print(f"  Characters: {chunk.metadata.character_count}")
        print(f"  Content preview: {chunk.content[:150]}...")
    
    if len(chunks) > 5:
        print(f"\n... and {len(chunks) - 5} more chunks")
    
    # Get statistics
    stats = chunker.get_chunking_statistics(chunks)
    print(f"\n{'-'*80}")
    print(f"STATISTICS:")
    print(f"  Strategy: {stats['strategy_used']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Average words per chunk: {stats['average_word_count']:.1f}")
    print(f"  Min words: {stats['min_word_count']}")
    print(f"  Max words: {stats['max_word_count']}")
    print(f"  Total words: {stats['total_words']}")
    
    return chunks, stats


def main():
    """Run chunking comparison tests."""
    print("\n" + "="*80)
    print("CHUNKING STRATEGY COMPARISON TEST")
    print("="*80)
    
    # Configuration
    config = {
        'chunk_size': 100,  # words
        'chunk_overlap': 20,  # words
        'min_chunk_size': 10,
        'language': 'en'
    }
    
    print(f"\nConfiguration:")
    print(f"  Chunk size: {config['chunk_size']} words")
    print(f"  Overlap: {config['chunk_overlap']} words")
    print(f"  Min chunk size: {config['min_chunk_size']} words")
    
    # Test each strategy
    results = {}
    
    # 1. Recursive (Primary/Recommended)
    chunks, stats = test_chunking_strategy(ChunkingStrategy.RECURSIVE, config)
    results['recursive'] = {'chunks': chunks, 'stats': stats}
    
    # 2. Fixed-size (Baseline)
    chunks, stats = test_chunking_strategy(ChunkingStrategy.FIXED_SIZE, config)
    results['fixed_size'] = {'chunks': chunks, 'stats': stats}
    
    # 3. Semantic (Quality benchmark - without embeddings for now)
    semantic_config = {**config, 'use_embeddings': False}  # Disable embeddings for quick test
    chunks, stats = test_chunking_strategy(ChunkingStrategy.SEMANTIC, semantic_config)
    results['semantic'] = {'chunks': chunks, 'stats': stats}
    
    # Comparison summary
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}")
    print(f"\n{'Strategy':<15} {'Chunks':<10} {'Avg Words':<12} {'Min':<8} {'Max':<8}")
    print("-" * 80)
    
    for name, data in results.items():
        stats = data['stats']
        print(f"{name:<15} {stats['total_chunks']:<10} "
              f"{stats['average_word_count']:<12.1f} "
              f"{stats['min_word_count']:<8} "
              f"{stats['max_word_count']:<8}")
    
    print(f"\n{'='*80}")
    print("Phase 1 Implementation Complete! ✓")
    print(f"{'='*80}")
    print("\nNext steps:")
    print("- Phase 2: Implement Context Enrichment")
    print("- Phase 3: Update Database Schema")
    print("- Phase 4: Add Question-Oriented Indexing")
    print("- Phase 5: Build Evaluation Framework")
    

if __name__ == "__main__":
    main()
