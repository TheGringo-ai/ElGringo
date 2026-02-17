"""
Shell Tools - Execute shell commands for AI agents
===================================================

Capabilities:
- Execute shell commands
- Run scripts
- Manage processes
- Environment variables
"""

import asyncio
import logging
import os
import shlex
import subprocess
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class ShellTools(Tool):
    """
    Shell command execution tools.

    Security:
    - Commands are validated before execution
    - Dangerous commands are blocked
    - Timeout prevents runaway processes
    """

    # Commands that are NEVER allowed
    BLOCKED_COMMANDS = [
        "rm -rf /", "rm -rf ~", "rm -rf /*",
        ":(){ :|:& };:",  # Fork bomb
        "mkfs", "dd if=/dev/zero",
        "chmod -R 777 /", "chown -R",
        "> /dev/sda", "mv / ",
    ]

    # Commands that require explicit permission
    SENSITIVE_COMMANDS = [
        "rm", "mv", "cp", "chmod", "chown",
        "sudo", "su", "passwd",
        "curl", "wget", "ssh", "scp",
        "docker", "kubectl",
        "pip install", "npm install",
    ]

    # Safe commands that don't need permission
    SAFE_COMMANDS = [
        "ls", "pwd", "cd", "cat", "head", "tail",
        "grep", "find", "which", "whereis",
        "echo", "date", "whoami", "hostname",
        "git status", "git log", "git diff", "git branch",
        "python --version", "node --version", "npm --version",
        "ps", "top -l 1", "df -h", "du -sh",
    ]

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_timeout: int = 60,
        default_cwd: Optional[str] = None
    ):
        super().__init__(
            name="shell",
            description="Execute shell commands",
            permission_manager=permission_manager,
        )

        self.default_timeout = default_timeout
        self.default_cwd = default_cwd

        # Register operations
        self.register_operation("run", self._run_command, "Run a shell command")
        self.register_operation("run_safe", self._run_safe_command, "Run a safe command", requires_permission=False)
        self.register_operation("background", self._run_background, "Run command in background")
        self.register_operation("env", self._get_env, "Get environment variable", requires_permission=False)
        self.register_operation("set_env", self._set_env, "Set environment variable")
        self.register_operation("which", self._which, "Find command location", requires_permission=False)
        self.register_operation("processes", self._list_processes, "List running processes", requires_permission=False)
        self.register_operation("kill", self._kill_process, "Kill a process")

    def _is_blocked(self, command: str) -> bool:
        """Check if command is blocked"""
        cmd_lower = command.lower().strip()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return True
        return False

    def _is_safe(self, command: str) -> bool:
        """Check if command is in safe list"""
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return False

        base_cmd = cmd_parts[0]

        # Check exact matches
        for safe in self.SAFE_COMMANDS:
            if command.startswith(safe) or base_cmd == safe.split()[0]:
                return True

        return False

    def _is_sensitive(self, command: str) -> bool:
        """Check if command is sensitive"""
        cmd_lower = command.lower()
        for sensitive in self.SENSITIVE_COMMANDS:
            if sensitive.lower() in cmd_lower:
                return True
        return False

    async def _run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Run a shell command"""
        # Security check
        if self._is_blocked(command):
            return ToolResult(
                success=False,
                output=None,
                error=f"Command blocked for security: {command}"
            )

        try:
            # Prepare environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            # Run command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or self.default_cwd,
                env=run_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout or self.default_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command timed out after {timeout or self.default_timeout}s"
                )

            return ToolResult(
                success=process.returncode == 0,
                output={
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "return_code": process.returncode,
                },
                error=stderr.decode() if process.returncode != 0 else None,
                metadata={"command": command, "cwd": cwd}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _run_safe_command(self, command: str, cwd: Optional[str] = None) -> ToolResult:
        """Run a command from the safe list (no permission needed)"""
        if not self._is_safe(command):
            return ToolResult(
                success=False,
                output=None,
                error=f"Command not in safe list: {command}. Use 'run' for other commands."
            )

        return await self._run_command(command, cwd=cwd)

    async def _run_background(
        self,
        command: str,
        cwd: Optional[str] = None,
        log_file: Optional[str] = None
    ) -> ToolResult:
        """Run a command in the background"""
        if self._is_blocked(command):
            return ToolResult(
                success=False,
                output=None,
                error=f"Command blocked: {command}"
            )

        try:
            # Redirect output if log file specified
            if log_file:
                command = f"{command} > {log_file} 2>&1"

            # Run detached
            process = await asyncio.create_subprocess_shell(
                f"nohup {command} &",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=cwd or self.default_cwd,
            )

            return ToolResult(
                success=True,
                output={
                    "pid": process.pid,
                    "command": command,
                    "log_file": log_file,
                },
                metadata={"background": True}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _get_env(self, name: str) -> ToolResult:
        """Get an environment variable"""
        value = os.environ.get(name)
        return ToolResult(
            success=True,
            output={"name": name, "value": value, "exists": value is not None}
        )

    def _set_env(self, name: str, value: str) -> ToolResult:
        """Set an environment variable for this session"""
        try:
            os.environ[name] = value
            return ToolResult(
                success=True,
                output=f"Set {name}={value}",
                metadata={"name": name}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _which(self, command: str) -> ToolResult:
        """Find the location of a command"""
        try:
            import shutil
            path = shutil.which(command)
            return ToolResult(
                success=True,
                output={"command": command, "path": path, "found": path is not None}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _list_processes(self, filter_name: Optional[str] = None) -> ToolResult:
        """List running processes"""
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.strip().split("\n")
            processes = []

            for line in lines[1:]:  # Skip header
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    proc = {
                        "user": parts[0],
                        "pid": parts[1],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "command": parts[10],
                    }

                    if filter_name:
                        if filter_name.lower() in proc["command"].lower():
                            processes.append(proc)
                    else:
                        processes.append(proc)

            return ToolResult(
                success=True,
                output=processes[:100],  # Limit results
                metadata={"count": len(processes)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _kill_process(self, pid: int, signal: int = 15) -> ToolResult:
        """Kill a process by PID"""
        try:
            os.kill(pid, signal)
            return ToolResult(
                success=True,
                output=f"Sent signal {signal} to process {pid}",
                metadata={"pid": pid, "signal": signal}
            )
        except ProcessLookupError:
            return ToolResult(success=False, output=None, error=f"Process {pid} not found")
        except PermissionError:
            return ToolResult(success=False, output=None, error=f"Permission denied for process {pid}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of available operations"""
        return [
            {"operation": "run", "description": "Run a shell command"},
            {"operation": "run_safe", "description": "Run a safe command (no permission needed)"},
            {"operation": "background", "description": "Run command in background"},
            {"operation": "env", "description": "Get environment variable"},
            {"operation": "set_env", "description": "Set environment variable"},
            {"operation": "which", "description": "Find command location"},
            {"operation": "processes", "description": "List running processes"},
            {"operation": "kill", "description": "Kill a process"},
        ]
