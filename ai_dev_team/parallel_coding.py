"""
Parallel Coding Automation System
==================================

Enables Claude (team lead) to orchestrate the AI team for parallel
code review, fixing, and development tasks.

This is the core engine that powers automated multi-agent development.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .agents import AIAgent, AgentResponse
from .orchestrator import AIDevTeam, CollaborationResult

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of parallel coding tasks"""
    CODE_REVIEW = "code_review"
    SECURITY_AUDIT = "security_audit"
    BUG_FIX = "bug_fix"
    FEATURE_IMPL = "feature_impl"
    REFACTOR = "refactor"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


@dataclass
class CodeTask:
    """A task for an AI agent to work on"""
    task_id: str
    task_type: TaskType
    description: str
    file_path: Optional[str] = None
    code_snippet: Optional[str] = None
    context: str = ""
    assigned_agent: Optional[str] = None
    priority: int = 1  # 1=highest
    dependencies: List[str] = field(default_factory=list)


@dataclass
class CodeFix:
    """A code fix proposed by an agent"""
    file_path: str
    original_code: str
    fixed_code: str
    description: str
    agent_name: str
    confidence: float
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class ParallelCodingResult:
    """Result of a parallel coding session"""
    session_id: str
    project_path: str
    task_type: TaskType
    success: bool
    total_time: float
    agent_results: Dict[str, Any]
    proposed_fixes: List[CodeFix]
    summary: str
    timestamp: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)


