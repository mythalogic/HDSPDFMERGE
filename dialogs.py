"""
Dialog components for HDS Route Sequencer
Custom dialogs for workflow, printing, and error handling
"""

import sys
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QTextEdit, QProgressBar, QMessageBox, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
except ImportError:
    raise ImportError("PyQt6 is required. Install with: pip install PyQt6")

from models import ErrorReport
from error_detector import ErrorDetector

# Styling
STYLE_MAIN = """
QDialog {
    background-color: #f5f5f5;
}
QLabel {
    color: #000000;
}
"""

STYLE_DIALOG_BUTTON = """
QPushButton {
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 11pt;
    min-width: 100px;
}
QPushButton:hover {
    background-color: #218838;
}
QPushButton:pressed {
    background-color: #1e7e34;
}
"""

STYLE_SECONDARY_BUTTON = """
QPushButton {
    background-color: #6c757d;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 11pt;
    min-width: 100px;
}
QPushButton:hover {
    background-color: #5a6268;
}
"""

STYLE_DANGER_BUTTON = """
QPushButton {
    background-color: #dc3545;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 11pt;
    min-width: 100px;
}
QPushButton:hover {
    background-color: #c82333;
}
"""

STYLE_HEADER = """
QLabel {
    color: #000000;
    font-weight: bold;
    font-size: 16pt;
    padding: 10px;
    background-color: #e3f2fd;
    border-radius: 4px;
    border: 1px solid #007bff;
}
"""

STYLE_INFO_TEXT = """
QLabel {
    color: #333333;
    font-size: 12pt;
    padding: 8px;
}
"""

