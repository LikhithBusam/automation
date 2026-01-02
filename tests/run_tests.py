"""
Test Runner Script
Runs all tests with coverage reporting
"""

import subprocess
import sys


def run_tests():
    """Run all tests"""
    # Run pytest with coverage
    cmd = [
        "pytest",
        "tests/",
        "-v",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
        "--asyncio-mode=auto"
    ]
    
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())

