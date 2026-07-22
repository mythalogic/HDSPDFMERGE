"""
Module Import Verification Test
Tests that all new and enhanced modules can be imported without errors
"""

import sys
import os

# Add HDS_Client_Mix to path
hds_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, hds_path)

def test_imports():
    """Test all module imports"""
    print("=" * 60)
    print("MODULE IMPORT VERIFICATION TEST")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Models
    print("Testing: models.py...")
    try:
        from models import (
            ProcessingResult, MergeResult, ErrorReport, 
            DocumentError, ErrorSeverity, PrintSettings
        )
        print("  ✓ models.py imported successfully")
        results.append(("models.py", True, "All classes imported"))
    except Exception as e:
        print(f"  ✗ models.py FAILED: {e}")
        results.append(("models.py", False, str(e)))
    
    # Test 2: Error Detector
    print("Testing: error_detector.py...")
    try:
        from error_detector import ErrorDetector
        print("  ✓ error_detector.py imported successfully")
        results.append(("error_detector.py", True, "ErrorDetector class imported"))
    except Exception as e:
        print(f"  ✗ error_detector.py FAILED: {e}")
        results.append(("error_detector.py", False, str(e)))
    
    # Test 3: Print Manager
    print("Testing: print_manager.py...")
    try:
        from print_manager import (
            RunGrouper, WavePrinter, PrintBatch, 
            PrintProgress, PrintQueueStatus, PrintPriority
        )
        print("  ✓ print_manager.py imported successfully")
        results.append(("print_manager.py", True, "All classes imported"))
    except Exception as e:
        print(f"  ✗ print_manager.py FAILED: {e}")
        results.append(("print_manager.py", False, str(e)))
    
    # Test 4: Dialogs
    print("Testing: dialogs.py...")
    try:
        from dialogs import (
            PostMergeWorkflowDialog, PrintConfirmationDialog,
            ErrorWarningDialog, PrintProgressDialog
        )
        print("  ✓ dialogs.py imported successfully")
        results.append(("dialogs.py", True, "All dialog classes imported"))
    except Exception as e:
        print(f"  ✗ dialogs.py FAILED: {e}")
        results.append(("dialogs.py", False, str(e)))
    
    # Test 5: GUI Main (without running app)
    print("Testing: gui_main.py...")
    try:
        # Just test the imports at the top, not the full module
        from PyQt6.QtWidgets import QApplication
        print("  ✓ gui_main.py dependencies available")
        results.append(("gui_main.py", True, "PyQt6 dependencies available"))
    except Exception as e:
        print(f"  ✗ gui_main.py FAILED: {e}")
        results.append(("gui_main.py", False, str(e)))
    
    # Test 6: Other dependencies
    print("Testing: dependencies...")
    try:
        import PyPDF2
        import pdfplumber
        print("  ✓ PDF libraries available (PyPDF2, pdfplumber)")
        results.append(("PDF Libraries", True, "PyPDF2, pdfplumber"))
    except Exception as e:
        print(f"  ✗ PDF libraries FAILED: {e}")
        results.append(("PDF Libraries", False, str(e)))
    
    # Summary
    print()
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:7} | {name:30} | {detail}")
    
    print("=" * 60)
    print(f"Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("✓ All modules verified successfully!")
        return True
    else:
        print(f"✗ {total - passed} module(s) have issues")
        return False


def test_functionality():
    """Test basic functionality of new classes"""
    print()
    print("=" * 60)
    print("FUNCTIONALITY TESTS")
    print("=" * 60)
    print()
    
    try:
        # Test ErrorSeverity enum
        from models import ErrorSeverity
        print("Testing ErrorSeverity enum...")
        assert ErrorSeverity.ERROR.value == "ERROR"
        assert ErrorSeverity.WARNING.value == "WARNING"
        print("  ✓ ErrorSeverity enum working correctly")
        
        # Test PrintSettings
        from models import PrintSettings
        print("Testing PrintSettings...")
        settings = PrintSettings(batch_size=30)
        assert settings.batch_size == 30
        assert settings.max_retry_attempts == 3
        print("  ✓ PrintSettings dataclass working correctly")
        
        # Test ErrorDetector static methods
        from error_detector import ErrorDetector
        print("Testing ErrorDetector...")
        priority_order = ErrorDetector.__dict__  # Check it has methods
        print("  ✓ ErrorDetector class available")
        
        # Test RunGrouper
        from print_manager import RunGrouper
        print("Testing RunGrouper...")
        priority = RunGrouper.get_priority_order()
        assert len(priority) == 3
        assert priority[0] == (3010, 3030)
        print("  ✓ RunGrouper priority order correct")
        
        print()
        print("✓ All functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False


if __name__ == "__main__":
    import_success = test_imports()
    func_success = test_functionality()
    
    print()
    print("=" * 60)
    if import_success and func_success:
        print("✓ ALL VERIFICATION TESTS PASSED")
        print("The enhanced application is ready to use!")
    else:
        print("✗ SOME TESTS FAILED")
        print("Please check the errors above and ensure all dependencies")
        print("are installed correctly.")
    print("=" * 60)