class ParallelCodingEngine:
    """
    Orchestrates parallel coding tasks across the AI team.

    Claude acts as team lead, delegating work to specialists:
    - ChatGPT: Senior Developer (coding, debugging)
    - Gemini: Creative Solutions (innovation, UI/UX)
    - Grok Reasoner: Strategic Analysis
    - Grok Coder: Fast Implementation
    """

    def __init__(self, team: Optional[AIDevTeam] = None):
        self.team = team or AIDevTeam(project_name="parallel-coding")
        self.session_id = f"pc_{int(time.time())}"
        self.results_dir = Path.home() / ".ai_team" / "parallel_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def review_project(
        self,
        project_path: str,
        focus_areas: Optional[List[str]] = None,
    ) -> ParallelCodingResult:
        """
        Run parallel code review on a project.

        Each agent reviews with their specialty:
        - ChatGPT: Code quality, patterns, bugs
        - Gemini: Architecture, innovation opportunities
        - Grok Reasoner: Logic, security, edge cases
        - Grok Coder: Performance, optimization
        """
        start_time = time.time()
        focus = focus_areas or ["security", "performance", "code_quality", "architecture"]

        # Gather project files
        files_to_review = self._gather_project_files(project_path)

        if not files_to_review:
            return ParallelCodingResult(
                session_id=self.session_id,
                project_path=project_path,
                task_type=TaskType.CODE_REVIEW,
                success=False,
                total_time=0,
                agent_results={},
                proposed_fixes=[],
                summary="No files found to review",
                errors=["No reviewable files found in project"]
            )

        # Create tasks for each agent with their specialty
        tasks = self._create_review_tasks(files_to_review, focus, project_path)

        # Execute in parallel
        results = await self._execute_parallel_tasks(tasks)

        # Collect and merge results
        proposed_fixes = self._extract_fixes(results)
        summary = self._generate_summary(results, TaskType.CODE_REVIEW)

        total_time = time.time() - start_time

        result = ParallelCodingResult(
            session_id=self.session_id,
            project_path=project_path,
            task_type=TaskType.CODE_REVIEW,
            success=True,
            total_time=total_time,
            agent_results=results,
            proposed_fixes=proposed_fixes,
            summary=summary
        )

        # Save results
        self._save_results(result)

        return result

    async def fix_issues(
        self,
        issues: List[Dict[str, Any]],
        project_path: str,
        auto_apply: bool = False
    ) -> ParallelCodingResult:
        """
        Fix multiple issues in parallel.

        Each agent works on different files/issues simultaneously.
        """
        start_time = time.time()

        # Distribute issues across agents
        agent_assignments = self._distribute_issues(issues)

        # Create fix tasks
        tasks = []
        for agent_name, agent_issues in agent_assignments.items():
            for issue in agent_issues:
                task = CodeTask(
                    task_id=f"fix_{len(tasks)}",
                    task_type=TaskType.BUG_FIX,
                    description=f"Fix: {issue.get('description', 'Unknown issue')}",
                    file_path=issue.get('file_path'),
                    code_snippet=issue.get('code'),
                    context=f"Project: {project_path}\nIssue Type: {issue.get('type', 'bug')}",
                    assigned_agent=agent_name
                )
                tasks.append(task)

        # Execute fixes in parallel
        results = await self._execute_parallel_tasks(tasks)

        # Extract proposed fixes
        proposed_fixes = self._extract_fixes(results)

        # Auto-apply if requested
        if auto_apply and proposed_fixes:
            await self._apply_fixes(proposed_fixes, project_path)

        total_time = time.time() - start_time

        return ParallelCodingResult(
            session_id=self.session_id,
            project_path=project_path,
            task_type=TaskType.BUG_FIX,
            success=True,
            total_time=total_time,
            agent_results=results,
            proposed_fixes=proposed_fixes,
            summary=f"Generated {len(proposed_fixes)} fixes from {len(issues)} issues"
        )

    async def implement_feature(
        self,
        feature_description: str,
        project_path: str,
        specifications: Optional[Dict[str, Any]] = None
    ) -> ParallelCodingResult:
        """
        Implement a feature with parallel agent contributions.

        - ChatGPT: Core implementation
        - Gemini: UI/UX components
        - Grok Reasoner: Architecture decisions
        - Grok Coder: Utility functions, tests
        """
        start_time = time.time()
        specs = specifications or {}

        # Phase 1: Architecture discussion (consensus)
        arch_result = await self.team.collaborate(
            prompt=f"""
            Design the architecture for this feature:

            Feature: {feature_description}
            Project: {project_path}
            Specs: {json.dumps(specs, indent=2)}

            Provide:
            1. Component breakdown
            2. Files to create/modify
            3. Data models needed
            4. Integration points
            """,
            mode="consensus"
        )

        # Phase 2: Parallel implementation
        impl_tasks = self._create_implementation_tasks(
            feature_description,
            arch_result.final_answer,
            project_path
        )

        results = await self._execute_parallel_tasks(impl_tasks)

        total_time = time.time() - start_time

        return ParallelCodingResult(
            session_id=self.session_id,
            project_path=project_path,
            task_type=TaskType.FEATURE_IMPL,
            success=True,
            total_time=total_time,
            agent_results={
                "architecture": arch_result.final_answer,
                "implementation": results
            },
            proposed_fixes=[],
            summary=f"Feature implementation complete: {feature_description[:50]}..."
        )

    async def security_audit(
        self,
        project_path: str,
        severity_threshold: str = "medium"
    ) -> ParallelCodingResult:
        """
        Run parallel security audit with all agents.

        Each agent focuses on different vulnerability types:
        - Injection attacks
        - Authentication/Authorization
        - Data exposure
        - Cryptographic issues
        """
        start_time = time.time()

        files = self._gather_project_files(project_path)

        # Security-focused prompts for each agent
        security_tasks = [
            CodeTask(
                task_id="sec_injection",
                task_type=TaskType.SECURITY_AUDIT,
                description="Check for injection vulnerabilities (SQL, command, XSS)",
                context=f"Files: {len(files)} | Focus: OWASP Top 10 Injection",
                assigned_agent="chatgpt-coder"
            ),
            CodeTask(
                task_id="sec_auth",
                task_type=TaskType.SECURITY_AUDIT,
                description="Audit authentication and authorization",
                context=f"Files: {len(files)} | Focus: Auth bypass, session management",
                assigned_agent="gemini-creative"
            ),
            CodeTask(
                task_id="sec_data",
                task_type=TaskType.SECURITY_AUDIT,
                description="Check for sensitive data exposure",
                context=f"Files: {len(files)} | Focus: Secrets, PII, logging",
                assigned_agent="grok-reasoner"
            ),
            CodeTask(
                task_id="sec_crypto",
                task_type=TaskType.SECURITY_AUDIT,
                description="Audit cryptographic implementations",
                context=f"Files: {len(files)} | Focus: Hashing, encryption, randomness",
                assigned_agent="grok-coder"
            ),
        ]

        # Read key security-relevant files
        security_files = self._identify_security_files(files, project_path)
        code_context = self._read_files_for_context(security_files[:10])  # Limit

        for task in security_tasks:
            task.code_snippet = code_context

        results = await self._execute_parallel_tasks(security_tasks)

        # Compile findings
        proposed_fixes = self._extract_fixes(results)
        summary = self._generate_security_summary(results)

        total_time = time.time() - start_time

        return ParallelCodingResult(
            session_id=self.session_id,
            project_path=project_path,
            task_type=TaskType.SECURITY_AUDIT,
            success=True,
            total_time=total_time,
            agent_results=results,
            proposed_fixes=proposed_fixes,
            summary=summary
        )

    def _gather_project_files(
        self,
        project_path: str,
        extensions: Optional[List[str]] = None
    ) -> List[Path]:
        """Gather relevant project files"""
        exts = extensions or ['.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.go', '.rs']
        project = Path(project_path)

        if not project.exists():
            return []

        files = []
        for ext in exts:
            files.extend(project.rglob(f"*{ext}"))

        # Filter out common excludes
        excludes = ['node_modules', 'venv', '.git', '__pycache__', 'dist', 'build']
        files = [f for f in files if not any(ex in str(f) for ex in excludes)]

        return files[:50]  # Limit to prevent context overflow

    def _create_review_tasks(
        self,
        files: List[Path],
        focus_areas: List[str],
        project_path: str
    ) -> List[CodeTask]:
        """Create review tasks distributed across agents"""
        tasks = []
        agents = list(self.team.agents.keys())

        # Read file contents
        file_contents = {}
        for f in files[:20]:  # Limit files
            try:
                file_contents[str(f)] = f.read_text()[:5000]  # Truncate
            except Exception:
                logger.debug("Failed to read file for review: %s", f)

        # Create specialized review tasks
        task_configs = [
            ("chatgpt-coder", "code_quality", "Review code quality, patterns, and potential bugs"),
            ("gemini-creative", "architecture", "Review architecture and suggest improvements"),
            ("grok-reasoner", "security", "Review for security vulnerabilities and logic issues"),
            ("grok-coder", "performance", "Review for performance issues and optimizations"),
        ]

        for agent_name, focus, description in task_configs:
            if agent_name in agents:
                code_sample = "\n\n---\n\n".join(
                    f"# {path}\n{content[:2000]}"
                    for path, content in list(file_contents.items())[:5]
                )

                tasks.append(CodeTask(
                    task_id=f"review_{focus}",
                    task_type=TaskType.CODE_REVIEW,
                    description=description,
                    code_snippet=code_sample,
                    context=f"Project: {project_path}\nFocus: {focus}\nFiles: {len(files)}",
                    assigned_agent=agent_name
                ))

        return tasks

    def _create_implementation_tasks(
        self,
        feature: str,
        architecture: str,
        project_path: str
    ) -> List[CodeTask]:
        """Create implementation tasks from architecture"""
        tasks = []

        # Parse architecture to identify components
        # This is simplified - in production would parse more intelligently
        task_configs = [
            ("chatgpt-coder", "core", "Implement the core business logic"),
            ("gemini-creative", "interface", "Design and implement user-facing components"),
            ("grok-coder", "utilities", "Implement utility functions and helpers"),
        ]

        for agent, component, desc in task_configs:
            tasks.append(CodeTask(
                task_id=f"impl_{component}",
                task_type=TaskType.FEATURE_IMPL,
                description=f"{desc}\n\nFeature: {feature}",
                context=f"Architecture:\n{architecture}\n\nProject: {project_path}",
                assigned_agent=agent
            ))

        return tasks

    def _distribute_issues(
        self,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Distribute issues across available agents"""
        agents = list(self.team.agents.keys())
        if not agents:
            return {}

        distribution = {agent: [] for agent in agents}

        for i, issue in enumerate(issues):
            # Round-robin distribution
            agent = agents[i % len(agents)]
            distribution[agent].append(issue)

        return distribution

    async def _execute_parallel_tasks(
        self,
        tasks: List[CodeTask]
    ) -> Dict[str, Any]:
        """Execute tasks in parallel across agents"""
        results = {}

        # Group tasks by agent
        agent_tasks = {}
        for task in tasks:
            agent_name = task.assigned_agent or list(self.team.agents.keys())[0]
            if agent_name not in agent_tasks:
                agent_tasks[agent_name] = []
            agent_tasks[agent_name].append(task)

        # Execute each agent's tasks
        async def run_agent_tasks(agent_name: str, agent_task_list: List[CodeTask]):
            agent = self.team.agents.get(agent_name)
            if not agent:
                return agent_name, {"error": f"Agent {agent_name} not available"}

            task_results = []
            for task in agent_task_list:
                prompt = f"""
                TASK: {task.description}
                TYPE: {task.task_type.value}

                {f'CODE TO REVIEW:' if task.code_snippet else ''}
                {task.code_snippet or ''}

                CONTEXT:
                {task.context}

                Provide your analysis and any recommended code changes.
                If proposing fixes, format them clearly with:
                - File path
                - Original code (if replacing)
                - New/fixed code
                - Explanation
                """

                response = await agent.generate_response(prompt, "")
                task_results.append({
                    "task_id": task.task_id,
                    "success": response.success,
                    "content": response.content if response.success else response.error,
                    "confidence": response.confidence
                })

            return agent_name, task_results

        # Run all agents in parallel
        agent_coroutines = [
            run_agent_tasks(agent_name, task_list)
            for agent_name, task_list in agent_tasks.items()
        ]

        completed = await asyncio.gather(*agent_coroutines, return_exceptions=True)

        for result in completed:
            if isinstance(result, tuple):
                agent_name, agent_results = result
                results[agent_name] = agent_results
            elif isinstance(result, Exception):
                logger.error(f"Agent task failed: {result}")

        return results

    def _extract_fixes(self, results: Dict[str, Any]) -> List[CodeFix]:
        """Extract proposed code fixes from agent results"""
        fixes = []

        for agent_name, agent_results in results.items():
            if not isinstance(agent_results, list):
                continue

            for result in agent_results:
                if not result.get("success"):
                    continue

                content = result.get("content", "")

                # Simple extraction - look for code blocks with fix indicators
                # In production, would use more sophisticated parsing
                if "```" in content and ("fix" in content.lower() or "replace" in content.lower()):
                    fixes.append(CodeFix(
                        file_path="extracted",
                        original_code="",
                        fixed_code=content,
                        description=f"Fix from {agent_name}",
                        agent_name=agent_name,
                        confidence=result.get("confidence", 0.5)
                    ))

        return fixes

    async def _apply_fixes(
        self,
        fixes: List[CodeFix],
        project_path: str
    ):
        """Apply fixes to the codebase"""
        # This would integrate with Claude Bridge for terminal access
        # or write files directly
        logger.info(f"Would apply {len(fixes)} fixes to {project_path}")
        # Implementation depends on bridge availability

    def _identify_security_files(
        self,
        files: List[Path],
        project_path: str
    ) -> List[Path]:
        """Identify security-relevant files"""
        security_keywords = [
            'auth', 'login', 'password', 'token', 'session',
            'user', 'admin', 'crypto', 'secret', 'key', 'api'
        ]

        security_files = []
        for f in files:
            name_lower = f.name.lower()
            if any(kw in name_lower for kw in security_keywords):
                security_files.append(f)

        # Also check for common security files
        for name in ['main.py', 'app.py', 'routes.py', 'views.py', 'config.py']:
            for f in files:
                if f.name == name:
                    security_files.append(f)

        return list(set(security_files))

    def _read_files_for_context(self, files: List[Path]) -> str:
        """Read files and format for context"""
        content_parts = []
        for f in files:
            try:
                text = f.read_text()[:3000]
                content_parts.append(f"# File: {f.name}\n{text}")
            except Exception:
                logger.debug("Failed to read file for summary: %s", f)
        return "\n\n---\n\n".join(content_parts)

    def _generate_summary(
        self,
        results: Dict[str, Any],
        task_type: TaskType
    ) -> str:
        """Generate summary from results"""
        successful = 0
        total = 0

        for agent_results in results.values():
            if isinstance(agent_results, list):
                for r in agent_results:
                    total += 1
                    if r.get("success"):
                        successful += 1

        return f"{task_type.value.replace('_', ' ').title()}: {successful}/{total} tasks completed successfully"

    def _generate_security_summary(self, results: Dict[str, Any]) -> str:
        """Generate security-focused summary"""
        findings = []
        for agent_name, agent_results in results.items():
            if isinstance(agent_results, list):
                for r in agent_results:
                    if r.get("success") and r.get("content"):
                        # Look for severity indicators
                        content = r.get("content", "").lower()
                        if "critical" in content:
                            findings.append(f"CRITICAL finding from {agent_name}")
                        elif "high" in content:
                            findings.append(f"High severity finding from {agent_name}")

        return f"Security Audit Complete. Findings: {len(findings)} notable issues identified."

    def _save_results(self, result: ParallelCodingResult):
        """Save results to file"""
        output_file = self.results_dir / f"{result.session_id}.json"

        # Convert to serializable format
        data = {
            "session_id": result.session_id,
            "project_path": result.project_path,
            "task_type": result.task_type.value,
            "success": result.success,
            "total_time": result.total_time,
            "summary": result.summary,
            "timestamp": result.timestamp.isoformat(),
            "agent_results": result.agent_results,
            "proposed_fixes": [
                {
                    "file_path": f.file_path,
                    "description": f.description,
                    "agent_name": f.agent_name,
                    "confidence": f.confidence
                }
                for f in result.proposed_fixes
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Results saved to {output_file}")


# Convenience function
def create_parallel_engine(team: Optional[AIDevTeam] = None) -> ParallelCodingEngine:
    """Create a parallel coding engine"""
    return ParallelCodingEngine(team)
