# HDS Route Sequencer - Complete Build & Deployment Instructions

## Quick Summary

This document provides step-by-step instructions to convert your Python application into a professional Windows installer that users can download and install like commercial software.

**Total Time Required**: ~30-45 minutes (first time: 1-2 hours including downloads)

---

## STEP 1: Install Required Tools (5-10 minutes)

### 1.1 Install PyInstaller
PyInstaller converts your Python code to a standalone .exe file.

```powershell
# Open PowerShell in your project directory
cd "c:\Python Project\HDS_Client_Mix"

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install PyInstaller
pip install pyinstaller

# Verify installation
pyinstaller --version
```

### 1.2 Download & Install Inno Setup
Inno Setup creates the professional Windows installer (.exe) with wizard interface.

**Download**: https://jrsoftware.org/isinfo.php

**Steps**:
1. Click "Download Inno Setup 6"
2. Run installer: `is-6.x.x.exe`
3. Click "Next" through wizard
4. Install to default location (C:\Program Files (x86)\Inno Setup 6)
5. Finish

**Verify Installation**: Look for folder `C:\Program Files (x86)\Inno Setup 6`

---

## STEP 2: Prepare Application Icon (Optional but Recommended)

The application needs a professional .ico file.

### 2.1 Option A: Use Existing Icon (Easiest)
Download from free icon sites:
- https://www.flaticon.com (search: "PDF routing")
- https://www.iconfinder.com (search: "PDF document")
- https://www.freeicons.io

**Requirements**:
- Format: PNG or JPG
- Size: At least 256x256 pixels
- Concept: PDF/routing/delivery

### 2.2 Option B: Convert Icon to .ico Format

If you have PNG/JPG:
1. Visit: https://convertio.co/png-ico/
2. Upload your image
3. Download .ico file
4. Save to: `C:\Python Project\HDS_Client_Mix\deployment\icon.ico`

### 2.3 Option C: Skip Icon (Uses Windows Default)
If you skip this step, the application will use the default Windows icon. Still looks professional!

---

## STEP 3: Build the Executable (10-15 minutes)

This step converts Python code → standalone .exe file.

### 3.1 Run Build Script

```powershell
# Navigate to project directory
cd "c:\Python Project\HDS_Client_Mix"

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run the build script
python build_exe.py
```

### 3.2 What Happens During Build

You'll see:
```
[*] Checking dependencies...
[*] Cleaning previous builds...
[*] Building executable...  <- This takes 1-2 minutes
[✓] BUILD COMPLETE!
[📁] Output: dist\HDS_Route_Sequencer.exe (~160 MB)
```

### 3.3 Build Output Location

**Created Files**:
- `dist/HDS_Route_Sequencer.exe` - Your standalone application (160 MB)
- `build/` - Temporary build files (can delete after testing)
- `HDS_Route_Sequencer.spec` - Build configuration file

---

## STEP 4: Test the Executable (5 minutes)

### 4.1 Test Standalone .exe

```powershell
# Run the executable directly
& "C:\Python Project\HDS_Client_Mix\dist\HDS_Route_Sequencer.exe"
```

### 4.2 Verify Functionality

✓ Application window opens with mode selection
✓ Can select "Picking Slips" or "Delivery Dockets"
✓ Main window displays with drag-drop area
✓ Can drag files into drop zone
✓ Can click "+ Add Files" to browse
✓ Files appear in list
✓ Progress bar updates
✓ Success dialog shows (all text readable)
✓ Can open output folder

If everything works → Proceed to Step 5
If issues occur → Check troubleshooting at end

---

## STEP 5: Create the Windows Installer (5-10 minutes)

The installer is the file users download and run.

### 5.1 Open Inno Setup Compiler

**Option A: GUI (Easiest)**
1. Open "Inno Setup 6" from Start Menu
2. Click "File" → "Open"
3. Navigate to: `C:\Python Project\HDS_Client_Mix\deployment\installer.iss`
4. Click "Open"
5. Click "Build" → "Compile"
6. Wait for compilation (~2 minutes)

**Option B: Command Line**
```powershell
# Using command line
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Python Project\HDS_Client_Mix\deployment\installer.iss"
```

### 5.2 Build Output

**Successfully Created**:
- `deployment/HDS_Route_Sequencer_Setup.exe` (80-100 MB)

