"""
Main Code Validator
===================

Unified code validation for AI-generated code.
Coordinates language-specific validators and provides consistent results.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """A validation error."""
    error_type: str  # syntax, lint, type, security, etc.
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    code: Optional[str] = None  # Error code (e.g., E501, W503)
    severity: str = "error"  # error, warning, info

    def __str__(self) -> str:
        location = f" (line {self.line})" if self.line else ""
        code_str = f" [{self.code}]" if self.code else ""
        return f"{self.error_type}{code_str}: {self.message}{location}"


@dataclass
class ValidationWarning:
    """A validation warning (non-blocking)."""
    warning_type: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        location = f" (line {self.line})" if self.line else ""
        return f"{self.warning_type}: {self.message}{location}"


@dataclass
class ValidationResult:
    """Result of code validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    fixed_code: Optional[str] = None  # Auto-fixed version if available
    language: str = "unknown"
    validators_run: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        if self.valid and not self.warnings:
            return "Code validation passed."

        parts = []

        if self.errors:
            parts.append(f"{len(self.errors)} error(s):")
            for err in self.errors[:5]:  # Limit to first 5
                parts.append(f"  - {err}")

        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s):")
            for warn in self.warnings[:5]:
                parts.append(f"  - {warn}")

        if self.suggestions:
            parts.append("Suggestions:")
            for sug in self.suggestions[:3]:
                parts.append(f"  - {sug}")

        return "\n".join(parts)


