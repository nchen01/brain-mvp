#!/usr/bin/env python3
"""
Real Document Chunking Test

This script tests the three chunking strategies on real PDF documents
by integrating with the Brain MVP document processing pipeline.
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.advanced_pdf_processor import AdvancedPDFProcessor
from docforge.postprocessing.chunker import DocumentChunker
from docforge.postprocessing.schemas import ChunkingStrategy


def find_sample_pdfs(base_dir: str = "./", max_files: int = 3) -> List[Path]:
    """Find sample PDF files for testing."""
    pdf_paths = []
    
    # Common locations for test PDFs
    search_dirs = [
        Path(base_dir) / "uploads",
        Path(base_dir) / "data" / "uploads",
        Path(base_dir) / "temp",
        Path(base_dir) / "processed",
        Path(base_dir),
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            pdfs = list(search_dir.glob("*.pdf"))
            pdf_paths.extend(pdfs)
            if len(pdf_paths) >= max_files:
                break
    
    return pdf_paths[:max_files]


def process_pdf_with_chunking(
    pdf_path: Path,
    strategy: ChunkingStrategy,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Process a PDF and chunk it with specified strategy."""
    print(f"\n  Processing with {strategy.value}...", end="", flush=True)
    
    try:
        # Process PDF
        processor = AdvancedPDFProcessor()
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Process document
        result = processor.process_document(
            filename=pdf_path.name,
            file_content=pdf_content
        )
        
        if not result.success:
            print(f" ❌ FAILED: {result.error.error_message if result.error else 'Unknown error'}")
            return None
        
        # Chunk the processed document
        chunker = DocumentChunker(strategy=strategy, config=config)
        chunks = chunker.chunk_document(result.output)
        
        # Get statistics
        stats = chunker.get_chunking_statistics(chunks)
        
        print(f" ✓ ({len(chunks)} chunks)", flush=True)
        
        return {
            'strategy': strategy.value,
            'chunks': chunks,
            'stats': stats,
            'document': result.output
        }
        
    except Exception as e:
        print(f" ❌ ERROR: {str(e)}")
        return None


def compare_chunking_results(results: List[Dict[str, Any]]):
    """Compare and display chunking results."""
    if not results:
        print("\n❌ No results to compare")
        return
    
    print(f"\n{'='*80}")
    print("CHUNKING COMPARISON")
    print(f"{'='*80}")
    
    # Table header
    print(f"\n{'Strategy':<15} {'Chunks':<10} {'Avg Words':<12} {'Min':<8} {'Max':<8} {'Total Words':<12}")
    print("-" * 80)
    
    # Table rows
    for result in results:
        if result:
            stats = result['stats']
            print(f"{result['strategy']:<15} "
                  f"{stats['total_chunks']:<10} "
                  f"{stats['average_word_count']:<12.1f} "
                  f"{stats['min_word_count']:<8} "
                  f"{stats['max_word_count']:<8} "
                  f"{stats['total_words']:<12}")
    
    print("\n" + "-" * 80)
    
    # Show sample chunks from each strategy
    print(f"\nSAMPLE CHUNKS (First chunk from each strategy):")
    print("=" * 80)
    
    for result in results:
        if result and result['chunks']:
            chunk = result['chunks'][0]
            print(f"\n{result['strategy'].upper()} - {chunk.chunk_id}")
            print(f"Words: {chunk.metadata.word_count}, Chars: {chunk.metadata.character_count}")
            print(f"Preview: {chunk.content[:200]}...")
            print("-" * 80)


def analyze_chunk_distribution(results: List[Dict[str, Any]]):
    """Analyze chunk size distribution."""
    print(f"\n{'='*80}")
    print("CHUNK SIZE DISTRIBUTION")
    print(f"{'='*80}")
    
    for result in results:
        if not result:
            continue
            
        chunks = result['chunks']
        stats = result['stats']
        
        print(f"\n{result['strategy'].upper()}")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Word count - Mean: {stats['average_word_count']:.1f}, "
              f"Std: {_calculate_std([c.metadata.word_count for c in chunks]):.1f}")
        
        # Show distribution as simple histogram
        word_counts = [c.metadata.word_count for c in chunks]
        bins = 5
        hist = _create_histogram(word_counts, bins)
        
        print(f"  Distribution:")
        for bin_range, count in hist:
            bar = '█' * count
            print(f"    {bin_range[0]:>4}-{bin_range[1]:<4}: {bar} ({count})")


def _calculate_std(values: List[float]) -> float:
    """Calculate standard deviation."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


def _create_histogram(values: List[int], bins: int = 5) -> List[tuple]:
    """Create simple histogram."""
    if not values:
        return []
    
    min_val = min(values)
    max_val = max(values)
    bin_width = (max_val - min_val) / bins if max_val > min_val else 1
    
    histogram = []
    for i in range(bins):
        bin_start = int(min_val + i * bin_width)
        bin_end = int(min_val + (i + 1) * bin_width) if i < bins - 1 else max_val
        
        count = sum(1 for v in values if bin_start <= v <= bin_end)
        histogram.append(((bin_start, bin_end), count))
    
    return histogram


def main():
    """Run real document chunking tests."""
    print("\n" + "=" * 80)
    print("REAL DOCUMENT CHUNKING TEST")
    print("=" * 80)
    
    # Configuration
    config = {
        'chunk_size': 300,  # words
        'chunk_overlap': 50,  # words
        'min_chunk_size': 30,
        'language': 'en'
    }
    
    print(f"\nConfiguration:")
    print(f"  Chunk size: {config['chunk_size']} words")
    print(f"  Overlap: {config['chunk_overlap']} words")
    print(f"  Min chunk size: {config['min_chunk_size']} words")
    
    # Find sample PDFs
    print(f"\nSearching for PDF files...")
    pdf_files = find_sample_pdfs(max_files=1)  # Test with 1 PDF first
    
    if not pdf_files:
        print("\n❌ No PDF files found!")
        print("\nPlease upload a PDF to one of these directories:")
        print("  - ./uploads/")
        print("  - ./data/uploads/")
        print("  - ./temp/")
        print("\nOr specify a PDF path as argument: python test_real_documents.py path/to/file.pdf")
        return
    
    # Allow passing PDF path as argument
    if len(sys.argv) > 1:
        custom_path = Path(sys.argv[1])
        if custom_path.exists() and custom_path.suffix.lower() == '.pdf':
            pdf_files = [custom_path]
        else:
            print(f"\n⚠️  Custom path '{custom_path}' not found or not a PDF. Using discovered files.")
    
    print(f"\nFound {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        file_size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  - {pdf.name} ({file_size_mb:.2f} MB)")
    
    # Process each PDF with all strategies
    strategies = [
        ChunkingStrategy.RECURSIVE,
        ChunkingStrategy.FIXED_SIZE,
        ChunkingStrategy.SEMANTIC,
    ]
    
    for pdf_path in pdf_files:
        print(f"\n{'='*80}")
        print(f"TESTING: {pdf_path.name}")
        print(f"{'='*80}")
        
        results = []
        
        for strategy in strategies:
            result = process_pdf_with_chunking(pdf_path, strategy, config)
            if result:
                results.append(result)
        
        # Compare results
        if results:
            compare_chunking_results(results)
            analyze_chunk_distribution(results)
        
        print(f"\n{'='*80}")
    
    print("\n✅ Real document testing complete!")
    print("\nNext steps:")
    print("  1. Review chunk quality and size distribution")
    print("  2. Adjust chunk_size/overlap parameters if needed")
    print("  3. Proceed to Phase 2: Context Enrichment")
    print()


if __name__ == "__main__":
    main()
