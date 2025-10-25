#!/bin/bash
# Docker Setup Testing Script for Brain MVP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    print_status "Testing: $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        print_success "✓ $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        print_error "✗ $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Function to run test with output
run_test_with_output() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    print_status "Testing: $test_name"
    
    if output=$(eval "$test_command" 2>&1); then
        print_success "✓ $test_name"
        echo "   Output: $output"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        print_error "✗ $test_name"
        echo "   Error: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

print_header "Brain MVP Docker Setup Testing"

# Step 1: Check Docker Installation
print_header "Step 1: Docker Installation Check"

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    echo ""
    echo "Please install Docker Desktop for macOS:"
    echo "1. Visit: https://docs.docker.com/desktop/install/mac-install/"
    echo "2. Download Docker Desktop for Mac"
    echo "3. Install and start Docker Desktop"
    echo "4. Run this script again"
    echo ""
    exit 1
fi

run_test_with_output "Docker version" "docker --version"
run_test_with_output "Docker Compose version" "docker-compose --version"

# Step 2: Check Docker Service
print_header "Step 2: Docker Service Check"

run_test "Docker daemon running" "docker info"

# Step 3: Check System Resources
print_header "Step 3: System Resources Check"

# Check available memory (should be at least 4GB)
if command -v free &> /dev/null; then
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
elif command -v vm_stat &> /dev/null; then
    # macOS memory check
    MEMORY_BYTES=$(sysctl -n hw.memsize)
    MEMORY_GB=$((MEMORY_BYTES / 1024 / 1024 / 1024))
else
    MEMORY_GB=8  # Assume sufficient memory if we can't check
fi

if [ "$MEMORY_GB" -ge 4 ]; then
    print_success "✓ Sufficient memory: ${MEMORY_GB}GB"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "⚠ Low memory: ${MEMORY_GB}GB (recommended: 4GB+)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Check available disk space (should be at least 10GB)
DISK_AVAILABLE=$(df -h . | awk 'NR==2{print $4}' | sed 's/G.*//')
if [ "$DISK_AVAILABLE" -ge 10 ]; then
    print_success "✓ Sufficient disk space: ${DISK_AVAILABLE}GB available"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "⚠ Low disk space: ${DISK_AVAILABLE}GB (recommended: 10GB+)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Step 4: Check Environment Configuration
print_header "Step 4: Environment Configuration"

if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "✓ Created .env from .env.example"
    else
        print_error "✗ .env.example not found"
        exit 1
    fi
fi

run_test ".env file exists" "test -f .env"

# Step 5: Test Docker Build
print_header "Step 5: Docker Build Test"

print_status "Building Docker image (this may take a few minutes)..."
if docker build -t brain-mvp-test --target development . > build.log 2>&1; then
    print_success "✓ Docker image built successfully"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "✗ Docker build failed"
    echo "Build log:"
    tail -20 build.log
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Step 6: Test Docker Compose Configuration
print_header "Step 6: Docker Compose Configuration Test"

run_test "Docker Compose config validation" "docker-compose config"

# Step 7: Start Services Test
print_header "Step 7: Services Startup Test"

print_status "Starting services (this may take a few minutes)..."
if docker-compose up -d > startup.log 2>&1; then
    print_success "✓ Services started successfully"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    print_header "Step 8: Service Health Checks"
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "✓ Containers are running"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "✗ Some containers failed to start"
        docker-compose ps
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test PostgreSQL connection
    if docker-compose exec -T postgres pg_isready -U brain_user > /dev/null 2>&1; then
        print_success "✓ PostgreSQL is ready"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "✗ PostgreSQL connection failed"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test Redis connection
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "✓ Redis is ready"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "✗ Redis connection failed"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test application health endpoint
    print_status "Testing application health endpoint..."
    sleep 10  # Give app more time to start
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "✓ Application health endpoint responding"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        # Test API documentation
        if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
            print_success "✓ API documentation accessible"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            print_error "✗ API documentation not accessible"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
        
    else
        print_error "✗ Application health endpoint not responding"
        print_status "Checking application logs..."
        docker-compose logs brain-mvp | tail -20
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
else
    print_error "✗ Failed to start services"
    echo "Startup log:"
    tail -20 startup.log
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Step 9: API Functionality Test
print_header "Step 9: API Functionality Test"

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    # Test root endpoint
    if curl -f http://localhost:8000/ > /dev/null 2>&1; then
        print_success "✓ Root endpoint responding"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "✗ Root endpoint not responding"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test health endpoint with detailed response
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    if echo "$HEALTH_RESPONSE" | grep -q "status"; then
        print_success "✓ Health endpoint returning valid JSON"
        echo "   Health status: $(echo "$HEALTH_RESPONSE" | grep -o '"status":"[^"]*"')"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "✗ Health endpoint not returning valid response"
        echo "   Response: $HEALTH_RESPONSE"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

# Step 10: Cleanup Test
print_header "Step 10: Cleanup Test"

print_status "Stopping services..."
if docker-compose down > /dev/null 2>&1; then
    print_success "✓ Services stopped successfully"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "✗ Failed to stop services"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Final Results
print_header "Test Results Summary"

echo ""
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests:  $TESTS_TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    print_success "🎉 All tests passed! Docker setup is working correctly."
    echo ""
    echo "Next steps:"
    echo "1. Start development environment: ./scripts/docker-dev.sh start"
    echo "2. Access application: http://localhost:8000"
    echo "3. View API docs: http://localhost:8000/docs"
    echo ""
    exit 0
else
    print_error "❌ Some tests failed. Please check the errors above."
    echo ""
    echo "Common solutions:"
    echo "1. Ensure Docker Desktop is running"
    echo "2. Check system resources (memory, disk space)"
    echo "3. Review .env configuration"
    echo "4. Check Docker logs: docker-compose logs"
    echo ""
    exit 1
fi