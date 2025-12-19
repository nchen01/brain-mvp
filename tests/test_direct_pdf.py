#!/usr/bin/env python3
"""
Direct PDF Chunking Test - Downloads sample PDF and tests chunking strategies
"""

import sys
import os
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.advanced_pdf_processor import AdvancedPDFProcessor
from docforge.postprocessing.chunker import DocumentChunker
from docforge.postprocessing.schemas import ChunkingStrategy


def download_sample_pdf():
    """Download a sample PDF for testing."""
    # Using a publicly available research paper PDF
    sample_pdfs = [
        {
            "url": "https://arxiv.org/pdf/2005.11401.pdf",
            "name": "rag_paper.pdf",
            "description": "RAG: Retrieval-Augmented Generation (Lewis et al.)"
        }
    ]
    
    print("\nDownloading sample PDF for testing...")
    
    for pdf_info in sample_pdfs:
        try:
            print(f"  Fetching: {pdf_info['description']}")
            response = requests.get(pdf_info['url'], timeout=30)
            
            if response.status_code == 200:
                pdf_path = Path(f"/tmp/{pdf_info['name']}")
                pdf_path.write_bytes(response.content)
                print(f"  ✓ Downloaded to {pdf_path} ({len(response.content) / 1024:.1f} KB)")
                return pdf_path, pdf_info['description']
            else:
                print(f"  ✗ Failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    return None, None


def test_chunking_on_pdf(pdf_path: Path, description: str):
    """Test all chunking strategies on a PDF."""
    print(f"\n{'='*80}")
    print(f"TESTING: {description}")
    print(f"{'='*80}")
    
    # Configuration
    config = {
        'chunk_size': 300,
        'chunk_overlap': 50,
        'min_chunk_size': 30,
        'language': 'en'
    }
    
    # Process PDF
    print(f"\n1. Processing PDF...")
    processor = AdvancedPDFProcessor()
    
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    # Use the correct processor interface
    result_output = processor._process_document(
        file_path=str(pdf_path),
        file_content=pdf_content
    )
    
    print(f"  ✓ Extracted {len(result_output.content_elements)} content elements")
    print(f"  ✓ Total text length: {len(result_output.plain_text)} characters")
    
    # Test each chunking strategy
    strategies = [
        ChunkingStrategy.RECURSIVE,
        ChunkingStrategy.FIXED_SIZE,
        ChunkingStrategy.SEMANTIC,
    ]
    
    results = []
    
    print(f"\n2. Chunking with different strategies:")
    for strategy in strategies:
        print(f"\n  {strategy.value.upper()}")
        
        try:
            # Use enhanced config for semantic chunking
            if strategy == ChunkingStrategy.SEMANTIC:
                semantic_config = {
                    **config,
                    'use_embeddings': True,  # Now enabled with proper cache dirs
                    'similarity_threshold': 0.5  # Lowered from 0.75
                }
                print(f"    Using embeddings with similarity_threshold=0.5")
                chunker = DocumentChunker(strategy=strategy, config=semantic_config)
            else:
                chunker = DocumentChunker(strategy=strategy, config=config)
            
            chunks = chunker.chunk_document(result_output)
            stats = chunker.get_chunking_statistics(chunks)
            
            results.append({
                'strategy': strategy.value,
                'chunks': chunks,
                'stats': stats
            })
            
            print(f"    ✓ Created {len(chunks)} chunks")
            print(f"    ✓ Avg: {stats['average_word_count']:.1f} words, "
                  f"Min: {stats['min_word_count']}, Max: {stats['max_word_count']}")
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    # Display comparison
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"{'Strategy':<15} {'Chunks':<10} {'Avg Words':<12} {'Min':<8} {'Max':<8} {'Total':<10}")
    print("-" * 80)
    
    for r in results:
        s = r['stats']
        print(f"{r['strategy']:<15} {s['total_chunks']:<10} "
              f"{s['average_word_count']:<12.1f} {s['min_word_count']:<8} "
              f"{s['max_word_count']:<8} {s['total_words']:<10}")
    
    # Show sample chunks
    print(f"\n{'='*80}")
    print("SAMPLE CHUNKS (First chunk from each strategy)")
    print(f"{'='*80}")
    
    for r in results:
        if r['chunks']:
            chunk = r['chunks'][0]
            print(f"\n{r['strategy'].upper()} - {chunk.chunk_id}")
            print(f"  Words: {chunk.metadata.word_count}, Chars: {chunk.metadata.character_count}")
            print(f"  Preview:")
            print(f"  {chunk.content[:300]}...")
            print("-" * 80)
    
    # Analysis
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}\n")
    
    if len(results) >= 3:
        rec = next((r for r in results if r['strategy'] == 'recursive'), None)
        fixed = next((r for r in results if r['strategy'] == 'fixed_size'), None)
        sem = next((r for r in results if r['strategy'] == 'semantic'), None)
        
        if rec and fixed and sem:
            print("📊 Chunk Count:")
            print(f"  Recursive: {rec['stats']['total_chunks']} chunks")
            print(f"  Fixed-size: {fixed['stats']['total_chunks']} chunks")
            print(f"  Semantic: {sem['stats']['total_chunks']} chunks")
            
            print("\n📏 Consistency (lower std dev = more consistent):")
            for r in results:
                word_counts = [c.metadata.word_count for c in r['chunks']]
                std = (sum((x - r['stats']['average_word_count'])**2 for x in word_counts) / len(word_counts))**0.5
                print(f"  {r['strategy']}: {std:.1f}")
            
            print("\n💡 Recommendations:")
            print("  - Recursive: Best for general use (semantic + size balance)")
            print("  - Fixed-size: Good for quick baseline, consistent size")
            print("  - Semantic: Best quality, may need size tuning")


def main():
    """Run the chunking test."""
    print("\n" + "=" * 80)
    print("DIRECT PDF CHUNKING TEST")
    print("=" * 80)
    
    # Download sample PDF
    pdf_path, description = download_sample_pdf()
    
    if not pdf_path:
        print("\n❌ Could not download sample PDF. Please check your internet connection.")
        print("\nAlternatively, you can specify a local PDF:")
        print("  docker-compose exec brain-mvp python3 test_direct_pdf.py /path/to/file.pdf")
        return
    
    # Test chunking
    test_chunking_on_pdf(pdf_path, description)
    
    print(f"\n{'='*80}")
    print("✅ Test Complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # Allow custom PDF path
    if len(sys.argv) > 1:
        custom_path = Path(sys.argv[1])
        if custom_path.exists():
            test_chunking_on_pdf(custom_path, custom_path.name)
        else:
            print(f"❌ File not found: {custom_path}")
    else:
        main()
