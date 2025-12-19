#!/usr/bin/env python3
"""
Simple Docker End-to-End Test for Brain MVP
Tests basic Docker functionality without external dependencies.
"""

import subprocess
import time
import sys
import json
from pathlib import Path

def run_command(command, timeout=60):
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

def test_docker_environment():
    """Test Docker environment"""
    print("🔧 Testing Docker Environment...")
    
    # Check Docker
    success, stdout, stderr = run_command("docker --version")
    if success:
        print(f"✅ Docker: {stdout.strip()}")
    else:
        print(f"❌ Docker not found: {stderr}")
        return False
    
    # Check Docker Compose
    success, stdout, stderr = run_command("docker-compose --version")
    if success:
        print(f"✅ Docker Compose: {stdout.strip()}")
    else:
        print(f"❌ Docker Compose not found: {stderr}")
        return False
    
    return True

def test_required_files():
    """Test required files exist"""
    print("\\n📁 Testing Required Files...")
    
    required_files = [
        "docker-compose.yml",
        "Dockerfile", 
        "requirements.txt",
        "src/api/main.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def test_docker_build():
    """Test Docker build"""
    print("\\n🏗️  Testing Docker Build...")
    
    # Clean up first
    print("Cleaning up existing containers...")
    run_command("docker-compose down -v", timeout=30)
    
    # Build
    print("Building Docker images...")
    success, stdout, stderr = run_command("docker-compose build brain-mvp", timeout=300)
    
    if success:
        print("✅ Docker build successful")
        return True
    else:
        print(f"❌ Docker build failed:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False

def test_docker_startup():
    """Test Docker startup"""
    print("\\n🚀 Testing Docker Startup...")
    
    # Start database services first
    print("Starting database services...")
    success, stdout, stderr = run_command("docker-compose up -d postgres redis", timeout=60)
    
    if not success:
        print(f"❌ Failed to start database services: {stderr}")
        return False
    
    print("✅ Database services started")
    
    # Wait for databases to be ready
    print("Waiting for databases to initialize...")
    time.sleep(15)
    
    # Start main application
    print("Starting Brain MVP application...")
    success, stdout, stderr = run_command("docker-compose up -d brain-mvp", timeout=60)
    
    if success:
        print("✅ Brain MVP application started")
        return True
    else:
        print(f"❌ Failed to start Brain MVP: {stderr}")
        return False

def test_container_health():
    """Test container health"""
    print("\\n🏥 Testing Container Health...")
    
    # Wait for application to start
    print("Waiting for application to initialize...")
    time.sleep(30)
    
    # Check container status
    success, stdout, stderr = run_command("docker-compose ps")
    print("Container Status:")
    print(stdout)
    
    # Check if containers are running
    success, stdout, stderr = run_command("docker-compose ps --services --filter status=running")
    running_services = stdout.strip().split('\\n') if stdout.strip() else []
    
    expected_services = ['postgres', 'redis', 'brain-mvp']
    all_running = True
    
    for service in expected_services:
        if service in running_services:
            print(f"✅ {service} is running")
        else:
            print(f"❌ {service} is not running")
            all_running = False
    
    return all_running

def test_application_logs():
    """Test application logs"""
    print("\\n📊 Testing Application Logs...")
    
    # Get application logs
    success, stdout, stderr = run_command("docker-compose logs --tail=20 brain-mvp")
    
    if success and stdout.strip():
        print("✅ Application is generating logs")
        print("Recent logs:")
        print(stdout[-500:])  # Show last 500 characters
        return True
    else:
        print("❌ No application logs found")
        if stderr:
            print(f"Error: {stderr}")
        return False

def test_database_connectivity():
    """Test database connectivity"""
    print("\\n🗄️  Testing Database Connectivity...")
    
    # Test PostgreSQL
    success, stdout, stderr = run_command(
        "docker-compose exec -T postgres pg_isready -U brain_user -d brain_mvp",
        timeout=10
    )
    
    if success:
        print("✅ PostgreSQL is ready")
    else:
        print(f"❌ PostgreSQL not ready: {stderr}")
    
    # Test Redis
    success2, stdout2, stderr2 = run_command(
        "docker-compose exec -T redis redis-cli ping",
        timeout=10
    )
    
    if success2 and "PONG" in stdout2:
        print("✅ Redis is responding")
    else:
        print(f"❌ Redis not responding: {stderr2}")
    
    return success and success2

def test_api_accessibility():
    """Test API accessibility using curl"""
    print("\\n🌐 Testing API Accessibility...")
    
    # Test health endpoint with curl
    success, stdout, stderr = run_command(
        "curl -f -s http://localhost:8080/health",
        timeout=10
    )
    
    if success:
        print("✅ Health endpoint accessible")
        print(f"Response: {stdout}")
        return True
    else:
        print(f"❌ Health endpoint not accessible: {stderr}")
        
        # Try to get more info about the application
        print("\\nChecking application status...")
        run_command("docker-compose logs --tail=10 brain-mvp")
        
        return False

def cleanup():
    """Clean up test resources"""
    print("\\n🧹 Cleanup...")
    print("Containers will be left running for manual inspection.")
    print("To stop them, run: docker-compose down")

def main():
    """Run all tests"""
    print("🧪 Brain MVP Simple Docker End-to-End Test")
    print("=" * 50)
    
    tests = [
        ("Docker Environment", test_docker_environment),
        ("Required Files", test_required_files),
        ("Docker Build", test_docker_build),
        ("Docker Startup", test_docker_startup),
        ("Container Health", test_container_health),
        ("Application Logs", test_application_logs),
        ("Database Connectivity", test_database_connectivity),
        ("API Accessibility", test_api_accessibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\\n🎉 ALL TESTS PASSED! Brain MVP is working correctly.")
    else:
        print(f"\\n⚠️  {total - passed} tests failed. Check the output above for details.")
    
    cleanup()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)