# Testing Brain MVP with Real Documents

## Current Status Assessment

### ✅ What's Working
- **Docker Environment**: Fully functional with PostgreSQL, Redis, and API
- **API Infrastructure**: All endpoints working (auth, health, monitoring)
- **Database**: Document versioning and storage systems implemented
- **Basic Processing**: Text processing capabilities available
- **Sentence Transformers**: Installed for embeddings

### ❌ What's Missing for Full Document Processing
- **MinerU (magic-pdf)**: Not installed - required for advanced PDF processing
- **MarkItDown**: Not installed - required for Office document processing
- **LightRAG**: Using mock implementation - full RAG capabilities limited

## Testing Options

### Option 1: Quick Test with Current Setup (Text Documents)

**What you can test now:**
- Document upload and versioning
- Basic text processing
- Storage and retrieval
- API functionality

**Steps:**
1. Start the environment:
   ```bash
   docker-compose up -d
   ```

2. Test with simple text files:
   ```bash
   # Create a test text file
   echo "This is a test document for Brain MVP processing." > test_document.txt
   
   # Upload via API (you'll need to implement the upload endpoint test)
   curl -X POST http://localhost:8000/api/v1/documents/upload \
     -F "file=@test_document.txt" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. Check the API documentation:
   ```bash
   open http://localhost:8000/docs
   ```

### Option 2: Install Missing Dependencies for Full Testing

**To get full document processing capabilities:**

1. **Install MinerU in Docker container:**
   ```bash
   # Add to requirements-docker.txt
   magic-pdf>=0.7.0
   
   # Rebuild Docker image
   docker-compose build --no-cache
   ```

2. **Install MarkItDown:**
   ```bash
   # Add to requirements-docker.txt  
   markitdown>=0.0.1a2
   
   # Rebuild Docker image
   docker-compose build --no-cache
   ```

### Option 3: Local Development Setup (Recommended for Full Testing)

**For complete functionality with all dependencies:**

1. **Set up local Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install magic-pdf>=0.7.0
   pip install markitdown>=0.0.1a2
   ```

3. **Start services locally:**
   ```bash
   # Start PostgreSQL and Redis via Docker
   docker-compose up postgres redis -d
   
   # Run the application locally
   python src/main.py
   ```

## Step-by-Step Testing Guide

### Phase 1: Basic API Testing (Current Capabilities)

1. **Start the environment:**
   ```bash
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test authentication:**
   ```bash
   curl http://localhost:8000/api/v1/auth/test/users
   ```

4. **Access API documentation:**
   ```bash
   open http://localhost:8000/docs
   ```

### Phase 2: Document Upload Testing (Limited)

**Current limitations:**
- Only basic text processing available
- PDF processing will use fallback methods
- No advanced table/image extraction

**Test files you can try:**
- `.txt` files (full support)
- `.pdf` files (basic text extraction only)
- `.docx` files (limited support)

### Phase 3: Full Document Processing (After Installing Dependencies)

**Once MinerU and MarkItDown are installed:**

1. **Test PDF processing:**
   - Upload complex PDFs with tables and images
   - Verify table extraction
   - Check image extraction
   - Test OCR capabilities

2. **Test Office documents:**
   - Upload .docx, .pptx, .xlsx files
   - Verify formatting preservation
   - Test metadata extraction

3. **Test RAG pipeline:**
   - Upload multiple documents
   - Test document chunking
   - Verify embedding generation
   - Test retrieval functionality

## Recommended Testing Approach

### Immediate Testing (Today)
1. **Use Option 1** to test the API infrastructure and basic functionality
2. Test with simple text files to verify the pipeline works
3. Explore the API documentation at `/docs`

### Full Testing (Next Steps)
1. **Install missing dependencies** using Option 2 or 3
2. Test with real PDF documents containing tables and images
3. Test with Office documents (.docx, .pptx, .xlsx)
4. Test the complete RAG pipeline with multiple documents

## Sample Test Documents

Create these test files to verify functionality:

### Simple Text File
```bash
cat > sample.txt << 'EOF'
# Sample Document

This is a test document for the Brain MVP system.

## Features to Test
- Document upload
- Text processing
- Versioning
- Storage and retrieval

The system should be able to process this document and extract meaningful content.
EOF
```

### Sample API Test Script
```bash
#!/bin/bash
# test_document_upload.sh

echo "Testing Brain MVP Document Processing..."

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq .

# Test auth
echo "2. Testing authentication..."
curl -s http://localhost:8000/api/v1/auth/test/users | jq .

# Test document upload (when endpoint is available)
echo "3. Testing document upload..."
# curl -X POST http://localhost:8000/api/v1/documents/upload \
#   -F "file=@sample.txt" \
#   -H "Content-Type: multipart/form-data"

echo "Testing complete!"
```

## Next Steps for Full Functionality

1. **Install MinerU**: Add `magic-pdf>=0.7.0` to requirements
2. **Install MarkItDown**: Add `markitdown>=0.0.1a2` to requirements  
3. **Implement LightRAG**: Replace mock implementation with real LightRAG
4. **Test with real documents**: PDFs with tables, images, complex layouts
5. **Performance testing**: Large documents, multiple concurrent uploads

## Current MVP Limitations

- **PDF Processing**: Basic text extraction only (no tables/images)
- **Office Documents**: Limited support without MarkItDown
- **RAG Capabilities**: Mock implementation only
- **Performance**: Not optimized for large documents

The infrastructure is solid and ready - we just need to install the processing dependencies for full functionality!