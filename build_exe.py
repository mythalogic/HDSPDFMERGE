#!/usr/bin/env python3
"""
HDS Route Sequencer - PyInstaller Build Script
Converts Python application to standalone Windows .exe executable

Usage:
    python build_exe.py

Requirements:
    - PyInstaller installed: pip install pyinstaller
    - All dependencies installed: pip install -r requirements.txt
    - Application icon (optional): deployment/icon.ico

Output:
    - dist/HDS_Route_Sequencer.exe (~160 MB)
    - deployment/HDS_Route_Sequencer_Setup.exe (after Inno Setup compilation)

Author: Your Company
Date: May 26, 2026
Version: 1.0.0
"""

import os
import sys
import shutil
import subprocess

# Configuration
APP_NAME = "HDS_Route_Sequencer"
APP_VERSION = "1.0.0"
ENTRY_POINT = "hds_route_sequencer.py"
ICON_FILE = "deployment/icon.ico"

# The RTR stamp PNG (and anything else pdf_merger.py loads via
# STAMP_IMAGE_PATH / _resource_path) lives here and needs to be bundled
# into the frozen build, not just left next to the source files.
STAMP_ASSET_DIR = "assets"

# Required packages
REQUIRED_PACKAGES = [
    "PyQt6",
    "pdfplumber",
    "PyPDF2",
    "pandas",
    "openpyxl",
    "Pillow",
    "PyMuPDF",
    "pyinstaller"
]

# Local modules to include (hidden imports)
HIDDEN_IMPORTS = [
    "pdf_detector",
    "route_sequencer",
    "pdf_merger",
    "logger",
    "models"
]


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_status(text, status="*"):
    """Print status message"""
    icons = {
        "*": "▶",
        "✓": "✅",
        "✗": "❌",
        "!": "⚠️",
        "i": "ℹ️"
    }
    print(f"[{icons.get(status, status)}] {text}")


def check_dependencies():
    """Verify all required packages are installed"""
    print_header("CHECKING DEPENDENCIES")

    missing = []
    package_map = {
        "PyQt6": "PyQt6",
        "pdfplumber": "pdfplumber",
        "PyPDF2": "PyPDF2",
        "pandas": "pandas",
        "openpyxl": "openpyxl",
        "Pillow": "PIL",
        "PyMuPDF": "fitz",
    }

    for package, import_name in package_map.items():
        try:
            __import__(import_name)
            print_status(f"{package} ... OK", "✓")
        except ImportError:
            print_status(f"{package} ... MISSING", "✗")
            missing.append(package)

    # Check pyinstaller
    try:
        import PyInstaller
        print_status(f"pyinstaller ... OK", "✓")
    except ImportError:
        print_status(f"pyinstaller ... MISSING", "✗")
        missing.append("pyinstaller")

    if missing:
        print_status(
            f"\n❌ Missing packages: {', '.join(missing)}\n"
            f"   Install with: pip install {' '.join(missing)}",
            "!"
        )
        return False

    print_status("All dependencies installed", "✓")
    return True


def check_files():
    """Verify entry point exists"""
    print_header("CHECKING PROJECT FILES")

    if not os.path.exists(ENTRY_POINT):
        print_status(f"Entry point not found: {ENTRY_POINT}", "✗")
        return False

    print_status(f"Found: {ENTRY_POINT}", "✓")

    if os.path.exists(ICON_FILE):
        print_status(f"Found: {ICON_FILE}", "✓")
    else:
        print_status(f"Icon not found (will use default): {ICON_FILE}", "i")

    # The RTR stamp PNG that pdf_merger.py stamps onto RTR order pages - see
    # STAMP_IMAGE_PATH in pdf_merger.py. Warn rather than abort: the app
    # still runs without it, it just skips the stamp.
    if os.path.exists(STAMP_ASSET_DIR):
        print_status(f"Found: {STAMP_ASSET_DIR}", "✓")
    else:
        print_status(
            f"RTR stamp assets not found: {STAMP_ASSET_DIR} "
            f"(build will succeed, but the app won't be able to stamp RTR pages)",
            "!"
        )

    return True


def clean_build_artifacts():
    """Remove previous build artifacts"""
    print_header("CLEANING PREVIOUS BUILDS")

    folders_to_remove = ["build", "dist", "__pycache__"]

    for folder in folders_to_remove:
        if os.path.exists(folder):
            print_status(f"Removing: {folder}")
            shutil.rmtree(folder, ignore_errors=True)
        else:
            print_status(f"Not found (skipping): {folder}", "i")

    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        print_status(f"Removing: {spec_file}")
        os.remove(spec_file)

    print_status("Clean complete", "✓")


