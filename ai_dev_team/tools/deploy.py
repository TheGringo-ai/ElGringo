"""
Cloud Deployment Tools - Deploy applications to cloud platforms
===============================================================

Capabilities:
- Google Cloud Platform (Cloud Run, App Engine, Firebase)
- Firebase (Hosting, Functions)
- Vercel
- AWS (Lambda, ECS, S3)
- Generic deployment helpers
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class DeployTools(Tool):
    """
    Cloud deployment tools for AI-powered development.

    Supports GCP, Firebase, Vercel, and AWS for deploying
    applications to production.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_cwd: Optional[str] = None,
        gcp_project: Optional[str] = None
    ):
        super().__init__(
            name="deploy",
            description="Cloud deployment operations (GCP, Firebase, Vercel, AWS)",
            permission_manager=permission_manager,
        )

        self.default_cwd = default_cwd or os.getcwd()
        self.gcp_project = gcp_project or os.getenv("GOOGLE_CLOUD_PROJECT")

        # Firebase operations
        self.register_operation("firebase_deploy", self._firebase_deploy, "Deploy to Firebase")
        self.register_operation("firebase_hosting", self._firebase_hosting, "Deploy Firebase Hosting")
        self.register_operation("firebase_functions", self._firebase_functions, "Deploy Firebase Functions")
        self.register_operation("firebase_init", self._firebase_init, "Initialize Firebase")

        # Google Cloud operations
        self.register_operation("gcp_run_deploy", self._gcp_run_deploy, "Deploy to Cloud Run")
        self.register_operation("gcp_build", self._gcp_build, "Build with Cloud Build")
        self.register_operation("gcp_app_deploy", self._gcp_app_deploy, "Deploy to App Engine")
        self.register_operation("gcp_functions", self._gcp_functions_deploy, "Deploy Cloud Function")

        # Vercel operations
        self.register_operation("vercel_deploy", self._vercel_deploy, "Deploy to Vercel")
        self.register_operation("vercel_preview", self._vercel_preview, "Deploy Vercel preview")

        # AWS operations
        self.register_operation("aws_lambda_deploy", self._aws_lambda_deploy, "Deploy to AWS Lambda")
        self.register_operation("aws_s3_sync", self._aws_s3_sync, "Sync to S3 bucket")
        self.register_operation("aws_ecr_push", self._aws_ecr_push, "Push to ECR")

        # Generic operations
        self.register_operation("status", self._deployment_status, "Check deployment status", requires_permission=False)
        self.register_operation("logs", self._deployment_logs, "Get deployment logs", requires_permission=False)
        self.register_operation("rollback", self._rollback, "Rollback deployment")

    async def _run_cmd(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 600,
        env: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Execute a deployment command"""
        try:
            work_dir = cwd or self.default_cwd
            cmd_env = os.environ.copy()
            if env:
                cmd_env.update(env)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=cmd_env
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
            return ToolResult(success=False, output=None, error=f"Deployment timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error=f"Command not found: {cmd[0]}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # Firebase operations
    def _firebase_deploy(
        self,
        only: Optional[List[str]] = None,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy all Firebase services"""
        args = ["firebase", "deploy"]
        if project or self.gcp_project:
            args.extend(["--project", project or self.gcp_project])
        if only:
            args.extend(["--only", ",".join(only)])
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _firebase_hosting(
        self,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy Firebase Hosting only"""
        return self._firebase_deploy(only=["hosting"], project=project, cwd=cwd)

    def _firebase_functions(
        self,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy Firebase Functions only"""
        return self._firebase_deploy(only=["functions"], project=project, cwd=cwd)

    def _firebase_init(
        self,
        features: Optional[List[str]] = None,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Initialize Firebase in project"""
        args = ["firebase", "init"]
        if features:
            args.extend(features)
        if project or self.gcp_project:
            args.extend(["--project", project or self.gcp_project])
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    # Google Cloud operations
    def _gcp_run_deploy(
        self,
        service: str,
        image: Optional[str] = None,
        source: Optional[str] = None,
        region: str = "us-central1",
        port: int = 8080,
        allow_unauthenticated: bool = True,
        env_vars: Optional[Dict[str, str]] = None,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy to Cloud Run"""
        args = ["gcloud", "run", "deploy", service]

        if image:
            args.extend(["--image", image])
        elif source:
            args.extend(["--source", source])
        else:
            args.extend(["--source", "."])

        args.extend(["--region", region])
        args.extend(["--port", str(port)])

        if allow_unauthenticated:
            args.append("--allow-unauthenticated")

        if env_vars:
            env_str = ",".join([f"{k}={v}" for k, v in env_vars.items()])
            args.extend(["--set-env-vars", env_str])

        if project or self.gcp_project:
            args.extend(["--project", project or self.gcp_project])

        args.append("--quiet")

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd, timeout=900)  # 15 min for build + deploy
        )

    def _gcp_build(
        self,
        tag: str,
        config: Optional[str] = None,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Build with Cloud Build"""
        args = ["gcloud", "builds", "submit", "--tag", tag]

        if config:
            args.extend(["--config", config])

        if project or self.gcp_project:
            args.extend(["--project", project or self.gcp_project])

        args.append("--quiet")

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd, timeout=900)
        )

    def _gcp_app_deploy(
        self,
        version: Optional[str] = None,
        promote: bool = True,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy to App Engine"""
        args = ["gcloud", "app", "deploy"]

        if version:
            args.extend(["--version", version])

        if not promote:
            args.append("--no-promote")

        if project or self.gcp_project:
            args.extend(["--project", project or self.gcp_project])

        args.append("--quiet")

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd, timeout=900)
        )

    def _gcp_functions_deploy(
        self,
        function_name: str,
        runtime: str = "python311",
        trigger: str = "http",
        entry_point: Optional[str] = None,
        region: str = "us-central1",
        env_vars: Optional[Dict[str, str]] = None,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy Cloud Function"""
        args = [
            "gcloud", "functions", "deploy", function_name,
            "--runtime", runtime,
            "--region", region,
            f"--trigger-{trigger}"
        ]

        if entry_point:
            args.extend(["--entry-point", entry_point])

        if trigger == "http":
            args.append("--allow-unauthenticated")

        if env_vars:
            env_str = ",".join([f"{k}={v}" for k, v in env_vars.items()])
            args.extend(["--set-env-vars", env_str])

        if project or self.gcp_project:
            args.extend(["--project", project or self.gcp_project])

        args.append("--quiet")

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd, timeout=600)
        )

    # Vercel operations
    def _vercel_deploy(
        self,
        prod: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy to Vercel"""
        args = ["vercel"]
        if prod:
            args.append("--prod")
        args.append("--yes")

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _vercel_preview(self, cwd: Optional[str] = None) -> ToolResult:
        """Deploy Vercel preview"""
        return self._vercel_deploy(prod=False, cwd=cwd)

    # AWS operations
    def _aws_lambda_deploy(
        self,
        function_name: str,
        zip_file: str,
        handler: str = "lambda_function.handler",
        runtime: str = "python3.11",
        role: Optional[str] = None,
        region: str = "us-east-1",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Deploy to AWS Lambda"""
        # Check if function exists first
        check_args = [
            "aws", "lambda", "get-function",
            "--function-name", function_name,
            "--region", region
        ]

        check_result = asyncio.get_event_loop().run_until_complete(
            self._run_cmd(check_args, cwd, timeout=30)
        )

        if check_result.success:
            # Update existing function
            args = [
                "aws", "lambda", "update-function-code",
                "--function-name", function_name,
                "--zip-file", f"fileb://{zip_file}",
                "--region", region
            ]
        else:
            # Create new function
            if not role:
                return ToolResult(
                    success=False,
                    output=None,
                    error="IAM role required for new Lambda function"
                )

            args = [
                "aws", "lambda", "create-function",
                "--function-name", function_name,
                "--runtime", runtime,
                "--handler", handler,
                "--role", role,
                "--zip-file", f"fileb://{zip_file}",
                "--region", region
            ]

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _aws_s3_sync(
        self,
        source: str,
        bucket: str,
        delete: bool = False,
        acl: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Sync files to S3 bucket"""
        args = ["aws", "s3", "sync", source, f"s3://{bucket}"]

        if delete:
            args.append("--delete")

        if acl:
            args.extend(["--acl", acl])

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _aws_ecr_push(
        self,
        image: str,
        repository: str,
        tag: str = "latest",
        region: str = "us-east-1",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Push image to ECR"""
        # Get ECR login
        login_result = asyncio.get_event_loop().run_until_complete(
            self._run_cmd([
                "aws", "ecr", "get-login-password", "--region", region
            ], cwd)
        )

        if not login_result.success:
            return login_result

        # Get account ID
        account_result = asyncio.get_event_loop().run_until_complete(
            self._run_cmd([
                "aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"
            ], cwd)
        )

        if not account_result.success:
            return account_result

        account_id = account_result.output.strip()
        ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repository}:{tag}"

        # Tag image
        tag_result = asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["docker", "tag", image, ecr_uri], cwd)
        )

        if not tag_result.success:
            return tag_result

        # Push to ECR
        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(["docker", "push", ecr_uri], cwd, timeout=600)
        )

    # Generic operations
    def _deployment_status(
        self,
        platform: str,
        service: str,
        region: str = "us-central1",
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Check deployment status"""
        if platform == "cloudrun" or platform == "gcp":
            args = [
                "gcloud", "run", "services", "describe", service,
                "--region", region,
                "--format", "json"
            ]
            if project or self.gcp_project:
                args.extend(["--project", project or self.gcp_project])

        elif platform == "firebase":
            args = ["firebase", "hosting:channel:list"]
            if project or self.gcp_project:
                args.extend(["--project", project or self.gcp_project])

        elif platform == "vercel":
            args = ["vercel", "ls"]

        elif platform == "lambda" or platform == "aws":
            args = [
                "aws", "lambda", "get-function",
                "--function-name", service,
                "--region", region
            ]

        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown platform: {platform}"
            )

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _deployment_logs(
        self,
        platform: str,
        service: str,
        region: str = "us-central1",
        limit: int = 100,
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Get deployment logs"""
        if platform == "cloudrun" or platform == "gcp":
            args = [
                "gcloud", "logging", "read",
                f"resource.type=cloud_run_revision AND resource.labels.service_name={service}",
                "--limit", str(limit),
                "--format", "value(textPayload)"
            ]
            if project or self.gcp_project:
                args.extend(["--project", project or self.gcp_project])

        elif platform == "lambda" or platform == "aws":
            args = [
                "aws", "logs", "filter-log-events",
                "--log-group-name", f"/aws/lambda/{service}",
                "--limit", str(limit),
                "--region", region
            ]

        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown platform: {platform}"
            )

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )

    def _rollback(
        self,
        platform: str,
        service: str,
        revision: str,
        region: str = "us-central1",
        project: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Rollback deployment"""
        if platform == "cloudrun" or platform == "gcp":
            args = [
                "gcloud", "run", "services", "update-traffic", service,
                "--to-revisions", f"{revision}=100",
                "--region", region
            ]
            if project or self.gcp_project:
                args.extend(["--project", project or self.gcp_project])
            args.append("--quiet")

        elif platform == "lambda" or platform == "aws":
            args = [
                "aws", "lambda", "update-alias",
                "--function-name", service,
                "--name", "live",
                "--function-version", revision,
                "--region", region
            ]

        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown platform: {platform}"
            )

        return asyncio.get_event_loop().run_until_complete(
            self._run_cmd(args, cwd)
        )


    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of Deploy tool capabilities."""
        return [
            {"name": "firebase_deploy", "description": "Deploy to Firebase"},
            {"name": "firebase_hosting", "description": "Deploy Firebase Hosting"},
            {"name": "gcp_run_deploy", "description": "Deploy to Cloud Run"},
            {"name": "gcp_build", "description": "Build with Cloud Build"},
            {"name": "vercel_deploy", "description": "Deploy to Vercel"},
            {"name": "aws_lambda_deploy", "description": "Deploy to AWS Lambda"},
            {"name": "aws_s3_sync", "description": "Sync to S3 bucket"},
            {"name": "rollback", "description": "Rollback deployment"},
        ]


# Convenience function
def create_deploy_tools(
    cwd: Optional[str] = None,
    gcp_project: Optional[str] = None
) -> DeployTools:
    """Create Deploy tools instance"""
    return DeployTools(default_cwd=cwd, gcp_project=gcp_project)
