"""
Data Loss Prevention (DLP) Controls
Detect and prevent sensitive data exposure
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"  # Personally Identifiable Information
    PHI = "phi"  # Protected Health Information
    PCI = "pci"  # Payment Card Information


@dataclass
class DLPPattern:
    """DLP detection pattern"""
    name: str
    pattern: str
    classification: DataClassification
    severity: str
    action: str  # "block", "warn", "log"


class DLPEngine:
    """Data Loss Prevention engine"""
    
    def __init__(self):
        self.patterns = self._load_dlp_patterns()
        self.policies: Dict[str, List[DLPPattern]] = {}
    
    def _load_dlp_patterns(self) -> List[DLPPattern]:
        """Load DLP detection patterns"""
        return [
            # Credit card numbers
            DLPPattern(
                name="credit_card",
                pattern=r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
                classification=DataClassification.PCI,
                severity="high",
                action="block",
            ),
            # SSN
            DLPPattern(
                name="ssn",
                pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                classification=DataClassification.PII,
                severity="high",
                action="block",
            ),
            # Email addresses (potential PII)
            DLPPattern(
                name="email",
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                classification=DataClassification.PII,
                severity="medium",
                action="warn",
            ),
            # API keys
            DLPPattern(
                name="api_key",
                pattern=r"(?i)(api[_-]?key|apikey|access[_-]?token|secret[_-]?key)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{20,})['\"]?",
                classification=DataClassification.RESTRICTED,
                severity="critical",
                action="block",
            ),
            # AWS keys
            DLPPattern(
                name="aws_key",
                pattern=r"AKIA[0-9A-Z]{16}",
                classification=DataClassification.RESTRICTED,
                severity="critical",
                action="block",
            ),
            # Private keys
            DLPPattern(
                name="private_key",
                pattern=r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                classification=DataClassification.RESTRICTED,
                severity="critical",
                action="block",
            ),
        ]
    
    def scan_content(self, content: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Scan content for sensitive data.
        
        Returns:
            List of detected patterns with metadata
        """
        findings = []
        
        for pattern in self.patterns:
            matches = re.finditer(pattern.pattern, content, re.IGNORECASE)
            for match in matches:
                # Mask sensitive data for logging
                masked_value = self._mask_sensitive_data(match.group(0), pattern.name)
                
                finding = {
                    "pattern_name": pattern.name,
                    "classification": pattern.classification.value,
                    "severity": pattern.severity,
                    "action": pattern.action,
                    "position": match.span(),
                    "matched_text": masked_value,
                    "context": context or {},
                }
                findings.append(finding)
        
        return findings
    
    def _mask_sensitive_data(self, value: str, pattern_name: str) -> str:
        """Mask sensitive data for logging"""
        if pattern_name == "credit_card":
            # Show only last 4 digits
            return f"****-****-****-{value[-4:]}"
        elif pattern_name == "ssn":
            # Show only last 4 digits
            return f"***-**-{value[-4:]}"
        elif pattern_name in ["api_key", "aws_key", "private_key"]:
            # Show only first and last few characters
            if len(value) > 10:
                return f"{value[:4]}...{value[-4:]}"
            return "****"
        else:
            # Partial masking
            if len(value) > 8:
                return f"{value[:2]}...{value[-2:]}"
            return "****"
    
    def should_block(self, findings: List[Dict[str, Any]]) -> bool:
        """Determine if content should be blocked"""
        for finding in findings:
            if finding["action"] == "block":
                return True
        return False
    
    def get_highest_severity(self, findings: List[Dict[str, Any]]) -> Optional[str]:
        """Get highest severity from findings"""
        severities = ["low", "medium", "high", "critical"]
        found_severities = [f["severity"] for f in findings]
        
        for severity in reversed(severities):
            if severity in found_severities:
                return severity
        return None


class DLPManager:
    """DLP management system"""
    
    def __init__(self):
        self.engine = DLPEngine()
        self.scan_history: List[Dict[str, Any]] = []
    
    def scan_data(
        self,
        data: str,
        data_type: str = "text",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Scan data for sensitive information"""
        findings = self.engine.scan_content(data, context)
        
        result = {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "data_type": data_type,
            "findings_count": len(findings),
            "findings": findings,
            "should_block": self.engine.should_block(findings),
            "highest_severity": self.engine.get_highest_severity(findings),
        }
        
        # Log scan
        self.scan_history.append(result)
        
        return result
    
    def scan_file(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Scan file for sensitive data"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            return self.scan_data(content, data_type="file", context={"file_path": file_path})
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return {
                "scan_timestamp": datetime.utcnow().isoformat(),
                "data_type": "file",
                "error": str(e),
                "findings": [],
            }
    
    def enforce_policy(self, findings: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Enforce DLP policy based on findings"""
        if self.engine.should_block(findings):
            return False, "Content blocked due to sensitive data detection"
        
        # Check for warnings
        warnings = [f for f in findings if f["action"] == "warn"]
        if warnings:
            warning_msg = f"Warning: {len(warnings)} sensitive data patterns detected"
            return True, warning_msg
        
        return True, None