def build_executable():
    """Build executable with PyInstaller"""
    print_header("BUILDING EXECUTABLE WITH PYINSTALLER")

    # Import PyInstaller directly and use programmatic API
    try:
        import PyInstaller.__main__
    except ImportError:
        print_status("PyInstaller not found. Installing now...", "!")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                      capture_output=True)
        import PyInstaller.__main__

    # Build arguments
    # NOTE: --onedir (the default, no --onefile flag) instead of --onefile.
    # --onefile re-extracts the whole bundle to a temp folder on every launch,
    # which is what made the app slow to open. --onedir starts instantly.
    args = [
        "--windowed",                         # No console window
        "--name", APP_NAME,                   # Output filename
    ]

    # Add icon if available
    if os.path.exists(ICON_FILE):
        args.extend(["--icon", ICON_FILE])

    # Add hidden imports
    for module in HIDDEN_IMPORTS:
        args.extend(["--hidden-import", module])

    # Bundle the RTR stamp asset folder so pdf_merger.py's STAMP_IMAGE_PATH
    # resolves under sys._MEIPASS in the frozen build. --add-data wants
    # "source<sep>dest_in_bundle" with an OS-specific separator.
    if os.path.exists(STAMP_ASSET_DIR):
        args.extend(["--add-data", f"{STAMP_ASSET_DIR}{os.pathsep}{STAMP_ASSET_DIR}"])

    # Add PyQt6 and other packages that need all modules
    args.extend([
        "--collect-all", "PyQt6",
        "--collect-all", "pdfplumber",
        "--collect-all", "pandas",
        "--collect-all", "openpyxl",
        "--collect-all", "fitz",
    ])

    # Add entry point
    args.append(ENTRY_POINT)

    print_status("Building executable...")
    print_status("(this may take 2-5 minutes on first build)\n", "i")

    try:
        # Call PyInstaller programmatically
        PyInstaller.__main__.run(args)
        print_status("Build completed successfully", "✓")
        return True
    except Exception as e:
        print_status(f"Build error: {str(e)}", "✗")
        return False


def verify_executable():
    """Verify the executable was created"""
    print_header("VERIFYING EXECUTABLE")

    exe_path = f"dist/{APP_NAME}/{APP_NAME}.exe"

    if not os.path.exists(exe_path):
        print_status(f"Executable not found: {exe_path}", "✗")
        return False

    # Get file size
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print_status(f"Found: {exe_path}", "✓")
    print_status(f"Size: {size_mb:.1f} MB", "i")

    if size_mb < 50:
        print_status(
            "Warning: Executable smaller than expected (50+ MB typical)",
            "!"
        )

    return True


def display_completion_info():
    """Display build completion information"""
    print_header("BUILD COMPLETE! ✅")

    exe_path = f"dist/{APP_NAME}/{APP_NAME}.exe"

    print("📦 EXECUTABLE CREATED")
    print(f"   Location: {os.path.abspath(exe_path)}")
    print(f"   Size: {os.path.getsize(exe_path) / (1024*1024):.1f} MB\n")

    print("🧪 TEST THE EXECUTABLE")
    print(f"   {os.path.abspath(exe_path)}\n")

    print("📝 NEXT STEPS")
    print("   1. Test the executable:")
    print(f"      & \"{os.path.abspath(exe_path)}\"\n")
    print("   2. If testing passes, create installer:")
    print("      Open: deployment/installer.iss in Inno Setup")
    print("      Click: Build → Compile\n")
    print("   3. Installer will be created:")
    print("      deployment/HDS_Route_Sequencer_Setup.exe\n")

    print("📖 FOR DETAILED INSTRUCTIONS")
    print("   See: BUILD_INSTRUCTIONS.md\n")


def main():
    """Main build process"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + f"  HDS Route Sequencer - PyInstaller Build Script".center(68) + "║")
    print("║" + f"  Version {APP_VERSION}".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    # Step 1: Check files (critical)
    if not check_files():
        print_status("Aborting build due to missing files", "✗")
        sys.exit(1)

    # Step 2: Clean previous builds
    clean_build_artifacts()

    # Step 3: Build executable
    if not build_executable():
        print_status("Aborting build due to PyInstaller failure", "✗")
        sys.exit(1)

    # Step 4: Verify executable
    if not verify_executable():
        print_status("Aborting build due to verification failure", "✗")
        sys.exit(1)

    # Step 5: Display completion info
    display_completion_info()

    print("="*70)
    print("\n✅ Build script completed successfully!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        sys.exit(1)