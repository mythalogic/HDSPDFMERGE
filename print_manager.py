"""
Print Manager for HDS Route Sequencer
Handles intelligent print prioritization, wave-based printing, and print queue monitoring
"""

import os
import time
import threading
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

try:
    from PyPDF2 import PdfWriter, PdfReader
except ImportError:
    raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")

try:
    import win32print
    import win32api
except ImportError:
    raise ImportError("pywin32 is required for print monitoring. Install with: pip install pywin32")

from models import PageInfo
from logger import get_logger


class PrintPriority(Enum):
    """Print priority groups"""
    PRIORITY_1 = (3010, 3030)  # Runs 3010-3030
    PRIORITY_2 = (3001, 3009)  # Runs 3001-3009
    PRIORITY_3 = (3031, 3033)  # Runs 3031-3033
    PRIORITY_4 = None           # All remaining runs


class PrintQueueStatus(Enum):
    """Printer queue status"""
    READY = "READY"
    PRINTING = "PRINTING"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    PAUSED = "PAUSED"


@dataclass
class PrintBatch:
    """Represents a print batch (wave)"""
    wave_number: int
    run_range: Tuple[int, int]  # (min_run, max_run)
    page_indices: List[int]
    page_count: int
    status: str = "PENDING"
    error_message: Optional[str] = None
    queued_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def duration(self) -> Optional[float]:
        """Get duration in seconds if completed"""
        if self.queued_at and self.completed_at:
            return self.completed_at - self.queued_at
        return None


@dataclass
class PrintProgress:
    """Tracks overall print progress"""
    total_pages: int = 0
    total_batches: int = 0
    current_batch: int = 0
    pages_printed: int = 0
    pages_remaining: int = 0
    overall_progress_percent: int = 0
    current_run_range: Tuple[int, int] = (0, 0)
    batches_queued: int = 0
    batches_completed: int = 0
    batches_failed: int = 0
    printer_status: str = "UNKNOWN"
    last_updated: float = field(default_factory=time.time)
    errors: List[str] = field(default_factory=list)


class RunGrouper:
    """Groups pages by run numbers with priority-based ordering"""
    
    @staticmethod
    def extract_run_number(page: PageInfo) -> Optional[int]:
        """Extract run number from page (route number)"""
        return page.route
    
    @staticmethod
    def group_pages_by_run(pages: List[PageInfo]) -> Dict[int, List[int]]:
        """
        Group pages by run number
        
        Returns: Dict mapping run_number -> list of page indices
        """
        logger = get_logger()
        run_groups = defaultdict(list)
        
        for idx, page in enumerate(pages):
            run_num = RunGrouper.extract_run_number(page)
            if run_num is not None:
                run_groups[run_num].append(idx)
        
        logger.info(f"Grouped {len(pages)} pages into {len(run_groups)} run groups")
        return dict(run_groups)
    
    @staticmethod
    def get_priority_order() -> List[Tuple[int, int]]:
        """
        Get run number priority order
        
        Returns: List of (min_run, max_run) tuples in priority order
        """
        return [
            (3010, 3030),  # Priority 1
            (3001, 3009),  # Priority 2
            (3031, 3033),  # Priority 3
        ]
    
    @staticmethod
    def sort_runs_by_priority(run_numbers: List[int]) -> List[int]:
        """
        Sort run numbers by priority
        
        Sorting order:
        1. Priority 1: Runs 3010-3030
        2. Priority 2: Runs 3001-3009
        3. Priority 3: Runs 3031-3033
        4. Remaining: Ascending order
        """
        logger = get_logger()
        priority_order = RunGrouper.get_priority_order()
        
        sorted_runs = []
        remaining_runs = set(run_numbers)
        
        # Add priority groups
        for min_run, max_run in priority_order:
            priority_runs = sorted([r for r in remaining_runs if min_run <= r <= max_run])
            sorted_runs.extend(priority_runs)
            remaining_runs -= set(priority_runs)
        
        # Add remaining in ascending order
        sorted_runs.extend(sorted(remaining_runs))
        
        logger.debug(f"Priority-sorted runs: {sorted_runs}")
        return sorted_runs
    
    @staticmethod
    def get_pages_by_priority(pages: List[PageInfo]) -> List[int]:
        """
        Get page indices sorted by run priority
        
        Returns: List of page indices in priority order
        """
        # Group pages by run
        run_groups = RunGrouper.group_pages_by_run(pages)
        
        # Sort runs by priority
        sorted_runs = RunGrouper.sort_runs_by_priority(list(run_groups.keys()))
        
        # Flatten back to page indices
        prioritized_indices = []
        for run_num in sorted_runs:
            prioritized_indices.extend(run_groups[run_num])
        
        return prioritized_indices


