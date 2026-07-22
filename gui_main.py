"""
Main GUI Application for HDS Route Sequencer
Modern PyQt6 interface with drag-and-drop, mode selection, and route preview
"""

import sys
import os
import time
from typing import List, Optional
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QListWidget, QListWidgetItem, QMessageBox,
        QFileDialog, QProgressBar, QTabWidget, QTextEdit, QDialog,
        QComboBox, QCheckBox, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, QMimeData, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QIcon, QDragEnterEvent, QDropEvent
    from PyQt6.QtCore import QSize
except ImportError:
    raise ImportError("PyQt6 is required. Install with: pip install PyQt6")

from models import ProcessingResult, MergeResult, ErrorReport
from pdf_detector import PDFValidator, PDFDetector
from route_sequencer import RouteSequencer, RoutePreview
from pdf_merger import PDFProcessor
from logger import get_logger, reset_logger
from dialogs import (
    PostMergeWorkflowDialog, PrintConfirmationDialog, 
    ErrorWarningDialog, PrintProgressDialog
)
from print_manager import WavePrinter, RunGrouper
from error_detector import ErrorDetector

# Styling constants
STYLE_MAIN = """
QMainWindow {
    background-color: #f5f5f5;
}
QWidget {
    background-color: #f5f5f5;
}
"""

STYLE_MESSAGE_BOX = """
QMessageBox {
    background-color: #ffffff;
}
QMessageBox QLabel {
    color: #000000;
}
QMessageBox QDialogButtonBox {
    button-layout: 0;
}
"""

STYLE_MODE_BUTTON = """
QPushButton {
    background-color: #ffffff;
    border: 2px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    font-size: 14pt;
    font-weight: bold;
    color: #333;
}
QPushButton:hover {
    border: 2px solid #007bff;
    background-color: #f0f8ff;
}
QPushButton:pressed {
    background-color: #007bff;
    color: white;
}
"""

STYLE_ACTION_BUTTON = """
QPushButton {
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 11pt;
}
QPushButton:hover {
    background-color: #218838;
}
QPushButton:pressed {
    background-color: #1e7e34;
}
"""

STYLE_DANGER_BUTTON = """
QPushButton {
    background-color: #dc3545;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 11pt;
}
QPushButton:hover {
    background-color: #c82333;
}
"""

STYLE_SECONDARY_BUTTON = """
QPushButton {
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 11pt;
}
QPushButton:hover {
    background-color: #5a6268;
}
"""

STYLE_DROP_ZONE = """
QListWidget {
    border: 3px dashed #007bff;
    border-radius: 12px;
    background-color: #f0f8ff;
    padding: 20px;
    min-height: 200px;
    font-size: 12pt;
    color: #000000;
}
QListWidget:focus {
    border: 3px solid #007bff;
    background-color: #e6f4ff;
    color: #000000;
}
QListWidget:hover {
    background-color: #e6f4ff;
    color: #000000;
}
QListWidgetItem {
    padding: 8px;
    border-radius: 4px;
    color: #000000;
}
"""

STYLE_DROP_ZONE_DRAG = """
QListWidget {
    border: 3px solid #28a745;
    border-radius: 12px;
    background-color: #e6f9e6;
    padding: 20px;
    font-size: 12pt;
}
"""

STYLE_STATUS_BAR = """
QLabel {
    padding: 12px;
    background-color: #ffffff;
    border-radius: 6px;
    border: 1px solid #ddd;
    font-weight: bold;
    font-size: 11pt;
    color: #000000;
}
"""

STYLE_INFO_LABEL = """
QLabel {
    color: #000000;
    font-weight: bold;
    font-size: 11pt;
}
"""

STYLE_PROGRESS_BAR = """
QProgressBar {
    border: 2px solid #007bff;
    border-radius: 8px;
    text-align: center;
    background-color: #f0f0f0;
    height: 30px;
}
QProgressBar::chunk {
    background-color: #28a745;
    border-radius: 6px;
}
"""

STYLE_OPERATION_LABEL = """
QLabel {
    color: #000000;
    font-weight: bold;
    font-size: 12pt;
    padding: 8px;
    background-color: #e3f2fd;
    border-radius: 4px;
    border: 1px solid #007bff;
}
"""


