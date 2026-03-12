"""
Auto-Failure Detector — Catch AI mistakes before users do
==========================================================

Automatically detects failures in AI-generated responses:
1. Syntax errors in generated code
2. Security vulnerabilities
3. Incomplete/placeholder code
4. Import errors and hallucinations

Feeds failures back into the learning loop for automatic improvement.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class FailureCategory(Enum):
    SYNTAX_ERROR = "syntax_error"
    TEST_FAILURE = "test_failure"
    BUILD_FAILURE = "build_failure"
    SECURITY_ISSUE = "security_issue"
    INCOMPLETE_CODE = "incomplete_code"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"
    HALLUCINATION = "hallucination"


@dataclass
class DetectedFailure:
    category: FailureCategory
    severity: str  # "critical", "warning", "info"
    description: str
    code_snippet: str = ""
    line_number: Optional[int] = None
    fix_suggestion: str = ""
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity,
            "description": self.description,
            "line_number": self.line_number,
            "fix_suggestion": self.fix_suggestion,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class DetectionResult:
    task_id: str
    passed: bool
    failures: List[DetectedFailure] = field(default_factory=list)
    code_blocks_checked: int = 0
    tests_run: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "passed": self.passed,
            "failures_found": len(self.failures),
            "code_blocks_checked": self.code_blocks_checked,
            "critical_failures": sum(1 for f in self.failures if f.severity == "critical"),
            "warnings": sum(1 for f in self.failures if f.severity == "warning"),
            "failures": [f.to_dict() for f in self.failures[:10]],
        }


class AutoFailureDetector:
    """
    Automatically detects failures in AI-generated code and responses.

    Runs checks on every collaboration result:
    1. Syntax validation for all code blocks
    2. Import verification
    3. Security pattern scanning
    4. Completeness checking
    """

    SECURITY_PATTERNS = [
        (r'eval\s*\(', "Use of eval() is a security risk", "critical"),
        (r'exec\s*\(', "Use of exec() is a security risk", "critical"),
        (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell injection risk with shell=True", "critical"),
        (r'os\.system\s*\(', "Use subprocess.run instead of os.system", "warning"),
        (r'pickle\.loads?\s*\(', "Pickle deserialization can execute arbitrary code", "warning"),
        (r'yaml\.load\s*\([^)]*\)(?!.*Loader)', "Use yaml.safe_load instead of yaml.load", "warning"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected", "critical"),
        (r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}["\']', "Hardcoded API key detected", "critical"),
        (r'SELECT\s+.*\+\s*(?:request|input|user)', "Potential SQL injection", "critical"),
        (r'innerHTML\s*=\s*(?:.*\+|.*\$\{)', "Potential XSS vulnerability", "critical"),
    ]

    PLACEHOLDER_PATTERNS = [
        (r'TODO\b', "Contains TODO placeholder"),
        (r'FIXME\b', "Contains FIXME placeholder"),
        (r'\.\.\.(?!\s*\))', "Contains ellipsis placeholder (...)"),
        (r'pass\s*#\s*(?:implement|todo|fix)', "Contains pass with TODO comment"),
        (r'raise\s+NotImplementedError', "Contains NotImplementedError"),
    ]

    def check(self, content: str, task_id: str = "", task_type: str = "general", language: Optional[str] = None) -> DetectionResult:
        result = DetectionResult(task_id=task_id, passed=True)
        code_blocks = self._extract_code_blocks(content)
        result.code_blocks_checked = len(code_blocks)

        for lang, code in code_blocks:
            effective_lang = language or lang or self._detect_language(code)
            result.failures.extend(self._check_syntax(code, effective_lang))
            result.failures.extend(self._check_imports(code, effective_lang))
            result.failures.extend(self._check_security(code))
            result.failures.extend(self._check_completeness(code))

        result.failures.extend(self._check_response_quality(content, task_type))
        result.passed = not any(f.severity == "critical" for f in result.failures)
        return result

    async def check_and_report(
        self, content: str, task_id: str, task_type: str,
        agents: List[str],
        feedback_fn: Optional[Callable[..., Coroutine]] = None,
    ) -> DetectionResult:
        result = self.check(content, task_id, task_type)
        if not result.passed and feedback_fn:
            critical = [f for f in result.failures if f.severity == "critical"]
            if critical:
                error_summary = "; ".join(f.description for f in critical[:3])
                try:
                    await feedback_fn(
                        task_id=task_id, error=f"Auto-detected: {error_summary}",
                        agents=agents, task_type=task_type,
                    )
                except Exception as e:
                    logger.debug(f"Failed to auto-report: {e}")
        return result

    def _extract_code_blocks(self, content):
        return [(lang.lower(), code.strip())
                for lang, code in re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
                if code.strip()]

    def _detect_language(self, code):
        if re.search(r'\bdef\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import', code):
            return "python"
        if re.search(r'\bfunction\s+\w+|const\s+\w+\s*=|=>\s*\{', code):
            return "javascript"
        if re.search(r'\bfunc\s+\w+|package\s+\w+', code):
            return "go"
        return "unknown"

    def _check_syntax(self, code, language):
        failures = []
        if language == "python":
            try:
                compile(code, '<ai-generated>', 'exec')
            except SyntaxError as e:
                failures.append(DetectedFailure(
                    category=FailureCategory.SYNTAX_ERROR, severity="critical",
                    description=f"Python syntax error: {e.msg}",
                    line_number=e.lineno,
                    fix_suggestion=f"Fix syntax at line {e.lineno}: {e.msg}",
                ))
        elif language in ("javascript", "typescript"):
            for open_c, close_c, name in [('{', '}', 'curly braces'), ('(', ')', 'parentheses'), ('[', ']', 'square brackets')]:
                if code.count(open_c) != code.count(close_c):
                    failures.append(DetectedFailure(
                        category=FailureCategory.SYNTAX_ERROR, severity="critical",
                        description=f"Unbalanced {name}: {code.count(open_c)} open, {code.count(close_c)} close",
                    ))
        return failures

    def _check_imports(self, code, language):
        failures = []
        if language == "python":
            misspellings = {"reqeusts": "requests", "flaks": "flask", "numppy": "numpy", "pnadas": "pandas"}
            for wrong, right in misspellings.items():
                if f"import {wrong}" in code or f"from {wrong}" in code:
                    failures.append(DetectedFailure(
                        category=FailureCategory.IMPORT_ERROR, severity="critical",
                        description=f"Misspelled import: '{wrong}' should be '{right}'",
                        fix_suggestion=f"Replace '{wrong}' with '{right}'",
                        auto_fixable=True,
                    ))
        return failures

    def _check_security(self, code):
        failures = []
        for pattern, description, severity in self.SECURITY_PATTERNS:
            if re.search(pattern, code, re.I):
                failures.append(DetectedFailure(
                    category=FailureCategory.SECURITY_ISSUE, severity=severity,
                    description=description,
                    fix_suggestion=f"Review and fix: {description}",
                ))
        return failures

    def _check_completeness(self, code):
        failures = []
        for pattern, description in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, code, re.I):
                failures.append(DetectedFailure(
                    category=FailureCategory.INCOMPLETE_CODE, severity="warning",
                    description=description,
                    fix_suggestion="Complete the implementation",
                ))
        return failures

    def _check_response_quality(self, content, task_type):
        failures = []
        if task_type in ("coding", "debugging") and '```' not in content and len(content) > 100:
            failures.append(DetectedFailure(
                category=FailureCategory.INCOMPLETE_CODE, severity="warning",
                description="Coding task but no code block in response",
            ))
        return failures


_detector: Optional[AutoFailureDetector] = None

def get_failure_detector() -> AutoFailureDetector:
    global _detector
    if _detector is None:
        _detector = AutoFailureDetector()
    return _detector
