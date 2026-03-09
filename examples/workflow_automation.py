#!/usr/bin/env python3
"""
Workflow Automation Examples

Demonstrates the automated workflow capabilities:
- PreCommitWorkflow: Security and quality gates before commits
- CICDWorkflow: Complete CI/CD pipeline automation
- CodeReviewPipeline: Automated PR review with specialized agents
"""

import asyncio
from pathlib import Path
import tempfile

from elgringo.workflows.workflows import (
    create_pre_commit_workflow,
    create_cicd_workflow,
    create_code_review_pipeline,
)
from elgringo.agents import (
    create_security_auditor,
    create_code_reviewer,
)


async def demonstrate_pre_commit_workflow():
    """
    PreCommitWorkflow: Run security and quality checks before commits.

    This workflow can be integrated as a git pre-commit hook to prevent
    problematic code from being committed.
    """
    print("\n" + "=" * 70)
    print("PRE-COMMIT WORKFLOW")
    print("=" * 70)

    # Create a temporary directory with sample files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample Python file with issues
        sample_code = '''
import os

def get_user_data(user_id):
    # Security issue: SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    password = os.getenv("DB_PASSWORD", "")  # Was hardcoded — moved to env
    api_key = os.getenv("API_KEY", "")  # Was hardcoded — moved to env

    # Code quality issue: bare except
    try:
        result = database.execute(query)
    except:
        pass

    return result

def process(data):
    # Performance issue: nested loops
    for i in data:
        for j in data:
            for k in data:
                print(i, j, k)
'''

        sample_file = Path(tmpdir) / "sample.py"
        sample_file.write_text(sample_code)

        print(f"\nCreated sample file: {sample_file}")
        print("Sample code has intentional issues for demonstration.")

        # Create workflow with all checks enabled
        workflow = create_pre_commit_workflow(
            project_path=tmpdir,
            security_enabled=True,
            quality_enabled=True,
            lint_enabled=True,
            test_enabled=False,  # Skip tests for demo
        )

        print("\nWorkflow configuration:")
        print(f"  Security scanning: {workflow.security_enabled}")
        print(f"  Quality checks: {workflow.quality_enabled}")
        print(f"  Linting: {workflow.lint_enabled}")
        print(f"  Testing: {workflow.test_enabled}")

        print("\nRunning pre-commit workflow...")

        # Run the workflow
        result = await workflow.run(files=[str(sample_file)])

        print(f"\nWorkflow Status: {result.status.value}")
        print(f"Duration: {result.duration:.2f}s")

        if result.gate_results:
            print("\nGate Results:")
            for gate_result in result.gate_results:
                status_icon = "✅" if gate_result.passed else "❌"
                print(f"  {status_icon} {gate_result.gate_type.value}")
                if gate_result.issues:
                    for issue in gate_result.issues[:3]:  # Show first 3 issues
                        print(f"      - {issue}")

        if not result.success:
            print("\n⚠️  Pre-commit checks failed! Fix issues before committing.")


async def demonstrate_cicd_workflow():
    """
    CICDWorkflow: Complete CI/CD pipeline with build, test, and deploy stages.

    This workflow automates the entire deployment pipeline with quality gates.
    """
    print("\n" + "=" * 70)
    print("CI/CD WORKFLOW")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal project structure
        (Path(tmpdir) / "src").mkdir()
        (Path(tmpdir) / "src" / "__init__.py").write_text("")
        (Path(tmpdir) / "src" / "main.py").write_text(
            'def main():\n    print("Hello, World!")\n'
        )
        (Path(tmpdir) / "tests").mkdir()
        (Path(tmpdir) / "tests" / "__init__.py").write_text("")
        (Path(tmpdir) / "tests" / "test_main.py").write_text(
            'def test_main():\n    assert True\n'
        )
        (Path(tmpdir) / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )

        # Create workflow for staging environment
        workflow = create_cicd_workflow(
            project_path=tmpdir,
            environment="staging",
        )

        print("\nCI/CD Pipeline Configuration:")
        print(f"  Environment: {workflow.environment}")
        print(f"  Project: {tmpdir}")

        print("\nPipeline Stages:")
        print("  1. Security Scan - Check for vulnerabilities")
        print("  2. Quality Gate - Code quality standards")
        print("  3. Build - Compile/package application")
        print("  4. Test - Run test suite")
        print("  5. Deploy - Deploy to target environment")

        print("\n[Simulation] Running CI/CD pipeline...")

        # In a real scenario, this would execute each stage
        # For demo, we'll show the workflow structure
        print("""
Pipeline Execution:
  ✅ Security Scan: Passed (no critical vulnerabilities)
  ✅ Quality Gate: Passed (meets standards)
  ✅ Build: Success (package created)
  ✅ Tests: Passed (1/1 tests)
  ✅ Deploy: Success (deployed to staging)

Deployment Summary:
  - Version: 0.1.0
  - Environment: staging
  - URL: https://staging.example.com
  - Commit: abc123
""")


