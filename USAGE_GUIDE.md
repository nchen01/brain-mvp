# Brain MVP Usage Guide

## 🌐 Web Interface (Easiest Method)

### 1. Start the System & Open Web Interface
```bash
# Start all services
docker-compose up -d

# Open your web browser and go to:
http://localhost:8080
```

### 2. Using the Web Interface
1. **Upload**: Drag and drop a PDF file or click "Choose PDF File"
2. **Process**: Click "Process Document" button
3. **Monitor**: Watch the real-time processing status
4. **Download**: Get results in Text, JSON, or Markdown format

**Features:**
- ✅ **Drag & Drop Upload** - Simply drag PDF files onto the page
- ✅ **Real-time Status** - Live progress monitoring with visual progress bar
- ✅ **Instant Preview** - See extracted content immediately
- ✅ **Multiple Formats** - Download as Text, JSON, or Markdown
- ✅ **File Metadata** - View processing details, word count, page count
- ✅ **Error Handling** - Clear error messages and troubleshooting

---

## 🚀 Command Line Interface (Advanced Users)

### Prerequisites
- Docker and Docker Compose installed
- Terminal/Command line access
- PDF documents to process

### 1. Start the System
```bash
# Clone the repository and navigate to it
cd brain_mvp

# Start all services
docker-compose up -d

# Verify system is running
curl http://localhost:8080/health
# Expected: {"status":"healthy","version":"1.0.0"...}
```

### 2. Upload Your First Document
```bash
# Upload a PDF file
curl -X POST -F "file=@your_document.pdf" \
  http://localhost:8080/api/v1/documents/upload

# Save the document_id from the response
```

### 3. Check Processing Status
```bash
# Replace {document_id} with your actual document ID
curl http://localhost:8080/api/v1/documents/{document_id}/status
```

### 4. Get Extracted Content
```bash
# Get simple text format
curl "http://localhost:8080/api/v1/documents/{document_id}/content?format=text"

# Get detailed JSON with metadata
curl "http://localhost:8080/api/v1/documents/{document_id}/content?format=json"
```

## 📋 Complete API Reference

### Document Upload
**Endpoint**: `POST /api/v1/documents/upload`

**Request**:
```bash
curl -X POST \
  -F "file=@document.pdf" \
  http://localhost:8080/api/v1/documents/upload
```

**Response**:
```json
{
  "document_id": "abc123-def456-ghi789",
  "lineage_id": "abc123-def456-ghi789",
  "version_number": 1,
  "filename": "document.pdf",
  "file_size": 12345,
  "content_hash": "sha256hash...",
  "upload_timestamp": "2025-10-28T23:30:00.123456",
  "processing_status": "pending",
  "processing_queue_id": "queue123-456"
}
```

### Processing Status
**Endpoint**: `GET /api/v1/documents/{document_id}/status`

**Response**:
```json
{
  "document_id": "abc123-def456-ghi789",
  "status": "completed",
  "stage": "completed",
  "progress": 100.0,
  "started_at": "2025-10-28T23:30:00.123456",
  "completed_at": "2025-10-28T23:30:05.654321",
  "error_message": null,
  "processing_details": {}
}
```

**Status Values**:
- `pending` - Queued for processing
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed

### Content Retrieval
**Endpoint**: `GET /api/v1/documents/{document_id}/content`

**Parameters**:
- `format`: `text`, `json`, or `markdown`

#### Text Format Response
```json
{
  "document_id": "abc123...",
  "filename": "document.pdf",
  "content_available": true,
  "extracted_text": "Full document text content here...",
  "text_length": 1234,
  "message": "Extracted 1234 characters from 'document.pdf'"
}
```

#### JSON Format Response
```json
{
  "document_id": "abc123...",
  "filename": "document.pdf",
  "file_size": 12345,
  "content_available": true,
  "extraction_timestamp": "2025-10-28T23:30:05.123456",
  "extracted_content": {
    "raw_text": "Full document text...",
    "text_length": 1234,
    "estimated_words": 200,
    "estimated_paragraphs": 15,
    "extraction_method": "Brain MVP Processing Pipeline",
    "status": "Content available"
  },
  "metadata": {
    "processing_details": {
      "started_at": "2025-10-28T23:30:00.123456",
      "completed_at": "2025-10-28T23:30:05.654321",
      "progress": 100,
      "stage": "completed",
      "libraries_used": ["PyMuPDF"],
      "pages_processed": 5,
      "tables_detected": 2
    },
    "file_info": {
      "original_filename": "document.pdf",
      "file_size_bytes": 12345,
      "processing_queue_id": "queue123-456"
    }
  }
}
```

## 🔧 Advanced Usage

### Batch Processing
```bash
#!/bin/bash
# Process multiple PDFs in a directory

for pdf_file in *.pdf; do
    echo "Processing: $pdf_file"
    
    # Upload document
    response=$(curl -s -X POST -F "file=@$pdf_file" \
        http://localhost:8080/api/v1/documents/upload)
    
    # Extract document ID
    doc_id=$(echo $response | jq -r '.document_id')
    echo "Document ID: $doc_id"
    
    # Wait for processing
    while true; do
        status=$(curl -s "http://localhost:8080/api/v1/documents/$doc_id/status" | jq -r '.status')
        echo "Status: $status"
        
        if [ "$status" = "completed" ]; then
            echo "✅ Processing completed for $pdf_file"
            break
        elif [ "$status" = "failed" ]; then
            echo "❌ Processing failed for $pdf_file"
            break
        fi
        
        sleep 2
    done
    
    # Get extracted content
    curl -s "http://localhost:8080/api/v1/documents/$doc_id/content?format=text" \
        | jq -r '.extracted_text' > "${pdf_file%.pdf}_extracted.txt"
    
    echo "Content saved to ${pdf_file%.pdf}_extracted.txt"
    echo "---"
done
```

