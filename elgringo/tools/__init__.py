"""
AI Agent Tools - Extend agent capabilities
==========================================

Complete toolkit for AI-powered development:
- FileSystem: Read, write, execute files
- Browser: Web automation, scraping, search
- Shell: Execute shell commands
- Git: Version control operations
- Docker: Container management
- Database: Firestore, PostgreSQL, SQLite
- Package: npm, pip, cargo, brew
- Deploy: GCP, Firebase, Vercel, AWS
- Infrastructure: Kubernetes, Terraform, GCP
- Frontend: React, Next.js, Vue, Tailwind, Vite, Testing
"""

from .base import Tool, ToolResult, ToolPermission, PermissionManager
from .filesystem import FileSystemTools
from .browser import BrowserTools
from .shell import ShellTools
from .git import GitTools, SmartGitTools, create_git_tools, create_smart_git_tools
from .docker import DockerTools, create_docker_tools
from .database import DatabaseTools, create_database_tools
from .package import PackageTools, create_package_tools
from .deploy import DeployTools, create_deploy_tools
from .infrastructure import (
    KubernetesTools,
    TerraformTools,
    GCPTools,
    create_kubernetes_tools,
    create_terraform_tools,
    create_gcp_tools,
)
from .frontend import FrontendTools, create_frontend_tools

__all__ = [
    # Base classes
    "Tool", "ToolResult", "ToolPermission", "PermissionManager",
    # Tool classes
    "FileSystemTools", "BrowserTools", "ShellTools",
    "GitTools", "SmartGitTools", "DockerTools", "DatabaseTools", "PackageTools", "DeployTools",
    # Infrastructure tools
    "KubernetesTools", "TerraformTools", "GCPTools",
    # Frontend tools
    "FrontendTools",
    # Factory functions
    "create_git_tools", "create_smart_git_tools", "create_docker_tools", "create_database_tools",
    "create_package_tools", "create_deploy_tools",
    "create_kubernetes_tools", "create_terraform_tools", "create_gcp_tools",
    "create_frontend_tools",
]


def create_all_tools(
    cwd: str = None,
    gcp_project: str = None,
    gcp_region: str = "us-central1",
    k8s_namespace: str = "default",
    k8s_context: str = None,
    terraform_dir: str = None,
) -> dict:
    """
    Create all development tools.

    Args:
        cwd: Working directory for tools
        gcp_project: GCP project ID
        gcp_region: GCP region (default: us-central1)
        k8s_namespace: Kubernetes namespace (default: default)
        k8s_context: Kubernetes context (optional)
        terraform_dir: Terraform working directory (optional, defaults to cwd)

    Returns a dictionary of tool instances ready for AI agents.
    """
    return {
        "filesystem": FileSystemTools(),
        "browser": BrowserTools(),
        "shell": ShellTools(default_cwd=cwd),
        "git": create_git_tools(cwd),
        "docker": create_docker_tools(cwd),
        "database": create_database_tools(),
        "package": create_package_tools(cwd),
        "deploy": create_deploy_tools(cwd, gcp_project),
        # Infrastructure tools
        "kubernetes": create_kubernetes_tools(
            namespace=k8s_namespace,
            context=k8s_context,
        ),
        "terraform": create_terraform_tools(
            working_dir=terraform_dir or cwd,
        ),
        "gcp": create_gcp_tools(
            project=gcp_project,
            region=gcp_region,
        ),
        # Frontend tools
        "frontend": create_frontend_tools(cwd),
    }
