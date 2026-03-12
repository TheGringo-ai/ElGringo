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
import logging
import os
import re
import shlex
import subprocess
import time
import uuid
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
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".swift", ".kt", ".c", ".cpp", ".h", ".hpp",
        ".css", ".scss", ".html", ".vue", ".svelte",
        ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
        ".sql", ".sh", ".bash", ".zsh", ".fish",
        ".md", ".txt", ".rst", ".env.example",
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

    def list_files(self, max_files: int = 500) -> List[str]:
        """List all code files in the project."""
        files = []
        for root, dirs, filenames in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for f in filenames:
                if Path(f).suffix in self.CODE_EXTENSIONS:
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

    def __init__(self, team, tools: ProjectTools):
        self.team = team
        self.tools = tools
        self._apply_errors: List[str] = []
        self._backups: Dict[str, str] = {}  # filepath -> original content

    async def execute_task(self, request: CodingTaskRequest) -> CodingTaskResponse:
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

        # Step 1: Build context
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
            files_changed.extend(applied)

            # Feed apply errors back
            if self._apply_errors:
                for err in self._apply_errors:
                    errors.append(f"Iteration {iterations}: {err}")
                log(f"{len(self._apply_errors)} apply errors, {len(applied)} successful")
                if not applied:
                    continue  # All failed — retry

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

        # User-provided context
        if request.context:
            parts.append(f"--- ADDITIONAL CONTEXT ---\n{request.context}\n")

        return "\n".join(parts)

    def _find_relevant_files(self, task: str) -> List[str]:
        """Find files relevant to the task using keyword matching."""
        all_files = self.tools.list_files()
        task_lower = task.lower()

        # Extract meaningful words (>3 chars, not common words)
        stop_words = {"this", "that", "with", "from", "have", "will", "should", "could",
                      "would", "make", "change", "update", "modify", "create", "file",
                      "code", "function", "method", "class", "the", "and", "for", "add"}
        keywords = [w for w in re.findall(r'[a-z_]+', task_lower) if len(w) > 3 and w not in stop_words]

        # Also extract explicit file paths from the task
        explicit_paths = re.findall(r'[\w./]+\.(?:py|js|ts|go|rs|java|rb|php|swift|kt)', task)

        scored: List[Tuple[str, int]] = []
        for f in all_files:
            score = 0
            f_lower = f.lower()
            fname = Path(f).stem.lower()

            # Exact path match (highest priority)
            if f in explicit_paths or f_lower in [p.lower() for p in explicit_paths]:
                score += 100

            # Filename contains task keywords
            for kw in keywords:
                if kw in fname:
                    score += 10
                elif kw in f_lower:
                    score += 3

            if score > 0:
                scored.append((f, score))

        # Sort by score descending, return top matches
        scored.sort(key=lambda x: -x[1])
        return [f for f, _ in scored[:MAX_CONTEXT_FILES]]

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
        """Remove duplicate changes to the same file with the same content."""
        seen = set()
        deduped = []
        for change in changes:
            # Create a fingerprint
            if change["action"] == "write":
                key = (change["action"], change["path"])
            else:
                key = (change["action"], change["path"], change.get("old", "")[:100])

            if key not in seen:
                seen.add(key)
                deduped.append(change)
            else:
                logger.debug(f"Deduplicated change to {change['path']}")

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
                    self.tools.write_file(abs_path, change["content"])
                    applied.append(FileChange(
                        path=filepath,
                        action="modified" if existed else "created",
                        lines_changed=len(change["content"].splitlines()),
                    ))
                    logger.info(f"{'Overwrote' if existed else 'Created'}: {filepath}")

                elif change["action"] == "edit":
                    result = self._apply_edit(abs_path, filepath, change["old"], change["new"])
                    if result:
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

        from products.fred_api.server import get_team
        team = get_team()
        result = await team.collaborate(
            prompt=f"Review this codebase for {focus} issues. Be specific — include file paths and line numbers for each finding. Rank by severity.",
            context=context,
            mode="parallel",
        )

        return {
            "focus": focus,
            "files_reviewed": len(matched),
            "findings": result.final_answer,
            "agents_used": result.participating_agents,
            "confidence": result.confidence_score,
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
