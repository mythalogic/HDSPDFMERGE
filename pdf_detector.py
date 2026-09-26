"""
PDF Detection and Validation Module for HDS Route Sequencer
Identifies document types and validates PDFs
"""

import os
import re
from typing import List, Tuple, Optional, Dict
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

    # Customer name patterns, per document layout.
    #
    # Picking slip pages carry a "Customer <NAME>" line, e.g.:
    #   "...R 3029 D 1\nOrder Details\nInvoice ...\nOrdered On ...\nCustomer THE FRUIT MEN\nEmail\nPhone..."
    # The same page's footer also has a "Customer Order Reference: <number>" line
    # further down - the negative lookahead below skips that one so it never gets
    # mistaken for the "Customer <NAME>" field.
    #
    # Delivery docket pages carry a "Ship to:" block with the name on the next line, e.g.:
    #   "Route No.: 3019 - 9\n...\nShip to:\nTHRIFT PARK PIES & CAKES\n171 Nepean Highway\n..."
    PICKING_SLIP_CUSTOMER_PATTERN = re.compile(
        r'Customer(?!\s*Order\b)\s*[:\-]?\s*(.+?)\s*(?=Email\b|Phone\b|Shipping\s+Address\b|'
        r'Message\s+to\s+seller\b|\r?\n|$)'
    )
    DELIVERY_DOCKET_CUSTOMER_PATTERN = re.compile(r'Ship\s+to:\s*\r?\n\s*([^\r\n]+)')

    # A "Customer" match that reduces to one of these (case-insensitive, after
    # stripping) is not a real customer name - it's page furniture (a company
    # badge, a boilerplate label, etc.) that a text-flattening regex can glue
    # onto the "Customer" label when unrelated page regions land on the same
    # extracted line. Never highlight these even if a match is found.
    _CUSTOMER_NAME_BLOCKLIST = {
        "RTR", "LAC", "RTR DISTRIBUTION", "LACTALIS", "DISTRIBUTION",
        "LACTALIS (CLAYTON VIC)", "DELIVERY", "PICKING", "N/A", "",
    }
    _MIN_CUSTOMER_NAME_LENGTH = 3

    @classmethod
    def _is_plausible_customer_name(cls, name: Optional[str]) -> bool:
        """Reject captures that are clearly page furniture, not a real name."""
        if not name:
            return False
        cleaned = name.strip()
        if len(cleaned) < cls._MIN_CUSTOMER_NAME_LENGTH:
            return False
        if cleaned.upper() in cls._CUSTOMER_NAME_BLOCKLIST:
            return False
        # A real shop/customer name has at least one letter in it.
        if not re.search(r'[A-Za-z]', cleaned):
            return False
        return True

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

    # Labels that mark the end of the customer-name run of words on a picking
    # slip's "Customer <NAME>" line.
    _PICKING_SLIP_STOP_WORDS = {"Email", "Phone", "Shipping", "Message"}
    _SAME_LINE_TOLERANCE = 3       # points of vertical wiggle to call two words "the same line"
    _MAX_WORD_GAP = 20             # points - a bigger horizontal jump means "different element"

    @classmethod
    def detect_customer_name_from_words(cls, words: List[Dict], doc_type: str) -> Optional[str]:
        """
        Locate the customer name using each word's on-page position rather than
        the flattened text string.

        Why this exists: pdfplumber's extract_text() clusters words into lines
        by vertical position and then joins them left-to-right. On a couple of
        real picking-slip pages this has glued an unrelated word from a
        different part of the page (e.g. the small "RTR" company badge) onto
        the "Customer" label ahead of the real name, so a plain regex over the
        flattened text can grab the wrong word. Working from extract_words()
        instead lets us require that every word we accept is (a) on the same
        line as the "Customer" label and (b) close enough horizontally to be
        part of the same field - a badge sitting elsewhere on the page fails
        one of those two checks and gets excluded.

        Args:
            words: pdfplumber page.extract_words() output
            doc_type: only 'PICKING_SLIP' is handled here; other types return None

        Returns: Customer name, or None if it could not be confidently located
        """
        if doc_type != "PICKING_SLIP" or not words:
            return None

        for i, word in enumerate(words):
            if word.get('text') != 'Customer':
                continue

            # Skip the "Customer Order Reference: ..." footer line
            if i + 1 < len(words) and words[i + 1].get('text') == 'Order':
                continue

            name_words = []
            prev = word
            for candidate in words[i + 1:]:
                same_line = abs(candidate['top'] - word['top']) <= cls._SAME_LINE_TOLERANCE
                close_enough = (candidate['x0'] - prev['x1']) <= cls._MAX_WORD_GAP
                if not same_line or not close_enough:
                    break
                if candidate.get('text', '').rstrip(':') in cls._PICKING_SLIP_STOP_WORDS:
                    break
                name_words.append(candidate['text'])
                prev = candidate

            if name_words:
                candidate_name = " ".join(name_words).strip()
                if cls._is_plausible_customer_name(candidate_name):
                    return candidate_name

        return None

    @classmethod
    def detect_customer_name(cls, text: str, doc_type: Optional[str] = None,
                              words: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Extract the customer/ship-to name from a page.

        Args:
            text: Extracted page text (used for the DELIVERY_DOCKET pattern,
                  and as a fallback for PICKING_SLIP if word positions aren't
                  available or don't yield a match)
            doc_type: 'PICKING_SLIP', 'DELIVERY_DOCKET', or None to try both
            words: Optional page.extract_words() output. When supplied for a
                   PICKING_SLIP page, this is tried first as it's more robust
                   against page-layout quirks than the plain-text regex.

        Returns: Cleaned customer name, or None if not found
        """
        if doc_type in (None, "PICKING_SLIP") and words:
            name = cls.detect_customer_name_from_words(words, "PICKING_SLIP")
            if name:
                return name

        if not text:
            return None

        patterns = []
        if doc_type == "PICKING_SLIP":
            patterns = [PDFDetector.PICKING_SLIP_CUSTOMER_PATTERN]
        elif doc_type == "DELIVERY_DOCKET":
            patterns = [PDFDetector.DELIVERY_DOCKET_CUSTOMER_PATTERN]
        else:
            patterns = [
                PDFDetector.PICKING_SLIP_CUSTOMER_PATTERN,
                PDFDetector.DELIVERY_DOCKET_CUSTOMER_PATTERN,
            ]

        for pattern in patterns:
            match = pattern.search(text)
            if match:
                name = match.group(1).strip()
                if cls._is_plausible_customer_name(name):
                    return name

        return None

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
