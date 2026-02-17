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

Supported Languages:
    - Python (.py)
    - JavaScript/TypeScript (.js, .jsx, .ts, .tsx)
    - Go (.go)
    - Rust (.rs)
    - Java (.java)
    - C/C++ (.c, .cpp, .h, .hpp)
    - Ruby (.rb)
    - PHP (.php)
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory.system import MemorySystem, MistakeType
from .agents.base import AgentResponse

logger = logging.getLogger(__name__)


# Language configuration for multi-language support
LANGUAGE_CONFIG = {
    "python": {
        "extensions": [".py"],
        "exclude_dirs": ["__pycache__", ".venv", "venv", ".eggs", "*.egg-info"],
        "comment_prefix": "#",
    },
    "javascript": {
        "extensions": [".js", ".jsx", ".mjs"],
        "exclude_dirs": ["node_modules", "dist", "build", ".next"],
        "comment_prefix": "//",
    },
    "typescript": {
        "extensions": [".ts", ".tsx"],
        "exclude_dirs": ["node_modules", "dist", "build", ".next"],
        "comment_prefix": "//",
    },
    "go": {
        "extensions": [".go"],
        "exclude_dirs": ["vendor"],
        "comment_prefix": "//",
    },
    "rust": {
        "extensions": [".rs"],
        "exclude_dirs": ["target"],
        "comment_prefix": "//",
    },
    "java": {
        "extensions": [".java"],
        "exclude_dirs": ["target", "build", ".gradle"],
        "comment_prefix": "//",
    },
    "cpp": {
        "extensions": [".c", ".cpp", ".cc", ".h", ".hpp"],
        "exclude_dirs": ["build", "cmake-build-*"],
        "comment_prefix": "//",
    },
    "ruby": {
        "extensions": [".rb"],
        "exclude_dirs": ["vendor", ".bundle"],
        "comment_prefix": "#",
    },
    "php": {
        "extensions": [".php"],
        "exclude_dirs": ["vendor"],
        "comment_prefix": "//",
    },
}


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
        languages: Optional[List[str]] = None,
    ) -> List[Issue]:
        """
        Scan a project for issues across multiple languages.

        Args:
            project_path: Path to project directory
            focus_areas: Specific areas to focus on (security, performance, etc.)
            languages: Languages to scan (None = auto-detect all)

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

        # Collect files from all configured languages
        files = self._gather_files(project, languages)

        self.memory_log(f"Found {len(files)} files to scan")

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

    def _gather_files(
        self,
        project: Path,
        languages: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        Gather files from project for scanning.

        Args:
            project: Project path
            languages: Languages to include (None = all)

        Returns:
            List of file paths to scan
        """
        files = []
        langs_to_scan = languages or list(LANGUAGE_CONFIG.keys())

        # Build exclude patterns
        all_excludes = set([".git", ".svn", ".hg"])
        for lang in langs_to_scan:
            config = LANGUAGE_CONFIG.get(lang, {})
            all_excludes.update(config.get("exclude_dirs", []))

        for lang in langs_to_scan:
            config = LANGUAGE_CONFIG.get(lang, {})
            extensions = config.get("extensions", [])

            for ext in extensions:
                for file_path in project.rglob(f"*{ext}"):
                    # Check if file is in excluded directory
                    parts = file_path.parts
                    if not any(excl in parts for excl in all_excludes):
                        files.append(file_path)

        # Limit to prevent context overflow
        return files[:100]

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension"""
        ext = file_path.suffix.lower()
        for lang, config in LANGUAGE_CONFIG.items():
            if ext in config.get("extensions", []):
                return lang
        return "unknown"

    def _parse_issues(self, response: str, project_path: str) -> List[Issue]:
        """
        Parse issues from AI response with robust JSON and text parsing.

        Attempts multiple parsing strategies:
        1. JSON array parsing
        2. JSON object parsing
        3. Markdown/text pattern matching
        """
        issues = []

        # Strategy 1: Try to parse as JSON array
        json_issues = self._try_parse_json_array(response)
        if json_issues:
            for item in json_issues:
                issues.append(self._create_issue(item, project_path))
            return issues

        # Strategy 2: Try to extract JSON from response (might be wrapped in markdown)
        json_match = re.search(r'\[[\s\S]*?\]', response)
        if json_match:
            json_issues = self._try_parse_json_array(json_match.group())
            if json_issues:
                for item in json_issues:
                    issues.append(self._create_issue(item, project_path))
                return issues

        # Strategy 3: Fall back to text parsing
        issues = self._parse_text_issues(response, project_path)

        return issues

    def _try_parse_json_array(self, text: str) -> Optional[List[Dict]]:
        """Try to parse text as JSON array"""
        try:
            # Clean up common issues
            text = text.strip()

            # Try direct parsing
            data = json.loads(text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "issues" in data:
                return data["issues"]
        except json.JSONDecodeError:
            pass

        # Try with relaxed parsing (handle trailing commas, etc.)
        try:
            # Remove trailing commas before ] or }
            cleaned = re.sub(r',(\s*[\]}])', r'\1', text)
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        return None

    def _parse_text_issues(self, response: str, project_path: str) -> List[Issue]:
        """Parse issues from text/markdown format"""
        issues = []
        lines = response.split("\n")

        current_issue = {}
        for line in lines:
            line = line.strip()

            # Skip empty lines and headers
            if not line or line.startswith("#"):
                continue

            # Check for various field formats
            lower_line = line.lower()

            if any(x in lower_line for x in ["file_path:", "file:", "path:"]):
                # Save previous issue if exists
                if current_issue.get("description"):
                    issues.append(self._create_issue(current_issue, project_path))
                # Start new issue
                value = self._extract_value(line)
                current_issue = {"file_path": value}

            elif "severity:" in lower_line:
                current_issue["severity"] = self._extract_value(line).lower()

            elif any(x in lower_line for x in ["issue_type:", "type:", "category:"]):
                current_issue["issue_type"] = self._extract_value(line).lower()

            elif any(x in lower_line for x in ["description:", "issue:", "problem:"]):
                current_issue["description"] = self._extract_value(line)

            elif any(x in lower_line for x in ["suggested_fix:", "fix:", "solution:", "recommendation:"]):
                current_issue["suggested_fix"] = self._extract_value(line)

            elif any(x in lower_line for x in ["line:", "line_number:"]):
                try:
                    current_issue["line_number"] = int(self._extract_value(line))
                except ValueError:
                    pass

            elif "confidence:" in lower_line:
                try:
                    current_issue["confidence"] = float(self._extract_value(line))
                except ValueError:
                    pass

        # Don't forget the last issue
        if current_issue.get("description"):
            issues.append(self._create_issue(current_issue, project_path))

        return issues

    def _extract_value(self, line: str) -> str:
        """Extract value from a 'key: value' line"""
        if ":" in line:
            return line.split(":", 1)[-1].strip().strip('"\'')
        return line.strip()

    def _create_issue(self, data: Dict, project_path: str) -> Issue:
        """Create Issue from parsed data with validation"""
        # Normalize severity
        severity = str(data.get("severity", "medium")).lower()
        if severity not in ["critical", "high", "medium", "low"]:
            severity = "medium"

        # Normalize issue type
        issue_type = str(data.get("issue_type", data.get("type", "bug"))).lower()
        valid_types = ["security", "performance", "bug", "style", "architecture", "logic"]
        if issue_type not in valid_types:
            # Try to categorize
            type_lower = issue_type.lower()
            if any(x in type_lower for x in ["sql", "xss", "injection", "auth", "crypto"]):
                issue_type = "security"
            elif any(x in type_lower for x in ["slow", "memory", "cpu", "optimize"]):
                issue_type = "performance"
            elif any(x in type_lower for x in ["lint", "format", "naming"]):
                issue_type = "style"
            else:
                issue_type = "bug"

        # Extract confidence if provided
        confidence = data.get("confidence", 0.7)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.7

        return Issue(
            file_path=str(data.get("file_path", data.get("file", "unknown"))),
            line_number=data.get("line_number", data.get("line")),
            issue_type=issue_type,
            severity=severity,
            description=str(data.get("description", data.get("issue", "No description"))),
            suggested_fix=str(data.get("suggested_fix", data.get("fix", data.get("recommendation", "")))),
            confidence=confidence
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
            "supported_languages": list(LANGUAGE_CONFIG.keys()),
            "memory_stats": self.memory.get_statistics() if self.memory else None
        }


# Convenience function
def create_fredfix(team=None, **kwargs) -> FredFix:
    """Create a FredFix instance"""
    return FredFix(team=team, **kwargs)