class CodeValidator:
    """
    Unified code validation for AI-generated code.

    Supports multiple languages and validation types:
    - Syntax validation (AST parsing)
    - Linting (ruff for Python, ESLint for JS/TS)
    - Type checking (mypy for Python, tsc for TS)
    - Security patterns
    - Domain-specific rules (Firebase, etc.)
    """

    def __init__(self):
        from .python_validator import PythonValidator
        from .typescript_validator import TypeScriptValidator
        from .firebase_validator import FirebaseValidator

        self._python_validator = PythonValidator()
        self._typescript_validator = TypeScriptValidator()
        self._firebase_validator = FirebaseValidator()

        # Language detection patterns
        self._language_patterns = {
            "python": [
                r'^\s*import\s+\w+',
                r'^\s*from\s+\w+\s+import',
                r'^\s*def\s+\w+\s*\(',
                r'^\s*class\s+\w+',
                r':\s*$',
                r'^\s*@\w+',
            ],
            "typescript": [
                r'^\s*import\s+.*\s+from\s+[\'"]',
                r'^\s*export\s+(default\s+)?(function|class|const|interface|type)',
                r':\s*(string|number|boolean|any|void)\s*[;=\)]',
                r'<\w+>',
                r'interface\s+\w+',
                r'type\s+\w+\s*=',
            ],
            "javascript": [
                r'^\s*import\s+.*\s+from\s+[\'"]',
                r'^\s*export\s+(default\s+)?(function|class|const)',
                r'^\s*const\s+\w+\s*=',
                r'^\s*let\s+\w+\s*=',
                r'function\s+\w+\s*\(',
                r'=>',
            ],
        }

    def detect_language(self, code: str) -> str:
        """Detect the programming language of the code."""
        scores = {"python": 0, "typescript": 0, "javascript": 0}

        for lang, patterns in self._language_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, code, re.MULTILINE)
                scores[lang] += len(matches)

        # TypeScript is a superset of JavaScript
        if scores["typescript"] > scores["javascript"]:
            return "typescript"
        elif scores["javascript"] > 0:
            return "javascript"
        elif scores["python"] > 0:
            return "python"

        return "unknown"

    def validate(
        self,
        code: str,
        language: str = None,
        context: str = None,
        check_syntax: bool = True,
        check_lint: bool = True,
        check_types: bool = False,  # Disabled by default (slower)
        check_security: bool = True,
        check_domain: bool = True,
    ) -> ValidationResult:
        """
        Validate code with specified checks.

        Args:
            code: The code to validate
            language: Programming language (auto-detected if None)
            context: Optional context about what the code does
            check_syntax: Run syntax validation
            check_lint: Run linting
            check_types: Run type checking (slower)
            check_security: Check for security issues
            check_domain: Run domain-specific checks (Firebase, etc.)

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        if not code or not code.strip():
            return ValidationResult(valid=True, language="unknown")

        # Detect language if not specified
        if not language:
            language = self.detect_language(code)

        result = ValidationResult(valid=True, language=language)

        # Run appropriate validators
        if language == "python":
            self._validate_python(code, result, check_syntax, check_lint, check_types)
        elif language in ["typescript", "javascript"]:
            self._validate_typescript(code, result, language, check_syntax, check_lint, check_types)

        # Run domain-specific validators
        if check_domain:
            self._validate_domain(code, result, context)

        # Run security checks
        if check_security:
            self._validate_security(code, result, language)

        # Update valid flag
        result.valid = len(result.errors) == 0

        return result

    def _validate_python(
        self,
        code: str,
        result: ValidationResult,
        check_syntax: bool,
        check_lint: bool,
        check_types: bool,
    ):
        """Run Python validators."""
        py_result = self._python_validator.validate(
            code,
            check_syntax=check_syntax,
            check_lint=check_lint,
            check_types=check_types,
        )

        result.errors.extend(py_result.errors)
        result.warnings.extend(py_result.warnings)
        result.suggestions.extend(py_result.suggestions)
        result.validators_run.extend(py_result.validators_run)

        if py_result.fixed_code:
            result.fixed_code = py_result.fixed_code

    def _validate_typescript(
        self,
        code: str,
        result: ValidationResult,
        language: str,
        check_syntax: bool,
        check_lint: bool,
        check_types: bool,
    ):
        """Run TypeScript/JavaScript validators."""
        ts_result = self._typescript_validator.validate(
            code,
            is_typescript=(language == "typescript"),
            check_syntax=check_syntax,
            check_lint=check_lint,
            check_types=check_types,
        )

        result.errors.extend(ts_result.errors)
        result.warnings.extend(ts_result.warnings)
        result.suggestions.extend(ts_result.suggestions)
        result.validators_run.extend(ts_result.validators_run)

    def _validate_domain(self, code: str, result: ValidationResult, context: str):
        """Run domain-specific validators."""
        # Check for Firebase patterns
        firebase_keywords = ['firebase', 'firestore', 'auth.', 'storage.bucket', 'cloud.firestore']
        if any(kw in code.lower() for kw in firebase_keywords):
            fb_result = self._firebase_validator.validate(code, context)
            result.warnings.extend(fb_result.warnings)
            result.suggestions.extend(fb_result.suggestions)
            result.validators_run.append("firebase")

    def _validate_security(self, code: str, result: ValidationResult, language: str):
        """Check for common security issues."""
        security_patterns = [
            # Hardcoded secrets
            (r'(api[_-]?key|secret|password|token)\s*=\s*["\'][^"\']+["\']',
             "Potential hardcoded secret detected",
             "Use environment variables for sensitive values"),

            # SQL injection risks
            (r'f["\'].*SELECT.*\{',
             "Potential SQL injection risk with f-string",
             "Use parameterized queries instead of string formatting"),

            # Eval usage
            (r'\beval\s*\(',
             "Use of eval() is a security risk",
             "Avoid eval() - use safer alternatives like ast.literal_eval() or JSON parsing"),

            # Exec usage
            (r'\bexec\s*\(',
             "Use of exec() is a security risk",
             "Avoid exec() - consider safer alternatives"),
        ]

        for pattern, message, suggestion in security_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                result.warnings.append(ValidationWarning(
                    warning_type="security",
                    message=message,
                    suggestion=suggestion,
                ))

        if result.warnings:
            result.validators_run.append("security")

    def validate_and_fix(
        self,
        code: str,
        language: str = None,
        context: str = None,
    ) -> ValidationResult:
        """
        Validate code and attempt to auto-fix issues.

        Returns ValidationResult with fixed_code if fixes were applied.
        """
        result = self.validate(code, language, context)

        if result.errors and result.language == "python":
            # Try to get auto-fixed version
            fixed_result = self._python_validator.validate(code, auto_fix=True)
            if fixed_result.fixed_code and fixed_result.fixed_code != code:
                result.fixed_code = fixed_result.fixed_code
                result.suggestions.append("Auto-fix applied. Review the changes.")

        return result

    def extract_code_blocks(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract code blocks from markdown-formatted text.

        Returns list of (language, code) tuples.
        """
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        result = []
        for lang, code in matches:
            if not lang:
                lang = self.detect_language(code)
            result.append((lang, code.strip()))

        return result

    def validate_response(self, response_text: str) -> List[ValidationResult]:
        """
        Validate all code blocks in an AI response.

        Returns list of ValidationResults, one per code block.
        """
        code_blocks = self.extract_code_blocks(response_text)
        results = []

        for language, code in code_blocks:
            result = self.validate(code, language)
            results.append(result)

        return results


# Global instance
_validator_instance: Optional[CodeValidator] = None


def get_validator() -> CodeValidator:
    """Get or create the global validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = CodeValidator()
    return _validator_instance
