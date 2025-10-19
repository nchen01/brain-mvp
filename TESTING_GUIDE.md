# DocForge MVP - Testing Guide

This guide provides step-by-step instructions for testing the DocForge MVP with your own PDF files.

## Quick Start (5 minutes)

### Option 1: Simple Test Script

1. **Place your PDF file** in the project directory
2. **Run the test script**:
   ```bash
   python3 test_your_pdf.py your_document.pdf
   ```
3. **Check results** in the `./output` directory

### Option 2: Interactive Python Session

1. **Start Python**:
   ```bash
   python3
   ```

2. **Run this code** (replace `your_document.pdf` with your file):
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path.cwd() / "src"))
   
   from docforge.preprocessing.processor_factory import ProcessorFactory
   
   # Initialize processor
   factory = ProcessorFactory()
   processor = factory.get_processor_for_file("your_document.pdf")
   
   # Process your PDF
   with open("your_document.pdf", "rb") as f:
       content = f.read()
   
   result = processor.process_document("your_document.pdf", file_content=content)
   
   # Check results
   if result.success:
       print("✅ Success!")
       print(f"Pages: {result.output.document_structure.total_pages}")
       print(f"Elements: {result.output.document_structure.total_elements}")
       print(f"Text preview: {result.output.plain_text[:200]}...")
   else:
       print(f"❌ Error: {result.error.error_message}")
   ```

## Detailed Testing Instructions

### Prerequisites

1. **Python 3.8+** installed
2. **Project dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```
3. **A PDF file** to test with

### Step 1: Verify Installation

First, make sure everything is working:

```bash
# Run the example demo
python3 examples/mineru_pdf_processing.py

# Run the tests
python3 -m pytest tests/unit/test_processors.py::test_mineru_processor_mock_processing -v
```

You should see:
- ✅ Demo runs successfully
- ✅ Test passes
- ⚠️ "MinerU not installed. Using mock processing" (this is expected)

### Step 2: Test with Your PDF

#### Method A: Using the Test Script

1. **Copy your PDF** to the project directory:
   ```bash
   cp /path/to/your/document.pdf ./my_test.pdf
   ```

2. **Run the test script**:
   ```bash
   python3 test_your_pdf.py my_test.pdf
   ```

3. **Check the output**:
   ```
   🔍 Testing PDF: my_test.pdf
   📁 Output directory: ./output
   ============================================================
   ✅ File type supported
   ✅ Processor selected: MinerUProcessor
      - Extract images: True
      - Extract tables: True
      - OCR enabled: False
      - Language: en
   
   🔄 Processing PDF...
      File size: 1,234,567 bytes
   ✅ Processing completed successfully in 0.05s
   
   💾 Plain text saved: ./output/my_test_plain.txt
   💾 Markdown saved: ./output/my_test_markdown.md
   💾 Structured data saved: ./output/my_test_structured.json
   ```

#### Method B: Custom Python Script

Create your own test script:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from docforge.preprocessing.mineru_processor import MinerUProcessor

# Configure processor
config = {
    "extract_images": True,
    "extract_tables": True,
    "ocr_enabled": False,  # Set to True if you have scanned PDFs
    "language": "en"
}

processor = MinerUProcessor(config)

# Process your PDF
pdf_path = "your_document.pdf"
with open(pdf_path, "rb") as f:
    pdf_content = f.read()

print(f"Processing {pdf_path}...")
result = processor.process_document(pdf_path, file_content=pdf_content)

if result.success:
    output = result.output
    print(f"✅ Success! Processed {output.document_structure.total_pages} pages")
    print(f"Found {len(output.content_elements)} content elements")
    print(f"Found {len(output.tables)} tables")
    print(f"Found {len(output.images)} images")
    
    # Save results
    with open("extracted_text.txt", "w") as f:
        f.write(output.plain_text)
    
    with open("extracted_markdown.md", "w") as f:
        f.write(output.markdown_text)
    
    print("Results saved to extracted_text.txt and extracted_markdown.md")
else:
    print(f"❌ Error: {result.error.error_message}")
