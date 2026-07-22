"""
Error Detector for HDS Route Sequencer
Detects missing run numbers, invalid runs, and other issues
"""

from typing import List, Set, Tuple
from collections import Counter, defaultdict

from models import PageInfo, DocumentError, ErrorReport, ErrorSeverity
from logger import get_logger


class ErrorDetector:
    """Detects various error conditions in processed documents"""
    
    @staticmethod
    def detect_all_errors(pages: List[PageInfo]) -> ErrorReport:
        """
        Detect all possible errors in the document set
        
        Args:
            pages: List of PageInfo objects
            
        Returns:
            ErrorReport with all detected issues
        """
        logger = get_logger()
        logger.separator("ERROR DETECTION", char="=")
        
        report = ErrorReport()
        
        # Extract run numbers
        run_numbers = set()
        run_pages = defaultdict(list)
        
        for idx, page in enumerate(pages):
            if page.route is not None:
                run_numbers.add(page.route)
                run_pages[page.route].append((idx, page))
        
        # 1. Detect missing run numbers in sequence
        ErrorDetector._detect_missing_runs(list(run_numbers), report, logger)
        
        # 2. Detect invalid run numbers (outside expected ranges)
        ErrorDetector._detect_invalid_runs(list(run_numbers), report, logger)
        
        # 3. Detect duplicate runs
        ErrorDetector._detect_duplicate_runs(run_pages, pages, report, logger)
        
        # Log summary
        logger.info(f"\nError Detection Summary:")
        logger.info(f"  Total Errors: {report.total_errors}")
        logger.info(f"  Total Warnings: {report.total_warnings}")
        logger.info(f"  Critical Errors: {report.has_critical_errors}")
        
        if report.missing_runs:
            logger.warning(f"  Missing Runs: {sorted(report.missing_runs)}")
        if report.invalid_runs:
            logger.warning(f"  Invalid Runs: {sorted(report.invalid_runs)}")
        if report.duplicate_runs:
            logger.warning(f"  Duplicate Runs: {report.duplicate_runs}")
        
        logger.separator()
        
        return report
    
    @staticmethod
    def _detect_missing_runs(run_numbers: List[int], report: ErrorReport, logger) -> None:
        """
        Detect missing run numbers in expected sequences
        
        Expected sequences:
        - 3001-3033 (core range)
        - Any detected run should have related runs nearby
        """
        if not run_numbers:
            return
        
        sorted_runs = sorted(run_numbers)
        
        # Check for gaps in the 3000 range
        for i in range(sorted_runs[0], sorted_runs[-1] + 1):
            if i not in run_numbers and 3000 <= i <= 3099:
                report.missing_runs.append(i)
                
                error = DocumentError(
                    severity=ErrorSeverity.WARNING.value,
                    error_type="MISSING_RUN",
                    route=i,
                    message=f"Run {i} is missing (gap in sequence)"
                )
                report.add_error(error)
                logger.warning(f"  ⚠️  Missing run in sequence: {i}")
    
    @staticmethod
    def _detect_invalid_runs(run_numbers: List[int], report: ErrorReport, logger) -> None:
        """
        Detect invalid/unexpected run numbers
        
        Ranges:
        - Expected: 3000-3099 (core operations)
        - Expected: 3001-3033 (standard range)
        - Outside these ranges are flagged as invalid
        """
        VALID_RANGES = [(3000, 3099)]
        EXPECTED_RANGES = [(3001, 3033)]
        
        for run_num in run_numbers:
            # Check if in any valid range
            is_valid = any(min_r <= run_num <= max_r for min_r, max_r in VALID_RANGES)
            is_expected = any(min_r <= run_num <= max_r for min_r, max_r in EXPECTED_RANGES)
            
            if not is_valid:
                report.invalid_runs.append(run_num)
                error = DocumentError(
                    severity=ErrorSeverity.ERROR.value,
                    error_type="INVALID_RUN",
                    route=run_num,
                    message=f"Run {run_num} is outside valid range (3000-3099)"
                )
                report.add_error(error)
                logger.error(f"  ✗ Invalid run number: {run_num}")
            elif not is_expected:
                error = DocumentError(
                    severity=ErrorSeverity.WARNING.value,
                    error_type="UNEXPECTED_RUN",
                    route=run_num,
                    message=f"Run {run_num} is outside expected range (3001-3033)"
                )
                report.add_error(error)
                logger.warning(f"  ⚠️  Unexpected run number: {run_num}")
    
    @staticmethod
    def _detect_duplicate_runs(run_pages: dict, pages: List[PageInfo], 
                              report: ErrorReport, logger) -> None:
        """
        Detect duplicate pages for the same run
        
        Duplicates are multiple occurrences of the same route-delivery combination
        """
        for run_num, pages_in_run in run_pages.items():
            # Count run-delivery combinations
            run_delivery_counts = Counter()
            run_delivery_files = defaultdict(list)
            
            for idx, page in pages_in_run:
                key = (page.route, page.delivery)
                run_delivery_counts[key] += 1
                run_delivery_files[key].append(page.source_file)
            
            # Check for duplicates
            for (route, delivery), count in run_delivery_counts.items():
                if count > 1:
                    report.duplicate_runs.append((route, count))
                    
                    error = DocumentError(
                        severity=ErrorSeverity.WARNING.value,
                        error_type="DUPLICATE_RUN",
                        route=route,
                        delivery=delivery,
                        message=f"Route {route}-{delivery} appears {count} times in: "
                               f"{', '.join(set(run_delivery_files[(route, delivery)]))}"
                    )
                    report.add_error(error)
                    logger.warning(f"  ⚠️  Duplicate found: Route {route}-{delivery} ({count} occurrences)")
    
    @staticmethod
    def get_error_summary_text(report: ErrorReport) -> str:
        """
        Generate human-readable error summary
        
        Returns: Formatted error summary text
        """
        lines = []
        lines.append("DOCUMENT ERROR REPORT")
        lines.append("=" * 50)
        lines.append("")
        
        # Summary
        lines.append(f"Total Issues: {report.total_errors + report.total_warnings}")
        lines.append(f"  Errors: {report.total_errors}")
        lines.append(f"  Warnings: {report.total_warnings}")
        lines.append("")
        
        # Missing runs
        if report.missing_runs:
            lines.append(f"Missing Runs ({len(report.missing_runs)}):")
            for run in sorted(report.missing_runs)[:10]:
                lines.append(f"  • Run {run}")
            if len(report.missing_runs) > 10:
                lines.append(f"  • ... and {len(report.missing_runs) - 10} more")
            lines.append("")
        
        # Invalid runs
        if report.invalid_runs:
            lines.append(f"Invalid Runs ({len(report.invalid_runs)}):")
            for run in sorted(report.invalid_runs)[:10]:
                lines.append(f"  • Run {run}")
            if len(report.invalid_runs) > 10:
                lines.append(f"  • ... and {len(report.invalid_runs) - 10} more")
            lines.append("")
        
        # Duplicate runs
        if report.duplicate_runs:
            lines.append(f"Duplicate Runs ({len(report.duplicate_runs)}):")
            for run, count in sorted(report.duplicate_runs)[:10]:
                lines.append(f"  • Run {run}: {count} occurrences")
            if len(report.duplicate_runs) > 10:
                lines.append(f"  • ... and {len(report.duplicate_runs) - 10} more")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def should_warn_before_print(report: ErrorReport) -> Tuple[bool, str]:
        """
        Determine if user should be warned before printing
        
        Returns: Tuple of (should_warn: bool, reason: str)
        """
        if report.has_critical_errors:
            return True, "CRITICAL: Critical errors detected - printing not recommended"
        
        if report.has_warnings and (report.missing_runs or report.invalid_runs):
            missing_count = len(report.missing_runs)
            invalid_count = len(report.invalid_runs)
            
            if missing_count + invalid_count > 5:
                return True, f"WARNING: {missing_count} missing and {invalid_count} invalid runs detected"
        
        if report.duplicate_runs and len(report.duplicate_runs) > 3:
            return True, f"WARNING: {len(report.duplicate_runs)} duplicate runs detected"
        
        return False, ""
