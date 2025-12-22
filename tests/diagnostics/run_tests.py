#!/usr/bin/env python
"""
Test Runner for AutoGen Development Assistant
Simple, efficient test execution script
"""
import subprocess
import sys


def run_tests(test_type="all", verbose=False):
    """Run tests with pytest"""
    base_cmd = ["python", "-m", "pytest"]

    if verbose:
        base_cmd.append("-vv")
    else:
        base_cmd.append("-v")

    # Select tests based on type
    if test_type == "unit":
        base_cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        base_cmd.extend(["-m", "integration"])
    elif test_type == "mcp":
        base_cmd.extend(["-m", "mcp"])
    elif test_type == "agent":
        base_cmd.extend(["-m", "agent"])
    elif test_type == "quick":
        base_cmd.extend(["-m", "not slow"])

    print(f"\nRunning {test_type} tests...")
    print(f"Command: {' '.join(base_cmd)}\n")

    result = subprocess.run(base_cmd)
    return result.returncode


def main():
    """Main entry point"""
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    exit_code = run_tests(test_type, verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
