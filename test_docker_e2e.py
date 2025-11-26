#!/usr/bin/env python3
"""
Comprehensive End-to-End Docker Testing for Brain MVP
Tests the complete system after cleanup to ensure all functionality works.
"""

import requests
import time
import json
import os
import subprocess
import sys
from pathlib import Path

class DockerE2ETest:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    def run_command(self, command, timeout=60):
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
    
    def wait_for_service(self, url, timeout=120, interval=5):
        """Wait for service to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(interval)
        return False
    
    def test_docker_setup(self):
        """Test Docker environment setup"""
        print("\\n🔧 Testing Docker Setup...")
        
        # Check Docker is running
        success, stdout, stderr = self.run_command("docker --version")
        self.log_test("Docker Installation", success, stdout.strip() if success else stderr)
        
        # Check Docker Compose
        success, stdout, stderr = self.run_command("docker-compose --version")
        self.log_test("Docker Compose Installation", success, stdout.strip() if success else stderr)
        
        return all(result["success"] for result in self.test_results[-2:])
    
    def test_environment_files(self):
        """Test required environment files exist"""
        print("\\n📁 Testing Environment Files...")
        
        required_files = [
            ".env.example",
            "docker-compose.yml", 
            "Dockerfile",
            "requirements.txt",
            "pyproject.toml"
        ]
        
        for file_path in required_files:
            exists = Path(file_path).exists()
            self.log_test(f"File exists: {file_path}", exists)
        
        # Check if .env exists, if not create from example
        if not Path(".env").exists():
            if Path(".env.example").exists():
                success, _, _ = self.run_command("cp .env.example .env")
                self.log_test("Create .env from example", success)
            else:
                self.log_test("Create .env from example", False, ".env.example not found")
    
    def create_missing_files(self):
        """Create any missing files needed for Docker"""
        print("\\n🔨 Creating Missing Files...")
        
        # Create init-db.sql if missing
        init_db_path = Path("scripts/init-db.sql")
        if not init_db_path.exists():
            init_db_path.parent.mkdir(exist_ok=True)
            init_db_content = '''-- Brain MVP Database Initialization
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create basic tables will be handled by application migrations
'''
            init_db_path.write_text(init_db_content)
            self.log_test("Create init-db.sql", True)
        
        # Create test document if missing
        test_doc_path = Path("test_sample.txt")
        if not test_doc_path.exists():
            test_content = '''# Brain MVP Test Document

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
'''
            test_doc_path.write_text(test_content)
            self.log_test("Create test document", True)
    
    def test_docker_build(self):
        """Test Docker image building"""
        print("\\n🏗️  Testing Docker Build...")
        
        # Clean up any existing containers
        self.run_command("docker-compose down -v", timeout=30)
        
        # Build the images
        success, stdout, stderr = self.run_command("docker-compose build", timeout=300)
        self.log_test("Docker Build", success, "Build completed" if success else f"Build failed: {stderr}")
        
        return success
    
    def test_docker_startup(self):
        """Test Docker container startup"""
        print("\\n🚀 Testing Docker Startup...")
        
        # Start the services
        success, stdout, stderr = self.run_command("docker-compose up -d postgres redis", timeout=60)
        self.log_test("Start Database Services", success, "Services started" if success else stderr)
        
        if not success:
            return False
        
        # Wait for database to be ready
        time.sleep(10)
        
        # Start main application
        success, stdout, stderr = self.run_command("docker-compose up -d brain-mvp", timeout=60)
        self.log_test("Start Brain MVP Application", success, "Application started" if success else stderr)
        
        return success
    
    def test_service_health(self):
        """Test service health endpoints"""
        print("\\n🏥 Testing Service Health...")
        
        # Wait for application to be ready
        print("Waiting for application to start...")
        ready = self.wait_for_service(f"{self.base_url}/health", timeout=120)
        self.log_test("Application Health Check", ready, "Service is healthy" if ready else "Service not responding")
        
        if not ready:
            # Check container logs for debugging
            success, logs, _ = self.run_command("docker-compose logs brain-mvp")
            print(f"\\nContainer logs:\\n{logs}")
        
        return ready
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        print("\\n🌐 Testing API Endpoints...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=10)
            self.log_test("Health Endpoint", response.status_code == 200, f"Status: {response.status_code}")
            
            # Test docs endpoint
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            self.log_test("API Documentation", response.status_code == 200, f"Status: {response.status_code}")
            
            # Test root endpoint
            response = requests.get(f"{self.base_url}/", timeout=10)
            self.log_test("Root Endpoint", response.status_code in [200, 404], f"Status: {response.status_code}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.log_test("API Endpoints", False, f"Request failed: {e}")
            return False
    
    def test_document_upload(self):
        """Test document upload functionality"""
        print("\\n📄 Testing Document Upload...")
        
        try:
            # Prepare test file
            test_file_path = Path("test_sample.txt")
            if not test_file_path.exists():
                self.log_test("Document Upload", False, "Test file not found")
                return False
            
            # Upload document
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_sample.txt', f, 'text/plain')}
                response = requests.post(
                    f"{self.base_url}/api/documents/upload",
                    files=files,
                    timeout=30
                )
            
            success = response.status_code in [200, 201]
            message = f"Status: {response.status_code}"
            if success and response.headers.get('content-type', '').startswith('application/json'):
                try:
                    result = response.json()
                    message += f", Document ID: {result.get('document_id', 'N/A')}"
                except:
                    pass
            
            self.log_test("Document Upload", success, message)
            return success
            
        except requests.exceptions.RequestException as e:
            self.log_test("Document Upload", False, f"Upload failed: {e}")
            return False
    
    def test_database_connection(self):
        """Test database connectivity"""
        print("\\n🗄️  Testing Database Connection...")
        
        # Test PostgreSQL connection
        success, stdout, stderr = self.run_command(
            "docker-compose exec -T postgres psql -U brain_user -d brain_mvp -c 'SELECT version();'",
            timeout=10
        )
        self.log_test("PostgreSQL Connection", success, "Connected" if success else stderr)
        
        # Test Redis connection
        success, stdout, stderr = self.run_command(
            "docker-compose exec -T redis redis-cli ping",
            timeout=10
        )
        self.log_test("Redis Connection", success, "Connected" if success else stderr)
    
    def test_logs_and_monitoring(self):
        """Test logging and monitoring"""
        print("\\n📊 Testing Logs and Monitoring...")
        
        # Check if logs are being generated
        success, logs, _ = self.run_command("docker-compose logs --tail=10 brain-mvp")
        has_logs = success and len(logs.strip()) > 0
        self.log_test("Application Logging", has_logs, "Logs are being generated" if has_logs else "No logs found")
        
        # Check log volume
        success, stdout, _ = self.run_command("docker volume ls | grep brain_logs")
        self.log_test("Log Volume", success, "Log volume exists" if success else "Log volume not found")
    
    def cleanup(self):
        """Clean up test resources"""
        print("\\n🧹 Cleaning Up...")
        
        # Remove test file
        test_file = Path("test_sample.txt")
        if test_file.exists():
            test_file.unlink()
            print("Removed test file")
        
        # Optionally stop containers (uncomment if desired)
        # self.run_command("docker-compose down")
        # print("Stopped Docker containers")
    
    def run_all_tests(self):
        """Run complete end-to-end test suite"""
        print("🧪 Brain MVP Docker End-to-End Testing")
        print("=" * 50)
        
        # Pre-flight checks
        if not self.test_docker_setup():
            print("\\n❌ Docker setup failed. Please install Docker and Docker Compose.")
            return False
        
        self.test_environment_files()
        self.create_missing_files()
        
        # Docker tests
        if not self.test_docker_build():
            print("\\n❌ Docker build failed. Check the build logs above.")
            return False
        
        if not self.test_docker_startup():
            print("\\n❌ Docker startup failed. Check the startup logs above.")
            return False
        
        # Service tests
        if not self.test_service_health():
            print("\\n❌ Service health check failed. Application may not be running properly.")
            return False
        
        # Functional tests
        self.test_api_endpoints()
        self.test_document_upload()
        self.test_database_connection()
        self.test_logs_and_monitoring()
        
        # Results summary
        self.print_summary()
        
        # Cleanup
        self.cleanup()
        
        # Return overall success
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        return passed_tests == total_tests
    
    def print_summary(self):
        """Print test results summary"""
        print("\\n" + "=" * 50)
        print("📋 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        overall_status = "✅ ALL TESTS PASSED" if failed_tests == 0 else "❌ SOME TESTS FAILED"
        print(f"\\n{overall_status}")

if __name__ == "__main__":
    tester = DockerE2ETest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)