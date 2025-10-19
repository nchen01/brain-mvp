#!/usr/bin/env python3
"""
DocForge MVP - Interactive PDF Testing

This script provides an interactive interface for testing PDF processing.
Just run it and follow the prompts!
"""

import sys
import os
import glob
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from docforge.preprocessing.processor_factory import ProcessorFactory


def find_pdf_files():
    """Find PDF files in the current directory."""
    pdf_files = glob.glob("*.pdf")
    return sorted(pdf_files)


def select_pdf_file():
    """Interactive PDF file selection."""
    print("🔍 Looking for PDF files in current directory...")
    pdf_files = find_pdf_files()
    
    if not pdf_files:
        print("❌ No PDF files found in current directory.")
        print("\nOptions:")
        print("1. Copy a PDF file to this directory")
        print("2. Specify full path to a PDF file")
        
        choice = input("\nEnter full path to PDF file (or press Enter to exit): ").strip()
        if not choice:
            return None
        
        if os.path.exists(choice) and choice.lower().endswith('.pdf'):
            return choice
        else:
            print(f"❌ File not found or not a PDF: {choice}")
            return None
    
    print(f"\n📁 Found {len(pdf_files)} PDF file(s):")
    for i, pdf_file in enumerate(pdf_files, 1):
        file_size = os.path.getsize(pdf_file)
        print(f"  {i}. {pdf_file} ({file_size:,} bytes)")
    
    if len(pdf_files) == 1:
        choice = input(f"\nPress Enter to process '{pdf_files[0]}' or type a number: ").strip()
        if not choice:
            return pdf_files[0]
    else:
        choice = input(f"\nSelect PDF file (1-{len(pdf_files)}): ").strip()
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(pdf_files):
            return pdf_files[index]
        else:
            print(f"❌ Invalid selection. Please choose 1-{len(pdf_files)}")
            return None
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
        return None


def configure_processor():
    """Interactive processor configuration."""
    print("\n⚙️  Processor Configuration")
    print("=" * 30)
    
    config = {}
    
    # Extract images
    choice = input("Extract images? (Y/n): ").strip().lower()
    config["extract_images"] = choice != 'n'
    
    # Extract tables
    choice = input("Extract tables? (Y/n): ").strip().lower()
    config["extract_tables"] = choice != 'n'
    
    # OCR (for scanned PDFs)
    choice = input("Enable OCR for scanned PDFs? (y/N): ").strip().lower()
    config["ocr_enabled"] = choice == 'y'
    
    # Language
    language = input("Document language (en): ").strip()
    config["language"] = language if language else "en"
    
    return config


