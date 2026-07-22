# HDS Route Sequencer - Architecture & Implementation Guide

## Overview

HDS Route Sequencer is a production-ready Python desktop application for intelligent PDF processing with route sequencing. It employs a fully modular, object-oriented architecture built with PyQt6.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     hds_route_sequencer.py                  │
│                      (Entry Point)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        gui_main.py                          │
│                   (PyQt6 GUI Application)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • MainWindow: Main application window               │   │
│  │ • ModeSelectionDialog: Mode choice (Picking/Delivery)   │   │
│  │ • RoutePreviewDialog: Route visualization          │   │
│  │ • ProcessWorker: Background processing thread      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────────┐  ┌──────────────┐  ┌─────────────────┐
│ pdf_detector.py  │  │route_         │  │  pdf_merger.py  │
│                  │  │sequencer.py   │  │                 │
│ • PDFDetector    │  │               │  │ • PDFMerger     │
│ • PDFValidator   │  │ • RouteSequ-  │  │ • PDFProcessor  │
└──────────────────┘  │   encer       │  └─────────────────┘
                      │ • RoutePreview│
                      └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
    ┌────────────┐   ┌────────────┐   ┌──────────┐
    │logger.py   │   │models.py   │   │ External │
    │            │   │            │   │ Libraries│
    │ • Process  │   │ • Document │   │          │
    │   Logger   │   │   Type     │   │ PyQt6    │
    │            │   │ • PageInfo │   │ PyPDF2   │
    └────────────┘   │ • Routes   │   │pdfplumber│
                     │ • Results  │   │ pandas   │
                     └────────────┘   └──────────┘
```

## Module Breakdown

### 1. **hds_route_sequencer.py** (Entry Point)
**Purpose**: Application entry point
**Responsibilities**:
- Import main GUI application
- Initialize application
- Handle startup

**Key Code**:
```python
from gui_main import main

if __name__ == '__main__':
    main()
```

---

### 2. **models.py** (Data Models)
**Purpose**: Define all data structures used throughout application
**Responsibilities**:
- Enums for document types and companies
- Data classes for type safety
- Validation report structure

**Key Classes**:
- `DocumentType` enum: PICKING_SLIP, DELIVERY_DOCKET, UNKNOWN
- `CompanyType` enum: LAC, RTR, UNKNOWN
- `PageInfo`: Single PDF page metadata
- `PDFFileInfo`: PDF file information
- `RouteInfo`: Route and delivery summary
- `ValidationReport`: Validation findings
- `ProcessingResult`: Operation outcome
- `MergeResult`: Complete merge operation result

**Benefits**:
- Type safety throughout codebase
- IDE autocomplete support
- Self-documenting code
- Easy refactoring

---

### 3. **logger.py** (Logging System)
**Purpose**: Comprehensive logging for audit trail and debugging
**Responsibilities**:
- Console and file logging
- Multiple log levels
- Formatted output
- Report generation

**Key Classes**:
- `ProcessLogger`: Main logging class
- Global logger instance management

**Features**:
- DEBUG: Detailed diagnostic information
- INFO: Informational messages
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical issues
- Separators for visual organization
- Validation report logging
- Processing summary logging

**Usage**:
```python
from logger import get_logger

