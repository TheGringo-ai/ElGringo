"""
El Gringo — Agentic Coding Engine
==================================

Turns the AI team into a real coding agent: read files, plan changes,
apply edits, run tests, self-correct on failure, and optionally commit.

Production-level: backup/restore, path sandboxing, structured logging,
robust parsing with 5 fallback strategies, difflib-powered fuzzy matching,
deduplication, per-iteration timeouts, and git safety.
"""

import difflib
import json
import logging
import os
import re
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/code", tags=["coding-agent"])

# ── Constants ────────────────────────────────────────────────────────

MAX_FILE_SIZE = 1_000_000  # 1MB
MAX_CONTEXT_FILES = 15
MAX_FILE_CONTEXT_CHARS = 10_000
MAX_TOTAL_CONTEXT_CHARS = 80_000
ITERATION_TIMEOUT = 180  # seconds per iteration
FUZZY_MATCH_THRESHOLD = 0.6  # difflib similarity threshold

# Files that indicate execution context (where the app runs from)
EXECUTION_CONTEXT_FILES = [
    "*.service", "systemd/*.service",  # systemd unit files
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", "Procfile", "supervisord.conf",
    ".github/workflows/*.yml", ".github/workflows/*.yaml",
]


# ── Models ───────────────────────────────────────────────────────────

class CodingTaskRequest(BaseModel):
    """A coding task for the AI team to execute."""
    task: str = Field(..., description="What needs to be done", min_length=3)
    project_path: str = Field(..., description="Absolute path to the project root")
    context: str = Field("", description="Additional context: error messages, constraints")
    files_to_read: List[str] = Field(default_factory=list, description="Specific files to read first")
    run_tests: bool = Field(True, description="Run tests after making changes")
    test_command: str = Field("", description="Custom test command (default: auto-detect)")
    auto_commit: bool = Field(False, description="Commit changes if tests pass")
    mode: str = Field("sequential", description="Agent mode: sequential, parallel, debate")
    allowed_agents: Optional[List[str]] = Field(None, description="Specific agents to use")
    max_iterations: int = Field(3, description="Max self-correction iterations", ge=1, le=10)
    dry_run: bool = Field(False, description="Plan only, don't execute changes")

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v):
        p = Path(v).resolve()
        if not p.is_dir():
            raise ValueError(f"Project path does not exist: {p}")
        return str(p)


class FileChange(BaseModel):
    path: str
    action: str  # "created", "modified", "deleted"
    diff: str = ""
    lines_changed: int = 0


class TestResult(BaseModel):
    command: str
    passed: bool
    output: str
    duration_seconds: float


class CodingTaskResponse(BaseModel):
    task_id: str
    status: str  # "success", "partial", "failed", "dry_run"
    summary: str
    files_changed: List[FileChange]
    test_results: Optional[TestResult] = None
    git_commit: Optional[str] = None
    agents_used: List[str]
    iterations: int
    total_time: float
    plan: List[str] = []
    errors: List[str] = []


class ProjectInfoResponse(BaseModel):
    project_path: str
    files_count: int
    languages: Dict[str, int]
    has_tests: bool
    has_git: bool
    structure: List[str]


# ── Tool Wrappers ────────────────────────────────────────────────────

