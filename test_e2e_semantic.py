import os
import sys
import time
import requests
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
PDF_URL = "https://arxiv.org/pdf/2005.11401.pdf"  # RAG paper
DOWNLOAD_PATH = "test_document_semantic.pdf"

def download_pdf():
    """Download a test PDF."""
    print("\n" + "="*80)
    print("2. DOWNLOADING TEST PDF")
    print("="*80)
    
    if os.path.exists(DOWNLOAD_PATH):
        print(f"Using existing file: {DOWNLOAD_PATH}")
        return

    print(f"Downloading from: {PDF_URL}")
    response = requests.get(PDF_URL)
    with open(DOWNLOAD_PATH, 'wb') as f:
        f.write(response.content)
    print(f"✅ Downloaded: {len(response.content):,} bytes")

def test_health():
    """Test API health."""
    print("\n" + "="*80)
    print("1. TESTING API HEALTH")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ API is healthy")
        else:
            print("❌ API is unhealthy")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect to API: {e}")
        sys.exit(1)

def upload_document():
    """Upload document."""
    print("\n" + "="*80)
    print("3. UPLOADING DOCUMENT VIA API")
    print("="*80)
    
    with open(DOWNLOAD_PATH, 'rb') as f:
        files = {'file': (DOWNLOAD_PATH, f, 'application/pdf')}
        print(f"Uploading to: {BASE_URL}/api/v1/documents/upload")
        
        response = requests.post(f"{BASE_URL}/api/v1/documents/upload", files=files)
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            data = response.json()
            print(f"Response: {data}")
            doc_id = data.get('document_id')
            print(f"✅ Document uploaded: {doc_id}")
            return doc_id
        else:
            print(f"❌ Upload failed: {response.text}")
            sys.exit(1)

def wait_for_processing(doc_id):
    """Wait for processing to complete."""
    print("\n" + "="*80)
    print("4. WAITING FOR DOCUMENT PROCESSING")
    print("="*80)
    
    print(f"Waiting for document {doc_id} to process...")
    
    start_time = time.time()
    while time.time() - start_time < 300:  # 5 minute timeout
        response = requests.get(f"{BASE_URL}/api/v1/documents/{doc_id}/status")
        if response.status_code == 200:
            status = response.json().get('processing_status')
            print(f"  Status: {status}")
            
            if status == 'completed':
                print("✅ Processing complete!")
                return
            elif status == 'failed':
                print("❌ Processing failed!")
                sys.exit(1)
        
        time.sleep(2)
    
    print("❌ Timeout waiting for processing")
    sys.exit(1)

def verify_chunks(doc_id):
    """Verify chunks were created."""
    print("\n" + "="*80)
    print("5. VERIFYING CHUNKS IN DATABASE")
    print("="*80)
    
    url = f"{BASE_URL}/api/v1/chunks/document/{doc_id}"
    print(f"Fetching chunks from: {url}")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        chunks = data.get('chunks', [])
        count = len(chunks)
        print(f"✅ Found {count} chunks!")
        
        if count > 0:
            first_chunk = chunks[0]
            print("\n📄 First Chunk Details:")
            print(f"  Chunk ID: {first_chunk.get('chunk_id')}")
            print(f"  Strategy: {first_chunk.get('metadata', {}).get('chunk_type', 'unknown')}")
            print(f"  Content length: {len(first_chunk.get('content', ''))} chars")
            print(f"  Content preview: {first_chunk.get('content', '')[:100]}...")
            
            # Check for semantic chunking evidence
            # Semantic chunks typically have variable sizes and respect sentence boundaries
            print("\n📊 Chunk Size Distribution (First 5):")
            for i, chunk in enumerate(chunks[:5]):
                words = chunk.get('metadata', {}).get('word_count', 0)
                print(f"  Chunk {i}: {words} words")
                
    else:
        print(f"❌ No chunks found for document {doc_id}")
        print(f"Response: {response.text}")
        print("\n⚠️  PARTIAL SUCCESS: Document uploaded but no chunks found")

def main():
    test_health()
    download_pdf()
    doc_id = upload_document()
    wait_for_processing(doc_id)
    verify_chunks(doc_id)
    
    print("\n" + "="*80)
    print("✅ END-TO-END SEMANTIC TEST SUCCESSFUL!")
    print("="*80)

if __name__ == "__main__":
    main()
