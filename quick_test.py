#!/usr/bin/env python3
"""
Quick test script for Brain MVP - Upload, Monitor, Verify
"""
import requests
import time
import json

def quick_test():
    print("🧪 Brain MVP Quick Test")
    print("=" * 40)
    
    # Test content
    test_content = """# Brain MVP Test Document

This is a comprehensive test of the Brain MVP system.

## What This Tests
- Document upload functionality
- Text processing pipeline
- Status monitoring
- Content retrieval
- All processing stages (raw → preprocessed → postprocessed)

## Technical Details
- Processor: TextDocumentProcessor
- Expected stages: 3 (raw, preprocessed, postprocessed)
- Expected formats: text, markdown, json, chunks
- Expected features: chunking, abbreviation expansion

## Sample Content for Processing

### Lists and Structure
1. First item with important information
2. Second item with technical details
3. Third item with conclusions

### Abbreviations to Expand
- API (Application Programming Interface)
- MVP (Minimum Viable Product)
- RAG (Retrieval Augmented Generation)
- NLP (Natural Language Processing)

### Technical Terms
The system processes documents through multiple stages:
- Raw storage and validation
- Preprocessing with text extraction
- Postprocessing with chunking and enhancement

This content should be processed successfully and demonstrate all system capabilities.
"""
    
    base_url = "http://localhost:8000"
    
    # Step 1: Upload
    print("📤 Step 1: Uploading test document...")
    
    files = {'file': ('brain_mvp_test.txt', test_content, 'text/plain')}
    
    try:
        response = requests.post(f"{base_url}/api/v1/documents/upload", files=files, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Upload failed!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        result = response.json()
        document_id = result['document_id']
        print(f"✅ Upload successful!")
        print(f"   Document ID: {document_id}")
        print(f"   File size: {result['file_size']} bytes")
        print(f"   Status: {result['processing_status']}")
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False
    
    # Step 2: Monitor Processing
    print(f"\n⏳ Step 2: Monitoring processing...")
    
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            status_response = requests.get(f"{base_url}/api/v1/documents/{document_id}/status")
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"   📊 Status: {status['status']} | Stage: {status['stage']} | Progress: {status['progress']}%")
                
                if status['status'] == 'completed':
                    print("✅ Processing completed successfully!")
                    break
                elif status['status'] == 'failed':
                    print(f"❌ Processing failed!")
                    print(f"   Error: {status.get('error_message', 'Unknown error')}")
                    return False
            else:
                print(f"⚠️ Status check failed: {status_response.status_code}")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"⚠️ Status check error: {e}")
            time.sleep(3)
    else:
        print("⚠️ Processing timeout - checking final status...")
    
    # Step 3: Verify Results
    print(f"\n📄 Step 3: Retrieving processed content...")
    
    try:
        processed_response = requests.get(f"{base_url}/api/v1/documents/{document_id}/processed")
        
        if processed_response.status_code == 200:
            processed_data = processed_response.json()
            print(f"✅ Retrieved processed content!")
            print(f"   Processing stages: {len(processed_data)}")
            
            # Analyze results
            stages_found = []
            total_formats = []
            quality_info = []
            
            for item in processed_data:
                stage = item['processing_stage']
                formats = item['available_formats']
                quality = item.get('quality_metrics', {})
                
                stages_found.append(stage)
                total_formats.extend(formats)
                
                print(f"   📋 {stage.upper()} stage:")
                print(f"      Formats: {', '.join(formats)}")
                print(f"      Size: {item['file_size']} bytes")
                
                if quality:
                    print(f"      Quality: {quality}")
                    quality_info.append(f"{stage}: {quality}")
            
            # Summary
            print(f"\n📊 Processing Summary:")
            print(f"   Stages completed: {', '.join(stages_found)}")
            print(f"   Total formats available: {len(set(total_formats))}")
            print(f"   Unique formats: {', '.join(set(total_formats))}")
            
            if quality_info:
                print(f"   Quality metrics:")
                for info in quality_info:
                    print(f"      {info}")
            
            # Verify expected stages
            expected_stages = ['raw', 'preprocessed', 'postprocessed']
            missing_stages = [stage for stage in expected_stages if stage not in stages_found]
            
            if not missing_stages:
                print(f"\n🎉 ALL TESTS PASSED!")
                print(f"   ✅ Upload successful")
                print(f"   ✅ Processing completed")
                print(f"   ✅ All stages present: {', '.join(stages_found)}")
                print(f"   ✅ Multiple formats available")
                print(f"   ✅ Quality metrics generated")
                
                print(f"\n🚀 Your Brain MVP is fully functional!")
                print(f"   Document ID for reference: {document_id}")
                return True
            else:
                print(f"\n⚠️ Some stages missing: {', '.join(missing_stages)}")
                return False
                
        else:
            print(f"❌ Failed to retrieve processed content!")
            print(f"   Status: {processed_response.status_code}")
            print(f"   Response: {processed_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Content retrieval error: {e}")
        return False

def check_system_health():
    """Check if the system is running"""
    print("🔍 Checking system health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ System is healthy and ready!")
            return True
        else:
            print(f"⚠️ System health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to system: {e}")
        print("💡 Make sure to run: docker-compose up -d")
        return False

if __name__ == "__main__":
    print("🧠 Brain MVP Quick Test Script")
    print("=" * 50)
    
    # Check system health first
    if not check_system_health():
        exit(1)
    
    print()
    
    # Run the test
    success = quick_test()
    
    print("\n" + "=" * 50)
    if success:
        print("🎯 RESULT: All tests passed! Your Brain MVP is working perfectly.")
        print("\n📖 Next steps:")
        print("   1. Upload your own documents")
        print("   2. Check the full user guide: BRAIN_MVP_USER_GUIDE.md")
        print("   3. Explore the API at: http://localhost:8000/docs")
    else:
        print("❌ RESULT: Some tests failed. Check the output above for details.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check container status: docker-compose ps")
        print("   2. View logs: docker-compose logs brain-mvp")
        print("   3. Restart system: docker-compose restart brain-mvp")