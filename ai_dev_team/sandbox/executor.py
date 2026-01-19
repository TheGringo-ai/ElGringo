"""
Code Execution Sandbox
======================

Safely executes Python and JavaScript code snippets with:
- Resource limits (memory, CPU time)
- Timeout handling
- Output capture
- Error isolation

Two execution modes:
1. SUBPROCESS: Uses subprocess with resource limits (default, safer)
2. DOCKER: Uses Docker containers for full isolation (requires Docker)
"""

import asyncio
import json
import logging
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for the sandbox"""
    SUBPROCESS = "subprocess"  # Uses subprocess with resource limits
    DOCKER = "docker"  # Uses Docker containers (requires Docker)


@dataclass
class ExecutionResult:
    """Result of code execution"""
    execution_id: str
    language: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float  # seconds
    memory_used: Optional[int] = None  # bytes
    error: Optional[str] = None
    timed_out: bool = False
    killed: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ResourceLimits:
    """Resource limits for code execution"""
    def __init__(
        self,
        max_memory_mb: int = 128,
        max_cpu_time: int = 10,  # seconds
        max_wall_time: int = 30,  # seconds
        max_output_size: int = 1024 * 1024,  # 1MB
        max_processes: int = 10,
    ):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self.max_wall_time = max_wall_time
        self.max_output_size = max_output_size
        self.max_processes = max_processes


# Dangerous modules/functions to block in Python
PYTHON_BLOCKED_MODULES = {
    'os.system', 'os.popen', 'os.spawn', 'os.exec',
    'subprocess', 'multiprocessing',
    'socket', 'http', 'urllib', 'ftplib', 'smtplib',
    '__import__', 'importlib', 'eval', 'exec', 'compile',
    'open',  # We'll provide a restricted version
    'input',  # No interactive input
}

# Safe builtins for restricted execution
SAFE_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'complex', 'dict', 'dir', 'divmod',
    'enumerate', 'filter', 'float', 'format', 'frozenset', 'getattr',
    'hasattr', 'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'object', 'oct',
    'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round',
    'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum',
    'super', 'tuple', 'type', 'vars', 'zip',
    'True', 'False', 'None',
    'Exception', 'BaseException', 'ValueError', 'TypeError', 'KeyError',
    'IndexError', 'AttributeError', 'RuntimeError', 'StopIteration',
}


class CodeExecutor:
    """
    Safe code execution sandbox for Python and JavaScript
    """

    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.SUBPROCESS,
        limits: Optional[ResourceLimits] = None,
        docker_image_python: str = "python:3.11-slim",
        docker_image_node: str = "node:20-slim",
    ):
        self.mode = mode
        self.limits = limits or ResourceLimits()
        self.docker_image_python = docker_image_python
        self.docker_image_node = docker_image_node
        self._execution_history: List[ExecutionResult] = []

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute code in the sandbox

        Args:
            code: The code to execute
            language: 'python' or 'javascript'
            timeout: Override default timeout (seconds)

        Returns:
            ExecutionResult with stdout, stderr, exit code, etc.
        """
        execution_id = str(uuid.uuid4())[:8]
        timeout = timeout or self.limits.max_wall_time
        language = language.lower()

        if language not in ('python', 'javascript', 'js'):
            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=0,
                error=f"Unsupported language: {language}. Use 'python' or 'javascript'."
            )

        # Normalize javascript
        if language == 'js':
            language = 'javascript'

        try:
            if self.mode == ExecutionMode.DOCKER:
                result = await self._execute_docker(code, language, execution_id, timeout)
            else:
                result = await self._execute_subprocess(code, language, execution_id, timeout)

            self._execution_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=0,
                error=str(e)
            )

    async def _execute_subprocess(
        self,
        code: str,
        language: str,
        execution_id: str,
        timeout: int,
    ) -> ExecutionResult:
        """Execute code using subprocess with resource limits"""
        start_time = time.time()

        # Create temp file for code
        suffix = '.py' if language == 'python' else '.js'
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(code)
            code_file = f.name

        try:
            # Build command
            if language == 'python':
                cmd = [sys.executable, code_file]
            else:
                # Try node, nodejs, or fallback
                node_cmd = 'node' if os.system('which node > /dev/null 2>&1') == 0 else 'nodejs'
                cmd = [node_cmd, code_file]

            # Set up resource limits for the subprocess (best effort on macOS)
            def set_limits():
                try:
                    # CPU time limit (works on macOS and Linux)
                    resource.setrlimit(resource.RLIMIT_CPU, (self.limits.max_cpu_time, self.limits.max_cpu_time))
                except (ValueError, OSError):
                    pass  # May fail on some systems

                # These may not work on macOS but try anyway
                if sys.platform == 'linux':
                    try:
                        # Memory limit (Linux only)
                        mem_bytes = self.limits.max_memory_mb * 1024 * 1024
                        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
                    except (ValueError, OSError):
                        pass
                    try:
                        # Max processes (Linux only)
                        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
                    except (ValueError, OSError):
                        pass

            # Run the code
            preexec = set_limits if sys.platform != 'win32' else None
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                timed_out = False
                killed = False
            except asyncio.TimeoutError:
                process.kill()
                stdout, stderr = await process.communicate()
                timed_out = True
                killed = True

            execution_time = time.time() - start_time

            # Truncate output if too large
            max_size = self.limits.max_output_size
            stdout_str = stdout.decode('utf-8', errors='replace')[:max_size]
            stderr_str = stderr.decode('utf-8', errors='replace')[:max_size]

            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                success=process.returncode == 0 and not timed_out,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode or 0,
                execution_time=round(execution_time, 3),
                timed_out=timed_out,
                killed=killed,
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(code_file)
            except:
                pass

    async def _execute_docker(
        self,
        code: str,
        language: str,
        execution_id: str,
        timeout: int,
    ) -> ExecutionResult:
        """Execute code in a Docker container for full isolation"""
        start_time = time.time()

        # Select image and command
        if language == 'python':
            image = self.docker_image_python
            cmd_prefix = ['python', '-c']
        else:
            image = self.docker_image_node
            cmd_prefix = ['node', '-e']

        # Docker run command with security restrictions
        docker_cmd = [
            'docker', 'run',
            '--rm',  # Remove container after execution
            '--network', 'none',  # No network access
            f'--memory={self.limits.max_memory_mb}m',
            f'--cpus=0.5',  # Limit to half a CPU
            '--pids-limit', str(self.limits.max_processes),
            '--read-only',  # Read-only filesystem
            '--security-opt', 'no-new-privileges',
            '--name', f'sandbox-{execution_id}',
            image,
            *cmd_prefix, code
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                timed_out = False
                killed = False
            except asyncio.TimeoutError:
                # Kill the container
                await asyncio.create_subprocess_exec(
                    'docker', 'kill', f'sandbox-{execution_id}',
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, stderr = b'', b'Execution timed out'
                timed_out = True
                killed = True

            execution_time = time.time() - start_time

            max_size = self.limits.max_output_size
            stdout_str = stdout.decode('utf-8', errors='replace')[:max_size]
            stderr_str = stderr.decode('utf-8', errors='replace')[:max_size]

            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                success=process.returncode == 0 and not timed_out,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode or 0,
                execution_time=round(execution_time, 3),
                timed_out=timed_out,
                killed=killed,
            )

        except FileNotFoundError:
            return ExecutionResult(
                execution_id=execution_id,
                language=language,
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time=0,
                error="Docker not available. Install Docker or use SUBPROCESS mode."
            )

    def validate_python_code(self, code: str) -> Dict[str, Any]:
        """
        Validate Python code for dangerous operations

        Returns dict with:
            - valid: bool
            - warnings: list of potential issues
            - blocked: list of blocked operations found
        """
        import ast

        warnings = []
        blocked = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f"Syntax error: {e}",
                'warnings': [],
                'blocked': []
            }

        class SecurityChecker(ast.NodeVisitor):
            def visit_Import(self, node):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in ('subprocess', 'os', 'sys', 'socket', 'multiprocessing'):
                        blocked.append(f"Import of restricted module: {alias.name}")
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in ('subprocess', 'os', 'sys', 'socket', 'multiprocessing'):
                        blocked.append(f"Import from restricted module: {node.module}")
                self.generic_visit(node)

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name in ('eval', 'exec', 'compile', 'open', '__import__'):
                        blocked.append(f"Blocked function call: {name}()")
                    elif name == 'input':
                        warnings.append("input() may hang - interactive input not supported")
                self.generic_visit(node)

            def visit_Attribute(self, node):
                if isinstance(node.value, ast.Name):
                    attr_path = f"{node.value.id}.{node.attr}"
                    if attr_path in ('os.system', 'os.popen', 'os.exec', 'os.spawn'):
                        blocked.append(f"Blocked system call: {attr_path}")
                self.generic_visit(node)

        checker = SecurityChecker()
        checker.visit(tree)

        return {
            'valid': len(blocked) == 0,
            'warnings': warnings,
            'blocked': blocked
        }

    async def execute_with_validation(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute code with pre-validation for dangerous operations
        """
        execution_id = str(uuid.uuid4())[:8]

        if language.lower() == 'python':
            validation = self.validate_python_code(code)
            if not validation['valid']:
                # Check if it's a syntax error vs blocked operations
                if 'error' in validation and validation['error']:
                    return ExecutionResult(
                        execution_id=execution_id,
                        language=language,
                        success=False,
                        stdout="",
                        stderr=validation['error'],
                        exit_code=-1,
                        execution_time=0,
                        error=validation['error']
                    )
                else:
                    return ExecutionResult(
                        execution_id=execution_id,
                        language=language,
                        success=False,
                        stdout="",
                        stderr="\n".join(validation['blocked']),
                        exit_code=-1,
                        execution_time=0,
                        error="Code validation failed: dangerous operations detected"
                    )

        return await self.execute(code, language, timeout)

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        return [r.to_dict() for r in self._execution_history[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0,
                'by_language': {},
                'avg_execution_time': 0,
                'timeout_rate': 0
            }

        total = len(self._execution_history)
        successes = sum(1 for r in self._execution_history if r.success)
        timeouts = sum(1 for r in self._execution_history if r.timed_out)
        avg_time = sum(r.execution_time for r in self._execution_history) / total

        by_language = {}
        for r in self._execution_history:
            if r.language not in by_language:
                by_language[r.language] = {'total': 0, 'successes': 0}
            by_language[r.language]['total'] += 1
            if r.success:
                by_language[r.language]['successes'] += 1

        return {
            'total_executions': total,
            'success_rate': round(successes / total, 3) if total > 0 else 0,
            'by_language': by_language,
            'avg_execution_time': round(avg_time, 3),
            'timeout_rate': round(timeouts / total, 3) if total > 0 else 0,
            'mode': self.mode.value,
            'limits': {
                'max_memory_mb': self.limits.max_memory_mb,
                'max_cpu_time': self.limits.max_cpu_time,
                'max_wall_time': self.limits.max_wall_time,
            }
        }


# Singleton instance
_executor: Optional[CodeExecutor] = None


def get_code_executor() -> CodeExecutor:
    """Get the global code executor instance"""
    global _executor
    if _executor is None:
        _executor = CodeExecutor()
    return _executor
