"""
HDS_Client_Mix - PDF Dockets Merger
Combines two PDF files into one merged PDF for picking or delivery dockets
"""

import PyPDF2
import os
from pathlib import Path
from datetime import datetime

# === CONFIGURATION ===
INPUT_FOLDER = r"C:\Python Project\HDS_Client_Mix\input"
OUTPUT_FOLDER = r"C:\Python Project\HDS_Client_Mix\output"

# Create folders if they don't exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def merge_pdfs(pdf1_path, pdf2_path, output_path):
    """
    Merge two PDF files into one
    
    Args:
        pdf1_path: Path to first PDF file
        pdf2_path: Path to second PDF file
        output_path: Path to save merged PDF
    
    Returns:
        tuple: (bool: success status, str: message)
    """
    try:
        print(f"\n[INFO] Starting PDF merge process...")
        print(f"[INFO] PDF 1: {os.path.basename(pdf1_path)}")
        print(f"[INFO] PDF 2: {os.path.basename(pdf2_path)}")
        
        # Open PDFs
        print(f"[INFO] Opening PDF files...")
        pdf1 = PyPDF2.PdfReader(pdf1_path)
        pdf2 = PyPDF2.PdfReader(pdf2_path)
        
        pages1 = len(pdf1.pages)
        pages2 = len(pdf2.pages)
        
        print(f"[SUCCESS] ✓ PDF 1: {pages1} pages")
        print(f"[SUCCESS] ✓ PDF 2: {pages2} pages")
        
        # Create merged PDF
        print(f"[INFO] Creating merged PDF...")
        merger = PyPDF2.PdfMerger()
        
        # Add first PDF
        merger.append(pdf1_path)
        print(f"[SUCCESS] ✓ Added PDF 1")
        
        # Add second PDF
        merger.append(pdf2_path)
        print(f"[SUCCESS] ✓ Added PDF 2")
        
        # Write merged PDF
        merger.write(output_path)
        merger.close()
        
        total_pages = pages1 + pages2
        output_filename = os.path.basename(output_path)
        output_size = os.path.getsize(output_path) / (1024 * 1024)
        
        print(f"[SUCCESS] ✓ Merged PDF created successfully!")
        print(f"[INFO] Total pages: {total_pages}")
        print(f"[INFO] File size: {output_size:.2f} MB")
        print(f"[INFO] Output file: {output_filename}")
        
        return True, output_filename
        
    except FileNotFoundError as e:
        msg = f"File not found: {e}"
        print(f"[ERROR] ❌ {msg}")
        return False, msg
    except Exception as e:
        msg = f"Error merging PDFs: {e}"
        print(f"[ERROR] ❌ {msg}")
        return False, msg

def merge_picking_dockets(pdf1_filename, pdf2_filename):
    """
    Merge two picking docket PDFs
    
    Args:
        pdf1_filename: First PDF file name
        pdf2_filename: Second PDF file name
    
    Returns:
        tuple: (bool: success status, str: output filename or error message)
    """
    pdf1_path = os.path.join(INPUT_FOLDER, pdf1_filename)
    pdf2_path = os.path.join(INPUT_FOLDER, pdf2_filename)
    
    # Check if input files exist
    if not os.path.exists(pdf1_path):
        msg = f"File not found: {pdf1_path}"
        print(f"[ERROR] ❌ {msg}")
        return False, msg
    
    if not os.path.exists(pdf2_path):
        msg = f"File not found: {pdf2_path}"
        print(f"[ERROR] ❌ {msg}")
        return False, msg
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"Picking_Dockets_Merged_{timestamp}.pdf"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
    # Merge PDFs
    return merge_pdfs(pdf1_path, pdf2_path, output_path)

def merge_delivery_dockets(pdf1_filename, pdf2_filename):
    """
    Merge two delivery docket PDFs
    
    Args:
        pdf1_filename: First PDF file name
        pdf2_filename: Second PDF file name
    
    Returns:
        tuple: (bool: success status, str: output filename or error message)
    """
    pdf1_path = os.path.join(INPUT_FOLDER, pdf1_filename)
    pdf2_path = os.path.join(INPUT_FOLDER, pdf2_filename)
    
    # Check if input files exist
    if not os.path.exists(pdf1_path):
        msg = f"File not found: {pdf1_path}"
        print(f"[ERROR] ❌ {msg}")
        return False, msg
    
    if not os.path.exists(pdf2_path):
        msg = f"File not found: {pdf2_path}"
        print(f"[ERROR] ❌ {msg}")
        return False, msg
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"Delivery_Dockets_Merged_{timestamp}.pdf"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
    # Merge PDFs
    return merge_pdfs(pdf1_path, pdf2_path, output_path)