STYLE_TEXT_EDIT = """
QTextEdit {
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #ffffff;
    color: #000000;
    padding: 8px;
    font-family: 'Courier New';
    font-size: 10pt;
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


class PostMergeWorkflowDialog(QDialog):
    """
    Dialog for selecting what to do after merge
    
    Options:
    1. Process Picking Dockets
    2. Process Delivery Dockets
    3. Save and Exit
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Next Step - Select Processing Mode")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet(STYLE_MAIN)
        self.selected_action = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("✓ PDF Merge Complete!\n\nWhat would you like to do next?")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet(STYLE_HEADER)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        layout.addSpacing(20)
        
        # Info
        info = QLabel(
            "You have successfully merged all PDF files.\n"
            "Now choose how to process and sequence the merged document:"
        )
        info.setFont(QFont("Arial", 11))
        info.setStyleSheet("color: #666; padding: 10px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # Option 1: Process as Picking Dockets
        picking_btn = QPushButton("📦 Process as Picking Dockets")
        picking_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        picking_btn.setMinimumHeight(60)
        picking_btn.setStyleSheet(STYLE_DIALOG_BUTTON)
        picking_btn.clicked.connect(lambda: self.select_action("PICKING_DOCKET"))
        button_layout.addWidget(picking_btn)
        
        # Option 2: Process as Delivery Dockets
        delivery_btn = QPushButton("🚚 Process as Delivery Dockets")
        delivery_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        delivery_btn.setMinimumHeight(60)
        delivery_btn.setStyleSheet(STYLE_DIALOG_BUTTON)
        delivery_btn.clicked.connect(lambda: self.select_action("DELIVERY_DOCKET"))
        button_layout.addWidget(delivery_btn)
        
        # Option 3: Save and Exit
        save_btn = QPushButton("💾 Save and Exit")
        save_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        save_btn.setMinimumHeight(60)
        save_btn.setStyleSheet(STYLE_SECONDARY_BUTTON)
        save_btn.clicked.connect(lambda: self.select_action("SAVE_AND_EXIT"))
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def select_action(self, action: str):
        """Select action and close dialog"""
        self.selected_action = action
        self.accept()
    
    def get_selected_action(self) -> Optional[str]:
        """Get selected action"""
        return self.selected_action


class PrintConfirmationDialog(QDialog):
    """
    Dialog for confirming print action
    
    Shows: "Processing Complete. Would you like to print the document now?"
    Options: Print Now, Save Only, Cancel
    """
    
    def __init__(self, output_filename: str, page_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Confirmation")
        self.setGeometry(100, 100, 600, 350)
        self.setStyleSheet(STYLE_MAIN)
        self.output_filename = output_filename
        self.page_count = page_count
        self.user_choice = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("✅ Processing Complete!")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet(STYLE_HEADER)
        layout.addWidget(header)
        
        layout.addSpacing(15)
        
        # Question
        question = QLabel("Would you like to print the document now?")
        question.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        question.setStyleSheet(STYLE_INFO_TEXT)
        layout.addWidget(question)
        
        # Details
        details = QLabel(
            f"File: {self.output_filename}\n"
            f"Pages: {self.page_count}\n\n"
            f"Choose an option below:"
        )
        details.setFont(QFont("Arial", 11))
        details.setStyleSheet("color: #333; padding: 10px; background-color: #f9f9f9; border-radius: 4px;")
        layout.addWidget(details)
        
        layout.addSpacing(15)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Print Now
        print_btn = QPushButton("🖨️  Print Now")
        print_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        print_btn.setMinimumHeight(50)
        print_btn.setStyleSheet(STYLE_DIALOG_BUTTON)
        print_btn.clicked.connect(lambda: self.select_choice("PRINT_NOW"))
        button_layout.addWidget(print_btn)
        
        # Save Only
        save_btn = QPushButton("💾 Save Only")
        save_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        save_btn.setMinimumHeight(50)
        save_btn.setStyleSheet(STYLE_SECONDARY_BUTTON)
        save_btn.clicked.connect(lambda: self.select_choice("SAVE_ONLY"))
        button_layout.addWidget(save_btn)
        
        # Cancel
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        cancel_btn.setMinimumHeight(50)
        cancel_btn.setStyleSheet(STYLE_DANGER_BUTTON)
        cancel_btn.clicked.connect(lambda: self.select_choice("CANCEL"))
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def select_choice(self, choice: str):
        """Select choice and close dialog"""
        self.user_choice = choice
        self.accept()
    
    def get_choice(self) -> Optional[str]:
        """Get user's choice"""
        return self.user_choice


class ErrorWarningDialog(QDialog):
    """
    Dialog showing detected errors before printing
    
    Allows user to review errors and choose to continue or cancel
    """
    
    def __init__(self, error_report: ErrorReport, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️  Error Detection Report")
        self.setGeometry(100, 100, 700, 600)
        self.setStyleSheet(STYLE_MAIN)
        self.error_report = error_report
        self.user_choice = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        if self.error_report.has_critical_errors:
            header_text = "🚨 CRITICAL ERRORS DETECTED"
            header_color = "#dc3545"
        elif self.error_report.has_warnings:
            header_text = "⚠️  WARNINGS DETECTED"
            header_color = "#ff9800"
        else:
            header_text = "✓ No Issues Found"
            header_color = "#28a745"
        
        header = QLabel(header_text)
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-weight: bold;
                font-size: 14pt;
                padding: 12px;
                background-color: {header_color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(header)
        
        # Error summary
        error_text = QTextEdit()
        error_text.setReadOnly(True)
        error_text.setStyleSheet(STYLE_TEXT_EDIT)
        error_text.setMinimumHeight(300)
        
        # Get error summary
        summary = ErrorDetector.get_error_summary_text(self.error_report)
        error_text.setText(summary)
        layout.addWidget(error_text)
        
        # Warning message
        if self.error_report.has_critical_errors:
            warning = QLabel(
                "❌ Critical errors detected. Printing is NOT recommended.\n"
                "Please review and resolve these issues before printing."
            )
            warning.setStyleSheet("color: #dc3545; font-weight: bold; padding: 10px;")
        elif self.error_report.has_warnings:
            warning = QLabel(
                "⚠️  Issues have been detected. You can continue printing, but be aware of potential problems.\n"
                "Review the report above before proceeding."
            )
            warning.setStyleSheet("color: #ff9800; font-weight: bold; padding: 10px;")
        else:
            warning = QLabel("✓ No errors or warnings detected. Safe to print.")
            warning.setStyleSheet("color: #28a745; font-weight: bold; padding: 10px;")
        
        layout.addWidget(warning)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        if not self.error_report.has_critical_errors:
            # Continue button
            continue_btn = QPushButton("✓ Continue Printing")
            continue_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            continue_btn.setMinimumHeight(45)
            continue_btn.setStyleSheet(STYLE_DIALOG_BUTTON)
            continue_btn.clicked.connect(lambda: self.select_choice("CONTINUE"))
            button_layout.addWidget(continue_btn)
        else:
            # For critical errors, disable continue
            info = QLabel("Printing disabled due to critical errors.")
            info.setStyleSheet("color: #dc3545; font-weight: bold;")
            button_layout.addWidget(info)
        
        # Cancel button
        cancel_btn = QPushButton("✗ Cancel Printing")
        cancel_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        cancel_btn.setMinimumHeight(45)
        cancel_btn.setStyleSheet(STYLE_DANGER_BUTTON)
        cancel_btn.clicked.connect(lambda: self.select_choice("CANCEL"))
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def select_choice(self, choice: str):
        """Select choice and close dialog"""
        self.user_choice = choice
        self.accept()
    
    def get_choice(self) -> Optional[str]:
        """Get user's choice"""
        return self.user_choice


class PrintProgressDialog(QDialog):
    """
    Real-time print progress dialog
    Shows current batch, pages printed, and overall progress
    """
    
    update_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Progress")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet(STYLE_MAIN)
        self.user_choice = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("🖨️  Printing in Progress...")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet(STYLE_HEADER)
        layout.addWidget(header)
        
        # Current batch info
        self.current_batch_label = QLabel("Current Batch: Wave 0 (Runs 0000-0000)")
        self.current_batch_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.current_batch_label.setStyleSheet(STYLE_INFO_TEXT)
        layout.addWidget(self.current_batch_label)
        
        # Pages info
        self.pages_label = QLabel("Pages Printed: 0 / 0")
        self.pages_label.setFont(QFont("Arial", 11))
        self.pages_label.setStyleSheet(STYLE_INFO_TEXT)
        layout.addWidget(self.pages_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(STYLE_PROGRESS_BAR)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(STYLE_TEXT_EDIT)
        self.status_text.setMinimumHeight(150)
        layout.addWidget(self.status_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.pause_btn = QPushButton("⏸️  Pause")
        self.pause_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.pause_btn.setMinimumHeight(45)
        self.pause_btn.setStyleSheet(STYLE_SECONDARY_BUTTON)
        self.pause_btn.clicked.connect(lambda: self.select_choice("PAUSE"))
        button_layout.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton("✗ Cancel")
        self.cancel_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.cancel_btn.setMinimumHeight(45)
        self.cancel_btn.setStyleSheet(STYLE_DANGER_BUTTON)
        self.cancel_btn.clicked.connect(lambda: self.select_choice("CANCEL"))
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_progress(self, current_batch: int, total_batches: int, 
                       pages_printed: int, total_pages: int, 
                       run_range: tuple, printer_status: str):
        """Update progress display"""
        self.current_batch_label.setText(
            f"Current Batch: Wave {current_batch} / {total_batches} "
            f"(Runs {run_range[0]:04d}-{run_range[1]:04d})"
        )
        
        self.pages_label.setText(
            f"Pages Printed: {pages_printed} / {total_pages} "
            f"({int((pages_printed/total_pages*100) if total_pages > 0 else 0)}%)"
        )
        
        progress_percent = int((pages_printed / total_pages * 100) if total_pages > 0 else 0)
        self.progress_bar.setValue(progress_percent)
        
        status_msg = f"Wave {current_batch}: Printing runs {run_range[0]:04d}-{run_range[1]:04d}...\nPrinter: {printer_status}"
        self.status_text.setText(status_msg)
    
    def add_status_line(self, message: str):
        """Add a line to status text"""
        current = self.status_text.toPlainText()
        self.status_text.setText(current + "\n" + message if current else message)
    
    def select_choice(self, choice: str):
        """Select choice"""
        self.user_choice = choice
        if choice == "CANCEL":
            self.accept()
    
    def get_choice(self) -> Optional[str]:
        """Get user's choice"""
        return self.user_choice
