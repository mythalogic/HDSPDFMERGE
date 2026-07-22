#!/usr/bin/env python3
"""
HDS Route Sequencer - Production-Ready Desktop Application
Intelligent PDF route sequencing and merging system

Entry point for the application. Uses modular architecture with:
- gui_main.py: PyQt6 GUI application  
- pdf_detector.py: PDF type detection and validation
- route_sequencer.py: Route and delivery number extraction
- pdf_merger.py: PDF merging operations
- logger.py: Comprehensive logging
- models.py: Data models

Usage:
    python hds_route_sequencer.py
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui_main import main


if __name__ == '__main__':
    main()
