#!/usr/bin/env python3
"""
Security Test Runner
Runs comprehensive security test suite and generates report
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def run_security_tests() -> Dict[str, Any]:
    """Run all security tests"""
    print("🔒 Running Security Test Suite...")
    print("=" * 60)
    
    test_modules = [
        "tests/security/test_penetration.py",
        "tests/security/test_dependency_scanning.py",
        "tests/security/test_sast.py",
        "tests/security/test_dast.py",
        "tests/security/test_infrastructure.py",
        "tests/security/test_audit.py",
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "modules": {},
        "summary": {}
    }
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    
    for module in test_modules:
        if not Path(module).exists():
            print(f"⚠️  Skipping {module} (not found)")
            continue
        
        print(f"\n📋 Running {module}...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", module, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse output
            output = result.stdout + result.stderr
            passed = output.count("PASSED")
            failed = output.count("FAILED")
            
            results["modules"][module] = {
                "status": "passed" if result.returncode == 0 else "failed",
                "passed": passed,
                "failed": failed,
                "returncode": result.returncode
            }
            
            total_tests += passed + failed
            total_passed += passed
            total_failed += failed
            
            if result.returncode == 0:
                print(f"✅ {module}: {passed} tests passed")
            else:
                print(f"❌ {module}: {failed} tests failed, {passed} passed")
        
        except subprocess.TimeoutExpired:
            print(f"⏱️  {module}: Timeout")
            results["modules"][module] = {
                "status": "timeout",
                "passed": 0,
                "failed": 0
            }
        except Exception as e:
            print(f"❌ {module}: Error - {e}")
            results["modules"][module] = {
                "status": "error",
                "error": str(e)
            }
    
    # Generate summary
    results["summary"] = {
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
    }
    
    return results


def generate_report(results: Dict[str, Any]):
    """Generate security test report"""
    print("\n" + "=" * 60)
    print("📊 Security Test Report")
    print("=" * 60)
    
    summary = results["summary"]
    print(f"\nTotal Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    
    print("\n📋 Module Results:")
    for module, module_results in results["modules"].items():
        status_icon = "✅" if module_results.get("status") == "passed" else "❌"
        print(f"  {status_icon} {Path(module).name}: {module_results.get('passed', 0)} passed, {module_results.get('failed', 0)} failed")
    
    # Save report
    report_file = Path("security_test_report.json")
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Report saved to: {report_file}")
    
    return summary["success_rate"] >= 80


if __name__ == "__main__":
    results = run_security_tests()
    success = generate_report(results)
    sys.exit(0 if success else 1)

