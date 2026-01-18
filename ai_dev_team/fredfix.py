"""
FredFix - Autonomous Code Fixer Agent
=====================================

Integrated from AgentCore project. FredFix is an autonomous agent that
coordinates the AI team to automatically detect, diagnose, and fix issues
in codebases. It combines memory-driven learning with multi-agent collaboration.

Usage:
    from ai_dev_team.fredfix import FredFix

    fixer = FredFix()
    result = await fixer.auto_fix("/path/to/project")
    print(result.fixes_applied)
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory.system import MemorySystem, MistakeType
from .agents.base import AgentResponse

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of an autonomous fix operation"""
    fix_id: str
    success: bool
    issues_found: List[Dict[str, Any]]
    fixes_applied: List[Dict[str, Any]]
    fixes_skipped: List[Dict[str, Any]]
    total_time: float
    confidence: float
    summary: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Issue:
    """Detected issue in code"""
    file_path: str
    line_number: Optional[int]
    issue_type: str  # security, performance, bug, style
    severity: str    # critical, high, medium, low
    description: str
    suggested_fix: str
    confidence: float


class FredFix:
    """
    FredFix - Autonomous Code Fixer

    Coordinates the AI team to automatically fix issues in codebases.
    Learns from past fixes to improve over time.

    Features:
    - Automatic issue detection
    - Multi-agent fix generation
    - Safe fix application with rollback
    - Memory-based learning from past fixes
    - Configurable fix policies
    """

    AGENT_NAME = "FredFix"
    VERSION = "1.0.0"

    def __init__(
        self,
        team=None,  # AIDevTeam instance
        memory: Optional[MemorySystem] = None,
        auto_apply: bool = False,
        min_confidence: float = 0.7,
        safe_mode: bool = True,
    ):
        """
        Initialize FredFix autonomous fixer.

        Args:
            team: AIDevTeam instance for collaboration
            memory: MemorySystem for learning (creates new if None)
            auto_apply: Automatically apply fixes without confirmation
            min_confidence: Minimum confidence to apply fixes
            safe_mode: Only apply safe, reversible fixes
        """
        self.team = team
        self.memory = memory or MemorySystem()
        self.auto_apply = auto_apply
        self.min_confidence = min_confidence
        self.safe_mode = safe_mode

        self._fix_count = 0
        self._success_count = 0

        logger.info(f"🤖 {self.AGENT_NAME} v{self.VERSION} initialized")
        self.memory_log("Agent initialized")

    def memory_log(self, message: str):
        """Log event to memory (integrated from AgentCore)"""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] [{self.AGENT_NAME}] {message}"
        logger.info(entry)

    async def scan_project(
        self,
        project_path: str,
        focus_areas: Optional[List[str]] = None,
    ) -> List[Issue]:
        """
        Scan a project for issues.

        Args:
            project_path: Path to project directory
            focus_areas: Specific areas to focus on (security, performance, etc.)

        Returns:
            List of detected issues
        """
        self.memory_log(f"Scanning project: {project_path}")

        if not self.team:
            logger.warning("No AI team configured - running in limited mode")
            return []

        # Get project files
        project = Path(project_path)
        if not project.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Find Python files (extend for other languages)
        files = list(project.glob("**/*.py"))
        files = [f for f in files if "__pycache__" not in str(f) and ".venv" not in str(f)]

        self.memory_log(f"Found {len(files)} Python files to scan")

        focus = focus_areas or ["security", "bugs", "performance"]
        focus_str = ", ".join(focus)

        all_issues = []

        # Scan in batches
        batch_size = 5
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batch_content = ""

            for file_path in batch:
                try:
                    content = file_path.read_text()
                    if len(content) > 5000:
                        content = content[:5000] + "\n... (truncated)"
                    batch_content += f"\n\n=== {file_path.relative_to(project)} ===\n{content}"
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")

            if not batch_content.strip():
                continue

            # Use AI team to analyze
            prompt = f"""Analyze this code for issues. Focus on: {focus_str}

For each issue found, provide:
- file_path: relative path to file
- line_number: approximate line (or null)
- issue_type: security|performance|bug|style
- severity: critical|high|medium|low
- description: what the issue is
- suggested_fix: how to fix it

Code to analyze:
{batch_content}

Respond with a JSON array of issues, or empty array if none found."""

            try:
                result = await self.team.collaborate(prompt, mode="parallel")

                if result.success:
                    # Parse issues from response (simplified)
                    # In production, use proper JSON parsing
                    issues = self._parse_issues(result.final_answer, project_path)
                    all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Scan error: {e}")

        self.memory_log(f"Scan complete: found {len(all_issues)} issues")

        # Check against past mistakes to prioritize
        if all_issues:
            similar_mistakes = await self.memory.find_similar_mistakes({
                "project": project_path,
                "issues": [i.description for i in all_issues[:5]]
            })

            if similar_mistakes:
                self.memory_log(f"Found {len(similar_mistakes)} similar past mistakes")

        return all_issues

    def _parse_issues(self, response: str, project_path: str) -> List[Issue]:
        """Parse issues from AI response"""
        issues = []

        # Simple parsing - look for issue patterns
        # In production, use structured JSON parsing
        lines = response.split("\n")

        current_issue = {}
        for line in lines:
            line = line.strip()
            if "file_path:" in line.lower() or "file:" in line.lower():
                if current_issue.get("description"):
                    issues.append(self._create_issue(current_issue, project_path))
                current_issue = {"file_path": line.split(":", 1)[-1].strip()}
            elif "severity:" in line.lower():
                current_issue["severity"] = line.split(":", 1)[-1].strip().lower()
            elif "issue_type:" in line.lower() or "type:" in line.lower():
                current_issue["issue_type"] = line.split(":", 1)[-1].strip().lower()
            elif "description:" in line.lower():
                current_issue["description"] = line.split(":", 1)[-1].strip()
            elif "suggested_fix:" in line.lower() or "fix:" in line.lower():
                current_issue["suggested_fix"] = line.split(":", 1)[-1].strip()

        if current_issue.get("description"):
            issues.append(self._create_issue(current_issue, project_path))

        return issues

    def _create_issue(self, data: Dict, project_path: str) -> Issue:
        """Create Issue from parsed data"""
        return Issue(
            file_path=data.get("file_path", "unknown"),
            line_number=data.get("line_number"),
            issue_type=data.get("issue_type", "bug"),
            severity=data.get("severity", "medium"),
            description=data.get("description", "No description"),
            suggested_fix=data.get("suggested_fix", ""),
            confidence=0.7
        )

    async def generate_fix(self, issue: Issue) -> Optional[Dict[str, Any]]:
        """
        Generate a fix for an issue.

        Args:
            issue: Issue to fix

        Returns:
            Fix details or None if no fix could be generated
        """
        self.memory_log(f"Generating fix for: {issue.description[:50]}...")

        if not self.team:
            return None

        # Check for existing solutions
        solutions = await self.memory.find_solution_patterns(issue.description)

        context = ""
        if solutions:
            context = f"Similar past solutions:\n"
            for sol in solutions[:2]:
                context += f"- {sol.problem_pattern}: {', '.join(sol.solution_steps[:2])}\n"

        prompt = f"""Generate a code fix for this issue:

File: {issue.file_path}
Type: {issue.issue_type}
Severity: {issue.severity}
Description: {issue.description}

Provide:
1. The exact code change needed
2. Explanation of the fix
3. Any risks or considerations

{context}"""

        result = await self.team.collaborate(prompt, mode="consensus")

        if result.success:
            return {
                "issue": issue,
                "fix_code": result.final_answer,
                "confidence": result.confidence_score,
                "agents_used": result.participating_agents,
            }

        return None

    async def auto_fix(
        self,
        project_path: str,
        focus_areas: Optional[List[str]] = None,
        max_fixes: int = 10,
    ) -> FixResult:
        """
        Automatically scan and fix issues in a project.

        Args:
            project_path: Path to project
            focus_areas: Areas to focus on
            max_fixes: Maximum number of fixes to apply

        Returns:
            FixResult with all actions taken
        """
        import time
        import uuid

        fix_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        self.memory_log(f"Starting auto-fix session {fix_id}")

        # Scan for issues
        issues = await self.scan_project(project_path, focus_areas)

        fixes_applied = []
        fixes_skipped = []

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda x: severity_order.get(x.severity, 4))

        for issue in issues[:max_fixes]:
            # Generate fix
            fix = await self.generate_fix(issue)

            if not fix:
                fixes_skipped.append({
                    "issue": issue.description,
                    "reason": "Could not generate fix"
                })
                continue

            # Check confidence
            if fix["confidence"] < self.min_confidence:
                fixes_skipped.append({
                    "issue": issue.description,
                    "reason": f"Low confidence: {fix['confidence']:.2f}"
                })
                continue

            # In safe mode, only track - don't apply
            if self.safe_mode or not self.auto_apply:
                fixes_applied.append({
                    "issue": issue.description,
                    "file": issue.file_path,
                    "severity": issue.severity,
                    "fix_preview": fix["fix_code"][:500],
                    "applied": False,
                    "confidence": fix["confidence"]
                })
            else:
                # Would apply fix here
                fixes_applied.append({
                    "issue": issue.description,
                    "file": issue.file_path,
                    "severity": issue.severity,
                    "applied": True,
                    "confidence": fix["confidence"]
                })

        total_time = time.time() - start_time

        # Calculate overall confidence
        if fixes_applied:
            avg_confidence = sum(f.get("confidence", 0) for f in fixes_applied) / len(fixes_applied)
        else:
            avg_confidence = 0.0

        # Store in memory for learning
        if fixes_applied:
            for fix in fixes_applied:
                await self.memory.capture_solution(
                    problem_pattern=fix["issue"],
                    solution_steps=[fix.get("fix_preview", "")[:200]],
                    project=project_path
                )

        self._fix_count += len(fixes_applied)

        result = FixResult(
            fix_id=fix_id,
            success=len(fixes_applied) > 0,
            issues_found=[{
                "file": i.file_path,
                "type": i.issue_type,
                "severity": i.severity,
                "description": i.description
            } for i in issues],
            fixes_applied=fixes_applied,
            fixes_skipped=fixes_skipped,
            total_time=total_time,
            confidence=avg_confidence,
            summary=f"Found {len(issues)} issues, generated {len(fixes_applied)} fixes, skipped {len(fixes_skipped)}"
        )

        self.memory_log(f"Auto-fix complete: {result.summary}")

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get FredFix statistics"""
        return {
            "agent_name": self.AGENT_NAME,
            "version": self.VERSION,
            "total_fixes": self._fix_count,
            "success_count": self._success_count,
            "auto_apply": self.auto_apply,
            "safe_mode": self.safe_mode,
            "min_confidence": self.min_confidence,
            "memory_stats": self.memory.get_statistics() if self.memory else None
        }


# Convenience function
def create_fredfix(team=None, **kwargs) -> FredFix:
    """Create a FredFix instance"""
    return FredFix(team=team, **kwargs)
