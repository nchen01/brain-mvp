# Brain MVP - Document Processing System

A production-ready document processing system that extracts text from PDF documents using advanced multi-library processing. Features both a modern web interface and comprehensive REST API for seamless document processing and content retrieval.

## Features

- **Web Interface**: Modern drag-and-drop interface for easy document upload and processing
- **Advanced PDF Processing**: Multi-library approach using PyMuPDF, pdfplumber, and pdfminer with automatic fallbacks
- **Real-time Status Monitoring**: Live progress tracking with visual feedback
- **Multiple Output Formats**: Text, JSON, and Markdown export options
- **Robust Error Handling**: Graceful fallbacks and comprehensive error recovery
- **Document Versioning**: Complete document lineage and version tracking
- **RESTful API**: Full API access for programmatic integration
- **Production Ready**: Docker containerization with all dependencies included

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Web browser (for web interface)
- curl or similar tool (for API testing)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/nchen01/brain-mvp.git
cd brain-mvp
```

2. Start the system:
```bash
docker-compose up -d
```

3. Access the system:
```bash
# Web Interface (Recommended)
open http://localhost:8000

# API Health Check
curl http://localhost:8000/health
# Should return: {"status": "healthy", "version": "1.0.0"}
```

### Using the Web Interface (Easiest Method)

1. **Open your browser**: Navigate to `http://localhost:8000`
2. **Upload PDF**: Drag and drop a PDF file or click "Choose PDF File"
3. **Process**: Click "Process Document" and watch real-time progress
4. **Download Results**: Get extracted content in Text, JSON, or Markdown format

### Using the API (Advanced Users)

#### Upload a Document

```bash
# Upload a PDF file
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@your_document.pdf"

# Response includes document_id for tracking
```

#### Check Processing Status

```bash
# Replace {document_id} with the ID from upload response
curl "http://localhost:8000/api/v1/documents/{document_id}/status"
```

#### Get Extracted Content

```bash
# Get simple text format
curl "http://localhost:8000/api/v1/documents/{document_id}/content?format=text"

# Get detailed JSON with metadata
curl "http://localhost:8000/api/v1/documents/{document_id}/content?format=json"
```

### Testing the System

Run the comprehensive end-to-end test:

```bash
# Inside Docker container
docker-compose exec brain-mvp python final_e2e_test.py

# Or test web interface functionality
docker-compose exec brain-mvp python -c "
import requests
response = requests.get('http://localhost:8000/health')
print('System Status:', response.json())
"
```

## Architecture

### System Components

- **Web Interface** (`web_interface.html`): Modern single-page application for document processing
- **FastAPI Application** (`src/api/`): RESTful API server with comprehensive endpoints
- **Advanced PDF Processor** (`src/docforge/preprocessing/`): Multi-library PDF processing engine
- **Database Layer** (`init_tables.sql`): SQLite database with comprehensive schema
- **Docker Environment**: Containerized deployment with PostgreSQL and Redis support

### Processing Pipeline

1. **Upload**: Document uploaded via web interface or API
2. **Registration**: Document registered with unique UUIDs and metadata
3. **Processing**: Advanced PDF processor extracts text using multiple libraries:
   - **PyMuPDF** (Primary): Fast and accurate text extraction
   - **pdfplumber** (Fallback): Complex layouts and table extraction
   - **pdfminer** (Final fallback): Difficult or corrupted PDFs
4. **Storage**: Extracted content stored in database with full metadata
5. **Retrieval**: Content available via API in multiple formats

### Supported File Types

| Type | Extensions | Processor | Status | Features |
|------|------------|-----------|---------|----------|
| PDF Files | .pdf | AdvancedPDFProcessor | Production Ready | Multi-library processing, table extraction, metadata |
| Text Files | .txt, .md, .rst | TextDocumentProcessor | Available | Basic text processing |

### PDF Processing Capabilities

- **Text Extraction**: Full document text with page breaks
- **Table Detection**: Automatic table identification and extraction
- **Metadata Extraction**: Document properties, page count, processing statistics
- **Multi-page Support**: Handles documents of any size
- **Error Recovery**: Graceful fallbacks between processing libraries
- **Performance Tracking**: Processing time and library usage statistics

## API Documentation

### Interactive Documentation

- **Web Interface**: http://localhost:8000 (Primary user interface)
- **Swagger UI**: http://localhost:8000/docs (API documentation)
- **System Health**: http://localhost:8000/health (Status monitoring)

### Core API Endpoints

- `POST /api/v1/documents/upload` - Upload PDF documents
- `GET /api/v1/documents/{id}/status` - Real-time processing status
- `GET /api/v1/documents/{id}/content` - Extract processed content
  - `?format=text` - Plain text output
  - `?format=json` - Detailed JSON with metadata
  - `?format=markdown` - Markdown formatted output
- `GET /health` - System health and version information

### Response Formats

#### Status Response
```json
{
  "document_id": "abc123-def456-ghi789",
  "status": "completed",
  "progress": 100.0,
  "started_at": "2025-10-29T07:00:00Z",
  "completed_at": "2025-10-29T07:00:05Z"
}
```

#### Content Response (JSON Format)
```json
{
  "document_id": "abc123-def456-ghi789",
  "filename": "document.pdf",
  "extracted_content": {
    "raw_text": "Full document text...",
    "text_length": 1234,
    "estimated_words": 200,
    "estimated_paragraphs": 15
  },
  "metadata": {
    "processing_details": {
      "libraries_used": ["PyMuPDF"],
      "pages_processed": 5,
      "tables_detected": 2,
      "processing_time": 1.23
    }
  }
}
```

## Processing Metrics

The system provides comprehensive processing statistics:

- **Processing Time**: Actual time taken for document processing
- **Libraries Used**: Which PDF processing library was successful
- **Pages Processed**: Total number of pages in the document
- **Tables Detected**: Number of tables found and extracted
- **Text Length**: Character count of extracted content
- **Word Count**: Estimated number of words extracted
- **File Size**: Original document size and processing efficiency

## Project Structure

```
brain_mvp/
├── web_interface.html                    # Modern web interface
├── src/
│   ├── api/                             # FastAPI REST API
│   │   ├── app.py                       # Main application
│   │   └── routers/documents.py         # Document endpoints
│   ├── docforge/preprocessing/          # PDF processing engine
│   │   ├── advanced_pdf_processor.py    # Multi-library PDF processor
│   │   ├── processor_factory.py         # Processor management
│   │   └── schemas.py                   # Data models
│   └── dbm/                            # Database operations
├── init_tables.sql                      # Database schema
├── docker-compose.yml                   # Container orchestration
├── PROJECT_EXPLANATION.md               # Complete technical documentation
├── USAGE_GUIDE.md                      # User and developer guide
└── END_TO_END_TEST_RESULTS.md          # Testing validation
```

### Development and Testing

```bash
# Run comprehensive end-to-end tests
docker-compose exec brain-mvp python final_e2e_test.py

# Test PDF processing directly
docker-compose exec brain-mvp python -c "
from src.docforge.preprocessing.advanced_pdf_processor import AdvancedPDFProcessor
processor = AdvancedPDFProcessor()
print(f'PDF libraries available: {processor.libraries_available}')
"

# Monitor application logs
docker-compose logs -f brain-mvp
```

### Configuration

Current system configuration:

- **Database**: SQLite (development) with PostgreSQL support
- **Web Server**: FastAPI on port 8000
- **PDF Processing**: PyMuPDF, pdfplumber, pdfminer libraries
- **Storage**: Local filesystem with database content storage
- **Containerization**: Docker with multi-service orchestration

## Deployment

### Docker Deployment (Recommended)

The system is fully containerized and production-ready:

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs brain-mvp
```

### Services

- **brain-mvp**: Main application (FastAPI + PDF processing)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache for background tasks (port 6379)

### Environment Configuration

The system works out-of-the-box with sensible defaults. For production:

- **Database**: Configure PostgreSQL connection in docker-compose.yml
- **Storage**: Persistent volumes for data and uploads
- **Scaling**: Add load balancer for multiple application instances
- **Security**: Add authentication and HTTPS termination

## Monitoring and Troubleshooting

### Health Monitoring

```bash
# System health check
curl http://localhost:8000/health

# Web interface accessibility
curl -I http://localhost:8000

# Database connectivity
docker-compose exec postgres psql -U brain_user -d brain_mvp -c "SELECT 1;"
```

### Logs and Debugging

```bash
# Application logs
docker-compose logs brain-mvp

# Real-time log monitoring
docker-compose logs -f brain-mvp

# Check PDF processing logs
docker-compose logs brain-mvp | grep -i "pdf\|processing\|extract"
```

### Common Issues and Solutions

1. **Web Interface Not Loading**
   ```bash
   # Check if containers are running
   docker-compose ps
   
   # Restart if needed
   docker-compose restart brain-mvp
   ```

2. **PDF Processing Fails**
   ```bash
   # Check PDF processing libraries
   docker-compose exec brain-mvp python -c "
   import fitz, pdfplumber
   print('PDF libraries loaded successfully')
   "
   ```

3. **Upload Errors**
   - Ensure PDF file is not corrupted
   - Check file size (recommended under 10MB)
   - Verify file is actually a PDF format

4. **JavaScript Errors in Browser**
   - Clear browser cache and reload
   - Check browser console for specific errors
   - Ensure JavaScript is enabled

### System Reset

```bash
# Complete system reset
docker-compose down
docker-compose up -d

# Check system status
curl http://localhost:8000/health
```

## Documentation

### Complete Documentation

- **PROJECT_EXPLANATION.md**: Complete technical overview and data flow
- **USAGE_GUIDE.md**: Comprehensive user and developer guide
- **END_TO_END_TEST_RESULTS.md**: Testing validation and results
- **API Documentation**: http://localhost:8000/docs (when running)

### Key Features Demonstrated

- Modern web interface with drag-and-drop functionality
- Advanced PDF processing with multiple library fallbacks
- Real-time status monitoring and progress tracking
- Multiple output formats with comprehensive metadata
- Production-ready Docker deployment
- Complete database schema and data management

## Performance

### Typical Processing Times

- **Simple PDFs**: 1-3 seconds
- **Complex PDFs**: 3-10 seconds
- **Large Documents**: Scales with document size and complexity

### Supported Scale

- **File Size**: Tested up to 50MB PDFs
- **Concurrent Processing**: Multiple simultaneous uploads
- **Storage**: SQLite for development, PostgreSQL for production

## Contributing

1. Fork the repository
2. Create a feature branch (no emojis in commit messages)
3. Follow the existing code style and documentation standards
4. Add tests for new functionality
5. Submit a pull request with clear description

## License

This project is licensed under the MIT License.

## Support

The Brain MVP is a complete, working document processing system. For support:

1. **Check Documentation**: Review PROJECT_EXPLANATION.md and USAGE_GUIDE.md
2. **Run Tests**: Execute final_e2e_test.py to verify functionality
3. **Check Logs**: Use docker-compose logs for debugging
4. **Web Interface**: Use http://localhost:8000 for easy document processing
5. **API Access**: Use http://localhost:8000/docs for programmatic integration

The system is production-ready and provides comprehensive PDF processing capabilities with both user-friendly web interface and developer-friendly API access.