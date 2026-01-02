#!/usr/bin/env python3
"""
Cleanup Script: Remove CrewAI Components
This script removes CrewAI-specific files and prepares the codebase for AutoGen
"""

import os
import shutil
from pathlib import Path

# Files and directories to remove
REMOVE_FILES = [
    # CrewAI Agent Implementations
    "src/agents/base_agent.py",
    "src/agents/code_analyzer_agent.py",
    "src/agents/deployment_agent.py",
    "src/agents/documentation_agent.py",
    "src/agents/project_manager_agent.py",
    "src/agents/research_agent.py",
    "src/agents/__init__.py",
    # CrewAI Workflow Manager
    "src/workflows/crew_manager.py",
    "src/workflows/__init__.py",
    # CrewAI Tool Wrapper
    "src/mcp/crewai_wrapper.py",
    # Old main.py (will be replaced)
    "main.py.crewai.backup",  # We'll rename current main.py to this
]

REMOVE_DIRS = [
    "src/agents",  # Will be replaced with AutoGen agents
    "src/workflows",  # Will be replaced with AutoGen conversations
]

KEEP_FILES = [
    # MCP Tools (independent of CrewAI/AutoGen)
    "src/mcp/base_tool.py",
    "src/mcp/tool_manager.py",
    "src/mcp/github_tool.py",
    "src/mcp/filesystem_tool.py",
    "src/mcp/memory_tool.py",
    "src/mcp/slack_tool.py",
    "src/mcp/__init__.py",
    # Memory System (independent)
    "src/memory/memory_manager.py",
    "src/memory/__init__.py",
    # Models (keep OpenRouter LLM)
    "src/models/openrouter_llm.py",
    "src/models/__init__.py",
    # Security (independent)
    "src/security/auth.py",
    "src/security/validation.py",
    "src/security/__init__.py",
    # API (independent)
    "src/api/health.py",
]


def backup_file(filepath):
    """Backup a file before removing"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)
        print(f"  [OK] Backed up: {filepath} -> {backup_path}")
        return True
    return False


def remove_file(filepath):
    """Remove a file"""
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"  [X] Removed: {filepath}")
        return True
    else:
        print(f"  [-] Not found: {filepath}")
        return False


def remove_directory(dirpath):
    """Remove a directory and its contents"""
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        shutil.rmtree(dirpath)
        print(f"  [X] Removed directory: {dirpath}")
        return True
    else:
        print(f"  [-] Directory not found: {dirpath}")
        return False


def main():
    print("=" * 70)
    print("CrewAI Cleanup Script")
    print("=" * 70)
    print()

    # Get current directory
    base_dir = Path.cwd()
    print(f"Working directory: {base_dir}")
    print()

    # Step 1: Backup main.py
    print("Step 1: Backup main.py")
    print("-" * 70)
    if backup_file("main.py"):
        shutil.move("main.py", "main.py.crewai.backup")
        print("  [OK] Renamed main.py -> main.py.crewai.backup")
    print()

    # Step 2: Remove CrewAI agent files
    print("Step 2: Remove CrewAI Agent Files")
    print("-" * 70)
    removed_count = 0
    for filepath in REMOVE_FILES:
        if filepath != "main.py.crewai.backup":  # Already handled
            if remove_file(filepath):
                removed_count += 1
    print(f"  Summary: Removed {removed_count} files")
    print()

    # Step 3: Remove CrewAI directories
    print("Step 3: Remove CrewAI Directories")
    print("-" * 70)
    for dirpath in REMOVE_DIRS:
        remove_directory(dirpath)
    print()

    # Step 4: Show what's kept
    print("Step 4: Verify Kept Components")
    print("-" * 70)
    kept_count = 0
    for filepath in KEEP_FILES:
        if os.path.exists(filepath):
            print(f"  [OK] Kept: {filepath}")
            kept_count += 1
        else:
            print(f"  [!] Missing (should exist): {filepath}")
    print(f"  Summary: {kept_count} files kept")
    print()

    # Step 5: Create AutoGen directory structure
    print("Step 5: Create AutoGen Directory Structure")
    print("-" * 70)
    autogen_dirs = [
        "src/autogen_agents",
        "src/autogen_conversations",
        "src/autogen_adapters",
    ]
    for dirpath in autogen_dirs:
        os.makedirs(dirpath, exist_ok=True)
        print(f"  [OK] Created: {dirpath}")

        # Create __init__.py
        init_file = os.path.join(dirpath, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write(f'"""{os.path.basename(dirpath)} package"""\n')
            print(f"  [OK] Created: {init_file}")
    print()

    # Summary
    print("=" * 70)
    print("Cleanup Summary")
    print("=" * 70)
    print()
    print("[REMOVED]")
    print("  - CrewAI agent implementations (src/agents/)")
    print("  - CrewAI workflow manager (src/workflows/)")
    print("  - CrewAI wrapper (src/mcp/crewai_wrapper.py)")
    print("  - Old main.py (backed up as main.py.crewai.backup)")
    print()
    print("[KEPT]")
    print("  - MCP tool implementations (src/mcp/)")
    print("  - Memory manager (src/memory/)")
    print("  - OpenRouter LLM (src/models/openrouter_llm.py)")
    print("  - Security modules (src/security/)")
    print("  - API modules (src/api/)")
    print()
    print("[CREATED]")
    print("  - src/autogen_agents/ (for AutoGen agent implementations)")
    print("  - src/autogen_conversations/ (for conversation patterns)")
    print("  - src/autogen_adapters/ (for AutoGen integration)")
    print()
    print("Next steps:")
    print("  1. Update requirements.txt (remove crewai, add pyautogen)")
    print("  2. Implement AutoGen adapters")
    print("  3. Create new main.py with AutoGen")
    print("  4. Test the AutoGen implementation")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
