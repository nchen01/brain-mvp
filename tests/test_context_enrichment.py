#!/usr/bin/env python3
"""
Test script for context-enriched chunking.

This demonstrates Phase 2: adding LLM-generated situational context to chunks.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.advanced_pdf_processor import AdvancedPDFProcessor
from docforge.postprocessing.chunker import DocumentChunker
from docforge.postprocessing.schemas import ChunkingStrategy


def test_context_enrichment():
    """Test context enrichment on a sample document."""
    
    print("\n" + "="*80)
    print("CONTEXT ENRICHMENT TEST")
    print("="*80)
    
    # Sample document (synthetic for testing without PDF)
    sample_text = """
    Q3 2023 Earnings Report - TechCorp Inc.
    
    Financial Performance:
    TechCorp reported strong Q3 2023 results with revenue of $2.5 billion, up 15% year-over-year. 
    The company's cloud services division led growth with $800 million in revenue.
    
    Product Updates:
    The company launched its new AI platform, TechAI Pro, which has already signed 50 enterprise customers.
    The platform uses advanced machine learning to automate business processes.
    
    Future Outlook:
    Management forecasts Q4 revenue between $2.7-2.9 billion, indicating continued strong growth.
    The company plans to invest heavily in AI R&D throughout 2024.
    """
    
    # Create a mock document
    from docforge.preprocessing.schemas import (
        create_content_element,
        create_processing_metadata,
        create_standardized_output,
        ContentType,
        ProcessingStatus
    )
    
    content_elements = [
        create_content_element(
            element_id="text_1",
            content_type=ContentType.TEXT,
            content=sample_text,
            metadata={"source": "test"}
        )
    ]
    
    processing_metadata = create_processing_metadata(
        processor_name="TestProcessor",
        processor_version="1.0.0",
        processing_duration=0.1,
        input_file_info={"filename": "test_earnings.txt"}
    )
    
    document = create_standardized_output(
        content_elements=content_elements,
        processing_metadata=processing_metadata,
        processing_status=ProcessingStatus.SUCCESS
    )
    
    print("\n1. Chunking document with Recursive strategy...")
    
    # Test WITHOUT enrichment first
    config_no_enrich = {
        'chunk_size': 100,
        'chunk_overlap': 20,
        'min_chunk_size': 30,
        'enrich_contexts': False  # Disabled
    }
    
    chunker = DocumentChunker(strategy=ChunkingStrategy.RECURSIVE, config=config_no_enrich)
    chunks_plain = chunker.chunk_document(document)
    
    print(f"   ✓ Created {len(chunks_plain)} chunks without enrichment")
    print(f"\n   Sample plain chunk:")
    print(f"   {chunks_plain[0].content[:200]}...")
    
    # Test WITH enrichment (requires API key)
    print("\n2. Testing WITH context enrichment...")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("   ⚠️  No OPENAI_API_KEY found in environment")
        print("   → Context enrichment will be skipped (feature disabled)")
        print("\n   To test enrichment, set OPENAI_API_KEY environment variable:")
        print("   export OPENAI_API_KEY='your-key-here'")
        enrichment_tested = False
    else:
        print(f"   ✓ OpenAI API key found: {api_key[:10]}...")
        
        config_with_enrich = {
            'chunk_size': 100,
            'chunk_overlap': 20,
            'min_chunk_size': 30,
            'enrich_contexts': True,  # Enabled
            'openai_api_key': api_key,
            'context_model': 'gpt-3.5-turbo',
            'context_prompt_style': 'default',
            'context_max_words': 50,
            'context_temperature': 0.3
        }
        
        chunker_enriched = DocumentChunker(strategy=ChunkingStrategy.RECURSIVE, config=config_with_enrich)
        chunks_base = chunker_enriched.chunk_document(document)
        
        # Enrich the chunks
        print("\n   Calling LLM to generate context for chunks...")
        chunks_enriched = chunker_enriched.enrich_chunks_with_context(
            chunks=chunks_base,
            full_document_text=sample_text,
            document_metadata={'title': 'Q3 2023 Earnings Report', 'company': 'TechCorp'}
        )
        
        print(f"   ✓ Enriched {len(chunks_enriched)} chunks")
        
        # Show comparison
        print("\n" + "="*80)
        print("COMPARISON: Plain vs Enriched")
        print("="*80)
        
        for i, (plain, enriched) in enumerate(zip(chunks_plain[:2], chunks_enriched[:2])):
            print(f"\n--- Chunk {i+1} ---")
            print(f"\nPLAIN (no context):")
            print(f"{plain.content[:200]}...")
            print(f"\nENRICHED (with LLM context):")
            print(f"{enriched.content[:300]}...")
            print("-" * 80)
        
        enrichment_tested = True
    
    # Summary
    print("\n" + "="*80)
    print("✅ TEST COMPLETE!")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"  - Plain chunks created: {len(chunks_plain)}")
    print(f"  - Enrichment tested: {'Yes' if enrichment_tested else 'No (no API key)'}")
    
    if enrichment_tested:
        print(f"  - Enriched chunks created: {len(chunks_enriched)}")
        print(f"\n💡 Key Benefit:")
        print(f"  Enriched chunks include document-level context, making them")
        print(f"  more retrievable when embedded and searched.")
    else:
        print(f"\n💡 To enable enrichment:")
        print(f"  1. Get an OpenAI API key from https://platform.openai.com")
        print(f"  2. Set: export OPENAI_API_KEY='sk-...'")
        print(f"  3. Re-run this script")
    
    print("\n")


if __name__ == "__main__":
    test_context_enrichment()
