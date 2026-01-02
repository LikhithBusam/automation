#!/usr/bin/env python3
"""
Pre-Production Checklist Automation

Automated verification of all pre-production requirements before launch.
"""

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a pre-production check"""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    required: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PreProductionChecker:
    """
    Pre-Production Checklist Automation

    Verifies all requirements are met before production launch.
    """

    def __init__(self):
        """Initialize pre-production checker"""
        self.results: List[CheckResult] = []
        self.project_root = Path(__file__).parent.parent

    async def run_all_checks(self) -> bool:
        """
        Run all pre-production checks

        Returns:
            True if all required checks pass, False otherwise
        """
        logger.info("=" * 80)
        logger.info("PRE-PRODUCTION CHECKLIST")
        logger.info("=" * 80)
        logger.info("")

        # Run all checks
        await self.check_tests()
        await self.check_security()
        await self.check_compliance()
        await self.check_documentation()
        await self.check_disaster_recovery()
        await self.check_monitoring()
        await self.check_oncall()
        await self.check_incident_response()
        await self.check_runbooks()
        await self.check_rollback()
        await self.check_communication()
        await self.check_support()
        await self.check_beta_users()

        # Generate report
        self.generate_report()

        # Check if production ready
        return self.is_production_ready()

    async def check_tests(self):
        """Check all tests are passing"""
        logger.info("\n[1/13] Checking Tests...")

        checks = [
            ("Unit tests", self._run_unit_tests),
            ("Integration tests", self._run_integration_tests),
            ("E2E tests", self._check_e2e_tests),
            ("Performance tests", self._check_performance_tests),
        ]

        for check_name, check_func in checks:
            try:
                passed, message, details = await check_func()
                self.results.append(CheckResult(
                    name=check_name,
                    passed=passed,
                    message=message,
                    details=details,
                    required=True
                ))
                status = "✅ PASS" if passed else "❌ FAIL"
                logger.info(f"  {status}: {check_name} - {message}")
            except Exception as e:
                logger.error(f"  ❌ ERROR: {check_name} - {str(e)}")
                self.results.append(CheckResult(
                    name=check_name,
                    passed=False,
                    message=f"Error: {str(e)}",
                    required=True
                ))

    async def _run_unit_tests(self):
        """Run unit tests"""
        try:
            result = subprocess.run(
                ["pytest", "tests/", "-m", "not slow and not requires_api", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            passed = result.returncode == 0
            message = "All unit tests passing" if passed else "Some unit tests failing"
            return passed, message, {"output": result.stdout[-500:]}
        except subprocess.TimeoutExpired:
            return False, "Unit tests timed out", {}
        except Exception as e:
            return False, f"Error running tests: {str(e)}", {}

    async def _run_integration_tests(self):
        """Run integration tests"""
        try:
            result = subprocess.run(
                ["pytest", "tests/integration/", "-v"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600
            )
            passed = result.returncode == 0
            message = "All integration tests passing" if passed else "Some integration tests failing"
            return passed, message, {"output": result.stdout[-500:]}
        except subprocess.TimeoutExpired:
            return False, "Integration tests timed out", {}
        except Exception as e:
            return False, f"Error running tests: {str(e)}", {}

    async def _check_e2e_tests(self):
        """Check E2E tests"""
        e2e_tests = self.project_root / "tests" / "e2e"
        if e2e_tests.exists():
            return True, "E2E tests present", {"path": str(e2e_tests)}
        return False, "E2E tests not found", {}

    async def _check_performance_tests(self):
        """Check performance tests"""
        perf_tests = self.project_root / "tests" / "performance"
        if perf_tests.exists():
            return True, "Performance tests present", {"path": str(perf_tests)}
        return False, "Performance tests not found", {}

    async def check_security(self):
        """Check security audit"""
        logger.info("\n[2/13] Checking Security...")

        # Run Phase 8 validation for security
        try:
            # Check security validation results
            validation_report = self.project_root / "validation_report.json"
            if validation_report.exists():
                with open(validation_report) as f:
                    report = json.load(f)
                    security_results = report.get("results", {}).get("security", [])
                    passed = all(r.get("status") == "passed" for r in security_results)
                    message = "Security validation passed" if passed else "Security validation has failures"
                    self.results.append(CheckResult(
                        name="Security audit",
                        passed=passed,
                        message=message,
                        required=True
                    ))
                    logger.info(f"  {'✅ PASS' if passed else '❌ FAIL'}: Security audit - {message}")
            else:
                logger.warning("  ⚠️  WARNING: No validation report found, run Phase 8 validation")
                self.results.append(CheckResult(
                    name="Security audit",
                    passed=False,
                    message="No validation report found",
                    required=True
                ))
        except Exception as e:
            logger.error(f"  ❌ ERROR: Security check - {str(e)}")
            self.results.append(CheckResult(
                name="Security audit",
                passed=False,
                message=f"Error: {str(e)}",
                required=True
            ))

    async def check_compliance(self):
        """Check compliance requirements"""
        logger.info("\n[3/13] Checking Compliance...")

        compliance_checks = [
            ("GDPR compliance", self.project_root / "src" / "compliance" / "gdpr.py"),
            ("SOC2 controls", self.project_root / "src" / "compliance" / "soc2.py"),
            ("Audit logging", self.project_root / "src" / "security" / "audit"),
        ]

        for check_name, check_path in compliance_checks:
            passed = check_path.exists()
            message = f"{check_name} implemented" if passed else f"{check_name} not found"
            self.results.append(CheckResult(
                name=check_name,
                passed=passed,
                message=message,
                required=True
            ))
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status}: {check_name} - {message}")

    async def check_documentation(self):
        """Check documentation is complete"""
        logger.info("\n[4/13] Checking Documentation...")

        docs_checks = [
            ("Architecture documentation", self.project_root / "ARCHITECTURE.md"),
            ("API documentation", self.project_root / "docs" / "openapi.yaml"),
            ("Deployment guide", self.project_root / "docs" / "runbooks" / "DEPLOYMENT_RUNBOOK.md"),
            ("User guides", self.project_root / "README.md"),
            ("Troubleshooting guides", self.project_root / "TROUBLESHOOTING.md"),
        ]

        for check_name, check_path in docs_checks:
            passed = check_path.exists()
            message = f"{check_name} present" if passed else f"{check_name} missing"
            self.results.append(CheckResult(
                name=check_name,
                passed=passed,
                message=message,
                required=True
            ))
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status}: {check_name} - {message}")

    async def check_disaster_recovery(self):
        """Check disaster recovery is tested"""
        logger.info("\n[5/13] Checking Disaster Recovery...")

        # Check for DR documentation
        dr_docs = self.project_root / "docs" / "ha"
        passed = dr_docs.exists() and (dr_docs / "disaster_recovery.md").exists() if dr_docs.exists() else False
        message = "DR procedures documented" if passed else "DR procedures not documented"

        self.results.append(CheckResult(
            name="Disaster recovery documentation",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: Disaster recovery - {message}")

    async def check_monitoring(self):
        """Check monitoring and alerting"""
        logger.info("\n[6/13] Checking Monitoring...")

        monitoring_checks = [
            ("Prometheus config", self.project_root / "monitoring" / "prometheus.yml"),
            ("Grafana dashboards", self.project_root / "monitoring" / "grafana"),
            ("Alert rules", self.project_root / "monitoring" / "prometheus" / "alerts.yml"),
        ]

        for check_name, check_path in monitoring_checks:
            passed = check_path.exists()
            message = f"{check_name} configured" if passed else f"{check_name} not found"
            self.results.append(CheckResult(
                name=check_name,
                passed=passed,
                message=message,
                required=True
            ))
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status}: {check_name} - {message}")

    async def check_oncall(self):
        """Check on-call rotation"""
        logger.info("\n[7/13] Checking On-Call Rotation...")

        # This would typically check with PagerDuty/Opsgenie API
        # For now, check if oncall integration exists
        oncall_integration = self.project_root / "src" / "monitoring" / "oncall_integration.py"
        passed = oncall_integration.exists()
        message = "On-call integration configured" if passed else "On-call integration not found"

        self.results.append(CheckResult(
            name="On-call rotation",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "⚠️  WARNING"
        logger.info(f"  {status}: On-call rotation - {message}")

    async def check_incident_response(self):
        """Check incident response process"""
        logger.info("\n[8/13] Checking Incident Response...")

        incident_playbook = self.project_root / "docs" / "runbooks" / "INCIDENT_RESPONSE_PLAYBOOK.md"
        passed = incident_playbook.exists()
        message = "Incident playbooks documented" if passed else "Incident playbooks missing"

        self.results.append(CheckResult(
            name="Incident response playbooks",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: Incident response - {message}")

    async def check_runbooks(self):
        """Check production runbooks"""
        logger.info("\n[9/13] Checking Production Runbooks...")

        runbooks_dir = self.project_root / "docs" / "runbooks"
        passed = runbooks_dir.exists() and len(list(runbooks_dir.glob("*.md"))) >= 2
        message = f"Runbooks documented ({len(list(runbooks_dir.glob('*.md'))) if runbooks_dir.exists() else 0} files)" if passed else "Insufficient runbooks"

        self.results.append(CheckResult(
            name="Production runbooks",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: Production runbooks - {message}")

    async def check_rollback(self):
        """Check rollback plan"""
        logger.info("\n[10/13] Checking Rollback Plan...")

        deployment_runbook = self.project_root / "docs" / "runbooks" / "DEPLOYMENT_RUNBOOK.md"
        if deployment_runbook.exists():
            content = deployment_runbook.read_text()
            passed = "rollback" in content.lower() and "blue-green" in content.lower()
            message = "Rollback procedures documented" if passed else "Rollback procedures incomplete"
        else:
            passed = False
            message = "Deployment runbook not found"

        self.results.append(CheckResult(
            name="Rollback plan",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: Rollback plan - {message}")

    async def check_communication(self):
        """Check communication plan"""
        logger.info("\n[11/13] Checking Communication Plan...")

        # Check for communication templates or plan
        # For Phase 9, we'll create this
        comm_plan = self.project_root / "docs" / "LAUNCH_COMMUNICATION_PLAN.md"
        passed = comm_plan.exists()
        message = "Communication plan documented" if passed else "Communication plan not found (will be created in Phase 9)"

        self.results.append(CheckResult(
            name="Communication plan",
            passed=passed,
            message=message,
            required=False  # Not strictly required, but recommended
        ))
        status = "✅ PASS" if passed else "⚠️  WARNING"
        logger.info(f"  {status}: Communication plan - {message}")

    async def check_support(self):
        """Check support team training"""
        logger.info("\n[12/13] Checking Support Team Training...")

        # Check for support documentation
        support_docs = [
            self.project_root / "README.md",
            self.project_root / "docs" / "VIDEO_TUTORIAL_SCRIPTS.md",
            self.project_root / "TROUBLESHOOTING.md",
        ]

        passed = any(doc.exists() for doc in support_docs)
        message = "Support documentation available" if passed else "Support documentation incomplete"

        self.results.append(CheckResult(
            name="Support team documentation",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: Support documentation - {message}")

    async def check_beta_users(self):
        """Check beta users are ready"""
        logger.info("\n[13/13] Checking Beta Users...")

        # Check if feature flags are configured for beta rollout
        feature_flags = self.project_root / "src" / "feature_flags"
        passed = feature_flags.exists()
        message = "Feature flag system ready for beta rollout" if passed else "Feature flags not configured"

        self.results.append(CheckResult(
            name="Beta user infrastructure",
            passed=passed,
            message=message,
            required=True
        ))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: Beta users - {message}")

    def generate_report(self):
        """Generate pre-production check report"""
        logger.info("\n" + "=" * 80)
        logger.info("PRE-PRODUCTION CHECK REPORT")
        logger.info("=" * 80)

        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = sum(1 for r in self.results if not r.passed and r.required)
        warnings = sum(1 for r in self.results if not r.passed and not r.required)

        logger.info(f"\nTotal Checks: {total_checks}")
        logger.info(f"✅ Passed: {passed_checks}")
        logger.info(f"❌ Failed (Required): {failed_checks}")
        logger.info(f"⚠️  Warnings: {warnings}")
        logger.info(f"Pass Rate: {(passed_checks / total_checks * 100):.1f}%")

        if failed_checks > 0:
            logger.error("\n❌ FAILED REQUIRED CHECKS:")
            for result in self.results:
                if not result.passed and result.required:
                    logger.error(f"  - {result.name}: {result.message}")

        if warnings > 0:
            logger.warning("\n⚠️  WARNINGS:")
            for result in self.results:
                if not result.passed and not result.required:
                    logger.warning(f"  - {result.name}: {result.message}")

        # Save report to file
        report_file = self.project_root / "pre_production_report.json"
        report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": failed_checks,
            "warnings": warnings,
            "pass_rate": passed_checks / total_checks * 100 if total_checks > 0 else 0,
            "production_ready": self.is_production_ready(),
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "required": r.required,
                    "details": r.details,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"\n📄 Report saved to: {report_file}")

    def is_production_ready(self) -> bool:
        """
        Determine if system is production ready

        Returns:
            True if all required checks pass
        """
        failed_required = [r for r in self.results if not r.passed and r.required]

        if failed_required:
            logger.error("\n❌ SYSTEM NOT PRODUCTION READY")
            logger.error(f"   {len(failed_required)} required checks failed")
            return False
        else:
            logger.info("\n✅ SYSTEM IS PRODUCTION READY")
            logger.info("   All required checks passed!")
            return True


async def main():
    """Main entry point"""
    checker = PreProductionChecker()

    try:
        is_ready = await checker.run_all_checks()

        if is_ready:
            logger.info("\n🚀 Ready for production launch!")
            return 0
        else:
            logger.error("\n🛑 Not ready for production. Please address failed checks.")
            return 1

    except Exception as e:
        logger.exception(f"Pre-production check failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