class DragDropListWidget(QListWidget):
    """Custom QListWidget with proper drag-and-drop support"""
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.is_dragging = False
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            self.is_dragging = True
            self.setStyleSheet(STYLE_DROP_ZONE_DRAG)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        self.is_dragging = False
        self.setStyleSheet(STYLE_DROP_ZONE)
    
    def dragMoveEvent(self, event):
        """Handle drag move event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        self.is_dragging = False
        self.setStyleSheet(STYLE_DROP_ZONE)
        
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if path.lower().endswith('.pdf'):
                    files.append(path)
        
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            event.ignore()


class ProcessWorker(QThread):
    """Worker thread for PDF processing"""
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(ProcessingResult)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_files: List[str], doc_type: str, output_folder: str):
        super().__init__()
        self.pdf_files = pdf_files
        self.doc_type = doc_type
        self.output_folder = output_folder
        self.current_progress = 0
    
    def emit_progress(self, target: int, steps: int = 10):
        """Emit progress gradually from current to target"""
        step_size = (target - self.current_progress) / steps
        for i in range(steps + 1):
            new_progress = int(self.current_progress + (step_size * i))
            if new_progress != self.current_progress:
                self.current_progress = new_progress
                self.progress_updated.emit(new_progress)
            time.sleep(0.1)  # Gradual update with 100ms delay
        self.current_progress = target
    
    def run(self):
        """Run processing in background thread"""
        try:
            # Gradual progress from 0 to 15 for initialization
            self.emit_progress(15, steps=5)
            
            # Gradual progress from 15 to 40 for validation
            self.emit_progress(40, steps=5)
            
            result = PDFProcessor.process_pdfs(
                self.pdf_files,
                self.doc_type,
                self.output_folder
            )
            
            # Gradual progress from 40 to 100 for completion
            self.emit_progress(100, steps=12)
            self.finished.emit(result)
        
        except Exception as e:
            self.error_occurred.emit(str(e))


class PrintWorker(QThread):
    """Worker thread for PDF printing"""
    progress_updated = pyqtSignal(dict)  # Emits progress dict
    finished = pyqtSignal(bool, str)  # Success and message
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_path: str, pages: List, batch_size: int = 25):
        super().__init__()
        self.pdf_path = pdf_path
        self.pages = pages
        self.batch_size = batch_size
        self.printer = None
    
    def run(self):
        """Run printing in background thread"""
        try:
            logger = get_logger()
            logger.info("Starting print worker thread...")
            
            # Create wave printer
            self.printer = WavePrinter(self.pdf_path, self.batch_size)
            
            # Start printing
            self.printer.start_print_queue(self.pages)
            
            # Monitor progress
            last_progress = -1
            while self.printer.is_printing:
                time.sleep(0.5)
                
                progress = self.printer.get_progress()
                if progress.overall_progress_percent != last_progress:
                    last_progress = progress.overall_progress_percent
                    
                    # Emit progress update
                    self.progress_updated.emit({
                        'current_batch': progress.current_batch,
                        'total_batches': progress.total_batches,
                        'pages_printed': progress.pages_printed,
                        'total_pages': progress.total_pages,
                        'run_range': progress.current_run_range,
                        'printer_status': progress.printer_status,
                        'progress_percent': progress.overall_progress_percent
                    })
            
            # Wait for print thread
            if self.printer.print_thread:
                self.printer.print_thread.join(timeout=10)
            
            # Check for errors
            if self.printer.progress.errors:
                error_msg = "\n".join(self.printer.progress.errors[:5])
                if len(self.printer.progress.errors) > 5:
                    error_msg += f"\n... and {len(self.printer.progress.errors) - 5} more"
                self.finished.emit(False, f"Print completed with errors:\n{error_msg}")
            else:
                self.finished.emit(True, f"Successfully printed {self.printer.progress.pages_printed} pages")
        
        except Exception as e:
            logger = get_logger()
            logger.error(f"Print worker error: {e}")
            self.error_occurred.emit(str(e))


class ModeSelectionDialog(QDialog):
    """Dialog for selecting processing mode"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HDS Route Sequencer - Select Mode")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet(STYLE_MAIN)
        self.selected_mode = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Select Processing Mode")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(header)
        
        subtitle = QLabel("Choose what type of documents you want to process")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Mode buttons
        button_layout = QHBoxLayout()
        
        # Picking Slips button
        picking_btn = QPushButton("📦 Picking Slips")
        picking_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        picking_btn.setMinimumHeight(120)
        picking_btn.setStyleSheet(STYLE_MODE_BUTTON)
        picking_btn.clicked.connect(lambda: self.select_mode("PICKING_SLIP"))
        button_layout.addWidget(picking_btn)
        
        # Spacer
        button_layout.addSpacing(30)
        
        # Delivery Dockets button
        delivery_btn = QPushButton("🚚 Delivery Dockets")
        delivery_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        delivery_btn.setMinimumHeight(120)
        delivery_btn.setStyleSheet(STYLE_MODE_BUTTON)
        delivery_btn.clicked.connect(lambda: self.select_mode("DELIVERY_DOCKET"))
        button_layout.addWidget(delivery_btn)
        
        layout.addLayout(button_layout)
        
        layout.addSpacing(20)
        
        # Info
        info_label = QLabel(
            "Picking Slips: For processing route picking sheets with R/D format\n"
            "Delivery Dockets: For processing delivery documents with Route No. format"
        )
        info_label.setFont(QFont("Arial", 10))
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def select_mode(self, mode: str):
        """Select mode and close dialog"""
        self.selected_mode = mode
        self.accept()


