#!/usr/bin/env python3
"""
Full Phase 8 Validation Runner

Runs comprehensive validation across all categories matching the Phase 8 checklist.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.validation.validator import ValidationFramework
from tests.validation.validators.agents import register_agent_validators
from tests.validation.validators.workflows import register_workflow_validators
from tests.validation.validators.mcp_tools import register_mcp_tool_validators
from tests.validation.validators.security import register_security_validators
from tests.validation.validators.performance import register_performance_validators
from tests.validation.validators.reliability import register_reliability_validators
from tests.validation.validators.compliance import register_compliance_validators

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Run full validation suite"""
    logger.info("=" * 80)
    logger.info("PHASE 8: VALIDATION AND QUALITY ASSURANCE")
    logger.info("=" * 80)
    logger.info("")

    # Create validation framework
    framework = ValidationFramework()

    # Register all validators
    logger.info("Registering validation checks...")
    register_agent_validators(framework)
    register_workflow_validators(framework)
    register_mcp_tool_validators(framework)
    register_security_validators(framework)
    register_performance_validators(framework)
    register_reliability_validators(framework)
    register_compliance_validators(framework)

    # Run all validations
    logger.info("\nRunning validation suite...\n")
    await framework.run_all()

    # Generate report
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING VALIDATION REPORT")
    logger.info("=" * 80 + "\n")

    # Text report to console
    print(framework.generate_report(format="text"))

    # HTML report to file
    html_report = framework.generate_report(format="html")
    report_file = Path("validation_report.html")
    report_file.write_text(html_report)
    logger.info(f"\nHTML report saved to: {report_file.absolute()}")

    # JSON report to file
    json_report = framework.generate_report(format="json")
    json_file = Path("validation_report.json")
    json_file.write_text(json_report)
    logger.info(f"JSON report saved to: {json_file.absolute()}")

    # Check production readiness
    is_ready = framework.is_production_ready()

    if is_ready:
        logger.info("\n✅ SYSTEM IS PRODUCTION READY!")
        return 0
    else:
        logger.error("\n❌ SYSTEM IS NOT PRODUCTION READY!")
        logger.error("Please review failed checks and address issues before deployment.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
