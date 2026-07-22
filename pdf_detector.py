"""
PDF Detection and Validation Module for HDS Route Sequencer
Identifies document types and validates PDFs
"""

import os
import re
from typing import List, Tuple, Optional
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")

from models import DocumentType, CompanyType, PageInfo, PDFFileInfo
from logger import get_logger


class PDFDetector:
    """Detects and validates PDF document types"""
    
    # Patterns for document detection
    PICKING_SLIP_PATTERNS = [
        r'R\s+(\d+)\s+D\s+(\d+)',  # Format: R 3001 D 2
        r'Route\s+(\d+)\s+Delivery\s+(\d+)',
        r'PICK\s+SLIP',
        r'PICKING\s+SHEET',
    ]
    
    DELIVERY_DOCKET_PATTERNS = [
        r'Route\s+No\.:\s+(\d+)\s+-\s+(\d+)',  # Format: Route No.: 3001 - 2
        r'Route\s+No\.\s+(\d+)\s*-\s*(\d+)',
        r'DELIVERY\s+DOCKET',
        r'DELIVERY\s+SHEET',
    ]
    
    COMPANY_PATTERNS = {
        'LAC': [r'LACTALIS', r'LAC\s+DELIVERY', r'LAC\s+PICKING'],
        'RTR': [r'RTR\s+DISTRIBUTION', r'RTR\s+DELIVERY', r'RTR\s+PICKING'],
    }
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str, page_limit: int = 5) -> List[str]:
        """
        Extract text from first N pages of PDF
        
        Args:
            pdf_path: Path to PDF file
            page_limit: Maximum pages to extract
            
        Returns:
            List of text from each page
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texts = []
                for page in pdf.pages[:page_limit]:
                    text = page.extract_text()
                    texts.append(text if text else "")
                return texts
        except Exception as e:
            get_logger().error(f"Failed to extract text from {os.path.basename(pdf_path)}: {e}")
            return []
    
    @staticmethod
    def detect_company_type(text: str) -> str:
        """
        Detect company type from text
        
        Returns: 'LAC', 'RTR', or 'UNKNOWN'
        """
        if not text:
            return "UNKNOWN"
        
        text_upper = text.upper()
        
        for company, patterns in PDFDetector.COMPANY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    return company
        
        return "UNKNOWN"
    
    @staticmethod
    def detect_picking_slip_markers(text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract route and delivery from picking slip text
        
        Returns: (route_number, delivery_number) or (None, None)
        """
        if not text:
            return None, None
        
        for pattern in PDFDetector.PICKING_SLIP_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    route = int(match.group(1))
                    delivery = int(match.group(2))
                    return route, delivery
                except (ValueError, IndexError):
                    continue
        
        return None, None
    
    @staticmethod
    def detect_delivery_docket_markers(text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract route and delivery from delivery docket text
        
        Returns: (route_number, delivery_number) or (None, None)
        """
        if not text:
            return None, None
        
        for pattern in PDFDetector.DELIVERY_DOCKET_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    route = int(match.group(1))
                    delivery = int(match.group(2))
                    return route, delivery
                except (ValueError, IndexError):
                    continue
        
        return None, None
    
    @classmethod
    def detect_pdf_type(cls, pdf_path: str) -> str:
        """
        Detect whether PDF is PICKING_SLIP, DELIVERY_DOCKET, or UNKNOWN
        
        Scans first few pages and looks for characteristic patterns
        """
        logger = get_logger()
        
        try:
            texts = cls.extract_text_from_pdf(pdf_path)
            
            if not texts:
                logger.debug(f"No text extracted from {os.path.basename(pdf_path)}")
                return "UNKNOWN"
            
            picking_slip_score = 0
            delivery_docket_score = 0
            
            for text in texts:
                # Check for picking slip indicators
                if re.search(r'R\s+\d+\s+D\s+\d+', text):
                    picking_slip_score += 2
                if re.search(r'PICK(?:ING)?\s+SLIP|PICKING\s+SHEET', text, re.IGNORECASE):
                    picking_slip_score += 3
                
                # Check for delivery docket indicators
                if re.search(r'Route\s+No\.:\s+\d+\s+-\s+\d+', text):
                    delivery_docket_score += 2
                if re.search(r'DELIVERY\s+(?:DOCKET|SHEET)', text, re.IGNORECASE):
                    delivery_docket_score += 3
                
                # If one score is clear winner, can return early
                if picking_slip_score >= 5:
                    return "PICKING_SLIP"
                if delivery_docket_score >= 5:
                    return "DELIVERY_DOCKET"
            
            # Return based on final scores
            if picking_slip_score > delivery_docket_score and picking_slip_score > 0:
                return "PICKING_SLIP"
            elif delivery_docket_score > picking_slip_score and delivery_docket_score > 0:
                return "DELIVERY_DOCKET"
            else:
                return "UNKNOWN"
        
        except Exception as e:
            logger.error(f"Failed to detect PDF type for {os.path.basename(pdf_path)}: {e}")
            return "UNKNOWN"
    
    @classmethod
    def validate_pdf_file(cls, pdf_path: str, expected_type: Optional[str] = None) -> PDFFileInfo:
        """
        Validate a PDF file
        
        Args:
            pdf_path: Path to PDF file
            expected_type: Expected document type ('PICKING_SLIP', 'DELIVERY_DOCKET', or None for any)
            
        Returns:
            PDFFileInfo with validation results
        """
        logger = get_logger()
        file_info = PDFFileInfo(
            file_path=pdf_path,
            file_name=os.path.basename(pdf_path)
        )
        
        # Check if file exists
        if not os.path.isfile(pdf_path):
            file_info.error_message = "File does not exist"
            return file_info
        
        # Check if it's a PDF
        if not pdf_path.lower().endswith('.pdf'):
            file_info.error_message = "File is not a PDF"
            return file_info
        
        try:
            # Get page count
            with pdfplumber.open(pdf_path) as pdf:
                file_info.page_count = len(pdf.pages)
            
            # Detect document type
            detected_type = cls.detect_pdf_type(pdf_path)
            file_info.document_type = detected_type
            
            # Extract text to find company and routes
            texts = cls.extract_text_from_pdf(pdf_path)
            
            if texts:
                combined_text = " ".join(texts)
                file_info.company_type = cls.detect_company_type(combined_text)
                
                # Extract routes
                routes = set()
                for text in texts:
                    if detected_type == "PICKING_SLIP":
                        route, delivery = cls.detect_picking_slip_markers(text)
                    else:
                        route, delivery = cls.detect_delivery_docket_markers(text)
                    
                    if route:
                        routes.add(route)
                
                file_info.routes_detected = sorted(list(routes))
            
            # Validate against expected type
            if expected_type and detected_type != expected_type:
                file_info.error_message = f"Expected {expected_type} but found {detected_type}"
                file_info.is_valid = False
            else:
                file_info.is_valid = detected_type != "UNKNOWN"
                if not file_info.is_valid:
                    file_info.error_message = "Could not identify document type"
        
        except Exception as e:
            file_info.error_message = f"Failed to validate: {str(e)}"
            logger.error(f"Validation error for {file_info.file_name}: {e}")
        
        return file_info
    
    @classmethod
    def validate_pdf_files(cls, pdf_paths: List[str], expected_type: Optional[str] = None) -> List[PDFFileInfo]:
        """
        Validate multiple PDF files
        
        Args:
            pdf_paths: List of PDF file paths
            expected_type: Expected document type for all files
            
        Returns:
            List of PDFFileInfo objects
        """
        results = []
        for pdf_path in pdf_paths:
            results.append(cls.validate_pdf_file(pdf_path, expected_type))
        return results


class PDFValidator:
    """Validates PDF file collections for processing"""
    
    @staticmethod
    def validate_file_collection(pdf_files: List[str], mode: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate collection of PDF files for a specific mode
        
        Args:
            pdf_files: List of PDF file paths
            mode: Processing mode ('PICKING_SLIP' or 'DELIVERY_DOCKET')
            
        Returns:
            Tuple of (all_valid: bool, valid_files: List[str], error_messages: List[str])
        """
        logger = get_logger()
        valid_files = []
        error_messages = []
        
        logger.debug(f"Validating {len(pdf_files)} files for mode: {mode}")
        
        file_infos = PDFDetector.validate_pdf_files(pdf_files, mode)
        
        for file_info in file_infos:
            if file_info.is_valid:
                valid_files.append(file_info.file_path)
                logger.debug(f"✓ Valid: {file_info.file_name} ({file_info.document_type})")
            else:
                error_msg = file_info.error_message or f"Invalid file: {file_info.file_name}"
                error_messages.append(f"{file_info.file_name}: {error_msg}")
                logger.warning(f"✗ Invalid: {file_info.file_name} - {error_msg}")
        
        all_valid = len(error_messages) == 0
        
        return all_valid, valid_files, error_messages
