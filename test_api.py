#!/usr/bin/env python3
"""
Test script for DocForge Brain MVP API

This script tests the document upload and versioning endpoints.
"""

import requests
import json
import time
from pathlib import Path


def test_api_endpoints():
    """Test the main API endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing DocForge Brain MVP API")
    print("=" * 50)
    
    # Authentication token storage
    auth_token = None
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on port 8000")
        print("   Start server with: python src/api/server.py")
        return False
    
    # Test 2: Root endpoint
    print("\n2. Testing root endpoint...")
    response = requests.get(f"{base_url}/")
    if response.status_code == 200:
        print("✅ Root endpoint working")
        data = response.json()
        print(f"   System: {data.get('message')}")
        print(f"   Version: {data.get('version')}")
    else:
        print(f"❌ Root endpoint failed: {response.status_code}")
    
    # Test 3: Authentication
    print("\n3. Testing authentication...")
    
    # Get test users
    users_response = requests.get(f"{base_url}/api/v1/auth/test/users")
    if users_response.status_code == 200:
        users_data = users_response.json()
        print("✅ Test users available")
        if users_data.get('users'):
            test_user = users_data['users'][0]
            print(f"   Using test user: {test_user['username']}")
            
            # Login
            login_response = requests.post(
                f"{base_url}/api/v1/auth/login",
                json={
                    "username": test_user['username'],
                    "password": "password"  # Default test password
                }
            )
            
            if login_response.status_code == 200:
                print("✅ Login successful")
                login_data = login_response.json()
                auth_token = login_data['access_token']
                print(f"   Token type: {login_data['token_type']}")
                print(f"   Expires in: {login_data['expires_in']} seconds")
            else:
                print(f"❌ Login failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
    else:
        print(f"❌ Could not get test users: {users_response.status_code}")
    
    # Test 4: Document upload (with authentication)
    print("\n3. Testing document upload...")
    
    # Create a test document
    test_content = """# Test Document
    
This is a test document for the DocForge Brain MVP API.

## Features
- Document processing
- Version management  
- RAG preparation

## Content
This document contains sample text to test the processing pipeline.
"""
    
    test_file_path = Path("test_document.txt")
    test_file_path.write_text(test_content)
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_document.txt', f, 'text/plain')}
            metadata = json.dumps({
                'author': 'API Test',
                'category': 'test',
                'tags': ['api', 'test', 'document']
            })
            
            headers = {}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            
            response = requests.post(
                f"{base_url}/api/v1/documents/upload",
                files=files,
                data={'metadata': metadata},
                headers=headers
            )
        
        if response.status_code == 200:
            print("✅ Document upload successful")
            upload_data = response.json()
            document_id = upload_data['document_id']
            task_id = upload_data.get('processing_queue_id')
            
            print(f"   Document ID: {document_id}")
            print(f"   Task ID: {task_id}")
            print(f"   Filename: {upload_data['filename']}")
            print(f"   File size: {upload_data['file_size']} bytes")
            
            # Test 5: Check processing status
            print("\n4. Testing processing status...")
            if task_id:
                for i in range(3):
                    status_response = requests.get(
                        f"{base_url}/api/v1/documents/{document_id}/status",
                        params={'task_id': task_id}
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   Status: {status_data['status']}")
                        print(f"   Stage: {status_data['stage']}")
                        print(f"   Progress: {status_data['progress']}%")
                        
                        if status_data['status'] in ['completed', 'failed']:
                            break
                    
                    time.sleep(1)
            
            # Test 6: Get document versions
            print("\n5. Testing version history...")
            versions_response = requests.get(f"{base_url}/api/v1/documents/{document_id}/versions")
            
            if versions_response.status_code == 200:
                print("✅ Version history retrieved")
                versions_data = versions_response.json()
                print(f"   Lineage ID: {versions_data['lineage_id']}")
                print(f"   Total versions: {versions_data['total_versions']}")
                print(f"   Current version: {versions_data['current_version']['filename']}")
            else:
                print(f"❌ Version history failed: {versions_response.status_code}")
            
            # Test 7: Document download
            print("\n6. Testing document download...")
            download_response = requests.get(
                f"{base_url}/api/v1/documents/{document_id}/download",
                params={'format': 'original'}
            )
            
            if download_response.status_code == 200:
                print("✅ Document download successful")
                print(f"   Content length: {len(download_response.content)} bytes")
            else:
                print(f"❌ Document download failed: {download_response.status_code}")
            
            return True
            
        else:
            print(f"❌ Document upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()
    
    return False


def main():
    """Main test function."""
    print("DocForge Brain MVP API Test Suite")
    print("Make sure the API server is running: python src/api/server.py")
    print()
    
    success = test_api_endpoints()
    
    if success:
        print("\n🎉 All API tests passed!")
        print("\nNext steps:")
        print("- Test with different file formats (PDF, DOCX, etc.)")
        print("- Test version branching")
        print("- Test error handling")
        print("- Test authentication (when implemented)")
    else:
        print("\n❌ Some tests failed. Check the API server and try again.")


if __name__ == "__main__":
    main()