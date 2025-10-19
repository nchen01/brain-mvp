# Brain MVP - Intelligent Document Processing System

## Overview

Brain MVP is an AI-powered document processing and retrieval system that transforms your documents into a searchable, intelligent knowledge base. Upload documents in various formats (PDF, Excel, PowerPoint, etc.) and get them processed, enhanced, and prepared for intelligent querying.

## Features

### 🔄 Document Processing Pipeline
- **Multi-format Support**: PDF (via MinerU), Excel, PowerPoint, and more (via MarkItDown)
- **Intelligent Routing**: Automatic processor selection based on file type
- **Standardized Output**: Consistent format regardless of input document type
- **Duplicate Detection**: Prevents processing of duplicate documents

### 📝 Post-Processing Enhancement
- **Smart Chunking**: Multiple strategies (paragraph, section, sentence, topic-based)
- **Abbreviation Expansion**: Automatically expands abbreviations with context
- **Content Normalization**: Standardizes formatting and structure
- **Metadata Enrichment**: Adds contextual information and tags

### 🔍 RAG-Ready Preparation
- **LightRAG Integration**: Optimized for retrieval-augmented generation
- **Vector Embeddings**: Semantic search capabilities
- **Knowledge Graph**: Document relationships and context mapping
- **Efficient Indexing**: Fast retrieval and search operations

### 🚀 REST API
- **Document Upload**: Simple file upload with processing status tracking
- **Processing Status**: Real-time status updates and progress monitoring
- **Document Retrieval**: Access processed documents at any stage
- **Search Endpoints**: RAG-powered document search and retrieval

## Quick Start

### Prerequisites
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- PostgreSQL database
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd brain-mvp
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**
   ```bash
   uv run scripts/migrate_db.py
   ```

5. **Start the application**
   ```bash
   uv run src/main.py
   ```

The API will be available at `http://localhost:8000`

### Docker Setup (Alternative)

```bash
# Start all services with Docker
docker-compose up --build

# The API will be available at http://localhost:8000
```

## Usage

### 1. Upload a Document

**Endpoint**: `POST /api/documents/upload`

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf" \
  -F "labels=research,important"
```

**Response**:
```json
{
  "doc_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "your-document.pdf",
  "status": "uploaded",
  "processing_started": true
}
```

### 2. Check Processing Status

**Endpoint**: `GET /api/processing/status/{doc_uuid}`

```bash
curl "http://localhost:8000/api/processing/status/123e4567-e89b-12d3-a456-426614174000"
```

**Response**:
```json
{
  "doc_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "processing_stage": "rag_preparation",
  "progress": 100,
  "stages": {
    "registration": "completed",
    "processing": "completed",
    "post_processing": "completed",
    "rag_preparation": "completed"
  }
}
```

### 3. Retrieve Processed Document

**Endpoint**: `GET /api/documents/{doc_uuid}`

```bash
curl "http://localhost:8000/api/documents/123e4567-e89b-12d3-a456-426614174000"
```

**Response**:
```json
{
  "doc_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "content": "Processed document content...",
  "metadata": {
    "filename": "your-document.pdf",
    "file_type": "pdf",
    "processing_method": "mineru_pdf",
    "chunking_strategy": "paragraph",
    "abbreviations_expanded": 15
  },
  "extracted_elements": [
    {
      "type": "table",
      "content": "...",
      "page": 1
    }
  ]
}
```

### 4. Get Document Version History

**Endpoint**: `GET /api/documents/lineage/{lineage_uuid}/versions`

```bash
curl "http://localhost:8000/api/documents/lineage/abc12345-def6-7890-ghij-klmnopqrstuv/versions"
```

**Response**:
```json
{
  "lineage_uuid": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "original_filename": "research-paper.pdf",
  "total_versions": 3,
  "current_version": 3,
  "versions": [
    {
      "doc_uuid": "123e4567-e89b-12d3-a456-426614174000",
      "version_number": 1,
      "filename": "research-paper.pdf",
      "timestamp": "2024-01-15T10:30:00Z",
      "is_current": false,
      "is_deleted": false
    },
    {
      "doc_uuid": "234f5678-f90c-23e4-b567-537725285111",
      "version_number": 2,
      "filename": "research-paper-updated.pdf",
      "timestamp": "2024-01-16T14:20:00Z",
      "is_current": false,
      "is_deleted": true,
      "deletion_reason": "privacy_request"
    },
    {
      "doc_uuid": "345g6789-g01d-34f5-c678-648836396222",
      "version_number": 3,
      "filename": "research-paper-final.pdf",
      "timestamp": "2024-01-17T09:15:00Z",
      "is_current": true,
      "is_deleted": false
    }
  ]
}
```

### 5. Edit Old Version (Create Branch)

**Endpoint**: `POST /api/documents/edit-version`

```bash
curl -X POST "http://localhost:8000/api/documents/edit-version" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@updated-document.pdf" \
  -F "lineage_uuid=abc12345-def6-7890-ghij-klmnopqrstuv" \
  -F "edit_source_version=1"
