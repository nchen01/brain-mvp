#!/usr/bin/env python3
"""
Example: PDF Processing with MinerU in DocForge MVP

This example demonstrates how to use the MinerU processor for PDF document processing.
It shows both the mock implementation (for development) and how to integrate with real MinerU.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.mineru_processor import MinerUProcessor
from docforge.preprocessing.processor_factory import ProcessorFactory
from docforge.preprocessing.schemas import ProcessingStatus


def demonstrate_mineru_processor():
    """Demonstrate MinerU processor capabilities."""
    print("DocForge MVP - MinerU PDF Processing Demo")
    print("=" * 50)
    
    # Initialize MinerU processor with configuration
    config = {
        "extract_images": True,
        "extract_tables": True,
        "ocr_enabled": False,  # Disable OCR for faster processing in demo
        "language": "en",
        "output_dir": "./temp/mineru_output"
    }
    
    processor = MinerUProcessor(config)
    
    print(f"Processor: {processor.processor_name} v{processor.processor_version}")
    print(f"Supported formats: {processor.get_supported_formats()}")
    print(f"Configuration: {config}")
    print()
    
    # Validate configuration
    errors = processor.validate_config()
    if errors:
        print(f"Configuration errors: {errors}")
        return
    else:
        print("✓ Configuration is valid")
    
    # Create mock PDF content for demonstration
    mock_pdf_content = create_mock_pdf_content()
    
    print(f"\n📄 Processing mock PDF document...")
    print(f"PDF size: {len(mock_pdf_content)} bytes")
    
    try:
        # Process the PDF
        result = processor.process_document(
            "sample_document.pdf",
            file_content=mock_pdf_content
        )
        
        if result.success:
            print(f"✓ Processing completed successfully in {result.processing_time:.3f}s")
            
            output = result.output
            print(f"\n📊 Processing Results:")
            status_value = output.processing_status.value if hasattr(output.processing_status, 'value') else str(output.processing_status)
            print(f"  Status: {status_value}")
            print(f"  Total elements: {output.document_structure.total_elements}")
            print(f"  Total pages: {output.document_structure.total_pages}")
            print(f"  Has tables: {output.document_structure.has_tables}")
            print(f"  Has images: {output.document_structure.has_images}")
            print(f"  Language: {output.document_structure.language}")
            
            # Show content elements
            print(f"\n📝 Content Elements ({len(output.content_elements)} found):")
            for i, element in enumerate(output.content_elements[:3]):  # Show first 3
                content_type = element.content_type.value if hasattr(element.content_type, 'value') else str(element.content_type)
                print(f"  {i+1}. [{content_type}] {element.content[:60]}...")
            
            if len(output.content_elements) > 3:
                print(f"  ... and {len(output.content_elements) - 3} more elements")
            
            # Show tables
            if output.tables:
                print(f"\n📋 Tables ({len(output.tables)} found):")
                for i, table in enumerate(output.tables):
                    print(f"  Table {i+1}: {len(table.headers)} columns, {len(table.rows)} rows")
                    if table.caption:
                        print(f"    Caption: {table.caption}")
                    
                    # Show table preview
                    if table.headers:
                        print(f"    Headers: {', '.join(table.headers[:3])}{'...' if len(table.headers) > 3 else ''}")
                    if table.rows:
                        first_row = table.rows[0]
                        print(f"    First row: {', '.join(str(cell)[:20] for cell in first_row[:3])}{'...' if len(first_row) > 3 else ''}")
            
            # Show images
            if output.images:
                print(f"\n🖼️  Images ({len(output.images)} found):")
                for i, image in enumerate(output.images):
                    print(f"  Image {i+1}: {image.image_id}")
                    if image.caption:
                        print(f"    Caption: {image.caption}")
                    if image.file_path:
                        print(f"    Path: {image.file_path}")
            
            # Show text previews
            print(f"\n📄 Plain Text Preview (first 200 chars):")
            plain_preview = output.plain_text[:200] + "..." if len(output.plain_text) > 200 else output.plain_text
            print(f"  {plain_preview}")
            
            print(f"\n📝 Markdown Preview (first 300 chars):")
            markdown_preview = output.markdown_text[:300] + "..." if len(output.markdown_text) > 300 else output.markdown_text
            print(f"  {markdown_preview}")
            
            # Show processing metadata
            print(f"\n⚙️  Processing Metadata:")
            metadata = output.processing_metadata
            print(f"  Processor: {metadata.processor_name} v{metadata.processor_version}")
            print(f"  Processing time: {metadata.processing_duration:.3f}s")
            print(f"  Parameters: {metadata.processing_parameters}")
            
        else:
            print(f"✗ Processing failed: {result.error.error_message}")
            print(f"  Error type: {result.error.error_type}")
            
    except Exception as e:
        print(f"✗ Error during processing: {e}")


def demonstrate_processor_factory():
    """Demonstrate using MinerU through the processor factory."""
    print("\n" + "=" * 50)
    print("Processor Factory Demo")
    print("=" * 50)
    
    factory = ProcessorFactory()
    
    # Show factory statistics
    stats = factory.get_processing_statistics()
    print(f"Available processors: {stats['processors']}")
    print(f"Total processors: {stats['total_processors']}")
    
    # Test file support
    test_files = [
        "document.pdf",
        "report.docx", 
        "data.xlsx",
        "slides.pptx",
        "readme.txt"
    ]
    
    print(f"\n📁 File Support Check:")
    for filename in test_files:
        supported = factory.is_file_supported(filename)
        processor = factory.get_processor_for_file(filename)
        
        if filename.endswith('.pdf'):
            status = "✓ Supported (MVP)"
        else:
            status = "✗ Not supported (MVP limitation - future release)"
        
        processor_name = processor.processor_name if processor else "None (MVP limitation)"
        print(f"  {filename:<15} {status:<40} Processor: {processor_name}")
    
    # Get routing decision for PDF
    pdf_file = "sample_document.pdf"
    routing = factory.get_routing_decision(pdf_file)
    print(f"\n🔀 Routing Decision for {pdf_file}:")
    print(f"  File category: {routing['file_category']}")
    print(f"  Processor type: {routing['processor_type']}")
    print(f"  Can process: {routing['can_process']}")
    print(f"  Confidence: {routing['routing_confidence']:.2f}")


def create_mock_pdf_content() -> bytes:
    """Create mock PDF content for demonstration."""
    # This creates a minimal PDF-like byte sequence for testing
    pdf_header = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'
    
    # Add some mock content
    mock_content = (
        b'1 0 obj\n'
        b'<<\n'
        b'/Type /Catalog\n'
        b'/Pages 2 0 R\n'
        b'>>\n'
        b'endobj\n'
        b'2 0 obj\n'
        b'<<\n'
        b'/Type /Pages\n'
        b'/Kids [3 0 R]\n'
        b'/Count 1\n'
        b'>>\n'
        b'endobj\n'
        b'3 0 obj\n'
        b'<<\n'
        b'/Type /Page\n'
        b'/Parent 2 0 R\n'
        b'/MediaBox [0 0 612 792]\n'
        b'>>\n'
        b'endobj\n'
    )
    
    # Add trailer
    trailer = (
        b'xref\n'
        b'0 4\n'
        b'0000000000 65535 f \n'
        b'0000000009 00000 n \n'
        b'0000000074 00000 n \n'
        b'0000000120 00000 n \n'
        b'trailer\n'
        b'<<\n'
        b'/Size 4\n'
        b'/Root 1 0 R\n'
        b'>>\n'
        b'startxref\n'
        b'199\n'
        b'%%EOF\n'
    )
    
    return pdf_header + mock_content + trailer


def show_installation_info():
    """Show information about MinerU installation."""
    print("\n" + "=" * 50)
    print("MinerU Installation Information")
    print("=" * 50)
    
    print("Current Status: Using mock implementation (MinerU not installed)")
    print()
    print("To install MinerU for real PDF processing:")
    print("1. Run the installation script: ./scripts/install_mineru.sh")
    print("2. Or install manually:")
    print("   pip install magic-pdf>=0.7.0")
    print("   pip install Pillow pandas numpy")
    print()
    print("System Requirements:")
    print("- Python 3.8+")
    print("- Linux: libgl1-mesa-glx libglib2.0-0")
    print("- macOS: OpenCV (brew install opencv)")
    print("- Windows: Visual C++ redistributables")
    print()
    print("For more information:")
    print("- GitHub: https://github.com/opendatalab/MinerU")
    print("- Documentation: Check the repository for detailed setup instructions")


def main():
    """Main demonstration function."""
    try:
        demonstrate_mineru_processor()
        demonstrate_processor_factory()
        show_installation_info()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()