#!/bin/bash
# Docker Authentication Fix Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_header "Docker Authentication Fix"

print_status "The Docker test failed due to authentication issues with Docker Hub."
print_status "This is a common issue that can be resolved in several ways:"

echo ""
echo "🔧 SOLUTION OPTIONS:"
echo ""

echo "1. 📧 VERIFY DOCKER HUB EMAIL (Recommended)"
echo "   - Go to: https://hub.docker.com/"
echo "   - Log in to your Docker Hub account"
echo "   - Check your email and verify your account"
echo "   - Restart Docker Desktop"
echo ""

echo "2. 🔐 LOGIN TO DOCKER HUB"
echo "   - Run: docker login"
echo "   - Enter your Docker Hub credentials"
echo "   - Or create a free account at: https://hub.docker.com/"
echo ""

echo "3. 🚀 USE ALTERNATIVE REGISTRY (Quick Fix)"
echo "   - We can modify the Dockerfile to use a different registry"
echo "   - This bypasses Docker Hub authentication issues"
echo ""

echo "4. 🔄 RESTART DOCKER DESKTOP"
echo "   - Sometimes simply restarting Docker Desktop resolves auth issues"
echo "   - Quit Docker Desktop completely and restart it"
echo ""

print_warning "Would you like me to apply the quick fix using an alternative registry? (y/N)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    print_status "Applying quick fix using alternative registry..."
    
    # Create a backup of the original Dockerfile
    cp Dockerfile Dockerfile.backup
    
    # Update Dockerfile to use alternative registry
    sed -i.bak 's|FROM python:3.11-slim|FROM registry.access.redhat.com/ubi8/python-311:latest|g' Dockerfile
    
    print_success "✓ Dockerfile updated to use Red Hat registry"
    print_status "Original Dockerfile backed up as Dockerfile.backup"
    
    print_status "Testing Docker build with alternative registry..."
    if docker build -t brain-mvp-test --target development . > /dev/null 2>&1; then
        print_success "✓ Docker build successful with alternative registry!"
        print_status "You can now run: ./scripts/test-docker-setup.sh"
    else
        print_error "✗ Build still failed. Restoring original Dockerfile..."
        mv Dockerfile.backup Dockerfile
        print_status "Please try one of the other solutions above."
    fi
else
    print_status "No changes made. Please try one of the solutions above:"
    echo ""
    echo "Quick commands to try:"
    echo "  docker login                    # Login to Docker Hub"
    echo "  docker system prune -a          # Clean Docker cache"
    echo "  ./scripts/test-docker-setup.sh  # Re-run tests"
    echo ""
fi

print_header "Additional Troubleshooting"

echo "If issues persist, try these steps:"
echo ""
echo "1. Check Docker Desktop status:"
echo "   - Ensure Docker Desktop is running"
echo "   - Check for updates in Docker Desktop"
echo ""
echo "2. Clear Docker cache:"
echo "   docker system prune -a"
echo ""
echo "3. Check network connectivity:"
echo "   ping registry-1.docker.io"
echo ""
echo "4. Use Docker without authentication:"
echo "   - Some base images are available without authentication"
echo "   - Consider using official images from alternative registries"
echo ""

print_status "For more help, see: https://docs.docker.com/docker-hub/access-tokens/"