logger = get_logger()
logger.info("Processing started")
logger.warning("Duplicate found")
logger.error("Processing failed")
```

---

### 4. **pdf_detector.py** (PDF Detection & Validation)
**Purpose**: Detect document types and validate files
**Responsibilities**:
- PDF type detection
- Company type detection
- File validation
- Pattern matching

**Key Classes**:
- `PDFDetector`: Detection algorithms
- `PDFValidator`: Collection validation

**Detection Patterns**:

**Picking Slips**:
```
R 3001 D 2
Route 3001 Delivery 2
PICKING SHEET
PICK SLIP
```

**Delivery Dockets**:
```
Route No.: 3001 - 2
DELIVERY DOCKET
DELIVERY SHEET
```

**Company Detection**:
```
LACTALIS → LAC
RTR DISTRIBUTION → RTR
```

**Methods**:
- `extract_text_from_pdf()`: Extract first N pages
- `detect_company_type()`: LAC or RTR
- `detect_picking_slip_markers()`: Extract R D numbers
- `detect_delivery_docket_markers()`: Extract Route No. numbers
- `detect_pdf_type()`: Overall document type
- `validate_pdf_file()`: Single file validation
- `validate_pdf_files()`: Multiple file validation

---

### 5. **route_sequencer.py** (Route Extraction & Sequencing)
**Purpose**: Extract routes/deliveries and sequence pages
**Responsibilities**:
- Page extraction from PDFs
- Route number extraction
- Delivery number extraction
- Page sequencing
- Route analysis and preview

**Key Classes**:
- `RouteSequencer`: Extraction and sequencing
- `RoutePreview`: Preview generation

**Key Algorithms**:

**Page Extraction**:
1. Scan each page for route/delivery markers
2. If found: mark as "main page", store route/delivery
3. If not found: mark as "continuation page", assign to last route/delivery

**Sequencing**:
1. Separate main and continuation pages
2. Sort main pages by (route, delivery)
3. Group: each main page + its continuation pages
4. Append remaining continuation and orphan pages

**Validation**:
1. Count main/continuation pages
2. Detect duplicates (same route+delivery twice)
3. Detect missing drops (gaps in sequences)
4. Generate report with findings

---

### 6. **pdf_merger.py** (PDF Merging)
**Purpose**: Merge PDF pages into output files
**Responsibilities**:
- Sequenced page merging
- PDF file assembly
- Output file generation
- Complete processing pipeline

**Key Classes**:
- `PDFMerger`: Low-level PDF merging
- `PDFProcessor`: High-level processing pipeline

**Pipeline**:
```
Input Files
    ↓
Extract Pages (from pdf_detector, route_sequencer)
    ↓
Sequence Pages (from route_sequencer)
    ↓
Validate (from route_sequencer)
    ↓
Merge Pages (from pdf_merger)
    ↓
Generate Output PDF
    ↓
Success/Error Report
```

**Methods**:
- `merge_pages()`: Core merging logic
- `process_pdfs()`: Complete pipeline

**Processing Result**:
- Success flag
- Pages merged count
- Routes detected
- Output file path
- Validation report
- Warnings/errors

---

### 7. **gui_main.py** (PyQt6 GUI)
**Purpose**: Modern desktop GUI with drag-and-drop
**Responsibilities**:
- User interface
- Drag-and-drop file handling
- Mode selection dialog
- Route preview display
- Background processing
- Progress tracking
- Status reporting

**Key Classes**:
- `MainWindow`: Main application window
- `ModeSelectionDialog`: Mode selection
- `RoutePreviewDialog`: Route preview display
- `ProcessWorker`: Background worker thread

**UI Features**:
- Mode selection screen (Picking Slips / Delivery Dockets)
- Full-window drag-and-drop zone
- File list with add/remove/clear buttons
- Progress bar during processing
- Route preview before merge
- Status label with color coding
- Output folder button
- Professional styling with CSS

**Workflow**:
```
Start App
    ↓
Show Mode Selection
    ↓
Wait for Mode Selection
    ↓
Show Main Window with Drag-Drop Zone
    ↓
User adds PDFs (drag-drop or button)
    ↓
[Optional] Click "Preview Routes"
    ↓
Click "Merge & Sequence"
    ↓
Select Output Folder
    ↓
Validate Files
    ↓
Start Processing Worker Thread
    ↓
Show Progress
    ↓
Processing Complete
    ↓
