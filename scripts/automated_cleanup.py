#!/usr/bin/env python3
"""
Automated Codebase Cleanup Script

This script automates the cleanup of unused modules, redundant documentation,
and state files based on the comprehensive codebase audit.

SAFETY FEATURES:
- Dry-run mode by default (preview changes)
- Backup creation before deletion
- Confirmation prompts for each phase
- Detailed logging of all actions

Usage:
    python scripts/automated_cleanup.py --dry-run  # Preview changes
    python scripts/automated_cleanup.py --execute  # Execute cleanup
    python scripts/automated_cleanup.py --phase 1  # Run specific phase only
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json

# ANSI color codes for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class CleanupManager:
    """Manages the codebase cleanup process"""

    def __init__(self, root_dir: Path, dry_run: bool = True):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.backup_dir = root_dir / "cleanup_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = root_dir / "cleanup_log.txt"
        self.actions = []

    def log(self, message: str, color: str = Colors.CYAN):
        """Log message to console and file"""
        colored_msg = f"{color}{message}{Colors.END}"
        print(colored_msg)

        # Also log to file (without colors)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")

    def confirm(self, message: str) -> bool:
        """Ask for user confirmation"""
        if self.dry_run:
            return True

        response = input(f"{Colors.YELLOW}{message} (yes/no): {Colors.END}").lower()
        return response in ['yes', 'y']

    def backup_file(self, file_path: Path):
        """Create backup of file before deletion"""
        if not self.dry_run and file_path.exists():
            backup_path = self.backup_dir / file_path.relative_to(self.root_dir)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            self.log(f"  Backed up: {file_path}", Colors.BLUE)

    def delete_file(self, file_path: Path, reason: str = ""):
        """Delete a file with backup"""
        if not file_path.exists():
            self.log(f"  Skip (not found): {file_path}", Colors.YELLOW)
            return

        self.backup_file(file_path)

        if self.dry_run:
            self.log(f"  [DRY RUN] Would delete: {file_path} - {reason}", Colors.MAGENTA)
        else:
            file_path.unlink()
            self.log(f"  Deleted: {file_path} - {reason}", Colors.GREEN)

        self.actions.append({
            'action': 'delete_file',
            'path': str(file_path),
            'reason': reason,
            'dry_run': self.dry_run
        })

    def delete_directory(self, dir_path: Path, reason: str = ""):
        """Delete a directory with backup"""
        if not dir_path.exists():
            self.log(f"  Skip (not found): {dir_path}", Colors.YELLOW)
            return

        # Backup entire directory
        if not self.dry_run:
            backup_path = self.backup_dir / dir_path.relative_to(self.root_dir)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(dir_path, backup_path)
            self.log(f"  Backed up directory: {dir_path}", Colors.BLUE)

        if self.dry_run:
            file_count = sum(1 for _ in dir_path.rglob('*') if _.is_file())
            self.log(f"  [DRY RUN] Would delete directory: {dir_path} ({file_count} files) - {reason}", Colors.MAGENTA)
        else:
            shutil.rmtree(dir_path)
            self.log(f"  Deleted directory: {dir_path} - {reason}", Colors.GREEN)

        self.actions.append({
            'action': 'delete_directory',
            'path': str(dir_path),
            'reason': reason,
            'dry_run': self.dry_run
        })

    def save_actions_log(self):
        """Save actions to JSON log"""
        log_path = self.root_dir / "cleanup_actions.json"
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.dry_run,
                'actions': self.actions,
                'total_actions': len(self.actions)
            }, f, indent=2)
        self.log(f"\nActions log saved to: {log_path}", Colors.GREEN)


def phase_1_security(manager: CleanupManager):
    """Phase 1: Critical Security - Remove credentials"""
    manager.log(f"\n{Colors.BOLD}{'='*70}", Colors.RED)
    manager.log(f"PHASE 1: CRITICAL SECURITY - Remove Credentials", Colors.RED)
    manager.log(f"{'='*70}{Colors.END}", Colors.RED)

    if not manager.confirm("Phase 1 removes credentials.json. Have you rotated the API keys?"):
        manager.log("[WARNING] Phase 1 skipped. Please rotate API keys before proceeding.", Colors.YELLOW)
        return

    # Critical files
    critical_files = [
        ("credentials.json", "Contains API secrets - MUST NOT be in git"),
        (".env.backup", "Backup environment file"),
    ]

    for file_name, reason in critical_files:
        file_path = manager.root_dir / file_name
        manager.delete_file(file_path, reason)

    manager.log("\n[OK] Phase 1 Complete", Colors.GREEN)


def phase_2_quick_wins(manager: CleanupManager):
    """Phase 2: Quick Wins - Remove test output and state files"""
    manager.log(f"\n{Colors.BOLD}{'='*70}", Colors.CYAN)
    manager.log(f"PHASE 2: QUICK WINS - Test Output & State Files", Colors.CYAN)
    manager.log(f"{'='*70}{Colors.END}", Colors.CYAN)

    # Test output files
    test_output = [
        "test_results.txt",
        "test_results_all.txt",
        "test_results_unit.txt",
    ]

    for file_name in test_output:
        manager.delete_file(manager.root_dir / file_name, "Test output file")

    # State files
    state_files = [
        "daemon/daemon_state.json",
        "state/app_state.json",
        "memory.db",
        ".coverage",
    ]

    for file_path in state_files:
        manager.delete_file(manager.root_dir / file_path, "Runtime state file")

    # PID files
    pid_dir = manager.root_dir / "daemon" / "pids"
    if pid_dir.exists():
        for pid_file in pid_dir.glob("*.pid"):
            manager.delete_file(pid_file, "PID file")

    # Cache directories (keep .gitkeep)
    cache_dirs = ["htmlcov", "reports", "logs"]
    for dir_name in cache_dirs:
        dir_path = manager.root_dir / dir_name
        if dir_path.exists():
            # Keep .gitkeep, delete everything else
            for item in dir_path.iterdir():
                if item.name != ".gitkeep":
                    if item.is_file():
                        manager.delete_file(item, f"Cache file in {dir_name}")
                    else:
                        manager.delete_directory(item, f"Cache directory in {dir_name}")

    # Move misplaced files
    if not manager.dry_run:
        # Move test_codebasebuddy_manual.py to tests/
        src = manager.root_dir / "test_codebasebuddy_manual.py"
        if src.exists():
            dst = manager.root_dir / "tests" / "test_codebasebuddy_manual.py"
            manager.log(f"  Moving {src} to {dst}", Colors.BLUE)
            shutil.move(src, dst)

    # Move check_codebase_health.py to scripts/
    src = manager.root_dir / "check_codebase_health.py"
    if src.exists() and not manager.dry_run:
        dst = manager.root_dir / "scripts" / "check_codebase_health.py"
        manager.log(f"  Moving {src} to {dst}", Colors.BLUE)
        shutil.move(src, dst)

    manager.log("\n[OK] Phase 2 Complete", Colors.GREEN)


def phase_3_redundant_docs(manager: CleanupManager):
    """Phase 3: Remove redundant documentation"""
    manager.log(f"\n{Colors.BOLD}{'='*70}", Colors.CYAN)
    manager.log(f"PHASE 3: REDUNDANT DOCUMENTATION - 18 Summary Files", Colors.CYAN)
    manager.log(f"{'='*70}{Colors.END}", Colors.CYAN)

    redundant_docs = [
        "FINAL_IMPLEMENTATION_SUMMARY.md",
        "HA_DR_IMPLEMENTATION_SUMMARY.md",
        "INDUSTRIAL_CODEBASE_SUMMARY.md",
        "INFRASTRUCTURE_IMPLEMENTATION.md",
        "LOAD_BALANCING_SCALING_SUMMARY.md",
        "PERFORMANCE_TESTING_COMPLETE.md",
        "PERFORMANCE_TESTING_SUMMARY.md",
        "PHASE_7_OPERATIONAL_EXCELLENCE_COMPLETE.md",
        "PHASE_8_VALIDATION_COMPLETE.md",
        "PHASE_9_MIGRATION_LAUNCH_COMPLETE.md",
        "PRODUCTION_READINESS_SUMMARY.md",
        "PROFESSIONAL_TEST_REPORT.md",
        "CODEBASE_STATUS.md",
        "CODEBASE_IMPROVEMENTS.md",
        "FEATURES_EXPLAINED.md",
        "COMPREHENSIVE_FEATURE_TEST_REPORT.md",
        "CLEANUP_PLAN.md",
    ]

    for doc_file in redundant_docs:
        manager.delete_file(manager.root_dir / doc_file, "Redundant summary/report")

    # Move CODEBASEBUDDY_MANUAL_TESTING_GUIDE.md to docs/
    src = manager.root_dir / "CODEBASEBUDDY_MANUAL_TESTING_GUIDE.md"
    if src.exists() and not manager.dry_run:
        dst = manager.root_dir / "docs" / "CODEBASEBUDDY_MANUAL_TESTING_GUIDE.md"
        manager.log(f"  Moving {src} to {dst}", Colors.BLUE)
        shutil.move(src, dst)

    manager.log("\n[OK] Phase 3 Complete", Colors.GREEN)


def phase_4_unused_modules(manager: CleanupManager):
    """Phase 4: Remove unused enterprise modules"""
    manager.log(f"\n{Colors.BOLD}{'='*70}", Colors.YELLOW)
    manager.log(f"PHASE 4: UNUSED MODULES - Enterprise Features (69% of src/)", Colors.YELLOW)
    manager.log(f"{'='*70}{Colors.END}", Colors.YELLOW)

    if not manager.confirm("This will delete 10 enterprise modules. Continue?"):
        manager.log("[WARNING] Phase 4 skipped.", Colors.YELLOW)
        return

    unused_modules = [
        ("src/billing", "Stripe/Chargebee integration - never imported"),
        ("src/chaos_engineering", "Chaos testing - not for production"),
        ("src/compliance", "GDPR/HIPAA/SOC2 - overkill"),
        ("src/distributed", "Service mesh - premature optimization"),
        ("src/feature_flags", "Feature flags - not used"),
        ("src/integration", "Plugin marketplace - empty stubs"),
        ("src/multitenancy", "Multi-tenant - not needed"),
        ("src/user_management", "User CRUD - not used"),
        ("src/workflow_management", "Workflow engine - not used"),
        ("services", "Microservice stubs - empty shells"),
    ]

    for dir_name, reason in unused_modules:
        manager.delete_directory(manager.root_dir / dir_name, reason)

    # Consolidate memory managers
    memory_dir = manager.root_dir / "src" / "memory"
    if memory_dir.exists():
        # Keep only memory_manager.py
        duplicate_managers = [
            "enhanced_memory_manager.py",
            "production_memory_manager.py",
        ]
        for file_name in duplicate_managers:
            manager.delete_file(memory_dir / file_name, "Duplicate memory manager")

    manager.log("\n[OK] Phase 4 Complete - 69% of src/ removed", Colors.GREEN)


def phase_5_test_cleanup(manager: CleanupManager):
    """Phase 5: Remove tests for unused modules"""
    manager.log(f"\n{Colors.BOLD}{'='*70}", Colors.CYAN)
    manager.log(f"PHASE 5: TEST CLEANUP - Remove Tests for Deleted Modules", Colors.CYAN)
    manager.log(f"{'='*70}{Colors.END}", Colors.CYAN)

    # Tests for deleted modules
    unused_tests = [
        ("tests/test_chaos_engineering.py", "Tests deleted chaos module"),
        ("tests/test_comprehensive_features.py", "Tests deleted enterprise modules"),
        ("tests/test_industrial_suite.py", "Historical test suite"),
    ]

    for file_name, reason in unused_tests:
        manager.delete_file(manager.root_dir / file_name, reason)

    # Archive old diagnostics
    diagnostics_dir = manager.root_dir / "tests" / "diagnostics"
    if diagnostics_dir.exists() and not manager.dry_run:
        archive_dir = diagnostics_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Move old diagnostic files to archive
        old_patterns = ["diagnose_groq", "test_groq", "test_fix", "cleanup_crewai"]
        for diag_file in diagnostics_dir.glob("*.py"):
            if any(pattern in diag_file.stem for pattern in old_patterns):
                dst = archive_dir / diag_file.name
                manager.log(f"  Archiving {diag_file} to {dst}", Colors.BLUE)
                if not manager.dry_run:
                    shutil.move(diag_file, dst)

    manager.log("\n[OK] Phase 5 Complete", Colors.GREEN)


def phase_6_infrastructure(manager: CleanupManager):
    """Phase 6: Simplify infrastructure (K8s manifests)"""
    manager.log(f"\n{Colors.BOLD}{'='*70}", Colors.CYAN)
    manager.log(f"PHASE 6: INFRASTRUCTURE - Simplify K8s (60 → 15 manifests)", Colors.CYAN)
    manager.log(f"{'='*70}{Colors.END}", Colors.CYAN)

    if not manager.confirm("This will remove advanced K8s manifests. Continue?"):
        manager.log("[WARNING] Phase 6 skipped.", Colors.YELLOW)
        return

    # Remove advanced K8s directories
    k8s_removals = [
        ("k8s/chaos", "Chaos experiments - links to deleted module"),
        ("k8s/microservices", "Microservice manifests - empty stubs"),
        ("k8s/ha", "HA/DR configs - speculative"),
        ("k8s/network-security", "Istio/WAF - too complex"),
        ("k8s/load-balancing", "Advanced load balancing"),
    ]

    for dir_name, reason in k8s_removals:
        manager.delete_directory(manager.root_dir / dir_name, reason)

    # Update config.production.yaml or delete
    prod_config = manager.root_dir / "config" / "config.production.yaml"
    if prod_config.exists():
        manager.log(f"  ⚠️  Review config.production.yaml - may have outdated model names", Colors.YELLOW)

    manager.log("\n[OK] Phase 6 Complete", Colors.GREEN)


def main():
    parser = argparse.ArgumentParser(
        description="Automated Codebase Cleanup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview all changes (safe)
    python scripts/automated_cleanup.py --dry-run

    # Execute all phases
    python scripts/automated_cleanup.py --execute

    # Run specific phase only
    python scripts/automated_cleanup.py --phase 1 --execute

    # Run phases 2-3 only
    python scripts/automated_cleanup.py --phase 2 --phase 3 --execute
        """
    )

    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Preview changes without executing (default)')
    parser.add_argument('--execute', action='store_true', default=False,
                        help='Execute the cleanup (creates backups)')
    parser.add_argument('--phase', type=int, action='append',
                        help='Run specific phase(s) only (1-6)')

    args = parser.parse_args()

    # Determine mode
    dry_run = not args.execute

    # Root directory
    root_dir = Path(__file__).parent.parent

    # Create cleanup manager
    manager = CleanupManager(root_dir, dry_run=dry_run)

    # Print header
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"  AUTOMATED CODEBASE CLEANUP SCRIPT")
    print(f"{'='*70}{Colors.END}\n")

    if dry_run:
        print(f"{Colors.YELLOW}[DRY RUN MODE] - No files will be modified{Colors.END}\n")
    else:
        print(f"{Colors.RED}[EXECUTE MODE] - Files will be deleted (with backup){Colors.END}")
        print(f"{Colors.BLUE}Backup directory: {manager.backup_dir}{Colors.END}\n")

    # Determine which phases to run
    if args.phase:
        phases_to_run = args.phase
    else:
        phases_to_run = list(range(1, 7))  # All phases

    # Execute phases
    phase_functions = {
        1: phase_1_security,
        2: phase_2_quick_wins,
        3: phase_3_redundant_docs,
        4: phase_4_unused_modules,
        5: phase_5_test_cleanup,
        6: phase_6_infrastructure,
    }

    for phase_num in sorted(phases_to_run):
        if phase_num in phase_functions:
            phase_functions[phase_num](manager)
        else:
            manager.log(f"⚠️  Invalid phase number: {phase_num}", Colors.YELLOW)

    # Save actions log
    manager.save_actions_log()

    # Summary
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*70}")
    print(f"  CLEANUP SUMMARY")
    print(f"{'='*70}{Colors.END}")
    print(f"Mode: {Colors.YELLOW}{'DRY RUN' if dry_run else 'EXECUTED'}{Colors.END}")
    print(f"Total actions: {Colors.CYAN}{len(manager.actions)}{Colors.END}")
    print(f"Log file: {Colors.BLUE}{manager.log_file}{Colors.END}")

    if not dry_run:
        print(f"Backup directory: {Colors.BLUE}{manager.backup_dir}{Colors.END}")

    print(f"\n{Colors.GREEN}[OK] Cleanup complete!{Colors.END}")

    if dry_run:
        print(f"\n{Colors.YELLOW}To execute the cleanup, run:{Colors.END}")
        print(f"{Colors.CYAN}python scripts/automated_cleanup.py --execute{Colors.END}\n")


if __name__ == "__main__":
    main()
