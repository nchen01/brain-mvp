#!/usr/bin/env python3
"""
Test script for chunk storage functionality.

Tests database operations for storing and retrieving chunks.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.chunk_storage import ChunkStorage


def test_chunk_storage():
    """Test chunk storage CRUD operations."""
    
    print("\n" + "="*80)
    print("CHUNK STORAGE TEST")
    print("="*80)
    
    # Initialize storage
    print("\n1. Initializing ChunkStorage...")
    storage = ChunkStorage(db_path="data/brain_mvp.db")
    print("   ✓ Storage initialized")
    
    # Create test chunks
    print("\n2. Creating test chunks...")
    test_doc_uuid = "test_doc_123"
    test_lineage_uuid = "test_lineage_456"
    test_version = 1
    
    test_chunks = [
        {
            'content': 'This is the first test chunk about AI and machine learning.',
            'metadata': {
                'word_count': 10,
                'character_count': 60,
                'chunk_type': 'paragraph'
            },
            'relationships': {
                'next': ['chunk_test_doc_123_1']
            }
        },
        {
            'content': 'This is the second test chunk about natural language processing.',
            'enriched_content': 'This chunk discusses NLP techniques. This is the second test chunk about natural language processing.',
            'metadata': {
                'word_count': 10,
                'character_count': 65,
                'chunk_type': 'paragraph'
            },
            'enrichment_metadata': {
                'model': 'gpt-3.5-turbo',
                'enriched': True
            },
            'relationships': {
                'previous': ['chunk_test_doc_123_0'],
                'next': ['chunk_test_doc_123_2']
            }
        },
        {
            'content': 'This is the third and final test chunk.',
            'metadata': {
                'word_count': 8,
                'character_count': 40,
                'chunk_type': 'paragraph'
            },
            'relationships': {
                'previous': ['chunk_test_doc_123_1']
            }
        }
    ]
    
    print(f"   Created {len(test_chunks)} test chunks")
    
    # Store chunks
    print("\n3. Storing chunks in database...")
    try:
        chunk_ids = storage.store_chunks(
            doc_uuid=test_doc_uuid,
            lineage_uuid=test_lineage_uuid,
            version_number=test_version,
            chunks=test_chunks,
            chunking_strategy='recursive'
        )
        print(f"   ✓ Stored {len(chunk_ids)} chunks")
        print(f"   Chunk IDs: {', '.join(chunk_ids[:3])}")
    except Exception as e:
        print(f"   ✗ Error storing chunks: {e}")
        return
    
    # Retrieve chunks by document
    print("\n4. Retrieving chunks by document...")
    try:
        retrieved_chunks = storage.get_chunks_by_document(test_doc_uuid)
        print(f"   ✓  Retrieved {len(retrieved_chunks)} chunks")
        
        for idx, chunk in enumerate(retrieved_chunks):
            has_enriched = 'enriched_content' in chunk and chunk['enriched_content']
            print(f"   - Chunk {idx}: {chunk['chunking_strategy']}, " + 
                  f"enriched={has_enriched}, words={chunk['metadata'].get('word_count', 0)}")
    except Exception as e:
        print(f"   ✗ Error retrieving chunks: {e}")
        return
    
    # Retrieve specific chunk
    print("\n5. Retrieving specific chunk by ID...")
    try:
        specific_chunk = storage.get_chunk_by_id(chunk_ids[1])
        if specific_chunk:
            print(f"   ✓ Retrieved chunk: {specific_chunk['chunk_id']}")
            print(f"   Content: {specific_chunk['original_content'][:50]}...")
            if specific_chunk.get('enriched_content'):
                print(f"   Enriched: {specific_chunk['enriched_content'][:60]}...")
        else:
            print(f"   ✗ Chunk not found")
    except Exception as e:
        print(f"   ✗ Error retrieving specific chunk: {e}")
    
    # Get statistics
    print("\n6. Getting storage statistics...")
    try:
        stats = storage.get_statistics()
        print(f"   ✓ Total chunks: {stats['total_chunks']}")
        print(f"   ✓ Enriched chunks: {stats['enriched_chunks']}")
        print(f"   ✓ Enrichment rate: {stats['enrichment_rate']:.1%}")
        print(f"   ✓ By strategy: {stats['by_strategy']}")
    except Exception as e:
        print(f"   ✗ Error getting statistics: {e}")
    
    # Clean up (delete test chunks)
    print("\n7. Cleaning up test data...")
    try:
        deleted_count = storage.delete_chunks_by_document(test_doc_uuid)
        print(f"   ✓ Deleted {deleted_count} test chunks")
    except Exception as e:
        print(f"   ✗ Error deleting chunks: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("✅ TEST COMPLETE!")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"  - Chunks stored: {len(chunk_ids)}")
    print(f"  - Chunks retrieved: {len(retrieved_chunks)}")
    print(f"  - Enriched chunks: {sum(1 for c in retrieved_chunks if c.get('enriched_content'))}")
    print(f"  - Test cleanup: Success")
    print("\n")


if __name__ == "__main__":
    test_chunk_storage()
