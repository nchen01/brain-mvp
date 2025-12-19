# Brain MVP - Advanced Document Processing & RAG System

A production-ready document processing system that extracts text from PDF documents using advanced multi-library processing and prepares it for high-precision RAG (Retrieval-Augmented Generation).

## 🚀 Key Features

- **Modern Web Interface**: Premium drag-and-drop interface for document management, real-time status monitoring, and chunking visualization.
- **Advanced PDF Processing**: Multi-library approach using **PyMuPDF**, **pdfplumber**, and **pdfminer** with automatic fallbacks for maximum extraction reliability.
- **High-Precision RAG Pipeline**:
  - **Multiple Chunking Strategies**: Recursive, Fixed-size, and Semantic chunking.
  - **Context Enrichment**: Anthropic-style context-enriched chunking for improved retrieval accuracy.
- **Individual Document Management**: Support for individual document deletion with full cleanup of associated chunks and metadata.
- **Robust Storage Architecture**: Multi-tier storage system supporting both SQLite (development) and PostgreSQL (production).
- **Production Ready**: Fully containerized with Docker, including PostgreSQL and Redis for caching and background tasks.

---

## 🛠 Architecture Overview

### Processing Pipeline
1. **Upload**: Document received via Web UI or REST API.
2. **Extraction**: `AdvancedPDFProcessor` extracts text and metadata using the best available library.
3. **Chunking**: Documents are split into chunks using configurable strategies (Recursive, Semantic, etc.).
4. **Enrichment**: Chunks are optionally enriched with document-level context using LLMs.
5. **Storage**: Content is stored across specialized databases (Raw, Post, Meta, and Chunks).

### Database Schema
The system uses a comprehensive schema to track document lineage and processing history:
- `document_lineage`: Tracks document versions and history.
- `raw_document_register`: Stores original file information and status.
- `document_chunks`: Stores processed chunks with strategy metadata and enrichment content.
- `meta_document_register`: Stores structural metadata and processing status.

---

## ⚡ Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API Key (optional, for semantic chunking and context enrichment)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/nchen01/brain-mvp.git
   cd brain-mvp
   ```

2. **Configure Environment**:
   Create a `.env` file or set environment variables:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   PROCESSING__DEFAULT_CHUNKING_STRATEGY=recursive
   ```

3. **Start the System**:
   ```bash
   docker-compose up -d
   ```

4. **Access the Interface**:
   - **Web UI**: [http://localhost:8080](http://localhost:8080)
   - **API Docs (Swagger)**: [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 🧠 Advanced RAG Capabilities

### Chunking Strategies
The system supports three primary chunking strategies to optimize for different RAG use cases:
- **Recursive Character**: Splits text based on character hierarchy (paragraphs, sentences, words).
- **Fixed Size**: Simple fixed-token windows with configurable overlap.
- **Semantic**: Uses embeddings to find natural semantic boundaries in the text.

### Context Enrichment
Inspired by Anthropic's "Contextual Retrieval", the system can enrich each chunk with document-level context. This significantly improves retrieval accuracy by providing the LLM with the necessary background for each individual chunk.

---

## 🐳 Docker Orchestration

The system is composed of three main services:

| Service | Container Name | Port | Description |
|---------|----------------|------|-------------|
| **App** | `brain-mvp-app` | 8080 | FastAPI application & PDF processing engine |
| **Postgres** | `brain-mvp-postgres` | 5433 | Primary database for document metadata & chunks |
| **Redis** | `brain-mvp-redis` | 6380 | Cache for background tasks and session management |

### Useful Commands
```bash
# View logs
docker-compose logs -f brain-mvp

# Restart the application
docker-compose restart brain-mvp

# Run end-to-end tests
docker-compose exec brain-mvp python final_e2e_test.py
```

---

## 📡 API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload and process a new PDF |
| `GET` | `/api/v1/documents/` | List all uploaded documents |
| `GET` | `/api/v1/documents/{id}/status` | Check processing progress |
| `GET` | `/api/v1/documents/{id}/content` | Retrieve extracted text/JSON/Markdown |
| `DELETE` | `/api/v1/documents/{id}` | Permanently delete a document and its chunks |
| `GET` | `/chunks/document/{id}` | Retrieve all chunks for a document |

---

## 🛡 Safety and Security

### Strict Approval Commands
To prevent accidental data loss, certain operations require explicit user approval. See [`STRICT_APPROVAL_COMMANDS.md`](STRICT_APPROVAL_COMMANDS.md) for details.

### Data Privacy
- Support for encrypted storage of document content.
- Local processing of PDF documents (no external PDF APIs used).
- Configurable data retention policies.

---

## 📄 License
This project is licensed under the MIT License.

## 🤝 Support
For technical support or feature requests, please check the following:
1. **Technical Overview**: [`PROJECT_EXPLANATION.md`](PROJECT_EXPLANATION.md)
2. **User Guide**: [`USAGE_GUIDE.md`](USAGE_GUIDE.md)
3. **Test Results**: [`END_TO_END_TEST_RESULTS.md`](END_TO_END_TEST_RESULTS.md)