```

### Step 3: Understanding the Results

After processing, you'll get several output files:

#### 1. Plain Text (`*_plain.txt`)
- Clean text extraction from your PDF
- Paragraphs and headings preserved
- Good for search indexing or analysis

#### 2. Markdown (`*_markdown.md`)
- Formatted text with structure preserved
- Tables converted to markdown format
- Headings with proper hierarchy
- Images referenced with captions

#### 3. Structured Data (`*_structured.json`)
- Complete structured representation
- All content elements with metadata
- Table data in structured format
- Image information and locations
- Processing metadata

### Step 4: Analyzing Results

#### Content Elements
Each piece of content is categorized:
- `heading`: Document headings and titles
- `paragraph`: Regular text paragraphs
- `list`: Bulleted or numbered lists
- `table`: Table content (also in separate tables array)
- `image`: Image references (also in separate images array)

#### Tables
Tables are extracted with:
- Headers (column names)
- Rows (data rows)
- Captions (if present)
- Metadata (page number, position)

#### Images
Images are identified with:
- Unique ID
- File path (if extracted)
- Alt text description
- Caption (if present)
- Position information

### Step 5: Testing Different PDF Types

Try different types of PDFs to see how the system handles them:

#### Simple Text PDFs
```bash
python3 test_your_pdf.py simple_text_document.pdf
```
Expected: Clean text extraction, good paragraph structure

#### Complex Layout PDFs
```bash
python3 test_your_pdf.py complex_layout_document.pdf
```
Expected: Structured content with headings, multiple columns handled

#### PDFs with Tables
```bash
python3 test_your_pdf.py document_with_tables.pdf
```
Expected: Tables extracted in structured format

#### PDFs with Images
```bash
python3 test_your_pdf.py document_with_images.pdf
```
Expected: Image locations identified, captions extracted

## Advanced Testing

### Custom Configuration

Test with different processor configurations:

```python
# High-quality processing (slower)
config = {
    "extract_images": True,
    "extract_tables": True,
    "ocr_enabled": True,  # Enable OCR for scanned documents
    "language": "en"
}

# Fast processing (basic text only)
config = {
    "extract_images": False,
    "extract_tables": False,
    "ocr_enabled": False,
    "language": "en"
}
```

### Batch Processing

Process multiple PDFs:

```python
import os
from pathlib import Path

pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

for pdf_file in pdf_files:
    print(f"\nProcessing {pdf_file}...")
    success = test_pdf_file(pdf_file, f"./output/{Path(pdf_file).stem}")
    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
```

### Performance Testing

Test processing time with different file sizes:

```python
import time

start_time = time.time()
result = processor.process_document(pdf_path, file_content=pdf_content)
end_time = time.time()

print(f"Processing time: {end_time - start_time:.2f} seconds")
print(f"File size: {len(pdf_content):,} bytes")
print(f"Processing speed: {len(pdf_content) / (end_time - start_time):,.0f} bytes/second")
```

## Troubleshooting

### Common Issues

#### "File not found" Error
```
❌ Error: File not found: document.pdf
```
**Solution**: Check file path and permissions
```bash
ls -la document.pdf  # Verify file exists and is readable
```

#### "File must be a PDF" Error
```
❌ Error: File must be a PDF: document.txt
```
**Solution**: Ensure file has `.pdf` extension and is actually a PDF

#### Processing Fails
```
❌ Processing failed: 'str' object has no attribute 'value'
```
**Solution**: This indicates a code issue. Try with a different PDF or report the bug.

#### Empty Results
If processing succeeds but results are empty:
- Try a different PDF file
- Check if the PDF has selectable text (not just scanned images)
- Enable OCR if processing scanned documents

### Getting Help

1. **Check the logs**: Look for detailed error messages in the console output
2. **Try the demo**: Run `python3 examples/mineru_pdf_processing.py` to verify basic functionality
3. **Run tests**: Execute `python3 -m pytest tests/unit/test_processors.py -v` to check system health
4. **Test with simple PDF**: Try with a basic text-only PDF first

## What's Happening Under the Hood

### Current Implementation (MVP)
- **Mock Processing**: Since MinerU isn't installed, the system uses realistic mock data
- **File Type Detection**: Multi-method detection (extension, MIME type, magic numbers)
- **Standardized Output**: All results converted to consistent format
- **Error Handling**: Graceful fallback and clear error messages

### With Real MinerU (Future)
When you install MinerU (`pip install magic-pdf`), the system will:
- Use actual PDF parsing instead of mock data
- Extract real text, tables, and images from your PDFs
- Provide more accurate layout detection
- Support OCR for scanned documents

### Architecture
```
Your PDF → File Type Detection → MinerU Processor → Standardized Output → Results
```

## Next Steps

After testing the preprocessing:

1. **Document Registration**: Test with the document versioning system
2. **Post-Processing**: Try the chunking and abbreviation expansion (when implemented)
3. **RAG Integration**: Test with LightRAG for document search (when implemented)
4. **API Testing**: Use the REST API endpoints (when implemented)

## Sample Test Files

For testing, you can use these types of documents:

- **Simple text document**: Any basic PDF with paragraphs
- **Academic paper**: PDF with abstract, sections, references
- **Business report**: Document with tables, charts, executive summary
- **Technical manual**: Multi-column layout with images and tables
- **Scanned document**: Image-based PDF (requires OCR)

The system should handle all these types gracefully, extracting what it can and providing clear feedback about the results.