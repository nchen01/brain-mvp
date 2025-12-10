# Testing Chunking Strategies with Real Documents

## Quick Start

To test the chunking strategies with real PDFs, you have two options:

### Option 1: Use Your Own PDF

Upload a PDF to the `uploads/` directory and run:

```bash
docker-compose exec brain-mvp python3 test_real_documents.py
```

### Option 2: Use the Web Interface

1. Start the system:
   ```bash
   docker-compose up -d
   ```

2. Open the web interface:
   ```
   http://localhost:8080
   ```

3. Upload a PDF through the interface

4. Then run the test script:
   ```bash
   docker-compose exec brain-mvp python3 test_real_documents.py
   ```

### Option 3: Specify a PDF Path

If you have a PDF elsewhere, you can specify the path:

```bash
docker-compose exec brain-mvp python3 test_real_documents.py /path/to/your/file.pdf
```

## What the Test Does

The test script will:

1. ✅ **Process the PDF** using Brain MVP's AdvancedPDFProcessor
2. ✅ **Apply all three chunking strategies**:
   - Recursive Chunking (recommended)
   - Fixed-size Chunking (baseline)
   - Semantic Chunking (quality benchmark)
3. ✅ **Compare results** with detailed statistics:
   - Chunk counts
   - Word count distributions
   - Sample chunk previews
   - Size distribution histograms

## Expected Output

```
================================================================================
REAL DOCUMENT CHUNKING TEST
================================================================================

Configuration:
  Chunk size: 300 words
  Overlap: 50 words
  Min chunk size: 30 words

Found 1 PDF file(s):
  - your_document.pdf (1.23 MB)

================================================================================
TESTING: your_document.pdf
================================================================================

  Processing with recursive... ✓ (15 chunks)
  Processing with fixed_size... ✓ (18 chunks)
  Processing with semantic... ✓ (12 chunks)

================================================================================
CHUNKING COMPARISON
================================================================================

Strategy        Chunks     Avg Words    Min      Max      Total Words 
--------------------------------------------------------------------------------
recursive       15         287.3        245      320      4309        
fixed_size      18         239.4        200      300      4310        
semantic        12         359.2        280      425      4310        

SAMPLE CHUNKS (First chunk from each strategy):
...
```

## Customizing Chunk Parameters

Edit the config in `test_real_documents.py`:

```python
config = {
    'chunk_size': 300,      # Target words per chunk
    'chunk_overlap': 50,    # Overlapping words
    'min_chunk_size': 30,   # Minimum chunk size
    'language': 'en'
}
```

## Troubleshooting

**No PDFs found?**
- Check these directories: `uploads/`, `data/uploads/`, `temp/`, `processed/`
- Use the web interface at http://localhost:8080 to upload a PDF
- Specify a PDF path as command argument

**Import errors?**
- Make sure you're running inside Docker: `docker-compose exec brain-mvp python3 test_real_documents.py`
- The script needs the full Brain MVP environment

**Processing fails?**
- Check that the PDF is valid and not corrupted
- Try with a smaller, simpler PDF first
- Check logs: `docker-compose logs brain-mvp`

## Next Steps After Testing

Once you've tested with real documents:

1. **Review the results** - Which chunking strategy works best for your documents?
2. **Adjust parameters** - Tune chunk_size and overlap based on your needs
3. **Proceed to Phase 2** - Implement Context Enrichment for even better retrieval
