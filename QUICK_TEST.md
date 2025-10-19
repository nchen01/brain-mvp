# Quick Test - DocForge MVP

## 🚀 Test Your PDF in 3 Steps

### Step 1: Get a PDF
Place any PDF file in this directory, or have the path ready.

### Step 2: Run the Interactive Tester
```bash
python3 interactive_test.py
```

### Step 3: Follow the Prompts
The script will guide you through:
- Selecting your PDF file
- Configuring processing options
- Viewing results
- Saving output files

## 🎯 Alternative: Direct Testing

### Quick Command Line Test
```bash
python3 test_your_pdf.py your_document.pdf
```

### Quick Python Test
```python
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from docforge.preprocessing.processor_factory import ProcessorFactory

factory = ProcessorFactory()
processor = factory.get_processor_for_file('your_document.pdf')

with open('your_document.pdf', 'rb') as f:
    content = f.read()

result = processor.process_document('your_document.pdf', file_content=content)

if result.success:
    print('✅ Success!')
    print(f'Pages: {result.output.document_structure.total_pages}')
    print(f'Elements: {result.output.document_structure.total_elements}')
    print(f'Text: {result.output.plain_text[:200]}...')
else:
    print(f'❌ Error: {result.error.error_message}')
"
```

## 📁 What You'll Get

After processing, you'll have:
- **Plain text** extraction
- **Markdown** formatted version  
- **Structured JSON** with all data
- **Tables** in structured format
- **Image** locations and captions

## 🔧 Current Status

- ✅ **PDF Processing**: Works with mock data (realistic results)
- ⚠️ **MinerU**: Not installed (using mock - install with `pip install magic-pdf` for real processing)
- ✅ **All File Types**: Detected and routed correctly
- ✅ **Error Handling**: Graceful fallbacks and clear messages

## 🆘 Need Help?

1. **File not found**: Make sure PDF path is correct
2. **Processing fails**: Try a different PDF file
3. **Empty results**: Check if PDF has selectable text
4. **Other issues**: Check `TESTING_GUIDE.md` for detailed troubleshooting

## 🎉 What's Next?

After testing preprocessing:
1. Document registration and versioning
2. Post-processing (chunking, abbreviation expansion)  
3. RAG integration with LightRAG
4. REST API endpoints
5. Complete system integration