#!/usr/bin/env python3
"""
PDF page splitter utility.
Splits a multi-page PDF into individual per-page PDF files with configurable compression.

Usage:
    python split_pdf.py input.pdf [output_dir] [--dpi DPI] [--quality QUALITY]
    
Output:
    input_1.pdf, input_2.pdf, input_3.pdf, ...

Arguments:
    input.pdf       : Input PDF file path (required)
    output_dir      : Output directory for split PDF files (optional, default: same as input)

Parameters:
    --dpi DPI       : Rasterization DPI (36-300, default: 85)
    --quality QUALITY : JPEG quality (1-100, default: 20)

Examples:
    python split_pdf.py input.pdf                                  # Split to same directory
    python split_pdf.py input.pdf ./output                         # Split to ./output directory
    python split_pdf.py input.pdf ./output --dpi 100 --quality 50  # Custom compression
    python split_pdf.py input.pdf ./output --dpi 120 --quality 60  # Better quality
"""

import sys
import os
from pathlib import Path
import argparse


def _compress_pdf_page(doc, page_num, dpi=85, quality=20):
    """Compress a single PDF page by rasterizing to grayscale JPEG (configurable DPI and quality)."""
    import fitz
    
    page = doc[page_num]
    
    # Rasterize to grayscale JPEG at specified DPI and quality
    pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
    img_bytes = pix.tobytes("jpg", jpg_quality=quality)
    
    # Create new single-page PDF with the rasterized image
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
    new_page.insert_image(new_page.rect, stream=img_bytes)
    
    return new_doc


def split_pdf(pdf_path, output_dir=None, dpi=85, quality=20):
    """Split a multi-page PDF into individual per-page PDF files with compression."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF not installed. Install with: pip install pymupdf")
        return False
    
    # Validate DPI and quality
    if dpi < 36 or dpi > 300:
        print(f"ERROR: DPI must be between 36 and 300 (got {dpi})")
        return False
    if quality < 1 or quality > 100:
        print(f"ERROR: Quality must be between 1 and 100 (got {quality})")
        return False
    
    # Validate input
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        return False
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"ERROR: File is not a PDF: {pdf_path}")
        return False
    
    # Set output directory (use provided or default to input directory)
    if output_dir is None:
        output_dir = pdf_path.parent
    else:
        output_dir = Path(output_dir)
        # Create output directory if it doesn't exist
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Failed to create output directory '{output_dir}': {e}")
            return False
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"ERROR: Failed to open PDF: {e}")
        return False
    
    page_count = len(doc)
    if page_count == 0:
        print("ERROR: PDF has no pages")
        doc.close()
        return False
    
    print(f"Processing: {pdf_path}")
    print(f"Total pages: {page_count}")
    print(f"Compression: DPI {dpi}, Quality {quality}")
    print(f"Output: {output_dir}")
    
    # Calculate original size
    original_size = pdf_path.stat().st_size
    print(f"Original size: {original_size / 1024 / 1024:.2f} MB")
    
    base_name = pdf_path.stem  # filename without extension
    
    created_files = []
    total_compressed_size = 0
    
    try:
        for page_num in range(page_count):
            # Compress page by rasterizing to JPEG
            new_doc = _compress_pdf_page(doc, page_num, dpi=dpi, quality=quality)
            
            # Output filename
            output_name = f"{base_name}_{page_num + 1}.pdf"
            output_path = output_dir / output_name
            
            # Save with compression
            new_doc.save(output_path, garbage=4, deflate=True)
            new_doc.close()
            
            file_size = output_path.stat().st_size
            total_compressed_size += file_size
            created_files.append(output_path)
            print(f"  ✓ Created: {output_name} ({file_size / 1024:.1f} KB)")
    
    except Exception as e:
        print(f"ERROR: Failed to split PDF: {e}")
        doc.close()
        return False
    
    doc.close()
    
    # Summary
    saved = original_size - total_compressed_size
    saved_pct = (saved / original_size * 100) if original_size > 0 else 0
    print(f"\nSuccess: {len(created_files)} files created")
    print(f"Total size: {total_compressed_size / 1024 / 1024:.2f} MB")
    print(f"Space saved: {saved / 1024 / 1024:.2f} MB ({saved_pct:.1f}%)")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Split multi-page PDF into individual per-page PDF files with configurable compression.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python split_pdf.py input.pdf                                  # Split to input directory
  python split_pdf.py input.pdf ./output                         # Split to ./output directory
  python split_pdf.py input.pdf ./output --dpi 100 --quality 50  # Custom compression to output dir
  python split_pdf.py input.pdf -d 150 -q 80                     # High quality to input directory
  python split_pdf.py input.pdf ./split -d 120 -q 60             # High quality to split directory
        """
    )
    parser.add_argument("input", help="Input PDF file path")
    parser.add_argument(
        "output",
        nargs='?',
        default=None,
        help="Output directory for split PDFs (optional, default: same as input)",
    )
    parser.add_argument(
        "--dpi",
        "-d",
        type=int,
        default=50,
        help="DPI for rasterization (36-300, default: 50)",
    )
    parser.add_argument(
        "--quality",
        "-q",
        type=int,
        default=20,
        help="JPEG quality (1-100, default: 20)",
    )
    
    args = parser.parse_args()
    success = split_pdf(args.input, output_dir=args.output, dpi=args.dpi, quality=args.quality)
    sys.exit(0 if success else 1)
