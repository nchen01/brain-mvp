# Brain MVP - Complete Project Explanation

## System Overview

The Brain MVP is a **document processing and knowledge management system** that transforms PDF documents into structured, searchable, and manipulable data. It provides a complete pipeline from document upload to content extraction, storage, and retrieval with comprehensive versioning and metadata tracking.

---

## End-to-End Data Flow

### Phase 1: Document Upload & Registration

#### **1.1 User Upload (Web Interface or API)**
```
User uploads PDF → FastAPI endpoint → Document validation → UUID generation
```

**Entry Points:**
- **Web Interface**: `http://localhost:8000/` (drag & drop or file picker)
- **API Endpoint**: `POST /api/v1/documents/upload`

#### **1.2 Document Registration Process**
```python
# Location: src/docforge/versioning/versions.py
def register_document():
    doc_uuid = generate_document_uuid()        # Primary document identifier
    lineage_uuid = generate_lineage_uuid()     # Document family identifier
    file_hash = calculate_sha256(file_content) # Content fingerprint
    version_number = 1                         # Initial version
```

**UUID Generation & Storage:**
- **Document UUID (`doc_uuid`)**: Unique identifier for this specific document version
- **Lineage UUID (`lineage_uuid`)**: Groups all versions of the same document family
- **File Hash**: SHA-256 fingerprint for duplicate detection
- **Version Number**: Sequential version within the lineage

### Phase 2: Database Storage (Initial Registration)

#### **2.1 Primary Storage Table: `raw_document_register`**
```sql
-- Location: init_tables.sql
CREATE TABLE raw_document_register (
    doc_uuid TEXT PRIMARY KEY,           -- Unique document version ID
    lineage_uuid TEXT NOT NULL,          -- Document family ID
    version_number INTEGER NOT NULL,     -- Version within family
    filename TEXT NOT NULL,              -- Original filename
    file_path TEXT NOT NULL,             -- Storage path
    file_type TEXT NOT NULL,             -- File extension (.pdf)
    file_hash TEXT NOT NULL,             -- SHA-256 content hash
    file_size INTEGER NOT NULL,          -- File size in bytes
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT NOT NULL,               -- User who uploaded
    content TEXT DEFAULT '',             -- EXTRACTED TEXT STORED HERE
    metadata TEXT DEFAULT '{}',          -- PROCESSING METADATA (JSON)
    status TEXT DEFAULT 'active',        -- Document status
    is_current BOOLEAN DEFAULT TRUE      -- Latest version flag
);
```

#### **2.2 Lineage Tracking Table: `document_lineage`**
```sql
CREATE TABLE document_lineage (
    lineage_uuid TEXT PRIMARY KEY,       -- Family identifier
    original_filename TEXT NOT NULL,     -- First uploaded filename
    created_by TEXT NOT NULL,            -- Original uploader
    current_version INTEGER DEFAULT 1,   -- Latest version number
    total_versions INTEGER DEFAULT 1,    -- Total versions in family
    is_active BOOLEAN DEFAULT TRUE       -- Family active status
);
```

### Phase 3: Background Processing Pipeline

#### **3.1 Processing Queue**
```python
# Location: src/api/routers/documents.py
processing_tasks = {}  # In-memory task tracking

# Task structure:
task = {
    'document_id': doc_uuid,
    'filename': filename,
    'file_size': file_size,
    'status': 'pending',      # pending → processing → completed/failed
    'started_at': timestamp,
    'progress': 0.0,          # 0-100%
    'extracted_content': None # Will store extracted text
}
```

#### **3.2 PDF Processing Engine**
```python
# Location: src/docforge/preprocessing/advanced_pdf_processor.py
class AdvancedPDFProcessor:
    def process_document(self, filename, file_content):
        # Multi-library approach with fallbacks:
        
        # 1. PyMuPDF (Primary)
        extracted_content = pymupdf_extract(file_content)
        
        # 2. pdfplumber (Fallback for tables)
        if len(extracted_content) < 100:
            extracted_content = pdfplumber_extract(file_content)
        
        # 3. pdfminer (Final fallback)
        if len(extracted_content) < 50:
            extracted_content = pdfminer_extract(file_content)
        
        return ProcessingResult(
            success=True,
            output=StandardizedDocumentOutput(
                content=extracted_content,    # RAW TEXT
                metadata={                    # PROCESSING DETAILS
                    'libraries_used': ['PyMuPDF'],
                    'pages_processed': 5,
                    'tables_detected': 2,
                    'processing_time': 1.23
                }
            )
        )
```

