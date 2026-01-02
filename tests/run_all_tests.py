"""
Test Runner Script
Runs all test suites and provides a summary
"""

import subprocess
import sys
from pathlib import Path


def run_tests(test_path: str, name: str) -> tuple[int, int, int]:
    """Run tests and return (passed, failed, errors)"""
    print(f"\n{'='*80}")
    print(f"Running {name} Tests")
    print(f"{'='*80}\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=line"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Parse results from output
    passed = result.stdout.count(" PASSED")
    failed = result.stdout.count(" FAILED")
    errors = result.stdout.count(" ERROR")
    
    return passed, failed, errors


def main():
    """Run all test suites"""
    test_suites = [
        ("tests/unit/", "Unit"),
        ("tests/integration/", "Integration"),
        ("tests/e2e/", "End-to-End"),
    ]
    
    total_passed = 0
    total_failed = 0
    total_errors = 0
    
    results = {}
    
    for test_path, name in test_suites:
        if Path(test_path).exists():
            passed, failed, errors = run_tests(test_path, name)
            total_passed += passed
            total_failed += failed
            total_errors += errors
            results[name] = {"passed": passed, "failed": failed, "errors": errors}
        else:
            print(f"\n{name} test directory not found: {test_path}")
            results[name] = {"passed": 0, "failed": 0, "errors": 0}
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}\n")
    
    for name, result in results.items():
        print(f"{name} Tests:")
        print(f"  Passed:  {result['passed']}")
        print(f"  Failed:  {result['failed']}")
        print(f"  Errors:  {result['errors']}")
        print()
    
    print(f"Total:")
    print(f"  Passed:  {total_passed}")
    print(f"  Failed:  {total_failed}")
    print(f"  Errors:  {total_errors}")
    print(f"  Total:   {total_passed + total_failed + total_errors}")
    
    if total_failed == 0 and total_errors == 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total_failed + total_errors} test(s) failed or had errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())

