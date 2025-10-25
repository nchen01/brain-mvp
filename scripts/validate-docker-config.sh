#!/bin/bash
# Docker Configuration Validation Script (No Docker Required)
# This script validates Docker configuration files without running Docker

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
    print_status "Validating: $test_name"
    
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

print_header "Brain MVP Docker Configuration Validation"

# Step 1: Check Required Files
print_header "Step 1: Required Files Check"

run_test "Dockerfile exists" "test -f Dockerfile"
run_test "docker-compose.yml exists" "test -f docker-compose.yml"
run_test "docker-compose.prod.yml exists" "test -f docker-compose.prod.yml"
run_test "requirements-docker.txt exists" "test -f requirements-docker.txt"
run_test ".env.example exists" "test -f .env.example"
run_test ".dockerignore exists" "test -f .dockerignore"

# Step 2: Check Scripts
print_header "Step 2: Management Scripts Check"

run_test "docker-dev.sh exists and executable" "test -x scripts/docker-dev.sh"
run_test "docker-prod.sh exists and executable" "test -x scripts/docker-prod.sh"
run_test "test-docker-setup.sh exists and executable" "test -x scripts/test-docker-setup.sh"
run_test "init-db.sql exists" "test -f scripts/init-db.sql"

# Step 3: Check Nginx Configuration
print_header "Step 3: Nginx Configuration Check"

run_test "nginx directory exists" "test -d nginx"
run_test "nginx.conf exists" "test -f nginx/nginx.conf"

# Step 4: Validate Environment Configuration
print_header "Step 4: Environment Configuration Check"

if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_success "✓ Created .env from .env.example"
fi

run_test ".env file exists" "test -f .env"

# Check for required environment variables in .env.example
required_vars=("ENVIRONMENT" "SECRET_KEY" "POSTGRES_PASSWORD" "REDIS_PASSWORD" "DATABASE_URL" "REDIS_URL")
for var in "${required_vars[@]}"; do
    if grep -q "^${var}=" .env.example; then
        print_success "✓ $var defined in .env.example"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "✗ $var missing from .env.example"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
done

# Step 5: Validate Docker Compose Syntax (if docker-compose available)
print_header "Step 5: Docker Compose Syntax Check"

if command -v docker-compose &> /dev/null; then
    run_test "docker-compose.yml syntax" "docker-compose -f docker-compose.yml config"
    run_test "docker-compose.prod.yml syntax" "docker-compose -f docker-compose.prod.yml config"
else
    print_warning "docker-compose not available - skipping syntax validation"
    print_status "Install Docker to run full syntax validation"
fi

# Step 6: Check Python Dependencies
print_header "Step 6: Python Dependencies Check"

run_test "requirements.txt exists" "test -f requirements.txt"

# Check if requirements-docker.txt includes base requirements
if grep -q "^-r requirements.txt" requirements-docker.txt; then
    print_success "✓ requirements-docker.txt includes base requirements"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "✗ requirements-docker.txt should include base requirements"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Check for Docker-specific dependencies
docker_deps=("psycopg2-binary" "redis" "gunicorn")
for dep in "${docker_deps[@]}"; do
    if grep -q "^${dep}" requirements-docker.txt; then
        print_success "✓ $dep included in Docker requirements"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "⚠ $dep not found in Docker requirements"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
done

# Step 7: Check Application Structure
print_header "Step 7: Application Structure Check"

required_dirs=("src" "src/api" "src/config" "src/utils" "tests" "docs")
for dir in "${required_dirs[@]}"; do
    run_test "$dir directory exists" "test -d $dir"
done

# Check for main application files
required_files=("src/api/app.py" "src/config/settings.py" "pyproject.toml")
for file in "${required_files[@]}"; do
    run_test "$file exists" "test -f $file"
done

# Step 8: Validate Dockerfile Syntax
print_header "Step 8: Dockerfile Validation"

# Check for multi-stage build
if grep -q "FROM.*as.*base" Dockerfile; then
    print_success "✓ Multi-stage Dockerfile detected"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "⚠ Single-stage Dockerfile (multi-stage recommended)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Check for non-root user
if grep -q "USER.*appuser" Dockerfile; then
    print_success "✓ Non-root user configured"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "✗ No non-root user found (security risk)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Check for health check
if grep -q "HEALTHCHECK" Dockerfile; then
    print_success "✓ Health check configured"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "⚠ No health check found"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Step 9: Security Checks
print_header "Step 9: Security Configuration Check"

# Check .dockerignore for sensitive files
sensitive_patterns=(".env" "*.key" "*.pem" ".git")
for pattern in "${sensitive_patterns[@]}"; do
    if grep -q "$pattern" .dockerignore; then
        print_success "✓ $pattern excluded in .dockerignore"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "⚠ $pattern not found in .dockerignore"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
done

# Check for default passwords in .env.example
if grep -q "change_this\|password_here\|your-.*-key" .env.example; then
    print_success "✓ Placeholder values found in .env.example"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "⚠ Consider using placeholder values in .env.example"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Final Results
print_header "Validation Results Summary"

echo ""
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests:  $TESTS_TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    print_success "🎉 All validations passed! Docker configuration looks good."
    echo ""
    echo "Next steps:"
    echo "1. Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/"
    echo "2. Run full test: ./scripts/test-docker-setup.sh"
    echo "3. Start development: ./scripts/docker-dev.sh start"
    echo ""
    exit 0
else
    print_warning "⚠ Some validations failed or have warnings."
    echo ""
    echo "The configuration should still work, but consider addressing the issues above."
    echo ""
    echo "Next steps:"
    echo "1. Review and fix any errors above"
    echo "2. Install Docker Desktop if not already installed"
    echo "3. Run full test: ./scripts/test-docker-setup.sh"
    echo ""
    exit 0
fi