### Phase 4: Content Storage & Indexing

#### **4.1 Extracted Content Storage**
```python
# Location: src/api/routers/documents.py (background_process_document)
def store_extracted_content():
    db_ops.execute_query("""
        INSERT OR REPLACE INTO raw_document_register 
        (doc_uuid, lineage_uuid, version_number, filename, file_path, file_type, 
         file_hash, file_size, user_id, content, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_uuid,                    # Document UUID
        lineage_uuid,                # Family UUID  
        version_number,              # Version number
        filename,                    # Original filename
        file_path,                   # Storage path
        file_type,                   # .pdf
        file_hash,                   # SHA-256 hash
        file_size,                   # File size
        user_id,                     # Uploader
        extracted_content,           # FULL EXTRACTED TEXT
        json.dumps({                 # PROCESSING METADATA
            'processing_method': 'AdvancedPDFProcessor',
            'processing_timestamp': '2025-10-29T07:00:00Z',
            'content_length': 1234,
            'libraries_used': ['PyMuPDF'],
            'pages_processed': 5,
            'tables_detected': 2
        })
    ))
```

#### **4.2 Data Structure After Processing**
```json
{
  "doc_uuid": "abc123-def456-ghi789",
  "lineage_uuid": "family-uuid-123",
  "version_number": 1,
  "filename": "report.pdf",
  "content": "Full extracted text content from the PDF document...",
  "metadata": {
    "processing_method": "AdvancedPDFProcessor",
    "libraries_used": ["PyMuPDF"],
    "pages_processed": 5,
    "tables_detected": 2,
    "processing_time": 1.23,
    "content_length": 1234
  }
}
```

---

## Data Storage Architecture

### Primary Storage Locations

#### **1. Document Content Storage**
```
Table: raw_document_register
Primary Key: doc_uuid
Content Location: content column (TEXT)
Metadata Location: metadata column (JSON TEXT)
```

#### **2. Document Relationships**
```
Table: document_lineage
Primary Key: lineage_uuid
Purpose: Groups document versions into families
Tracks: version history, current version, total versions
```

#### **3. Post-Processing Storage**
```
Table: post_document_register
Purpose: Stores chunked/processed document segments
Links to: raw_document_register via doc_uuid
```

#### **4. Meta Document Storage**
```
Table: meta_document_register  
Purpose: Stores document metadata and analysis results
Links to: raw_document_register via doc_uuid
```

### UUID Hierarchy & Relationships

```
Document Family (lineage_uuid)
├── Version 1 (doc_uuid_v1) ──┐
├── Version 2 (doc_uuid_v2)   │── All share same lineage_uuid
└── Version 3 (doc_uuid_v3) ──┘

Each doc_uuid has:
├── Raw content in raw_document_register
├── Processed chunks in post_document_register  
└── Metadata in meta_document_register
```

---

## Content Retrieval & API Access

### API Endpoints for Data Access

#### **1. Document Status**
```http
GET /api/v1/documents/{doc_uuid}/status
```
**Returns:**
```json
{
  "document_id": "abc123-def456-ghi789",
  "status": "completed",
  "progress": 100.0,
  "started_at": "2025-10-29T07:00:00Z",
  "completed_at": "2025-10-29T07:00:05Z"
}
```

#### **2. Content Extraction (Multiple Formats)**
```http
GET /api/v1/documents/{doc_uuid}/content?format={text|json|markdown}
```

**Text Format Response:**
```json
{
  "document_id": "abc123-def456-ghi789",
  "filename": "report.pdf",
  "extracted_text": "Full document text content...",
  "text_length": 1234
}
```

**JSON Format Response (Complete Metadata):**
```json
{
  "document_id": "abc123-def456-ghi789",
  "filename": "report.pdf",
  "file_size": 12345,
  "content_available": true,
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
    },
    "file_info": {
      "original_filename": "report.pdf",
      "file_size_bytes": 12345,
      "upload_timestamp": "2025-10-29T07:00:00Z"
    }
  }
}
```

---

## Data Manipulation & Future Use

### Direct Database Access

