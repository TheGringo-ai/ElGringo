"""
Package Manager Tools - Package operations for AI agents
=========================================================

Capabilities:
- npm (Node.js packages)
- pip (Python packages)
- cargo (Rust packages)
- brew (macOS packages)
- Project initialization
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class PackageTools(Tool):
    """
    Package manager tools for AI-powered development.

    Supports npm, pip, cargo, and brew for managing
    dependencies across different languages.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_cwd: Optional[str] = None
    ):
        super().__init__(
            name="package",
            description="Package manager operations (npm, pip, cargo, brew)",
            permission_manager=permission_manager,
        )

        self.default_cwd = default_cwd or os.getcwd()

        # npm operations
        self.register_operation("npm_install", self._npm_install, "Install npm packages")
        self.register_operation("npm_uninstall", self._npm_uninstall, "Uninstall npm package")
        self.register_operation("npm_list", self._npm_list, "List npm packages", requires_permission=False)
        self.register_operation("npm_run", self._npm_run, "Run npm script")
        self.register_operation("npm_init", self._npm_init, "Initialize npm project")
        self.register_operation("npm_update", self._npm_update, "Update npm packages")
        self.register_operation("npm_audit", self._npm_audit, "Audit npm packages", requires_permission=False)
        self.register_operation("npm_outdated", self._npm_outdated, "Check outdated packages", requires_permission=False)

        # pip operations
        self.register_operation("pip_install", self._pip_install, "Install pip packages")
        self.register_operation("pip_uninstall", self._pip_uninstall, "Uninstall pip package")
        self.register_operation("pip_list", self._pip_list, "List pip packages", requires_permission=False)
        self.register_operation("pip_freeze", self._pip_freeze, "Freeze pip requirements", requires_permission=False)
        self.register_operation("pip_show", self._pip_show, "Show pip package info", requires_permission=False)

        # cargo operations
        self.register_operation("cargo_build", self._cargo_build, "Build Rust project")
        self.register_operation("cargo_run", self._cargo_run, "Run Rust project")
        self.register_operation("cargo_test", self._cargo_test, "Test Rust project")
        self.register_operation("cargo_add", self._cargo_add, "Add Rust dependency")
        self.register_operation("cargo_new", self._cargo_new, "Create new Rust project")

        # brew operations
        self.register_operation("brew_install", self._brew_install, "Install brew package")
        self.register_operation("brew_uninstall", self._brew_uninstall, "Uninstall brew package")
        self.register_operation("brew_list", self._brew_list, "List brew packages", requires_permission=False)
        self.register_operation("brew_update", self._brew_update, "Update brew")
        self.register_operation("brew_upgrade", self._brew_upgrade, "Upgrade brew packages")
        self.register_operation("brew_search", self._brew_search, "Search brew packages", requires_permission=False)

        # Project initialization
        self.register_operation("init_project", self._init_project, "Initialize new project")

    async def _run_cmd(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 300
    ) -> ToolResult:
        """Execute a command"""
        try:
            work_dir = cwd or self.default_cwd

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout_str or stderr_str,
                    metadata={"command": " ".join(cmd), "cwd": work_dir}
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"Command failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"Command timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error=f"Command not found: {cmd[0]}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # npm operations
    def _npm_install(
        self,
        packages: Optional[List[str]] = None,
        dev: bool = False,
        global_install: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Install npm packages"""
        args = ["npm", "install"]
        if global_install:
            args.append("-g")
        if dev:
            args.append("--save-dev")
        if packages:
            args.extend(packages)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _npm_uninstall(
        self,
        package: str,
        global_uninstall: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Uninstall npm package"""
        args = ["npm", "uninstall"]
        if global_uninstall:
            args.append("-g")
        args.append(package)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _npm_list(
        self,
        depth: int = 0,
        global_list: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """List npm packages"""
        args = ["npm", "list", f"--depth={depth}"]
        if global_list:
            args.append("-g")
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _npm_run(
        self,
        script: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Run npm script"""
        cmd = ["npm", "run", script]
        if args:
            cmd.append("--")
            cmd.extend(args)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(cmd, cwd)
        )

    def _npm_init(
        self,
        yes: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Initialize npm project"""
        args = ["npm", "init"]
        if yes:
            args.append("-y")
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _npm_update(
        self,
        packages: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Update npm packages"""
        args = ["npm", "update"]
        if packages:
            args.extend(packages)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _npm_audit(
        self,
        fix: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Audit npm packages for vulnerabilities"""
        args = ["npm", "audit"]
        if fix:
            args.append("fix")
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _npm_outdated(self, cwd: Optional[str] = None) -> ToolResult:
        """Check for outdated packages"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["npm", "outdated"], cwd)
        )

    # pip operations
    def _pip_install(
        self,
        packages: List[str],
        requirements: Optional[str] = None,
        upgrade: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Install pip packages"""
        args = ["pip3", "install"]
        if upgrade:
            args.append("--upgrade")
        if requirements:
            args.extend(["-r", requirements])
        else:
            args.extend(packages)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _pip_uninstall(
        self,
        package: str,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Uninstall pip package"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["pip3", "uninstall", "-y", package], cwd)
        )

    def _pip_list(
        self,
        outdated: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """List pip packages"""
        args = ["pip3", "list"]
        if outdated:
            args.append("--outdated")
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _pip_freeze(self, cwd: Optional[str] = None) -> ToolResult:
        """Freeze pip requirements"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["pip3", "freeze"], cwd)
        )

    def _pip_show(self, package: str, cwd: Optional[str] = None) -> ToolResult:
        """Show pip package info"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["pip3", "show", package], cwd)
        )

    # cargo operations
    def _cargo_build(
        self,
        release: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Build Rust project"""
        args = ["cargo", "build"]
        if release:
            args.append("--release")
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _cargo_run(
        self,
        release: bool = False,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Run Rust project"""
        cmd = ["cargo", "run"]
        if release:
            cmd.append("--release")
        if args:
            cmd.append("--")
            cmd.extend(args)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(cmd, cwd)
        )

    def _cargo_test(
        self,
        test_name: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Test Rust project"""
        args = ["cargo", "test"]
        if test_name:
            args.append(test_name)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _cargo_add(
        self,
        package: str,
        features: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Add Rust dependency"""
        args = ["cargo", "add", package]
        if features:
            args.extend(["--features", ",".join(features)])
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _cargo_new(
        self,
        name: str,
        lib: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create new Rust project"""
        args = ["cargo", "new", name]
        if lib:
            args.append("--lib")
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    # brew operations
    def _brew_install(
        self,
        package: str,
        cask: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Install brew package"""
        args = ["brew", "install"]
        if cask:
            args.append("--cask")
        args.append(package)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _brew_uninstall(
        self,
        package: str,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Uninstall brew package"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["brew", "uninstall", package], cwd)
        )

    def _brew_list(self, cwd: Optional[str] = None) -> ToolResult:
        """List brew packages"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["brew", "list"], cwd)
        )

    def _brew_update(self, cwd: Optional[str] = None) -> ToolResult:
        """Update brew"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["brew", "update"], cwd)
        )

    def _brew_upgrade(
        self,
        package: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Upgrade brew packages"""
        args = ["brew", "upgrade"]
        if package:
            args.append(package)
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _brew_search(
        self,
        query: str,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Search brew packages"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["brew", "search", query], cwd)
        )

    # Project initialization
    def _init_project(
        self,
        project_type: str,
        name: str,
        path: Optional[str] = None,
        template: Optional[str] = None
    ) -> ToolResult:
        """Initialize a new project"""
        work_dir = path or self.default_cwd

        try:
            project_path = Path(work_dir) / name
            project_path.mkdir(parents=True, exist_ok=True)

            if project_type == "node" or project_type == "npm":
                return self._npm_init(yes=True, cwd=str(project_path))

            elif project_type == "react":
                return asyncio.get_event_loop().run_until_complete(
                    self._run_cmd(
                        ["npx", "create-react-app", name],
                        cwd=work_dir,
                        timeout=600
                    )
                )

            elif project_type == "next":
                return asyncio.get_event_loop().run_until_complete(
                    self._run_cmd(
                        ["npx", "create-next-app@latest", name, "--typescript"],
                        cwd=work_dir,
                        timeout=600
                    )
                )

            elif project_type == "vite":
                cmd = ["npm", "create", "vite@latest", name, "--"]
                if template:
                    cmd.extend(["--template", template])
                else:
                    cmd.extend(["--template", "react-ts"])
                return asyncio.get_event_loop().run_until_complete(
                    self._run_cmd(cmd, cwd=work_dir, timeout=300)
                )

            elif project_type == "python":
                # Create Python project structure
                (project_path / "src").mkdir(exist_ok=True)
                (project_path / "tests").mkdir(exist_ok=True)
                (project_path / "src" / "__init__.py").touch()
                (project_path / "tests" / "__init__.py").touch()
                (project_path / "requirements.txt").touch()
                (project_path / "README.md").write_text(f"# {name}\n")

                return ToolResult(
                    success=True,
                    output=f"Python project '{name}' created at {project_path}",
                    metadata={"type": "python", "path": str(project_path)}
                )

            elif project_type == "rust":
                return self._cargo_new(name, cwd=work_dir)

            elif project_type == "flask":
                # Create Flask project structure
                (project_path / "app").mkdir(exist_ok=True)
                (project_path / "app" / "__init__.py").write_text(
                    'from flask import Flask\n\napp = Flask(__name__)\n\nfrom app import routes\n'
                )
                (project_path / "app" / "routes.py").write_text(
                    'from app import app\n\n@app.route("/")\ndef index():\n    return "Hello, World!"\n'
                )
                (project_path / "run.py").write_text(
                    'from app import app\n\nif __name__ == "__main__":\n    app.run(debug=True)\n'
                )
                (project_path / "requirements.txt").write_text("flask>=3.0.0\n")

                return ToolResult(
                    success=True,
                    output=f"Flask project '{name}' created at {project_path}",
                    metadata={"type": "flask", "path": str(project_path)}
                )

            elif project_type == "fastapi":
                # Create FastAPI project structure
                (project_path / "app").mkdir(exist_ok=True)
                (project_path / "app" / "__init__.py").touch()
                (project_path / "app" / "main.py").write_text(
                    'from fastapi import FastAPI\n\napp = FastAPI()\n\n'
                    '@app.get("/")\nasync def root():\n    return {"message": "Hello World"}\n'
                )
                (project_path / "requirements.txt").write_text(
                    "fastapi>=0.109.0\nuvicorn>=0.27.0\n"
                )

                return ToolResult(
                    success=True,
                    output=f"FastAPI project '{name}' created at {project_path}",
                    metadata={"type": "fastapi", "path": str(project_path)}
                )

            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown project type: {project_type}. Supported: node, react, next, vite, python, rust, flask, fastapi"
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of Package tool capabilities."""
        return [
            {"name": "npm_install", "description": "Install npm packages"},
            {"name": "npm_run", "description": "Run npm script"},
            {"name": "pip_install", "description": "Install pip packages"},
            {"name": "pip_freeze", "description": "Freeze pip requirements"},
            {"name": "cargo_build", "description": "Build Rust project"},
            {"name": "cargo_add", "description": "Add Rust dependency"},
            {"name": "brew_install", "description": "Install brew package"},
            {"name": "init_project", "description": "Initialize new project"},
        ]


# Convenience function
def create_package_tools(cwd: Optional[str] = None) -> PackageTools:
    """Create Package tools instance"""
    return PackageTools(default_cwd=cwd)
