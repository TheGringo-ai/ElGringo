#!/usr/bin/env python3
"""
Infrastructure Tools Examples

Demonstrates the infrastructure management capabilities:
- Kubernetes: kubectl operations for cluster management
- Terraform: Infrastructure as Code operations
- GCP: Google Cloud Platform operations via gcloud
"""

import asyncio
from ai_dev_team.tools import (
    KubernetesTools,
    TerraformTools,
    GCPTools,
    create_kubernetes_tools,
    create_terraform_tools,
    create_gcp_tools,
    create_all_tools,
)


def demonstrate_kubernetes_tools():
    """
    KubernetesTools: Manage Kubernetes clusters with kubectl.

    Operations include pod management, deployments, services,
    ConfigMaps, Secrets, and more.
    """
    print("\n" + "=" * 70)
    print("KUBERNETES TOOLS")
    print("=" * 70)

    # Create Kubernetes tools instance
    k8s = create_kubernetes_tools(
        namespace="production",
        context="my-cluster",  # Optional: specific kubeconfig context
    )

    print(f"\nKubernetes Tools Configuration:")
    print(f"  Namespace: {k8s.namespace}")
    print(f"  Context: {k8s.context or 'default'}")
    print(f"  Operations available: {len(k8s._operations)}")

    print("\nAvailable Operations:")
    print("-" * 40)

    # Read Operations (safe, no permission required)
    read_ops = [
        ("get_pods", "List all pods in namespace"),
        ("get_deployments", "List all deployments"),
        ("get_services", "List all services"),
        ("get_namespaces", "List all namespaces"),
        ("get_configmaps", "List ConfigMaps"),
        ("get_secrets", "List Secrets (names only)"),
        ("describe", "Describe a specific resource"),
        ("logs", "Get pod logs"),
    ]

    print("\n📖 Read Operations (Safe):")
    for op, desc in read_ops:
        print(f"  • {op}: {desc}")

    # Write Operations (require permission)
    write_ops = [
        ("apply", "Apply a YAML manifest"),
        ("delete", "Delete a resource"),
        ("scale", "Scale deployment replicas"),
        ("rollout_restart", "Restart a deployment"),
        ("exec", "Execute command in pod"),
        ("create_namespace", "Create new namespace"),
        ("set_context", "Switch kubectl context"),
    ]

    print("\n✏️  Write Operations (Require Permission):")
    for op, desc in write_ops:
        print(f"  • {op}: {desc}")

    print("\nUsage Examples:")
    print("-" * 40)

    print("""
# List pods in production namespace
result = k8s.execute("get_pods", namespace="production")
print(result.output)

# Get logs from a specific pod
result = k8s.execute("logs", pod="api-server-abc123", tail=100)
print(result.output)

# Scale a deployment
result = k8s.execute("scale", deployment="web-app", replicas=5)
print(f"Scaled: {result.success}")

# Apply a manifest
manifest = '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-app:latest
'''
result = k8s.execute("apply", manifest=manifest)
print(result.output)

# Execute command in pod
result = k8s.execute("exec", pod="web-abc123", command="ls -la /app")
print(result.output)

# Rollout restart deployment
result = k8s.execute("rollout_restart", deployment="api-server")
print(f"Restarted: {result.success}")
""")


