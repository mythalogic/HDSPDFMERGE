"""
Route Sequencer Module for HDS Route Sequencer
Extracts and sequences route and delivery information from PDFs
"""

import os
import re
from typing import List, Dict, Optional
from collections import defaultdict

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")

from models import PageInfo, RouteInfo, ValidationReport
from pdf_detector import PDFDetector
from logger import get_logger


class RouteSequencer:
    """Extracts and sequences route/delivery information from PDFs"""
    
    @staticmethod
    def extract_picking_slip_pages(pdf_path: str) -> List[PageInfo]:
        """
        Extract page information from picking slip PDF
        
        Pattern: R 3001 D 2 (route and delivery numbers)
        
        Logic:
        1. Pages with "R XXXX D YY" are main pages
        2. Pages without pattern are continuation pages (assigned to last known route/delivery)
        3. Returns all pages with route/delivery info
        """
        logger = get_logger()
        pages_info = []
        last_route = None
        last_delivery = None
        last_company = "UNKNOWN"
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # Update company if found
                    company = PDFDetector.detect_company_type(text)
                    if company != "UNKNOWN":
                        last_company = company
                    
                    # Try to extract route and delivery
                    route_num, delivery_num = PDFDetector.detect_picking_slip_markers(text)
                    
                    is_continuation = False
                    if route_num is None:
                        # This is a continuation page
                        is_continuation = True
                        route_num = last_route
                        delivery_num = last_delivery
                    else:
                        # Update last known values
                        last_route = route_num
                        last_delivery = delivery_num
                    
                    pages_info.append(PageInfo(
                        page_num=page_num,
                        source_file=os.path.basename(pdf_path),
                        route=route_num,
                        delivery=delivery_num,
                        company=last_company,
                        doc_type="PICKING_SLIP",
                        is_continuation=is_continuation,
                        text=text[:100] if text else ""
                    ))
        
        except Exception as e:
            logger.error(f"Failed to extract picking slip pages from {os.path.basename(pdf_path)}: {e}")
        
        return pages_info
    
    @staticmethod
    def extract_delivery_docket_pages(pdf_path: str) -> List[PageInfo]:
        """
        Extract page information from delivery docket PDF
        
        Pattern: Route No.: 3001 - 2 (route and delivery numbers)
        
        Logic:
        1. Pages with "Route No.: XXXX - YY" are main pages
        2. Pages without pattern are continuation pages (assigned to last known route/delivery)
        3. Returns all pages with route/delivery info
        """
        logger = get_logger()
        pages_info = []
        last_route = None
        last_delivery = None
        last_company = "UNKNOWN"
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # Update company if found
                    company = PDFDetector.detect_company_type(text)
                    if company != "UNKNOWN":
                        last_company = company
                    
                    # Try to extract route and delivery
                    route_num, delivery_num = PDFDetector.detect_delivery_docket_markers(text)
                    
                    is_continuation = False
                    if route_num is None:
                        # This is a continuation page
                        is_continuation = True
                        route_num = last_route
                        delivery_num = last_delivery
                    else:
                        # Update last known values
                        last_route = route_num
                        last_delivery = delivery_num
                    
                    pages_info.append(PageInfo(
                        page_num=page_num,
                        source_file=os.path.basename(pdf_path),
                        route=route_num,
                        delivery=delivery_num,
                        company=last_company,
                        doc_type="DELIVERY_DOCKET",
                        is_continuation=is_continuation,
                        text=text[:100] if text else ""
                    ))
        
        except Exception as e:
            logger.error(f"Failed to extract delivery docket pages from {os.path.basename(pdf_path)}: {e}")
        
        return pages_info
    
    @staticmethod
    def extract_pages(pdf_path: str, doc_type: Optional[str] = None) -> List[PageInfo]:
        """
        Extract pages from PDF (auto-detects type if not specified)
        
        Args:
            pdf_path: Path to PDF file
            doc_type: Document type ('PICKING_SLIP', 'DELIVERY_DOCKET', or None for auto-detect)
            
        Returns:
            List of PageInfo objects
        """
        logger = get_logger()
        
        # Auto-detect if not specified
        if doc_type is None:
            detected_type = PDFDetector.detect_pdf_type(pdf_path)
            logger.debug(f"Auto-detected {os.path.basename(pdf_path)} as {detected_type}")
        else:
            detected_type = doc_type
        
        if detected_type == "PICKING_SLIP":
            return RouteSequencer.extract_picking_slip_pages(pdf_path)
        elif detected_type == "DELIVERY_DOCKET":
            return RouteSequencer.extract_delivery_docket_pages(pdf_path)
        else:
            logger.warning(f"Could not determine document type for {os.path.basename(pdf_path)}")
            return []
    
    @staticmethod
    def sequence_pages(pages: List[PageInfo]) -> List[PageInfo]:
        """
        Sequence pages by route and delivery number
        
        Sorting order:
        1. Route number (ascending)
        2. Delivery number (ascending)
        3. Original order within same route/delivery (for duplicates)
        
        Note: ALL pages are kept, including duplicates
        """
        logger = get_logger()
        
        # Separate main and continuation pages
        main_pages = [p for p in pages if not p.is_continuation and p.route is not None]
        continuation_pages = [p for p in pages if p.is_continuation]
        orphan_pages = [p for p in pages if not p.is_continuation and p.route is None]
        
        logger.debug(f"Sequencing: {len(main_pages)} main, "
                    f"{len(continuation_pages)} continuation, {len(orphan_pages)} orphan")
        
        # Sort main pages by route and delivery (keeps duplicates in order)
        main_pages.sort(key=lambda x: (x.route or 0, x.delivery or 0))
        
        # Group pages: each main page followed by its continuation pages
        sequenced = []
        used_continuations = set()
        
        for main_page in main_pages:
            sequenced.append(main_page)
            
            # Add continuation pages for this route/delivery (only once)
            for idx, cont_page in enumerate(continuation_pages):
                if idx not in used_continuations and \
                   cont_page.route == main_page.route and \
                   cont_page.delivery == main_page.delivery:
                    sequenced.append(cont_page)
                    used_continuations.add(idx)
        
        # Add remaining continuation pages
        for idx, cont_page in enumerate(continuation_pages):
            if idx not in used_continuations:
                sequenced.append(cont_page)
        
        # Add orphan pages
        sequenced.extend(orphan_pages)
        
        return sequenced
    
    @staticmethod
    def get_route_summary(pages: List[PageInfo]) -> Dict[int, RouteInfo]:
        """
        Build summary of routes and deliveries from pages
        
        Returns: Dict mapping route number to RouteInfo
        """
        logger = get_logger()
        routes = {}
        
        # Filter to main pages only
        main_pages = [p for p in pages if not p.is_continuation and p.route is not None]
        
        for page in main_pages:
            route_num = page.route
            delivery_num = page.delivery
            
            if route_num not in routes:
                routes[route_num] = RouteInfo(route_number=route_num)
            
            routes[route_num].add_delivery(delivery_num, page.source_file)
        
        # Analyze each route for duplicates and missing
        for route_info in routes.values():
            route_info.detect_duplicates_and_missing()
        
        logger.debug(f"Route summary: {len(routes)} unique routes")
        
        return routes
    
    @staticmethod
    def validate_pages(pages: List[PageInfo]) -> ValidationReport:
        """
        Validate pages for duplicates and missing deliveries
        
        Returns: ValidationReport with findings
        """
        logger = get_logger()
        report = ValidationReport()
        
        # Count pages
        report.total_pages = len(pages)
        report.main_pages = sum(1 for p in pages if not p.is_continuation and p.route is not None)
        report.continuation_pages = sum(1 for p in pages if p.is_continuation)
        
        # Get route summary
        routes = RouteSequencer.get_route_summary(pages)
        report.routes = sorted(list(routes.keys()))
        
        # Build route info
        for route_num, route_info in routes.items():
            if route_info.deliveries:
                report.delivery_range[route_num] = (min(route_info.deliveries), max(route_info.deliveries))
                
                # Find duplicates
                from collections import Counter
                counts = Counter()
                for page in pages:
                    if not page.is_continuation and page.route == route_num:
                        counts[(page.route, page.delivery)] += 1
                
                for (route, delivery), count in counts.items():
                    if count > 1:
                        # Find which files have duplicates
                        files_with_dup = []
                        for page in pages:
                            if not page.is_continuation and page.route == route and page.delivery == delivery:
                                files_with_dup.append(page.source_file)
                        
                        report.duplicates.append({
                            'route': route,
                            'delivery': delivery,
                            'count': count,
                            'files': files_with_dup
                        })
                
                # Find missing
                if route_info.missing_deliveries:
                    for delivery in route_info.missing_deliveries:
                        report.missing_drops.append({
                            'route': route_num,
                            'delivery': delivery
                        })
        
        report.has_issues = len(report.duplicates) > 0 or len(report.missing_drops) > 0
        
        logger.debug(f"Validation report: has_issues={report.has_issues}, "
                    f"duplicates={len(report.duplicates)}, missing={len(report.missing_drops)}")
        
        return report