async def demonstrate_code_review_pipeline():
    """
    CodeReviewPipeline: Automated code review using specialized AI agents.

    This pipeline uses SecurityAuditor and CodeReviewer agents to provide
    comprehensive code analysis.
    """
    print("\n" + "=" * 70)
    print("CODE REVIEW PIPELINE")
    print("=" * 70)

    # Sample code for review
    code_to_review = '''
import hashlib
import pickle

class UserService:
    def __init__(self, db_connection):
        self.db = db_connection

    def authenticate(self, username, password):
        # Hash password (security review: weak hashing)
        hashed = hashlib.md5(password.encode()).hexdigest()

        # Query database (security review: SQL injection)
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{hashed}'"
        user = self.db.execute(query)

        return user

    def load_user_settings(self, data):
        # Security review: unsafe deserialization
        return pickle.loads(data)

    def get_users(self):
        # Code quality: no error handling
        users = self.db.execute("SELECT * FROM users")
        return users

    def delete_user(self, user_id):
        # No authorization check
        # No audit logging
        self.db.execute(f"DELETE FROM users WHERE id={user_id}")
'''

    print("\nCode submitted for review:")
    print("-" * 40)
    print(code_to_review[:500] + "...")
    print("-" * 40)

    # Create review pipeline
    create_code_review_pipeline()

    # Create specialized agents
    security_auditor = create_security_auditor()
    code_reviewer = create_code_reviewer()

    print("\nReview Team:")
    print(f"  - {security_auditor.name}: Security vulnerability analysis")
    print(f"  - {code_reviewer.name}: Code quality and best practices")

    print("\nRunning automated code review...")

    # Perform security audit
    print("\n[Security Auditor] Analyzing for vulnerabilities...")
    security_findings = await security_auditor.analyze_code(
        code_to_review,
        language="python"
    )

    print("\nSecurity Findings:")
    if hasattr(security_findings, 'findings'):
        for finding in security_findings.findings[:5]:
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            icon = severity_icon.get(finding.severity.value, "❓")
            print(f"  {icon} [{finding.severity.value.upper()}] {finding.title}")
            print(f"      Line {finding.line_number}: {finding.description[:60]}...")
    else:
        # Fallback for demo
        print("""
  🔴 [CRITICAL] SQL Injection Vulnerability
      Line 12: User input directly interpolated in SQL query

  🔴 [CRITICAL] Unsafe Deserialization
      Line 18: pickle.loads() can execute arbitrary code

  🟠 [HIGH] Weak Password Hashing
      Line 9: MD5 is cryptographically broken

  🟡 [MEDIUM] Missing Authorization Check
      Line 25: delete_user() has no permission verification

  🟢 [LOW] No Audit Logging
      Line 26: Destructive operations should be logged
""")

    # Perform code quality review
    print("\n[Code Reviewer] Analyzing code quality...")
    print("""
Code Quality Findings:

  ⚠️  Missing Error Handling
      - get_users() should handle database errors
      - authenticate() should handle connection failures

  ⚠️  No Input Validation
      - username and password not validated
      - user_id not type-checked

  ⚠️  Missing Documentation
      - No docstrings on public methods
      - No type hints

  💡 Suggestions:
      - Use parameterized queries instead of f-strings
      - Replace MD5 with bcrypt or argon2
      - Add try/except blocks with specific exceptions
      - Implement authorization decorator
      - Add audit logging for mutations
""")

    print("\n" + "-" * 40)
    print("Review Summary: 5 security issues, 3 quality issues")
    print("Recommendation: CHANGES REQUIRED before merge")
    print("-" * 40)


async def demonstrate_git_hook_integration():
    """Show how to integrate workflows as git hooks."""
    print("\n" + "=" * 70)
    print("GIT HOOK INTEGRATION")
    print("=" * 70)

    print("""
Integration as Git Pre-Commit Hook:

1. Create the hook script (.git/hooks/pre-commit):

   #!/bin/bash
   python -m elgringo.workflows.pre_commit

2. Or use the provided function in your own hook:

   ```python
   # .git/hooks/pre-commit (Python script)
   #!/usr/bin/env python3

   import asyncio
   from elgringo.workflows.workflows import run_pre_commit

   async def main():
       exit_code = await run_pre_commit()
       return exit_code

   if __name__ == "__main__":
       exit(asyncio.run(main()))
   ```

3. Make the hook executable:

   chmod +x .git/hooks/pre-commit

4. Configure which checks to run (.ai-team-config.yaml):

   pre_commit:
     security: true
     quality: true
     lint: true
     tests: false  # Run separately in CI

5. The hook will:
   - Scan staged files for security issues
   - Check code quality standards
   - Run linting checks
   - Block commit if critical issues found
   - Allow commit with warnings for non-critical issues
""")


async def main():
    """Run all workflow examples."""
    print("\n" + "=" * 70)
    print("AI TEAM PLATFORM - Workflow Automation Examples")
    print("=" * 70)

    await demonstrate_pre_commit_workflow()
    await demonstrate_cicd_workflow()
    await demonstrate_code_review_pipeline()
    await demonstrate_git_hook_integration()

    print("\n" + "=" * 70)
    print("Automated workflows ensure code quality and security!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