#### **1. Raw SQL Queries**
```sql
-- Get all documents with extracted content
SELECT doc_uuid, filename, content, metadata 
FROM raw_document_register 
WHERE content IS NOT NULL AND content != '';

-- Get document families with version counts
SELECT l.lineage_uuid, l.original_filename, l.total_versions, l.current_version
FROM document_lineage l;

-- Get processing statistics
SELECT 
    JSON_EXTRACT(metadata, '$.libraries_used') as processing_method,
    COUNT(*) as document_count,
    AVG(JSON_EXTRACT(metadata, '$.processing_time')) as avg_processing_time
FROM raw_document_register 
WHERE metadata != '{}' 
GROUP BY JSON_EXTRACT(metadata, '$.libraries_used');
```

#### **2. Content Search & Analysis**
```sql
-- Full-text search (SQLite FTS if enabled)
SELECT doc_uuid, filename, 
       SUBSTR(content, 1, 200) as preview
FROM raw_document_register 
WHERE content LIKE '%search_term%';

-- Document size analysis
SELECT 
    file_type,
    COUNT(*) as count,
    AVG(file_size) as avg_size,
    AVG(LENGTH(content)) as avg_extracted_length
FROM raw_document_register 
GROUP BY file_type;
```

### Programmatic Access

#### **1. Python Database Operations**
```python
from dbm.operations import get_db_operations

db_ops = get_db_operations()

# Get all documents with content
documents = db_ops.execute_query("""
    SELECT doc_uuid, filename, content, metadata 
    FROM raw_document_register 
    WHERE content IS NOT NULL
""", fetch=True)

for doc in documents:
    doc_id = doc['doc_uuid']
    content = doc['content']
    metadata = json.loads(doc['metadata'])
    
    # Process content for analysis
    word_count = len(content.split())
    processing_method = metadata.get('libraries_used', [])
    
    print(f"Document {doc_id}: {word_count} words, processed with {processing_method}")
```

#### **2. Content Processing Pipeline**
```python
# Example: Extract all document content for ML processing
def extract_all_content():
    db_ops = get_db_operations()
    
    results = db_ops.execute_query("""
        SELECT doc_uuid, filename, content, 
               JSON_EXTRACT(metadata, '$.pages_processed') as pages,
               JSON_EXTRACT(metadata, '$.tables_detected') as tables
        FROM raw_document_register 
        WHERE content IS NOT NULL AND content != ''
    """, fetch=True)
    
    corpus = []
    for row in results:
        corpus.append({
            'id': row['doc_uuid'],
            'filename': row['filename'],
            'text': row['content'],
            'pages': row['pages'],
            'tables': row['tables']
        })
    
    return corpus

# Use for ML/NLP processing
documents = extract_all_content()
# Feed to embedding models, search engines, etc.
```

### Advanced Manipulation Scenarios

#### **1. Document Versioning & Comparison**
```python
def compare_document_versions(lineage_uuid):
    db_ops = get_db_operations()
    
    versions = db_ops.execute_query("""
        SELECT doc_uuid, version_number, filename, content, timestamp
        FROM raw_document_register 
        WHERE lineage_uuid = ? 
        ORDER BY version_number
    """, (lineage_uuid,), fetch=True)
    
    # Compare content between versions
    for i in range(1, len(versions)):
        prev_content = versions[i-1]['content']
        curr_content = versions[i]['content']
        
        # Calculate similarity, changes, etc.
        similarity = calculate_similarity(prev_content, curr_content)
        print(f"Version {i} vs {i+1}: {similarity:.2%} similar")
```

#### **2. Batch Content Processing**
```python
def process_all_documents_for_rag():
    """Prepare all documents for RAG (Retrieval Augmented Generation)"""
    
    db_ops = get_db_operations()
    
    # Get all processed documents
    documents = db_ops.execute_query("""
        SELECT doc_uuid, filename, content, metadata
        FROM raw_document_register 
        WHERE content IS NOT NULL AND LENGTH(content) > 100
    """, fetch=True)
    
    processed_docs = []
    for doc in documents:
        # Chunk content for vector embeddings
        chunks = chunk_text(doc['content'], chunk_size=512)
        
        for i, chunk in enumerate(chunks):
            processed_docs.append({
                'doc_id': doc['doc_uuid'],
                'chunk_id': f"{doc['doc_uuid']}_chunk_{i}",
                'filename': doc['filename'],
                'content': chunk,
                'metadata': json.loads(doc['metadata'])
            })
    
    return processed_docs
```

