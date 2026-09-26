"""
PDF Merger Module for HDS Route Sequencer
Handles PDF merging and file output operations
"""

import os
import io
import sys
import json
from typing import List, Tuple, Optional, Callable
from datetime import datetime

try:
    from PyPDF2 import PdfWriter, PdfReader
except ImportError:
    raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")

try:
    import fitz  # PyMuPDF - used for RTR customer-name highlighting and stamping
except ImportError:
    fitz = None

from models import PageInfo, ProcessingResult, ValidationReport
from route_sequencer import RouteSequencer, RoutePreview
from pdf_detector import PDFDetector
from logger import get_logger
import run_separator
from run_separator import (
    normalize_customer, PALLET_CUSTOMERS, HIGH_PRIORITY_CUSTOMERS,
    PALLET_HIGHLIGHT_COLOR, HIGH_PRIORITY_HIGHLIGHT_COLOR,
)

# Flip to False to turn run-separator pages off entirely - merge_pages will
# just merge pages with no dividers, same as before this feature existed.
INSERT_RUN_SEPARATORS = False

# Flip to False to turn off the RTR stamp entirely without removing the code.
INSERT_RTR_STAMP = True

# Type of the optional progress_callback threaded through process_pdfs and
# merge_pages: (percent_complete, human_readable_status_message) -> None.
# Both PDFProcessor.process_pdfs and PDFMerger.merge_pages call this at real
# milestones (a file extracted, a page merged, a report written) instead of
# a canned animation, so a caller (e.g. the GUI's progress bar) tracks
# actual work rather than a fixed timer.
ProgressCallback = Optional[Callable[[int, str], None]]


def _report_progress(callback: ProgressCallback, percent: int, message: str) -> None:
    """Best-effort progress callback invocation - never let a UI callback
    error abort the actual processing work."""
    if callback is None:
        return
    try:
        callback(max(0, min(100, int(percent))), message)
    except Exception:
        get_logger().debug("Progress callback raised - ignoring", exc_info=True)


