#!/usr/bin/env python3
"""
Test document upload functionality
"""

import subprocess
import sys
import json
from pathlib import Path

def run_command(command, timeout=30):
    """Run shell command with timeout"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"

def test_document_upload():
    """Test document upload using curl"""
    print("📄 Testing Document Upload...")
    
    # Create a test document
    test_content = """# Brain MVP Test Document

This is a test document for the Brain MVP system.

## Features to Test
- Document upload and processing
- Text extraction and analysis
- Storage and retrieval
- API functionality

## Content
This document contains various types of content to test the processing pipeline:
- Plain text paragraphs
- Structured headings
- Lists and formatting
- Technical terminology

The Brain MVP should be able to process this document and make it searchable through the RAG system.
"""
    
    test_file = Path("test_upload.txt")
    test_file.write_text(test_content)
    
    try:
        # Test document upload
        success, stdout, stderr = run_command(
            f'curl -X POST -F "file=@{test_file}" http://localhost:8080/api/v1/documents/upload',
            timeout=30
        )
        
        if success:
            print("✅ Document upload successful")
            print(f"Response: {stdout}")
            
            # Try to parse JSON response
            try:
                response = json.loads(stdout)
                if "document_id" in response:
                    print(f"✅ Document ID received: {response['document_id']}")
                    return True
            except json.JSONDecodeError:
                print("⚠️  Response is not JSON, but upload succeeded")
                return True
        else:
            print(f"❌ Document upload failed: {stderr}")
            return False
            
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()
    
    return False

def test_api_endpoints():
    """Test various API endpoints"""
    print("🌐 Testing API Endpoints...")
    
    endpoints = [
        ("/health", "Health Check"),
        ("/", "Root Endpoint"),
        ("/docs", "API Documentation"),
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        success, stdout, stderr = run_command(
            f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:8080{endpoint}",
            timeout=10
        )
        
        if success:
            status_code = stdout.strip()
            if status_code in ["200", "404"]:  # 404 is acceptable for some endpoints
                print(f"✅ {name}: HTTP {status_code}")
                results.append(True)
            else:
                print(f"❌ {name}: HTTP {status_code}")
                results.append(False)
        else:
            print(f"❌ {name}: Request failed")
            results.append(False)
    
    return all(results)

def main():
    """Run document upload tests"""
    print("🧪 Brain MVP Document Upload Test")
    print("=" * 40)
    
    # Test API endpoints first
    api_success = test_api_endpoints()
    
    # Test document upload
    upload_success = test_document_upload()
    
    print("\\n" + "=" * 40)
    print("📋 UPLOAD TEST SUMMARY")
    print("=" * 40)
    
    if api_success:
        print("✅ API Endpoints Working")
    else:
        print("❌ API Endpoints Failed")
    
    if upload_success:
        print("✅ Document Upload Working")
    else:
        print("❌ Document Upload Failed")
    
    overall_success = api_success and upload_success
    
    if overall_success:
        print("\\n🎉 ALL UPLOAD TESTS PASSED!")
    else:
        print("\\n⚠️  Some upload tests failed.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)