"""
QUICK START GUIDE - Using the Enhanced PDF Merge and Route Sequencing Application
"""

# ============================================================================
# WHAT'S NEW
# ============================================================================

The enhanced HDS Route Sequencer now includes:

✓ Smart workflow selection after merging PDFs
✓ Intelligent print prioritization by run number
✓ Wave-based printing system (25 pages per wave)
✓ Real-time print progress monitoring
✓ Automatic error detection before printing
✓ Enhanced processing dashboard


# ============================================================================
# STEP-BY-STEP USAGE GUIDE
# ============================================================================

## Step 1: Start the Application
```bash
python hds_route_sequencer.py
```

Expected: Main window opens with file upload area


## Step 2: Select Processing Mode
Dialog appears asking: "Select Processing Mode"

Options:
- 📦 **Picking Slips**: For picking sheet PDFs (R D format)
- 🚚 **Delivery Dockets**: For delivery docket PDFs (Route No. format)

Action: Click on your document type


## Step 3: Add PDF Files
- Drag and drop PDF files into the gray drop zone
- OR click "+ Add Files" to browse files
- Files appear in the list

Show: Files Loaded counter shows how many files added


## Step 4: Merge & Sequence
Click: **🔗 Merge & Sequence** button

Progress shows:
- 0-40%: 🔍 Validating PDF files
- 40-50%: 📍 Extracting routes and deliveries  
- 50-75%: 🔗 Sequencing and merging pages
- 75-95%: 💾 Saving output files
- 95-100%: ✅ Finalizing

Time: Depends on file count and size
- 5 files (500 pages): ~5-10 seconds
- 20 files (2000 pages): ~30-60 seconds


## Step 5: **[NEW]** Post-Merge Workflow Dialog

After merge completes, dialog appears:
```
✓ PDF Merge Complete!
What would you like to do next?
```

Options:

### Option A: 📦 Process as Picking Dockets
- Resequence using Picking Docket format
- Proceeds to printing options

### Option B: 🚚 Process as Delivery Dockets  
- Resequence using Delivery Docket format
- Proceeds to printing options

### Option C: 💾 Save and Exit
- Saves merged PDF to ~/Downloads/
- Does NOT print
- Application remains open for new job

Action: Click your choice


## Step 6: **[NEW]** Print Confirmation Dialog

If you chose a processing option, dialog appears:
```
✅ Processing Complete!
Would you like to print the document now?
```

Options:

### Option A: 🖨️ Print Now
- Analyzes document for errors
- Shows warning if errors detected
- Sends to printer in intelligent waves
- Shows real-time progress

### Option B: 💾 Save Only
- Keeps PDF but does NOT print
- Can print manually later
- Recommended if you want to review first

### Option C: ✗ Cancel
- Does not print
- Returns to main menu
- PDF remains in output folder

Action: Click your choice


## Step 7: **[NEW]** Error Detection (If Printing)

If document has potential issues, dialog appears:
```
⚠️ WARNINGS DETECTED
```

Shows:
- Missing run numbers
- Duplicate pages
- Invalid run numbers

Action:
- **✓ Continue Printing**: Ignore warnings and proceed
- **✗ Cancel Printing**: Stop and review document

Note: Critical errors will show 🚨 and block printing


## Step 8: **[NEW]** Real-Time Printing

While printing:
- Progress bar shows overall progress
- Current wave shown (Wave X of Y)
- Current run range displayed
- Pages printed / Pages remaining shown
- Operation label shows: "🖨️ Printing Wave X (Runs XXXX-XXXX)"

Example:
```
Wave 1: Runs 3010-3015 (25 pages) ✓ Printed
Wave 2: Runs 3016-3020 (25 pages) ⏳ Printing
Wave 3: Runs 3021-3030 (25 pages) ⏳ Queued
```


## Step 9: Completion

When printing finishes:
- Success message shows total pages printed
- Status shows: "✓ Printing complete!"
- "📂 Open Output Folder" button becomes visible
- Can click to view saved PDFs


