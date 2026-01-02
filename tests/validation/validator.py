"""
Core Validation Framework

Provides base classes and utilities for comprehensive feature validation.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of a validation check"""

    name: str
    status: ValidationStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class ValidationCheck:
    """Base class for validation checks"""

    def __init__(self, name: str, description: str = "", required: bool = True):
        """
        Initialize validation check

        Args:
            name: Check name
            description: Check description
            required: Whether this check is required for acceptance
        """
        self.name = name
        self.description = description
        self.required = required

    async def run(self) -> ValidationResult:
        """
        Run the validation check

        Returns:
            ValidationResult
        """
        start_time = time.time()

        try:
            result = await self._execute()
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            logger.error(f"Validation check '{self.name}' failed with error: {e}", exc_info=True)
            return ValidationResult(
                name=self.name,
                status=ValidationStatus.ERROR,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    async def _execute(self) -> ValidationResult:
        """
        Execute the validation check (to be implemented by subclasses)

        Returns:
            ValidationResult
        """
        raise NotImplementedError


class ValidationFramework:
    """
    Framework for running comprehensive validation checks

    Organizes and executes validation checks across different categories.
    """

    def __init__(self):
        """Initialize validation framework"""
        self.checks: Dict[str, List[ValidationCheck]] = {}
        self.results: Dict[str, List[ValidationResult]] = {}

    def register_check(self, category: str, check: ValidationCheck):
        """
        Register a validation check

        Args:
            category: Category name (e.g., "agents", "security", "performance")
            check: ValidationCheck instance
        """
        if category not in self.checks:
            self.checks[category] = []
        self.checks[category].append(check)
        logger.debug(f"Registered check '{check.name}' in category '{category}'")

    async def run_category(self, category: str) -> List[ValidationResult]:
        """
        Run all checks in a category

        Args:
            category: Category name

        Returns:
            List of ValidationResults
        """
        if category not in self.checks:
            logger.warning(f"Category '{category}' not found")
            return []

        logger.info(f"Running validation category: {category}")
        results = []

        for check in self.checks[category]:
            logger.info(f"Running check: {check.name}")
            result = await check.run()
            results.append(result)

            # Log result
            if result.status == ValidationStatus.PASSED:
                logger.info(f"✅ {check.name}: PASSED ({result.duration_ms:.2f}ms)")
            elif result.status == ValidationStatus.FAILED:
                logger.error(f"❌ {check.name}: FAILED - {result.message}")
            elif result.status == ValidationStatus.WARNING:
                logger.warning(f"⚠️  {check.name}: WARNING - {result.message}")
            elif result.status == ValidationStatus.SKIPPED:
                logger.info(f"⏭️  {check.name}: SKIPPED - {result.message}")
            else:
                logger.error(f"💥 {check.name}: ERROR - {result.message}")

        # Store results
        self.results[category] = results
        return results

    async def run_all(self) -> Dict[str, List[ValidationResult]]:
        """
        Run all validation checks across all categories

        Returns:
            Dictionary mapping category to list of ValidationResults
        """
        logger.info("Starting comprehensive validation")
        start_time = time.time()

        for category in self.checks:
            await self.run_category(category)

        total_time = time.time() - start_time
        logger.info(f"Validation complete in {total_time:.2f}s")

        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of validation results

        Returns:
            Summary dictionary with counts and percentages
        """
        total_checks = 0
        passed = 0
        failed = 0
        warnings = 0
        errors = 0
        skipped = 0

        category_summaries = {}

        for category, results in self.results.items():
            cat_total = len(results)
            cat_passed = sum(1 for r in results if r.status == ValidationStatus.PASSED)
            cat_failed = sum(1 for r in results if r.status == ValidationStatus.FAILED)
            cat_warnings = sum(1 for r in results if r.status == ValidationStatus.WARNING)
            cat_errors = sum(1 for r in results if r.status == ValidationStatus.ERROR)
            cat_skipped = sum(1 for r in results if r.status == ValidationStatus.SKIPPED)

            total_checks += cat_total
            passed += cat_passed
            failed += cat_failed
            warnings += cat_warnings
            errors += cat_errors
            skipped += cat_skipped

            category_summaries[category] = {
                "total": cat_total,
                "passed": cat_passed,
                "failed": cat_failed,
                "warnings": cat_warnings,
                "errors": cat_errors,
                "skipped": cat_skipped,
                "pass_rate": (cat_passed / cat_total * 100) if cat_total > 0 else 0,
            }

        return {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": (passed / total_checks * 100) if total_checks > 0 else 0,
            "categories": category_summaries,
        }

    def is_production_ready(self) -> bool:
        """
        Check if system is production ready based on validation results

        Criteria:
        - All required checks must pass
        - No errors allowed
        - Warnings are acceptable but logged
        - Pass rate must be >= 95%

        Returns:
            True if production ready, False otherwise
        """
        summary = self.get_summary()

        # Check for errors
        if summary["errors"] > 0:
            logger.error("System not production ready: validation errors detected")
            return False

        # Check for failed required checks
        for category, results in self.results.items():
            for result in results:
                # Find the check
                check = next(
                    (c for c in self.checks[category] if c.name == result.name), None
                )
                if check and check.required and result.status == ValidationStatus.FAILED:
                    logger.error(
                        f"System not production ready: required check '{result.name}' failed"
                    )
                    return False

        # Check pass rate
        if summary["pass_rate"] < 95.0:
            logger.error(
                f"System not production ready: pass rate {summary['pass_rate']:.1f}% < 95%"
            )
            return False

        logger.info("✅ System is production ready!")
        return True

    def generate_report(self, format: str = "text") -> str:
        """
        Generate validation report

        Args:
            format: Report format ("text", "json", "html")

        Returns:
            Formatted report string
        """
        summary = self.get_summary()

        if format == "text":
            return self._generate_text_report(summary)
        elif format == "json":
            import json

            return json.dumps(
                {"summary": summary, "results": {cat: [r.to_dict() for r in results] for cat, results in self.results.items()}},
                indent=2,
            )
        elif format == "html":
            return self._generate_html_report(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_text_report(self, summary: Dict[str, Any]) -> str:
        """Generate text report"""
        lines = []
        lines.append("=" * 80)
        lines.append("VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Overall summary
        lines.append("OVERALL SUMMARY:")
        lines.append(f"  Total Checks: {summary['total_checks']}")
        lines.append(f"  ✅ Passed: {summary['passed']}")
        lines.append(f"  ❌ Failed: {summary['failed']}")
        lines.append(f"  ⚠️  Warnings: {summary['warnings']}")
        lines.append(f"  💥 Errors: {summary['errors']}")
        lines.append(f"  ⏭️  Skipped: {summary['skipped']}")
        lines.append(f"  Pass Rate: {summary['pass_rate']:.1f}%")
        lines.append("")

        # Production ready status
        is_ready = self.is_production_ready()
        status = "✅ PRODUCTION READY" if is_ready else "❌ NOT PRODUCTION READY"
        lines.append(f"Status: {status}")
        lines.append("")

        # Category details
        for category, cat_summary in summary["categories"].items():
            lines.append(f"\n{category.upper()}:")
            lines.append(f"  Total: {cat_summary['total']}")
            lines.append(f"  Passed: {cat_summary['passed']}")
            lines.append(f"  Failed: {cat_summary['failed']}")
            lines.append(f"  Pass Rate: {cat_summary['pass_rate']:.1f}%")

            # Failed checks details
            failed_results = [
                r for r in self.results[category] if r.status == ValidationStatus.FAILED
            ]
            if failed_results:
                lines.append("\n  Failed Checks:")
                for result in failed_results:
                    lines.append(f"    ❌ {result.name}: {result.message}")

            # Warning checks details
            warning_results = [
                r for r in self.results[category] if r.status == ValidationStatus.WARNING
            ]
            if warning_results:
                lines.append("\n  Warnings:")
                for result in warning_results:
                    lines.append(f"    ⚠️  {result.name}: {result.message}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

    def _generate_html_report(self, summary: Dict[str, Any]) -> str:
        """Generate HTML report"""
        is_ready = self.is_production_ready()
        status_color = "green" if is_ready else "red"
        status_text = "PRODUCTION READY" if is_ready else "NOT PRODUCTION READY"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .status {{ font-size: 24px; font-weight: bold; color: {status_color}; }}
        .category {{ margin: 20px 0; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .warning {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Validation Report</h1>
    <p class="status">{status_text}</p>

    <div class="summary">
        <h2>Overall Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Checks</td><td>{summary['total_checks']}</td></tr>
            <tr><td class="passed">Passed</td><td>{summary['passed']}</td></tr>
            <tr><td class="failed">Failed</td><td>{summary['failed']}</td></tr>
            <tr><td class="warning">Warnings</td><td>{summary['warnings']}</td></tr>
            <tr><td>Errors</td><td>{summary['errors']}</td></tr>
            <tr><td>Skipped</td><td>{summary['skipped']}</td></tr>
            <tr><td><strong>Pass Rate</strong></td><td><strong>{summary['pass_rate']:.1f}%</strong></td></tr>
        </table>
    </div>
"""

        # Add category details
        for category, cat_summary in summary["categories"].items():
            html += f"""
    <div class="category">
        <h2>{category.title()}</h2>
        <p>Pass Rate: {cat_summary['pass_rate']:.1f}% ({cat_summary['passed']}/{cat_summary['total']})</p>
        <table>
            <tr><th>Check</th><th>Status</th><th>Message</th><th>Duration (ms)</th></tr>
"""
            for result in self.results[category]:
                status_class = result.status.value
                html += f"""
            <tr>
                <td>{result.name}</td>
                <td class="{status_class}">{result.status.value.upper()}</td>
                <td>{result.message}</td>
                <td>{result.duration_ms:.2f}</td>
            </tr>
"""
            html += """
        </table>
    </div>
"""

        html += """
</body>
</html>
"""
        return html


class FunctionValidationCheck(ValidationCheck):
    """Validation check that runs a function"""

    def __init__(
        self,
        name: str,
        description: str,
        check_function: Callable,
        required: bool = True,
    ):
        """
        Initialize function validation check

        Args:
            name: Check name
            description: Check description
            check_function: Async function that returns (bool, str, dict)
                           where bool is pass/fail, str is message, dict is details
            required: Whether this check is required
        """
        super().__init__(name, description, required)
        self.check_function = check_function

    async def _execute(self) -> ValidationResult:
        """Execute the check function"""
        try:
            result = await self.check_function()

            if isinstance(result, tuple) and len(result) >= 2:
                passed, message = result[0], result[1]
                details = result[2] if len(result) > 2 else {}
            else:
                passed = bool(result)
                message = "Check completed"
                details = {}

            return ValidationResult(
                name=self.name,
                status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
                message=message,
                details=details,
            )
        except Exception as e:
            return ValidationResult(
                name=self.name,
                status=ValidationStatus.ERROR,
                message=f"Check function raised exception: {str(e)}",
            )