def _resource_path(*parts: str) -> str:
    """
    Resolve a bundled resource path that works both running from source and
    when frozen into a PyInstaller build (onedir or onefile - PyInstaller
    unpacks data files under sys._MEIPASS at runtime in both cases).
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


# Where the stamp image lives. Put rtr-stamp-c6-yellow.png in an "assets"
# folder next to this file (create the folder if it doesn't exist yet),
# and add that folder to the PyInstaller build - see
# HDS_Route_Sequencer.spec and build_exe.py.
STAMP_IMAGE_PATH = _resource_path("assets", "rtr-stamp-c6-yellow.png")


# A single real customer name should appear at most a couple of times on its
# own page. If a candidate string matches many more spots than that, it's a
# sign extraction grabbed something too generic (e.g. a company badge that
# also appears in the barcode/invoice number) rather than an actual name -
# skip highlighting rather than plastering color across the page.
MAX_PLAUSIBLE_MATCHES_PER_PAGE = 4


class PDFMerger:
    """Merges and sequences PDF files"""

    # --- RTR stamp placement tuning -------------------------------------
    # Every RTR order page has a barcode image (wide/short) top-left and a
    # QR code image (roughly square) top-right, sitting on the same header
    # row, with a band of empty page between them. These constants control
    # how that pair is found and how the stamp is sized once found - tune
    # them here if a future docket layout needs different values.

    # Only look for the barcode/QR pair in the top slice of the page, so a
    # similarly-shaped image further down the page (e.g. in a footer logo)
    # never gets mistaken for either of them.
    STAMP_HEADER_BAND_FRACTION = 0.30

    # A barcode image is short and wide - width/height at or above this
    # counts as "barcode-shaped".
    BARCODE_MIN_ASPECT = 2.2

    # A QR code image is close to square - width/height inside this range
    # counts as "QR-shaped".
    QR_ASPECT_RANGE = (0.8, 1.25)

    # Padding (in PDF points) kept clear between the stamp and the barcode
    # / QR code on either side of it.
    STAMP_PADDING = 4.0

    # Never let the stamp grow taller than this fraction of the page, even
    # if the detected gap is unusually large.
    STAMP_MAX_HEIGHT_FRACTION = 0.16

    @staticmethod
    def merge_pages(pages: List[PageInfo], output_path: str, label: str = "Document",
                     progress_callback: ProgressCallback = None,
                     progress_range: Tuple[int, int] = (60, 90)) -> Tuple[bool, str]:
        """
        Merge pages into a single PDF file. A run-separator page (see
        run_separator.build_separator_page) is inserted immediately before
        the first page of every route/run, including the first, so a
        printed stack can be split by run without reading a single docket.

        Args:
            pages: List of PageInfo objects to merge (should be pre-sequenced)
            output_path: Output PDF file path
            label: Label for logging
            progress_callback: Optional (percent, message) -> None, called
                periodically while pages are written so a UI can show real
                progress through the merge (usually the slowest step for a
                large pack) instead of a static bar.
            progress_range: (start, end) percent to spread the page-writing
                loop across.

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
            separators_added = 0

            # Pages actually written to the output, in output-page order. This
            # is what lets us line up "page N of the merged PDF" with the
            # PageInfo (route/company/customer) that produced it, e.g. for the
            # RTR customer-name highlighting pass below. Separator pages get a
            # blank placeholder entry so the index alignment holds.
            written_pages: List[PageInfo] = []

            # Track the route currently being written, so a separator is
            # inserted only once per run rather than once per page.
            current_run_route: Optional[int] = None
            warned_no_fitz = False

            total_pages = len(pages) or 1
            progress_start, progress_end = progress_range
            last_reported_percent = -1

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

                    pdf_page = reader.pages[page_num]

                    # New run starting - drop in a separator page first
                    if INSERT_RUN_SEPARATORS and page.route is not None and page.route != current_run_route:
                        if fitz is None:
                            if not warned_no_fitz:
                                logger.warning("  ⚠️  PyMuPDF (fitz) is not installed - skipping run "
                                              "separator pages. Install with: pip install PyMuPDF")
                                warned_no_fitz = True
                        else:
                            run_pages = [p for p in pages if p.route == page.route]
                            stats = run_separator.compute_run_stats(page.route, run_pages)
                            mediabox = pdf_page.mediabox
                            sep_bytes = run_separator.build_separator_page(
                                stats, float(mediabox.width), float(mediabox.height)
                            )
                            sep_reader = PdfReader(io.BytesIO(sep_bytes))
                            writer.add_page(sep_reader.pages[0])
                            written_pages.append(PageInfo(page_num=-1, source_file="__separator__",
                                                          route=page.route))
                            pages_added += 1
                            separators_added += 1
                            logger.info(f"  ✦ Run separator: Route {page.route} "
                                       f"({stats['total_drops']} drops)")
                        current_run_route = page.route

                    # Add page to writer
                    writer.add_page(pdf_page)
                    pages_added += 1
                    written_pages.append(page)

                    # Log
                    if page.route is not None and page.delivery is not None:
                        marker = " (continuation)" if page.is_continuation else ""
                        logger.info(f"✓ Page {idx:3d}: Route {page.route:4d} - Delivery {page.delivery:2d} "
                                  f"({page.source_file}){marker}")
                    else:
                        logger.info(f"✓ Page {idx:3d}: Orphan page ({page.source_file})")

                    # Real, work-proportional progress for the slowest step in
                    # the pipeline - only report when the percentage actually
                    # moves, so this doesn't spam the callback once per page
                    # on a 500-page pack.
                    percent = progress_start + int((progress_end - progress_start) * (idx / total_pages))
                    if percent != last_reported_percent:
                        last_reported_percent = percent
                        _report_progress(progress_callback, percent,
                                          f"Merging page {idx}/{total_pages}")

                except Exception as e:
                    logger.error(f"Failed to add page {idx}: {e}")
                    continue

            # Write output file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            _report_progress(progress_callback, progress_end, "Writing merged PDF to disk")

            # Get file stats
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            filename = os.path.basename(output_path)

            logger.info(f"\n✓ Successfully merged {pages_added} pages "
                       f"({separators_added} run separator{'s' if separators_added != 1 else ''})")
            logger.info(f"  Output: {filename}")
            logger.info(f"  Size: {file_size_mb:.2f} MB")

            # Highlight RTR customer names in the merged output (best-effort -
            # a highlighting failure should not fail the merge itself)
            highlight_note = ""
            try:
                highlighted = PDFMerger.highlight_rtr_customer_names(output_path, written_pages)
                if highlighted > 0:
                    logger.info(f"  ✓ Highlighted {highlighted} customer name(s)")
                    highlight_note = f", {highlighted} customer name(s) highlighted"
            except Exception as e:
                logger.warning(f"  ⚠️  RTR customer-name highlighting skipped: {e}")

            # Stamp every RTR page in the header gap between its barcode and
            # QR code (best-effort - a stamping failure should not fail the
            # merge itself, same reasoning as the highlighting pass above).
            stamp_note = ""
            if INSERT_RTR_STAMP:
                try:
                    stamped = PDFMerger.stamp_rtr_orders(output_path, written_pages)
                    if stamped > 0:
                        logger.info(f"  ✓ Stamped {stamped} RTR order page(s)")
                        stamp_note = f", {stamped} RTR stamp(s) applied"
                except Exception as e:
                    logger.warning(f"  ⚠️  RTR stamp placement skipped: {e}")

            logger.separator()

            return True, f"{filename} ({pages_added} pages, {file_size_mb:.2f} MB{highlight_note}{stamp_note})"

        except Exception as e:
            logger.error(f"Merge failed: {e}")
            logger.separator()
            return False, f"Merge failed: {str(e)}"

    @staticmethod
    def highlight_rtr_customer_names(output_path: str, written_pages: List[PageInfo]) -> int:
        """
        Highlight the customer name on every pallet/high-priority page of
        the merged PDF, regardless of company (RTR no longer gets a
        generic yellow highlight).

        Args:
            output_path: Path to the merged PDF (already written to disk)
            written_pages: PageInfo objects in the same order as the pages
                           that ended up in the merged PDF (index i in this
                           list corresponds to page i of output_path)

        Returns:
            Number of customer names actually highlighted
        """
        logger = get_logger()

        if fitz is None:
            logger.warning("PyMuPDF (fitz) is not installed - skipping RTR customer-name "
                          "highlighting. Install with: pip install PyMuPDF")
            return 0

        # Anything to do at all?
        if not any(p.customer for p in written_pages):
            return 0

        highlighted_count = 0
        doc = fitz.open(output_path)

        try:
            page_count = min(len(doc), len(written_pages))
            for i in range(page_count):
                page_info = written_pages[i]

                if not page_info.customer:
                    continue

                # High-priority (blood orange) beats pallet (blue), both
                # regardless of company. No more generic RTR-only yellow.
                normalized = normalize_customer(page_info.customer)
                if normalized in HIGH_PRIORITY_CUSTOMERS:
                    color = HIGH_PRIORITY_HIGHLIGHT_COLOR
                elif normalized in PALLET_CUSTOMERS:
                    color = PALLET_HIGHLIGHT_COLOR
                else:
                    continue

                # Belt-and-suspenders: never highlight a candidate that looks
                # like page furniture (a company badge, etc.) rather than an
                # actual customer name, even if it slipped past extraction.
                if not PDFDetector._is_plausible_customer_name(page_info.customer):
                    logger.warning(f"  ⚠️  Skipping implausible customer name "
                                  f"'{page_info.customer}' on output page {i + 1}")
                    continue

                pdf_page = doc[i]
                rects = pdf_page.search_for(page_info.customer)

                if not rects:
                    logger.debug(f"  Could not locate customer name '{page_info.customer}' "
                               f"on output page {i + 1} for highlighting")
                    continue

                if len(rects) > MAX_PLAUSIBLE_MATCHES_PER_PAGE:
                    logger.warning(f"  ⚠️  '{page_info.customer}' matched {len(rects)} spots on "
                                  f"output page {i + 1} - looks like a generic string, not a "
                                  f"customer name; skipping highlight")
                    continue

                for rect in rects:
                    annot = pdf_page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color)
                    annot.update()

                highlighted_count += 1

            if highlighted_count > 0:
                # The document was opened directly from output_path with no
                # structural changes other than annotations, so an
                # incremental save is safe and avoids rewriting the file.
                doc.saveIncr()
        finally:
            doc.close()

        return highlighted_count

    @staticmethod
    def _find_barcode_and_qr_rects(page) -> Tuple[Optional["fitz.Rect"], Optional["fitz.Rect"]]:
        """
        Best-effort locate the barcode image and the QR-code image in an
        RTR page's header, using each element's on-page bounding box and
        aspect ratio rather than any fixed coordinates (docket layouts
        shift slightly between exports/print runs, so hard-coded positions
        would drift out from under the real content).

        Checks both raster images (get_image_info) and vector drawings
        (get_drawings) - real dockets render the QR as a raster image but
        the barcode as vector paths, so relying on images alone misses the
        barcode entirely.

        Returns (barcode_rect, qr_rect) - either is None if not confidently
        found.
        """
        header_limit = page.rect.height * PDFMerger.STAMP_HEADER_BAND_FRACTION
        barcode_rect = None
        qr_rect = None

        candidate_bboxes = [fitz.Rect(info["bbox"]) for info in page.get_image_info()]
        candidate_bboxes += [d["rect"] for d in page.get_drawings()]

        for bbox in candidate_bboxes:
            if bbox.is_empty or bbox.y0 > header_limit:
                continue

            width, height = bbox.width, bbox.height
            if width <= 0 or height <= 0:
                continue
            aspect = width / height

            if aspect >= PDFMerger.BARCODE_MIN_ASPECT:
                # Keep the widest match - the real barcode, not some thin
                # decorative rule that happens to live in the header.
                if barcode_rect is None or width > barcode_rect.width:
                    barcode_rect = bbox
            elif PDFMerger.QR_ASPECT_RANGE[0] <= aspect <= PDFMerger.QR_ASPECT_RANGE[1]:
                # Keep the largest square-ish match - the QR code, not a
                # small square bullet/icon elsewhere in the header.
                if qr_rect is None or (width * height) > (qr_rect.width * qr_rect.height):
                    qr_rect = bbox

        return barcode_rect, qr_rect

    @staticmethod
    def _stamp_target_rect(barcode_rect: "fitz.Rect", qr_rect: "fitz.Rect",
                            stamp_aspect: float, page_height: float) -> Optional["fitz.Rect"]:
        """
        Compute where the stamp should go: centered in the empty band
        between the barcode (left) and the QR code (right), sized as large
        as that gap allows without distorting the stamp image or spilling
        past a sane fraction of the page height.
        """
        # The gap only means something if the barcode really is left of the
        # QR code - if a layout ever has them the other way round, or
        # overlapping, don't guess.
        if barcode_rect.x1 >= qr_rect.x0:
            return None

        left = barcode_rect.x1 + PDFMerger.STAMP_PADDING
        right = qr_rect.x0 - PDFMerger.STAMP_PADDING
        if right <= left:
            return None

        top = min(barcode_rect.y0, qr_rect.y0)
        bottom = max(barcode_rect.y1, qr_rect.y1)
        gap_width = right - left
        gap_height = max(bottom - top, 1.0)

        max_height = min(gap_height, page_height * PDFMerger.STAMP_MAX_HEIGHT_FRACTION)
        width_limited_height = gap_width / stamp_aspect
        target_height = min(max_height, width_limited_height)
        target_width = target_height * stamp_aspect

        cx = (left + right) / 2
        cy = (top + bottom) / 2
        return fitz.Rect(
            cx - target_width / 2, cy - target_height / 2,
            cx + target_width / 2, cy + target_height / 2,
        )

    @staticmethod
    def stamp_rtr_orders(output_path: str, written_pages: List[PageInfo],
                          stamp_path: str = STAMP_IMAGE_PATH) -> int:
        """
        Place the RTR stamp image in the header gap between the barcode and
        the QR code on every RTR page of the merged PDF, sized to fill that
        gap while keeping the stamp's own proportions.

        Args:
            output_path: Path to the merged PDF (already written to disk)
            written_pages: PageInfo objects in the same order as the pages
                           that ended up in the merged PDF
            stamp_path: Path to the stamp PNG. Defaults to STAMP_IMAGE_PATH.

        Returns:
            Number of pages actually stamped
        """
        logger = get_logger()

        if fitz is None:
            logger.warning("PyMuPDF (fitz) is not installed - skipping RTR stamp placement. "
                          "Install with: pip install PyMuPDF")
            return 0

        if not stamp_path or not os.path.exists(stamp_path):
            logger.warning(f"  ⚠️  RTR stamp image not found at '{stamp_path}' - skipping. "
                          f"Place the PNG there (see STAMP_IMAGE_PATH in pdf_merger.py).")
            return 0

        rtr_pages = [p for p in written_pages if p.company == "RTR"]
        if not rtr_pages:
            logger.info("  RTR stamp: 0 RTR page(s) in this merge - nothing to stamp")
            return 0

        # The stamp's own width/height ratio, so it drops into the gap
        # undistorted no matter how wide or tall that gap turns out to be.
        stamp_pix = fitz.Pixmap(stamp_path)
        stamp_aspect = stamp_pix.width / stamp_pix.height
        stamp_pix = None

        stamped_count = 0
        no_barcode_qr = 0
        no_gap = 0
        doc = fitz.open(output_path)

        try:
            page_count = min(len(doc), len(written_pages))
            for i in range(page_count):
                page_info = written_pages[i]

                if page_info.company != "RTR":
                    continue

                page = doc[i]
                barcode_rect, qr_rect = PDFMerger._find_barcode_and_qr_rects(page)

                if barcode_rect is None or qr_rect is None:
                    no_barcode_qr += 1
                    continue

                target_rect = PDFMerger._stamp_target_rect(
                    barcode_rect, qr_rect, stamp_aspect, page.rect.height
                )

                if target_rect is None:
                    no_gap += 1
                    continue

                page.insert_image(target_rect, filename=stamp_path, keep_proportion=True)
                stamped_count += 1

            if stamped_count > 0:
                # Same reasoning as highlight_rtr_customer_names: nothing
                # structural changed other than adding image content, so an
                # incremental save is safe and avoids rewriting the file.
                doc.saveIncr()
        finally:
            doc.close()

        # Always visible at INFO, not just on success - a silent 0 here is
        # exactly what made the first version of this feature hard to debug.
        logger.info(f"  RTR stamp: {len(rtr_pages)} RTR page(s), {stamped_count} stamped, "
                   f"{no_barcode_qr} had no detectable barcode+QR, {no_gap} had no usable gap")

        return stamped_count


