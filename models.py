"""
Data models for HDS Route Sequencer
Defines data structures for PDFs, routes, and processing results
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class DocumentType(Enum):
    """Enum for document types"""
    PICKING_SLIP = "PICKING_SLIP"
    DELIVERY_DOCKET = "DELIVERY_DOCKET"
    UNKNOWN = "UNKNOWN"


class CompanyType(Enum):
    """Enum for company types"""
    LAC = "LAC"
    RTR = "RTR"
    UNKNOWN = "UNKNOWN"


@dataclass
class PageInfo:
    """Information about a PDF page"""
    page_num: int
    source_file: str
    route: Optional[int] = None
    delivery: Optional[int] = None
    company: str = "UNKNOWN"
    doc_type: str = "UNKNOWN"
    is_continuation: bool = False
    text: str = ""
    customer: Optional[str] = None


@dataclass
class PDFFileInfo:
    """Information about a PDF file"""
    file_path: str
    file_name: str
    document_type: str = "UNKNOWN"
    company_type: str = "UNKNOWN"
    page_count: int = 0
    routes_detected: List[int] = field(default_factory=list)
    is_valid: bool = False
    error_message: Optional[str] = None


@dataclass
class RouteInfo:
    """Information about a route"""
    route_number: int
    deliveries: List[int] = field(default_factory=list)
    source_files: Dict[Tuple[int, int], str] = field(default_factory=dict)  # (route, delivery) -> source_file
    duplicate_deliveries: List[int] = field(default_factory=list)
    missing_deliveries: List[int] = field(default_factory=list)

    def add_delivery(self, delivery_num: int, source_file: str):
        """Add delivery number to route"""
        if delivery_num not in self.deliveries:
            self.deliveries.append(delivery_num)
        self.source_files[(self.route_number, delivery_num)] = source_file

    def detect_duplicates_and_missing(self):
        """Detect duplicate and missing delivery numbers"""
        if not self.deliveries:
            return

        sorted_deliveries = sorted(self.deliveries)

        # Detect duplicates (more than one occurrence)
        from collections import Counter
        counts = Counter(self.deliveries)
        self.duplicate_deliveries = [d for d, c in counts.items() if c > 1]

        # Detect missing
        if sorted_deliveries:
            for i in range(sorted_deliveries[0], sorted_deliveries[-1] + 1):
                if i not in self.deliveries:
                    self.missing_deliveries.append(i)


@dataclass
class ValidationReport:
    """Validation report for processed pages"""
    total_pages: int = 0
    main_pages: int = 0
    continuation_pages: int = 0
    duplicates: List[Dict] = field(default_factory=list)
    missing_drops: List[Dict] = field(default_factory=list)
    has_issues: bool = False
    routes: List[int] = field(default_factory=list)
    delivery_range: Dict[int, Tuple[int, int]] = field(default_factory=dict)  # route -> (min, max)


@dataclass
class ProcessingResult:
    """Result of processing operation"""
    success: bool
    document_type: str
    file_count: int = 0
    pages_merged: int = 0
    routes_detected: List[int] = field(default_factory=list)
    output_file: Optional[str] = None
    validation_report: Optional[ValidationReport] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    # Path to the human-readable stats/warnings report written alongside
    # output_file (see PDFProcessor.write_processing_report). None if no
    # report could be written.
    report_file: Optional[str] = None
    # Path to the machine-readable (JSON) twin of report_file, if written.
    report_json_file: Optional[str] = None


@dataclass
class MergeResult:
    """Result of merge operation"""
    success: bool
    picking_slips: Optional[ProcessingResult] = None
    delivery_dockets: Optional[ProcessingResult] = None
    total_duration: float = 0.0


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DocumentError:
    """Represents a document error"""
    severity: str
    error_type: str
    route: Optional[int] = None
    delivery: Optional[int] = None
    message: str = ""
    pages: List[int] = field(default_factory=list)

    def __str__(self) -> str:
        if self.route and self.delivery:
            return f"{self.severity}: Route {self.route}-{self.delivery}: {self.message}"
        return f"{self.severity}: {self.message}"


@dataclass
class ErrorReport:
    """Report of all detected errors"""
    total_errors: int = 0
    total_warnings: int = 0
    missing_runs: List[int] = field(default_factory=list)
    invalid_runs: List[int] = field(default_factory=list)
    duplicate_runs: List[Tuple[int, int]] = field(default_factory=list)  # (run, count)
    errors: List[DocumentError] = field(default_factory=list)
    has_critical_errors: bool = False
    has_warnings: bool = False

    def add_error(self, error: DocumentError):
        """Add an error to the report"""
        self.errors.append(error)
        if error.severity == ErrorSeverity.CRITICAL.value:
            self.has_critical_errors = True
        elif error.severity == ErrorSeverity.WARNING.value:
            self.has_warnings = True
        self.total_errors += 1


@dataclass
class PrintSettings:
    """Print configuration settings"""
    batch_size: int = 25
    printer_name: Optional[str] = None
    auto_pause_on_error: bool = True
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5