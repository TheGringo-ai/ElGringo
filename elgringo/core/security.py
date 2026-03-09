"""
Security Module - Input validation and threat prevention
=========================================================

Provides security validation for AI-generated tool calls to prevent:
- Command injection attacks
- Path traversal attacks
- Arbitrary code execution
- Data exfiltration
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels"""
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ValidationResult:
    """Result of security validation"""
    is_valid: bool
    threat_level: ThreatLevel
    issues: List[str]
    sanitized_value: Optional[Any] = None


class SecurityValidator:
    """
    Validates and sanitizes AI-generated inputs before execution.

    Security Principles:
    - Whitelist over blacklist
    - Fail closed (reject if uncertain)
    - Log all security events
    - Defense in depth
    """

    # Allowed tool names (strict whitelist)
    ALLOWED_TOOLS: Set[str] = {
        "filesystem", "shell", "browser", "git",
        "docker", "database", "package", "deploy"
    }

    # Allowed operations per tool
    ALLOWED_OPERATIONS: Dict[str, Set[str]] = {
        "filesystem": {
            "read", "write", "append", "list", "search",
            "exists", "info", "delete", "mkdir", "execute"
        },
        "shell": {
            "run", "run_safe", "background", "env",
            "set_env", "which", "processes", "kill"
        },
        "browser": {
            "fetch", "search", "screenshot", "extract_links"
        },
        "git": {
            "status", "log", "diff", "branch", "checkout",
            "add", "commit", "push", "pull", "fetch",
            "merge", "stash", "init", "clone", "create_pr",
            "rebase", "reset", "cherry_pick", "tag"
        },
        "docker": {
            "build", "pull", "push", "images", "rmi",
            "run", "start", "stop", "restart", "rm",
            "ps", "logs", "exec", "inspect",
            "compose_up", "compose_down", "compose_logs",
            "compose_ps", "compose_build", "prune", "system_df"
        },
        "database": {
            "firestore_get", "firestore_set", "firestore_update",
            "firestore_delete", "firestore_query", "firestore_list",
            "sqlite_query", "sqlite_execute", "sqlite_schema", "sqlite_tables",
            "postgres_query", "postgres_execute", "postgres_schema",
            "design_schema", "generate_migration"
        },
        "package": {
            "npm_install", "npm_uninstall", "npm_list", "npm_run",
            "npm_init", "npm_update", "npm_audit", "npm_outdated",
            "pip_install", "pip_uninstall", "pip_list", "pip_freeze", "pip_show",
            "cargo_build", "cargo_run", "cargo_test", "cargo_add", "cargo_new",
            "brew_install", "brew_uninstall", "brew_list",
            "brew_update", "brew_upgrade", "brew_search",
            "init_project"
        },
        "deploy": {
            "firebase_deploy", "firebase_hosting", "firebase_functions", "firebase_init",
            "gcp_run_deploy", "gcp_build", "gcp_app_deploy", "gcp_functions",
            "vercel_deploy", "vercel_preview",
            "aws_lambda_deploy", "aws_s3_sync", "aws_ecr_push",
            "status", "logs", "rollback"
        }
    }

    # Dangerous patterns in parameter values
    DANGEROUS_PATTERNS: List[Tuple[str, str, ThreatLevel]] = [
        # Command injection
        (r'[;&|`$]', "Shell metacharacter detected", ThreatLevel.HIGH),
        (r'\$\([^)]+\)', "Command substitution detected", ThreatLevel.CRITICAL),
        (r'`[^`]+`', "Backtick command execution detected", ThreatLevel.CRITICAL),

        # Path traversal
        (r'\.\./', "Path traversal attempt", ThreatLevel.HIGH),
        (r'\.\.\\', "Path traversal attempt (Windows)", ThreatLevel.HIGH),

        # Sensitive paths
        (r'/etc/passwd', "Access to passwd file", ThreatLevel.CRITICAL),
        (r'/etc/shadow', "Access to shadow file", ThreatLevel.CRITICAL),
        (r'~/.ssh', "Access to SSH keys", ThreatLevel.CRITICAL),
        (r'~/.aws', "Access to AWS credentials", ThreatLevel.CRITICAL),
        (r'\.env', "Access to environment file", ThreatLevel.MEDIUM),

        # SQL injection (for database operations)
        (r"('|\")\s*(OR|AND)\s*('|\")", "Possible SQL injection", ThreatLevel.HIGH),
        (r';\s*(DROP|DELETE|TRUNCATE)\s+', "Destructive SQL detected", ThreatLevel.CRITICAL),

        # Code injection
        (r'eval\s*\(', "Eval detected", ThreatLevel.CRITICAL),
        (r'exec\s*\(', "Exec detected", ThreatLevel.HIGH),
        (r'__import__', "Dynamic import detected", ThreatLevel.HIGH),
    ]

    # Dangerous shell commands
    DANGEROUS_COMMANDS: Set[str] = {
        "rm -rf /", "rm -rf ~", "rm -rf /*",
        "mkfs", "dd if=/dev/zero", "dd if=/dev/random",
        "chmod -R 777 /", "chmod 777 /",
        "> /dev/sda", "mv / ", "mv /* ",
        ":(){ :|:& };:",  # Fork bomb
        "wget -O- | sh", "curl | sh", "curl | bash",
    }

    # Maximum parameter value length
    MAX_PARAM_LENGTH = 10000

    def __init__(self, strict_mode: bool = True):
        """
        Initialize security validator.

        Args:
            strict_mode: If True, reject any suspicious input.
                        If False, attempt to sanitize.
        """
        self.strict_mode = strict_mode
        self._security_events: List[Dict] = []

    def validate_tool_name(self, tool_name: str) -> ValidationResult:
        """Validate a tool name against whitelist."""
        issues = []

        # Check format (alphanumeric and underscore only)
        if not re.match(r'^[a-z_]+$', tool_name):
            issues.append(f"Invalid tool name format: {tool_name}")
            self._log_security_event("invalid_tool_format", tool_name, ThreatLevel.MEDIUM)
            return ValidationResult(False, ThreatLevel.MEDIUM, issues)

        # Check whitelist
        if tool_name not in self.ALLOWED_TOOLS:
            issues.append(f"Unknown tool: {tool_name}")
            self._log_security_event("unknown_tool", tool_name, ThreatLevel.MEDIUM)
            return ValidationResult(False, ThreatLevel.MEDIUM, issues)

        return ValidationResult(True, ThreatLevel.SAFE, [])

    def validate_operation(self, tool_name: str, operation: str) -> ValidationResult:
        """Validate an operation for a specific tool."""
        issues = []

        # Check format
        if not re.match(r'^[a-z_]+$', operation):
            issues.append(f"Invalid operation format: {operation}")
            self._log_security_event("invalid_operation_format", operation, ThreatLevel.MEDIUM)
            return ValidationResult(False, ThreatLevel.MEDIUM, issues)

        # Check if operation is allowed for this tool
        allowed_ops = self.ALLOWED_OPERATIONS.get(tool_name, set())
        if operation not in allowed_ops:
            issues.append(f"Operation '{operation}' not allowed for tool '{tool_name}'")
            self._log_security_event("unauthorized_operation", f"{tool_name}.{operation}", ThreatLevel.HIGH)
            return ValidationResult(False, ThreatLevel.HIGH, issues)

        return ValidationResult(True, ThreatLevel.SAFE, [])

    def validate_parameter_value(
        self,
        key: str,
        value: Any,
        tool_name: str,
        operation: str
    ) -> ValidationResult:
        """Validate a parameter value for dangerous content."""
        issues = []
        threat_level = ThreatLevel.SAFE

        # Convert to string for pattern matching
        str_value = str(value) if value is not None else ""

        # Check length
        if len(str_value) > self.MAX_PARAM_LENGTH:
            issues.append(f"Parameter '{key}' exceeds maximum length")
            return ValidationResult(False, ThreatLevel.MEDIUM, issues)

        # Check for dangerous patterns
        for pattern, description, level in self.DANGEROUS_PATTERNS:
            if re.search(pattern, str_value, re.IGNORECASE):
                issues.append(f"{description} in parameter '{key}'")
                if level.value > threat_level.value:
                    threat_level = level

                self._log_security_event(
                    "dangerous_pattern",
                    f"{tool_name}.{operation}: {key}={str_value[:100]}",
                    level
                )

        # Special checks for shell commands
        if tool_name == "shell" and key == "command":
            cmd_lower = str_value.lower()
            for dangerous_cmd in self.DANGEROUS_COMMANDS:
                if dangerous_cmd.lower() in cmd_lower:
                    issues.append(f"Dangerous command detected: {dangerous_cmd}")
                    threat_level = ThreatLevel.CRITICAL
                    self._log_security_event("dangerous_command", str_value, ThreatLevel.CRITICAL)

        # Determine if we should reject
        is_valid = threat_level.value < ThreatLevel.HIGH.value or not self.strict_mode

        # Attempt sanitization if not in strict mode
        sanitized = str_value
        if not self.strict_mode and threat_level.value >= ThreatLevel.MEDIUM.value:
            sanitized = self._sanitize_value(str_value)

        return ValidationResult(is_valid, threat_level, issues, sanitized)

    def validate_tool_call(self, call: Dict[str, Any]) -> ValidationResult:
        """
        Validate an entire tool call.

        Args:
            call: Dict with 'tool', 'operation', 'params' keys

        Returns:
            ValidationResult with aggregated issues
        """
        all_issues = []
        max_threat = ThreatLevel.SAFE

        tool_name = call.get("tool", "")
        operation = call.get("operation", "")
        params = call.get("params", {})

        # Validate tool name
        tool_result = self.validate_tool_name(tool_name)
        if not tool_result.is_valid:
            return tool_result

        # Validate operation
        op_result = self.validate_operation(tool_name, operation)
        if not op_result.is_valid:
            return op_result

        # Validate each parameter
        for key, value in params.items():
            param_result = self.validate_parameter_value(key, value, tool_name, operation)
            all_issues.extend(param_result.issues)
            if param_result.threat_level.value > max_threat.value:
                max_threat = param_result.threat_level

        is_valid = max_threat.value < ThreatLevel.HIGH.value or not self.strict_mode

        if not is_valid:
            logger.warning(
                f"SECURITY: Blocked tool call {tool_name}.{operation} - "
                f"Threat level: {max_threat.name}, Issues: {all_issues}"
            )

        return ValidationResult(is_valid, max_threat, all_issues)

    def _sanitize_value(self, value: str) -> str:
        """Attempt to sanitize a potentially dangerous value."""
        sanitized = value

        # Remove shell metacharacters
        sanitized = re.sub(r'[;&|`$]', '', sanitized)

        # Remove path traversal
        sanitized = sanitized.replace('../', '').replace('..\\', '')

        # Escape quotes
        sanitized = sanitized.replace("'", "\\'").replace('"', '\\"')

        return sanitized

    def _log_security_event(self, event_type: str, details: str, level: ThreatLevel):
        """Log a security event."""
        event = {
            "type": event_type,
            "details": details[:500],  # Truncate for safety
            "level": level.name,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }
        self._security_events.append(event)

        if level.value >= ThreatLevel.HIGH.value:
            logger.warning(f"SECURITY EVENT [{level.name}]: {event_type} - {details[:200]}")
        else:
            logger.info(f"Security event [{level.name}]: {event_type}")

    def get_security_events(self, min_level: ThreatLevel = ThreatLevel.LOW) -> List[Dict]:
        """Get logged security events above a threshold."""
        return [
            e for e in self._security_events
            if ThreatLevel[e["level"]].value >= min_level.value
        ]

    def clear_security_events(self):
        """Clear the security event log."""
        self._security_events = []


# Global validator instance
_security_validator: Optional[SecurityValidator] = None


def get_security_validator(strict_mode: bool = True) -> SecurityValidator:
    """Get or create the global security validator."""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator(strict_mode=strict_mode)
    return _security_validator


def validate_tool_call(call: Dict[str, Any]) -> ValidationResult:
    """Convenience function to validate a tool call."""
    return get_security_validator().validate_tool_call(call)
