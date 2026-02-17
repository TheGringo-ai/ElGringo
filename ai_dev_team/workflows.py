"""
Automated Workflows
===================

Provides automated development workflows for:
- Pre-commit code review and security scanning
- CI/CD pipeline integration
- Deployment automation
- Code quality gates
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .agents.specialists import (
    SecurityAuditor, CodeReviewer, SolutionArchitect,
    create_security_auditor, create_code_reviewer,
    Severity, SecurityFinding, CodeReviewComment
)
from .security import validate_tool_call, get_security_validator

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GateType(Enum):
    """Quality gate types"""
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    TESTS = "tests"
    COVERAGE = "coverage"
    LINT = "lint"
    BUILD = "build"


@dataclass
class GateResult:
    """Result of a quality gate check"""
    gate_type: GateType
    status: WorkflowStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    blocking: bool = True


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution"""
    workflow_name: str
    status: WorkflowStatus
    gates: List[GateResult]
    start_time: datetime
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == WorkflowStatus.PASSED

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class PreCommitWorkflow:
    """
    Pre-commit workflow that runs before code is committed.

    Includes:
    - Security scanning
    - Code quality checks
    - Linting
    - Test execution
    """

    def __init__(
        self,
        project_path: Optional[str] = None,
        security_enabled: bool = True,
        quality_enabled: bool = True,
        lint_enabled: bool = True,
        test_enabled: bool = False,  # Optional, can be slow
    ):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.security_enabled = security_enabled
        self.quality_enabled = quality_enabled
        self.lint_enabled = lint_enabled
        self.test_enabled = test_enabled

        self._security_auditor = create_security_auditor()
        self._code_reviewer = create_code_reviewer()

    async def run(self, files: Optional[List[str]] = None) -> WorkflowResult:
        """
        Run pre-commit workflow on specified files or staged files.

        Args:
            files: List of files to check (default: git staged files)

        Returns:
            WorkflowResult with all gate results
        """
        start_time = datetime.now(timezone.utc)
        gates = []

        # Get files to check
        if files is None:
            files = self._get_staged_files()

        if not files:
            return WorkflowResult(
                workflow_name="pre-commit",
                status=WorkflowStatus.SKIPPED,
                gates=[],
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                metadata={"message": "No files to check"}
            )

        logger.info(f"Running pre-commit workflow on {len(files)} files")

        # Run security scan
        if self.security_enabled:
            security_result = await self._run_security_gate(files)
            gates.append(security_result)

        # Run code quality check
        if self.quality_enabled:
            quality_result = await self._run_quality_gate(files)
            gates.append(quality_result)

        # Run linting
        if self.lint_enabled:
            lint_result = await self._run_lint_gate(files)
            gates.append(lint_result)

        # Run tests
        if self.test_enabled:
            test_result = await self._run_test_gate()
            gates.append(test_result)

        # Determine overall status
        failed_blocking = [g for g in gates if g.status == WorkflowStatus.FAILED and g.blocking]
        if failed_blocking:
            overall_status = WorkflowStatus.FAILED
        else:
            overall_status = WorkflowStatus.PASSED

        return WorkflowResult(
            workflow_name="pre-commit",
            status=overall_status,
            gates=gates,
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            metadata={"files_checked": len(files)}
        )

    def _get_staged_files(self) -> List[str]:
        """Get git staged files"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f]
        except Exception as e:
            logger.warning(f"Could not get staged files: {e}")
        return []

    async def _run_security_gate(self, files: List[str]) -> GateResult:
        """Run security scanning gate"""
        all_findings: List[SecurityFinding] = []

        for file_path in files:
            if not file_path.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                continue

            full_path = self.project_path / file_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text()
                findings = self._security_auditor.scan_code(content, file_path)
                all_findings.extend(findings)
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")

        # Determine status based on findings
        critical_count = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)
        high_count = sum(1 for f in all_findings if f.severity == Severity.HIGH)

        if critical_count > 0:
            status = WorkflowStatus.FAILED
            message = f"Found {critical_count} critical security issues"
        elif high_count > 0:
            status = WorkflowStatus.FAILED
            message = f"Found {high_count} high severity security issues"
        elif all_findings:
            status = WorkflowStatus.PASSED
            message = f"Found {len(all_findings)} low/medium issues (review recommended)"
        else:
            status = WorkflowStatus.PASSED
            message = "No security issues found"

        return GateResult(
            gate_type=GateType.SECURITY,
            status=status,
            message=message,
            details={
                "total_findings": len(all_findings),
                "critical": critical_count,
                "high": high_count,
                "findings": [
                    {"severity": f.severity.value, "title": f.title, "location": f.location}
                    for f in all_findings[:10]  # Limit to first 10
                ]
            },
            blocking=critical_count > 0 or high_count > 0
        )

    async def _run_quality_gate(self, files: List[str]) -> GateResult:
        """Run code quality gate"""
        all_comments: List[CodeReviewComment] = []

        for file_path in files:
            if not file_path.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                continue

            full_path = self.project_path / file_path
            if not full_path.exists():
                continue

            try:
                content = full_path.read_text()
                comments = self._code_reviewer.review_code(content, file_path)
                all_comments.extend(comments)
            except Exception as e:
                logger.warning(f"Could not review {file_path}: {e}")

        # Count issues by type
        issues = [c for c in all_comments if c.type == "issue"]
        critical_issues = [c for c in issues if c.severity == Severity.CRITICAL]

        if critical_issues:
            status = WorkflowStatus.FAILED
            message = f"Found {len(critical_issues)} critical code quality issues"
        elif len(issues) > 10:
            status = WorkflowStatus.FAILED
            message = f"Found {len(issues)} code quality issues (too many)"
        elif issues:
            status = WorkflowStatus.PASSED
            message = f"Found {len(issues)} minor issues (review recommended)"
        else:
            status = WorkflowStatus.PASSED
            message = "Code quality looks good"

        return GateResult(
            gate_type=GateType.CODE_QUALITY,
            status=status,
            message=message,
            details={
                "total_comments": len(all_comments),
                "issues": len(issues),
                "suggestions": len([c for c in all_comments if c.type == "suggestion"]),
            },
            blocking=len(critical_issues) > 0
        )

    async def _run_lint_gate(self, files: List[str]) -> GateResult:
        """Run linting gate"""
        python_files = [f for f in files if f.endswith('.py')]
        js_files = [f for f in files if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]

        errors = []

        # Python linting with ruff or flake8
        if python_files:
            try:
                # Try ruff first (faster)
                result = subprocess.run(
                    ["ruff", "check", "--select=E,F,W"] + python_files,
                    capture_output=True,
                    text=True,
                    cwd=self.project_path
                )
                if result.returncode != 0:
                    errors.extend(result.stdout.strip().split('\n')[:10])
            except FileNotFoundError:
                # Fall back to flake8
                try:
                    result = subprocess.run(
                        ["flake8", "--select=E,F,W"] + python_files,
                        capture_output=True,
                        text=True,
                        cwd=self.project_path
                    )
                    if result.returncode != 0:
                        errors.extend(result.stdout.strip().split('\n')[:10])
                except FileNotFoundError:
                    logger.warning("No Python linter available (ruff or flake8)")

        # JavaScript/TypeScript linting with eslint
        if js_files:
            try:
                result = subprocess.run(
                    ["npx", "eslint", "--max-warnings=0"] + js_files,
                    capture_output=True,
                    text=True,
                    cwd=self.project_path
                )
                if result.returncode != 0:
                    errors.extend(result.stdout.strip().split('\n')[:10])
            except FileNotFoundError:
                logger.warning("ESLint not available")

        if errors:
            status = WorkflowStatus.FAILED
            message = f"Found {len(errors)} linting errors"
        else:
            status = WorkflowStatus.PASSED
            message = "Linting passed"

        return GateResult(
            gate_type=GateType.LINT,
            status=status,
            message=message,
            details={"errors": errors[:10]},
            blocking=len(errors) > 0
        )

    async def _run_test_gate(self) -> GateResult:
        """Run test gate"""
        try:
            # Try pytest first
            result = subprocess.run(
                ["pytest", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                status = WorkflowStatus.PASSED
                message = "All tests passed"
            else:
                status = WorkflowStatus.FAILED
                message = "Some tests failed"

            return GateResult(
                gate_type=GateType.TESTS,
                status=status,
                message=message,
                details={
                    "output": result.stdout[-1000:] if result.stdout else "",
                    "errors": result.stderr[-500:] if result.stderr else "",
                },
                blocking=True
            )

        except FileNotFoundError:
            return GateResult(
                gate_type=GateType.TESTS,
                status=WorkflowStatus.SKIPPED,
                message="pytest not available",
                blocking=False
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_type=GateType.TESTS,
                status=WorkflowStatus.FAILED,
                message="Tests timed out after 5 minutes",
                blocking=True
            )


class CICDWorkflow:
    """
    CI/CD workflow for continuous integration and deployment.

    Can be used standalone or integrated with GitHub Actions, GitLab CI, etc.
    """

    def __init__(
        self,
        project_path: Optional[str] = None,
        deploy_enabled: bool = False,
        environment: str = "development"
    ):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.deploy_enabled = deploy_enabled
        self.environment = environment

        self._pre_commit = PreCommitWorkflow(
            project_path=str(self.project_path),
            test_enabled=True  # Enable tests in CI
        )

    async def run_full_pipeline(self) -> WorkflowResult:
        """Run complete CI/CD pipeline"""
        start_time = datetime.now(timezone.utc)
        gates = []

        logger.info(f"Starting CI/CD pipeline for {self.environment}")

        # 1. Pre-commit checks (security, quality, lint)
        pre_commit_result = await self._pre_commit.run()
        gates.extend(pre_commit_result.gates)

        if pre_commit_result.status == WorkflowStatus.FAILED:
            return WorkflowResult(
                workflow_name="ci-cd",
                status=WorkflowStatus.FAILED,
                gates=gates,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                metadata={"failed_at": "pre-commit"}
            )

        # 2. Build
        build_result = await self._run_build_gate()
        gates.append(build_result)

        if build_result.status == WorkflowStatus.FAILED:
            return WorkflowResult(
                workflow_name="ci-cd",
                status=WorkflowStatus.FAILED,
                gates=gates,
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                metadata={"failed_at": "build"}
            )

        # 3. Deploy (if enabled)
        if self.deploy_enabled:
            deploy_result = await self._run_deploy_gate()
            gates.append(deploy_result)

            if deploy_result.status == WorkflowStatus.FAILED:
                return WorkflowResult(
                    workflow_name="ci-cd",
                    status=WorkflowStatus.FAILED,
                    gates=gates,
                    start_time=start_time,
                    end_time=datetime.now(timezone.utc),
                    metadata={"failed_at": "deploy"}
                )

        return WorkflowResult(
            workflow_name="ci-cd",
            status=WorkflowStatus.PASSED,
            gates=gates,
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            metadata={"environment": self.environment}
        )

    async def _run_build_gate(self) -> GateResult:
        """Run build gate"""
        # Detect project type and run appropriate build
        package_json = self.project_path / "package.json"
        setup_py = self.project_path / "setup.py"
        pyproject = self.project_path / "pyproject.toml"
        dockerfile = self.project_path / "Dockerfile"

        if dockerfile.exists():
            # Docker build
            try:
                result = subprocess.run(
                    ["docker", "build", "-t", "test-build", "."],
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    timeout=600
                )
                if result.returncode == 0:
                    return GateResult(
                        gate_type=GateType.BUILD,
                        status=WorkflowStatus.PASSED,
                        message="Docker build successful"
                    )
                else:
                    return GateResult(
                        gate_type=GateType.BUILD,
                        status=WorkflowStatus.FAILED,
                        message="Docker build failed",
                        details={"error": result.stderr[-500:]}
                    )
            except Exception as e:
                return GateResult(
                    gate_type=GateType.BUILD,
                    status=WorkflowStatus.FAILED,
                    message=f"Docker build error: {e}"
                )

        elif package_json.exists():
            # NPM build
            try:
                result = subprocess.run(
                    ["npm", "run", "build"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    timeout=300
                )
                if result.returncode == 0:
                    return GateResult(
                        gate_type=GateType.BUILD,
                        status=WorkflowStatus.PASSED,
                        message="NPM build successful"
                    )
                else:
                    return GateResult(
                        gate_type=GateType.BUILD,
                        status=WorkflowStatus.FAILED,
                        message="NPM build failed",
                        details={"error": result.stderr[-500:]}
                    )
            except Exception as e:
                return GateResult(
                    gate_type=GateType.BUILD,
                    status=WorkflowStatus.FAILED,
                    message=f"NPM build error: {e}"
                )

        elif pyproject.exists() or setup_py.exists():
            # Python build
            try:
                result = subprocess.run(
                    ["pip", "install", "-e", "."],
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    timeout=300
                )
                if result.returncode == 0:
                    return GateResult(
                        gate_type=GateType.BUILD,
                        status=WorkflowStatus.PASSED,
                        message="Python build successful"
                    )
                else:
                    return GateResult(
                        gate_type=GateType.BUILD,
                        status=WorkflowStatus.FAILED,
                        message="Python build failed"
                    )
            except Exception as e:
                return GateResult(
                    gate_type=GateType.BUILD,
                    status=WorkflowStatus.FAILED,
                    message=f"Python build error: {e}"
                )

        return GateResult(
            gate_type=GateType.BUILD,
            status=WorkflowStatus.SKIPPED,
            message="No build configuration found",
            blocking=False
        )

    async def _run_deploy_gate(self) -> GateResult:
        """Run deployment gate"""
        # This would integrate with the deploy tools
        # For now, return a placeholder
        return GateResult(
            gate_type=GateType.BUILD,  # Using BUILD as placeholder
            status=WorkflowStatus.SKIPPED,
            message=f"Deploy to {self.environment} not configured",
            blocking=False
        )


class CodeReviewPipeline:
    """
    Automated code review pipeline that uses AI agents.

    Provides comprehensive code review with:
    - Security analysis
    - Code quality checks
    - Architecture suggestions
    - Best practices enforcement
    """

    def __init__(self, base_agent=None):
        self._security_auditor = create_security_auditor()
        self._code_reviewer = create_code_reviewer()
        self._architect = SolutionArchitect(base_agent=base_agent)

    async def review_pull_request(
        self,
        files: Dict[str, str],  # {filename: content}
        pr_description: str = ""
    ) -> Dict[str, Any]:
        """
        Review a pull request.

        Args:
            files: Dictionary mapping filenames to their content
            pr_description: PR description for context

        Returns:
            Comprehensive review results
        """
        results = {
            "summary": "",
            "security": {"findings": [], "score": 100},
            "quality": {"comments": [], "score": 100},
            "overall_recommendation": "approve",
            "blocking_issues": [],
        }

        all_security_findings = []
        all_quality_comments = []

        for filename, content in files.items():
            # Security scan
            findings = self._security_auditor.scan_code(content, filename)
            all_security_findings.extend(findings)

            # Quality review
            comments = self._code_reviewer.review_code(content, filename)
            all_quality_comments.extend(comments)

        # Calculate security score
        critical_security = sum(1 for f in all_security_findings if f.severity == Severity.CRITICAL)
        high_security = sum(1 for f in all_security_findings if f.severity == Severity.HIGH)
        results["security"]["findings"] = [
            {"severity": f.severity.value, "title": f.title, "location": f.location, "cwe": f.cwe_id}
            for f in all_security_findings
        ]
        results["security"]["score"] = max(0, 100 - (critical_security * 30) - (high_security * 15))

        # Calculate quality score
        issues = [c for c in all_quality_comments if c.type == "issue"]
        critical_quality = sum(1 for c in issues if c.severity == Severity.CRITICAL)
        results["quality"]["comments"] = [
            {"type": c.type, "severity": c.severity.value, "file": c.file, "line": c.line, "message": c.message}
            for c in all_quality_comments
        ]
        results["quality"]["score"] = max(0, 100 - (critical_quality * 20) - (len(issues) * 5))

        # Determine recommendation
        blocking = []
        if critical_security > 0:
            blocking.append(f"{critical_security} critical security issues")
        if high_security > 0:
            blocking.append(f"{high_security} high severity security issues")
        if critical_quality > 0:
            blocking.append(f"{critical_quality} critical code quality issues")

        results["blocking_issues"] = blocking
        if blocking:
            results["overall_recommendation"] = "request_changes"
        elif results["security"]["score"] < 80 or results["quality"]["score"] < 80:
            results["overall_recommendation"] = "comment"
        else:
            results["overall_recommendation"] = "approve"

        # Generate summary
        results["summary"] = self._generate_summary(results, len(files))

        return results

    def _generate_summary(self, results: Dict, file_count: int) -> str:
        """Generate human-readable summary"""
        parts = [f"## Code Review Summary\n\nReviewed {file_count} files.\n"]

        # Security
        sec = results["security"]
        parts.append(f"### Security: {sec['score']}/100")
        if sec["findings"]:
            parts.append(f"Found {len(sec['findings'])} security issues.")
        else:
            parts.append("No security issues found. ✅")

        # Quality
        qual = results["quality"]
        parts.append(f"\n### Code Quality: {qual['score']}/100")
        if qual["comments"]:
            parts.append(f"Found {len(qual['comments'])} items to address.")
        else:
            parts.append("Code quality looks good. ✅")

        # Recommendation
        rec = results["overall_recommendation"]
        rec_emoji = {"approve": "✅", "comment": "💬", "request_changes": "❌"}
        parts.append(f"\n### Recommendation: {rec.upper()} {rec_emoji.get(rec, '')}")

        if results["blocking_issues"]:
            parts.append("\n**Blocking Issues:**")
            for issue in results["blocking_issues"]:
                parts.append(f"- {issue}")

        return "\n".join(parts)


# Factory functions
def create_pre_commit_workflow(project_path: Optional[str] = None, **kwargs) -> PreCommitWorkflow:
    """Create a pre-commit workflow"""
    return PreCommitWorkflow(project_path=project_path, **kwargs)


def create_cicd_workflow(project_path: Optional[str] = None, **kwargs) -> CICDWorkflow:
    """Create a CI/CD workflow"""
    return CICDWorkflow(project_path=project_path, **kwargs)


def create_code_review_pipeline(base_agent=None) -> CodeReviewPipeline:
    """Create a code review pipeline"""
    return CodeReviewPipeline(base_agent=base_agent)


# CLI-compatible function for pre-commit hooks
async def run_pre_commit(files: Optional[List[str]] = None, project_path: Optional[str] = None) -> int:
    """
    Run pre-commit checks. Returns exit code (0 = pass, 1 = fail).

    Can be used as a git pre-commit hook:
    ```
    #!/bin/bash
    python -c "import asyncio; from ai_dev_team.workflows import run_pre_commit; exit(asyncio.run(run_pre_commit()))"
    ```
    """
    workflow = create_pre_commit_workflow(project_path=project_path)
    result = await workflow.run(files)

    # Print results
    print(f"\n{'='*60}")
    print(f"Pre-commit Results: {result.status.value.upper()}")
    print(f"{'='*60}")

    for gate in result.gates:
        emoji = "✅" if gate.status == WorkflowStatus.PASSED else "❌" if gate.status == WorkflowStatus.FAILED else "⏭️"
        print(f"{emoji} {gate.gate_type.value}: {gate.message}")

    print(f"\nDuration: {result.duration_seconds:.2f}s")

    return 0 if result.passed else 1
