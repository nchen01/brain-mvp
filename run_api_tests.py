#!/usr/bin/env python3
"""
Run comprehensive API tests for DocForge Brain MVP.

This script runs the complete API test suite including:
- Authentication tests
- Document upload and management tests
- Version management tests
- Processing status tests
- Search functionality tests
- Error handling tests
- End-to-end workflow tests
"""

import subprocess
import sys
import time
import requests
from pathlib import Path


def check_api_server():
    """Check if API server is running."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_api_server():
    """Start the API server in background."""
    print("🚀 Starting API server...")
    
    # Start server in background
    server_process = subprocess.Popen(
        [sys.executable, "src/api/server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    for i in range(30):  # Wait up to 30 seconds
        if check_api_server():
            print("✅ API server is running")
            return server_process
        time.sleep(1)
        print(f"   Waiting for server... ({i+1}/30)")
    
    print("❌ Failed to start API server")
    server_process.terminate()
    return None


def run_tests():
    """Run the API tests."""
    print("🧪 Running comprehensive API tests...")
    
    # Run pytest with the API test file
    test_file = "tests/integration/test_api_comprehensive.py"
    
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_file,
            "-v",
            "--tb=short",
            "--color=yes"
        ], check=True)
        
        print("✅ All API tests passed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Some tests failed (exit code: {e.returncode})")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def main():
    """Main test runner."""
    print("DocForge Brain MVP - API Test Suite")
    print("=" * 50)
    
    # Check if server is already running
    if check_api_server():
        print("✅ API server is already running")
        server_process = None
    else:
        # Start server
        server_process = start_api_server()
        if not server_process:
            print("❌ Cannot start API server. Please start it manually:")
            print("   python src/api/server.py")
            return 1
    
    try:
        # Run tests
        success = run_tests()
        
        if success:
            print("\n🎉 All API tests completed successfully!")
            print("\nAPI Features Tested:")
            print("✅ Authentication and authorization")
            print("✅ Document upload and versioning")
            print("✅ Processing status tracking")
            print("✅ Version management")
            print("✅ Document retrieval and download")
            print("✅ Search functionality")
            print("✅ Error handling")
            print("✅ End-to-end workflows")
            return 0
        else:
            print("\n❌ Some tests failed. Check the output above for details.")
            return 1
            
    finally:
        # Clean up server if we started it
        if server_process:
            print("\n🛑 Stopping API server...")
            server_process.terminate()
            server_process.wait()


if __name__ == "__main__":
    sys.exit(main())