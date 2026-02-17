"""
File System Tools - Secure file operations for AI agents
=========================================================

Capabilities:
- Read files
- Write files
- List directories
- Search files
- Execute scripts (with permission)
"""

import glob
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class FileSystemTools(Tool):
    """
    File system tools with security sandboxing.

    All operations respect the permission system.
    Forbidden paths are never accessible.
    """

    # Maximum file size to read (10MB)
    MAX_READ_SIZE = 10 * 1024 * 1024

    # Maximum files to list
    MAX_LIST_FILES = 1000

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        super().__init__(
            name="filesystem",
            description="Read, write, and manage files on the local system",
            permission_manager=permission_manager,
        )

        # Register operations
        self.register_operation("read", self._read_file, "Read file contents")
        self.register_operation("write", self._write_file, "Write content to file")
        self.register_operation("append", self._append_file, "Append content to file")
        self.register_operation("list", self._list_directory, "List directory contents", requires_permission=False)
        self.register_operation("search", self._search_files, "Search for files by pattern", requires_permission=False)
        self.register_operation("exists", self._file_exists, "Check if file exists", requires_permission=False)
        self.register_operation("info", self._file_info, "Get file information", requires_permission=False)
        self.register_operation("delete", self._delete_file, "Delete a file")
        self.register_operation("mkdir", self._make_directory, "Create a directory")
        self.register_operation("execute", self._execute_script, "Execute a script file")

    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate a path"""
        return Path(path).expanduser().resolve()

    def _read_file(self, path: str, encoding: str = "utf-8") -> ToolResult:
        """Read a file's contents"""
        try:
            filepath = self._resolve_path(path)

            if not filepath.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {path}")

            if not filepath.is_file():
                return ToolResult(success=False, output=None, error=f"Not a file: {path}")

            # Check size
            size = filepath.stat().st_size
            if size > self.MAX_READ_SIZE:
                return ToolResult(
                    success=False, output=None,
                    error=f"File too large: {size} bytes (max {self.MAX_READ_SIZE})"
                )

            # Read file
            content = filepath.read_text(encoding=encoding)

            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(filepath), "size": size, "encoding": encoding}
            )

        except UnicodeDecodeError:
            # Try binary read
            try:
                content = filepath.read_bytes()
                return ToolResult(
                    success=True,
                    output=f"[Binary file: {len(content)} bytes]",
                    metadata={"path": str(filepath), "binary": True}
                )
            except Exception as e:
                return ToolResult(success=False, output=None, error=str(e))

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> ToolResult:
        """Write content to a file"""
        try:
            filepath = self._resolve_path(path)

            # Create parent directories if needed
            if create_dirs:
                filepath.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            filepath.write_text(content, encoding=encoding)

            return ToolResult(
                success=True,
                output=f"Written {len(content)} bytes to {filepath}",
                metadata={"path": str(filepath), "size": len(content)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _append_file(self, path: str, content: str, encoding: str = "utf-8") -> ToolResult:
        """Append content to a file"""
        try:
            filepath = self._resolve_path(path)

            with open(filepath, "a", encoding=encoding) as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Appended {len(content)} bytes to {filepath}",
                metadata={"path": str(filepath)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _list_directory(
        self,
        path: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        include_hidden: bool = False
    ) -> ToolResult:
        """List directory contents"""
        try:
            dirpath = self._resolve_path(path)

            if not dirpath.exists():
                return ToolResult(success=False, output=None, error=f"Directory not found: {path}")

            if not dirpath.is_dir():
                return ToolResult(success=False, output=None, error=f"Not a directory: {path}")

            # Get files
            if recursive:
                files = list(dirpath.rglob(pattern))
            else:
                files = list(dirpath.glob(pattern))

            # Filter hidden if needed
            if not include_hidden:
                files = [f for f in files if not f.name.startswith(".")]

            # Limit results
            files = files[:self.MAX_LIST_FILES]

            # Format output
            result = []
            for f in sorted(files):
                try:
                    stat = f.stat()
                    file_type = "d" if f.is_dir() else "f"
                    size = stat.st_size if f.is_file() else 0
                    result.append({
                        "name": f.name,
                        "path": str(f),
                        "type": file_type,
                        "size": size,
                    })
                except Exception:
                    continue

            return ToolResult(
                success=True,
                output=result,
                metadata={"path": str(dirpath), "count": len(result)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _search_files(
        self,
        pattern: str,
        path: str = ".",
        content_pattern: Optional[str] = None,
        max_results: int = 100
    ) -> ToolResult:
        """Search for files by name pattern and optionally content"""
        try:
            basepath = self._resolve_path(path)
            matches = []

            for filepath in basepath.rglob(pattern):
                if len(matches) >= max_results:
                    break

                if filepath.is_file():
                    match_info = {
                        "path": str(filepath),
                        "name": filepath.name,
                        "size": filepath.stat().st_size,
                    }

                    # Search content if pattern provided
                    if content_pattern:
                        try:
                            content = filepath.read_text(errors="ignore")
                            if content_pattern.lower() in content.lower():
                                # Find line numbers
                                lines = []
                                for i, line in enumerate(content.split("\n"), 1):
                                    if content_pattern.lower() in line.lower():
                                        lines.append(i)
                                match_info["matching_lines"] = lines[:10]
                                matches.append(match_info)
                        except Exception:
                            continue
                    else:
                        matches.append(match_info)

            return ToolResult(
                success=True,
                output=matches,
                metadata={"pattern": pattern, "count": len(matches)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _file_exists(self, path: str) -> ToolResult:
        """Check if a file or directory exists"""
        filepath = self._resolve_path(path)
        exists = filepath.exists()
        file_type = "directory" if filepath.is_dir() else "file" if filepath.is_file() else "unknown"

        return ToolResult(
            success=True,
            output={"exists": exists, "type": file_type if exists else None},
            metadata={"path": str(filepath)}
        )

    def _file_info(self, path: str) -> ToolResult:
        """Get detailed file information"""
        try:
            filepath = self._resolve_path(path)

            if not filepath.exists():
                return ToolResult(success=False, output=None, error=f"Not found: {path}")

            stat = filepath.stat()

            info = {
                "path": str(filepath),
                "name": filepath.name,
                "type": "directory" if filepath.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:],
            }

            if filepath.is_file():
                info["extension"] = filepath.suffix

            return ToolResult(success=True, output=info)

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _delete_file(self, path: str, recursive: bool = False) -> ToolResult:
        """Delete a file or directory"""
        try:
            filepath = self._resolve_path(path)

            if not filepath.exists():
                return ToolResult(success=False, output=None, error=f"Not found: {path}")

            if filepath.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(filepath)
                else:
                    filepath.rmdir()
            else:
                filepath.unlink()

            return ToolResult(
                success=True,
                output=f"Deleted: {filepath}",
                metadata={"path": str(filepath)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _make_directory(self, path: str, parents: bool = True) -> ToolResult:
        """Create a directory"""
        try:
            dirpath = self._resolve_path(path)
            dirpath.mkdir(parents=parents, exist_ok=True)

            return ToolResult(
                success=True,
                output=f"Created directory: {dirpath}",
                metadata={"path": str(dirpath)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _execute_script(
        self,
        path: str,
        args: Optional[List[str]] = None,
        timeout: int = 60,
        capture_output: bool = True
    ) -> ToolResult:
        """Execute a script file"""
        try:
            filepath = self._resolve_path(path)

            if not filepath.exists():
                return ToolResult(success=False, output=None, error=f"Script not found: {path}")

            if not filepath.is_file():
                return ToolResult(success=False, output=None, error=f"Not a file: {path}")

            # Determine interpreter
            suffix = filepath.suffix.lower()
            interpreters = {
                ".py": ["python3"],
                ".sh": ["bash"],
                ".js": ["node"],
                ".rb": ["ruby"],
                ".pl": ["perl"],
            }

            cmd = interpreters.get(suffix, [])
            cmd.append(str(filepath))
            if args:
                cmd.extend(args)

            # Execute
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                timeout=timeout,
                text=True,
                cwd=filepath.parent,
            )

            return ToolResult(
                success=result.returncode == 0,
                output={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                },
                error=result.stderr if result.returncode != 0 else None,
                metadata={"path": str(filepath), "args": args}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output=None, error=f"Script timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of available operations"""
        return [
            {"operation": "read", "description": "Read file contents"},
            {"operation": "write", "description": "Write content to file"},
            {"operation": "append", "description": "Append content to file"},
            {"operation": "list", "description": "List directory contents"},
            {"operation": "search", "description": "Search for files"},
            {"operation": "exists", "description": "Check if file exists"},
            {"operation": "info", "description": "Get file information"},
            {"operation": "delete", "description": "Delete a file"},
            {"operation": "mkdir", "description": "Create a directory"},
            {"operation": "execute", "description": "Execute a script"},
        ]
