# Brain MVP Complete Guide - Upload to Extraction

## 🚀 Complete Step-by-Step Instructions

This guide takes you from zero to fully functional document processing in minutes.

## 📋 Prerequisites

Make sure you have:
- Docker and Docker Compose installed
- Terminal/Command Prompt access
- Documents ready to process (text files, PDFs)

## 🏁 Step 1: Start the Brain MVP

```bash
# Start the system
docker-compose up -d

# Verify it's running (should return {"status": "healthy"})
curl http://localhost:8000/health
```

**Expected Output:**
```json
{"status": "healthy"}
```

## 📤 Step 2: Upload Your Document

### Method A: Command Line (Recommended)

```bash
# Upload a text file
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@your_document.txt" \
  -v

# Upload a PDF file  
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@your_document.pdf" \
  -v
```

### Method B: Web Interface

1. Open: http://localhost:8000/docs
2. Find `POST /api/v1/documents/upload`
3. Click "Try it out"
4. Choose your file and click "Execute"

### Method C: Python Script

```python
import requests

with open('your_document.txt', 'rb') as f:
    files = {'file': ('your_document.txt', f, 'text/plain')}
    response = requests.post(
        "http://localhost:8000/api/v1/documents/upload",
        files=files
    )
    
result = response.json()
document_id = result['document_id']
print(f"Document ID: {document_id}")
```

**Expected Upload Response:**
```json
{
  "document_id": "abc123-def456-ghi789",
  "lineage_id": "abc123-def456-ghi789", 
  "version_number": 1,
  "filename": "your_document.txt",
  "file_size": 1024,
  "processing_status": "pending",
  "upload_timestamp": "2025-10-25T05:03:58.804728"
}
```

**🔑 IMPORTANT: Copy the `document_id` - you'll need it for all next steps!**

## ⏳ Step 3: Monitor Processing

```bash
# Replace YOUR_DOCUMENT_ID with the actual ID from upload
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/status" | jq
```

**Processing Status Examples:**

**Still Processing:**
```json
{
  "document_id": "abc123-def456-ghi789",
  "status": "processing",
  "stage": "preprocessing", 
  "progress": 45.0,
  "started_at": "2025-10-25T05:03:58.804728",
  "completed_at": null,
  "error_message": null
}
```

**Completed Successfully:**
```json
{
  "document_id": "abc123-def456-ghi789", 
  "status": "completed",
  "stage": "completed",
  "progress": 100.0,
  "started_at": "2025-10-25T05:03:58.804728",
  "completed_at": "2025-10-25T05:03:58.810000",
  "error_message": null
}
```

**⏰ Wait until `"status": "completed"` before proceeding!**

## 📄 Step 4: Get Extraction Results

```bash
# Get all processing stages and extraction results
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/processed" | jq
```

**Expected Extraction Results:**
```json
[
  {
    "document_id": "abc123-def456-ghi789",
    "version_id": "version-uuid",
    "processing_stage": "raw",
    "available_formats": ["original"],
    "file_size": 1024,
    "processing_timestamp": "2025-10-25T05:03:58.804728",
    "processor_info": {
      "stage": "raw",
      "format": "original"
    },
    "quality_metrics": {}
  },
  {
    "document_id": "abc123-def456-ghi789",
    "version_id": "version-uuid", 
    "processing_stage": "preprocessed",
    "available_formats": ["text", "markdown", "json"],
    "file_size": 2048,
    "processing_timestamp": "2025-10-25T05:03:58.804728",
    "processor_info": {
      "stage": "preprocessed",
      "processor": "text"
    },
    "quality_metrics": {
      "confidence": 0.95,
      "completeness": 0.98
    }
  },
  {
    "document_id": "abc123-def456-ghi789",
    "version_id": "version-uuid",
    "processing_stage": "postprocessed", 
    "available_formats": ["chunks", "expanded", "structured"],
    "file_size": 3072,
    "processing_timestamp": "2025-10-25T05:03:58.810000",
    "processor_info": {
      "stage": "postprocessed",
      "methods": ["chunking", "abbreviation_expansion"]
    },
    "quality_metrics": {
      "chunk_count": 15,
      "abbreviations_expanded": 5
    }
  }
]
```