def demonstrate_terraform_tools():
    """
    TerraformTools: Infrastructure as Code with Terraform.

    Operations include plan, apply, destroy, state management,
    and workspace management.
    """
    print("\n" + "=" * 70)
    print("TERRAFORM TOOLS")
    print("=" * 70)

    # Create Terraform tools instance
    tf = create_terraform_tools(
        working_dir="/path/to/terraform",
        var_file="production.tfvars",
    )

    print(f"\nTerraform Tools Configuration:")
    print(f"  Working Directory: {tf.working_dir}")
    print(f"  Var File: {tf.var_file or 'none'}")
    print(f"  Operations available: {len(tf._operations)}")

    print("\nAvailable Operations:")
    print("-" * 40)

    # Safe Operations
    safe_ops = [
        ("init", "Initialize Terraform working directory"),
        ("validate", "Validate configuration syntax"),
        ("plan", "Generate execution plan"),
        ("show", "Show current state or plan"),
        ("output", "Show output values"),
        ("state_list", "List resources in state"),
        ("workspace_list", "List workspaces"),
        ("fmt", "Format configuration files"),
    ]

    print("\n📖 Safe Operations:")
    for op, desc in safe_ops:
        print(f"  • {op}: {desc}")

    # Dangerous Operations
    dangerous_ops = [
        ("apply", "Apply infrastructure changes"),
        ("destroy", "Destroy managed infrastructure"),
        ("import_resource", "Import existing resource"),
        ("workspace_new", "Create new workspace"),
        ("workspace_select", "Select workspace"),
        ("state_rm", "Remove resource from state"),
    ]

    print("\n⚠️  Dangerous Operations (Require Permission):")
    for op, desc in dangerous_ops:
        print(f"  • {op}: {desc}")

    print("\nUsage Examples:")
    print("-" * 40)

    print("""
# Initialize Terraform
result = tf.execute("init", upgrade=True)
print(result.output)

# Validate configuration
result = tf.execute("validate")
print(f"Valid: {result.success}")

# Generate execution plan
result = tf.execute("plan", out="tfplan")
print(result.output)

# Apply changes (auto-approved in code)
result = tf.execute("apply", plan_file="tfplan")
print(result.output)

# Show outputs
result = tf.execute("output", json_format=True)
outputs = result.output  # Parsed JSON

# Workspace management
result = tf.execute("workspace_list")
print(result.output)

result = tf.execute("workspace_new", name="staging")
print(f"Created workspace: {result.success}")

# State management
result = tf.execute("state_list")
for resource in result.output.split('\\n'):
    print(f"  - {resource}")

# Format configuration
result = tf.execute("fmt", recursive=True, check=True)
print(f"Formatting OK: {result.success}")
""")


def demonstrate_gcp_tools():
    """
    GCPTools: Google Cloud Platform operations via gcloud CLI.

    Operations include Cloud Run, Cloud Build, Cloud Storage,
    IAM, and Secret Manager.
    """
    print("\n" + "=" * 70)
    print("GCP TOOLS")
    print("=" * 70)

    # Create GCP tools instance
    gcp = create_gcp_tools(
        project="my-project-id",
        region="us-central1",
    )

    print(f"\nGCP Tools Configuration:")
    print(f"  Project: {gcp.project}")
    print(f"  Region: {gcp.region}")
    print(f"  Operations available: {len(gcp._operations)}")

    print("\nAvailable Operations:")
    print("-" * 40)

    # Info Operations
    info_ops = [
        ("projects_list", "List all GCP projects"),
        ("run_services_list", "List Cloud Run services"),
        ("run_revisions_list", "List service revisions"),
        ("builds_list", "List Cloud Build history"),
        ("storage_buckets_list", "List storage buckets"),
        ("iam_roles_list", "List IAM roles"),
        ("secrets_list", "List Secret Manager secrets"),
    ]

    print("\n📖 Info Operations (Safe):")
    for op, desc in info_ops:
        print(f"  • {op}: {desc}")

    # Action Operations
    action_ops = [
        ("run_deploy", "Deploy to Cloud Run"),
        ("run_update_traffic", "Update traffic split"),
        ("builds_submit", "Submit Cloud Build"),
        ("storage_cp", "Copy to/from Cloud Storage"),
        ("secrets_create", "Create new secret"),
        ("secrets_versions_add", "Add secret version"),
        ("run_services_delete", "Delete Cloud Run service"),
    ]

    print("\n✏️  Action Operations (Require Permission):")
    for op, desc in action_ops:
        print(f"  • {op}: {desc}")

    print("\nUsage Examples:")
    print("-" * 40)

    print("""
# List Cloud Run services
result = gcp.execute("run_services_list", region="us-central1")
for service in result.output:
    print(f"  {service['metadata']['name']}: {service['status']['url']}")

# Deploy to Cloud Run
result = gcp.execute(
    "run_deploy",
    service="my-api",
    image="gcr.io/my-project/my-api:latest",
    region="us-central1",
    memory="512Mi",
    cpu="1",
    min_instances=1,
    max_instances=10,
    allow_unauthenticated=False,
    env_vars={"ENV": "production", "LOG_LEVEL": "info"}
)
print(f"Deployed: {result.success}")

# Update traffic split (canary deployment)
result = gcp.execute(
    "run_update_traffic",
    service="my-api",
    revisions={
        "my-api-00001": 90,  # 90% to stable
        "my-api-00002": 10,  # 10% to canary
    }
)
print(f"Traffic updated: {result.success}")

# Submit Cloud Build
result = gcp.execute(
    "builds_submit",
    source=".",
    tag="gcr.io/my-project/my-api:latest"
)
print(result.output)

# Copy files to Cloud Storage
result = gcp.execute(
    "storage_cp",
    source="./build/*",
    destination="gs://my-bucket/releases/v1.0/",
    recursive=True
)
print(f"Uploaded: {result.success}")

# Create and manage secrets
result = gcp.execute("secrets_create", secret_id="api-key")
print(f"Created: {result.success}")

result = gcp.execute(
    "secrets_versions_add",
    secret_id="api-key",
    data="my-secret-value-123"
)
print(f"Version added: {result.success}")

# List build history
result = gcp.execute("builds_list", limit=5)
for build in result.output:
    print(f"  {build['id']}: {build['status']}")
""")