def process_pdf_interactive(pdf_path: str, config: dict):
    """Process PDF with interactive feedback."""
    print(f"\n🔄 Processing: {pdf_path}")
    print("=" * 50)
    
    try:
        # Initialize processor
        from docforge.preprocessing.mineru_processor import MinerUProcessor
        processor = MinerUProcessor(config)
        
        # Read file
        print("📖 Reading PDF file...")
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"   File size: {len(pdf_content):,} bytes")
        
        # Process
        print("🔄 Processing with MinerU...")
        if not config.get("ocr_enabled"):
            print("   (Using mock processing - MinerU not installed)")
        
        result = processor.process_document(pdf_path, file_content=pdf_content)
        
        if result.success:
            print(f"✅ Processing completed in {result.processing_time:.2f}s")
            return result.output
        else:
            print(f"❌ Processing failed: {result.error.error_message}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def show_results_interactive(output, pdf_path: str):
    """Show results with interactive options."""
    if not output:
        return
    
    print(f"\n📊 Results Summary")
    print("=" * 30)
    print(f"Status: {output.processing_status.value if hasattr(output.processing_status, 'value') else output.processing_status}")
    print(f"Pages: {output.document_structure.total_pages}")
    print(f"Elements: {output.document_structure.total_elements}")
    print(f"Tables: {len(output.tables)}")
    print(f"Images: {len(output.images)}")
    print(f"Language: {output.document_structure.language}")
    
    # Content breakdown
    if output.document_structure.element_counts:
        print(f"\nContent Types:")
        for content_type, count in output.document_structure.element_counts.items():
            print(f"  {content_type}: {count}")
    
    # Interactive options
    while True:
        print(f"\n📋 What would you like to see?")
        print("1. Text preview")
        print("2. Markdown preview") 
        print("3. Table data")
        print("4. Image information")
        print("5. Save all results to files")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            show_text_preview(output)
        elif choice == '2':
            show_markdown_preview(output)
        elif choice == '3':
            show_table_data(output)
        elif choice == '4':
            show_image_info(output)
        elif choice == '5':
            save_results_interactive(output, pdf_path)
        elif choice == '6':
            break
        else:
            print("❌ Invalid choice. Please select 1-6.")


def show_text_preview(output):
    """Show plain text preview."""
    print(f"\n📄 Plain Text Preview")
    print("-" * 40)
    
    text = output.plain_text
    if len(text) > 500:
        print(text[:500])
        print(f"\n... (showing first 500 of {len(text)} characters)")
        
        if input("\nShow full text? (y/N): ").strip().lower() == 'y':
            print(f"\n📄 Full Text:")
            print("-" * 40)
            print(text)
    else:
        print(text)


def show_markdown_preview(output):
    """Show markdown preview."""
    print(f"\n📝 Markdown Preview")
    print("-" * 40)
    
    markdown = output.markdown_text
    if len(markdown) > 500:
        print(markdown[:500])
        print(f"\n... (showing first 500 of {len(markdown)} characters)")
        
        if input("\nShow full markdown? (y/N): ").strip().lower() == 'y':
            print(f"\n📝 Full Markdown:")
            print("-" * 40)
            print(markdown)
    else:
        print(markdown)


def show_table_data(output):
    """Show table information."""
    if not output.tables:
        print("\n📋 No tables found in document")
        return
    
    print(f"\n📋 Tables Found: {len(output.tables)}")
    print("-" * 40)
    
    for i, table in enumerate(output.tables):
        print(f"\nTable {i+1}:")
        print(f"  Columns: {len(table.headers)}")
        print(f"  Rows: {len(table.rows)}")
        
        if table.caption:
            print(f"  Caption: {table.caption}")
        
        if table.headers:
            print(f"  Headers: {', '.join(table.headers)}")
        
        if table.rows and input(f"  Show table data? (y/N): ").strip().lower() == 'y':
            print(f"\n  Data:")
            if table.headers:
                print(f"    {' | '.join(table.headers)}")
                print(f"    {' | '.join(['---'] * len(table.headers))}")
            
            for row in table.rows[:5]:  # Show first 5 rows
                print(f"    {' | '.join(str(cell) for cell in row)}")
            
            if len(table.rows) > 5:
                print(f"    ... ({len(table.rows) - 5} more rows)")


def show_image_info(output):
    """Show image information."""
    if not output.images:
        print("\n🖼️  No images found in document")
        return
    
    print(f"\n🖼️  Images Found: {len(output.images)}")
    print("-" * 40)
    
    for i, image in enumerate(output.images):
        print(f"\nImage {i+1}:")
        print(f"  ID: {image.image_id}")
        
        if image.caption:
            print(f"  Caption: {image.caption}")
        
        if image.alt_text:
            print(f"  Alt text: {image.alt_text}")
        
        if image.file_path:
            print(f"  File path: {image.file_path}")
        
        if image.metadata:
            print(f"  Metadata: {image.metadata}")


def save_results_interactive(output, pdf_path: str):
    """Save results with user confirmation."""
    base_name = Path(pdf_path).stem
    output_dir = input(f"\nOutput directory (./output): ").strip()
    if not output_dir:
        output_dir = "./output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n💾 Saving results to {output_dir}/...")
    
    # Save plain text
    plain_path = os.path.join(output_dir, f"{base_name}_text.txt")
    with open(plain_path, 'w', encoding='utf-8') as f:
        f.write(output.plain_text)
    print(f"✅ Plain text: {plain_path}")
    
    # Save markdown
    md_path = os.path.join(output_dir, f"{base_name}_markdown.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(output.markdown_text)
    print(f"✅ Markdown: {md_path}")
    
    # Save structured data
    import json
    json_path = os.path.join(output_dir, f"{base_name}_data.json")
    
    # Convert to serializable format
    data = {
        "metadata": output.document_metadata,
        "structure": {
            "total_elements": output.document_structure.total_elements,
            "total_pages": output.document_structure.total_pages,
            "has_tables": output.document_structure.has_tables,
            "has_images": output.document_structure.has_images,
            "language": output.document_structure.language
        },
        "content_elements": [
            {
                "id": elem.element_id,
                "type": elem.content_type,
                "content": elem.content,
                "metadata": elem.metadata
            }
            for elem in output.content_elements
        ],
        "tables": [
            {
                "headers": table.headers,
                "rows": table.rows,
                "caption": table.caption
            }
            for table in output.tables
        ],
        "images": [
            {
                "id": img.image_id,
                "caption": img.caption,
                "alt_text": img.alt_text,
                "file_path": img.file_path
            }
            for img in output.images
        ]
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Structured data: {json_path}")
    
    print(f"\n🎉 All results saved to {output_dir}/")


def main():
    """Main interactive function."""
    print("🚀 DocForge MVP - Interactive PDF Testing")
    print("=" * 50)
    print("This tool helps you test PDF processing with your own files.")
    print("Follow the prompts to select and process a PDF document.")
    
    # Select PDF file
    pdf_path = select_pdf_file()
    if not pdf_path:
        print("\n👋 Goodbye!")
        return
    
    print(f"\n✅ Selected: {pdf_path}")
    
    # Configure processor
    config = configure_processor()
    
    print(f"\n⚙️  Configuration:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    
    # Process PDF
    output = process_pdf_interactive(pdf_path, config)
    
    # Show results
    show_results_interactive(output, pdf_path)
    
    print(f"\n🎉 Testing complete!")
    print("Thank you for testing DocForge MVP!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n👋 Testing interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()