This is the file users download and run!

---

## STEP 6: Test the Installer (10 minutes)

### 6.1 Run Installer

```powershell
# Run the installer
& "C:\Python Project\HDS_Client_Mix\deployment\HDS_Route_Sequencer_Setup.exe"
```

### 6.2 Installer Wizard

You should see:
1. **Welcome Screen** - Shows version, company info
2. **License Agreement** - Review/accept license
3. **Select Destination Folder** - Default is fine (or choose location)
4. **Installation** - Progress bar fills
5. **Completion** - "Finish" button

### 6.3 Launch After Installation

After installation completes:
- Check **Start Menu** → "HDS Route Sequencer"
- Check **Desktop** → "HDS Route Sequencer" shortcut
- Double-click to verify application launches

### 6.4 Verify Installation

✓ Application launches normally
✓ All features work (mode selection, file upload, processing)
✓ Files save to Downloads folder
✓ Success dialog visible

---

## STEP 7: Prepare for Distribution

### 7.1 Create Distribution Package

Copy these files to a distribution folder:

```
distribution/
├── HDS_Route_Sequencer_Setup.exe    (the installer - 80-100 MB)
├── README.txt                        (installation instructions)
├── LICENSE.txt                       (user license)
├── VERSION.txt                       (version info)
├── CHANGELOG.md                      (what's new)
└── download_page.html                (website download page)
```

### 7.2 File Descriptions

| File | Purpose | Size |
|------|---------|------|
| HDS_Route_Sequencer_Setup.exe | Main installer users download | 80-100 MB |
| README.txt | Installation & usage instructions | 10 KB |
| LICENSE.txt | Legal terms | 5 KB |
| VERSION.txt | Version & system info | 10 KB |
| CHANGELOG.md | What's new in this version | 5 KB |

---

## STEP 8: Host on Website for Download

### 8.1 Option A: GitHub (Recommended for Free)

1. Create GitHub account (free): https://github.com/join
2. Create new repository: `hds-route-sequencer`
3. Go to **Releases** section
4. Click **Create Release**
5. Upload: `HDS_Route_Sequencer_Setup.exe`
6. Share download link

**Generated Link**: `https://github.com/yourname/hds-route-sequencer/releases/download/v1.0.0/HDS_Route_Sequencer_Setup.exe`

### 8.2 Option B: Company Website

1. Copy files to web server: `/downloads/hds-route-sequencer/`
2. Upload `download_page.html` to website
3. Configure download links to point to .exe file
4. Share link: `https://yourcompany.com/download-hds-route-sequencer`

### 8.3 Option C: Cloud Storage (Simple)

**Google Drive:**
1. Create folder "HDS Route Sequencer"
2. Upload Setup.exe
3. Right-click → Get Link
4. Share with anyone with link

**OneDrive:**
1. Upload to OneDrive
2. Share → Get Link
3. Share with users

**Dropbox:**
1. Upload to Dropbox
2. Right-click → Share
3. Generate shareable link

---

## STEP 9: Distribute to Users

### 9.1 Create Download Page

Use the provided `download_page.html`:
1. Edit company name, website, email
2. Upload to your website
3. Users download from this page

### 9.2 User Instructions

Users receive:
1. Download link to Setup.exe
2. README.txt with installation steps
3. Website with support contact info

**User Steps**:
1. Download HDS_Route_Sequencer_Setup.exe
2. Run installer
3. Follow wizard
4. Launch application
5. Done!

---

## STEP 10: Updates & New Versions

### 10.1 Update for Version 1.1.0

When you make code changes and want to release Version 1.1.0:

**Step 1: Update Code**
```python
# In build_exe.py
APP_VERSION = "1.1.0"

# In installer.iss
AppVersion=1.1.0
```

**Step 2: Rebuild**
```powershell
python build_exe.py
```

**Step 3: Create New Installer**
```powershell
# Use Inno Setup to recompile
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Python Project\HDS_Client_Mix\deployment\installer.iss"
```

**Step 4: Upload New Version**
- GitHub: Create new release v1.1.0
- Website: Replace Setup.exe on download page
- Update VERSION.txt

**Step 5: Notify Users**
- Email: "Version 1.1.0 now available"
- Website: "Latest: v1.1.0"