class RoutePreview:
    """Generates preview of routes and deliveries"""
    
    @staticmethod
    def get_route_preview(pages: List[PageInfo]) -> Dict:
        """
        Get preview of routes and deliveries for user approval
        
        Returns: Dict with route information for display
        """
        routes = RouteSequencer.get_route_summary(pages)
        
        preview = {
            'total_routes': len(routes),
            'total_main_pages': sum(1 for p in pages if not p.is_continuation and p.route is not None),
            'routes': {}
        }
        
        for route_num in sorted(routes.keys()):
            route_info = routes[route_num]
            preview['routes'][route_num] = {
                'route': route_num,
                'deliveries': sorted(route_info.deliveries),
                'delivery_count': len(route_info.deliveries),
                'source_files': list(set(route_info.source_files.values())),
                'duplicates': route_info.duplicate_deliveries if route_info.duplicate_deliveries else [],
                'missing': route_info.missing_deliveries if route_info.missing_deliveries else [],
            }
        
        return preview
    
    @staticmethod
    def format_preview(preview: Dict) -> str:
        """
        Format route preview as readable string
        
        Returns: Formatted preview text
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"ROUTE PREVIEW - {preview['total_routes']} Route(s), {preview['total_main_pages']} Page(s)")
        lines.append("=" * 70)
        
        for route_num, route_data in sorted(preview['routes'].items()):
            deliveries = route_data['deliveries']
            delivery_str = f"{min(deliveries)}-{max(deliveries)}" if deliveries else "N/A"
            
            lines.append(f"\nRoute {route_num:4d} | Deliveries: {delivery_str} | Count: {route_data['delivery_count']}")
            lines.append(f"         Files: {', '.join(route_data['source_files'])}")
            
            if route_data['duplicates']:
                lines.append(f"         ⚠️  Duplicates: {route_data['duplicates']}")
            
            if route_data['missing']:
                lines.append(f"         ⚠️  Missing: {route_data['missing']}")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