Show Results Dialog
```

---

## Data Flow

### File Processing Flow

```
Input PDFs
    │
    ├─→ Validation (pdf_detector)
    │   ├─ Check file exists
    │   ├─ Check is PDF
    │   ├─ Detect type
    │   └─ Validate vs expected type
    │
    ├─→ Page Extraction (route_sequencer)
    │   ├─ Extract text from all pages
    │   ├─ Find route/delivery markers
    │   ├─ Assign continuation pages
    │   └─ Build PageInfo objects
    │
    ├─→ Sequencing (route_sequencer)
    │   ├─ Separate main/continuation/orphan
    │   ├─ Sort by (route, delivery)
    │   ├─ Group pages
    │   └─ Return sorted PageInfo list
    │
    ├─→ Validation (route_sequencer)
    │   ├─ Build route summary
    │   ├─ Detect duplicates
    │   ├─ Detect missing
    │   └─ Generate report
    │
    ├─→ PDF Merging (pdf_merger)
    │   ├─ Reopen PDFs using PyPDF2
    │   ├─ Add pages in order
    │   ├─ Write output file
    │   └─ Generate success/error
    │
    └─→ Output
        ├─ Merged PDF file
        ├─ Processing log
        └─ Results report
```

## Error Handling Strategy

### Validation Errors
```
Invalid File → Warning Dialog → Allow Skip → Continue/Abort
```

### Processing Errors
```
Processing Error → Catch Exception → Log Error → Show Error Dialog → Allow Retry
```

### Recovery
- Non-blocking dialogs
- Detailed error messages
- Logging for troubleshooting
- Partial success reporting

## Performance Optimization

### Lazy Loading
- PDFs loaded only during merge
- Text extracted only when needed

### Caching
- PDF readers cached during merge
- Compiled regex patterns (implicit in re module)

### Threading
- GUI responsive during processing
- Worker thread for long operations
- Progress updates to main thread

### Memory Management
- Pages processed without loading entire PDFs into memory
- Readers closed after use
- Large files split into smaller batches

## Extension Points

### Adding New Document Types

1. **pdf_detector.py**: Add detection patterns
2. **route_sequencer.py**: Add extraction method
3. **gui_main.py**: Add mode option

### Adding New Validation Rules

1. **route_sequencer.py**: Add validation method
2. **models.py**: Update ValidationReport
3. **logger.py**: Add report formatting

### Custom Output Formats

1. **pdf_merger.py**: Add output generation method
2. **gui_main.py**: Add output option

## Testing Recommendations

### Unit Tests
- PDF detection accuracy
- Route extraction correctness
- Sequencing algorithms
- Validation logic

### Integration Tests
- End-to-end file processing
- GUI interactions
- Error scenarios

### Performance Tests
- Large file sets (100+ PDFs)
- Large page counts (5000+ pages)
- Memory usage under load

## Deployment

### Prerequisites
- Python 3.9+
- Windows 10/11
- 200MB disk space
- 200MB RAM minimum

### Installation
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python hds_route_sequencer.py
```

### Distribution
- Bundle as executable using PyInstaller
- Create Windows installer
- Include all dependencies

### Configuration
- Edit `pdf_detector.py` for custom patterns
- Modify `logger.py` for log levels
- Update `gui_main.py` for styling

## Maintenance

### Regular Updates
- Monitor dependency updates
- Test with new Python versions
- Update pattern detection as needed

### Bug Fixes
1. Reproduce issue with test files
2. Add test case
3. Fix in appropriate module
4. Update logs and documentation

### Performance Monitoring
- Track processing times
- Monitor memory usage
- Identify bottlenecks

## Future Enhancements

### Short Term
- [ ] OCR support for scanned PDFs
- [ ] Batch scheduling
- [ ] Email delivery of results
- [ ] Configuration file support

### Medium Term
- [ ] Cloud storage integration (Azure/AWS)
- [ ] Web interface
- [ ] API for integration
- [ ] Advanced filtering

### Long Term
- [ ] Machine learning for pattern detection
- [ ] Mobile app
- [ ] Real-time processing dashboard
- [ ] Advanced analytics

---

**Version**: 1.0.0  
**Architecture**: Modular OOP with PyQt6  
**Python**: 3.9+  
**Last Updated**: 2024-12-25
