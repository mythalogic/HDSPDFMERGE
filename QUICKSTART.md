# HDS Route Sequencer - Quick Start Guide

Get up and running in 5 minutes!

## Installation (One Time)

### 1. Open PowerShell

Press `Win+R`, type `powershell`, press Enter

### 2. Navigate to Project

```powershell
cd "C:\Python Project\HDS_Client_Mix"
```

### 3. Create Virtual Environment

```powershell
python -m venv .venv
```

### 4. Activate Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your command prompt.

### 5. Install Dependencies

```powershell
pip install -r requirements.txt
```

Wait for installation to complete (2-5 minutes).

---

## Running the Application

### Every Time You Use It

#### 1. Open PowerShell
Press `Win+R`, type `powershell`, press Enter

#### 2. Navigate to Project
```powershell
cd "C:\Python Project\HDS_Client_Mix"
```

#### 3. Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

#### 4. Start Application
```powershell
python hds_route_sequencer.py
```

The GUI should open in 2-3 seconds.

---

## Using the Application

### Step 1: Select Mode
- Click **📦 Picking Slips** OR **🚚 Delivery Dockets**
- Choose based on your PDF type

### Step 2: Add PDFs
**Option A: Drag & Drop**
- Drag PDF files directly onto the file list area
- Drop when you see the blue border

**Option B: Click Button**
- Click **"+ Add Files"** button
- Select PDFs from file browser
- Click Open

### Step 3 (Optional): Preview Routes
- Click **"👁️ Preview Routes"**
- Review detected routes
- Check for warnings (duplicates, missing)
- Click **"✓ Proceed with Merge"** or **"✗ Cancel"**

### Step 4: Merge PDFs
- Click **"🔗 Merge & Sequence"**
- Select where to save merged PDF
- Processing starts automatically
- Watch the progress bar

### Step 5: View Results
- Success message shows:
  - Number of pages merged
  - Routes detected
  - Output filename
- Click **"📂 Open Output"** to see the PDF
- Or navigate to the folder you selected

---

## Output Files

### Location
Files are saved where you selected in Step 4.

### File Names
- **Picking Slips**: `Picking_Slips_Sequenced_TIMESTAMP.pdf`
- **Delivery Dockets**: `Delivery_Dockets_Sequenced_TIMESTAMP.pdf`
- **Log**: `logs/hds_route_sequencer_TIMESTAMP.log`

---

## Common Issues

### "Module not found" Error
**Solution**: Make sure virtual environment is activated
```powershell
.\.venv\Scripts\Activate.ps1  # Run this first!
python hds_route_sequencer.py
```

### "PDF type not recognized"
**Solution**: Ensure PDFs match selected mode
- Picking Slips: Look for `R 3001 D 2` format
- Delivery Dockets: Look for `Route No.: 3001 - 2` format

### Files not merging in correct order
**Check the log file**:
1. Look in `logs/` folder
2. Open latest log file in Notepad
3. Search for "Route" or "Delivery"
4. Verify numbers are in correct sequence

### Application not opening
1. Check Python is installed: `python --version`
2. Check dependencies: `pip list`
3. Try reinstalling: `pip install --upgrade PyQt6`

---

## Tips & Tricks

### Batch Processing
- Add all PDFs at once (drag 20+ files)
- Application handles them automatically
- No need to process one-by-one

### Repeated Files
- Try "Preview Routes" first
- Identifies duplicate deliveries BEFORE merging
- Allows you to remove duplicates from source

### Check Results
- Always check the final PDF
- Verify order looks correct
- Check log file for any warnings

### Save for Later
- Keep the output PDF
- Output is timestamped (won't overwrite)
- Logs are saved for audit trail

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open Output Folder |
| `Drag & Drop` | Add Files |
| `Delete` | Remove Selected File |

---

## Need Help?

### Check Documentation
- `README.md` - Full feature documentation
- `ARCHITECTURE.md` - Technical details
- `logs/` - Processing logs with full details

### Troubleshooting Checklist
- [ ] Python 3.9+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] PDFs are valid (can open in Adobe Reader)
- [ ] PDFs match selected mode
- [ ] Output folder has write permissions

### Log File Investigation
1. Go to: `C:\Python Project\HDS_Client_Mix\logs\`
2. Open latest `.log` file in Notepad
3. Search for "ERROR" or "WARNING"
4. Note any file paths or messages

---

## Example Session

```
PS C:\Python Project\HDS_Client_Mix> .\.venv\Scripts\Activate.ps1
(.venv) PS C:\Python Project\HDS_Client_Mix> python hds_route_sequencer.py

[GUI Opens]
1. Select: "📦 Picking Slips"
2. Drag 10 PDFs into the list
3. Click "👁️ Preview Routes"
   - See: 5 Routes with 25 total deliveries
   - See: 1 duplicate found (Route 3 - Delivery 5)
4. Click "✗ Cancel"
5. Remove duplicate PDF
6. Click "🔗 Merge & Sequence"
7. Select: "C:\Users\You\Desktop"
8. [Processing...]
9. Message: "✓ Processing Complete! 24 pages merged, 5 routes detected"
10. Click "📂 Open Output"
11. PDF opens: "Picking_Slips_Sequenced_20241225_143022.pdf"
12. ✓ Done!
```

---

## For Troubleshooting

**Always provide the log file** when reporting issues:
```
C:\Python Project\HDS_Client_Mix\logs\hds_route_sequencer_*.log
```

---

**Quick Start Version**: 1.0.0  
**Last Updated**: 2024-12-25  
**Time to Setup**: ~10 minutes  
**Time to Process**: 2-5 seconds (typical)