## 🎯 Step 5: Understanding Your Results

### **Raw Stage** - Original File Preserved
- **Formats**: `["original"]`
- **Meaning**: Your original document is safely stored
- **Use**: Reference back to original content

### **Preprocessed Stage** - Text Extracted ✨
- **Formats**: `["text", "markdown", "json"]`
- **Quality Metrics**:
  - `confidence: 0.95` = 95% confident extraction is accurate
  - `completeness: 0.98` = 98% of content successfully extracted
- **Meaning**: Clean, extracted text ready for use

### **Postprocessed Stage** - RAG-Ready Content 🚀
- **Formats**: `["chunks", "expanded", "structured"]`
- **Quality Metrics**:
  - `chunk_count: 15` = Document split into 15 searchable pieces
  - `abbreviations_expanded: 5` = Technical terms expanded
- **Meaning**: Content optimized for AI/RAG applications

## 🧪 Step 6: Quick Test Everything Works

Run the automated test to verify your setup:

```bash
python working_content_demo.py
```

**Expected Output:**
```
🧠 Brain MVP - Working Document Extraction Demo
============================================================
📤 Step 1: Uploading demonstration document...
✅ Upload successful!
   Document ID: abc123-def456-ghi789

⏳ Step 2: Monitoring processing...
   📊 Status: completed | Progress: 100.0%
✅ Processing completed!

📄 Step 3: Getting extraction results...
✅ Extraction results retrieved!
   Found 3 processing stages

🎯 Extraction Summary:
   ✅ Stages completed: raw, preprocessed, postprocessed
   ✅ Total formats available: 7
   ✅ Quality metrics available for 2 stages

🎉 SUCCESS! Document extraction is fully functional!
```

## 📁 Supported File Types

| File Type | Extensions | Processor | Status |
|-----------|------------|-----------|---------|
| **Text Files** | `.txt`, `.md`, `.rst` | TextDocumentProcessor | ✅ Fully Working |
| **PDF Files** | `.pdf` | MinerU (Advanced) | ✅ Fully Working |
| **Word Documents** | `.docx`, `.doc` | MarkItDown | 🔄 Available |
| **Excel Files** | `.xlsx`, `.xls`, `.csv` | MarkItDown | 🔄 Available |
| **PowerPoint** | `.pptx`, `.ppt` | MarkItDown | 🔄 Available |

## 🔧 Complete Working Example

```bash
# 1. Start system
docker-compose up -d

# 2. Create test document
echo "# My Test Document
This document contains important information about APIs and MVPs.
It should be processed into multiple chunks for RAG applications.

## Technical Content
- Application Programming Interface (API)
- Minimum Viable Product (MVP) 
- Retrieval Augmented Generation (RAG)

The system should extract this content with high confidence." > my_test.txt

# 3. Upload document
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@my_test.txt" -v

# 4. Copy document_id from response, then check status
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/status" | jq

# 5. Get extraction results (wait until status is "completed")
curl "http://localhost:8000/api/v1/documents/YOUR_DOCUMENT_ID/processed" | jq
```

## 🐍 Python Complete Example

