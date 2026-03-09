"""
Tests for Security module
"""

import pytest
from elgringo.core.security import (
    SecurityValidator,
    ThreatLevel,
    ValidationResult,
    get_security_validator,
    validate_tool_call,
)


class TestThreatLevel:
    def test_ordering(self):
        assert ThreatLevel.SAFE.value < ThreatLevel.LOW.value
        assert ThreatLevel.LOW.value < ThreatLevel.MEDIUM.value
        assert ThreatLevel.MEDIUM.value < ThreatLevel.HIGH.value
        assert ThreatLevel.HIGH.value < ThreatLevel.CRITICAL.value


class TestValidationResult:
    def test_basic(self):
        r = ValidationResult(is_valid=True, threat_level=ThreatLevel.SAFE, issues=[])
        assert r.is_valid
        assert r.threat_level == ThreatLevel.SAFE

    def test_with_issues(self):
        r = ValidationResult(is_valid=False, threat_level=ThreatLevel.HIGH, issues=["bad"])
        assert not r.is_valid
        assert len(r.issues) == 1


class TestSecurityValidator:
    @pytest.fixture
    def validator(self):
        return SecurityValidator(strict_mode=True)

    @pytest.fixture
    def lenient_validator(self):
        return SecurityValidator(strict_mode=False)

    # Tool name validation
    def test_valid_tool_name(self, validator):
        result = validator.validate_tool_name("filesystem")
        assert result.is_valid

    def test_invalid_tool_name_format(self, validator):
        result = validator.validate_tool_name("File-System!")
        assert not result.is_valid
        assert result.threat_level == ThreatLevel.MEDIUM

    def test_unknown_tool_name(self, validator):
        result = validator.validate_tool_name("hacking")
        assert not result.is_valid

    def test_all_allowed_tools(self, validator):
        for tool in SecurityValidator.ALLOWED_TOOLS:
            result = validator.validate_tool_name(tool)
            assert result.is_valid, f"Tool {tool} should be allowed"

    # Operation validation
    def test_valid_operation(self, validator):
        result = validator.validate_operation("filesystem", "read")
        assert result.is_valid

    def test_invalid_operation_format(self, validator):
        result = validator.validate_operation("filesystem", "READ-FILE!")
        assert not result.is_valid

    def test_unauthorized_operation(self, validator):
        result = validator.validate_operation("filesystem", "format_disk")
        assert not result.is_valid
        assert result.threat_level == ThreatLevel.HIGH

    def test_all_filesystem_ops(self, validator):
        for op in SecurityValidator.ALLOWED_OPERATIONS["filesystem"]:
            result = validator.validate_operation("filesystem", op)
            assert result.is_valid

    def test_all_shell_ops(self, validator):
        for op in SecurityValidator.ALLOWED_OPERATIONS["shell"]:
            result = validator.validate_operation("shell", op)
            assert result.is_valid

    # Parameter validation
    def test_safe_parameter(self, validator):
        result = validator.validate_parameter_value("path", "/home/user/file.txt", "filesystem", "read")
        assert result.is_valid

    def test_command_injection_semicolon(self, validator):
        result = validator.validate_parameter_value("command", "ls; rm -rf /", "shell", "run")
        assert not result.is_valid

    def test_command_substitution(self, validator):
        result = validator.validate_parameter_value("path", "$(whoami)", "filesystem", "read")
        assert not result.is_valid
        assert result.threat_level == ThreatLevel.CRITICAL

    def test_backtick_injection(self, validator):
        result = validator.validate_parameter_value("path", "`whoami`", "filesystem", "read")
        assert not result.is_valid

    def test_path_traversal(self, validator):
        result = validator.validate_parameter_value("path", "../../../etc/passwd", "filesystem", "read")
        assert not result.is_valid

    def test_sensitive_path_ssh(self, validator):
        result = validator.validate_parameter_value("path", "~/.ssh/id_rsa", "filesystem", "read")
        assert not result.is_valid

    def test_sensitive_path_aws(self, validator):
        result = validator.validate_parameter_value("path", "~/.aws/credentials", "filesystem", "read")
        assert not result.is_valid

    def test_env_file_access(self, validator):
        result = validator.validate_parameter_value("path", ".env", "filesystem", "read")
        # .env is MEDIUM threat, should be valid in strict mode (only HIGH+ blocked)
        assert result.threat_level == ThreatLevel.MEDIUM

    def test_sql_injection(self, validator):
        result = validator.validate_parameter_value("query", "' OR '1'='1", "database", "firestore_query")
        assert result.threat_level.value >= ThreatLevel.HIGH.value

    def test_destructive_sql(self, validator):
        result = validator.validate_parameter_value("query", "; DROP TABLE users", "database", "sqlite_query")
        assert result.threat_level == ThreatLevel.CRITICAL

    def test_eval_in_parameter(self, validator):
        result = validator.validate_parameter_value("code", "eval(input())", "shell", "run")
        assert result.threat_level == ThreatLevel.CRITICAL

    def test_exec_in_parameter(self, validator):
        result = validator.validate_parameter_value("code", "exec(code)", "shell", "run")
        assert result.threat_level.value >= ThreatLevel.HIGH.value

    def test_parameter_too_long(self, validator):
        result = validator.validate_parameter_value("data", "x" * 20000, "filesystem", "write")
        assert not result.is_valid

    def test_dangerous_shell_command_rm_rf(self, validator):
        result = validator.validate_parameter_value("command", "rm -rf /", "shell", "run")
        assert result.threat_level == ThreatLevel.CRITICAL

    def test_dangerous_shell_command_fork_bomb(self, validator):
        result = validator.validate_parameter_value("command", ":(){ :|:& };:", "shell", "run")
        assert result.threat_level == ThreatLevel.CRITICAL

    # Sanitization (lenient mode)
    def test_sanitize_removes_metacharacters(self, lenient_validator):
        result = lenient_validator.validate_parameter_value("cmd", "ls; cat /etc/passwd", "shell", "run")
        # In lenient mode, sanitized value should have metacharacters removed
        assert ";" not in result.sanitized_value

    def test_sanitize_removes_path_traversal(self, lenient_validator):
        result = lenient_validator.validate_parameter_value("path", "../../../secret", "filesystem", "read")
        assert "../" not in result.sanitized_value

    # Full tool call validation
    def test_valid_tool_call(self, validator):
        call = {"tool": "filesystem", "operation": "read", "params": {"path": "/home/user/file.txt"}}
        result = validator.validate_tool_call(call)
        assert result.is_valid

    def test_tool_call_bad_tool(self, validator):
        call = {"tool": "hacking", "operation": "exploit", "params": {}}
        result = validator.validate_tool_call(call)
        assert not result.is_valid

    def test_tool_call_bad_operation(self, validator):
        call = {"tool": "filesystem", "operation": "format", "params": {}}
        result = validator.validate_tool_call(call)
        assert not result.is_valid

    def test_tool_call_dangerous_params(self, validator):
        call = {"tool": "shell", "operation": "run", "params": {"command": "rm -rf /"}}
        result = validator.validate_tool_call(call)
        assert not result.is_valid

    # Security events
    def test_security_events_logged(self, validator):
        validator.validate_parameter_value("cmd", "$(whoami)", "shell", "run")
        events = validator.get_security_events()
        assert len(events) > 0

    def test_security_events_filtered_by_level(self, validator):
        validator.validate_parameter_value("path", ".env", "filesystem", "read")
        validator.validate_parameter_value("cmd", "$(whoami)", "shell", "run")
        high_events = validator.get_security_events(min_level=ThreatLevel.HIGH)
        all_events = validator.get_security_events(min_level=ThreatLevel.LOW)
        assert len(high_events) <= len(all_events)

    def test_clear_security_events(self, validator):
        validator.validate_parameter_value("cmd", "$(whoami)", "shell", "run")
        assert len(validator.get_security_events()) > 0
        validator.clear_security_events()
        assert len(validator.get_security_events()) == 0


class TestGlobalFunctions:
    def test_get_security_validator(self):
        v = get_security_validator()
        assert isinstance(v, SecurityValidator)

    def test_validate_tool_call_convenience(self):
        result = validate_tool_call({
            "tool": "filesystem", "operation": "read",
            "params": {"path": "/tmp/test.txt"}
        })
        assert result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
