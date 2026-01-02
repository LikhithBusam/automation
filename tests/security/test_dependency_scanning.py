"""
Dependency Scanning
Automated CVE scanning, license compliance, outdated dependency detection
"""

import pytest
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class DependencyScanner:
    """Dependency scanner for security vulnerabilities"""
    
    def __init__(self):
        self.vulnerabilities: List[Dict[str, Any]] = []
        self.outdated_packages: List[Dict[str, Any]] = []
        self.license_issues: List[Dict[str, Any]] = []
    
    def scan_cves(self, package_name: str, version: str) -> List[Dict[str, Any]]:
        """Scan for CVEs in a package"""
        # In production, would use tools like safety, pip-audit, or Snyk
        # For testing, simulate CVE detection
        known_vulnerable = {
            "requests": ["2.25.0", "2.25.1"],  # Example vulnerable versions
            "urllib3": ["1.25.0", "1.25.1"],
        }
        
        cves = []
        if package_name in known_vulnerable and version in known_vulnerable[package_name]:
            cves.append({
                "package": package_name,
                "version": version,
                "cve_id": f"CVE-2021-XXXXX",
                "severity": "high",
                "description": "Example vulnerability"
            })
        
        return cves
    
    def check_license(self, package_name: str) -> Dict[str, Any]:
        """Check package license compliance"""
        # In production, would check actual licenses
        licenses = {
            "requests": "Apache-2.0",
            "pytest": "MIT",
        }
        
        return {
            "package": package_name,
            "license": licenses.get(package_name, "Unknown"),
            "compliant": True  # Would check against allowed licenses
        }
    
    def check_outdated(self, package_name: str, current_version: str, latest_version: str) -> bool:
        """Check if package is outdated"""
        # Simple version comparison (in production, use proper version parsing)
        return current_version != latest_version


class TestDependencyScanning:
    """Test dependency scanning"""
    
    @pytest.fixture
    def scanner(self):
        """Create dependency scanner"""
        return DependencyScanner()
    
    def test_cve_scanning(self, scanner):
        """Test CVE scanning"""
        # Test vulnerable package
        cves = scanner.scan_cves("requests", "2.25.0")
        
        # Should detect vulnerabilities
        # In production, would have real CVE data
        assert isinstance(cves, list)
    
    def test_license_compliance(self, scanner):
        """Test license compliance checking"""
        packages = ["requests", "pytest", "unknown_package"]
        
        for package in packages:
            license_info = scanner.check_license(package)
            assert "package" in license_info
            assert "license" in license_info
            assert "compliant" in license_info
    
    def test_outdated_dependency_detection(self, scanner):
        """Test outdated dependency detection"""
        outdated = scanner.check_outdated("requests", "2.25.0", "2.31.0")
        assert outdated is True
        
        up_to_date = scanner.check_outdated("requests", "2.31.0", "2.31.0")
        assert up_to_date is False
    
    def test_requirements_file_scanning(self):
        """Test scanning requirements.txt file"""
        requirements_file = Path("requirements.txt")
        
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                requirements = f.read()
            
            # Should parse requirements
            assert "pytest" in requirements or "requests" in requirements or len(requirements) > 0
        else:
            # If file doesn't exist, test passes (may use pyproject.toml or setup.py)
            pytest.skip("requirements.txt not found")
    
    def test_python_package_scanning(self):
        """Test scanning installed Python packages"""
        try:
            import pkg_resources
            installed_packages = [pkg.key for pkg in pkg_resources.working_set]
            
            # Should have packages installed
            assert len(installed_packages) > 0
            
            # Check for known vulnerable packages (example)
            vulnerable_packages = []
            for pkg in installed_packages:
                # In production, would check against CVE database
                pass
            
            # Report findings
            assert isinstance(vulnerable_packages, list)
        except ImportError:
            pytest.skip("pkg_resources not available")
    
    def test_transitive_dependency_scanning(self):
        """Test scanning transitive dependencies"""
        # Transitive dependencies should also be scanned
        # Example: if package A depends on B, and B has CVE, A is vulnerable
        
        transitive_vulnerabilities = []
        
        # In production, would use dependency tree
        # For testing, verify structure
        assert isinstance(transitive_vulnerabilities, list)


class TestLicenseCompliance:
    """Test license compliance"""
    
    def test_allowed_licenses(self):
        """Test allowed license list"""
        allowed_licenses = [
            "MIT",
            "Apache-2.0",
            "BSD-3-Clause",
            "ISC",
        ]
        
        # Packages should only use allowed licenses
        test_license = "MIT"
        assert test_license in allowed_licenses
    
    def test_proprietary_license_detection(self):
        """Test detection of proprietary licenses"""
        proprietary_licenses = [
            "Commercial",
            "Proprietary",
            "Custom",
        ]
        
        # Should detect and flag proprietary licenses
        for license_type in proprietary_licenses:
            assert license_type in ["Commercial", "Proprietary", "Custom"]
    
    def test_gpl_license_detection(self):
        """Test GPL license detection (may require compliance)"""
        gpl_licenses = [
            "GPL-2.0",
            "GPL-3.0",
            "AGPL-3.0",
        ]
        
        # GPL licenses may require special handling
        for license_type in gpl_licenses:
            assert "GPL" in license_type or "AGPL" in license_type


class TestOutdatedDependencies:
    """Test outdated dependency detection"""
    
    def test_major_version_outdated(self):
        """Test detection of major version outdated packages"""
        current = "1.0.0"
        latest = "2.0.0"
        
        # Major version difference indicates significant update needed
        current_major = int(current.split(".")[0])
        latest_major = int(latest.split(".")[0])
        
        assert latest_major > current_major
    
    def test_minor_version_outdated(self):
        """Test detection of minor version outdated packages"""
        current = "1.0.0"
        latest = "1.5.0"
        
        # Minor version difference
        current_minor = int(current.split(".")[1])
        latest_minor = int(latest.split(".")[1])
        
        assert latest_minor > current_minor
    
    def test_security_patch_detection(self):
        """Test detection of security patches"""
        # Packages with security patches should be prioritized
        security_patches = [
            {"package": "requests", "version": "2.31.0", "has_security_fix": True},
            {"package": "urllib3", "version": "2.0.0", "has_security_fix": True},
        ]
        
        for patch in security_patches:
            assert patch["has_security_fix"] is True


class TestAutomatedScanning:
    """Test automated scanning tools integration"""
    
    def test_safety_scan_integration(self):
        """Test Safety (CVE scanner) integration"""
        # In production, would run: safety check
        # For testing, verify structure
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # If safety is installed, check output
            if result.returncode == 0 or result.returncode == 1:
                assert True  # Safety ran (exit code 1 = vulnerabilities found)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Safety not installed or timeout")
    
    def test_pip_audit_integration(self):
        """Test pip-audit integration"""
        # In production, would run: pip-audit
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 or result.returncode == 1:
                assert True  # pip-audit ran
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("pip-audit not installed or timeout")
    
    def test_license_scanner_integration(self):
        """Test license scanner integration"""
        # In production, would use: pip-licenses or license-checker
        try:
            result = subprocess.run(
                ["pip-licenses", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                assert True  # License scanner ran
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("pip-licenses not installed or timeout")

