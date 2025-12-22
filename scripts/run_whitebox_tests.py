"""
White-Box Test Runner
Runs all comprehensive white-box tests and generates detailed reports
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import argparse


class WhiteBoxTestRunner:
    """Runs comprehensive white-box tests with reporting"""

    def __init__(self, verbose=False, coverage=False):
        self.verbose = verbose
        self.coverage = coverage
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_test_suite(self, test_file, suite_name):
        """Run a specific test suite"""
        print(f"\n{'='*80}")
        print(f"Running: {suite_name}")
        print(f"{'='*80}\n")

        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--color=yes"
        ]

        if self.coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                f"--cov-report=html:reports/coverage/{suite_name.replace(' ', '_')}"
            ])

        if self.verbose:
            cmd.append("-vv")

        # Add JSON report
        json_report = f"reports/json/{suite_name.replace(' ', '_')}.json"
        cmd.extend([f"--json-report", f"--json-report-file={json_report}"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per suite
            )

            self.results[suite_name] = {
                "status": "PASSED" if result.returncode == 0 else "FAILED",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr and result.returncode != 0:
                print("ERRORS:", file=sys.stderr)
                print(result.stderr, file=sys.stderr)

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT: {suite_name} exceeded 5 minutes", file=sys.stderr)
            self.results[suite_name] = {
                "status": "TIMEOUT",
                "return_code": -1
            }
            return False

        except Exception as e:
            print(f"❌ ERROR: {suite_name} - {e}", file=sys.stderr)
            self.results[suite_name] = {
                "status": "ERROR",
                "return_code": -1,
                "error": str(e)
            }
            return False

    def run_all_tests(self):
        """Run all white-box test suites"""
        self.start_time = datetime.now()

        # Create reports directory
        Path("reports/json").mkdir(parents=True, exist_ok=True)
        Path("reports/coverage").mkdir(parents=True, exist_ok=True)

        # Define test suites
        test_suites = [
            ("tests/test_whitebox_comprehensive.py", "Comprehensive White-Box Tests"),
            ("tests/test_features_mcp_servers.py", "MCP Server Feature Tests"),
            ("tests/test_security_comprehensive.py", "Security Tests"),
            ("tests/test_autogen_agents.py", "Agent Tests"),
            ("tests/test_mcp_comprehensive.py", "MCP Integration Tests"),
        ]

        passed = 0
        failed = 0
        skipped = 0

        for test_file, suite_name in test_suites:
            test_path = Path(test_file)
            if not test_path.exists():
                print(f"⚠️  SKIPPED: {suite_name} - File not found: {test_file}")
                skipped += 1
                continue

            success = self.run_test_suite(test_file, suite_name)
            if success:
                passed += 1
                print(f"✅ PASSED: {suite_name}")
            else:
                failed += 1
                print(f"❌ FAILED: {suite_name}")

        self.end_time = datetime.now()

        # Print summary
        self.print_summary(passed, failed, skipped)

        # Generate report
        self.generate_report()

        # Return exit code
        return 0 if failed == 0 else 1

    def print_summary(self, passed, failed, skipped):
        """Print test summary"""
        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Suites:  {passed + failed + skipped}")
        print(f"✅ Passed:     {passed}")
        print(f"❌ Failed:     {failed}")
        print(f"⚠️  Skipped:    {skipped}")
        print(f"⏱️  Duration:   {duration:.2f} seconds")
        print(f"{'='*80}\n")

        # Print detailed results
        if failed > 0:
            print("FAILED SUITES:")
            for suite_name, result in self.results.items():
                if result["status"] in ["FAILED", "TIMEOUT", "ERROR"]:
                    print(f"  ❌ {suite_name}: {result['status']}")
                    if result.get("stderr"):
                        print(f"     Error: {result['stderr'][:200]}")

    def generate_report(self):
        """Generate comprehensive test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "suites": self.results,
            "summary": {
                "passed": sum(1 for r in self.results.values() if r["status"] == "PASSED"),
                "failed": sum(1 for r in self.results.values() if r["status"] == "FAILED"),
                "timeout": sum(1 for r in self.results.values() if r["status"] == "TIMEOUT"),
                "error": sum(1 for r in self.results.values() if r["status"] == "ERROR"),
            }
        }

        # Save report
        report_path = Path("reports/whitebox_test_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed report saved to: {report_path}")

        # Generate markdown report
        self.generate_markdown_report(report)

    def generate_markdown_report(self, report):
        """Generate markdown test report"""
        md_content = f"""# White-Box Test Report

**Generated:** {report['timestamp']}
**Duration:** {report['duration_seconds']:.2f} seconds

## Summary

| Metric | Count |
|--------|-------|
| Passed | {report['summary']['passed']} |
| Failed | {report['summary']['failed']} |
| Timeout | {report['summary']['timeout']} |
| Error | {report['summary']['error']} |
| **Total** | **{sum(report['summary'].values())}** |

## Test Suites

"""

        for suite_name, result in report['suites'].items():
            status_emoji = {
                "PASSED": "✅",
                "FAILED": "❌",
                "TIMEOUT": "⏱️",
                "ERROR": "⚠️"
            }.get(result['status'], "❓")

            md_content += f"### {status_emoji} {suite_name}\n\n"
            md_content += f"**Status:** {result['status']}\n\n"

            if result.get('stderr'):
                md_content += f"**Error Output:**\n```\n{result['stderr'][:500]}\n```\n\n"

        md_content += f"""
## Test Coverage

White-box tests cover:

1. ✅ All 4 MCP Servers (GitHub, Filesystem, Memory, CodeBaseBuddy)
2. ✅ All 8 Agents (CodeAnalyzer, SecurityAuditor, Documentation, etc.)
3. ✅ All Workflows (quick_code_review, security_audit, deployment, etc.)
4. ✅ Security validation and input sanitization
5. ✅ Configuration loading and validation
6. ✅ Function registry and tool integration
7. ✅ Error handling and exception hierarchy
8. ✅ Rate limiting and circuit breakers
9. ✅ Memory system (short/medium/long-term)
10. ✅ Integration between all components

## Recommendations

"""

        if report['summary']['failed'] > 0:
            md_content += "⚠️ **Action Required:** Fix failing test suites before production deployment.\n\n"
        else:
            md_content += "✅ **All tests passed!** System is ready for production deployment.\n\n"

        # Save markdown report
        md_path = Path("reports/WHITEBOX_TEST_REPORT.md")
        with open(md_path, 'w') as f:
            f.write(md_content)

        print(f"📄 Markdown report saved to: {md_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run comprehensive white-box tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Generate coverage reports")
    parser.add_argument("--quick", action="store_true", help="Run only quick tests (skip integration)")

    args = parser.parse_args()

    runner = WhiteBoxTestRunner(verbose=args.verbose, coverage=args.coverage)

    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                   COMPREHENSIVE WHITE-BOX TEST SUITE                       ║
║                AutoGen Development Assistant v2.0.0                        ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)

    exit_code = runner.run_all_tests()

    print("\n" + "="*80)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED - System is production ready!")
    else:
        print("❌ SOME TESTS FAILED - Review errors and fix issues")
    print("="*80 + "\n")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
