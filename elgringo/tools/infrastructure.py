"""
Infrastructure Tools - Kubernetes, Terraform, GCP Operations
=============================================================

Capabilities:
- Kubernetes cluster management (kubectl)
- Terraform infrastructure as code
- GCP-specific operations (gcloud)
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class KubernetesTools(Tool):
    """
    Kubernetes cluster management tools.

    Provides kubectl operations for managing:
    - Pods, deployments, services
    - ConfigMaps, Secrets
    - Namespaces
    - Logs and debugging
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        kubeconfig: Optional[str] = None,
        context: Optional[str] = None,
        namespace: str = "default"
    ):
        super().__init__(
            name="kubernetes",
            description="Kubernetes cluster operations via kubectl",
            permission_manager=permission_manager,
        )

        self.kubeconfig = kubeconfig or os.getenv("KUBECONFIG")
        self.context = context
        self.namespace = namespace

        # Register operations
        # Read operations (safe)
        self.register_operation("get_pods", self._get_pods, "List pods", requires_permission=False)
        self.register_operation("get_deployments", self._get_deployments, "List deployments", requires_permission=False)
        self.register_operation("get_services", self._get_services, "List services", requires_permission=False)
        self.register_operation("get_namespaces", self._get_namespaces, "List namespaces", requires_permission=False)
        self.register_operation("describe", self._describe, "Describe resource", requires_permission=False)
        self.register_operation("logs", self._logs, "Get pod logs", requires_permission=False)
        self.register_operation("get_configmaps", self._get_configmaps, "List ConfigMaps", requires_permission=False)
        self.register_operation("get_secrets", self._get_secrets, "List Secrets (names only)", requires_permission=False)

        # Write operations (require permission)
        self.register_operation("apply", self._apply, "Apply manifest")
        self.register_operation("delete", self._delete, "Delete resource")
        self.register_operation("scale", self._scale, "Scale deployment")
        self.register_operation("rollout_restart", self._rollout_restart, "Restart deployment")
        self.register_operation("exec", self._exec, "Execute command in pod")
        self.register_operation("port_forward", self._port_forward, "Port forward to pod")
        self.register_operation("create_namespace", self._create_namespace, "Create namespace")
        self.register_operation("set_context", self._set_context, "Set kubectl context")

    async def _run_kubectl(
        self,
        args: List[str],
        timeout: int = 60
    ) -> ToolResult:
        """Execute a kubectl command"""
        try:
            cmd = ["kubectl"]

            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            if self.context:
                cmd.extend(["--context", self.context])
            if self.namespace and "-n" not in args and "--namespace" not in args and "--all-namespaces" not in args:
                cmd.extend(["-n", self.namespace])

            cmd.extend(args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
                    output=stdout_str,
                    metadata={"command": " ".join(cmd)}
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"kubectl failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"kubectl timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="kubectl not found. Install kubectl.")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # Read operations
    def _get_pods(self, namespace: Optional[str] = None, all_namespaces: bool = False) -> ToolResult:
        args = ["get", "pods", "-o", "wide"]
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _get_deployments(self, namespace: Optional[str] = None) -> ToolResult:
        args = ["get", "deployments", "-o", "wide"]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _get_services(self, namespace: Optional[str] = None) -> ToolResult:
        args = ["get", "services", "-o", "wide"]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _get_namespaces(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_kubectl(["get", "namespaces"])
        )

    def _describe(self, resource_type: str, name: str, namespace: Optional[str] = None) -> ToolResult:
        args = ["describe", resource_type, name]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _logs(
        self,
        pod: str,
        container: Optional[str] = None,
        tail: int = 100,
        follow: bool = False,
        namespace: Optional[str] = None
    ) -> ToolResult:
        args = ["logs", pod, f"--tail={tail}"]
        if container:
            args.extend(["-c", container])
        if namespace:
            args.extend(["-n", namespace])
        # Note: follow not practical in automated context
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _get_configmaps(self, namespace: Optional[str] = None) -> ToolResult:
        args = ["get", "configmaps"]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _get_secrets(self, namespace: Optional[str] = None) -> ToolResult:
        """List secrets (names only for security)"""
        args = ["get", "secrets", "-o", "custom-columns=NAME:.metadata.name,TYPE:.type"]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    # Write operations
    def _apply(self, manifest: str, namespace: Optional[str] = None) -> ToolResult:
        """Apply a YAML manifest"""
        args = ["apply", "-f", "-"]
        if namespace:
            args.extend(["-n", namespace])
        # For stdin input, we need a different approach
        return asyncio.get_event_loop().run_until_complete(
            self._run_kubectl_stdin(args, manifest)
        )

    async def _run_kubectl_stdin(self, args: List[str], stdin_data: str) -> ToolResult:
        """Execute kubectl with stdin input"""
        try:
            cmd = ["kubectl"]
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])
            if self.context:
                cmd.extend(["--context", self.context])
            cmd.extend(args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_data.encode()),
                timeout=60
            )

            if process.returncode == 0:
                return ToolResult(success=True, output=stdout.decode().strip())
            else:
                return ToolResult(success=False, output=None, error=stderr.decode().strip())

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _delete(
        self,
        resource_type: str,
        name: str,
        namespace: Optional[str] = None,
        force: bool = False
    ) -> ToolResult:
        args = ["delete", resource_type, name]
        if namespace:
            args.extend(["-n", namespace])
        if force:
            args.append("--force")
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _scale(self, deployment: str, replicas: int, namespace: Optional[str] = None) -> ToolResult:
        args = ["scale", f"deployment/{deployment}", f"--replicas={replicas}"]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _rollout_restart(self, deployment: str, namespace: Optional[str] = None) -> ToolResult:
        args = ["rollout", "restart", f"deployment/{deployment}"]
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args))

    def _exec(
        self,
        pod: str,
        command: str,
        container: Optional[str] = None,
        namespace: Optional[str] = None
    ) -> ToolResult:
        args = ["exec", pod, "--", *command.split()]
        if container:
            args.insert(2, "-c")
            args.insert(3, container)
        if namespace:
            args.extend(["-n", namespace])
        return asyncio.get_event_loop().run_until_complete(self._run_kubectl(args, timeout=120))

    def _port_forward(
        self,
        pod: str,
        local_port: int,
        pod_port: int,
        namespace: Optional[str] = None
    ) -> ToolResult:
        """Note: This starts port forwarding but returns immediately"""
        args = ["port-forward", pod, f"{local_port}:{pod_port}"]
        if namespace:
            args.extend(["-n", namespace])
        # Return info about how to start, don't actually run in background
        return ToolResult(
            success=True,
            output=f"Run: kubectl {' '.join(args)}",
            metadata={"local_port": local_port, "pod_port": pod_port}
        )

    def _create_namespace(self, name: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_kubectl(["create", "namespace", name])
        )

    def _set_context(self, context: str) -> ToolResult:
        self.context = context
        return asyncio.get_event_loop().run_until_complete(
            self._run_kubectl(["config", "use-context", context])
        )

    def get_capabilities(self) -> List[Dict[str, str]]:
        return [
            {"operation": "get_pods", "description": "List pods in cluster"},
            {"operation": "get_deployments", "description": "List deployments"},
            {"operation": "get_services", "description": "List services"},
            {"operation": "logs", "description": "Get pod logs"},
            {"operation": "apply", "description": "Apply Kubernetes manifest"},
            {"operation": "scale", "description": "Scale deployment replicas"},
            {"operation": "rollout_restart", "description": "Restart deployment"},
            {"operation": "exec", "description": "Execute command in pod"},
        ]


