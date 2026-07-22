# HDS Route Sequencer - Intelligent PDF Processing Application

A production-ready Python desktop application for processing HDS Picking Slips and Delivery Dockets with intelligent route sequencing and PDF merging.

## Features

### 🎯 Core Features
- **Dual-Mode Processing**: Process Picking Slips (R D format) or Delivery Dockets (Route No. format)
- **Intelligent PDF Detection**: Automatically identifies document types and validates files
- **Route Sequencing**: Automatically sequences routes and delivery numbers in correct order
- **PDF Merging**: Merges multiple PDFs with continuation page support
- **Drag-and-Drop Interface**: Modern PyQt6 GUI with full drag-and-drop support
- **Route Preview**: View detected routes and deliveries before merging
- **Error Detection**: Identifies duplicate deliveries and missing drops
- **Comprehensive Logging**: Full audit trail of all operations

### 📊 Advanced Features
- Company detection (LAC/RTR)
- Multi-file batch processing
- Continuation page handling
- Duplicate delivery detection and reporting
- Missing delivery number detection
- Timestamped output files
- Progress tracking
- File validation before processing

## Project Structure

```
HDS_Client_Mix/
├── hds_route_sequencer.py          # Main entry point
├── gui_main.py                     # PyQt6 GUI application
├── pdf_detector.py                 # PDF detection and validation
├── route_sequencer.py              # Route extraction and sequencing
├── pdf_merger.py                   # PDF merging operations
├── logger.py                       # Comprehensive logging system
├── models.py                       # Data models and enums
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── input/                          # Input PDFs folder
├── output/                         # Output merged PDFs folder
└── logs/                           # Processing logs (auto-created)
```

## Installation

### Prerequisites
- Python 3.9+ (tested on Python 3.11)
- Windows OS (for Outlook integration and file operations)
- ~200MB disk space for dependencies

### Step 1: Create Virtual Environment

```bash
cd "C:\Python Project\HDS_Client_Mix"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Application
```bash
python hds_route_sequencer.py
```

The GUI will open with a mode selection dialog.

### Workflow

#### 1. Select Processing Mode
Choose one of:
- **📦 Picking Slips**: For processing route picking sheets (R D format)
- **🚚 Delivery Dockets**: For processing delivery documents (Route No. format)

#### 2. Add PDF Files
You can:
- **Drag-and-drop** PDFs directly into the file list area
- **Click "Add Files"** button to browse and select PDFs
- **Drag multiple files** at once

#### 3. Validate Files (Optional)
- **Click "Preview Routes"** to see detected routes and deliveries
- Review for any duplicates or missing deliveries
- Choose to proceed or cancel

#### 4. Merge and Sequence
- **Click "Merge & Sequence"**
- Select output folder for merged PDFs
- Processing will automatically:
  - Extract route/delivery information
  - Validate all pages
  - Sequence by route and delivery number
  - Merge into single PDF with timestamped filename
  - Generate processing log

#### 5. Review Results
- Check success message with statistics
- **Click "Open Output"** to view merged PDF
- Check logs for detailed processing information

## Document Format Detection

### Picking Slip Format
Detected by pattern: `R #### D ##`
- Example: `R 3003 D 4`
- Route: 3003, Delivery: 4

### Delivery Docket Format
Detected by pattern: `Route No.: #### - ##`
- Example: `Route No.: 3003 - 4`
- Route: 3003, Delivery: 4

## Output Files

### Picking Slips Processing
`Picking_Slips_Sequenced_YYYYMMDD_HHMMSS.pdf`

### Delivery Dockets Processing
`Delivery_Dockets_Sequenced_YYYYMMDD_HHMMSS.pdf`

### Log Files
`logs/hds_route_sequencer_YYYYMMDD_HHMMSS.log`

All files include timestamps for tracking and audit trail.

## Features in Detail

### PDF Detection Engine
- Multi-pattern regex matching
- Company type detection (LAC/RTR)
- Scoring system for accuracy
- Fallback detection logic

### Route Sequencing
- Route number sorting (ascending)
- Delivery number sorting within routes
- Duplicate delivery detection
- Missing delivery detection

### Validation System
- Pre-processing validation
- Duplicate delivery detection
- Missing delivery detection
- Page count validation

## Troubleshooting

### "Invalid file detected" Error
- Ensure PDFs match selected mode
- Verify PDF is readable and not corrupted
- Try a different PDF to confirm

### Files not merging in correct order
- Check log file for sequence information
- Verify route/delivery format in PDFs

### Memory issues with large files
- Split large collections into smaller batches
- Process one company (LAC/RTR) at a time

## Logging

All operations are logged to `logs/hds_route_sequencer_*.log` with full details.

## Version History

### v1.0.0 (2024-12-25)
- Initial release with complete modular architecture
- Dual-mode processing (Picking Slips / Delivery Dockets)  
- Intelligent PDF detection engine
- Route sequencing with validation
- Modern PyQt6 GUI with drag-and-drop
- Comprehensive error handling and logging

---

**Version**: 1.0.0 | **Python**: 3.9+ | **Platform**: Windows 10/11 | **Updated**: 2024-12-25
