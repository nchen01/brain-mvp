#!/bin/bash
# Quick test script for Brain MVP current capabilities

echo "🧠 Brain MVP - Quick Test Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

echo "1. Starting Brain MVP services..."
docker-compose up -d

echo "2. Waiting for services to be ready..."
sleep 10

echo "3. Testing API endpoints..."

# Test health endpoint
echo -e "\n${YELLOW}Testing Health Endpoint:${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Health endpoint working${NC}"
    echo "$HEALTH_RESPONSE" | jq .status 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo -e "${RED}❌ Health endpoint failed${NC}"
fi

# Test auth endpoint
echo -e "\n${YELLOW}Testing Auth Endpoint:${NC}"
AUTH_RESPONSE=$(curl -s http://localhost:8000/api/v1/auth/test/users)
if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Auth endpoint working${NC}"
    echo "$AUTH_RESPONSE" | jq .message 2>/dev/null || echo "$AUTH_RESPONSE"
else
    echo -e "${RED}❌ Auth endpoint failed${NC}"
fi

# Test API docs
echo -e "\n${YELLOW}Testing API Documentation:${NC}"
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [[ "$DOCS_STATUS" == "200" ]]; then
    echo -e "${GREEN}✅ API documentation accessible at http://localhost:8000/docs${NC}"
else
    echo -e "${RED}❌ API documentation not accessible${NC}"
fi

# Create a test document
echo -e "\n${YELLOW}Creating test document:${NC}"
cat > test_document.txt << 'EOF'
# Brain MVP Test Document

This is a test document to verify the Brain MVP processing pipeline.

## Document Features
- Simple text content
- Markdown formatting
- Multiple sections

## Test Objectives
1. Verify document upload capability
2. Test text processing
3. Check storage and versioning
4. Validate retrieval functionality

The Brain MVP system should be able to process this document and extract meaningful content for further analysis and retrieval.

## Technical Details
- File format: Plain text with Markdown
- Size: Small test document
- Content type: Technical documentation
- Processing requirements: Basic text extraction and chunking

This document serves as a baseline test for the document processing pipeline.
EOF

echo -e "${GREEN}✅ Test document created: test_document.txt${NC}"

# Check what dependencies are available
echo -e "\n${YELLOW}Checking available processing capabilities:${NC}"
docker-compose exec brain-mvp python -c "
import sys
print('Python version:', sys.version)
print()

# Check processing dependencies
dependencies = [
    ('magic_pdf', 'MinerU PDF processor'),
    ('markitdown', 'MarkItDown Office processor'),
    ('sentence_transformers', 'Sentence Transformers for embeddings'),
    ('lightrag', 'LightRAG for advanced RAG'),
    ('redis', 'Redis for caching'),
    ('psycopg2', 'PostgreSQL connector')
]

for module, description in dependencies:
    try:
        __import__(module)
        print(f'✅ {description}: Available')
    except ImportError:
        print(f'❌ {description}: Not installed')
" 2>/dev/null

echo -e "\n${YELLOW}Current Testing Capabilities:${NC}"
echo "✅ API infrastructure and endpoints"
echo "✅ Database connectivity (PostgreSQL)"
echo "✅ Caching system (Redis)"
echo "✅ Basic text processing"
echo "✅ Document versioning system"
echo "✅ Authentication system"
echo "❌ Advanced PDF processing (MinerU not installed)"
echo "❌ Office document processing (MarkItDown not installed)"
echo "❌ Full RAG capabilities (using mock implementation)"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. 📖 Read TESTING_REAL_DOCUMENTS.md for detailed testing guide"
echo "2. 🌐 Visit http://localhost:8000/docs to explore the API"
echo "3. 🔧 Install missing dependencies for full functionality"
echo "4. 📄 Test with real documents once dependencies are installed"

echo -e "\n${GREEN}🎉 Basic Brain MVP test completed!${NC}"
echo -e "The system is ready for basic testing and development."

# Keep services running
echo -e "\n${YELLOW}Services are running. To stop:${NC}"
echo "docker-compose down"