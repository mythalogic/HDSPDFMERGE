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
        default_base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        self.log_dir = log_dir or os.path.join(default_base, "HDS Route Sequencer", "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        self.logger = logging.getLogger("HDS_RouteSequencer")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-8s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)-8s - [%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        log_file = os.path.join(self.log_dir, f"hds_route_sequencer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        self.log_file = log_file

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def critical(self, message: str):
        self.logger.critical(message)

    def separator(self, title: str = "", char: str = "=", width: int = 70):
        if title:
            line = f" {title} ".center(width, char)
        else:
            line = char * width
        self.logger.info(line)

    def get_log_file(self) -> str:
        return self.log_file


_global_logger: Optional[ProcessLogger] = None


def get_logger(log_dir: Optional[str] = None) -> ProcessLogger:
    global _global_logger
    if _global_logger is None:
        _global_logger = ProcessLogger(log_dir)
    return _global_logger


def reset_logger():
    global _global_logger
    _global_logger = None