def list_available_pdfs():
    """List all PDF files in input folder"""
    if not os.path.exists(INPUT_FOLDER):
        return []
    
    pdfs = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]
    return sorted(pdfs)

def show_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("HDS_Client_Mix - PDF Dockets Merger")
    print("="*60)
    print("\n📋 MENU:")
    print("  1 - Merge Picking Dockets")
    print("  2 - Merge Delivery Dockets")
    print("  3 - List available PDFs")
    print("  4 - Exit")
    print("\n" + "-"*60)

def main():
    """Main program loop"""
    while True:
        show_menu()
        choice = input("\n👉 Enter choice (1-4): ").strip()
        
        if choice == '1':
            print("\n" + "="*60)
            print("PICKING DOCKETS MERGER")
            print("="*60)
            
            # List available files
            pdfs = list_available_pdfs()
            if len(pdfs) < 2:
                print(f"\n[ERROR] ❌ Need at least 2 PDF files in input folder")
                print(f"Found: {len(pdfs)} file(s)")
                print(f"Location: {INPUT_FOLDER}")
                continue
            
            print(f"\n[INFO] Available PDF files:")
            for i, pdf in enumerate(pdfs, 1):
                print(f"  {i}. {pdf}")
            
            pdf1 = input("\n👉 Enter first PDF filename: ").strip()
            pdf2 = input("👉 Enter second PDF filename: ").strip()
            
            if not pdf1 or not pdf2:
                print("\n[ERROR] ❌ Filenames cannot be empty!")
                continue
            
            success, result = merge_picking_dockets(pdf1, pdf2)
            
            if success:
                print(f"\n[SUCCESS] ✓ Picking dockets merged successfully!")
                print(f"[INFO] Output: {result}")
            else:
                print(f"\n[ERROR] ❌ Failed: {result}")
        
        elif choice == '2':
            print("\n" + "="*60)
            print("DELIVERY DOCKETS MERGER")
            print("="*60)
            
            # List available files
            pdfs = list_available_pdfs()
            if len(pdfs) < 2:
                print(f"\n[ERROR] ❌ Need at least 2 PDF files in input folder")
                print(f"Found: {len(pdfs)} file(s)")
                print(f"Location: {INPUT_FOLDER}")
                continue
            
            print(f"\n[INFO] Available PDF files:")
            for i, pdf in enumerate(pdfs, 1):
                print(f"  {i}. {pdf}")
            
            pdf1 = input("\n👉 Enter first PDF filename: ").strip()
            pdf2 = input("👉 Enter second PDF filename: ").strip()
            
            if not pdf1 or not pdf2:
                print("\n[ERROR] ❌ Filenames cannot be empty!")
                continue
            
            success, result = merge_delivery_dockets(pdf1, pdf2)
            
            if success:
                print(f"\n[SUCCESS] ✓ Delivery dockets merged successfully!")
                print(f"[INFO] Output: {result}")
            else:
                print(f"\n[ERROR] ❌ Failed: {result}")
        
        elif choice == '3':
            print("\n" + "="*60)
            print("AVAILABLE PDF FILES")
            print("="*60)
            
            pdfs = list_available_pdfs()
            
            if not pdfs:
                print(f"\n[INFO] No PDF files found in input folder")
                print(f"Location: {INPUT_FOLDER}")
            else:
                print(f"\n[INFO] Found {len(pdfs)} PDF file(s):\n")
                for i, pdf in enumerate(pdfs, 1):
                    filepath = os.path.join(INPUT_FOLDER, pdf)
                    size = os.path.getsize(filepath) / (1024 * 1024)
                    print(f"  {i}. {pdf} ({size:.2f} MB)")
        
        elif choice == '4':
            print("\n[INFO] Exiting HDS_Client_Mix...")
            print("=" * 60 + "\n")
            break
        
        else:
            print("\n[ERROR] ❌ Invalid choice! Please enter 1-4.")

if __name__ == '__main__':
    main()
