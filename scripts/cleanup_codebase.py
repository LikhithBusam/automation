#!/usr/bin/env python3
"""
Codebase Cleanup Script
Removes redundant files and organizes the codebase for industrial standards
"""

import os
import shutil
from pathlib import Path

# Files to remove (redundant documentation)
REDUNDANT_DOCS = [
    "CODEBASE_REORGANIZATION.md",
    "CODEBASEBUDDY_QUICKSTART.md",
    "CODEBASEBUDDY_USAGE_GUIDE.md",
    "CODEBASEBUDDY_GUIDE.md",
    "MANUAL_TESTING_GUIDE.md",
    "INDUSTRIAL_DEPLOYMENT_GUIDE.md",
    "INDUSTRIAL_AUDIT_REPORT.md",
    "PRODUCTION_FIXES_APPLIED.md",
    "INDUSTRIAL_GRADE_FIXES.md",
    "FIXES_APPLIED_REPORT.md",
    "COMPREHENSIVE_TEST_REPORT.md",
    "QUICK_START_OPTIMIZED.md",
    "INDUSTRIAL_GRADE_REPORT.md",
    "QA_COMPREHENSIVE_TEST_REPORT.md",
    "QA_TEST_REPORT.md",
    "WHITEBOX_TESTING_SUMMARY.md",
    "TESTING_GUIDE.md",
]

# Duplicate directories to remove
DUPLICATE_DIRS = [
    "scripts/daemon",
    "scripts/data",
    "scripts/logs",
    "scripts/reports",
]

# Empty directories to remove
EMPTY_DIRS = [
    "src/utils",
    "${DATA_DIR}",
    "${WORKSPACE_DIR}",
]

def remove_file(filepath: Path, dry_run: bool = False):
    """Remove a file if it exists"""
    if filepath.exists():
        if dry_run:
            print(f"[DRY RUN] Would remove: {filepath}")
        else:
            try:
                filepath.unlink()
                print(f"[OK] Removed: {filepath}")
            except Exception as e:
                print(f"[ERROR] Error removing {filepath}: {e}")
    else:
        print(f"[WARN] File not found: {filepath}")

def remove_directory(dirpath: Path, dry_run: bool = False):
    """Remove a directory if it exists"""
    if dirpath.exists():
        if dry_run:
            print(f"[DRY RUN] Would remove directory: {dirpath}")
        else:
            try:
                shutil.rmtree(dirpath)
                print(f"[OK] Removed directory: {dirpath}")
            except Exception as e:
                print(f"[ERROR] Error removing directory {dirpath}: {e}")
    else:
        print(f"[WARN] Directory not found: {dirpath}")

def main():
    """Main cleanup function"""
    import sys
    
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be deleted")
        print("=" * 80)
    
    root = Path(__file__).parent.parent
    
    print("\n" + "=" * 80)
    print("Codebase Cleanup - Industrial Grade")
    print("=" * 80 + "\n")
    
    # Remove redundant documentation
    print("1. Removing redundant documentation files...")
    for doc in REDUNDANT_DOCS:
        remove_file(root / doc, dry_run)
    
    # Remove duplicate directories
    print("\n2. Removing duplicate directories...")
    for dir_path in DUPLICATE_DIRS:
        remove_directory(root / dir_path, dry_run)
    
    # Remove empty directories
    print("\n3. Removing empty directories...")
    for dir_path in EMPTY_DIRS:
        # Skip invalid paths
        if dir_path.startswith("${"):
            continue
        remove_directory(root / dir_path, dry_run)
    
    # Check for empty utils directory
    utils_dir = root / "src" / "utils"
    if utils_dir.exists():
        try:
            if not any(utils_dir.iterdir()):
                remove_directory(utils_dir, dry_run)
        except Exception:
            pass
    
    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE - No files were actually deleted")
        print("Run without --dry-run to perform actual cleanup")
    else:
        print("CLEANUP COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

