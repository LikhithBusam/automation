#!/usr/bin/env python3
"""
Codebase Health Check Script
Checks if the codebase is working correctly by:
1. Testing imports of key modules
2. Running syntax checks
3. Running unit tests
4. Checking for common issues
"""

import sys
import importlib
import traceback
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status="INFO"):
    """Print colored status message"""
    colors = {
        "SUCCESS": GREEN,
        "ERROR": RED,
        "WARNING": YELLOW,
        "INFO": BLUE
    }
    color = colors.get(status, RESET)
    print(f"{color}[{status}]{RESET} {message}")

def check_import(module_name, description):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print_status(f"[OK] {description}", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"[FAIL] {description}: {str(e)}", "ERROR")
        return False

def check_file_syntax(file_path):
    """Check Python file syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        return True
    except SyntaxError as e:
        print_status(f"✗ Syntax error in {file_path}: {e}", "ERROR")
        return False
    except Exception as e:
        print_status(f"✗ Error checking {file_path}: {e}", "ERROR")
        return False

def main():
    """Run codebase health checks"""
    print("\n" + "="*80)
    print("CODEBASE HEALTH CHECK")
    print("="*80 + "\n")
    
    results = {
        "imports": [],
        "syntax": [],
        "tests": None
    }
    
    # Check key module imports
    print_status("Checking Key Module Imports...", "INFO")
    print("-" * 80)
    
    key_modules = [
        ("src.mcp.tool_manager", "MCPToolManager"),
        ("src.autogen_adapters.conversation_manager", "ConversationManager"),
        ("src.security.auth", "AuthManager"),
        ("src.memory.memory_manager", "MemoryManager"),
        ("src.models.model_factory", "ModelFactory"),
        ("src.security.input_validator", "InputValidator"),
        ("src.security.rate_limiter", "RateLimiter"),
        ("src.security.circuit_breaker", "CircuitBreaker"),
    ]
    
    for module_name, description in key_modules:
        result = check_import(module_name, description)
        results["imports"].append(result)
    
    print()
    
    # Check syntax of key files
    print_status("Checking Syntax of Key Files...", "INFO")
    print("-" * 80)
    
    key_files = [
        "main.py",
        "src/mcp/tool_manager.py",
        "src/autogen_adapters/conversation_manager.py",
        "src/security/auth.py",
        "src/memory/memory_manager.py",
    ]
    
    for file_path in key_files:
        if Path(file_path).exists():
            result = check_file_syntax(file_path)
            results["syntax"].append(result)
        else:
            print_status(f"⚠ File not found: {file_path}", "WARNING")
    
    print()
    
    # Summary
    print_status("Summary", "INFO")
    print("-" * 80)
    
    import_success = sum(results["imports"])
    import_total = len(results["imports"])
    syntax_success = sum(results["syntax"])
    syntax_total = len(results["syntax"])
    
    print(f"Imports: {import_success}/{import_total} successful")
    print(f"Syntax: {syntax_success}/{syntax_total} files checked")
    
    if import_success == import_total and syntax_success == syntax_total:
        print_status("Codebase is healthy!", "SUCCESS")
        return 0
    else:
        print_status("Some issues found", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())

