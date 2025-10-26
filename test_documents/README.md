# Test Documents

This folder contains sample documents for testing the Brain MVP system.

## Available Test Files

### Text Files
- `sample_text.txt` - Basic text document for testing text processing
- `technical_document.md` - Markdown document with technical content
- `structured_content.rst` - ReStructuredText document with structured content

### PDF Files
- `sample_pdf.pdf` - Basic PDF document for testing PDF processing
- `complex_document.pdf` - Multi-page PDF with tables and images

## Usage

These documents can be used to test the document processing pipeline:

```bash
# Upload a test document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@test_documents/sample_text.txt"

# Or use the automated test
python run_complete_test.py
```

## Document Characteristics

### sample_text.txt
- Size: Small (< 1KB)
- Content: Plain text with basic formatting
- Expected processing time: < 1 second
- Expected confidence: > 0.95

### technical_document.md
- Size: Medium (1-5KB)
- Content: Technical documentation with abbreviations
- Expected processing time: < 2 seconds
- Expected confidence: > 0.90
- Expected abbreviations expanded: 5+

### structured_content.rst
- Size: Medium (1-5KB)
- Content: Structured documentation format
- Expected processing time: < 2 seconds
- Expected confidence: > 0.90

## Quality Expectations

All test documents should achieve:
- Confidence score: > 0.90
- Completeness score: > 0.95
- Processing time: < 5 seconds
- Successful chunking for RAG applications