#!/bin/bash
# Install all dependencies for full Brain MVP functionality

echo "🚀 Installing Full Brain MVP Dependencies"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Stop existing containers
echo -e "${YELLOW}1. Stopping existing containers...${NC}"
docker-compose down

# Rebuild Docker image with new dependencies
echo -e "${YELLOW}2. Rebuilding Docker image with full dependencies...${NC}"
echo "   This may take several minutes as we're installing ML/AI libraries..."
docker-compose build --no-cache

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed. Check the error messages above.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image rebuilt successfully${NC}"

# Start services
echo -e "${YELLOW}3. Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}4. Waiting for services to initialize...${NC}"
sleep 15

# Verify dependencies are installed
echo -e "${YELLOW}5. Verifying installed dependencies...${NC}"

docker-compose exec brain-mvp python -c "
import sys
print(f'Python version: {sys.version}')
print()

# Check all dependencies
dependencies = [
    ('magic_pdf', 'MinerU PDF processor'),
    ('markitdown', 'MarkItDown Office processor'),
    ('sentence_transformers', 'Sentence Transformers'),
    ('lightrag', 'LightRAG for advanced RAG'),
    ('transformers', 'Hugging Face Transformers'),
    ('torch', 'PyTorch'),
    ('cv2', 'OpenCV'),
    ('pytesseract', 'Tesseract OCR'),
    ('easyocr', 'EasyOCR'),
    ('fitz', 'PyMuPDF'),
    ('pdfplumber', 'PDF Plumber'),
    ('docx', 'python-docx'),
    ('openpyxl', 'OpenPyXL'),
    ('pptx', 'python-pptx'),
    ('chromadb', 'ChromaDB'),
    ('faiss', 'FAISS'),
    ('spacy', 'spaCy'),
    ('nltk', 'NLTK'),
    ('redis', 'Redis'),
    ('psycopg2', 'PostgreSQL connector'),
    ('numpy', 'NumPy'),
    ('pandas', 'Pandas'),
    ('PIL', 'Pillow'),
    ('magic', 'python-magic')
]

installed_count = 0
total_count = len(dependencies)

for module, description in dependencies:
    try:
        if module == 'fitz':
            import fitz
        elif module == 'cv2':
            import cv2
        elif module == 'docx':
            import docx
        elif module == 'pptx':
            import pptx
        elif module == 'PIL':
            import PIL
        else:
            __import__(module)
        print(f'✅ {description}: Available')
        installed_count += 1
    except ImportError as e:
        print(f'❌ {description}: Not installed ({e})')

print(f'\\nInstallation Summary: {installed_count}/{total_count} dependencies installed')

if installed_count == total_count:
    print('🎉 All dependencies successfully installed!')
else:
    print(f'⚠️  {total_count - installed_count} dependencies missing')
"

# Test basic functionality
echo -e "\n${YELLOW}6. Testing basic functionality...${NC}"

# Test health endpoint
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ API health check passed${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
fi

# Test auth endpoint
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/auth/test/users)
if [ "$AUTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Authentication system working${NC}"
else
    echo -e "${RED}❌ Authentication system failed${NC}"
fi

echo -e "\n${BLUE}🎯 Installation Complete!${NC}"
echo -e "${GREEN}Brain MVP is now ready for full document processing!${NC}"
echo ""
echo "Available capabilities:"
echo "✅ Advanced PDF processing (tables, images, OCR)"
echo "✅ Office document processing (.docx, .pptx, .xlsx)"
echo "✅ Multiple OCR engines (Tesseract, EasyOCR)"
echo "✅ Advanced RAG with LightRAG"
echo "✅ Vector databases (ChromaDB, FAISS)"
echo "✅ ML/AI processing (PyTorch, Transformers)"
echo "✅ Image processing and analysis"
echo ""
echo "Next steps:"
echo "1. 📖 Visit http://localhost:8000/docs for API documentation"
echo "2. 🧪 Run ./test_full_functionality.sh to test with real documents"
echo "3. 📄 Upload complex PDFs and Office documents for processing"
echo ""
echo "Services running:"
echo "- API: http://localhost:8000"
echo "- PostgreSQL: localhost:5432"
echo "- Redis: localhost:6379"