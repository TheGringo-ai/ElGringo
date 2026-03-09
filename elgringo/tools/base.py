"""
Base Tool System - Security-first tool framework
================================================

All tools inherit from this base class and use the permission system.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for tool operations"""
    DENY = 0        # Never allowed
    ASK = 1         # Ask user each time
    SESSION = 2     # Allow for this session
    ALWAYS = 3      # Always allow (persistent)


class OperationRisk(Enum):
    """Risk level for operations"""
    SAFE = 0        # Read-only, no side effects
    LOW = 1         # Minor modifications (logs, temp files)
    MEDIUM = 2      # File modifications, network calls
    HIGH = 3        # System changes, deletions
    CRITICAL = 4    # Destructive operations, credentials access


@dataclass
class ToolPermission:
    """Permission configuration for a tool operation"""
    tool_name: str
    operation: str
    level: PermissionLevel = PermissionLevel.ASK
    allowed_paths: List[str] = field(default_factory=list)  # For file operations
    allowed_domains: List[str] = field(default_factory=list)  # For web operations
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None


@dataclass
class ToolError:
    """Detailed error information for tool operations"""
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = True
    suggested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action,
        }


@dataclass
class ToolResult:
    """Result from a tool operation"""
    success: bool
    output: Any
    error: Optional[str] = None
    error_detail: Optional[ToolError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    permission_used: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, warning: str):
        """Add a non-fatal warning"""
        self.warnings.append(warning)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class PermissionManager:
    """
    Manages permissions for tool operations.

    Security model:
    - Default deny for dangerous operations
    - User must explicitly grant permissions
    - Permissions can be session or persistent
    - Sandboxed paths prevent access to sensitive areas
    """

    # Paths that are NEVER accessible
    FORBIDDEN_PATHS = [
        "/etc/passwd", "/etc/shadow",
        "~/.ssh", "~/.gnupg", "~/.aws/credentials",
        "/System", "/Library", "/bin", "/sbin", "/usr/bin",
    ]

    # Default safe paths for file operations
    DEFAULT_SAFE_PATHS = [
        "~/Development", "~/Projects", "~/Documents",
        "/tmp", "~/.ai-dev-team",
    ]

    def __init__(self, config_path: str = "~/.ai-dev-team/permissions.json"):
        self.config_path = Path(config_path).expanduser()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._permissions: Dict[str, ToolPermission] = {}
        self._session_grants: Set[str] = set()
        self._pending_requests: List[Dict] = []
        self._load_errors: List[str] = []

        self._load_permissions()

    def get_load_errors(self) -> List[str]:
        """Get any errors that occurred during permission loading"""
        return self._load_errors

    def _load_permissions(self):
        """Load persistent permissions from disk"""
        import json
        self._load_errors: List[str] = []

        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    for key, perm_data in data.items():
                        try:
                            perm_data["level"] = PermissionLevel(perm_data["level"])
                            self._permissions[key] = ToolPermission(**perm_data)
                        except (KeyError, ValueError) as e:
                            error_msg = f"Invalid permission entry '{key}': {e}"
                            self._load_errors.append(error_msg)
                            logger.warning(error_msg)
            except json.JSONDecodeError as e:
                error_msg = f"Corrupted permissions file: {e}"
                self._load_errors.append(error_msg)
                logger.error(error_msg)
                # Create backup and reset
                backup_path = self.config_path.with_suffix('.json.bak')
                try:
                    self.config_path.rename(backup_path)
                    logger.info(f"Backed up corrupted file to {backup_path}")
                except Exception:
                    pass
            except PermissionError as e:
                error_msg = f"Cannot read permissions file: {e}"
                self._load_errors.append(error_msg)
                logger.error(error_msg)
            except Exception as e:
                error_msg = f"Failed to load permissions: {e}"
                self._load_errors.append(error_msg)
                logger.warning(error_msg)

        if self._load_errors:
            logger.warning(f"Permission loading had {len(self._load_errors)} error(s)")

    def _save_permissions(self):
        """Save persistent permissions to disk"""
        import json
        persistent = {
            k: {**v.__dict__, "level": v.level.value}
            for k, v in self._permissions.items()
            if v.level == PermissionLevel.ALWAYS
        }
        try:
            with open(self.config_path, "w") as f:
                json.dump(persistent, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save permissions: {e}")

    def _make_key(self, tool_name: str, operation: str) -> str:
        """Create permission key"""
        return f"{tool_name}:{operation}"

    def is_path_forbidden(self, path: str) -> bool:
        """Check if path is in forbidden list"""
        path = str(Path(path).expanduser().resolve())
        for forbidden in self.FORBIDDEN_PATHS:
            forbidden_resolved = str(Path(forbidden).expanduser().resolve())
            if path.startswith(forbidden_resolved):
                return True
        return False

    def is_path_safe(self, path: str) -> bool:
        """Check if path is in safe list"""
        path = str(Path(path).expanduser().resolve())
        for safe in self.DEFAULT_SAFE_PATHS:
            safe_resolved = str(Path(safe).expanduser().resolve())
            if path.startswith(safe_resolved):
                return True
        return False

    def check_permission(
        self,
        tool_name: str,
        operation: str,
        context: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """
        Check if an operation is permitted.

        Returns:
            (allowed, reason)
        """
        key = self._make_key(tool_name, operation)

        # Check forbidden paths for file operations
        if context and "path" in context:
            path = context["path"]
            if self.is_path_forbidden(path):
                return False, f"Access to {path} is forbidden for security"

        # Check session grants
        if key in self._session_grants:
            return True, "Granted for this session"

        # Check persistent permissions
        if key in self._permissions:
            perm = self._permissions[key]
            if perm.level == PermissionLevel.ALWAYS:
                return True, "Persistent permission granted"
            elif perm.level == PermissionLevel.DENY:
                return False, "Permission denied by user"

        # Check if path is in safe zone (auto-allow for safe paths)
        if context and "path" in context:
            if self.is_path_safe(context["path"]):
                return True, "Path is in safe zone"

        # Default: need to ask
        return False, "Permission required"

    def grant_permission(
        self,
        tool_name: str,
        operation: str,
        level: PermissionLevel = PermissionLevel.SESSION,
        allowed_paths: Optional[List[str]] = None,
    ):
        """Grant permission for an operation"""
        key = self._make_key(tool_name, operation)

        if level == PermissionLevel.SESSION:
            self._session_grants.add(key)
        else:
            self._permissions[key] = ToolPermission(
                tool_name=tool_name,
                operation=operation,
                level=level,
                allowed_paths=allowed_paths or [],
                granted_at=datetime.now(timezone.utc).isoformat(),
            )
            if level == PermissionLevel.ALWAYS:
                self._save_permissions()

        logger.info(f"Permission granted: {key} ({level.name})")

    def revoke_permission(self, tool_name: str, operation: str):
        """Revoke permission for an operation"""
        key = self._make_key(tool_name, operation)
        self._session_grants.discard(key)
        if key in self._permissions:
            del self._permissions[key]
            self._save_permissions()
        logger.info(f"Permission revoked: {key}")

    def get_all_permissions(self) -> List[ToolPermission]:
        """Get all granted permissions"""
        return list(self._permissions.values())

    def clear_session(self):
        """Clear all session grants"""
        self._session_grants.clear()

    # =================
    # Audit System
    # =================

    _audit_log: List[Dict[str, Any]] = []

    def _audit(self, action: str, tool: str, operation: str, result: str, details: Optional[Dict] = None):
        """Log an audit event"""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "tool": tool,
            "operation": operation,
            "result": result,
            "details": details or {},
        }
        self._audit_log.append(event)
        # Keep only last 1000 events
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

        # Log security-relevant events
        if result in ("DENIED", "BLOCKED"):
            logger.warning(f"AUDIT [{action}]: {tool}.{operation} - {result}")
        else:
            logger.debug(f"AUDIT [{action}]: {tool}.{operation} - {result}")

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit events"""
        return self._audit_log[-limit:]

    def get_denied_operations(self) -> List[Dict[str, Any]]:
        """Get all denied operations from audit log"""
        return [e for e in self._audit_log if e["result"] in ("DENIED", "BLOCKED")]

    # =================
    # Risk Assessment
    # =================

    # Operations that are considered high/critical risk
    HIGH_RISK_OPERATIONS = {
        "shell": {"run", "background", "kill"},
        "filesystem": {"write", "delete", "execute", "mkdir"},
        "docker": {"build", "run", "exec", "rm", "rmi", "prune"},
        "database": {"sqlite_execute", "postgres_execute", "firestore_delete"},
        "deploy": {"firebase_deploy", "gcp_run_deploy", "vercel_deploy", "aws_lambda_deploy"},
        "git": {"push", "reset", "rebase", "cherry_pick"},
        "package": {"npm_install", "pip_install", "cargo_add", "brew_install"},
    }

    CRITICAL_OPERATIONS = {
        "shell": {"run"},  # Arbitrary command execution
        "filesystem": {"delete", "execute"},  # File deletion, code execution
        "docker": {"prune", "rmi"},  # System cleanup
        "deploy": {"firebase_deploy", "aws_lambda_deploy"},  # Production deployments
        "git": {"push", "reset"},  # Repository modifications
    }

    def get_operation_risk(self, tool_name: str, operation: str) -> OperationRisk:
        """Determine the risk level of an operation"""
        if tool_name in self.CRITICAL_OPERATIONS:
            if operation in self.CRITICAL_OPERATIONS[tool_name]:
                return OperationRisk.CRITICAL

        if tool_name in self.HIGH_RISK_OPERATIONS:
            if operation in self.HIGH_RISK_OPERATIONS[tool_name]:
                return OperationRisk.HIGH

        # Default risk levels by tool type
        default_risks = {
            "shell": OperationRisk.MEDIUM,
            "filesystem": OperationRisk.LOW,
            "browser": OperationRisk.LOW,
            "git": OperationRisk.LOW,
            "docker": OperationRisk.MEDIUM,
            "database": OperationRisk.MEDIUM,
            "deploy": OperationRisk.HIGH,
            "package": OperationRisk.MEDIUM,
        }

        return default_risks.get(tool_name, OperationRisk.SAFE)

    def check_permission_with_risk(
        self,
        tool_name: str,
        operation: str,
        context: Optional[Dict] = None
    ) -> tuple[bool, str, OperationRisk]:
        """
        Check permission with risk assessment.

        Returns:
            (allowed, reason, risk_level)
        """
        risk = self.get_operation_risk(tool_name, operation)
        allowed, reason = self.check_permission(tool_name, operation, context)

        # Audit the check
        self._audit(
            action="PERMISSION_CHECK",
            tool=tool_name,
            operation=operation,
            result="ALLOWED" if allowed else "DENIED",
            details={"reason": reason, "risk": risk.name, "context": context}
        )

        return allowed, reason, risk


class Tool(ABC):
    """
    Base class for all tools.

    Tools provide capabilities that AI agents can use:
    - File system operations
    - Web browsing
    - Shell commands
    - etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        permission_manager: Optional[PermissionManager] = None
    ):
        self.name = name
        self.description = description
        self.permission_manager = permission_manager or PermissionManager()
        self._operations: Dict[str, Callable] = {}
        self._usage_count = 0
        self._last_used: Optional[str] = None

    def register_operation(
        self,
        name: str,
        func: Callable,
        description: str = "",
        requires_permission: bool = True
    ):
        """Register a tool operation"""
        self._operations[name] = {
            "func": func,
            "description": description,
            "requires_permission": requires_permission,
        }

    async def execute(
        self,
        operation: str,
        **kwargs
    ) -> ToolResult:
        """Execute a tool operation with permission check and comprehensive error handling"""
        import time
        import traceback
        start_time = time.time()

        # Validate operation exists
        if operation not in self._operations:
            error_detail = ToolError(
                error_type="INVALID_OPERATION",
                message=f"Unknown operation: {operation}",
                details={"available_operations": list(self._operations.keys())},
                recoverable=True,
                suggested_action=f"Use one of: {', '.join(self._operations.keys())}"
            )
            logger.warning(f"Tool {self.name}: Unknown operation '{operation}'")
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown operation: {operation}",
                error_detail=error_detail,
            )

        op_info = self._operations[operation]

        # Check permission with risk assessment
        if op_info["requires_permission"]:
            allowed, reason, risk = self.permission_manager.check_permission_with_risk(
                self.name, operation, kwargs
            )
            if not allowed:
                error_detail = ToolError(
                    error_type="PERMISSION_DENIED",
                    message=f"Permission denied: {reason}",
                    details={
                        "tool": self.name,
                        "operation": operation,
                        "risk_level": risk.name,
                    },
                    recoverable=True,
                    suggested_action=f"Grant permission with: grant_tool_permission('{self.name}', '{operation}')"
                )
                logger.info(f"Tool {self.name}.{operation}: Permission denied (risk={risk.name}) - {reason}")
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Permission denied: {reason}",
                    error_detail=error_detail,
                    metadata={
                        "permission_required": True,
                        "risk_level": risk.name,
                    }
                )

        # Execute operation with comprehensive error handling
        try:
            func = op_info["func"]
            if asyncio.iscoroutinefunction(func):
                result = await func(**kwargs)
            else:
                result = func(**kwargs)

            self._usage_count += 1
            self._last_used = datetime.now(timezone.utc).isoformat()

            execution_time = time.time() - start_time

            if isinstance(result, ToolResult):
                result.execution_time = execution_time
                # Log any warnings
                if result.has_warnings:
                    for warning in result.warnings:
                        logger.warning(f"Tool {self.name}.{operation}: {warning}")
                return result

            return ToolResult(
                success=True,
                output=result,
                execution_time=execution_time,
            )

        except FileNotFoundError as e:
            error_detail = ToolError(
                error_type="FILE_NOT_FOUND",
                message=str(e),
                details={"path": str(e.filename) if hasattr(e, 'filename') else None},
                recoverable=True,
                suggested_action="Check if the file path exists and is accessible"
            )
            logger.error(f"Tool {self.name}.{operation}: File not found - {e}")
            return ToolResult(
                success=False, output=None, error=str(e),
                error_detail=error_detail,
                execution_time=time.time() - start_time,
            )

        except PermissionError as e:
            error_detail = ToolError(
                error_type="OS_PERMISSION_DENIED",
                message=str(e),
                details={"errno": e.errno if hasattr(e, 'errno') else None},
                recoverable=False,
                suggested_action="Check file system permissions"
            )
            logger.error(f"Tool {self.name}.{operation}: OS permission denied - {e}")
            return ToolResult(
                success=False, output=None, error=str(e),
                error_detail=error_detail,
                execution_time=time.time() - start_time,
            )

        except TimeoutError as e:
            error_detail = ToolError(
                error_type="TIMEOUT",
                message=str(e),
                recoverable=True,
                suggested_action="Try again or increase timeout"
            )
            logger.error(f"Tool {self.name}.{operation}: Timeout - {e}")
            return ToolResult(
                success=False, output=None, error=str(e),
                error_detail=error_detail,
                execution_time=time.time() - start_time,
            )

        except ConnectionError as e:
            error_detail = ToolError(
                error_type="CONNECTION_ERROR",
                message=str(e),
                recoverable=True,
                suggested_action="Check network connectivity and try again"
            )
            logger.error(f"Tool {self.name}.{operation}: Connection error - {e}")
            return ToolResult(
                success=False, output=None, error=str(e),
                error_detail=error_detail,
                execution_time=time.time() - start_time,
            )

        except ValueError as e:
            error_detail = ToolError(
                error_type="INVALID_INPUT",
                message=str(e),
                details={"parameters": list(kwargs.keys())},
                recoverable=True,
                suggested_action="Check input parameters"
            )
            logger.error(f"Tool {self.name}.{operation}: Invalid input - {e}")
            return ToolResult(
                success=False, output=None, error=str(e),
                error_detail=error_detail,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            # Catch-all for unexpected errors
            tb = traceback.format_exc()
            error_detail = ToolError(
                error_type="UNEXPECTED_ERROR",
                message=str(e),
                details={
                    "exception_type": type(e).__name__,
                    "traceback": tb[:1000],  # Truncate long tracebacks
                },
                recoverable=False,
                suggested_action="Check logs for more details"
            )
            logger.error(f"Tool {self.name}.{operation}: Unexpected error - {e}\n{tb}")
            return ToolResult(
                success=False, output=None, error=str(e),
                error_detail=error_detail,
                execution_time=time.time() - start_time,
            )

    @abstractmethod
    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of available operations with descriptions"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        return {
            "name": self.name,
            "description": self.description,
            "usage_count": self._usage_count,
            "last_used": self._last_used,
            "operations": list(self._operations.keys()),
        }


# Need to import asyncio for the iscoroutinefunction check
import asyncio