## Step 10: View Output

Click: **📂 Open Output Folder**

Opens Windows Explorer to ~/Downloads/ where you'll find:
- `Picking_Slips_Sequenced_YYYYMMDD_HHMMSS.pdf` (if picking)
- `Delivery_Dockets_Sequenced_YYYYMMDD_HHMMSS.pdf` (if delivery)
- Wave batch PDFs (temporary files)


# ============================================================================
# NEW FEATURES EXPLAINED
# ============================================================================

## Intelligent Run Priority (New Feature #1)

What it does: Automatically orders print batches by run importance

Run Groups (in print order):
1. **First** (Primary): Runs 3010-3030
   - Main operations
   - Printed first
   
2. **Second** (Secondary): Runs 3001-3009
   - Lower priority
   - Printed after first group
   
3. **Third** (Tertiary): Runs 3031-3033
   - Least common runs
   - Printed after second group
   
4. **Last** (Others): Any remaining runs
   - Unusual run numbers
   - In ascending order

Example: If document has runs [3001, 3015, 3030, 3002, 3050]:
Print order becomes: [3010-3030 group] → [3001-3009 group] → [3031-3033 group] → [3050 and others]


## Wave-Based Printing (New Feature #2)

What it does: Breaks large print jobs into smaller batches

Why: Prevents printer overload and improves reliability

How it works:
1. Document split into 25-page waves (default)
2. Each wave respects run number boundaries
3. Wave 1 queued and printed first
4. After Wave 1 starts printing, Wave 2 queues
5. Process continues until all waves printed

Example for 150-page document:
```
Wave 1: Pages 1-25 (Runs 3010-3012) - Send immediately
Wave 2: Pages 26-50 (Runs 3013-3020) - Wait for Wave 1 to print
Wave 3: Pages 51-75 (Runs 3021-3030) - Wait for Wave 2 to print  
Wave 4: Pages 76-100 (Runs 3001-3005) - Wait for Wave 3 to print
Wave 5: Pages 101-125 (Runs 3006-3009) - Wait for Wave 4 to print
Wave 6: Pages 126-150 (Runs 3031-3033) - Wait for Wave 5 to print
```


## Error Detection (New Feature #3)

What it does: Finds potential problems before printing

Examples of issues detected:
- **Missing Runs**: Expected run 3005 but page has 3004 then 3006
  → Warning: Run 3005 is missing
  
- **Duplicate Runs**: Same route-delivery appears twice
  → Warning: Run 3001-02 appears 2 times
  
- **Invalid Runs**: Run number outside normal range
  → Error: Run 5000 is outside valid range

When shown: After clicking "Print Now" but before sending to printer

What you can do:
- Review the issues listed
- "Continue Printing" if issues acceptable
- "Cancel Printing" to fix document first

Note: Red/Critical errors block printing automatically


## Real-Time Progress Dashboard (New Feature #4)

What it shows during printing:
- Current wave number (e.g., "Wave 3 of 6")
- Current run range (e.g., "Runs 3021-3030")
- Pages printed so far (e.g., "75 / 150")
- Overall progress percentage
- Printer status
- Any errors that occurred


# ============================================================================
# COMMON WORKFLOWS
# ============================================================================

### Workflow 1: Just Merge PDFs (Simplest)
1. Select mode
2. Add files
3. Click Merge & Sequence
4. When asked "What would you like to do next?" → **Save and Exit**
5. Done! PDF is in ~/Downloads/


### Workflow 2: Merge and Review Before Printing
1. Select mode
2. Add files
3. Click Merge & Sequence
4. When asked "What would you like to do next?" → **Save and Exit**
5. Review PDF manually
6. Print manually from Windows when ready


