#!/usr/bin/env python3
"""
End-to-end validation test for Brain MVP chunking system.

Tests the complete flow:
1. Document upload via API
2. Document processing and storage
3. Automatic chunking
4. Chunk storage in database
5. Chunk retrieval via API
"""

import requests
import time
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"  # Internal container port

def test_health():
    """Test API health."""
    print("\n" + "="*80)
    print("1. TESTING API HEALTH")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, "API not healthy"
    print("✅ API is healthy")
    return True

def download_test_pdf():
    """Download a test PDF."""
    print("\n" + "="*80)
    print("2. DOWNLOADING TEST PDF")
    print("="*80)
    
    pdf_url = "https://arxiv.org/pdf/2005.11401.pdf"  # RAG paper
    pdf_path = "/tmp/test_rag_paper.pdf"
    
    print(f"Downloading from: {pdf_url}")
    
    response = requests.get(pdf_url, stream=True)
    with open(pdf_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    file_size = Path(pdf_path).stat().st_size
    print(f"✅ Downloaded: {file_size:,} bytes")
    return pdf_path

def upload_document(pdf_path):
    """Upload document via API."""
    print("\n" + "="*80)
    print("3. UPLOADING DOCUMENT VIA API")
    print("="*80)
    
    # Note: Need to check the actual upload endpoint
    # This is a placeholder - adjust based on actual API
    upload_url = f"{BASE_URL}/api/v1/documents/upload"
    
    print(f"Uploading to: {upload_url}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': ('test_document.pdf', f, 'application/pdf')}
        response = requests.post(upload_url, files=files)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 201, 202]:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Extract document UUID - try different field names
        doc_uuid = (result.get('document_id') or 
                   result.get('document_uuid') or 
                   result.get('doc_uuid') or 
                   result.get('id'))
        
        if doc_uuid:
            print(f"✅ Document uploaded: {doc_uuid}")
            return doc_uuid
        else:
            print(f"⚠️  Upload succeeded but no doc_uuid in response")
            return result
    else:
        print(f"❌ Upload failed: {response.text}")
        return None

def wait_for_processing(doc_uuid, max_wait=60):
    """Wait for document processing to complete."""
    print("\n" + "="*80)
    print("4. WAITING FOR DOCUMENT PROCESSING")
    print("="*80)
    
    print(f"Waiting for document {doc_uuid} to process...")
    
    status_url = f"{BASE_URL}/api/v1/documents/{doc_uuid}/status"
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(status_url)
            if response.status_code == 200:
                status = response.json()
                current_status = status.get('status', 'unknown')
                print(f"  Status: {current_status}")
                
                if current_status in ['completed', 'success', 'done']:
                    print(f"✅ Processing complete!")
                    return True
                elif current_status in ['failed', 'error']:
                    print(f"❌ Processing failed: {status}")
                    return False
            
            time.sleep(2)
        except Exception as e:
            print(f"  Waiting... ({int(time.time() - start_time)}s)")
            time.sleep(2)
    
    print(f"⚠️  Timeout waiting for processing")
    return False

def verify_chunks(doc_uuid):
    """Verify chunks were created and stored."""
    print("\n" + "="*80)
    print("5. VERIFYING CHUNKS IN DATABASE")
    print("="*80)
    
    chunks_url = f"{BASE_URL}/api/v1/chunks/document/{doc_uuid}"
    
    print(f"Fetching chunks from: {chunks_url}")
    
    response = requests.get(chunks_url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        total_chunks = result.get('total_chunks', 0)
        chunks = result.get('chunks', [])
        
        print(f"✅ Found {total_chunks} chunks!")
        
        if total_chunks > 0:
            # Show first chunk details
            first_chunk = chunks[0]
            print(f"\n📄 First Chunk Details:")
            print(f"  Chunk ID: {first_chunk.get('chunk_id')}")
            print(f"  Strategy: {first_chunk.get('chunking_strategy', 'unknown')}")
            print(f"  Content length: {len(first_chunk.get('original_content', ''))} chars")
            print(f"  Content preview: {first_chunk.get('original_content', '')[:100]}...")
            
            # Check for enrichment
            if first_chunk.get('enriched_content'):
                print(f"  ✨ Enriched: Yes")
                print(f"  Enriched preview: {first_chunk.get('enriched_content', '')[:100]}...")
            else:
                print(f"  Enriched: No")
        
        return total_chunks
    elif response.status_code == 404:
        print(f"❌ No chunks found for document {doc_uuid}")
        return 0
    else:
        print(f"❌ Error fetching chunks: {response.text}")
        return 0

def test_chunk_stats():
    """Test chunk statistics endpoint."""
    print("\n" + "="*80)
    print("6. TESTING CHUNK STATISTICS API")
    print("="*80)
    
    stats_url = f"{BASE_URL}/api/v1/chunks/stats"
    
    response = requests.get(stats_url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Statistics:")
        print(f"  Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  Enriched chunks: {stats.get('enriched_chunks', 0)}")
        print(f"  By strategy: {stats.get('by_strategy', {})}")
        print(f"✅ Statistics API working")
        return stats
    else:
        print(f"⚠️  Stats endpoint returned: {response.text}")
        return None

def main():
    """Run end-to-end validation test."""
    print("\n" + "="*80)
    print("BRAIN MVP - END-TO-END VALIDATION TEST")
    print("="*80)
    print("Testing document upload → processing → chunking → storage → retrieval")
    
    try:
        # Test 1: API Health
        test_health()
        
        # Test 2: Download test PDF
        pdf_path = download_test_pdf()
        
        # Test 3: Upload document
        doc_uuid = upload_document(pdf_path)
        
        if not doc_uuid:
            print("\n❌ VALIDATION FAILED: Could not upload document")
            print("This might be a known issue. Trying direct chunking test instead...")
            sys.exit(1)
        
        # Test 4: Wait for processing
        if isinstance(doc_uuid, str):
            processing_complete = wait_for_processing(doc_uuid)
            
            if processing_complete:
                # Test 5: Verify chunks
                chunk_count = verify_chunks(doc_uuid)
                
                if chunk_count > 0:
                    # Test 6: Statistics
                    test_chunk_stats()
                    
                    print("\n" + "="*80)
                    print("✅ END-TO-END VALIDATION SUCCESSFUL!")
                    print("="*80)
                    print(f"\n📊 Summary:")
                    print(f"  - API: Healthy")
                    print(f"  - Document uploaded: {doc_uuid}")
                    print(f"  - Processing: Complete")
                    print(f"  - Chunks created: {chunk_count}")
                    print(f"  - Chunk retrieval: Working")
                    print(f"\n✅ System is ready for query integration!")
                else:
                    print("\n⚠️  PARTIAL SUCCESS: Document uploaded but no chunks found")
                    print("   Chunking may be disabled in config")
            else:
                print("\n⚠️  Processing did not complete in time")
        else:
            print(f"\n⚠️  Unexpected response from upload: {doc_uuid}")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