---

## Troubleshooting

### ❌ PyInstaller Not Found
```powershell
# Solution: Install it
pip install pyinstaller
```

### ❌ Build Takes Too Long
- Normal: First build takes 1-2 minutes
- Subsequent: 30 seconds - 1 minute
- Large file size (160 MB) is normal

### ❌ Icon Doesn't Show
- Ensure `deployment\icon.ico` exists
- Or remove icon path from build_exe.py to use default

### ❌ Installer Won't Run
- Check Windows antivirus (might flag new application)
- Run with administrator privileges
- Try: Right-click installer → Run as Administrator

### ❌ Application Won't Start After Installation
- Check Event Viewer for errors
- Reinstall: Uninstall first, then reinstall
- Run: Search for "HDS Route Sequencer" in Start Menu

### ❌ Drag-Drop Not Working
- PyInstaller includes Qt libraries: Should work
- If not: Verify test .exe works before installer
- Reinstall to fix

### ❌ Antivirus Flags Installer as Suspicious
- Normal for new applications
- Add to antivirus whitelist
- Or sign executable with code certificate (paid option)

---

## Final Checklist Before Release

Use this checklist before distributing to users:

- [ ] PyInstaller installed
- [ ] Application icon created (or use default)
- [ ] build_exe.py script runs successfully
- [ ] Standalone .exe tested (all features work)
- [ ] Inno Setup installed
- [ ] installer.iss script configured
- [ ] Installer .exe created
- [ ] Installer tested on clean PC (or VM)
- [ ] README.txt and LICENSE.txt created
- [ ] VERSION.txt updated
- [ ] download_page.html customized
- [ ] Hosting configured (GitHub/Website/Cloud)
- [ ] Download links tested
- [ ] Support email configured
- [ ] Uninstall tested
- [ ] Version info displays correctly in About dialog

---

## Directory Structure After Build

```
c:\Python Project\HDS_Client_Mix\
├── hds_route_sequencer.py          (entry point)
├── gui_main.py
├── pdf_detector.py
├── route_sequencer.py
├── pdf_merger.py
├── logger.py
├── models.py
├── requirements.txt
├── build_exe.py                    ✓ Created
├── DEPLOYMENT_GUIDE.md             ✓ Created
├── venv/                           (virtual environment)
├── build/                          (PyInstaller temp - can delete)
├── dist/
│   └── HDS_Route_Sequencer.exe     ✓ Created (160 MB)
├── deployment/
│   ├── icon.ico                    (optional: application icon)
│   ├── installer.iss               ✓ Created
│   ├── HDS_Route_Sequencer_Setup.exe  ✓ Created (80-100 MB) ← FOR USERS
│   ├── README.txt                  ✓ Created
│   ├── LICENSE.txt                 ✓ Created
│   ├── VERSION.txt                 ✓ Created
│   ├── download_page.html          ✓ Created
│   └── CHANGELOG.md                (optional: update history)
└── logs/                           (application logs)
```

---

## How Users Will Experience It

### Before (with Python)
1. Download Python
2. Install Python
3. Download project
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python hds_route_sequencer.py`

### After (with Installer) ✨
1. Download HDS_Route_Sequencer_Setup.exe
2. Run installer
3. Click "Install"
4. Done! Run from Start Menu

**Much simpler for end users!**

---

## Summary

You've now created:

✅ Professional Windows installer
✅ Standalone .exe application
✅ Installation wizard
✅ Start Menu shortcuts
✅ Desktop shortcuts
✅ Uninstall support
✅ Professional installer branding
✅ System requirements detection
✅ Version information
✅ Download page template
✅ User documentation

**Your application is now ready for professional distribution!**

---

## Next Steps

1. ✅ Follow Steps 1-10 above
2. ✅ Test installer on another PC if possible
3. ✅ Create website/download page
4. ✅ Upload installer
5. ✅ Share download link with users
6. ✅ Provide support email
7. ✅ Monitor for bug reports
8. ✅ Plan future versions

**Congratulations! Your Python application is now a professional Windows application!** 🎉

---

For questions or issues:
- PyInstaller docs: https://pyinstaller.org/
- Inno Setup docs: https://jrsoftware.org/
- Your support email: support@yourcompany.com