def demonstrate_integrated_tools():
    """Show how to use all tools together with create_all_tools()."""
    print("\n" + "=" * 70)
    print("INTEGRATED INFRASTRUCTURE TOOLS")
    print("=" * 70)

    print("""
Create all development and infrastructure tools with a single call:

```python
from ai_dev_team.tools import create_all_tools

# Create all tools with configuration
tools = create_all_tools(
    cwd="/path/to/project",
    gcp_project="my-project-id",
    gcp_region="us-central1",
    k8s_namespace="production",
    k8s_context="prod-cluster",
    terraform_dir="/path/to/terraform",
)

# Access individual tool categories
tools["git"].execute("status")
tools["docker"].execute("build", tag="my-app:latest")
tools["kubernetes"].execute("get_pods")
tools["terraform"].execute("plan")
tools["gcp"].execute("run_services_list")
tools["database"].execute("query", query="SELECT * FROM users")
tools["deploy"].execute("cloud_run", service="my-api")
```

Tool Categories Available:
  • filesystem - File operations
  • browser - Web automation
  • shell - Command execution
  • git - Version control
  • docker - Container management
  • database - Database operations
  • package - Package management
  • deploy - Deployment operations
  • kubernetes - K8s cluster management
  • terraform - Infrastructure as Code
  • gcp - Google Cloud operations
""")


def demonstrate_ai_orchestration():
    """Show how infrastructure tools work with AIDevTeam."""
    print("\n" + "=" * 70)
    print("AI ORCHESTRATION WITH INFRASTRUCTURE TOOLS")
    print("=" * 70)

    print("""
The AIDevTeam orchestrator can use infrastructure tools to perform
complex DevOps tasks through natural language:

```python
from ai_dev_team import AIDevTeam

team = AIDevTeam(project_name="my-project")

# Natural language infrastructure commands
result = await team.ask(
    "Scale the web-app deployment to 5 replicas in production"
)
# AI uses: k8s.execute("scale", deployment="web-app", replicas=5)

result = await team.ask(
    "Deploy the latest version of my-api to Cloud Run with 2GB memory"
)
# AI uses: gcp.execute("run_deploy", service="my-api", memory="2Gi", ...)

result = await team.ask(
    "Show me the Terraform plan for the staging environment"
)
# AI uses: tf.execute("plan", target="staging")

result = await team.ask(
    "Create a canary deployment with 10% traffic to the new version"
)
# AI uses: gcp.execute("run_update_traffic", revisions={...})
```

Security Integration:
  • All infrastructure commands go through security validation
  • Dangerous operations (destroy, delete) require explicit confirmation
  • Audit logging tracks all infrastructure changes
  • Role-based access control for sensitive operations

Multi-Model Consensus for Critical Operations:
```python
# Use consensus mode for production changes
result = await team.collaborate(
    "Should we proceed with the database migration?",
    mode="consensus",
    context={
        "environment": "production",
        "changes": terraform_plan_output,
        "rollback_plan": rollback_steps,
    }
)
```
""")


async def main():
    """Run all infrastructure tools examples."""
    print("\n" + "=" * 70)
    print("AI TEAM PLATFORM - Infrastructure Tools Examples")
    print("=" * 70)

    demonstrate_kubernetes_tools()
    demonstrate_terraform_tools()
    demonstrate_gcp_tools()
    demonstrate_integrated_tools()
    demonstrate_ai_orchestration()

    print("\n" + "=" * 70)
    print("Infrastructure tools enable AI-powered DevOps automation!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
