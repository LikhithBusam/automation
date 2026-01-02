"""
Phase 8: Validation and Quality Assurance Framework

Comprehensive validation system for all features and acceptance criteria.
"""

from .validator import ValidationFramework, ValidationResult
from .acceptance_criteria import AcceptanceCriteriaValidator

__all__ = [
    "ValidationFramework",
    "ValidationResult",
    "AcceptanceCriteriaValidator",
]