class RoutePreviewDialog(QDialog):
    """Dialog showing route preview before merge"""
    
    def __init__(self, preview: dict, parent=None):
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle("Route Preview - Review Before Merge")
        self.setGeometry(100, 100, 700, 600)
        self.setStyleSheet(STYLE_MAIN)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Route Preview")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Info
        info = QLabel(
            f"Routes: {self.preview['total_routes']} | "
            f"Main Pages: {self.preview['total_main_pages']}"
        )
        info.setFont(QFont("Arial", 11))
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)
        
        # Preview text
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setFont(QFont("Courier", 10))
        preview_text.setText(RoutePreview.format_preview(self.preview))
        layout.addWidget(preview_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        merge_btn = QPushButton("✓ Proceed with Merge")
        merge_btn.setStyleSheet(STYLE_ACTION_BUTTON)
        merge_btn.clicked.connect(self.accept)
        button_layout.addWidget(merge_btn)
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setStyleSheet(STYLE_DANGER_BUTTON)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize logger
        reset_logger()
        self.logger = get_logger()
        
        self.setWindowTitle("HDS Route Sequencer - Intelligent PDF Sequencing")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet(STYLE_MAIN)
        
        self.current_mode = None
        self.source_files = []
        self.output_folder = None
        self.worker = None
        self.print_worker = None
        
        # Workflow state tracking
        self.merged_pages = None  # Pages from merge operation
        self.merged_pdf_path = None  # Path to merged PDF
        self.sequenced_pages = None  # Pages after sequencing
        self.current_processing_result = None  # Latest processing result
        self.error_report = None  # Latest error report
        
        self.init_ui()
        self.show_mode_selection()
        self.show()
    
    def show_message(self, title: str, message: str, msg_type: str = "information"):
        """Show message box with proper text styling and larger font"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #000000;
                font-size: 13pt;
                font-weight: bold;
            }
            QMessageBox QDialogButtonBox {
                button-layout: 0;
            }
            QDialogButtonBox QPushButton {
                color: #ffffff;
                background-color: #6c757d;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12pt;
                min-width: 80px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        if msg_type == "information":
            msg_box.setIcon(QMessageBox.Icon.Information)
        elif msg_type == "warning":
            msg_box.setIcon(QMessageBox.Icon.Warning)
        elif msg_type == "critical":
            msg_box.setIcon(QMessageBox.Icon.Critical)
        
        msg_box.exec()
    
    def init_ui(self):
        """Initialize main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout()
        
        # Header
        self.header_label = QLabel()
        self.header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.header_label.setStyleSheet("color: #000000;")
        self.main_layout.addWidget(self.header_label)
        
        # Subtitle
        self.subtitle_label = QLabel()
        self.subtitle_label.setFont(QFont("Arial", 11))
        self.subtitle_label.setStyleSheet("color: #333333;")
        self.main_layout.addWidget(self.subtitle_label)
        
        self.main_layout.addSpacing(10)
        
        # File count display
        self.file_count_label = QLabel("📊 Files Loaded: 0")
        self.file_count_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.file_count_label.setStyleSheet("color: #000000;")
        self.main_layout.addWidget(self.file_count_label)
        
        # Files section
        files_label = QLabel("📄 PDF Files - Drag & Drop Zone")
        files_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        files_label.setStyleSheet("color: #000000;")
        self.main_layout.addWidget(files_label)
        
        files_layout = QHBoxLayout()
        
        # File list (drag-and-drop zone) - using custom widget
        self.files_list = DragDropListWidget()
        self.files_list.setMinimumHeight(200)
        self.files_list.setStyleSheet(STYLE_DROP_ZONE)
        self.files_list.files_dropped.connect(self.add_files_to_list)
        files_layout.addWidget(self.files_list)
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        self.add_btn = QPushButton("+ Add Files")
        self.add_btn.setStyleSheet(STYLE_SECONDARY_BUTTON)
        self.add_btn.clicked.connect(self.add_files)
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("- Remove Selected")
        self.remove_btn.setStyleSheet(STYLE_SECONDARY_BUTTON)
        self.remove_btn.clicked.connect(self.remove_file)
        btn_layout.addWidget(self.remove_btn)
        
        btn_layout.addStretch()
        
        files_layout.addLayout(btn_layout)
        
        self.main_layout.addLayout(files_layout)
        self.main_layout.addSpacing(15)
        
        # Operation label (shows current operation)
        self.operation_label = QLabel()
        self.operation_label.setStyleSheet(STYLE_OPERATION_LABEL)
        self.operation_label.setVisible(False)
        self.main_layout.addWidget(self.operation_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLE_PROGRESS_BAR)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(30)
        self.main_layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(STYLE_STATUS_BAR)
        self.main_layout.addWidget(self.status_label)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("👁️ Preview Routes")
        self.preview_btn.setStyleSheet(STYLE_SECONDARY_BUTTON)
        self.preview_btn.clicked.connect(self.show_preview)
        action_layout.addWidget(self.preview_btn)
        
        self.merge_btn = QPushButton("🔗 Merge & Sequence")
        self.merge_btn.setStyleSheet(STYLE_ACTION_BUTTON)
        self.merge_btn.clicked.connect(self.merge_files)
        action_layout.addWidget(self.merge_btn)
        
        self.open_output_btn = QPushButton("📂 Open Output Folder")
        self.open_output_btn.setStyleSheet(STYLE_ACTION_BUTTON)
        self.open_output_btn.clicked.connect(self.open_output_folder)
        self.open_output_btn.setVisible(False)
        action_layout.addWidget(self.open_output_btn)
        
        self.main_layout.addLayout(action_layout)
        
        central_widget.setLayout(self.main_layout)
    
    def show_mode_selection(self):
        """Show mode selection dialog"""
        dialog = ModeSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_mode = dialog.selected_mode
            self.update_mode_display()
        else:
            sys.exit()
    
    def update_mode_display(self):
        """Update UI to reflect selected mode"""
        if self.current_mode == "PICKING_SLIP":
            self.header_label.setText("📦 Processing Mode: Picking Slips")
            self.subtitle_label.setText("Upload Picking Slip PDFs (R D format). They will be sequenced and merged.")
        else:
            self.header_label.setText("🚚 Processing Mode: Delivery Dockets")
            self.subtitle_label.setText("Upload Delivery Docket PDFs (Route No. format). They will be sequenced and merged.")
        
        self.update_status()
    
    
    def add_files(self):
        """Open file dialog to add files"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files",
            "",
            "PDF Files (*.pdf)"
        )
        
        if files:
            self.add_files_to_list(files)
    
    def add_files_to_list(self, files: List[str]):
        """Add files to list"""
        for file_path in files:
            if file_path not in self.source_files:
                self.source_files.append(file_path)
                self.files_list.addItem(os.path.basename(file_path))
        
        self.update_status()
    
    def remove_file(self):
        """Remove selected file from list"""
        current_row = self.files_list.currentRow()
        if current_row >= 0:
            self.files_list.takeItem(current_row)
            if current_row < len(self.source_files):
                self.source_files.pop(current_row)
        
        self.update_status()
    
    def update_status(self):
        """Update status label and file count"""
        file_count = len(self.source_files)
        self.file_count_label.setText(f"📊 Files Loaded: {file_count}")
        
        if file_count == 0:
            self.status_label.setText("⚠️ No files selected. Drag-and-drop or click 'Add Files'.")
            self.status_label.setStyleSheet("color: #d9534f; " + STYLE_STATUS_BAR)
        else:
            self.status_label.setText(f"✓ Ready: {file_count} file(s) ready to process")
            self.status_label.setStyleSheet("color: #5cb85c; " + STYLE_STATUS_BAR)
    
    def show_preview(self):
        """Show route preview"""
        if not self.source_files:
            self.show_message("No Files", "Please add files first", "warning")
            return
        
        try:
            self.status_label.setText("🔍 Analyzing files...")
            
            # Validate files
            all_valid, valid_files, errors = PDFValidator.validate_file_collection(
                self.source_files,
                self.current_mode
            )
            
            if not all_valid:
                error_msg = "Some files are invalid:\n\n" + "\n".join(errors)
                self.show_message("Invalid Files", error_msg, "warning")
                self.update_status()
                return
            
            # Extract and sequence
            all_pages = []
            for pdf_file in valid_files:
                pages = RouteSequencer.extract_pages(pdf_file, self.current_mode)
                all_pages.extend(pages)
            
            sequenced_pages = RouteSequencer.sequence_pages(all_pages)
            preview = RoutePreview.get_route_preview(sequenced_pages)
            
            # Show preview dialog
            dialog = RoutePreviewDialog(preview, self)
            dialog.exec()
            
            self.update_status()
        
        except Exception as e:
            self.logger.error(f"Preview failed: {e}")
            self.show_message("Error", f"Preview failed: {e}", "critical")
            self.update_status()
    
    def merge_files(self):
        """Merge files - hardcoded to Downloads folder"""
        if not self.source_files:
            self.show_message("No Files", "Please add files first", "warning")
            return
        
        # Hardcode to Downloads folder
        output_folder = os.path.expanduser("~/Downloads")
        
        # Ensure Downloads folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        self.output_folder = output_folder
        
        # Validate files
        all_valid, valid_files, errors = PDFValidator.validate_file_collection(
            self.source_files,
            self.current_mode
        )
        
        if not all_valid:
            error_msg = "Some files are invalid:\n\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more"
            self.show_message("Invalid Files", error_msg, "warning")
            return
        
        # Disable controls during processing
        self.disable_controls(True)
        
        # Show progress and operation label
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.operation_label.setVisible(True)
        self.operation_label.setText("🔄 Starting processing... (0%)")
        self.status_label.setText(f"⏳ Processing {len(valid_files)} file(s)... (0%)")
        self.status_label.setStyleSheet("color: #007bff; " + STYLE_STATUS_BAR)
        
        # Start worker thread
        self.worker = ProcessWorker(valid_files, self.current_mode, output_folder)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error_occurred.connect(self.on_processing_error)
        self.worker.start()
    
    def update_progress(self, value: int):
        """Update progress bar and show operation status with percentage"""
        self.progress_bar.setValue(value)
        
        # Determine operation step and status message
        if value < 25:
            step = "Validating PDF files"
            emoji = "🔍"
        elif value < 50:
            step = "Extracting routes and deliveries"
            emoji = "📍"
        elif value < 75:
            step = "Sequencing and merging pages"
            emoji = "🔗"
        elif value < 95:
            step = "Saving output files"
            emoji = "💾"
        else:
            step = "Finalizing"
            emoji = "✅"
        
        # Update labels with exact percentage
        self.operation_label.setText(f"{emoji} {step}... ({value}%)")
        self.status_label.setText(f"⏳ Processing... ({value}% complete)")
        self.status_label.setStyleSheet("color: #007bff; " + STYLE_STATUS_BAR)
    
    def disable_controls(self, disabled: bool):
        """Enable or disable all control buttons"""
        self.add_btn.setEnabled(not disabled)
        self.remove_btn.setEnabled(not disabled)
        self.preview_btn.setEnabled(not disabled)
        self.merge_btn.setEnabled(not disabled)
        self.files_list.setEnabled(not disabled)
    
    def on_processing_finished(self, result: ProcessingResult):
        """Handle processing completion - show post-merge workflow dialog"""
        # Re-enable controls
        self.disable_controls(False)
        self.progress_bar.setVisible(False)
        self.operation_label.setVisible(False)
        
        if not result.success:
            # Show error
            self.show_message("❌ Processing Failed", f"Processing failed:\n\n{result.error_message}", "critical")
            self.status_label.setText("✗ Processing failed - please check error details")
            self.status_label.setStyleSheet("color: #a32e2e; " + STYLE_STATUS_BAR)
            self.logger.error(f"Processing failed: {result.error_message}")
            return
        
        # Store result for later use
        self.current_processing_result = result
        self.merged_pdf_path = result.output_file
        
        # Build comprehensive statistics message
        msg = f"✅ PDF Merge Successful!\n\n"
        msg += f"📊 MERGE STATISTICS:\n"
        
        # Get validation report
        if result.validation_report:
            report = result.validation_report
            msg += f"  • Total Pages: {report.total_pages}\n"
            msg += f"  • Main Pages: {report.main_pages}\n"
            msg += f"  • Continuation Pages: {report.continuation_pages}\n"
        
        msg += f"  • Pages Merged: {result.pages_merged}\n"
        
        # Routes information
        routes_list = result.routes_detected if isinstance(result.routes_detected, list) else [result.routes_detected]
        routes_count = len(routes_list)
        msg += f"\n📍 ROUTE INFORMATION:\n"
        msg += f"  • Routes Detected: {routes_count}\n"
        
        if result.validation_report and result.validation_report.delivery_range:
            delivery_range = result.validation_report.delivery_range
            for route_num in sorted(delivery_range.keys())[:10]:  # Show first 10 routes
                min_delivery, max_delivery = delivery_range[route_num]
                msg += f"    Route {route_num}: Deliveries {min_delivery}-{max_delivery}\n"
            if len(delivery_range) > 10:
                msg += f"    ... and {len(delivery_range) - 10} more routes\n"
        
        # Issues summary
        if result.validation_report:
            report = result.validation_report
            duplicates_count = len(report.duplicates) if report.duplicates else 0
            missing_count = len(report.missing_drops) if report.missing_drops else 0
            
            if duplicates_count > 0 or missing_count > 0:
                msg += f"\n⚠️  ISSUES DETECTED:\n"
                if duplicates_count > 0:
                    msg += f"  • Duplicate Pages: {duplicates_count}\n"
                if missing_count > 0:
                    msg += f"  • Missing Deliveries: {missing_count}\n"
        
        # Output file info
        msg += f"\n📁 OUTPUT:\n"
        msg += f"  • File: {os.path.basename(result.output_file)}\n"
        msg += f"  • Location: {self.output_folder}\n"
        
        # Warnings if any
        if result.warnings:
            msg += f"\n⚠️  WARNINGS ({len(result.warnings)}):\n"
            for warning in result.warnings[:5]:
                msg += f"  • {warning}\n"
            if len(result.warnings) > 5:
                msg += f"  • ... and {len(result.warnings) - 5} more\n"
        
        self.show_message("✅ Merge Complete", msg, "information")
        
        # Show post-merge workflow dialog
        self.show_post_merge_workflow_dialog(result)
    
    def show_post_merge_workflow_dialog(self, result: ProcessingResult):
        """Show dialog asking what to do next after merge"""
        dialog = PostMergeWorkflowDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action = dialog.get_selected_action()
            
            if action == "PICKING_DOCKET":
                self.process_as_picking("Post-merge resequencing")
            elif action == "DELIVERY_DOCKET":
                self.process_as_delivery("Post-merge resequencing")
            elif action == "SAVE_AND_EXIT":
                # Build save completion message with stats
                save_msg = "✓ PDF saved successfully!\n\n"
                save_msg += "📊 MERGE SUMMARY:\n"
                
                if result.validation_report:
                    report = result.validation_report
                    save_msg += f"  • Total Pages: {report.total_pages}\n"
                    save_msg += f"  • Main Pages: {report.main_pages}\n"
                    save_msg += f"  • Continuation Pages: {report.continuation_pages}\n"
                
                routes_list = result.routes_detected if isinstance(result.routes_detected, list) else [result.routes_detected]
                routes_count = len(routes_list)
                save_msg += f"  • Routes Detected: {routes_count}\n"
                
                if result.validation_report:
                    report = result.validation_report
                    duplicates_count = len(report.duplicates) if report.duplicates else 0
                    missing_count = len(report.missing_drops) if report.missing_drops else 0
                    if duplicates_count > 0 or missing_count > 0:
                        save_msg += f"\n⚠️  Issues:\n"
                        if duplicates_count > 0:
                            save_msg += f"  • Duplicate Pages: {duplicates_count}\n"
                        if missing_count > 0:
                            save_msg += f"  • Missing Deliveries: {missing_count}\n"
                
                save_msg += f"\n📁 OUTPUT FILE:\n"
                save_msg += f"  • File: {os.path.basename(result.output_file)}\n"
                save_msg += f"  • Location: {self.output_folder}\n\n"
                save_msg += f"You can now close the application."
                
                self.show_message("✓ Complete", save_msg, "information")
                self.status_label.setText("✓ Processing complete! Output folder ready.")
                self.status_label.setStyleSheet("color: #2d5016; " + STYLE_STATUS_BAR)
                self.open_output_btn.setVisible(True)
    
    def process_as_picking(self, stage_label: str):
        """Process merged PDF as picking dockets"""
        try:
            self.disable_controls(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(50)
            self.operation_label.setVisible(True)
            self.operation_label.setText(f"🔄 {stage_label}: Applying Picking Docket sequencing... (50%)")
            self.status_label.setText("⏳ Resequencing as Picking Dockets...")
            self.status_label.setStyleSheet("color: #007bff; " + STYLE_STATUS_BAR)
            
            # For now, just continue to printing (actual resequencing would go here)
            self.show_print_confirmation_dialog(self.merged_pdf_path)
            
            self.progress_bar.setVisible(False)
            self.operation_label.setVisible(False)
            self.disable_controls(False)
        except Exception as e:
            self.on_processing_error(str(e))
    
    def process_as_delivery(self, stage_label: str):
        """Process merged PDF as delivery dockets"""
        try:
            self.disable_controls(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(50)
            self.operation_label.setVisible(True)
            self.operation_label.setText(f"🔄 {stage_label}: Applying Delivery Docket sequencing... (50%)")
            self.status_label.setText("⏳ Resequencing as Delivery Dockets...")
            self.status_label.setStyleSheet("color: #007bff; " + STYLE_STATUS_BAR)
            
            # For now, just continue to printing (actual resequencing would go here)
            self.show_print_confirmation_dialog(self.merged_pdf_path)
            
            self.progress_bar.setVisible(False)
            self.operation_label.setVisible(False)
            self.disable_controls(False)
        except Exception as e:
            self.on_processing_error(str(e))
    
    def show_print_confirmation_dialog(self, pdf_path: str):
        """Show print confirmation dialog"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            
            dialog = PrintConfirmationDialog(os.path.basename(pdf_path), page_count, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                choice = dialog.get_choice()
                
                if choice == "PRINT_NOW":
                    self.start_printing(pdf_path)
                elif choice == "SAVE_ONLY":
                    self.show_message("✓ Complete", "PDF saved successfully.", "information")
                    self.status_label.setText("✓ Processing complete! Output folder ready.")
                    self.status_label.setStyleSheet("color: #2d5016; " + STYLE_STATUS_BAR)
                    self.open_output_btn.setVisible(True)
                # Cancel does nothing
        except Exception as e:
            self.logger.error(f"Print confirmation failed: {e}")
    
    def start_printing(self, pdf_path: str):
        """Start the printing process"""
        try:
            # Detect errors first
            self.disable_controls(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.operation_label.setVisible(True)
            self.operation_label.setText("🔍 Detecting document errors... (10%)")
            self.status_label.setText("⏳ Analyzing document for errors...")
            self.status_label.setStyleSheet("color: #007bff; " + STYLE_STATUS_BAR)
            
            # Get pages from merged PDF
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            
            # Create dummy PageInfo objects for error detection
            pages = []
            for idx, _ in enumerate(reader.pages):
                from models import PageInfo
                # Extract basic info
                page_info = PageInfo(
                    page_num=idx,
                    source_file=os.path.basename(pdf_path),
                    route=None,  # Would be extracted from actual PDF
                    delivery=None
                )
                pages.append(page_info)
            
            # Detect errors
            self.error_report = ErrorDetector.detect_all_errors(pages)
            self.progress_bar.setValue(30)
            
            # Check if we should warn
            should_warn, reason = ErrorDetector.should_warn_before_print(self.error_report)
            
            if should_warn:
                # Show error warning dialog
                dialog = ErrorWarningDialog(self.error_report, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    choice = dialog.get_choice()
                    if choice == "CONTINUE":
                        self.continue_with_printing(pdf_path, pages)
                    else:
                        # User cancelled
                        self.disable_controls(False)
                        self.progress_bar.setVisible(False)
                        self.operation_label.setVisible(False)
                        self.status_label.setText("Printing cancelled.")
                        self.status_label.setStyleSheet("color: #ff9800; " + STYLE_STATUS_BAR)
            else:
                self.continue_with_printing(pdf_path, pages)
        
        except Exception as e:
            self.logger.error(f"Print start failed: {e}")
            self.on_processing_error(f"Failed to start printing: {e}")
    
    def continue_with_printing(self, pdf_path: str, pages: List):
        """Continue with actual printing"""
        try:
            self.disable_controls(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(40)
            self.operation_label.setVisible(True)
            self.operation_label.setText("🖨️  Starting print queue... (40%)")
            self.status_label.setText("⏳ Starting printing process...")
            self.status_label.setStyleSheet("color: #007bff; " + STYLE_STATUS_BAR)
            
            # Start print worker
            self.print_worker = PrintWorker(pdf_path, pages, batch_size=25)
            self.print_worker.progress_updated.connect(self.on_print_progress)
            self.print_worker.finished.connect(self.on_print_finished)
            self.print_worker.error_occurred.connect(self.on_print_error)
            self.print_worker.start()
        
        except Exception as e:
            self.logger.error(f"Print continue failed: {e}")
            self.on_processing_error(f"Failed to continue printing: {e}")
    
    def on_print_progress(self, progress_dict: dict):
        """Handle print progress updates"""
        current_batch = progress_dict.get('current_batch', 0)
        total_batches = progress_dict.get('total_batches', 1)
        pages_printed = progress_dict.get('pages_printed', 0)
        total_pages = progress_dict.get('total_pages', 1)
        run_range = progress_dict.get('run_range', (0, 0))
        progress_percent = progress_dict.get('progress_percent', 0)
        
        self.progress_bar.setValue(40 + int(progress_percent * 0.6))  # 40-100%
        self.operation_label.setText(
            f"🖨️  Printing Wave {current_batch}/{total_batches} "
            f"(Runs {run_range[0]:04d}-{run_range[1]:04d})... "
            f"({pages_printed}/{total_pages} pages)"
        )
        self.status_label.setText(f"⏳ Printing... ({progress_percent}% complete)")
    
    def on_print_finished(self, success: bool, message: str):
        """Handle print completion with comprehensive statistics"""
        self.disable_controls(False)
        self.progress_bar.setVisible(False)
        self.operation_label.setVisible(False)
        
        # Build comprehensive print stats message
        stats_msg = ""
        if self.print_worker and self.print_worker.printer:
            progress = self.print_worker.printer.get_progress()
            stats_msg += f"\n\n📊 PRINT STATISTICS:\n"
            stats_msg += f"  • Total Pages Printed: {progress.pages_printed} / {progress.total_pages}\n"
            stats_msg += f"  • Total Waves: {progress.total_batches}\n"
            stats_msg += f"  • Waves Completed: {progress.batches_completed}\n"
            
            if progress.batches_failed > 0:
                stats_msg += f"  • Waves Failed: {progress.batches_failed}\n"
            
            if progress.errors:
                stats_msg += f"\n⚠️  PRINT ERRORS ({len(progress.errors)}):\n"
                for error in progress.errors[:5]:
                    stats_msg += f"  • {error}\n"
                if len(progress.errors) > 5:
                    stats_msg += f"  • ... and {len(progress.errors) - 5} more\n"
        
        if success:
            full_message = f"✅ {message}" + stats_msg
            self.show_message("✅ Printing Complete", full_message, "information")
            self.status_label.setText("✓ Printing complete!")
            self.status_label.setStyleSheet("color: #2d5016; " + STYLE_STATUS_BAR)
        else:
            full_message = f"⚠️  {message}" + stats_msg
            self.show_message("⚠️  Printing Complete with Issues", full_message, "warning")
            self.status_label.setText("⚠️  Printing complete with issues")
            self.status_label.setStyleSheet("color: #ff9800; " + STYLE_STATUS_BAR)
        
        self.open_output_btn.setVisible(True)
    
    def on_print_error(self, error_msg: str):
        """Handle print error"""
        self.disable_controls(False)
        self.progress_bar.setVisible(False)
        self.operation_label.setVisible(False)
        
        self.show_message("❌ Print Error", f"An error occurred during printing:\n\n{error_msg}", "critical")
        self.status_label.setText("✗ Printing error - please try again")
        self.status_label.setStyleSheet("color: #a32e2e; " + STYLE_STATUS_BAR)
        self.logger.error(f"Print error: {error_msg}")
    
    def on_processing_error(self, error_msg: str):
        """Handle processing error"""
        # Re-enable controls
        self.disable_controls(False)
        self.progress_bar.setVisible(False)
        self.operation_label.setVisible(False)
        
        self.show_message("❌ Processing Error", f"An error occurred during processing:\n\n{error_msg}", "critical")
        self.status_label.setText("✗ Processing error - please try again")
        self.status_label.setStyleSheet("color: #a32e2e; " + STYLE_STATUS_BAR)
        
        self.logger.error(f"Processing error: {error_msg}")
    
    def open_output_folder(self):
        """Open output folder"""
        if self.output_folder and os.path.isdir(self.output_folder):
            try:
                os.startfile(self.output_folder)
            except Exception as e:
                self.show_message("Error", f"Could not open folder: {e}", "warning")
        else:
            self.show_message("No Output Folder", "Process files first or select an output folder", "warning")


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