class WavePrinter:
    """Manages wave-based PDF printing"""
    
    DEFAULT_BATCH_SIZE = 25  # Pages per batch
    
    def __init__(self, pdf_path: str, batch_size: int = DEFAULT_BATCH_SIZE):
        """
        Initialize wave printer
        
        Args:
            pdf_path: Path to PDF file to print
            batch_size: Number of pages per print batch
        """
        self.logger = get_logger()
        self.pdf_path = pdf_path
        self.batch_size = batch_size
        self.total_pages = 0
        self.batches: List[PrintBatch] = []
        self.progress = PrintProgress()
        self.is_printing = False
        self.print_thread: Optional[threading.Thread] = None
        self.printer_monitor_thread: Optional[threading.Thread] = None
        
        # Load PDF
        try:
            reader = PdfReader(pdf_path)
            self.total_pages = len(reader.pages)
            self.logger.info(f"Loaded PDF: {self.total_pages} pages")
        except Exception as e:
            self.logger.error(f"Failed to load PDF: {e}")
            raise
    
    def create_wave_batches(self, pages: List[PageInfo]) -> List[PrintBatch]:
        """
        Create print waves/batches from pages
        
        Args:
            pages: List of PageInfo objects (should be prioritized by run)
            
        Returns:
            List of PrintBatch objects
        """
        self.logger.separator("CREATING PRINT WAVES", char="=")
        
        self.batches = []
        self.progress.total_pages = len(pages)
        self.progress.pages_remaining = len(pages)
        
        # Get pages sorted by priority
        prioritized_indices = RunGrouper.get_pages_by_priority(pages)
        
        # Create batches
        wave_number = 1
        for i in range(0, len(prioritized_indices), self.batch_size):
            batch_indices = prioritized_indices[i:i + self.batch_size]
            
            # Get run range for this batch
            batch_pages = [pages[idx] for idx in batch_indices]
            run_numbers = [p.route for p in batch_pages if p.route is not None]
            
            if run_numbers:
                min_run = min(run_numbers)
                max_run = max(run_numbers)
                run_range = (min_run, max_run)
            else:
                run_range = (0, 0)
            
            batch = PrintBatch(
                wave_number=wave_number,
                run_range=run_range,
                page_indices=batch_indices,
                page_count=len(batch_indices)
            )
            
            self.batches.append(batch)
            
            self.logger.info(
                f"Wave {wave_number:2d}: Runs {min_run:4d}-{max_run:4d} "
                f"({len(batch_indices):3d} pages)"
            )
            
            wave_number += 1
        
        self.progress.total_batches = len(self.batches)
        
        self.logger.info(f"\nCreated {len(self.batches)} print waves")
        self.logger.info(f"Total pages to print: {len(prioritized_indices)}")
        self.logger.separator()
        
        return self.batches
    
    def create_batch_pdf(self, batch: PrintBatch) -> str:
        """
        Create a PDF file for a specific batch
        
        Args:
            batch: PrintBatch object
            
        Returns:
            Path to created batch PDF
        """
        try:
            reader = PdfReader(self.pdf_path)
            writer = PdfWriter()
            
            # Add pages for this batch
            for page_idx in batch.page_indices:
                if page_idx < len(reader.pages):
                    writer.add_page(reader.pages[page_idx])
            
            # Create batch PDF path
            batch_filename = f"Wave_{batch.wave_number:02d}_Run_{batch.run_range[0]:04d}_{batch.run_range[1]:04d}.pdf"
            batch_path = os.path.join(os.path.dirname(self.pdf_path), batch_filename)
            
            # Write batch PDF
            with open(batch_path, 'wb') as f:
                writer.write(f)
            
            self.logger.info(f"Created batch PDF: {batch_filename}")
            return batch_path
        
        except Exception as e:
            self.logger.error(f"Failed to create batch PDF: {e}")
            raise
    
    def print_batch(self, batch_path: str, printer_name: Optional[str] = None) -> bool:
        """
        Send a batch PDF to the printer
        
        Args:
            batch_path: Path to batch PDF
            printer_name: Name of printer (None = default printer)
            
        Returns:
            True if successfully queued, False otherwise
        """
        try:
            if printer_name is None:
                printer_name = win32print.GetDefaultPrinter()
            
            # Use Windows Print API to queue document
            try:
                win32api.ShellExecute(
                    0,
                    "print",
                    batch_path,
                    f'/d:"{printer_name}"',
                    ".",
                    0
                )
                self.logger.info(f"✓ Queued to printer: {batch_filename(batch_path)}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to queue print job: {e}")
                return False
        
        except Exception as e:
            self.logger.error(f"Print batch failed: {e}")
            return False
    
    def get_printer_status(self) -> PrintQueueStatus:
        """
        Get current printer status
        
        Returns:
            PrintQueueStatus enum value
        """
        try:
            printer_name = win32print.GetDefaultPrinter()
            # Check if printer exists and is ready
            printers = win32print.EnumPrinters(2)
            
            for printer in printers:
                if printer[2] == printer_name:
                    # Printer found
                    return PrintQueueStatus.READY
            
            return PrintQueueStatus.UNAVAILABLE
        except Exception as e:
            self.logger.warning(f"Failed to check printer status: {e}")
            return PrintQueueStatus.UNAVAILABLE
    
    def start_print_queue(self, pages: List[PageInfo], printer_name: Optional[str] = None):
        """
        Start printing all waves
        
        Args:
            pages: List of PageInfo objects
            printer_name: Name of printer (None = default)
        """
        self.print_thread = threading.Thread(
            target=self._print_queue_worker,
            args=(pages, printer_name)
        )
        self.print_thread.daemon = True
        self.print_thread.start()
    
    def _print_queue_worker(self, pages: List[PageInfo], printer_name: Optional[str] = None):
        """Worker thread for print queue"""
        self.is_printing = True
        
        try:
            # Create batches
            self.create_wave_batches(pages)
            
            # Print each batch
            for batch in self.batches:
                if not self.is_printing:
                    break
                
                try:
                    batch.status = "PROCESSING"
                    
                    # Create batch PDF
                    batch_path = self.create_batch_pdf(batch)
                    
                    # Queue batch
                    batch.status = "QUEUED"
                    batch.queued_at = time.time()
                    
                    if self.print_batch(batch_path, printer_name):
                        # Wait a bit before next batch
                        time.sleep(1)
                        batch.status = "PRINTING"
                        
                        # Update progress
                        self.progress.pages_printed += batch.page_count
                        self.progress.pages_remaining -= batch.page_count
                        self.progress.batches_queued += 1
                        self.progress.current_batch += 1
                        self.progress.overall_progress_percent = int(
                            (self.progress.pages_printed / self.progress.total_pages) * 100
                        )
                        self.progress.current_run_range = batch.run_range
                    else:
                        batch.status = "FAILED"
                        batch.error_message = "Failed to queue print job"
                        self.progress.batches_failed += 1
                        self.progress.errors.append(
                            f"Batch {batch.wave_number}: Failed to queue"
                        )
                
                except Exception as e:
                    batch.status = "FAILED"
                    batch.error_message = str(e)
                    self.progress.batches_failed += 1
                    self.progress.errors.append(f"Batch {batch.wave_number}: {e}")
                    self.logger.error(f"Failed to print batch {batch.wave_number}: {e}")
        
        finally:
            self.is_printing = False
            self.progress.last_updated = time.time()
    
    def stop_printing(self):
        """Stop printing"""
        self.is_printing = False
        if self.print_thread:
            self.print_thread.join(timeout=5)
    
    def get_progress(self) -> PrintProgress:
        """Get current print progress"""
        return self.progress


def batch_filename(path: str) -> str:
    """Get filename from path"""
    return os.path.basename(path)
