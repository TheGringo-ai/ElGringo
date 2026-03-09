"""
TypeScript/JavaScript Code Validator
=====================================

Validates TypeScript and JavaScript code using:
- Basic syntax checking with parsing
- ESLint for linting (if available)
- TypeScript compiler for type checking (if available)
"""

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from .code_validator import ValidationError, ValidationResult, ValidationWarning

logger = logging.getLogger(__name__)


class TypeScriptValidator:
    """Validator for TypeScript and JavaScript code."""

    def __init__(self):
        self._eslint_available = self._check_eslint_available()
        self._tsc_available = self._check_tsc_available()

    def _check_eslint_available(self) -> bool:
        """Check if ESLint is available."""
        try:
            result = subprocess.run(
                ["npx", "eslint", "--version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_tsc_available(self) -> bool:
        """Check if TypeScript compiler is available."""
        try:
            result = subprocess.run(
                ["npx", "tsc", "--version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def validate(
        self,
        code: str,
        is_typescript: bool = True,
        check_syntax: bool = True,
        check_lint: bool = True,
        check_types: bool = False,
    ) -> ValidationResult:
        """
        Validate TypeScript or JavaScript code.

        Args:
            code: Code to validate
            is_typescript: True for TypeScript, False for JavaScript
            check_syntax: Run basic syntax validation
            check_lint: Run ESLint linting
            check_types: Run TypeScript compiler type checking

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        language = "typescript" if is_typescript else "javascript"
        result = ValidationResult(valid=True, language=language)

        # Basic syntax check
        if check_syntax:
            syntax_result = self._check_syntax(code, is_typescript)
            result.errors.extend(syntax_result.errors)
            result.warnings.extend(syntax_result.warnings)
            result.validators_run.append("syntax")

            if syntax_result.errors:
                # Don't continue if syntax is broken
                return result

        # ESLint
        if check_lint and self._eslint_available:
            lint_result = self._check_lint(code, is_typescript)
            result.errors.extend(lint_result.errors)
            result.warnings.extend(lint_result.warnings)
            result.suggestions.extend(lint_result.suggestions)
            result.validators_run.append("eslint")

        # TypeScript type checking
        if check_types and is_typescript and self._tsc_available:
            type_result = self._check_types(code)
            result.errors.extend(type_result.errors)
            result.warnings.extend(type_result.warnings)
            result.validators_run.append("tsc")

        # Common JS/TS issues
        self._check_common_issues(code, result, is_typescript)

        result.valid = len(result.errors) == 0
        return result

    def _check_syntax(self, code: str, is_typescript: bool) -> ValidationResult:
        """Basic syntax validation using pattern matching."""
        result = ValidationResult(valid=True, language="typescript" if is_typescript else "javascript")

        lines = code.split('\n')

        # Track brackets/braces/parens
        brackets = {'(': 0, '[': 0, '{': 0}
        closing = {')': '(', ']': '[', '}': '{'}

        in_string = False
        string_char = None
        in_template = False
        in_multiline_comment = False

        for line_num, line in enumerate(lines, 1):
            i = 0
            while i < len(line):
                char = line[i]

                # Handle comments
                if not in_string and not in_template:
                    if i < len(line) - 1:
                        two_char = line[i:i+2]
                        if two_char == '//':
                            break  # Rest of line is comment
                        elif two_char == '/*':
                            in_multiline_comment = True
                            i += 2
                            continue
                        elif two_char == '*/' and in_multiline_comment:
                            in_multiline_comment = False
                            i += 2
                            continue

                if in_multiline_comment:
                    i += 1
                    continue

                # Handle strings
                if char in '"\'`' and not in_string:
                    in_string = True
                    string_char = char
                    if char == '`':
                        in_template = True
                elif char == string_char and in_string:
                    # Check for escape
                    escaped = False
                    j = i - 1
                    while j >= 0 and line[j] == '\\':
                        escaped = not escaped
                        j -= 1
                    if not escaped:
                        in_string = False
                        if char == '`':
                            in_template = False
                        string_char = None

                # Count brackets when not in string
                if not in_string and not in_multiline_comment:
                    if char in brackets:
                        brackets[char] += 1
                    elif char in closing:
                        brackets[closing[char]] -= 1
                        if brackets[closing[char]] < 0:
                            result.errors.append(ValidationError(
                                error_type="syntax",
                                message=f"Unexpected closing bracket '{char}'",
                                line=line_num,
                                column=i + 1,
                                severity="error",
                            ))
                            brackets[closing[char]] = 0

                i += 1

        # Check for unclosed brackets
        for bracket, count in brackets.items():
            if count > 0:
                result.errors.append(ValidationError(
                    error_type="syntax",
                    message=f"Unclosed bracket '{bracket}' ({count} unclosed)",
                    severity="error",
                ))

        # Check for unclosed string
        if in_string:
            result.errors.append(ValidationError(
                error_type="syntax",
                message="Unclosed string literal",
                severity="error",
            ))

        return result

    def _check_lint(self, code: str, is_typescript: bool) -> ValidationResult:
        """Run ESLint on the code."""
        result = ValidationResult(valid=True, language="typescript" if is_typescript else "javascript")

        try:
            ext = '.ts' if is_typescript else '.js'
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=ext,
                delete=False,
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                cmd = [
                    "npx", "eslint",
                    "--format=json",
                    "--no-eslintrc",
                    "--env", "es2021",
                    "--env", "node",
                    "--parser-options", "ecmaVersion:2021",
                    temp_path
                ]

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if proc.stdout:
                    try:
                        lint_results = json.loads(proc.stdout)
                        for file_result in lint_results:
                            for msg in file_result.get('messages', []):
                                severity = msg.get('severity', 1)
                                message = msg.get('message', 'Unknown issue')
                                rule = msg.get('ruleId', '')

                                if severity >= 2:  # Error
                                    result.errors.append(ValidationError(
                                        error_type="lint",
                                        message=message,
                                        line=msg.get('line'),
                                        column=msg.get('column'),
                                        code=rule,
                                        severity="error",
                                    ))
                                else:  # Warning
                                    result.warnings.append(ValidationWarning(
                                        warning_type="lint",
                                        message=message,
                                        line=msg.get('line'),
                                    ))
                    except json.JSONDecodeError:
                        pass

            finally:
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logger.warning("ESLint timed out")
        except Exception as e:
            logger.debug(f"ESLint not available: {e}")

        return result

    def _check_types(self, code: str) -> ValidationResult:
        """Run TypeScript compiler for type checking."""
        result = ValidationResult(valid=True, language="typescript")

        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.ts',
                delete=False,
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                cmd = [
                    "npx", "tsc",
                    "--noEmit",
                    "--strict",
                    "--skipLibCheck",
                    "--moduleResolution", "node",
                    temp_path
                ]

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if proc.stdout:
                    for line in proc.stdout.strip().split('\n'):
                        if not line:
                            continue

                        # Parse tsc output: file(line,col): error TSxxxx: message
                        match = re.match(r'.*\((\d+),(\d+)\):\s*(error|warning)\s*(TS\d+):\s*(.+)', line)
                        if match:
                            line_num = int(match.group(1))
                            col = int(match.group(2))
                            severity = match.group(3)
                            error_code = match.group(4)
                            message = match.group(5)

                            if severity == 'error':
                                result.errors.append(ValidationError(
                                    error_type="type",
                                    message=message,
                                    line=line_num,
                                    column=col,
                                    code=error_code,
                                    severity="error",
                                ))
                            else:
                                result.warnings.append(ValidationWarning(
                                    warning_type="type",
                                    message=message,
                                    line=line_num,
                                ))

            finally:
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logger.warning("tsc timed out")
        except Exception as e:
            logger.debug(f"TypeScript compiler not available: {e}")

        return result

    def _check_common_issues(self, code: str, result: ValidationResult, is_typescript: bool):
        """Check for common JavaScript/TypeScript issues."""
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for var usage
            if re.match(r'\bvar\s+\w+', stripped):
                result.warnings.append(ValidationWarning(
                    warning_type="style",
                    message="Use 'const' or 'let' instead of 'var'",
                    line=i,
                    suggestion="Replace 'var' with 'const' for values that don't change, or 'let' for values that do",
                ))

            # Check for == instead of ===
            if '==' in line and '===' not in line and '!==' not in line:
                if not re.search(r'[\'"].*==.*[\'"]', line):  # Not in a string
                    result.warnings.append(ValidationWarning(
                        warning_type="style",
                        message="Use '===' instead of '==' for strict equality",
                        line=i,
                    ))

            # Check for console.log in production code
            if 'console.log(' in stripped or 'console.error(' in stripped:
                result.warnings.append(ValidationWarning(
                    warning_type="style",
                    message="console.log/error found - consider removing for production",
                    line=i,
                ))

            # Check for any type in TypeScript
            if is_typescript and ': any' in line:
                result.warnings.append(ValidationWarning(
                    warning_type="type",
                    message="'any' type used - consider using a more specific type",
                    line=i,
                    suggestion="Use a proper type annotation or 'unknown' if the type is truly unknown",
                ))

        # Check for missing async/await patterns
        if 'Promise' in code or '.then(' in code:
            if 'async ' not in code and 'await ' not in code:
                result.suggestions.append(
                    "Consider using async/await syntax instead of .then() for cleaner code"
                )

        # Check for potential memory leaks in React
        if 'useEffect' in code:
            if 'return' not in code or ('setInterval' in code or 'addEventListener' in code):
                if 'clearInterval' not in code and 'removeEventListener' not in code:
                    result.warnings.append(ValidationWarning(
                        warning_type="bug",
                        message="useEffect with setInterval/addEventListener may need cleanup",
                        suggestion="Return a cleanup function from useEffect to prevent memory leaks",
                    ))