### Workflow 3: Merge and Print Immediately
1. Select mode
2. Add files
3. Click Merge & Sequence
4. When asked "What would you like to do next?" → **Process as [Picking/Delivery]**
5. When asked "Would you like to print?" → **Print Now**
6. If errors shown: **Continue Printing** (or review first)
7. Printing starts automatically
8. Watch real-time progress
9. Done! Output folder opens when complete


### Workflow 4: Auto-Resequence and Print
1. Select one mode (e.g., Picking Dockets)
2. Add picking PDF files
3. Merge & Sequence
4. Post-merge asks: "What next?" → **Process as Delivery Dockets**
   (This resequences the merged PDF as delivery format instead)
5. Print confirmation appears
6. Choose **Print Now**
7. Printing proceeds with new sequence


# ============================================================================
# TIPS & BEST PRACTICES
# ============================================================================

### ✓ DO:
- Add 5-20 files at a time for best performance
- Review error warnings before proceeding with printing
- Check printer is online before starting print workflow
- Allow 1-2 minutes for large document processing
- Open output folder to verify PDF after completion

### ✗ DON'T:
- Don't add 100+ files at once (may be slow)
- Don't dismiss error warnings without reading
- Don't disconnect printer during printing
- Don't force-close application during processing
- Don't delete output folder while printing

### 🔧 TIPS:
- Use "Save Only" first time to review PDF
- Print test batches with "Print Now" to verify quality
- Keep output folder (~500MB free space recommended)
- Monitor print queue in Windows for detailed info
- Check application logs for troubleshooting


# ============================================================================
# TROUBLESHOOTING QUICK REFERENCE
# ============================================================================

### "Failed to queue print job"
→ Check printer is online and set as default
→ Restart Windows Print Spooler service
→ Try again

### "No pages extracted from any file"
→ Verify PDF files are valid
→ Check files are not corrupted
→ Try with different PDF file

### "Missing runs warning appears"  
→ Normal for some documents
→ Click "Continue Printing" if okay
→ Or "Cancel" to review document

### Application seems frozen
→ This is normal for large files (5000+ pages)
→ Wait 1-2 minutes before giving up
→ Progress bar updates every few seconds

### Can't find output files
→ Click "📂 Open Output Folder" button
→ Or manually go to ~/Downloads/
→ Files named: `[Mode]_Sequenced_YYYYMMDD_HHMMSS.pdf`

### Printing never starts after clicking "Print Now"
→ Check printer status in Windows
→ Ensure printer has paper/toner
→ Restart printer and try again
→ Check Windows Print Spooler is running


# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

| Action | Shortcut |
|--------|----------|
| Add Files | (Click button - no shortcut yet) |
| Merge & Sequence | (Click button - no shortcut yet) |
| Open Output Folder | (Click button - no shortcut yet) |
| Close Application | Alt+F4 |
| Cancel Dialog | Escape |


# ============================================================================
# FILE LOCATIONS
# ============================================================================

**Application Directory**: 
`C:\[path to HDS_Client_Mix\`

**Output Directory**:
`C:\Users\[username]\Downloads\`

**Log Files**:
`C:\[HDS_Client_Mix]\processing_log_*.txt`

**Temporary Files**:
`C:\Users\[username]\Downloads\Wave_*.pdf` (created during printing)

**Configuration**:
Hardcoded in Python files - no separate config file currently


# ============================================================================
# GETTING HELP
# ============================================================================

1. **Check the logs**
   - Open `processing_log_*.txt` in Downloads folder
   - Look for ERROR or WARNING messages

2. **Read the detailed documentation**
   - WORKFLOW_ENHANCEMENTS.md - Full feature guide
   - ENHANCEMENT_SUMMARY.md - Implementation details

3. **Review error warnings**
   - Dialogs show specific error details
   - Error report lists all issues found

4. **Test with sample files**
   - Start with 1-2 small PDF files
   - Verify workflow works before large batches

---

**Need more help?** 
Refer to WORKFLOW_ENHANCEMENTS.md for comprehensive feature documentation.

Version 1.0 - 2024