```

### 6. Soft Delete Version

**Endpoint**: `DELETE /api/documents/{doc_uuid}`

```bash
curl -X DELETE "http://localhost:8000/api/documents/123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -d '{"reason": "privacy_request"}'
```

### 7. Search Documents (RAG)

**Endpoint**: `POST /api/search/query`

```bash
curl -X POST "http://localhost:8000/api/search/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings about AI in the research?",
    "max_results": 5,
    "include_context": true,
    "include_deleted": false
  }'
```

**Response**:
```json
{
  "query": "What are the main findings about AI in the research?",
  "results": [
    {
      "doc_uuid": "123e4567-e89b-12d3-a456-426614174000",
      "lineage_uuid": "abc12345-def6-7890-ghij-klmnopqrstuv",
      "version_number": 3,
      "relevance_score": 0.95,
      "content": "The research shows that AI technologies...",
      "context": "This finding was mentioned in the context of...",
      "metadata": {
        "filename": "research-paper-final.pdf",
        "page": 3,
        "section": "Results"
      }
    }
  ],
  "total_results": 1,
  "processing_time": 0.234
}
```

## API Documentation

### Authentication
Currently using basic authentication (dummy implementation for MVP):

```bash
# Include in headers for authenticated requests
Authorization: Bearer your-session-token
```

### Document Upload Formats Supported
- **PDF**: Processed using MinerU for advanced text and structure extraction
- **Excel (.xlsx, .xls)**: Processed using MarkItDown
- **PowerPoint (.pptx, .ppt)**: Processed using MarkItDown
- **Word (.docx, .doc)**: Processed using MarkItDown
- **Text files (.txt, .md)**: Processed using MarkItDown

### Processing Stages
1. **Registration**: Document upload and metadata extraction
2. **Processing**: Content extraction using appropriate processor
3. **Post-processing**: Chunking, abbreviation expansion, normalization
4. **RAG Preparation**: Vector embedding and indexing with LightRAG

### Error Handling
All API endpoints return consistent error responses:

```json
{
  "error": {
    "code": "PROCESSING_FAILED",
    "message": "Document processing failed due to corrupted file",
    "details": {
      "doc_uuid": "123e4567-e89b-12d3-a456-426614174000",
      "stage": "processing",
      "processor": "mineru_pdf"
    }
  }
}
```

## Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/brain_mvp
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-secret-key-here

# File Processing
MAX_FILE_SIZE=100MB
PROCESSING_TIMEOUT=300
SUPPORTED_FORMATS=pdf,xlsx,xls,pptx,ppt,docx,doc,txt,md

# LightRAG Configuration
LIGHTRAG_INDEX_PATH=./data/rag_index
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log
ENABLE_PROMPT_LOGGING=true
```

### Chunking Strategies

Configure document chunking strategy per document type:

- **paragraph**: Split by paragraphs (default for most documents)
- **section**: Split by document sections (good for structured documents)
- **sentence**: Split by sentences (good for detailed analysis)
- **topic**: Split by semantic topics (AI-powered, slower but more intelligent)

## Monitoring and Logs

### Log Files
- **Application Logs**: `logs/app.log` - General application activity
- **Processing Logs**: `logs/processing.log` - Document processing details
- **Prompt History**: `logs/prompt_history.txt` - AI interaction history

### Health Check
```bash
curl "http://localhost:8000/health"
```

### Metrics
```bash
curl "http://localhost:8000/metrics"
```

## Troubleshooting

### Common Issues

**1. Document Processing Fails**
- Check file format is supported
- Verify file is not corrupted
- Check file size is within limits
- Review processing logs for specific errors

**2. Slow Processing**
- Large files take longer to process
- PDF processing (MinerU) is more intensive than other formats
- Check system resources (CPU, memory)
- Consider adjusting chunk sizes

**3. Search Returns No Results**
- Ensure documents have completed RAG preparation stage
- Check if LightRAG index is properly created
- Verify search query is relevant to document content

**4. API Authentication Issues**
- Verify session token is valid
- Check if authentication is properly configured
- Review API logs for authentication errors

### Getting Help

1. Check the logs in `logs/` directory
2. Review the API documentation at `http://localhost:8000/docs`
3. Verify configuration in `.env` file
4. Check system requirements and dependencies

## Development

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Development Mode
```bash
# Start with auto-reload
uv run src/main.py --reload

# Enable debug logging
LOG_LEVEL=DEBUG uv run src/main.py
```

## Roadmap

### Current Version (Sprint 1)
- ✅ Complete document processing pipeline
- ✅ Multi-format document support
- ✅ Post-processing and enhancement
- ✅ LightRAG integration
- ✅ REST API with search capabilities

### Upcoming Features (Sprint 2)
- 🔄 QueryReactor: Advanced AI-powered question answering
- 🔄 LangGraph integration for complex reasoning
- 🔄 PydanticAI for structured AI interactions
- 🔄 Advanced query processing and response generation

### Future Enhancements
- 📋 Advanced authentication and user management
- 📋 Batch document processing
- 📋 Real-time document updates
- 📋 Advanced analytics and reporting
- 📋 Multi-language support
- 📋 Cloud deployment options

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]