```python
import requests
import time
import json

def complete_mvp_workflow():
    """Complete workflow from upload to extraction"""
    
    # 1. Create test content
    content = """# Complete MVP Test
    
This document tests the full Brain MVP pipeline.

## Features
- Document upload and processing
- Text extraction with high accuracy
- Content chunking for RAG applications
- Quality metrics and confidence scores

## Technical Terms
- API (Application Programming Interface)
- MVP (Minimum Viable Product)
- RAG (Retrieval Augmented Generation)

The system should process this successfully.
"""
    
    # 2. Upload document
    files = {'file': ('test.txt', content, 'text/plain')}
    response = requests.post(
        "http://localhost:8000/api/v1/documents/upload",
        files=files
    )
    
    if response.status_code == 200:
        result = response.json()
        document_id = result['document_id']
        print(f"✅ Uploaded! Document ID: {document_id}")
    else:
        print(f"❌ Upload failed: {response.text}")
        return
    
    # 3. Monitor processing
    print("⏳ Waiting for processing...")
    for i in range(30):
        status_response = requests.get(
            f"http://localhost:8000/api/v1/documents/{document_id}/status"
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"   Status: {status['status']} ({status['progress']}%)")
            
            if status['status'] == 'completed':
                break
        
        time.sleep(2)
    
    # 4. Get extraction results
    processed_response = requests.get(
        f"http://localhost:8000/api/v1/documents/{document_id}/processed"
    )
    
    if processed_response.status_code == 200:
        results = processed_response.json()
        print(f"✅ Extraction completed! Found {len(results)} stages:")
        
        for result in results:
            stage = result['processing_stage']
            formats = result['available_formats']
            quality = result.get('quality_metrics', {})
            
            print(f"   📋 {stage}: {formats}")
            if quality:
                print(f"      Quality: {quality}")
    
    return document_id

# Run the complete workflow
if __name__ == "__main__":
    document_id = complete_mvp_workflow()
    print(f"\n🎉 Complete! Your document ID: {document_id}")
```

## 🚨 Troubleshooting

### System Won't Start
```bash
# Check if containers are running
docker-compose ps

# Restart if needed
docker-compose restart brain-mvp

# Check logs
docker-compose logs brain-mvp
```

### Upload Fails
- **File too large**: Try smaller files first
- **Unsupported format**: Use .txt or .pdf files
- **Connection issues**: Check `curl http://localhost:8000/health`

### Processing Stuck
- **Check status**: Use the status endpoint
- **Wait longer**: Large files take more time
- **Restart system**: `docker-compose restart brain-mvp`

### No Extraction Results
- **Verify completion**: Status must be "completed"
- **Check file format**: Ensure supported file type
- **Review logs**: `docker-compose logs brain-mvp`

## 🎯 Quality Metrics Guide

### Confidence Scores
- **0.95+**: Excellent extraction quality
- **0.85-0.94**: Good extraction quality  
- **0.75-0.84**: Acceptable extraction quality
- **Below 0.75**: Review original document

### Completeness Scores
- **0.98+**: Nearly all content extracted
- **0.90-0.97**: Most content extracted
- **0.80-0.89**: Significant content extracted
- **Below 0.80**: Some content may be missing

## 🚀 Next Steps

Once everything is working:

1. **Upload your real documents** using the same process
2. **Monitor quality metrics** to ensure good extraction
3. **Use the chunked content** for RAG applications
4. **Build integrations** using the API endpoints
5. **Scale up processing** for larger document volumes

## 📞 Quick Reference Commands

```bash
# Start system
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Upload document
curl -X POST "http://localhost:8000/api/v1/documents/upload" -F "file=@doc.txt"

# Check status
curl "http://localhost:8000/api/v1/documents/DOC_ID/status" | jq

# Get results
curl "http://localhost:8000/api/v1/documents/DOC_ID/processed" | jq

# Run test
python working_content_demo.py

# View API docs
open http://localhost:8000/docs
```

## 🎉 Success Indicators

You know everything is working when you see:

✅ **Upload Response**: Document ID returned  
✅ **Status**: "completed" with 100% progress  
✅ **Extraction Results**: 3 processing stages (raw, preprocessed, postprocessed)  
✅ **Quality Metrics**: High confidence (0.95+) and completeness (0.98+)  
✅ **Multiple Formats**: 7+ available formats across all stages  
✅ **Chunking**: Document split into multiple chunks for RAG  

**Your Brain MVP is now fully functional and ready for production use!** 🚀