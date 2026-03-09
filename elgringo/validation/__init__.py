"""
Code Validation Module
======================

Validates AI-generated code before it's returned to users.
Includes syntax checking, linting, type checking, and domain-specific rules.

Usage:
    from elgringo.validation import CodeValidator, get_validator

    validator = get_validator()
    result = validator.validate(code, language="python")

    if not result.valid:
        print("Validation errors:", result.errors)
        print("Suggestions:", result.suggestions)
"""

from .code_validator import (
    CodeValidator,
    ValidationResult,
    ValidationError,
    ValidationWarning,
    get_validator,
)
from .python_validator import PythonValidator
from .typescript_validator import TypeScriptValidator
from .firebase_validator import FirebaseValidator

__all__ = [
    "CodeValidator",
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "get_validator",
    "PythonValidator",
    "TypeScriptValidator",
    "FirebaseValidator",
]
