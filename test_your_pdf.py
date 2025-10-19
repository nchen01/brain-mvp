#!/usr/bin/env python3
"""
DocForge MVP - Test Your Own PDF

This script allows you to test the DocForge preprocessing pipeline with your own PDF files.
It provides a simple interface to process PDFs and see the results.
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from docforge.preprocessing.processor_factory import ProcessorFactory
from docforge.preprocessing.mineru_processor import MinerUProcessor
from docforge.preprocessing.schemas import ProcessingStatus


def test_pdf_file(pdf_path: str, output_dir: Optional[str] = None) -> bool:
    """
    Test processing a PDF file with DocForge.
    
    Args:
        pdf_path: Path to the PDF file to process
        output_dir: Optional directory to save results (default: ./output)
        
    Returns:
        True if processing succeeded, False otherwise
    """
    # Validate input file
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        return False
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"❌ Error: File must be a PDF: {pdf_path}")
        return False
    
    # Set up output directory
    if output_dir is None:
        output_dir = "./output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🔍 Testing PDF: {pdf_path}")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 60)
    
    try:
        # Initialize processor factory
        factory = ProcessorFactory()
        
        # Check if file is supported
        if not factory.is_file_supported(pdf_path):
            print(f"❌ File type not supported: {pdf_path}")
            return False
        
        print("✅ File type supported")
        
        # Get processor for the file
        processor = factory.get_processor_for_file(pdf_path)
        if not processor:
            print("❌ No processor available for this file")
            return False
        
        print(f"✅ Processor selected: {processor.processor_name}")
        
        # Show processor configuration
        if isinstance(processor, MinerUProcessor):
            print(f"   - Extract images: {processor.extract_images}")
            print(f"   - Extract tables: {processor.extract_tables}")
            print(f"   - OCR enabled: {processor.ocr_enabled}")
            print(f"   - Language: {processor.language}")
        
        print("\n🔄 Processing PDF...")
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"   File size: {len(pdf_content):,} bytes")
        
        # Process the document
        result = processor.process_document(pdf_path, file_content=pdf_content)
        
        if result.success:
            print(f"✅ Processing completed successfully in {result.processing_time:.2f}s")
            
            # Save results
            save_results(result.output, pdf_path, output_dir)
            
            # Show summary
            show_processing_summary(result.output)
            
            return True
        else:
            print(f"❌ Processing failed: {result.error.error_message}")
            print(f"   Error type: {result.error.error_type}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_results(output, pdf_path: str, output_dir: str):
    """Save processing results to files."""
    base_name = Path(pdf_path).stem
    
    # Save plain text
    plain_text_path = os.path.join(output_dir, f"{base_name}_plain.txt")
    with open(plain_text_path, 'w', encoding='utf-8') as f:
        f.write(output.plain_text)
    print(f"💾 Plain text saved: {plain_text_path}")
    
    # Save markdown
    markdown_path = os.path.join(output_dir, f"{base_name}_markdown.md")
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(output.markdown_text)
    print(f"💾 Markdown saved: {markdown_path}")
    
    # Save structured data as JSON
    json_path = os.path.join(output_dir, f"{base_name}_structured.json")
    structured_data = {
        "document_metadata": output.document_metadata,
        "document_structure": {
            "total_elements": output.document_structure.total_elements,
            "total_pages": output.document_structure.total_pages,
            "has_tables": output.document_structure.has_tables,
            "has_images": output.document_structure.has_images,
            "language": output.document_structure.language,
            "element_counts": output.document_structure.element_counts
        },
        "content_elements": [
            {
                "element_id": elem.element_id,
                "content_type": elem.content_type,
                "content": elem.content,
                "metadata": elem.metadata,
                "position": elem.position,
                "formatting": elem.formatting
            }
            for elem in output.content_elements
        ],
        "tables": [
            {
                "headers": table.headers,
                "rows": table.rows,
                "caption": table.caption,
                "metadata": table.metadata
            }
            for table in output.tables
        ],
        "images": [
            {
                "image_id": img.image_id,
                "file_path": img.file_path,
                "alt_text": img.alt_text,
                "caption": img.caption,
                "metadata": img.metadata
            }
            for img in output.images
        ],
        "processing_metadata": {
            "processor_name": output.processing_metadata.processor_name,
            "processor_version": output.processing_metadata.processor_version,
            "processing_duration": output.processing_metadata.processing_duration,
            "processing_parameters": output.processing_metadata.processing_parameters
        }
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Structured data saved: {json_path}")


def show_processing_summary(output):
    """Show a summary of processing results."""
    print(f"\n📊 Processing Summary:")
    print(f"   Status: {output.processing_status.value if hasattr(output.processing_status, 'value') else output.processing_status}")
    print(f"   Total pages: {output.document_structure.total_pages}")
    print(f"   Total elements: {output.document_structure.total_elements}")
    print(f"   Language: {output.document_structure.language}")
    
    # Content breakdown
    if output.document_structure.element_counts:
        print(f"\n📝 Content Breakdown:")
        for content_type, count in output.document_structure.element_counts.items():
            print(f"   {content_type}: {count}")
    
    # Tables
    if output.tables:
        print(f"\n📋 Tables Found: {len(output.tables)}")
        for i, table in enumerate(output.tables[:3]):  # Show first 3
            print(f"   Table {i+1}: {len(table.headers)} columns, {len(table.rows)} rows")
            if table.caption:
                print(f"     Caption: {table.caption}")
    
    # Images
    if output.images:
        print(f"\n🖼️  Images Found: {len(output.images)}")
        for i, image in enumerate(output.images[:3]):  # Show first 3
            print(f"   Image {i+1}: {image.image_id}")
            if image.caption:
                print(f"     Caption: {image.caption}")
    
    # Text preview
    text_preview = output.plain_text[:200] + "..." if len(output.plain_text) > 200 else output.plain_text
    print(f"\n📄 Text Preview:")
    print(f"   {text_preview}")


def main():
    """Main function to handle command line usage."""
    print("DocForge MVP - PDF Processing Test")
    print("=" * 40)
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_your_pdf.py <pdf_file> [output_directory]")
        print("\nExample:")
        print("  python3 test_your_pdf.py my_document.pdf")
        print("  python3 test_your_pdf.py my_document.pdf ./results")
        print("\nThis will process your PDF and save results to the output directory.")
        return
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = test_pdf_file(pdf_path, output_dir)
    
    if success:
        print(f"\n🎉 Success! Your PDF has been processed.")
        print(f"📁 Check the output directory for results: {output_dir or './output'}")
        print("\nFiles created:")
        print("  - *_plain.txt: Plain text extraction")
        print("  - *_markdown.md: Markdown formatted text")
        print("  - *_structured.json: Complete structured data")
    else:
        print(f"\n❌ Processing failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("  - Make sure the file is a valid PDF")
        print("  - Check that you have read permissions for the file")
        print("  - Try with a different PDF file")


if __name__ == "__main__":
    main()