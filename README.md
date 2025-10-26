# Brain MVP - Document Processing System

A comprehensive document processing system that extracts, processes, and prepares documents for RAG (Retrieval Augmented Generation) applications.

## Features

- **Document Upload**: Support for text files (.txt, .md, .rst) and PDFs
- **Multi-stage Processing**: Raw storage, preprocessing, and postprocessing
- **Text Extraction**: High-accuracy text extraction with confidence metrics
- **RAG Preparation**: Document chunking and abbreviation expansion
- **Quality Metrics**: Confidence and completeness scoring
- **Multiple Output Formats**: Text, markdown, JSON, and structured chunks
- **Version Management**: Document versioning and lineage tracking
- **RESTful API**: Complete API for document operations

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for testing scripts)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd brain_mvp
```

2. Start the system:
```bash
docker-compose up -d
```

3. Verify the system is running:
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

### Basic Usage

#### Upload a Document

```bash
# Upload a text file
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@your_document.txt"

# Upload a PDF file
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@your_document.pdf"
```

#### Check Processing Status

```bash
# Replace YOUR_DOCUMENT_ID with the ID from upload response
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/status" | jq
```

#### Get Extraction Results

```bash
# Get all processing stages and quality metrics
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/processed" | jq
```

### Automated Testing

Run the complete end-to-end test:

```bash
python run_complete_test.py
```

## Architecture

### Core Components

- **API Layer** (`src/api/`): FastAPI-based REST API
- **Document Processing** (`src/docforge/`): Multi-stage document processing pipeline
- **Preprocessing** (`src/docforge/preprocessing/`): Text extraction and format conversion
- **Postprocessing** (`src/docforge/postprocessing/`): Chunking and enhancement
- **Storage** (`src/docforge/storage/`): Document storage and metadata management
- **Versioning** (`src/docforge/versioning/`): Document version control
- **Database** (`src/dbm/`): Database operations and management

### Processing Pipeline

1. **Raw Stage**: Original document storage and validation
2. **Preprocessing Stage**: Text extraction with quality metrics
3. **Postprocessing Stage**: Chunking and abbreviation expansion for RAG

### Supported File Types

| Type | Extensions | Processor | Status |
|------|------------|-----------|---------|
| Text Files | .txt, .md, .rst | TextDocumentProcessor | Fully Supported |
| PDF Files | .pdf | MinerU (Advanced) | Fully Supported |
| Word Documents | .docx, .doc | MarkItDown | Available |
| Excel Files | .xlsx, .xls, .csv | MarkItDown | Available |
| PowerPoint | .pptx, .ppt | MarkItDown | Available |

## API Documentation

Once the system is running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/documents/upload` - Upload documents
- `GET /api/v1/documents/{id}/status` - Check processing status
- `GET /api/v1/documents/{id}/processed` - Get extraction results
- `GET /api/v1/documents/{id}/versions` - Get document versions
- `GET /health` - System health check

## Quality Metrics

The system provides comprehensive quality metrics:

- **Confidence Score**: 0.0-1.0 (extraction accuracy confidence)
- **Completeness Score**: 0.0-1.0 (percentage of content extracted)
- **Chunk Count**: Number of chunks created for RAG
- **Abbreviations Expanded**: Count of technical terms expanded

## Development

### Project Structure

```
brain_mvp/
├── src/
│   ├── api/                 # REST API implementation
│   ├── docforge/           # Document processing pipeline
│   ├── accountmatrix/      # Authentication system
│   ├── dbm/               # Database management
│   ├── core/              # Core models and interfaces
│   └── utils/             # Utility functions
├── tests/                 # Test suites
├── scripts/              # Deployment and utility scripts
├── docs/                 # Documentation
└── docker-compose.yml    # Container orchestration
```

### Running Tests

```bash
# Run the complete test suite
python run_complete_test.py

# Run specific functionality tests
python working_content_demo.py
python quick_test.py
```

### Configuration

The system uses environment-based configuration. Key settings:

- **Database**: SQLite (default) or PostgreSQL
- **Storage**: Local filesystem or cloud storage
- **Processing**: Configurable processor selection
- **API**: Port and host configuration

## Deployment

### Docker Deployment

The system is containerized and ready for deployment:

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Development deployment
docker-compose up -d
```

### Environment Variables

- `DATABASE_URL`: Database connection string
- `STORAGE_PATH`: Document storage location
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)

## Monitoring

### Health Checks

```bash
# System health
curl http://localhost:8000/health

# Processing queue status
curl http://localhost:8000/api/v1/documents/processing/queue
```

### Logs

```bash
# View application logs
docker-compose logs brain-mvp

# Follow logs in real-time
docker-compose logs -f brain-mvp
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure Docker containers are running
2. **Upload Failures**: Check file size and format support
3. **Processing Stuck**: Monitor logs and restart if needed
4. **Low Quality Scores**: Review source document quality

### Support Commands

```bash
# Check container status
docker-compose ps

# Restart services
docker-compose restart

# View detailed logs
docker-compose logs brain-mvp

# Reset system
docker-compose down && docker-compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation
- Run the automated tests to verify functionality
- Check the logs for detailed error information