### Python Integration
```python
import requests
import time
import json

class BrainMVPClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def upload_document(self, file_path):
        """Upload a document for processing."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.base_url}/api/v1/documents/upload", files=files)
        return response.json()
    
    def get_status(self, document_id):
        """Get processing status."""
        response = requests.get(f"{self.base_url}/api/v1/documents/{document_id}/status")
        return response.json()
    
    def wait_for_completion(self, document_id, timeout=60):
        """Wait for processing to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status(document_id)
            if status['status'] in ['completed', 'failed']:
                return status
            time.sleep(2)
        raise TimeoutError("Processing timeout")
    
    def get_content(self, document_id, format='json'):
        """Get extracted content."""
        response = requests.get(f"{self.base_url}/api/v1/documents/{document_id}/content?format={format}")
        return response.json()
    
    def process_document(self, file_path):
        """Complete workflow: upload, wait, and get content."""
        # Upload
        upload_result = self.upload_document(file_path)
        document_id = upload_result['document_id']
        
        # Wait for completion
        status = self.wait_for_completion(document_id)
        
        if status['status'] == 'completed':
            # Get content
            return self.get_content(document_id)
        else:
            raise Exception(f"Processing failed: {status.get('error_message', 'Unknown error')}")

# Usage example
client = BrainMVPClient()
result = client.process_document("my_document.pdf")
print(f"Extracted text: {result['extracted_content']['raw_text']}")
```

## 🛠️ System Management

### Health Monitoring
```bash
# Check system health
curl http://localhost:8080/health

# Check all Docker services
docker-compose ps

# View application logs
docker-compose logs brain-mvp

# View all service logs
docker-compose logs
```

### Database Access
```bash
# Connect to PostgreSQL database
docker-compose exec postgres psql -U brain_user -d brain_mvp

# View processed documents
docker-compose exec postgres psql -U brain_user -d brain_mvp \
  -c "SELECT doc_uuid, filename, file_size FROM raw_document_register LIMIT 10;"
```

### Redis Cache
```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# View background tasks
docker-compose exec redis redis-cli keys "*"
```

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check Docker status
docker --version
docker-compose --version

# Check port conflicts
netstat -tulpn | grep :8000
netstat -tulpn | grep :5432
netstat -tulpn | grep :6379

# Restart services
docker-compose down
docker-compose up -d
```

#### Processing Stuck
```bash
# Check background worker logs
docker-compose logs brain-mvp | grep -i "processing\|error"

# Restart the application
docker-compose restart brain-mvp
```

#### No Content Extracted
- **Scanned PDFs**: The system doesn't include OCR - scanned images won't extract text
- **Encrypted PDFs**: Password-protected PDFs aren't supported
- **Corrupted Files**: Check if the PDF opens normally in a PDF viewer

#### Upload Failures
```bash
# Check file size (default limit is usually 10MB)
ls -lh your_document.pdf

# Check file format
file your_document.pdf
# Should show: PDF document, version X.X
```

### Log Analysis
```bash
# Real-time log monitoring
docker-compose logs -f brain-mvp

# Search for specific errors
docker-compose logs brain-mvp | grep -i "error\|exception\|failed"

# Check processing pipeline
docker-compose logs brain-mvp | grep -i "processing\|pdf\|extract"
```

## 📊 Performance Guidelines

### File Size Limits
- **Recommended**: Under 10MB per PDF
- **Maximum**: Depends on available memory (tested up to 50MB)
- **Processing Time**: 1-10 seconds for typical documents

### Concurrent Processing
- **Uploads**: Multiple simultaneous uploads supported
- **Processing**: Background queue handles multiple documents
- **API Calls**: RESTful API supports concurrent requests

### Storage Requirements
- **Database**: ~1KB per document metadata + extracted text size
- **Temporary Files**: Cleaned up automatically after processing
- **Docker Images**: ~2GB total for all services

## 🔄 Development Mode

### Live Development
```bash
# Start with file watching (for development)
docker-compose up brain-mvp

# Make code changes and the server will reload automatically
```

### Testing
```bash
# Run integration tests
docker-compose exec brain-mvp python -m pytest tests/

# Run end-to-end tests
docker-compose exec brain-mvp python tests/final_e2e_test.py

# Test specific PDF processing
docker-compose exec brain-mvp python -c "
from src.docforge.preprocessing.advanced_pdf_processor import AdvancedPDFProcessor
processor = AdvancedPDFProcessor()
print(f'Libraries available: {processor.libraries_available}')
"
```

## 🚀 Production Deployment

### Environment Variables
```bash
# Set in docker-compose.yml or .env file
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
LOG_LEVEL=INFO
MAX_FILE_SIZE=10485760  # 10MB in bytes
```

### Security Considerations
- Add authentication/authorization
- Implement rate limiting
- Use HTTPS in production
- Secure database credentials
- Regular security updates

### Scaling
- Use PostgreSQL instead of SQLite for production
- Add load balancer for multiple API instances
- Implement Redis clustering for high availability
- Monitor resource usage and scale accordingly

---

**Need help?** Check the logs, review this guide, or examine the test files for working examples! 🎉