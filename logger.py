"""
Logging system for HDS Route Sequencer
Handles console and file logging for processing operations
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProcessLogger:
    """Comprehensive logging system for HDS Route Sequencer"""
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize logger
        
        Args:
            log_dir: Directory to store log files. If None, uses 'logs' in current directory
        """
        self.log_dir = log_dir or os.path.join(os.getcwd(), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger("HDS_RouteSequencer")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-8s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-8s - [%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        log_file = os.path.join(self.log_dir, f"hds_route_sequencer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        self.log_file = log_file
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)
    
    def separator(self, title: str = "", char: str = "=", width: int = 70):
        """Log separator line"""
        if title:
            line = f" {title} ".center(width, char)
        else:
            line = char * width
        self.logger.info(line)
    
    def validation_report(self, report: dict):
        """Log validation report"""
        self.separator("VALIDATION REPORT", char="=")
        
        if 'total_pages' in report:
            self.info(f"Total Pages: {report['total_pages']}")
        if 'main_pages' in report:
            self.info(f"Main Pages: {report['main_pages']}")
        if 'continuation_pages' in report:
            self.info(f"Continuation Pages: {report['continuation_pages']}")
        
        if 'duplicates' in report and report['duplicates']:
            self.warning(f"DUPLICATES FOUND: {len(report['duplicates'])}")
            for dup in report['duplicates']:
                self.warning(f"  Route {dup.get('route')} - Delivery {dup.get('delivery')}: "
                           f"Found in {dup.get('first_file')} AND {dup.get('duplicate_file')}")
        
        if 'missing_drops' in report and report['missing_drops']:
            self.warning(f"MISSING DROPS: {len(report['missing_drops'])}")
            for miss in report['missing_drops']:
                self.warning(f"  Route {miss.get('route')} - Delivery {miss.get('delivery')}: NOT FOUND")
        
        self.separator()
    
    def processing_summary(self, result: dict):
        """Log processing summary"""
        self.separator("PROCESSING SUMMARY", char="=")
        
        if 'success' in result:
            status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
            self.info(f"Status: {status}")
        
        if 'file_count' in result:
            self.info(f"Files Processed: {result['file_count']}")
        
        if 'pages_merged' in result:
            self.info(f"Pages Merged: {result['pages_merged']}")
        
        if 'routes_detected' in result:
            self.info(f"Routes Detected: {len(result['routes_detected'])} - {result['routes_detected']}")
        
        if 'output_file' in result and result['output_file']:
            self.info(f"Output File: {result['output_file']}")
        
        if 'error_message' in result and result['error_message']:
            self.error(f"Error: {result['error_message']}")
        
        if 'warnings' in result and result['warnings']:
            self.warning(f"Warnings: {len(result['warnings'])}")
            for warning in result['warnings']:
                self.warning(f"  • {warning}")
        
        self.separator()
    
    def get_log_file(self) -> str:
        """Get current log file path"""
        return self.log_file


# Global logger instance
_global_logger: Optional[ProcessLogger] = None


def get_logger(log_dir: Optional[str] = None) -> ProcessLogger:
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = ProcessLogger(log_dir)
    return _global_logger


def reset_logger():
    """Reset global logger instance"""
    global _global_logger
    _global_logger = None
