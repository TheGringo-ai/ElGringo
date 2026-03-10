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
        # ── Read-only operations (safe, no permission needed) ──
        self.register_operation("projects_list", self._projects_list, "List projects", requires_permission=False)
        self.register_operation("run_services_list", self._run_services_list, "List Cloud Run services", requires_permission=False)
        self.register_operation("run_revisions_list", self._run_revisions_list, "List revisions", requires_permission=False)
        self.register_operation("builds_list", self._builds_list, "List Cloud Build history", requires_permission=False)
        self.register_operation("storage_buckets_list", self._storage_buckets_list, "List storage buckets", requires_permission=False)
        self.register_operation("iam_roles_list", self._iam_roles_list, "List IAM roles", requires_permission=False)
        self.register_operation("secrets_list", self._secrets_list, "List secrets", requires_permission=False)
        self.register_operation("compute_instances_list", self._compute_instances_list, "List VM instances", requires_permission=False)
        self.register_operation("compute_instances_describe", self._compute_instances_describe, "Describe a VM", requires_permission=False)
        self.register_operation("compute_firewall_list", self._compute_firewall_list, "List firewall rules", requires_permission=False)
        self.register_operation("compute_addresses_list", self._compute_addresses_list, "List static IPs", requires_permission=False)
        self.register_operation("compute_disks_list", self._compute_disks_list, "List disks", requires_permission=False)
        self.register_operation("iam_service_accounts_list", self._iam_service_accounts_list, "List service accounts", requires_permission=False)
        self.register_operation("iam_policy_get", self._iam_policy_get, "Get IAM policy", requires_permission=False)
        self.register_operation("networks_list", self._networks_list, "List VPC networks", requires_permission=False)
        self.register_operation("networks_subnets_list", self._networks_subnets_list, "List subnets", requires_permission=False)
        self.register_operation("dns_zones_list", self._dns_zones_list, "List DNS zones", requires_permission=False)
        self.register_operation("dns_record_sets_list", self._dns_record_sets_list, "List DNS records", requires_permission=False)
        self.register_operation("sql_instances_list", self._sql_instances_list, "List Cloud SQL instances", requires_permission=False)
        self.register_operation("sql_instances_describe", self._sql_instances_describe, "Describe SQL instance", requires_permission=False)
        self.register_operation("sql_databases_list", self._sql_databases_list, "List SQL databases", requires_permission=False)
        self.register_operation("logging_read", self._logging_read, "Read cloud logs", requires_permission=False)
        self.register_operation("monitoring_dashboards_list", self._monitoring_dashboards_list, "List dashboards", requires_permission=False)
        self.register_operation("services_list", self._services_list, "List enabled APIs", requires_permission=False)
        self.register_operation("billing_accounts_list", self._billing_accounts_list, "List billing accounts", requires_permission=False)
        self.register_operation("billing_projects_describe", self._billing_projects_describe, "Project billing info", requires_permission=False)
        self.register_operation("artifacts_repositories_list", self._artifacts_repositories_list, "List Artifact Registry repos", requires_permission=False)
        self.register_operation("artifacts_docker_images_list", self._artifacts_docker_images_list, "List Docker images", requires_permission=False)

        # ── Write operations (require permission) ──
        # Cloud Run
        self.register_operation("run_deploy", self._run_deploy, "Deploy to Cloud Run")
        self.register_operation("run_update_traffic", self._run_update_traffic, "Update traffic split")
        self.register_operation("run_services_delete", self._run_services_delete, "Delete Cloud Run service")
        # Cloud Build
        self.register_operation("builds_submit", self._builds_submit, "Submit Cloud Build")
        # Storage
        self.register_operation("storage_cp", self._storage_cp, "Copy to/from Cloud Storage")
        # Secrets
        self.register_operation("secrets_create", self._secrets_create, "Create secret")
        self.register_operation("secrets_versions_add", self._secrets_versions_add, "Add secret version")
        # Compute Engine
        self.register_operation("compute_instances_create", self._compute_instances_create, "Create a VM")
        self.register_operation("compute_instances_stop", self._compute_instances_stop, "Stop a VM")
        self.register_operation("compute_instances_start", self._compute_instances_start, "Start a VM")
        self.register_operation("compute_instances_delete", self._compute_instances_delete, "Delete a VM")
        self.register_operation("compute_ssh", self._compute_ssh, "SSH command on a VM")
        self.register_operation("compute_scp", self._compute_scp, "Copy files to/from VM")
        self.register_operation("compute_firewall_create", self._compute_firewall_create, "Create firewall rule")
        self.register_operation("compute_firewall_delete", self._compute_firewall_delete, "Delete firewall rule")
        self.register_operation("compute_addresses_create", self._compute_addresses_create, "Reserve static IP")
        self.register_operation("compute_snapshots_create", self._compute_snapshots_create, "Create disk snapshot")
        # IAM
        self.register_operation("iam_service_accounts_create", self._iam_service_accounts_create, "Create service account")
        self.register_operation("iam_policy_bindings_add", self._iam_policy_bindings_add, "Grant IAM role")
        self.register_operation("iam_policy_bindings_remove", self._iam_policy_bindings_remove, "Revoke IAM role")
        self.register_operation("iam_service_accounts_keys_create", self._iam_service_accounts_keys_create, "Create SA key")
        # Services
        self.register_operation("services_enable", self._services_enable, "Enable a GCP API")
        self.register_operation("services_disable", self._services_disable, "Disable a GCP API")

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

    # ── Compute Engine ──────────────────────────────────────────────
    def _compute_instances_list(self, zone: Optional[str] = None) -> ToolResult:
        args = ["compute", "instances", "list"]
        if zone:
            args.extend(["--zones", zone])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _compute_instances_describe(self, instance: str, zone: str) -> ToolResult:
        args = ["compute", "instances", "describe", instance, "--zone", zone]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _compute_instances_create(
        self, name: str, zone: str, machine_type: str = "e2-medium",
        image_family: str = "debian-12", image_project: str = "debian-cloud",
        disk_size: str = "20GB", tags: Optional[List[str]] = None,
        startup_script: Optional[str] = None,
    ) -> ToolResult:
        args = ["compute", "instances", "create", name, "--zone", zone,
                "--machine-type", machine_type,
                f"--image-family={image_family}", f"--image-project={image_project}",
                f"--boot-disk-size={disk_size}"]
        if tags:
            args.extend(["--tags", ",".join(tags)])
        if startup_script:
            args.extend(["--metadata", f"startup-script={startup_script}"])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=120))

    def _compute_instances_stop(self, instance: str, zone: str) -> ToolResult:
        args = ["compute", "instances", "stop", instance, "--zone", zone, "--quiet"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=120))

    def _compute_instances_start(self, instance: str, zone: str) -> ToolResult:
        args = ["compute", "instances", "start", instance, "--zone", zone]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=120))

    def _compute_instances_delete(self, instance: str, zone: str) -> ToolResult:
        args = ["compute", "instances", "delete", instance, "--zone", zone, "--quiet"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=120))

    def _compute_ssh(self, instance: str, zone: str, command: str) -> ToolResult:
        args = ["compute", "ssh", instance, "--zone", zone, "--command", command, "--quiet"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=120))

    def _compute_scp(self, source: str, destination: str, zone: str) -> ToolResult:
        args = ["compute", "scp", source, destination, "--zone", zone, "--quiet"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=120))

    def _compute_firewall_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["compute", "firewall-rules", "list"]))

    def _compute_firewall_create(
        self, name: str, allow: str, source_ranges: str = "0.0.0.0/0",
        target_tags: Optional[str] = None, description: Optional[str] = None,
    ) -> ToolResult:
        args = ["compute", "firewall-rules", "create", name,
                f"--allow={allow}", f"--source-ranges={source_ranges}"]
        if target_tags:
            args.extend([f"--target-tags={target_tags}"])
        if description:
            args.extend([f"--description={description}"])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _compute_firewall_delete(self, name: str) -> ToolResult:
        args = ["compute", "firewall-rules", "delete", name, "--quiet"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _compute_addresses_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["compute", "addresses", "list"]))

    def _compute_addresses_create(self, name: str, region: Optional[str] = None) -> ToolResult:
        args = ["compute", "addresses", "create", name, "--region", region or self.region]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _compute_disks_list(self, zone: Optional[str] = None) -> ToolResult:
        args = ["compute", "disks", "list"]
        if zone:
            args.extend(["--zones", zone])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _compute_snapshots_create(self, disk: str, zone: str, name: str) -> ToolResult:
        args = ["compute", "disks", "snapshot", disk, "--zone", zone, f"--snapshot-names={name}"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    # ── IAM & Service Accounts ───────────────────────────────────────
    def _iam_service_accounts_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["iam", "service-accounts", "list"]))

    def _iam_service_accounts_create(self, name: str, display_name: Optional[str] = None) -> ToolResult:
        args = ["iam", "service-accounts", "create", name]
        if display_name:
            args.extend([f"--display-name={display_name}"])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _iam_policy_bindings_add(self, member: str, role: str) -> ToolResult:
        args = ["projects", "add-iam-policy-binding", self.project,
                f"--member={member}", f"--role={role}"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _iam_policy_bindings_remove(self, member: str, role: str) -> ToolResult:
        args = ["projects", "remove-iam-policy-binding", self.project,
                f"--member={member}", f"--role={role}"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _iam_policy_get(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["projects", "get-iam-policy", self.project]))

    def _iam_service_accounts_keys_create(self, sa_email: str, output_file: str) -> ToolResult:
        args = ["iam", "service-accounts", "keys", "create", output_file,
                f"--iam-account={sa_email}"]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    # ── Networking (VPC, Subnets, DNS) ───────────────────────────────
    def _networks_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["compute", "networks", "list"]))

    def _networks_subnets_list(self, region: Optional[str] = None) -> ToolResult:
        args = ["compute", "networks", "subnets", "list"]
        if region:
            args.extend(["--regions", region])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _dns_zones_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["dns", "managed-zones", "list"]))

    def _dns_record_sets_list(self, zone: str) -> ToolResult:
        args = ["dns", "record-sets", "list", "--zone", zone]
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    # ── Cloud SQL ────────────────────────────────────────────────────
    def _sql_instances_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["sql", "instances", "list"]))

    def _sql_instances_describe(self, instance: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["sql", "instances", "describe", instance]))

    def _sql_databases_list(self, instance: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["sql", "databases", "list", "--instance", instance]))

    # ── Logging & Monitoring ─────────────────────────────────────────
    def _logging_read(self, log_filter: str = "", limit: int = 50) -> ToolResult:
        args = ["logging", "read", f"--limit={limit}"]
        if log_filter:
            args.append(log_filter)
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args, timeout=60))

    def _monitoring_dashboards_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["monitoring", "dashboards", "list"]))

    # ── Services & APIs ──────────────────────────────────────────────
    def _services_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["services", "list", "--enabled"]))

    def _services_enable(self, service: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["services", "enable", service]))

    def _services_disable(self, service: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["services", "disable", service, "--quiet"]))

    # ── Billing ──────────────────────────────────────────────────────
    def _billing_accounts_list(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["billing", "accounts", "list"]))

    def _billing_projects_describe(self) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["billing", "projects", "describe", self.project]))

    # ── Artifact Registry / Container Registry ───────────────────────
    def _artifacts_repositories_list(self, location: Optional[str] = None) -> ToolResult:
        args = ["artifacts", "repositories", "list"]
        if location:
            args.extend(["--location", location])
        return asyncio.get_event_loop().run_until_complete(self._run_gcloud(args))

    def _artifacts_docker_images_list(self, repository: str) -> ToolResult:
        return asyncio.get_event_loop().run_until_complete(
            self._run_gcloud(["artifacts", "docker", "images", "list", repository]))

    def get_capabilities(self) -> List[Dict[str, str]]:
        return [
            # Compute Engine
            {"operation": "compute_instances_list", "description": "List all VM instances"},
            {"operation": "compute_instances_describe", "description": "Get VM details (CPU, RAM, IP, status)"},
            {"operation": "compute_instances_create", "description": "Create a new VM instance"},
            {"operation": "compute_instances_stop", "description": "Stop a VM instance"},
            {"operation": "compute_instances_start", "description": "Start a VM instance"},
            {"operation": "compute_instances_delete", "description": "Delete a VM instance"},
            {"operation": "compute_ssh", "description": "Run a command on a VM via SSH"},
            {"operation": "compute_scp", "description": "Copy files to/from a VM"},
            {"operation": "compute_firewall_list", "description": "List firewall rules"},
            {"operation": "compute_firewall_create", "description": "Create a firewall rule"},
            {"operation": "compute_firewall_delete", "description": "Delete a firewall rule"},
            {"operation": "compute_addresses_list", "description": "List static IP addresses"},
            {"operation": "compute_addresses_create", "description": "Reserve a static IP"},
            {"operation": "compute_disks_list", "description": "List persistent disks"},
            {"operation": "compute_snapshots_create", "description": "Create a disk snapshot"},
            # Cloud Run
            {"operation": "projects_list", "description": "List GCP projects"},
            {"operation": "run_services_list", "description": "List Cloud Run services"},
            {"operation": "run_deploy", "description": "Deploy to Cloud Run"},
            {"operation": "run_update_traffic", "description": "Update Cloud Run traffic split"},
            {"operation": "run_services_delete", "description": "Delete a Cloud Run service"},
            # Cloud Build
            {"operation": "builds_list", "description": "List Cloud Build history"},
            {"operation": "builds_submit", "description": "Submit a Cloud Build"},
            # Cloud Storage
            {"operation": "storage_buckets_list", "description": "List storage buckets"},
            {"operation": "storage_cp", "description": "Copy to/from Cloud Storage"},
            # IAM & Security
            {"operation": "iam_roles_list", "description": "List IAM roles in project"},
            {"operation": "iam_service_accounts_list", "description": "List service accounts"},
            {"operation": "iam_service_accounts_create", "description": "Create a service account"},
            {"operation": "iam_policy_bindings_add", "description": "Grant IAM role to a member"},
            {"operation": "iam_policy_bindings_remove", "description": "Revoke IAM role from a member"},
            {"operation": "iam_policy_get", "description": "Get project IAM policy"},
            {"operation": "iam_service_accounts_keys_create", "description": "Create SA key file"},
            # Secrets
            {"operation": "secrets_list", "description": "List Secret Manager secrets"},
            {"operation": "secrets_create", "description": "Create a new secret"},
            {"operation": "secrets_versions_add", "description": "Add a secret version"},
            # Networking
            {"operation": "networks_list", "description": "List VPC networks"},
            {"operation": "networks_subnets_list", "description": "List subnets"},
            {"operation": "dns_zones_list", "description": "List DNS managed zones"},
            {"operation": "dns_record_sets_list", "description": "List DNS records in a zone"},
            # Cloud SQL
            {"operation": "sql_instances_list", "description": "List Cloud SQL instances"},
            {"operation": "sql_instances_describe", "description": "Describe a Cloud SQL instance"},
            {"operation": "sql_databases_list", "description": "List databases in a SQL instance"},
            # Logging & Monitoring
            {"operation": "logging_read", "description": "Read cloud logs (with filter)"},
            {"operation": "monitoring_dashboards_list", "description": "List monitoring dashboards"},
            # Services & APIs
            {"operation": "services_list", "description": "List enabled APIs/services"},
            {"operation": "services_enable", "description": "Enable a GCP API/service"},
            {"operation": "services_disable", "description": "Disable a GCP API/service"},
            # Billing
            {"operation": "billing_accounts_list", "description": "List billing accounts"},
            {"operation": "billing_projects_describe", "description": "Get project billing info"},
            # Artifacts
            {"operation": "artifacts_repositories_list", "description": "List Artifact Registry repos"},
            {"operation": "artifacts_docker_images_list", "description": "List Docker images in a repo"},
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