class PDFProcessor:
    """Processes PDF collections with full pipeline"""

    @staticmethod
    def process_pdfs(pdf_files: List[str], doc_type: str, output_folder: str,
                      progress_callback: ProgressCallback = None) -> ProcessingResult:
        """
        Complete pipeline: extract → sequence → validate → merge → report

        Args:
            pdf_files: List of PDF file paths
            doc_type: 'PICKING_SLIP' or 'DELIVERY_DOCKET'
            output_folder: Output folder for merged PDF
            progress_callback: Optional (percent, message) -> None called at
                each real pipeline milestone. Replaces the old fixed-timer
                animation - the bar now reflects actual work, including the
                page-by-page merge loop (usually the slowest step).

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
            _report_progress(progress_callback, 2, "Starting processing")

            if fitz is None:
                result.warnings.append(
                    "PyMuPDF is not installed - customer-name highlighting and RTR stamping "
                    "will NOT run. Run: pip install PyMuPDF"
                )

            # Step 1: Extract pages from all PDFs
            logger.info("\n[STEP 1] Extracting pages...")
            all_pages = []
            pdf_to_pages = {}

            file_count = len(pdf_files) or 1
            for file_idx, pdf_file in enumerate(pdf_files):
                try:
                    pages = RouteSequencer.extract_pages(pdf_file, doc_type)
                    all_pages.extend(pages)
                    pdf_to_pages[pdf_file] = pages
                    logger.info(f"  ✓ {os.path.basename(pdf_file)}: {len(pages)} pages")
                except Exception as e:
                    logger.error(f"  ✗ {os.path.basename(pdf_file)}: {e}")
                    result.warnings.append(f"Failed to extract {os.path.basename(pdf_file)}: {e}")

                percent = 5 + int(30 * ((file_idx + 1) / file_count))
                _report_progress(progress_callback, percent,
                                  f"Extracting pages ({file_idx + 1}/{file_count} files)")

            if not all_pages:
                result.error_message = "No pages extracted from any file"
                return result

            logger.info(f"  Total: {len(all_pages)} pages")

            # Step 2: Sequence pages
            logger.info("\n[STEP 2] Sequencing pages...")
            sequenced_pages = RouteSequencer.sequence_pages(all_pages, doc_type)
            logger.info(f"  ✓ Pages sequenced")
            _report_progress(progress_callback, 45, "Sequencing pages")

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

            # Drop numbers are shared between LAC and RTR on the same run, so
            # a single-client job will always look like it has ~40 gaps that
            # are really just "the other client's paperwork isn't loaded".
            # Warn once, clearly, instead of flooding the report with those
            # expected gaps as if each were a real missing delivery.
            companies = {p.company for p in sequenced_pages if p.company != "UNKNOWN"}
            single_client = len(companies) == 1
            if single_client and validation.missing_drops:
                only = ", ".join(sorted(companies))
                logger.warning(f"  ⚠️  Only {only} pages found - the other client's file does "
                               f"not appear to be loaded. Drop numbers are shared between "
                               f"clients on the same run, so the {len(validation.missing_drops)} "
                               f"gap(s) below are expected, not necessarily missing deliveries.")
                result.warnings.append(
                    f"Only {only} dockets were loaded for this merge. Route/delivery numbers "
                    f"are shared between LAC and RTR on the same run, so the "
                    f"{len(validation.missing_drops)} 'missing delivery' warning(s) below are "
                    f"most likely the other client's paperwork, not real gaps. Load both "
                    f"clients' files together for an accurate missing-delivery check."
                )
            elif validation.missing_drops:
                logger.warning(f"  ⚠️  Missing deliveries: {len(validation.missing_drops)}")
                for miss in validation.missing_drops:
                    logger.warning(f"     Route {miss['route']} - Delivery {miss['delivery']}: NOT FOUND")
                    result.warnings.append(f"Route {miss['route']}-Delivery {miss['delivery']}: MISSING")

            _report_progress(progress_callback, 55, "Validating pages")

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

            _report_progress(progress_callback, 60, "Merging pages")
            success, message = PDFMerger.merge_pages(
                sequenced_pages, output_path, doc_type,
                progress_callback=progress_callback, progress_range=(60, 90)
            )

            if success:
                result.success = True
                result.pages_merged = sum(1 for p in sequenced_pages if not p.is_continuation and p.route is not None)
                result.routes_detected = validation.routes
                result.output_file = output_path
                logger.info(f"\n✓ Processing complete: {output_filename}")

                # Step 5: Write the stats/warnings report alongside the PDF.
                # Best-effort - a reporting failure should never turn a
                # successful merge into a failed one.
                _report_progress(progress_callback, 92, "Writing stats & warnings report")
                try:
                    report_txt, report_json = PDFProcessor.write_processing_report(
                        result, doc_type, pdf_files
                    )
                    result.report_file = report_txt
                    result.report_json_file = report_json
                    logger.info(f"  ✓ Report: {os.path.basename(report_txt)}")
                except Exception as e:
                    logger.warning(f"  ⚠️  Could not write stats/warnings report: {e}")

                logger.separator()
                _report_progress(progress_callback, 100, "Done")
            else:
                result.error_message = message
                logger.error(f"\n✗ Processing failed: {message}")
                logger.separator()
                _report_progress(progress_callback, 100, "Failed")

            return result

        except Exception as e:
            logger.error(f"Processing failed with exception: {e}")
            result.error_message = str(e)
            logger.separator()
            return result

    @staticmethod
    def write_processing_report(result: ProcessingResult, doc_type: str,
                                 source_files: List[str]) -> Tuple[str, str]:
        """
        Write a stand-alone stats/warnings report next to the merged PDF, so
        the full picture (every duplicate, every missing delivery, every
        warning) is available as a file - not just truncated to "first 5"
        inside a popup that closes when the user clicks OK.

        Writes two files, both alongside result.output_file:
          - "<merged filename>_Report.txt"  - human-readable
          - "<merged filename>_Report.json" - same data, machine-readable

        Returns:
            (txt_path, json_path)
        """
        output_file = result.output_file
        base, _ = os.path.splitext(output_file)
        txt_path = f"{base}_Report.txt"
        json_path = f"{base}_Report.json"

        report = result.validation_report
        generated_at = datetime.now()

        # --- Human-readable report -----------------------------------
        lines = []
        lines.append("=" * 70)
        lines.append("HDS ROUTE SEQUENCER - MERGE STATS & WARNINGS REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Mode: {doc_type}")
        lines.append(f"Output file: {os.path.basename(output_file)}")
        lines.append("")

        lines.append(f"SOURCE FILES ({len(source_files)}):")
        for f in source_files:
            lines.append(f"  - {os.path.basename(f)}")
        lines.append("")

        lines.append("PAGE STATISTICS:")
        if report:
            lines.append(f"  Total pages:         {report.total_pages}")
            lines.append(f"  Main pages:          {report.main_pages}")
            lines.append(f"  Continuation pages:  {report.continuation_pages}")
        lines.append(f"  Pages merged (docket count): {result.pages_merged}")
        lines.append("")

        routes_list = result.routes_detected if isinstance(result.routes_detected, list) else [result.routes_detected]
        lines.append(f"ROUTES DETECTED: {len(routes_list)}")
        if report and report.delivery_range:
            for route_num in sorted(report.delivery_range.keys()):
                min_d, max_d = report.delivery_range[route_num]
                lines.append(f"  Route {route_num}: Deliveries {min_d}-{max_d}")
        lines.append("")

        duplicates = report.duplicates if report else []
        lines.append(f"DUPLICATES ({len(duplicates)}):")
        if duplicates:
            for dup in duplicates:
                files = ", ".join(dup.get('files', []))
                lines.append(f"  - Route {dup['route']} - Delivery {dup['delivery']}: "
                              f"{dup['count']} occurrences ({files})")
        else:
            lines.append("  None")
        lines.append("")

        missing = report.missing_drops if report else []
        lines.append(f"MISSING DELIVERIES ({len(missing)}):")
        if missing:
            for miss in missing:
                lines.append(f"  - Route {miss['route']} - Delivery {miss['delivery']}")
        else:
            lines.append("  None")
        lines.append("")

        lines.append(f"WARNINGS ({len(result.warnings)}):")
        if result.warnings:
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        else:
            lines.append("  None")
        lines.append("")

        lines.append("=" * 70)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # --- Machine-readable twin ------------------------------------
        json_data = {
            "generated_at": generated_at.isoformat(),
            "mode": doc_type,
            "output_file": os.path.basename(output_file),
            "source_files": [os.path.basename(f) for f in source_files],
            "page_stats": {
                "total_pages": report.total_pages if report else None,
                "main_pages": report.main_pages if report else None,
                "continuation_pages": report.continuation_pages if report else None,
                "pages_merged": result.pages_merged,
            },
            "routes_detected": routes_list,
            "delivery_ranges": {
                str(route): list(rng) for route, rng in (report.delivery_range.items() if report else [])
            },
            "duplicates": duplicates,
            "missing_deliveries": missing,
            "warnings": result.warnings,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        return txt_path, json_path