#### **3. Export & Integration**
```python
def export_to_external_systems():
    """Export processed documents to external systems"""
    
    db_ops = get_db_operations()
    
    # Export to Elasticsearch
    def export_to_elasticsearch():
        documents = db_ops.execute_query("""
            SELECT doc_uuid, filename, content, metadata, timestamp
            FROM raw_document_register 
            WHERE content IS NOT NULL
        """, fetch=True)
        
        for doc in documents:
            es_doc = {
                'id': doc['doc_uuid'],
                'filename': doc['filename'],
                'content': doc['content'],
                'metadata': json.loads(doc['metadata']),
                'indexed_at': datetime.now().isoformat()
            }
            # elasticsearch_client.index(index='documents', body=es_doc)
    
    # Export to Vector Database (Pinecone, Weaviate, etc.)
    def export_to_vector_db():
        documents = db_ops.execute_query("""
            SELECT doc_uuid, filename, content
            FROM raw_document_register 
            WHERE content IS NOT NULL
        """, fetch=True)
        
        for doc in documents:
            # Generate embeddings
            embedding = generate_embedding(doc['content'])
            
            # Store in vector database
            vector_record = {
                'id': doc['doc_uuid'],
                'values': embedding,
                'metadata': {
                    'filename': doc['filename'],
                    'content_preview': doc['content'][:200]
                }
            }
            # vector_db.upsert([vector_record])
```

---

## System Configuration & Scaling

### Database Configuration
```python
# Current: SQLite (MVP)
DATABASE_URL = "sqlite:///data/brain_mvp.db"

# Production: PostgreSQL
DATABASE_URL = "postgresql://user:pass@host:5432/brain_mvp"
```

### Storage Paths
```
Project Root/
├── data/
│   └── brain_mvp.db          # SQLite database file
├── uploads/                  # Temporary upload storage
├── processed/                # Processed document cache
└── logs/                     # Application logs
```

### Scaling Considerations

#### **1. Content Storage Optimization**
- **Current**: Full text stored in database `content` column
- **Future**: Move large content to file system, store file paths in database
- **Benefits**: Reduced database size, faster queries, better backup strategies

#### **2. Search Enhancement**
```sql
-- Add full-text search indexes
CREATE VIRTUAL TABLE document_fts USING fts5(
    doc_uuid, filename, content, 
    content='raw_document_register', 
    content_rowid='rowid'
);

-- Enable fast content search
SELECT doc_uuid, filename FROM document_fts 
WHERE document_fts MATCH 'search query';
```

#### **3. Caching Layer**
```python
# Add Redis caching for frequently accessed content
import redis

cache = redis.Redis(host='localhost', port=6379, db=0)

def get_document_content(doc_uuid):
    # Check cache first
    cached = cache.get(f"doc:{doc_uuid}")
    if cached:
        return json.loads(cached)
    
    # Fallback to database
    content = db_ops.execute_query("""
        SELECT content, metadata FROM raw_document_register 
        WHERE doc_uuid = ?
    """, (doc_uuid,), fetch=True)
    
    # Cache for future requests
    cache.setex(f"doc:{doc_uuid}", 3600, json.dumps(content))
    return content
```

---

## Summary: What Happens to Your Data

### Upload → Processing → Storage → Retrieval

1. **Upload**: PDF file uploaded via web interface or API
2. **Registration**: Document gets unique UUIDs and is registered in `document_lineage` and `raw_document_register`
3. **Processing**: Background task extracts text using PyMuPDF/pdfplumber/pdfminer
4. **Storage**: Extracted text stored in `raw_document_register.content` column with metadata
5. **Retrieval**: Content accessible via API in multiple formats (text, JSON, markdown)

### Key Data Locations

| Data Type | Storage Location | Access Method |
|-----------|------------------|---------------|
| **Extracted Text** | `raw_document_register.content` | API: `/documents/{id}/content` |
| **Processing Metadata** | `raw_document_register.metadata` | API: `/documents/{id}/content?format=json` |
| **Document UUIDs** | `raw_document_register.doc_uuid` | All API responses |
| **Version History** | `document_lineage` + `raw_document_register` | Database queries |
| **File Information** | `raw_document_register` (filename, size, hash) | API metadata |

### Future Manipulation Possibilities

- **Search & Discovery**: Full-text search across all extracted content
- **Version Comparison**: Compare different versions of the same document
- **Batch Processing**: Process all documents for ML/AI applications
- **Export Integration**: Send data to search engines, vector databases, etc.
- **Analytics**: Generate insights about document processing patterns
- **RAG Preparation**: Chunk and embed content for AI applications

**The Brain MVP provides a solid foundation for document processing with complete data accessibility and manipulation capabilities.**