class TerraformTools(Tool):
    """
    Terraform infrastructure as code tools.

    Provides operations for:
    - Plan and apply infrastructure
    - State management
    - Module management
    - Workspace management
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        working_dir: Optional[str] = None,
        var_file: Optional[str] = None
    ):
        super().__init__(
            name="terraform",
            description="Terraform infrastructure as code operations",
            permission_manager=permission_manager,
        )

        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.var_file = var_file

        # Register operations
        # Safe operations
        self.register_operation("init", self._init, "Initialize Terraform", requires_permission=False)
        self.register_operation("validate", self._validate, "Validate configuration", requires_permission=False)
        self.register_operation("plan", self._plan, "Generate execution plan", requires_permission=False)
        self.register_operation("show", self._show, "Show state", requires_permission=False)
        self.register_operation("output", self._output, "Show outputs", requires_permission=False)
        self.register_operation("state_list", self._state_list, "List resources in state", requires_permission=False)
        self.register_operation("workspace_list", self._workspace_list, "List workspaces", requires_permission=False)
        self.register_operation("fmt", self._fmt, "Format configuration", requires_permission=False)

        # Dangerous operations
        self.register_operation("apply", self._apply, "Apply changes")
        self.register_operation("destroy", self._destroy, "Destroy infrastructure")
        self.register_operation("import_resource", self._import, "Import existing resource")
        self.register_operation("workspace_new", self._workspace_new, "Create workspace")
        self.register_operation("workspace_select", self._workspace_select, "Select workspace")
        self.register_operation("state_rm", self._state_rm, "Remove from state")

    async def _run_terraform(
        self,
        args: List[str],
        timeout: int = 300,
        auto_approve: bool = False
    ) -> ToolResult:
        """Execute a terraform command"""
        try:
            cmd = ["terraform"] + args

            if self.var_file and "-var-file" not in " ".join(args):
                cmd.extend(["-var-file", self.var_file])

            if auto_approve and args[0] in ["apply", "destroy"]:
                cmd.append("-auto-approve")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
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
                    error=stderr_str or f"terraform failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"terraform timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="terraform not found. Install Terraform.")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # Operations
    def _init(self, upgrade: bool = False) -> ToolResult:
        args = ["init"]
        if upgrade:
            args.append("-upgrade")
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(args))

    def _validate(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(["validate"]))

    def _plan(self, out: Optional[str] = None, target: Optional[str] = None) -> ToolResult:
        args = ["plan"]
        if out:
            args.extend(["-out", out])
        if target:
            args.extend(["-target", target])
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(args))

    def _apply(self, plan_file: Optional[str] = None, target: Optional[str] = None) -> ToolResult:
        args = ["apply"]
        if plan_file:
            args.append(plan_file)
        if target:
            args.extend(["-target", target])
        return asyncio.get_event_loop().run_until_complete(
            self._run_terraform(args, timeout=600, auto_approve=True)
        )

    def _destroy(self, target: Optional[str] = None) -> ToolResult:
        args = ["destroy"]
        if target:
            args.extend(["-target", target])
        return asyncio.get_event_loop().run_until_complete(
            self._run_terraform(args, timeout=600, auto_approve=True)
        )

    def _show(self, plan_file: Optional[str] = None) -> ToolResult:
        args = ["show"]
        if plan_file:
            args.append(plan_file)
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(args))

    def _output(self, name: Optional[str] = None, json_format: bool = False) -> ToolResult:
        args = ["output"]
        if json_format:
            args.append("-json")
        if name:
            args.append(name)
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(args))

    def _state_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(["state", "list"]))

    def _state_rm(self, address: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_terraform(["state", "rm", address])
        )

    def _import(self, address: str, resource_id: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_terraform(["import", address, resource_id])
        )

    def _workspace_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(["workspace", "list"]))

    def _workspace_new(self, name: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_terraform(["workspace", "new", name])
        )

    def _workspace_select(self, name: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_terraform(["workspace", "select", name])
        )

    def _fmt(self, check: bool = False, recursive: bool = True) -> ToolResult:
        args = ["fmt"]
        if check:
            args.append("-check")
        if recursive:
            args.append("-recursive")
        return asyncio.get_event_loop().run_until_complete(self._run_terraform(args))

    def get_capabilities(self) -> List[Dict[str, str]]:
        return [
            {"operation": "init", "description": "Initialize Terraform working directory"},
            {"operation": "validate", "description": "Validate configuration files"},
            {"operation": "plan", "description": "Generate execution plan"},
            {"operation": "apply", "description": "Apply infrastructure changes"},
            {"operation": "destroy", "description": "Destroy managed infrastructure"},
            {"operation": "output", "description": "Show output values"},
            {"operation": "state_list", "description": "List resources in state"},
            {"operation": "workspace_list", "description": "List workspaces"},
        ]


class GCPTools(Tool):
    """
    Google Cloud Platform tools via gcloud CLI.

    Provides operations for:
    - Cloud Run deployments
    - Cloud Build
    - Cloud Storage
    - IAM management
    - Project management
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        project: Optional[str] = None,
        region: str = "us-central1"
    ):
        super().__init__(
            name="gcp",
            description="Google Cloud Platform operations via gcloud",
            permission_manager=permission_manager,
        )

        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region

        # Register operations
        # Info operations (safe)
        self.register_operation("projects_list", self._projects_list, "List projects", requires_permission=False)
        self.register_operation("run_services_list", self._run_services_list, "List Cloud Run services", requires_permission=False)
        self.register_operation("run_revisions_list", self._run_revisions_list, "List revisions", requires_permission=False)
        self.register_operation("builds_list", self._builds_list, "List Cloud Build history", requires_permission=False)
        self.register_operation("storage_buckets_list", self._storage_buckets_list, "List storage buckets", requires_permission=False)
        self.register_operation("iam_roles_list", self._iam_roles_list, "List IAM roles", requires_permission=False)
        self.register_operation("secrets_list", self._secrets_list, "List secrets", requires_permission=False)

        # Action operations (require permission)
        self.register_operation("run_deploy", self._run_deploy, "Deploy to Cloud Run")
        self.register_operation("run_update_traffic", self._run_update_traffic, "Update traffic split")
        self.register_operation("builds_submit", self._builds_submit, "Submit Cloud Build")
        self.register_operation("storage_cp", self._storage_cp, "Copy to/from Cloud Storage")
        self.register_operation("secrets_create", self._secrets_create, "Create secret")
        self.register_operation("secrets_versions_add", self._secrets_versions_add, "Add secret version")
        self.register_operation("run_services_delete", self._run_services_delete, "Delete Cloud Run service")

    async def _run_gcloud(
        self,
        args: List[str],
        timeout: int = 300
    ) -> ToolResult:
        """Execute a gcloud command"""
        try:
            cmd = ["gcloud"] + args

            if self.project and "--project" not in " ".join(args):
                cmd.extend(["--project", self.project])

            # Add format json where applicable
            if args[0] not in ["auth", "config"] and "--format" not in " ".join(args):
                cmd.extend(["--format", "json"])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            if process.returncode == 0:
                # Try to parse JSON output
                try:
                    output = json.loads(stdout_str) if stdout_str else None
                except json.JSONDecodeError:
                    output = stdout_str

                return ToolResult(
                    success=True,
                    output=output,
                    metadata={"command": " ".join(cmd)}
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"gcloud failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"gcloud timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="gcloud not found. Install Google Cloud SDK.")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # Info operations
    def _projects_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["projects", "list"])
        )

    def _run_services_list(self, region: Optional[str] = None) -> ToolResult:
        args = ["run", "services", "list", "--region", region or self.region]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _run_revisions_list(self, service: str, region: Optional[str] = None) -> ToolResult:
        args = ["run", "revisions", "list", "--service", service, "--region", region or self.region]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _builds_list(self, limit: int = 10) -> ToolResult:
        args = ["builds", "list", f"--limit={limit}"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _storage_buckets_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["storage", "buckets", "list"])
        )

    def _iam_roles_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["iam", "roles", "list", "--project", self.project])
        )

    def _secrets_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["secrets", "list"])
        )

    # Action operations
    def _run_deploy(
        self,
        service: str,
        image: Optional[str] = None,
        source: Optional[str] = None,
        region: Optional[str] = None,
        memory: str = "512Mi",
        cpu: str = "1",
        min_instances: int = 0,
        max_instances: int = 100,
        allow_unauthenticated: bool = False,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        args = ["run", "deploy", service, "--region", region or self.region]

        if image:
            args.extend(["--image", image])
        elif source:
            args.extend(["--source", source])

        args.extend([
            "--memory", memory,
            "--cpu", cpu,
            f"--min-instances={min_instances}",
            f"--max-instances={max_instances}",
        ])

        if allow_unauthenticated:
            args.append("--allow-unauthenticated")

        if env_vars:
            env_str = ",".join(f"{k}={v}" for k, v in env_vars.items())
            args.extend(["--set-env-vars", env_str])

        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(args, timeout=600)
        )

    def _run_update_traffic(
        self,
        service: str,
        revisions: Dict[str, int],  # {revision_name: percentage}
        region: Optional[str] = None
    ) -> ToolResult:
        traffic_str = ",".join(f"{k}={v}" for k, v in revisions.items())
        args = ["run", "services", "update-traffic", service,
                "--to-revisions", traffic_str,
                "--region", region or self.region]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _builds_submit(
        self,
        source: str = ".",
        tag: Optional[str] = None,
        config: Optional[str] = None
    ) -> ToolResult:
        args = ["builds", "submit", source]
        if tag:
            args.extend(["--tag", tag])
        if config:
            args.extend(["--config", config])
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(args, timeout=600)
        )

    def _storage_cp(self, source: str, destination: str, recursive: bool = False) -> ToolResult:
        args = ["storage", "cp"]
        if recursive:
            args.append("-r")
        args.extend([source, destination])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _secrets_create(self, secret_id: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["secrets", "create", secret_id, "--replication-policy=automatic"])
        )

    def _secrets_versions_add(self, secret_id: str, data: str) -> ToolResult:
        # Use stdin for secret data
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud_stdin(
                ["secrets", "versions", "add", secret_id, "--data-file=-"],
                data
            )
        )

    async def _run_gcloud_stdin(self, args: List[str], stdin_data: str) -> ToolResult:
        """Execute gcloud with stdin input"""
        try:
            cmd = ["gcloud"] + args
            if self.project:
                cmd.extend(["--project", self.project])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_data.encode()),
                timeout=60
            )

            if process.returncode == 0:
                return ToolResult(success=True, output=stdout.decode().strip())
            else:
                return ToolResult(success=False, output=None, error=stderr.decode().strip())

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _run_services_delete(self, service: str, region: Optional[str] = None) -> ToolResult:
        args = ["run", "services", "delete", service, "--region", region or self.region, "--quiet"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def get_capabilities(self) -> List[Dict[str, str]]:
        return [
            {"operation": "projects_list", "description": "List GCP projects"},
            {"operation": "run_services_list", "description": "List Cloud Run services"},
            {"operation": "run_deploy", "description": "Deploy to Cloud Run"},
            {"operation": "builds_submit", "description": "Submit Cloud Build"},
            {"operation": "storage_cp", "description": "Copy to/from Cloud Storage"},
            {"operation": "secrets_list", "description": "List Secret Manager secrets"},
            {"operation": "secrets_create", "description": "Create a new secret"},
        ]


# Convenience functions
def create_kubernetes_tools(
    kubeconfig: Optional[str] = None,
    context: Optional[str] = None,
    namespace: str = "default"
) -> KubernetesTools:
    """Create Kubernetes tools instance"""
    return KubernetesTools(kubeconfig=kubeconfig, context=context, namespace=namespace)


def create_terraform_tools(
    working_dir: Optional[str] = None,
    var_file: Optional[str] = None
) -> TerraformTools:
    """Create Terraform tools instance"""
    return TerraformTools(working_dir=working_dir, var_file=var_file)


def create_gcp_tools(
    project: Optional[str] = None,
    region: str = "us-central1"
) -> GCPTools:
    """Create GCP tools instance"""
    return GCPTools(project=project, region=region)
