"""
PDF Merger Module for HDS Route Sequencer
Handles PDF merging and file output operations
"""

import os
from typing import List, Tuple, Optional
from datetime import datetime

try:
    from PyPDF2 import PdfWriter, PdfReader
except ImportError:
    raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")

from models import PageInfo, ProcessingResult, ValidationReport
from route_sequencer import RouteSequencer, RoutePreview
from logger import get_logger


class PDFMerger:
    """Merges and sequences PDF files"""
    
    @staticmethod
    def merge_pages(pages: List[PageInfo], output_path: str, label: str = "Document") -> Tuple[bool, str]:
        """
        Merge pages into a single PDF file
        
        Args:
            pages: List of PageInfo objects to merge (should be pre-sequenced)
            output_path: Output PDF file path
            label: Label for logging
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger = get_logger()
        logger.separator(f"MERGING {label}", char="=")
        
        try:
            # Create writer
            writer = PdfWriter()
            pdf_readers = {}
            pages_added = 0
            
            # Map of PDF file paths that have already been opened
            pdf_file_map = {}
            
            # First pass: map source files to full paths
            for page in pages:
                if 'pdf_file' not in page.__dict__:
                    # Need to find the actual file path
                    # This is a limitation of current design - PageInfo doesn't store full path
                    logger.warning(f"PageInfo missing pdf_file attribute for {page.source_file}")
            
            # Add each page
            for idx, page in enumerate(pages, 1):
                try:
                    # Get PDF file path from page data
                    if hasattr(page, 'pdf_file'):
                        pdf_file = page.pdf_file
                    else:
                        # Try to infer from source_file (this is a fallback)
                        logger.error(f"Cannot determine PDF file for page {idx}")
                        continue
                    
                    page_num = page.page_num
                    
                    # Load PDF reader if not cached
                    if pdf_file not in pdf_readers:
                        pdf_readers[pdf_file] = PdfReader(pdf_file)
                    
                    reader = pdf_readers[pdf_file]
                    
                    # Validate page number
                    if page_num < 0 or page_num >= len(reader.pages):
                        logger.error(f"Invalid page number {page_num} for {page.source_file}")
                        continue
                    
                    # Add page to writer
                    pdf_page = reader.pages[page_num]
                    writer.add_page(pdf_page)
                    pages_added += 1
                    
                    # Log
                    if page.route is not None and page.delivery is not None:
                        marker = " (continuation)" if page.is_continuation else ""
                        logger.info(f"✓ Page {idx:3d}: Route {page.route:4d} - Delivery {page.delivery:2d} "
                                  f"({page.source_file}){marker}")
                    else:
                        logger.info(f"✓ Page {idx:3d}: Orphan page ({page.source_file})")
                
                except Exception as e:
                    logger.error(f"Failed to add page {idx}: {e}")
                    continue
            
            # Write output file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            # Get file stats
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            filename = os.path.basename(output_path)
            
            logger.info(f"\n✓ Successfully merged {pages_added} pages")
            logger.info(f"  Output: {filename}")
            logger.info(f"  Size: {file_size_mb:.2f} MB")
            logger.separator()
            
            return True, f"{filename} ({pages_added} pages, {file_size_mb:.2f} MB)"
        
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            logger.separator()
            return False, f"Merge failed: {str(e)}"


class PDFProcessor:
    """Processes PDF collections with full pipeline"""
    
    @staticmethod
    def process_pdfs(pdf_files: List[str], doc_type: str, output_folder: str) -> ProcessingResult:
        """
        Complete pipeline: extract → sequence → validate → merge
        
        Args:
            pdf_files: List of PDF file paths
            doc_type: 'PICKING_SLIP' or 'DELIVERY_DOCKET'
            output_folder: Output folder for merged PDF
            
        Returns:
            ProcessingResult with outcome
        """
        logger = get_logger()
        result = ProcessingResult(
            success=False,
            document_type=doc_type,
            file_count=len(pdf_files)
        )
        
        try:
            logger.separator(f"PROCESSING {doc_type}S", char="=")
            logger.info(f"Processing {len(pdf_files)} file(s)")
            
            # Step 1: Extract pages from all PDFs
            logger.info("\n[STEP 1] Extracting pages...")
            all_pages = []
            pdf_to_pages = {}
            
            for pdf_file in pdf_files:
                try:
                    pages = RouteSequencer.extract_pages(pdf_file, doc_type)
                    all_pages.extend(pages)
                    pdf_to_pages[pdf_file] = pages
                    logger.info(f"  ✓ {os.path.basename(pdf_file)}: {len(pages)} pages")
                except Exception as e:
                    logger.error(f"  ✗ {os.path.basename(pdf_file)}: {e}")
                    result.warnings.append(f"Failed to extract {os.path.basename(pdf_file)}: {e}")
            
            if not all_pages:
                result.error_message = "No pages extracted from any file"
                return result
            
            logger.info(f"  Total: {len(all_pages)} pages")
            
            # Step 2: Sequence pages
            logger.info("\n[STEP 2] Sequencing pages...")
            sequenced_pages = RouteSequencer.sequence_pages(all_pages)
            logger.info(f"  ✓ Pages sequenced")
            
            # Step 3: Validate
            logger.info("\n[STEP 3] Validating...")
            validation = RouteSequencer.validate_pages(sequenced_pages)
            result.validation_report = validation
            
            logger.info(f"  ✓ Total main pages: {validation.main_pages}")
            logger.info(f"  ✓ Total continuation pages: {validation.continuation_pages}")
            logger.info(f"  ✓ Routes detected: {len(validation.routes)}")
            
            if validation.duplicates:
                logger.warning(f"  ⚠️  Duplicates: {len(validation.duplicates)}")
                for dup in validation.duplicates:
                    logger.warning(f"     Route {dup['route']} - Delivery {dup['delivery']}: "
                                 f"{dup['count']} occurrences")
                    result.warnings.append(f"Route {dup['route']}-Delivery {dup['delivery']}: "
                                        f"Found {dup['count']} times in {', '.join(dup['files'])}")
            
            if validation.missing_drops:
                logger.warning(f"  ⚠️  Missing deliveries: {len(validation.missing_drops)}")
                for miss in validation.missing_drops:
                    logger.warning(f"     Route {miss['route']} - Delivery {miss['delivery']}: NOT FOUND")
                    result.warnings.append(f"Route {miss['route']}-Delivery {miss['delivery']}: MISSING")
            
            # Step 4: Merge PDFs
            logger.info("\n[STEP 4] Merging PDFs...")
            
            # Add pdf_file attribute to pages
            for page in sequenced_pages:
                # Find which PDF file this page came from
                for pdf_file, pages_from_file in pdf_to_pages.items():
                    if page in pages_from_file:
                        page.pdf_file = pdf_file
                        break
            
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if doc_type == "PICKING_SLIP":
                output_filename = f"Picking_Slips_Sequenced_{timestamp}.pdf"
            else:
                output_filename = f"Delivery_Dockets_Sequenced_{timestamp}.pdf"
            
            output_path = os.path.join(output_folder, output_filename)
            
            success, message = PDFMerger.merge_pages(sequenced_pages, output_path, doc_type)
            
            if success:
                result.success = True
                result.pages_merged = sum(1 for p in sequenced_pages if not p.is_continuation and p.route is not None)
                result.routes_detected = validation.routes
                result.output_file = output_path
                logger.info(f"\n✓ Processing complete: {output_filename}")
            else:
                result.error_message = message
                logger.error(f"\n✗ Processing failed: {message}")
            
            logger.separator()
            
            return result
        
        except Exception as e:
            logger.error(f"Processing failed with exception: {e}")
            result.error_message = str(e)
            logger.separator()
            return result
