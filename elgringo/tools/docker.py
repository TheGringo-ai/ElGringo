"""
Docker Tools - Container operations for AI agents
==================================================

Capabilities:
- Image management (build, pull, push, list)
- Container operations (run, stop, logs, exec)
- Docker Compose (up, down, logs)
- Registry operations
- Cleanup and maintenance
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class DockerTools(Tool):
    """
    Docker container management tools.

    Enables AI agents to build, run, and manage containers
    for local development and deployment.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_cwd: Optional[str] = None
    ):
        super().__init__(
            name="docker",
            description="Docker container operations",
            permission_manager=permission_manager,
        )

        self.default_cwd = default_cwd or os.getcwd()

        # Register operations
        # Image operations
        self.register_operation("build", self._build, "Build Docker image")
        self.register_operation("pull", self._pull, "Pull image from registry")
        self.register_operation("push", self._push, "Push image to registry")
        self.register_operation("images", self._list_images, "List images", requires_permission=False)
        self.register_operation("rmi", self._remove_image, "Remove image")

        # Container operations
        self.register_operation("run", self._run, "Run container")
        self.register_operation("start", self._start, "Start stopped container")
        self.register_operation("stop", self._stop, "Stop running container")
        self.register_operation("restart", self._restart, "Restart container")
        self.register_operation("rm", self._remove_container, "Remove container")
        self.register_operation("ps", self._list_containers, "List containers", requires_permission=False)
        self.register_operation("logs", self._logs, "View container logs", requires_permission=False)
        self.register_operation("exec", self._exec, "Execute command in container")
        self.register_operation("inspect", self._inspect, "Inspect container/image", requires_permission=False)

        # Compose operations
        self.register_operation("compose_up", self._compose_up, "Start compose services")
        self.register_operation("compose_down", self._compose_down, "Stop compose services")
        self.register_operation("compose_logs", self._compose_logs, "View compose logs", requires_permission=False)
        self.register_operation("compose_ps", self._compose_ps, "List compose services", requires_permission=False)
        self.register_operation("compose_build", self._compose_build, "Build compose services")

        # Maintenance
        self.register_operation("prune", self._prune, "Clean up unused resources")
        self.register_operation("system_df", self._system_df, "Show disk usage", requires_permission=False)

    async def _run_docker(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: int = 300
    ) -> ToolResult:
        """Execute a docker command"""
        try:
            cmd = ["docker"] + args
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
                    metadata={"command": " ".join(cmd)}
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"Docker command failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"Docker command timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="Docker not found. Is Docker Desktop running?")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # Image operations
    def _build(
        self,
        tag: str,
        dockerfile: str = "Dockerfile",
        context: str = ".",
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Build Docker image"""
        args = ["build", "-t", tag, "-f", dockerfile]
        if no_cache:
            args.append("--no-cache")
        if build_args:
            for key, value in build_args.items():
                args.extend(["--build-arg", f"{key}={value}"])
        args.append(context)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args, cwd, timeout=600)  # 10 min for builds
        )

    def _pull(self, image: str) -> ToolResult:
        """Pull image from registry"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["pull", image], timeout=300)
        )

    def _push(self, image: str) -> ToolResult:
        """Push image to registry"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["push", image], timeout=300)
        )

    def _list_images(self, all_images: bool = False) -> ToolResult:
        """List Docker images"""
        args = ["images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"]
        if all_images:
            args.insert(1, "-a")
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    def _remove_image(self, image: str, force: bool = False) -> ToolResult:
        """Remove Docker image"""
        args = ["rmi"]
        if force:
            args.append("-f")
        args.append(image)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    # Container operations
    def _run(
        self,
        image: str,
        name: Optional[str] = None,
        ports: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
        detach: bool = True,
        rm: bool = False,
        command: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Run Docker container"""
        args = ["run"]
        if detach:
            args.append("-d")
        if rm:
            args.append("--rm")
        if name:
            args.extend(["--name", name])
        if ports:
            for host_port, container_port in ports.items():
                args.extend(["-p", f"{host_port}:{container_port}"])
        if volumes:
            for host_path, container_path in volumes.items():
                args.extend(["-v", f"{host_path}:{container_path}"])
        if env:
            for key, value in env.items():
                args.extend(["-e", f"{key}={value}"])
        args.append(image)
        if command:
            args.extend(command.split())
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args, cwd)
        )

    def _start(self, container: str) -> ToolResult:
        """Start stopped container"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["start", container])
        )

    def _stop(self, container: str, timeout: int = 10) -> ToolResult:
        """Stop running container"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["stop", "-t", str(timeout), container])
        )

    def _restart(self, container: str) -> ToolResult:
        """Restart container"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["restart", container])
        )

    def _remove_container(self, container: str, force: bool = False, volumes: bool = False) -> ToolResult:
        """Remove container"""
        args = ["rm"]
        if force:
            args.append("-f")
        if volumes:
            args.append("-v")
        args.append(container)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    def _list_containers(self, all_containers: bool = False) -> ToolResult:
        """List containers"""
        args = ["ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
        if all_containers:
            args.insert(1, "-a")
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    def _logs(
        self,
        container: str,
        tail: int = 100,
        follow: bool = False,
        timestamps: bool = False
    ) -> ToolResult:
        """View container logs"""
        args = ["logs", "--tail", str(tail)]
        if timestamps:
            args.append("-t")
        # Note: follow (-f) not practical in automated context
        args.append(container)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    def _exec(
        self,
        container: str,
        command: str,
        interactive: bool = False,
        tty: bool = False,
        workdir: Optional[str] = None
    ) -> ToolResult:
        """Execute command in container"""
        args = ["exec"]
        if interactive:
            args.append("-i")
        if tty:
            args.append("-t")
        if workdir:
            args.extend(["-w", workdir])
        args.append(container)
        args.extend(command.split())
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    def _inspect(self, target: str, format_str: Optional[str] = None) -> ToolResult:
        """Inspect container or image"""
        args = ["inspect"]
        if format_str:
            args.extend(["--format", format_str])
        args.append(target)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    # Docker Compose operations
    def _compose_up(
        self,
        services: Optional[List[str]] = None,
        detach: bool = True,
        build: bool = False,
        file: str = "docker-compose.yml",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Start compose services"""
        args = ["compose", "-f", file, "up"]
        if detach:
            args.append("-d")
        if build:
            args.append("--build")
        if services:
            args.extend(services)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args, cwd, timeout=600)
        )

    def _compose_down(
        self,
        volumes: bool = False,
        rmi: Optional[str] = None,
        file: str = "docker-compose.yml",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Stop compose services"""
        args = ["compose", "-f", file, "down"]
        if volumes:
            args.append("-v")
        if rmi:
            args.extend(["--rmi", rmi])
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args, cwd)
        )

    def _compose_logs(
        self,
        services: Optional[List[str]] = None,
        tail: int = 100,
        file: str = "docker-compose.yml",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """View compose logs"""
        args = ["compose", "-f", file, "logs", "--tail", str(tail)]
        if services:
            args.extend(services)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args, cwd)
        )

    def _compose_ps(
        self,
        file: str = "docker-compose.yml",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """List compose services"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["compose", "-f", file, "ps"], cwd)
        )

    def _compose_build(
        self,
        services: Optional[List[str]] = None,
        no_cache: bool = False,
        file: str = "docker-compose.yml",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Build compose services"""
        args = ["compose", "-f", file, "build"]
        if no_cache:
            args.append("--no-cache")
        if services:
            args.extend(services)
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args, cwd, timeout=600)
        )

    # Maintenance
    def _prune(
        self,
        all_unused: bool = False,
        volumes: bool = False,
        force: bool = True
    ) -> ToolResult:
        """Clean up unused Docker resources"""
        args = ["system", "prune"]
        if force:
            args.append("-f")
        if all_unused:
            args.append("-a")
        if volumes:
            args.append("--volumes")
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(args)
        )

    def _system_df(self) -> ToolResult:
        """Show Docker disk usage"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_docker(["system", "df"])
        )


    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of Docker tool capabilities."""
        return [
            {"name": "build", "description": "Build Docker image"},
            {"name": "run", "description": "Run container"},
            {"name": "ps", "description": "List containers"},
            {"name": "logs", "description": "View container logs"},
            {"name": "exec", "description": "Execute command in container"},
            {"name": "compose_up", "description": "Start compose services"},
            {"name": "compose_down", "description": "Stop compose services"},
            {"name": "prune", "description": "Clean up unused resources"},
        ]


# Convenience function
def create_docker_tools(cwd: Optional[str] = None) -> DockerTools:
    """Create Docker tools instance"""
    return DockerTools(default_cwd=cwd)
