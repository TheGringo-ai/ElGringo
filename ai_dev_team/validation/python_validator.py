"""
Python Code Validator
=====================

Validates Python code using:
- AST parsing for syntax checking
- ruff for linting
- Optional mypy for type checking
"""

import ast
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .code_validator import ValidationError, ValidationResult, ValidationWarning

logger = logging.getLogger(__name__)


class PythonValidator:
    """Validator for Python code."""

    def __init__(self):
        self._ruff_available = self._check_ruff_available()

    def _check_ruff_available(self) -> bool:
        """Check if ruff is available."""
        try:
            result = subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def validate(
        self,
        code: str,
        check_syntax: bool = True,
        check_lint: bool = True,
        check_types: bool = False,
        auto_fix: bool = False,
    ) -> ValidationResult:
        """
        Validate Python code.

        Args:
            code: Python code to validate
            check_syntax: Run syntax validation with AST
            check_lint: Run ruff linting
            check_types: Run mypy type checking
            auto_fix: Attempt to auto-fix issues with ruff

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        result = ValidationResult(valid=True, language="python")

        # Syntax check with AST
        if check_syntax:
            syntax_result = self._check_syntax(code)
            result.errors.extend(syntax_result.errors)
            if syntax_result.errors:
                result.validators_run.append("ast")
                # Don't continue if syntax is broken
                return result

        result.validators_run.append("ast")

        # Lint with ruff
        if check_lint and self._ruff_available:
            lint_result = self._check_lint(code, auto_fix=auto_fix)
            result.errors.extend(lint_result.errors)
            result.warnings.extend(lint_result.warnings)
            result.suggestions.extend(lint_result.suggestions)
            result.validators_run.append("ruff")

            if lint_result.fixed_code:
                result.fixed_code = lint_result.fixed_code

        # Type check with mypy (optional)
        if check_types:
            type_result = self._check_types(code)
            result.errors.extend(type_result.errors)
            result.warnings.extend(type_result.warnings)
            result.validators_run.append("mypy")

        # Additional Python-specific checks
        self._check_common_issues(code, result)

        result.valid = len(result.errors) == 0
        return result

    def _check_syntax(self, code: str) -> ValidationResult:
        """Check Python syntax using AST parser."""
        result = ValidationResult(valid=True, language="python")

        try:
            ast.parse(code)
        except SyntaxError as e:
            result.errors.append(ValidationError(
                error_type="syntax",
                message=str(e.msg) if e.msg else "Syntax error",
                line=e.lineno,
                column=e.offset,
                severity="error",
            ))

            # Add suggestion for common syntax errors
            if "unexpected EOF" in str(e):
                result.suggestions.append("Check for missing closing brackets, parentheses, or quotes")
            elif "invalid syntax" in str(e):
                result.suggestions.append("Check for missing colons after if/for/def/class statements")

        return result

    def _check_lint(self, code: str, auto_fix: bool = False) -> ValidationResult:
        """Run ruff linting."""
        result = ValidationResult(valid=True, language="python")

        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run ruff check
                cmd = ["ruff", "check", "--output-format=json", temp_path]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if proc.stdout:
                    import json
                    try:
                        issues = json.loads(proc.stdout)
                        for issue in issues:
                            error_type = "lint"
                            severity = "warning"

                            # Classify severity
                            code = issue.get("code", "")
                            if code.startswith("E9") or code.startswith("F"):
                                severity = "error"

                            msg = issue.get("message", "Unknown lint issue")

                            if severity == "error":
                                result.errors.append(ValidationError(
                                    error_type=error_type,
                                    message=msg,
                                    line=issue.get("location", {}).get("row"),
                                    column=issue.get("location", {}).get("column"),
                                    code=code,
                                    severity=severity,
                                ))
                            else:
                                result.warnings.append(ValidationWarning(
                                    warning_type=error_type,
                                    message=msg,
                                    line=issue.get("location", {}).get("row"),
                                ))
                    except json.JSONDecodeError:
                        pass

                # Try auto-fix if requested
                if auto_fix:
                    fix_cmd = ["ruff", "check", "--fix", temp_path]
                    subprocess.run(fix_cmd, capture_output=True, timeout=30)

                    # Read fixed code
                    with open(temp_path, 'r') as f:
                        fixed_code = f.read()

                    if fixed_code != code:
                        result.fixed_code = fixed_code

            finally:
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logger.warning("ruff timed out")
        except Exception as e:
            logger.warning(f"ruff error: {e}")

        return result

    def _check_types(self, code: str) -> ValidationResult:
        """Run mypy type checking."""
        result = ValidationResult(valid=True, language="python")

        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                cmd = ["mypy", "--ignore-missing-imports", "--no-error-summary", temp_path]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if proc.stdout:
                    for line in proc.stdout.strip().split('\n'):
                        if not line or line.startswith('Found'):
                            continue

                        # Parse mypy output: file:line: severity: message
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            try:
                                line_num = int(parts[1])
                                severity = parts[2].strip()
                                message = parts[3].strip()

                                if 'error' in severity:
                                    result.errors.append(ValidationError(
                                        error_type="type",
                                        message=message,
                                        line=line_num,
                                        severity="error",
                                    ))
                                else:
                                    result.warnings.append(ValidationWarning(
                                        warning_type="type",
                                        message=message,
                                        line=line_num,
                                    ))
                            except ValueError:
                                pass

            finally:
                Path(temp_path).unlink(missing_ok=True)

        except FileNotFoundError:
            logger.debug("mypy not available")
        except subprocess.TimeoutExpired:
            logger.warning("mypy timed out")
        except Exception as e:
            logger.warning(f"mypy error: {e}")

        return result

    def _check_common_issues(self, code: str, result: ValidationResult):
        """Check for common Python issues."""
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for bare except
            if 'except:' in line and 'except Exception' not in line:
                result.warnings.append(ValidationWarning(
                    warning_type="style",
                    message="Bare 'except:' clause catches all exceptions including KeyboardInterrupt",
                    line=i,
                    suggestion="Use 'except Exception:' or a specific exception type",
                ))

            # Check for mutable default arguments
            if 'def ' in line and ('=[]' in line or '={}' in line or '=set()' in line):
                result.warnings.append(ValidationWarning(
                    warning_type="bug",
                    message="Mutable default argument - this can cause unexpected behavior",
                    line=i,
                    suggestion="Use None as default and create the mutable object inside the function",
                ))

            # Check for print statements in production code
            if line.strip().startswith('print(') and 'debug' not in line.lower():
                result.warnings.append(ValidationWarning(
                    warning_type="style",
                    message="print() statement found - consider using logging",
                    line=i,
                ))

        # Check for missing main guard
        if '__name__' not in code and 'def ' in code and 'class ' not in code:
            has_standalone_code = False
            try:
                tree = ast.parse(code)
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant):
                        has_standalone_code = True
                        break
            except Exception:
                logger.debug("Failed to parse code for standalone expression check")

            if has_standalone_code:
                result.suggestions.append(
                    "Consider adding an 'if __name__ == \"__main__\":' guard for scripts"
                )