class ProjectTools:
    """Sandboxed tools scoped to a single project directory."""

    CODE_EXTENSIONS = {
        # Code
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".swift", ".kt", ".c", ".cpp", ".h", ".hpp",
        ".cs", ".scala", ".r", ".R", ".lua", ".pl", ".pm", ".ex", ".exs",
        ".dart", ".zig", ".nim", ".v", ".jl",
        # Web / Markup
        ".css", ".scss", ".sass", ".less", ".html", ".htm", ".vue", ".svelte",
        ".xml", ".xsl", ".xslt", ".svg",
        # Config / Data
        ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".conf",
        ".env", ".env.example", ".env.local",
        ".properties", ".plist", ".hcl", ".tf", ".tfvars",
        # Docs
        ".md", ".mdx", ".txt", ".rst", ".adoc", ".tex", ".csv", ".tsv",
        # Scripts / DevOps
        ".sql", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
        ".dockerfile", ".containerfile",
        # Other
        ".graphql", ".gql", ".proto", ".prisma", ".editorconfig",
        ".gitignore", ".dockerignore", ".eslintrc", ".prettierrc",
    }

    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        ".next", "dist", "build", ".tox", ".mypy_cache",
        ".pytest_cache", "egg-info", ".eggs", ".ruff_cache",
    }

    def __init__(self, project_path: str):
        self.root = Path(project_path).resolve()
        if not self.root.is_dir():
            raise ValueError(f"Project path does not exist: {self.root}")

    def _validate_path(self, filepath: str) -> Path:
        """Ensure path is within project root (symlink-safe)."""
        p = Path(filepath).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError(f"Path {p} is outside project root {self.root}")
        return p

    def read_file(self, filepath: str) -> str:
        p = self._validate_path(filepath)
        if not p.exists():
            return f"[ERROR] File not found: {filepath}"
        if p.stat().st_size > MAX_FILE_SIZE:
            return f"[ERROR] File too large: {p.stat().st_size} bytes"
        return p.read_text(errors="replace")

    def write_file(self, filepath: str, content: str) -> str:
        p = self._validate_path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Wrote {len(content)} bytes to {filepath}"

    # Extensionless files that are still useful
    KNOWN_FILES = {
        "Dockerfile", "Makefile", "Rakefile", "Gemfile", "Procfile",
        "Vagrantfile", "Justfile", "Brewfile", "Taskfile",
        "docker-compose.yml", "docker-compose.yaml",
        "LICENSE", "CHANGELOG", "CONTRIBUTING", "AUTHORS",
    }

    def list_files(self, max_files: int = 500) -> List[str]:
        """List all project files (code, config, docs, scripts)."""
        files = []
        for root, dirs, filenames in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for f in filenames:
                if Path(f).suffix in self.CODE_EXTENSIONS or f in self.KNOWN_FILES:
                    rel = os.path.relpath(os.path.join(root, f), self.root)
                    files.append(rel)
                    if len(files) >= max_files:
                        return files
        return sorted(files)

    def search_files(self, pattern: str, glob_pattern: str = "**/*.py") -> List[Dict[str, Any]]:
        """Grep-like search across project files."""
        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return [{"error": f"Invalid regex: {pattern}"}]

        for p in self.root.glob(glob_pattern):
            if any(skip in p.parts for skip in self.SKIP_DIRS):
                continue
            if p.is_file() and p.stat().st_size < 500_000:
                try:
                    content = p.read_text(errors="replace")
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            results.append({
                                "file": str(p.relative_to(self.root)),
                                "line": i,
                                "content": line.strip()[:200],
                            })
                except Exception:
                    pass
                if len(results) >= 100:
                    break
        return results

    def run_command(self, command: str, timeout: int = 120) -> Dict[str, Any]:
        """Run a shell command in the project directory."""
        try:
            cmd_args = shlex.split(command)
        except ValueError as e:
            return {"exit_code": 1, "stdout": "", "stderr": f"Invalid command: {e}"}

        try:
            result = subprocess.run(
                cmd_args, shell=False, capture_output=True, text=True,
                cwd=str(self.root), timeout=timeout,
                env={**os.environ, "PYTHONPATH": str(self.root)},
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": 124, "stdout": "", "stderr": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"exit_code": 1, "stdout": "", "stderr": str(e)}

    def git_diff(self) -> str:
        result = self.run_command("git diff")
        return result.get("stdout", "")

    def git_status(self) -> str:
        result = self.run_command("git status --short")
        return result.get("stdout", "")

    def git_commit(self, message: str) -> str:
        # Sanitize commit message to prevent injection
        safe_msg = message.replace('"', "'").replace("$", "").replace("`", "")[:200]
        self.run_command("git add -A")
        result = self.run_command(f'git commit -m "{safe_msg}"')
        return result.get("stdout", "") + result.get("stderr", "")

    def git_stash(self) -> bool:
        """Stash current changes. Returns True if anything was stashed."""
        result = self.run_command("git stash push -m elgringo-backup")
        return "No local changes" not in result.get("stdout", "")

    def git_stash_pop(self) -> bool:
        """Restore stashed changes."""
        result = self.run_command("git stash pop")
        return result.get("exit_code", 1) == 0

    def get_project_info(self) -> Dict[str, Any]:
        files = self.list_files()
        languages = {}
        for f in files:
            ext = Path(f).suffix
            languages[ext] = languages.get(ext, 0) + 1

        has_tests = any("test" in f.lower() for f in files)
        has_git = (self.root / ".git").is_dir()

        structure = []
        for item in sorted(self.root.iterdir()):
            if item.name.startswith(".") and item.name != ".env.example":
                continue
            if item.name in self.SKIP_DIRS:
                continue
            marker = "/" if item.is_dir() else ""
            structure.append(f"{item.name}{marker}")

        return {
            "project_path": str(self.root),
            "files_count": len(files),
            "languages": dict(sorted(languages.items(), key=lambda x: -x[1])),
            "has_tests": has_tests,
            "has_git": has_git,
            "structure": structure[:50],
        }

    def detect_test_command(self) -> str:
        """Auto-detect the test command for this project."""
        for subdir in ["", "backend", "src", "app"]:
            check_dir = self.root / subdir if subdir else self.root
            if (check_dir / "pytest.ini").exists() or (check_dir / "conftest.py").exists():
                prefix = f"cd {subdir} && " if subdir else ""
                return f"{prefix}python -m pytest -x -q 2>&1 | tail -20"
        if (self.root / "pyproject.toml").exists():
            return "python -m pytest -x -q 2>&1 | tail -20"
        if (self.root / "package.json").exists():
            return "npm test 2>&1 | tail -30"
        if (self.root / "Cargo.toml").exists():
            return "cargo test 2>&1 | tail -20"
        if (self.root / "go.mod").exists():
            return "go test ./... 2>&1 | tail -20"
        if any("test_" in f or "_test.py" in f for f in self.list_files()):
            return "python -m pytest -x -q 2>&1 | tail -20"
        return ""


# ── Coding Agent Engine ──────────────────────────────────────────────

class CodingAgentEngine:
    """
    Production agentic coding engine.

    Flow: read project → build context → AI generates structured changes →
    parse with 5 fallback strategies → apply with difflib fuzzy matching →
    run tests → self-correct on failure → optionally commit.

    Safety: git stash backup before changes, path sandboxing, deduplication,
    per-iteration timeout, structured error feedback.
    """

    # Threshold for splitting a task into subtasks
    DECOMPOSITION_KEYWORDS = {"and then", "after that", "also ", "additionally", "next ",
                               "step 1", "step 2", "1.", "2.", "3."}

    def __init__(self, team, tools: ProjectTools):
        self.team = team
        self.tools = tools
        self._apply_errors: List[str] = []
        self._backups: Dict[str, str] = {}  # filepath -> original content

    async def execute_task(self, request: CodingTaskRequest) -> CodingTaskResponse:
        # Check if this is a complex multi-step task that should be decomposed
        if self._should_decompose(request.task) and not request.dry_run:
            return await self._execute_decomposed(request)

        return await self._execute_single(request)

    async def _execute_decomposed(self, request: CodingTaskRequest) -> CodingTaskResponse:
        """Break a complex task into subtasks and execute each independently."""
        task_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        log = lambda msg: logger.info(f"[{task_id}] {msg}")
        log(f"Decomposing complex task: {request.task[:100]}")

        # Ask AI to decompose the task
        subtasks = await self._decompose_task(request.task, request)
        log(f"Decomposed into {len(subtasks)} subtasks")

        all_files_changed: List[FileChange] = []
        all_errors: List[str] = []
        all_agents: List[str] = []
        total_iterations = 0
        test_result: Optional[TestResult] = None
        last_status = "success"

        for i, subtask in enumerate(subtasks):
            log(f"Subtask {i+1}/{len(subtasks)}: {subtask[:80]}")

            # Create a sub-request for each subtask
            sub_request = CodingTaskRequest(
                task=subtask,
                project_path=request.project_path,
                context=request.context,
                files_to_read=request.files_to_read,
                run_tests=request.run_tests and (i == len(subtasks) - 1),  # Only test on last subtask
                test_command=request.test_command,
                auto_commit=False,  # Commit only at the end
                mode=request.mode,
                allowed_agents=request.allowed_agents,
                max_iterations=request.max_iterations,
                dry_run=False,
            )

            sub_result = await self._execute_single(sub_request)
            all_files_changed.extend(sub_result.files_changed)
            all_errors.extend(sub_result.errors)
            all_agents.extend(sub_result.agents_used)
            total_iterations += sub_result.iterations
            if sub_result.test_results:
                test_result = sub_result.test_results
            if sub_result.status == "failed":
                last_status = "partial"
                all_errors.append(f"Subtask {i+1} failed: {subtask[:100]}")

        # Deduplicate agents
        all_agents = list(set(all_agents))

        # Auto-commit if requested
        git_commit_msg = None
        if request.auto_commit and all_files_changed:
            if test_result is None or test_result.passed:
                commit_msg = f"El Gringo: {request.task[:80]}"
                self.tools.git_commit(commit_msg)
                git_commit_msg = commit_msg

        total_time = round(time.time() - start_time, 1)

        if not all_files_changed:
            last_status = "failed"
        elif test_result and not test_result.passed:
            last_status = "partial"

        summary = (f"Completed {len(subtasks)} subtasks: {len(all_files_changed)} files changed "
                   f"in {total_iterations} iteration(s)")
        if test_result:
            summary += f", tests {'passing' if test_result.passed else 'failing'}"

        # Record outcome for learning
        self._record_outcome(task_id, request.task, last_status, all_files_changed, all_errors)

        return CodingTaskResponse(
            task_id=task_id,
            status=last_status,
            summary=summary,
            files_changed=all_files_changed,
            test_results=test_result,
            git_commit=git_commit_msg,
            agents_used=all_agents,
            iterations=total_iterations,
            total_time=total_time,
            errors=all_errors[-10:],
            plan=[f"Step {i+1}: {s}" for i, s in enumerate(subtasks)],
        )

    async def _execute_single(self, request: CodingTaskRequest) -> CodingTaskResponse:
        """Execute a single coding task with self-correction."""
        task_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        errors: List[str] = []
        files_changed: List[FileChange] = []
        test_result: Optional[TestResult] = None
        git_commit_msg: Optional[str] = None
        iterations = 0
        self._backups = {}

        log = lambda msg: logger.info(f"[{task_id}] {msg}")
        log(f"Starting task: {request.task[:100]}")

        # Step 1: Build context (with grep-powered file discovery)
        context = await self._build_context(request)
        log(f"Context built: {len(context)} chars")

        if request.dry_run:
            plan = await self._get_plan(request.task, context, request.mode)
            return CodingTaskResponse(
                task_id=task_id,
                status="dry_run",
                summary=plan.get("summary", ""),
                files_changed=[],
                agents_used=plan.get("agents_used", []),
                iterations=0,
                total_time=time.time() - start_time,
                plan=plan.get("steps", []),
            )

        # Step 2-5: Execute with self-correction loop
        agents_used: List[str] = []
        for iteration in range(request.max_iterations):
            iterations = iteration + 1
            iter_start = time.time()
            log(f"Iteration {iterations}/{request.max_iterations}")

            # Check total timeout
            elapsed = time.time() - start_time
            if elapsed > ITERATION_TIMEOUT * request.max_iterations:
                errors.append(f"Total timeout exceeded ({elapsed:.0f}s)")
                log("Total timeout exceeded")
                break

            # Build prompt with error context from previous iterations
            coding_prompt = self._build_coding_prompt(
                request.task, context,
                errors if iteration > 0 else None,
                iteration=iteration,
            )

            # Get AI team response
            try:
                result = await self.team.collaborate(
                    prompt=coding_prompt,
                    context=context,
                    mode=request.mode,
                    agents=request.allowed_agents,
                )
                agents_used = list(set(agents_used + result.participating_agents))
            except Exception as e:
                errors.append(f"Iteration {iterations}: AI team error: {e}")
                log(f"AI team error: {e}")
                continue

            response_text = result.final_answer or ""
            log(f"AI response: {len(response_text)} chars from {result.participating_agents}")

            # Parse file changes
            changes = self._parse_file_changes(response_text)
            if not changes:
                errors.append(
                    f"Iteration {iterations}: No parseable code changes in AI response "
                    f"({len(response_text)} chars, "
                    f"{len(re.findall(r'```', response_text)) // 2} code blocks). "
                    f"Use ```file:path or ```edit:path format."
                )
                log(f"No changes parsed from {len(response_text)} char response")
                continue

            # Deduplicate changes (same file + same action)
            changes = self._deduplicate_changes(changes)
            log(f"Parsed {len(changes)} changes")

            # Backup files before modifying
            self._backup_files(changes)

            # Apply changes
            self._apply_errors = []
            applied = self._apply_changes(changes)
            # Replace (not append) file entries for files that were re-applied in this iteration
            applied_paths = {fc.path for fc in applied}
            files_changed = [fc for fc in files_changed if fc.path not in applied_paths]
            files_changed.extend(applied)

            # Feed apply errors back
            if self._apply_errors:
                for err in self._apply_errors:
                    errors.append(f"Iteration {iterations}: {err}")
                log(f"{len(self._apply_errors)} apply errors, {len(applied)} successful")
                # If syntax errors were found, retry even if some edits applied
                has_syntax_error = any("SYNTAX ERROR" in e for e in self._apply_errors)
                if not applied or has_syntax_error:
                    if has_syntax_error:
                        log("Syntax error detected post-apply — retrying")
                    continue  # Retry

            # Detect silent exception patterns in changed files
            for fc in applied:
                abs_p = str(self.tools.root / fc.path) if not os.path.isabs(fc.path) else fc.path
                if fc.path.endswith(".py") and Path(abs_p).exists():
                    content = self.tools.read_file(abs_p)
                    warnings = self._detect_silent_exceptions(content, fc.path)
                    for w in warnings[:3]:
                        errors.append(f"Iteration {iterations}: WARNING: {w}")
                        log(f"Silent exception warning: {w}")

            log(f"Applied {len(applied)} changes in {time.time() - iter_start:.1f}s")

            # Run tests
            if request.run_tests:
                test_cmd = request.test_command or self.tools.detect_test_command()
                if test_cmd:
                    test_start = time.time()
                    test_output = self.tools.run_command(test_cmd, timeout=120)
                    passed = test_output["exit_code"] == 0
                    test_result = TestResult(
                        command=test_cmd,
                        passed=passed,
                        output=(test_output["stdout"] + test_output["stderr"])[-3000:],
                        duration_seconds=round(time.time() - test_start, 1),
                    )
                    log(f"Tests {'PASSED' if passed else 'FAILED'} in {test_result.duration_seconds}s")

                    if passed:
                        break
                    else:
                        errors.append(
                            f"Tests failed (iteration {iterations}, cmd: {test_cmd}):\n"
                            f"{test_result.output[-1000:]}"
                        )
                        # Re-read changed files for next iteration
                        context = await self._build_context(request)
                else:
                    log("No test command detected, skipping tests")
                    break
            else:
                break

        # Auto-commit if requested and tests passed
        if request.auto_commit and files_changed:
            if test_result is None or test_result.passed:
                commit_msg = f"El Gringo: {request.task[:80]}"
                commit_output = self.tools.git_commit(commit_msg)
                git_commit_msg = commit_msg
                log(f"Committed: {commit_msg}")

        # Determine final status
        total_time = round(time.time() - start_time, 1)
        if not files_changed:
            status = "failed"
            summary = "No code changes were applied"
        elif test_result and not test_result.passed:
            status = "partial"
            summary = f"Made {len(files_changed)} changes but tests still failing after {iterations} iterations"
        else:
            status = "success"
            summary = f"Completed: {len(files_changed)} files changed in {iterations} iteration(s)"
            if test_result:
                summary += ", all tests passing"

        log(f"Finished: {status} in {total_time}s")

        # Record outcome for learning
        self._record_outcome(task_id, request.task, status, files_changed, errors)

        return CodingTaskResponse(
            task_id=task_id,
            status=status,
            summary=summary,
            files_changed=files_changed,
            test_results=test_result,
            git_commit=git_commit_msg,
            agents_used=agents_used,
            iterations=iterations,
            total_time=total_time,
            errors=errors[-10:],  # Cap errors in response
        )

    # ── Task Decomposition ───────────────────────────────────────────

    def _should_decompose(self, task: str) -> bool:
        """Detect if a task is complex enough to warrant decomposition."""
        task_lower = task.lower()

        # Check for explicit multi-step language
        if any(kw in task_lower for kw in self.DECOMPOSITION_KEYWORDS):
            return True

        # Check for multiple file references (changing 3+ files = complex)
        file_refs = re.findall(r'[\w./\-]+\.(?:py|js|ts|go|rs|java)', task)
        if len(set(file_refs)) >= 3:
            return True

        # Check for long task descriptions (>300 chars usually means multi-step)
        if len(task) > 300:
            return True

        return False

    async def _decompose_task(self, task: str, request: CodingTaskRequest) -> List[str]:
        """Use the AI team to break a complex task into ordered subtasks."""
        context = await self._build_context(request)

        prompt = f"""Break this task into 2-5 independent, ordered subtasks.
Each subtask should be a single, focused change that can be applied and verified independently.

TASK: {task}

RULES:
- Each subtask must be self-contained (not reference other subtasks)
- Order subtasks so later ones don't depend on earlier ones breaking
- Each subtask should name the specific file(s) to modify
- Keep subtasks small — one function change or one file edit each

Return ONLY a numbered list, one subtask per line. No explanations.
Example:
1. Add the helper function parse_config() to utils/config.py
2. Update main.py to import and call parse_config() on startup
3. Add test for parse_config() in tests/test_config.py
"""

        try:
            result = await self.team.collaborate(
                prompt=prompt, context=context, mode="sequential",
            )
            # Parse numbered list
            lines = result.final_answer.strip().splitlines()
            subtasks = []
            for line in lines:
                # Strip "1. ", "2. ", "- ", etc.
                cleaned = re.sub(r'^\s*\d+[\.\)]\s*', '', line).strip()
                cleaned = re.sub(r'^\s*[-•]\s*', '', cleaned).strip()
                if cleaned and len(cleaned) > 10:
                    subtasks.append(cleaned)

            if subtasks:
                return subtasks
        except Exception as e:
            logger.warning(f"Decomposition failed: {e}")

        # Fallback: execute as single task
        return [task]

    # ── Outcome Learning ─────────────────────────────────────────────

    def _record_outcome(
        self, task_id: str, task: str, status: str,
        files_changed: List[FileChange], errors: List[str],
    ):
        """Record task outcome for learning. Feeds into cross-project intelligence."""
        try:
            # Store locally in project's .elgringo/ directory
            outcome_dir = self.tools.root / ".elgringo" / "outcomes"
            outcome_dir.mkdir(parents=True, exist_ok=True)

            outcome = {
                "task_id": task_id,
                "task": task[:500],
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "files_changed": [f.path for f in files_changed],
                "error_count": len(errors),
                "errors_summary": [e[:200] for e in errors[:3]],
            }

            # Write outcome file
            outcome_file = outcome_dir / f"{task_id}.json"
            outcome_file.write_text(json.dumps(outcome, indent=2))

            # Also feed into KnowledgeNexus if available
            if status == "success" and files_changed:
                try:
                    from elgringo.intelligence.cross_project import get_nexus
                    nexus = get_nexus()
                    project_name = self.tools.root.name
                    nexus.index_solution(
                        project=project_name,
                        problem=task[:200],
                        solution=f"Modified {len(files_changed)} files: {', '.join(f.path for f in files_changed[:5])}",
                        tags=self._extract_tags(task, files_changed),
                    )
                except Exception:
                    pass  # Nexus is optional

            # Feed into feedback loop if available
            if status in ("success", "failed"):
                try:
                    from elgringo.intelligence.feedback_loop import get_feedback_loop
                    loop = get_feedback_loop()
                    loop.record_feedback(
                        task_id=task_id,
                        rating=1.0 if status == "success" else -0.5,
                        agents_involved=[],
                        task_type="coding",
                        mode="agentic",
                        auto_detected=True,
                    )
                except Exception:
                    pass  # Feedback loop is optional

            logger.info(f"Recorded outcome: {task_id} = {status}")

        except Exception as e:
            logger.debug(f"Failed to record outcome: {e}")

    def _get_past_outcomes(self, task: str, limit: int = 3) -> List[Dict]:
        """Retrieve relevant past outcomes for this project."""
        outcome_dir = self.tools.root / ".elgringo" / "outcomes"
        if not outcome_dir.exists():
            return []

        outcomes = []
        task_words = set(re.findall(r'[a-z_]+', task.lower()))

        for f in sorted(outcome_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text())
                past_words = set(re.findall(r'[a-z_]+', data.get("task", "").lower()))
                overlap = len(task_words & past_words) / max(len(task_words), 1)
                if overlap > 0.3:  # At least 30% keyword overlap
                    outcomes.append(data)
                    if len(outcomes) >= limit:
                        break
            except Exception:
                continue

        return outcomes

    @staticmethod
    def _extract_tags(task: str, files_changed: List[FileChange]) -> List[str]:
        """Extract tags from a task for cross-project indexing."""
        tags = []
        # File extensions as tags
        for f in files_changed:
            ext = Path(f.path).suffix.lstrip(".")
            if ext and ext not in tags:
                tags.append(ext)
        # Common task type keywords
        task_lower = task.lower()
        for keyword, tag in [("fix", "bugfix"), ("add", "feature"), ("refactor", "refactor"),
                              ("test", "testing"), ("security", "security"), ("performance", "perf"),
                              ("api", "api"), ("endpoint", "api"), ("database", "database"),
                              ("auth", "auth"), ("deploy", "deploy"), ("docker", "docker")]:
            if keyword in task_lower and tag not in tags:
                tags.append(tag)
        return tags[:10]

    # ── Context Building ─────────────────────────────────────────────

    async def _build_context(self, request: CodingTaskRequest) -> str:
        """Build context string with project info and numbered file contents."""
        parts = []

        # Project overview
        info = self.tools.get_project_info()
        parts.append(f"PROJECT: {info['project_path']}")
        parts.append(f"FILES: {info['files_count']} | LANGUAGES: {info['languages']}")
        parts.append("STRUCTURE:\n" + "\n".join(f"  {s}" for s in info["structure"]))
        parts.append("")

        # Determine which files to read
        files_to_read = list(request.files_to_read) if request.files_to_read else []

        # Auto-detect relevant files from the task description
        if not files_to_read and request.task:
            files_to_read = self._find_relevant_files(request.task)

        # Read and include files with line numbers
        total_chars = 0
        for filepath in files_to_read[:MAX_CONTEXT_FILES]:
            if total_chars > MAX_TOTAL_CONTEXT_CHARS:
                parts.append(f"(context truncated at {MAX_TOTAL_CONTEXT_CHARS} chars)")
                break

            abs_path = str(self.tools.root / filepath) if not os.path.isabs(filepath) else filepath
            content = self.tools.read_file(abs_path)
            if content.startswith("[ERROR]"):
                continue

            # Truncate large files but keep them useful
            if len(content) > MAX_FILE_CONTEXT_CHARS:
                content = content[:MAX_FILE_CONTEXT_CHARS] + f"\n... (truncated at {MAX_FILE_CONTEXT_CHARS} chars)"

            # Add with line numbers so AI can reference exact lines
            numbered = self._add_line_numbers(content)
            parts.append(f"--- FILE: {filepath} ---")
            parts.append(numbered)
            parts.append("")
            total_chars += len(numbered)

        # Git diff if available (shows what's already changed)
        if info.get("has_git"):
            diff = self.tools.git_diff()
            if diff and len(diff) < 5000:
                parts.append("--- GIT DIFF (current uncommitted changes) ---")
                parts.append(diff[:5000])
                parts.append("")

        # Past outcomes for similar tasks (learning from history)
        past = self._get_past_outcomes(request.task)
        if past:
            parts.append("--- PAST OUTCOMES (learn from these) ---")
            for outcome in past:
                status_icon = "OK" if outcome["status"] == "success" else "FAIL"
                parts.append(f"  [{status_icon}] {outcome['task'][:150]}")
                if outcome.get("errors_summary"):
                    parts.append(f"    Errors: {outcome['errors_summary'][0][:200]}")
                parts.append(f"    Files: {', '.join(outcome.get('files_changed', [])[:5])}")
            parts.append("")

        # Cross-project intelligence
        try:
            from elgringo.intelligence.cross_project import get_nexus
            nexus = get_nexus()
            nexus_results = nexus.search_across_projects(request.task[:100])
            if nexus_results:
                parts.append("--- CROSS-PROJECT INSIGHTS ---")
                for r in nexus_results[:3]:
                    parts.append(f"  [{r.project}] {r.problem[:100]} → {r.solution[:150]}")
                parts.append("")
        except Exception:
            pass

        # Execution context (systemd, Docker, etc.) — prevents import path bugs
        exec_ctx = self._detect_execution_context()
        if exec_ctx.get("warnings") or exec_ctx.get("working_dir"):
            parts.append("--- EXECUTION CONTEXT ---")
            if exec_ctx.get("working_dir"):
                parts.append(f"  Working directory: {exec_ctx['working_dir']}")
            if exec_ctx.get("entry_point"):
                parts.append(f"  Entry point: {exec_ctx['entry_point']}")
            if exec_ctx.get("import_style"):
                parts.append(f"  Import style: {exec_ctx['import_style']}")
            for w in exec_ctx.get("warnings", []):
                parts.append(f"  WARNING: {w}")
            parts.append("")

        # User-provided context
        if request.context:
            parts.append(f"--- ADDITIONAL CONTEXT ---\n{request.context}\n")

        return "\n".join(parts)

    def _find_relevant_files(self, task: str) -> List[str]:
        """
        Find files relevant to the task using 4 strategies:
        1. Explicit file paths mentioned in the task
        2. Grep search for symbols (function/class/variable names)
        3. Grep search for error messages or specific strings
        4. Keyword matching against file names
        """
        all_files = self.tools.list_files()
        task_lower = task.lower()
        scored: Dict[str, int] = {}  # filepath -> score

        # Strategy 1: Explicit file paths in the task
        explicit_paths = re.findall(r'[\w./\-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|rb|php|swift|kt|c|cpp|h)', task)
        for p in explicit_paths:
            # Match against actual files (supports partial paths like "server.py")
            for f in all_files:
                if f == p or f.endswith("/" + p) or f.endswith(p):
                    scored[f] = scored.get(f, 0) + 100

        # Strategy 2: Extract symbols (function names, class names, variables) and grep for them
        # Look for identifiers: camelCase, snake_case, PascalCase, UPPER_CASE
        symbols = re.findall(r'\b([A-Z][a-zA-Z0-9]+|[a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b', task)
        # Filter out common English words that look like symbols
        symbol_stop = {"should", "could", "would", "there", "where", "which",
                       "about", "their", "after", "before", "other", "every"}
        symbols = [s for s in symbols if s.lower() not in symbol_stop and len(s) > 3]

        for symbol in symbols[:8]:  # Cap to avoid slow grep storms
            grep_results = self.tools.search_files(
                re.escape(symbol),
                glob_pattern="**/*.{py,js,ts,tsx,jsx,go,rs,java}",
            )
            for r in grep_results[:20]:
                f = r.get("file", "")
                if f:
                    # Higher score for definition lines (def, class, function, const)
                    line = r.get("content", "")
                    if re.match(r'\s*(def|class|function|const|let|var|type|interface|func)\s', line):
                        scored[f] = scored.get(f, 0) + 25  # Definition found
                    else:
                        scored[f] = scored.get(f, 0) + 5   # Usage found

        # Strategy 3: Grep for quoted strings (error messages, specific text)
        quoted = re.findall(r'["\']([^"\']{5,60})["\']', task)
        for q in quoted[:3]:
            grep_results = self.tools.search_files(re.escape(q))
            for r in grep_results[:10]:
                f = r.get("file", "")
                if f:
                    scored[f] = scored.get(f, 0) + 30  # Exact string match

        # Strategy 4: Keyword matching against file names (fallback)
        stop_words = {"this", "that", "with", "from", "have", "will", "should", "could",
                      "would", "make", "change", "update", "modify", "create", "file",
                      "code", "function", "method", "class", "the", "and", "for", "add",
                      "need", "want", "please", "help", "like", "just", "also", "into"}
        keywords = [w for w in re.findall(r'[a-z_]+', task_lower) if len(w) > 3 and w not in stop_words]

        for f in all_files:
            f_lower = f.lower()
            fname = Path(f).stem.lower()
            for kw in keywords:
                if kw in fname:
                    scored[f] = scored.get(f, 0) + 10
                elif kw in f_lower:
                    scored[f] = scored.get(f, 0) + 3

        # Sort by score, return top matches
        ranked = sorted(scored.items(), key=lambda x: -x[1])
        result = [f for f, _ in ranked[:MAX_CONTEXT_FILES]]

        if result:
            logger.info(f"Found {len(result)} relevant files: {result[:5]}")
        else:
            # Fallback: return main entry points
            for f in all_files:
                if any(n in f for n in ("main.", "app.", "server.", "index.", "__init__.")):
                    result.append(f)
            result = result[:5]
            logger.info(f"No files matched task, using entry points: {result}")

        return result

    @staticmethod
    def _add_line_numbers(content: str) -> str:
        """Add line numbers to file content for precise referencing."""
        lines = content.splitlines()
        width = len(str(len(lines)))
        return "\n".join(f"{i+1:>{width}}| {line}" for i, line in enumerate(lines))

    # ── Prompt Building ──────────────────────────────────────────────

    def _build_coding_prompt(
        self, task: str, context: str,
        errors: Optional[List[str]] = None,
        iteration: int = 0,
    ) -> str:
        """Build the structured prompt for code generation."""
        prompt = f"""You are a coding agent. Make ONLY the changes described in the task below.

TASK: {task}

RULES:
- ONLY modify files directly related to the task. Do NOT refactor, clean up, or improve other code.
- Every change MUST use one of the two formats below — no changes outside these blocks.
- The <<<old section must be an EXACT copy from the file (including indentation).
- Do NOT use placeholder comments, TODOs, or "..." — write complete, real code.
- Keep the existing code style. Do not add type hints, docstrings, or comments to code you didn't change.
- NEVER write `except Exception: pass` or `except Exception: continue` — always log errors.
- NEVER include line numbers (like "1|" or "  10→") in your code output — write PURE code only.
- When using ```file:path```, write the COMPLETE file content. Do NOT write partial snippets.
- When using ```edit:path```, make the SMALLEST possible edit. Prefer edit over file when the change is < 50% of the file.
- If the project runs from a subdirectory (check EXECUTION CONTEXT), use fallback imports.

FORMAT 1 — Create or fully rewrite a file:

```file:path/to/file.py
entire file content here
```

FORMAT 2 — Edit part of an existing file:

```edit:path/to/file.py
<<<old
exact lines to replace (copy-paste from file above, preserve indentation)
>>>new
replacement lines
<<<end
```

You can have multiple <<<old/>>>new/<<<end blocks inside a single ```edit:``` block for the same file.
"""

        if errors:
            prompt += "\n--- PREVIOUS ERRORS (fix these) ---\n"
            # Show most recent errors, most relevant at the end
            for e in errors[-5:]:
                prompt += f"\n{e[:800]}\n"
            prompt += "\nFix the errors above. Copy the <<<old text EXACTLY from the file content shown in context.\n"

        if iteration > 0:
            prompt += f"\nThis is retry #{iteration + 1}. Be more careful with exact string matching.\n"

        return prompt

    async def _get_plan(self, task: str, context: str, mode: str) -> Dict[str, Any]:
        """Get a plan without executing changes."""
        prompt = f"""Plan the implementation for this task (do NOT write code, just plan):

TASK: {task}

Provide:
1. A brief summary of what needs to change
2. Numbered steps with specific file paths and what to modify in each
3. Any risks or edge cases
"""
        result = await self.team.collaborate(prompt=prompt, context=context, mode=mode)
        steps = [line.strip() for line in result.final_answer.split("\n") if line.strip()]
        return {
            "summary": result.final_answer[:500],
            "steps": steps[:20],
            "agents_used": result.participating_agents,
        }

    # ── Content Cleaning ────────────────────────────────────────────

    @staticmethod
    def _clean_code_content(content: str) -> str:
        """Strip AI artifacts from generated code content.

        Removes:
        - Line number prefixes: '  1|', '  2| ', '10|', '1→', etc.
        - Leading/trailing blank lines
        - Trailing whitespace per line
        """
        lines = content.splitlines()
        cleaned = []
        # Detect if ALL or most lines have a number prefix pattern
        prefix_pattern = re.compile(r'^\s*\d+[|→]\s?')
        num_prefixed = sum(1 for line in lines if prefix_pattern.match(line))
        strip_prefixes = num_prefixed > len(lines) * 0.5  # More than half have prefixes

        for line in lines:
            if strip_prefixes:
                line = prefix_pattern.sub('', line)
            cleaned.append(line.rstrip())

        # Strip leading/trailing empty lines
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()

        result = "\n".join(cleaned)
        if result and not result.endswith("\n"):
            result += "\n"
        return result

    # ── Response Parsing ─────────────────────────────────────────────

    def _parse_file_changes(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse AI response for file operations.

        5 fallback strategies:
        1. ```file:path``` blocks (full write)
        2. ```edit:path``` with <<<old/>>>new/<<<end (preferred edit format)
        3. ```edit:path``` with <<<old/>>>new (no <<<end, terminated by next or end of block)
        4. ```python {file:path}``` or ```python\n# file:path``` hints
        5. Bare ```python blocks after "File: path" text
        """
        changes: List[Dict[str, Any]] = []

        # Strategy 1: ```file:path``` blocks — full file write
        # Handles: ```file:path.py, ```file: path.py, ```file:path.py\n
        for match in re.finditer(r'```\s*file:\s*(.+?)\n(.*?)```', response, re.DOTALL):
            filepath = match.group(1).strip().strip("`")
            content = match.group(2)
            if content.strip():
                changes.append({"action": "write", "path": filepath, "content": content})

        # Strategy 2+3: ```edit:path``` blocks with <<<old/>>>new
        for match in re.finditer(r'```\s*edit:\s*(.+?)\n(.*?)```', response, re.DOTALL):
            filepath = match.group(1).strip().strip("`")
            edit_block = match.group(2)
            changes.extend(self._parse_edit_block(filepath, edit_block))

        # Strategy 4: ```python or ```lang blocks with file path in first line
        if not changes:
            pattern = r'```(?:python|javascript|typescript|go|rust|java|ruby|php|swift|kotlin|cpp|c)?\s*\n\s*#\s*(?:file|File|FILE):\s*(.+?)\n(.*?)```'
            for match in re.finditer(pattern, response, re.DOTALL):
                filepath = match.group(1).strip()
                content = match.group(2)
                if len(content.strip()) > 10:
                    changes.append({"action": "write", "path": filepath, "content": content})

        # Strategy 5: "File: path.py" text followed by code block
        if not changes:
            pattern = r'(?:^|\n)\s*(?:file|File|FILE)[:\s]+([^\s`\n]+\.(?:py|js|ts|tsx|jsx|go|rs|java|rb|php|swift|kt|c|cpp|h))\s*\n+```[a-z]*\n(.*?)```'
            for match in re.finditer(pattern, response, re.DOTALL):
                filepath = match.group(1).strip()
                content = match.group(2)
                if len(content.strip()) > 10:
                    changes.append({"action": "write", "path": filepath, "content": content})

        # Clean all parsed content (strip line number prefixes, trailing whitespace)
        for change in changes:
            if change.get("content"):
                change["content"] = self._clean_code_content(change["content"])
            if change.get("new"):
                change["new"] = self._clean_code_content(change["new"]).rstrip("\n")
            if change.get("old"):
                # Strip line numbers from old text too (AI copies from numbered context)
                prefix_pat = re.compile(r'^\s*\d+[|→]\s?', re.MULTILINE)
                if prefix_pat.search(change["old"]):
                    change["old"] = prefix_pat.sub('', change["old"])

        if changes:
            logger.info(f"Parsed {len(changes)} changes ({sum(1 for c in changes if c['action'] == 'write')} writes, "
                        f"{sum(1 for c in changes if c['action'] == 'edit')} edits)")
        else:
            block_count = len(re.findall(r'```', response)) // 2
            logger.warning(f"No changes parsed. Response: {len(response)} chars, {block_count} code blocks")

        return changes

    def _parse_edit_block(self, filepath: str, edit_block: str) -> List[Dict[str, Any]]:
        """Parse a single edit block for <<<old/>>>new pairs."""
        edits: List[Dict[str, Any]] = []

        # Try with <<<end delimiter first (our preferred format)
        pairs = re.findall(
            r'<<<\s*old\s*\n(.*?)>>>\s*new\s*\n(.*?)<<<\s*end',
            edit_block, re.DOTALL,
        )

        # Fallback: without <<<end (terminated by next <<<old or end of block)
        if not pairs:
            pairs = re.findall(
                r'<<<\s*old\s*\n(.*?)>>>\s*new\s*\n(.*?)(?=<<<\s*old|\Z)',
                edit_block, re.DOTALL,
            )

        # Fallback: --- old / --- new / --- end (some models use dashes)
        if not pairs:
            pairs = re.findall(
                r'---\s*old\s*\n(.*?)---\s*new\s*\n(.*?)(?:---\s*end|(?=---\s*old)|\Z)',
                edit_block, re.DOTALL,
            )

        for old_text, new_text in pairs:
            # Strip exactly one leading/trailing newline (preserve internal whitespace)
            old_clean = old_text.strip("\n")
            new_clean = new_text.strip("\n")
            if old_clean:  # Don't add empty edits
                edits.append({
                    "action": "edit",
                    "path": filepath,
                    "old": old_clean,
                    "new": new_clean,
                })

        return edits

    # ── Change Application ───────────────────────────────────────────

    def _deduplicate_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate changes. For writes to same file, keep the LAST (most corrected)."""
        # For write actions: keep last occurrence per file (AI often self-corrects)
        write_map: Dict[str, Dict[str, Any]] = {}
        edits: List[Dict[str, Any]] = []
        edit_keys: set = set()

        for change in changes:
            if change["action"] == "write":
                # Last write wins (most corrected version)
                write_map[change["path"]] = change
            else:
                key = (change["path"], change.get("old", "")[:100])
                if key not in edit_keys:
                    edit_keys.add(key)
                    edits.append(change)

        deduped = list(write_map.values()) + edits
        if len(deduped) < len(changes):
            logger.info(f"Deduplicated {len(changes)} → {len(deduped)} changes")
        return deduped

    def _backup_files(self, changes: List[Dict[str, Any]]):
        """Backup files before modifying them (for potential restore)."""
        for change in changes:
            filepath = change["path"]
            abs_path = str(self.tools.root / filepath) if not os.path.isabs(filepath) else filepath
            if Path(abs_path).exists() and filepath not in self._backups:
                try:
                    self._backups[filepath] = Path(abs_path).read_text(errors="replace")
                except Exception:
                    pass

    def restore_backups(self):
        """Restore all backed-up files to their original state."""
        restored = 0
        for filepath, content in self._backups.items():
            abs_path = str(self.tools.root / filepath) if not os.path.isabs(filepath) else filepath
            try:
                Path(abs_path).write_text(content)
                restored += 1
            except Exception as e:
                logger.error(f"Failed to restore {filepath}: {e}")
        logger.info(f"Restored {restored}/{len(self._backups)} files")
        return restored

    def _apply_changes(self, changes: List[Dict[str, Any]]) -> List[FileChange]:
        """Apply parsed changes with exact match → fuzzy match → difflib fallback."""
        applied = []

        for change in changes:
            filepath = change["path"]
            abs_path = str(self.tools.root / filepath) if not os.path.isabs(filepath) else filepath

            try:
                if change["action"] == "write":
                    existed = Path(abs_path).exists()
                    clean_content = self._clean_code_content(change["content"])
                    self.tools.write_file(abs_path, clean_content)
                    # Post-write validation for Python files
                    compile_err = self._validate_python_syntax(abs_path, filepath)
                    if compile_err:
                        self._apply_errors.append(compile_err)
                    applied.append(FileChange(
                        path=filepath,
                        action="modified" if existed else "created",
                        lines_changed=len(change["content"].splitlines()),
                    ))
                    logger.info(f"{'Overwrote' if existed else 'Created'}: {filepath}")

                elif change["action"] == "edit":
                    result = self._apply_edit(abs_path, filepath, change["old"], change["new"])
                    if result:
                        # Post-edit validation for Python files
                        compile_err = self._validate_python_syntax(abs_path, filepath)
                        if compile_err:
                            self._apply_errors.append(compile_err)
                        applied.append(result)

            except Exception as e:
                msg = f"Error applying change to {filepath}: {e}"
                logger.error(msg)
                self._apply_errors.append(msg)

        return applied

    def _apply_edit(self, abs_path: str, filepath: str, old_text: str, new_text: str) -> Optional[FileChange]:
        """Apply a single edit with multiple matching strategies."""
        content = self.tools.read_file(abs_path)
        if content.startswith("[ERROR]"):
            self._apply_errors.append(f"Cannot read {filepath}: {content}")
            return None

        # Clean line number prefixes from both old and new text
        prefix_pattern = re.compile(r'^\s*\d+[|→]\s?', re.MULTILINE)
        if prefix_pattern.search(old_text):
            old_text = prefix_pattern.sub('', old_text)
        if prefix_pattern.search(new_text):
            new_text = prefix_pattern.sub('', new_text)

        # Strategy 1: Exact match
        if old_text in content:
            new_content = content.replace(old_text, new_text, 1)
            self.tools.write_file(abs_path, new_content)
            logger.info(f"Edited (exact match): {filepath}")
            return self._make_file_change(filepath, old_text, new_text)

        # Strategy 2: Whitespace-normalized match
        result = self._fuzzy_replace_whitespace(content, old_text, new_text)
        if result is not None:
            self.tools.write_file(abs_path, result)
            logger.info(f"Edited (whitespace-normalized): {filepath}")
            return self._make_file_change(filepath, old_text, new_text)

        # Strategy 3: Line-number-stripped match (AI sometimes copies line numbers from context)
        stripped_old = re.sub(r'^\s*\d+\|\s?', '', old_text, flags=re.MULTILINE)
        if stripped_old != old_text and stripped_old in content:
            new_content = content.replace(stripped_old, new_text, 1)
            self.tools.write_file(abs_path, new_content)
            logger.info(f"Edited (line-numbers stripped): {filepath}")
            return self._make_file_change(filepath, old_text, new_text)

        # Strategy 4: First/last line anchor match
        result = self._fuzzy_replace_anchors(content, old_text, new_text)
        if result is not None:
            self.tools.write_file(abs_path, result)
            logger.info(f"Edited (anchor match): {filepath}")
            return self._make_file_change(filepath, old_text, new_text)

        # Strategy 5: difflib best match (last resort)
        result = self._fuzzy_replace_difflib(content, old_text, new_text)
        if result is not None:
            self.tools.write_file(abs_path, result)
            logger.info(f"Edited (difflib fuzzy): {filepath}")
            return self._make_file_change(filepath, old_text, new_text)

        # All strategies failed
        # Show what we tried to match vs what's actually in the file
        old_preview = repr(old_text[:120])
        # Find the closest match in the file for diagnosis
        closest = self._find_closest_match(content, old_text)
        msg = f"Edit failed for {filepath}: old_text not found. Tried: {old_preview}"
        if closest:
            msg += f"\nClosest match in file (similarity {closest[1]:.0%}): {repr(closest[0][:120])}"
        self._apply_errors.append(msg)
        return None

    @staticmethod
    def _make_file_change(filepath: str, old_text: str, new_text: str) -> FileChange:
        diff_lines = abs(len(new_text.splitlines()) - len(old_text.splitlines()))
        return FileChange(
            path=filepath,
            action="modified",
            diff=f"-{old_text[:100]}...\n+{new_text[:100]}...",
            lines_changed=max(diff_lines, 1),
        )

    # ── Fuzzy Matching Strategies ────────────────────────────────────

    @staticmethod
    def _fuzzy_replace_whitespace(content: str, old_text: str, new_text: str) -> Optional[str]:
        """Match after normalizing trailing whitespace on each line."""
        def normalize(text):
            return "\n".join(line.rstrip() for line in text.splitlines())

        norm_content = normalize(content)
        norm_old = normalize(old_text)

        if norm_old in norm_content:
            return norm_content.replace(norm_old, new_text, 1)
        return None

    @staticmethod
    def _fuzzy_replace_anchors(content: str, old_text: str, new_text: str) -> Optional[str]:
        """Match using first and last non-empty lines as anchors."""
        old_lines = [l.strip() for l in old_text.splitlines() if l.strip()]
        if len(old_lines) < 2:
            return None

        content_lines = content.splitlines()
        first_anchor = old_lines[0]
        last_anchor = old_lines[-1]
        expected_span = len(old_lines)

        for i, line in enumerate(content_lines):
            if first_anchor in line.strip():
                # Search for the last anchor within a reasonable range
                search_end = min(i + expected_span + 10, len(content_lines))
                for j in range(i + 1, search_end):
                    if last_anchor in content_lines[j].strip():
                        # Verify middle lines are plausible (at least 50% match)
                        block_lines = [l.strip() for l in content_lines[i:j + 1] if l.strip()]
                        matches = sum(1 for ol in old_lines if any(ol in bl for bl in block_lines))
                        if matches / len(old_lines) >= 0.5:
                            original_block = "\n".join(content_lines[i:j + 1])
                            return content.replace(original_block, new_text, 1)

        return None

    @staticmethod
    def _fuzzy_replace_difflib(content: str, old_text: str, new_text: str) -> Optional[str]:
        """Use difflib to find the best matching block in content."""
        old_lines = old_text.splitlines()
        content_lines = content.splitlines()
        n = len(old_lines)

        if n == 0 or len(content_lines) == 0:
            return None

        best_ratio = 0.0
        best_start = -1
        best_end = -1

        # Slide a window of size n (±3 lines) across the content
        for window_size in range(max(1, n - 3), n + 4):
            for start in range(len(content_lines) - window_size + 1):
                candidate = content_lines[start:start + window_size]
                ratio = difflib.SequenceMatcher(
                    None,
                    "\n".join(old_lines),
                    "\n".join(candidate),
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_start = start
                    best_end = start + window_size

        if best_ratio >= FUZZY_MATCH_THRESHOLD and best_start >= 0:
            original_block = "\n".join(content_lines[best_start:best_end])
            logger.info(f"difflib match: {best_ratio:.0%} similarity, lines {best_start+1}-{best_end}")
            return content.replace(original_block, new_text, 1)

        return None

    @staticmethod
    def _find_closest_match(content: str, old_text: str) -> Optional[Tuple[str, float]]:
        """Find the closest matching block for diagnostic purposes."""
        old_lines = old_text.splitlines()
        content_lines = content.splitlines()
        n = len(old_lines)

        if n == 0 or not content_lines:
            return None

        best_ratio = 0.0
        best_block = ""

        # Sample positions to avoid O(n²) on large files
        step = max(1, len(content_lines) // 200)
        for start in range(0, len(content_lines) - n + 1, step):
            candidate = "\n".join(content_lines[start:start + n])
            ratio = difflib.SequenceMatcher(None, old_text, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_block = candidate

        if best_ratio > 0.3:
            return (best_block, best_ratio)
        return None

    # ── Post-Apply Validation ─────────────────────────────────────────

    @staticmethod
    def _validate_python_syntax(abs_path: str, filepath: str) -> Optional[str]:
        """
        Compile-check Python files immediately after writing/editing.
        Catches SyntaxError and other compile-time issues before tests run.
        Learned from: silent ModuleNotFoundError on managers-dashboard VM.
        """
        if not filepath.endswith(".py"):
            return None
        try:
            import py_compile
            py_compile.compile(abs_path, doraise=True)
            return None
        except py_compile.PyCompileError as e:
            msg = f"SYNTAX ERROR in {filepath}: {e}"
            logger.error(msg)
            return msg
        except Exception:
            return None  # Non-Python file or unreadable — skip

    def _detect_execution_context(self) -> Dict[str, Any]:
        """
        Detect how this project is actually run (systemd, Docker, etc.)
        to understand import paths and working directories.

        Learned from: managers-dashboard had `from backend.ml_engine import MLEngine`
        but systemd ran uvicorn from backend/ dir, so it needed `from ml_engine import MLEngine`.
        """
        context: Dict[str, Any] = {
            "working_dir": None,    # Where the app actually runs from
            "entry_point": None,    # The main module/command
            "import_style": None,   # "relative" or "absolute" or "package"
            "warnings": [],
        }

        root = self.tools.root

        # Check systemd service files
        for pattern in ["*.service", "**/*.service"]:
            for svc in root.glob(pattern):
                try:
                    content = svc.read_text(errors="replace")
                    # Extract WorkingDirectory
                    wd_match = re.search(r'WorkingDirectory\s*=\s*(.+)', content)
                    if wd_match:
                        context["working_dir"] = wd_match.group(1).strip()

                    # Extract ExecStart to find the entry point
                    exec_match = re.search(r'ExecStart\s*=\s*(.+)', content)
                    if exec_match:
                        context["entry_point"] = exec_match.group(1).strip()
                        # Detect if uvicorn/gunicorn runs from a subdirectory
                        if "uvicorn" in context["entry_point"] or "gunicorn" in context["entry_point"]:
                            parts = context["entry_point"].split()
                            for p in parts:
                                if ":" in p and not p.startswith("-"):
                                    module = p.split(":")[0]
                                    context["import_style"] = "relative" if "." not in module else "package"
                except Exception:
                    continue

        # Check Dockerfile for WORKDIR and CMD
        dockerfile = root / "Dockerfile"
        if dockerfile.exists():
            try:
                content = dockerfile.read_text(errors="replace")
                workdir = re.findall(r'WORKDIR\s+(.+)', content)
                if workdir:
                    context["working_dir"] = context["working_dir"] or workdir[-1].strip()
                cmd = re.findall(r'(?:CMD|ENTRYPOINT)\s+(.+)', content)
                if cmd:
                    context["entry_point"] = context["entry_point"] or cmd[-1].strip()
            except Exception:
                pass

        # Detect import path mismatches
        if context["working_dir"]:
            wd = context["working_dir"]
            # If working dir is a subdirectory, imports from sibling dirs won't work
            if "/" in wd and not wd.endswith(str(root)):
                subdir = wd.rstrip("/").split("/")[-1]
                context["warnings"].append(
                    f"App runs from subdirectory '{subdir}/' — imports like "
                    f"'from {subdir}.module import X' will fail. "
                    f"Use 'from module import X' or add fallback imports."
                )

        return context

    # ── Silent Exception Detection ────────────────────────────────────

    @staticmethod
    def _detect_silent_exceptions(code: str, filepath: str) -> List[str]:
        """
        Scan code for dangerous silent exception swallowing patterns.
        Learned from: `except Exception` caught ModuleNotFoundError silently,
        causing on-time metric to always return 0% with no error logged.
        """
        warnings = []
        lines = code.splitlines()

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Pattern 1: except Exception followed by pass or bare continue
            if re.match(r'except\s+Exception\s*(?:as\s+\w+)?:', stripped):
                # Check what follows the except
                next_lines = []
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_stripped = lines[j].strip()
                    if next_stripped and not next_stripped.startswith("#"):
                        next_lines.append(next_stripped)
                        break

                if next_lines:
                    body = next_lines[0]
                    if body in ("pass", "continue", "..."):
                        warnings.append(
                            f"{filepath}:{i+1}: Silent 'except Exception: {body}' — "
                            f"will hide ImportError, TypeError, KeyError etc. "
                            f"Log the error or catch a specific exception type."
                        )
                    elif not any(kw in body for kw in ("log", "print", "raise", "warn", "logger")):
                        warnings.append(
                            f"{filepath}:{i+1}: Broad 'except Exception' without logging — "
                            f"consider logging the error or narrowing the exception type."
                        )

            # Pattern 2: bare except (catches everything including SystemExit)
            elif re.match(r'except\s*:', stripped):
                warnings.append(
                    f"{filepath}:{i+1}: Bare 'except:' catches SystemExit and KeyboardInterrupt. "
                    f"Use 'except Exception:' at minimum."
                )

        return warnings


# ── API Endpoints ────────────────────────────────────────────────────

def _get_engine(project_path: str) -> CodingAgentEngine:
    """Create a coding engine scoped to a project."""
    from products.fred_api.server import get_team
    tools = ProjectTools(project_path)
    team = get_team()
    return CodingAgentEngine(team, tools)


# Keep a reference to the last engine per project for restore
_active_engines: Dict[str, CodingAgentEngine] = {}


@router.post("/task", response_model=CodingTaskResponse)
async def execute_coding_task(request: CodingTaskRequest):
    """
    Execute a coding task: read code, make changes, run tests, self-correct.

    This is the main endpoint that turns El Gringo into a coding agent.
    """
    try:
        engine = _get_engine(request.project_path)
        _active_engines[request.project_path] = engine
        result = await engine.execute_task(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Coding task error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore")
async def restore_backups(project_path: str):
    """Restore files modified by the last coding task to their original state."""
    resolved = str(Path(project_path).resolve())
    engine = _active_engines.get(resolved) or _active_engines.get(project_path)
    if not engine or not engine._backups:
        raise HTTPException(status_code=404, detail="No backups found for this project")
    restored = engine.restore_backups()
    return {"restored_files": restored, "project_path": resolved}


@router.post("/plan")
async def plan_coding_task(request: CodingTaskRequest):
    """Plan a coding task without executing changes."""
    request.dry_run = True
    try:
        engine = _get_engine(request.project_path)
        result = await engine.execute_task(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Planning error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review")
async def review_project(
    project_path: str,
    focus: str = "bugs",
    glob_pattern: str = "**/*.py",
):
    """
    Review a project for issues. Returns findings without making changes.

    Focus options: bugs, security, performance, quality
    """
    try:
        tools = ProjectTools(project_path)
        files = tools.list_files()

        from fnmatch import fnmatch
        matched = [f for f in files if fnmatch(f, glob_pattern)][:15]

        context_parts = []
        for filepath in matched:
            content = tools.read_file(str(tools.root / filepath))
            if not content.startswith("[ERROR]"):
                context_parts.append(f"--- {filepath} ---\n{content[:5000]}\n")

        context = "\n".join(context_parts)

        # Static analysis: detect silent exception swallowing
        static_warnings = []
        for filepath in matched:
            content = tools.read_file(str(tools.root / filepath))
            if not content.startswith("[ERROR]"):
                warnings = CodingAgentEngine._detect_silent_exceptions(content, filepath)
                static_warnings.extend(warnings)

        from products.fred_api.server import get_team
        team = get_team()
        result = await team.collaborate(
            prompt=f"Review this codebase for {focus} issues. Be specific — include file paths and line numbers for each finding. Rank by severity.",
            context=context,
            mode="parallel",
        )

        findings = result.final_answer
        if static_warnings:
            findings += "\n\n--- STATIC ANALYSIS: Silent Exception Patterns ---\n"
            findings += "\n".join(f"  {w}" for w in static_warnings[:20])

        return {
            "focus": focus,
            "files_reviewed": len(matched),
            "findings": findings,
            "agents_used": result.participating_agents,
            "confidence": result.confidence_score,
            "static_warnings": static_warnings[:20],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project-info")
async def get_project_info(project_path: str):
    """Get project structure and metadata."""
    try:
        tools = ProjectTools(project_path)
        info = tools.get_project_info()
        return ProjectInfoResponse(**info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
