"""
Fred API - Coding Agent Endpoints
==================================

Gives the AI team hands-on access to a project: read files, edit code,
run tests, execute shell commands, and commit via git.

Flow:
  1. POST /v1/code/task  — describe what needs fixing + project path
  2. Agents read the codebase, plan changes, execute edits, run tests
  3. Returns structured result with files changed, test output, and diff

This turns El Gringo from an advisory chatbot into a real coding agent.
"""

import asyncio
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/code", tags=["coding-agent"])


# ── Models ───────────────────────────────────────────────────────────

class CodingTaskRequest(BaseModel):
    """A coding task for the AI team to execute."""
    task: str = Field(..., description="What needs to be done (bug fix, feature, refactor, etc.)")
    project_path: str = Field(..., description="Absolute path to the project root")
    context: str = Field("", description="Additional context: error messages, screenshots, constraints")
    files_to_read: List[str] = Field(default_factory=list, description="Specific files to read first")
    run_tests: bool = Field(True, description="Run tests after making changes")
    test_command: str = Field("", description="Custom test command (default: auto-detect)")
    auto_commit: bool = Field(False, description="Commit changes if tests pass")
    mode: str = Field("sequential", description="Agent collaboration mode: sequential, parallel")
    allowed_agents: Optional[List[str]] = Field(None, description="Specific agents to use")
    max_iterations: int = Field(3, description="Max self-correction iterations")
    dry_run: bool = Field(False, description="Plan only, don't execute changes")


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

    # Extensions we can read/edit
    CODE_EXTENSIONS = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".swift", ".kt", ".c", ".cpp", ".h", ".hpp",
        ".css", ".scss", ".html", ".vue", ".svelte",
        ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
        ".sql", ".sh", ".bash", ".zsh", ".fish",
        ".md", ".txt", ".rst", ".env.example",
    }

    # Directories to skip
    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        ".next", "dist", "build", ".tox", ".mypy_cache",
        ".pytest_cache", "egg-info", ".eggs",
    }

    def __init__(self, project_path: str):
        self.root = Path(project_path).resolve()
        if not self.root.is_dir():
            raise ValueError(f"Project path does not exist: {self.root}")

    def _validate_path(self, filepath: str) -> Path:
        """Ensure path is within project root."""
        p = Path(filepath).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError(f"Path {p} is outside project root {self.root}")
        return p

    def read_file(self, filepath: str) -> str:
        p = self._validate_path(filepath)
        if not p.exists():
            return f"[ERROR] File not found: {filepath}"
        if p.stat().st_size > 1_000_000:
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
        import re
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
        import subprocess

        # Security: block dangerous commands
        dangerous = ["rm -rf /", "rm -rf ~", "mkfs", "dd if=/dev", "> /dev/sda"]
        cmd_lower = command.lower()
        for d in dangerous:
            if d in cmd_lower:
                return {"exit_code": 1, "stdout": "", "stderr": f"Blocked dangerous command: {command}"}

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
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
        """Get current git diff."""
        result = self.run_command("git diff")
        return result.get("stdout", "")

    def git_status(self) -> str:
        result = self.run_command("git status --short")
        return result.get("stdout", "")

    def git_commit(self, message: str) -> str:
        self.run_command("git add -A")
        result = self.run_command(f'git commit -m "{message}"')
        return result.get("stdout", "") + result.get("stderr", "")

    def get_project_info(self) -> Dict[str, Any]:
        """Get project structure and metadata."""
        files = self.list_files()
        languages = {}
        for f in files:
            ext = Path(f).suffix
            languages[ext] = languages.get(ext, 0) + 1

        has_tests = any("test" in f.lower() for f in files)
        has_git = (self.root / ".git").is_dir()

        # Top-level structure
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
        # Check root and common subdirs for pytest config
        for subdir in ["", "backend", "src", "app"]:
            check_dir = self.root / subdir if subdir else self.root
            if (check_dir / "pytest.ini").exists() or (check_dir / "conftest.py").exists():
                if subdir:
                    return f"cd {subdir} && python -m pytest -x -q 2>&1 | tail -20"
                return "python -m pytest -x -q 2>&1 | tail -20"
        if (self.root / "pyproject.toml").exists():
            return "python -m pytest -x -q 2>&1 | tail -20"
        if (self.root / "package.json").exists():
            return "npm test 2>&1 | tail -30"
        if (self.root / "Cargo.toml").exists():
            return "cargo test 2>&1 | tail -20"
        if (self.root / "go.mod").exists():
            return "go test ./... 2>&1 | tail -20"
        # Fallback: look for test files
        if any("test_" in f or "_test.py" in f for f in self.list_files()):
            return "python -m pytest -x -q 2>&1 | tail -20"
        return ""


# ── Coding Agent Engine ──────────────────────────────────────────────

class CodingAgentEngine:
    """
    The core engine that turns AI team responses into actual code changes.

    Flow:
    1. Read relevant files → build context
    2. Send task + context to AI team
    3. Parse response for file operations (create/edit/delete)
    4. Apply changes
    5. Run tests
    6. Self-correct if tests fail (up to max_iterations)
    """

    def __init__(self, team, tools: ProjectTools):
        self.team = team
        self.tools = tools

    async def execute_task(self, request: CodingTaskRequest) -> CodingTaskResponse:
        task_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        errors = []
        files_changed = []
        test_result = None
        git_commit_msg = None
        iterations = 0

        # Step 1: Build context by reading the project
        context = await self._build_context(request)

        if request.dry_run:
            # Plan only
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
        agents_used = []
        for iteration in range(request.max_iterations):
            iterations = iteration + 1
            logger.info(f"Task {task_id}: iteration {iterations}")

            # Get AI team's coding response
            coding_prompt = self._build_coding_prompt(
                request.task, context, errors if iteration > 0 else None
            )

            result = await self.team.collaborate(
                prompt=coding_prompt,
                context=context,
                mode=request.mode,
                agents=request.allowed_agents,
            )
            agents_used = list(set(agents_used + result.participating_agents))

            # Parse and apply file changes from response
            changes = self._parse_file_changes(result.final_answer)
            if changes:
                applied = self._apply_changes(changes)
                files_changed.extend(applied)

            # Run tests if requested
            if request.run_tests:
                test_cmd = request.test_command or self.tools.detect_test_command()
                if test_cmd:
                    test_output = self.tools.run_command(test_cmd)
                    passed = test_output["exit_code"] == 0
                    test_result = TestResult(
                        command=test_cmd,
                        passed=passed,
                        output=(test_output["stdout"] + test_output["stderr"])[-3000:],
                        duration_seconds=0,
                    )

                    if passed:
                        break  # Tests pass, we're done
                    else:
                        # Feed test failure back for next iteration
                        errors.append(f"Tests failed (iteration {iterations}):\n{test_result.output}")
                        context = await self._build_context(request)  # Re-read changed files
                else:
                    break  # No test command, can't verify
            else:
                break  # Tests not requested

        # Auto-commit if requested and tests passed
        if request.auto_commit and files_changed:
            if test_result is None or test_result.passed:
                commit_msg = f"El Gringo: {request.task[:80]}"
                git_output = self.tools.git_commit(commit_msg)
                git_commit_msg = commit_msg

        # Determine status
        if not files_changed:
            status = "failed"
            summary = "No code changes were generated"
        elif test_result and not test_result.passed:
            status = "partial"
            summary = f"Made {len(files_changed)} changes but tests still failing after {iterations} iterations"
        else:
            status = "success"
            summary = f"Completed: {len(files_changed)} files changed"
            if test_result:
                summary += ", all tests passing"

        return CodingTaskResponse(
            task_id=task_id,
            status=status,
            summary=summary,
            files_changed=files_changed,
            test_results=test_result,
            git_commit=git_commit_msg,
            agents_used=agents_used,
            iterations=iterations,
            total_time=time.time() - start_time,
            errors=errors,
        )

    async def _build_context(self, request: CodingTaskRequest) -> str:
        """Read files and build context string for the AI team."""
        parts = []

        # Project structure
        info = self.tools.get_project_info()
        parts.append(f"PROJECT: {info['project_path']}")
        parts.append(f"FILES: {info['files_count']} | LANGUAGES: {info['languages']}")
        parts.append(f"STRUCTURE:\n" + "\n".join(f"  {s}" for s in info["structure"]))
        parts.append("")

        # Read specific files
        files_to_read = request.files_to_read or []

        # If no files specified, try to find relevant ones
        if not files_to_read and request.task:
            # Search for files mentioned in the task
            all_files = self.tools.list_files()
            task_lower = request.task.lower()
            for f in all_files:
                fname = Path(f).stem.lower()
                if fname in task_lower or any(word in f.lower() for word in task_lower.split() if len(word) > 3):
                    files_to_read.append(f)
            files_to_read = files_to_read[:10]  # Cap at 10 files

        for filepath in files_to_read:
            abs_path = str(self.tools.root / filepath) if not os.path.isabs(filepath) else filepath
            content = self.tools.read_file(abs_path)
            if not content.startswith("[ERROR]"):
                parts.append(f"--- FILE: {filepath} ---")
                # Truncate very large files
                if len(content) > 8000:
                    content = content[:8000] + "\n... (truncated)"
                parts.append(content)
                parts.append("")

        # Add any user-provided context
        if request.context:
            parts.append(f"--- ADDITIONAL CONTEXT ---\n{request.context}\n")

        return "\n".join(parts)

    def _build_coding_prompt(self, task: str, context: str, errors: List[str] = None) -> str:
        """Build the prompt that tells the AI team to output structured code changes."""
        prompt = f"""You are a coding agent. Your job is to make actual code changes to fix/implement the following:

TASK: {task}

IMPORTANT: Output your changes using this EXACT format for each file you want to create or modify:

```file:path/to/file.py
<full file content or replacement content>
```

For editing specific parts of a file, use:

```edit:path/to/file.py
<<<old
the exact lines to replace
>>>new
the replacement lines
```

Rules:
- Read the context carefully before making changes
- Only change what's necessary — don't refactor unrelated code
- Keep the same code style as the existing codebase
- If you create new files, use ```file:path``` format
- If you edit existing files, use ```edit:path``` format with exact old/new blocks
- Include ALL necessary changes — don't leave TODOs or placeholders
"""

        if errors:
            prompt += f"\n\nPREVIOUS ATTEMPTS FAILED. Fix these errors:\n"
            for e in errors:
                prompt += f"\n{e}\n"

        return prompt

    async def _get_plan(self, task: str, context: str, mode: str) -> Dict[str, Any]:
        """Get a plan without executing changes."""
        prompt = f"""Plan the implementation for this task (do NOT write code, just plan):

TASK: {task}

Provide:
1. A brief summary of what needs to change
2. Numbered steps with specific file paths
3. Any risks or considerations
"""
        result = await self.team.collaborate(prompt=prompt, context=context, mode=mode)
        steps = [line.strip() for line in result.final_answer.split("\n") if line.strip()]
        return {
            "summary": result.final_answer[:500],
            "steps": steps[:20],
            "agents_used": result.participating_agents,
        }

    def _parse_file_changes(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response for file operations."""
        import re
        changes = []

        # Parse ```file:path``` blocks (full file creation/replacement)
        file_pattern = r'```file:(.+?)\n(.*?)```'
        for match in re.finditer(file_pattern, response, re.DOTALL):
            filepath = match.group(1).strip()
            content = match.group(2)
            changes.append({"action": "write", "path": filepath, "content": content})

        # Parse ```edit:path``` blocks (partial edits)
        edit_pattern = r'```edit:(.+?)\n(.*?)```'
        for match in re.finditer(edit_pattern, response, re.DOTALL):
            filepath = match.group(1).strip()
            edit_block = match.group(2)

            # Parse <<<old ... >>>new ... blocks
            old_new = re.findall(r'<<<old\n(.*?)>>>new\n(.*?)(?=<<<old|\Z)', edit_block, re.DOTALL)
            for old_text, new_text in old_new:
                changes.append({
                    "action": "edit",
                    "path": filepath,
                    "old": old_text.rstrip("\n"),
                    "new": new_text.rstrip("\n"),
                })

        return changes

    def _apply_changes(self, changes: List[Dict[str, Any]]) -> List[FileChange]:
        """Apply parsed changes to the filesystem."""
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
                    logger.info(f"Wrote file: {filepath}")

                elif change["action"] == "edit":
                    content = self.tools.read_file(abs_path)
                    if content.startswith("[ERROR]"):
                        logger.warning(f"Cannot edit {filepath}: {content}")
                        continue

                    old_text = change["old"]
                    new_text = change["new"]

                    if old_text in content:
                        new_content = content.replace(old_text, new_text, 1)
                        self.tools.write_file(abs_path, new_content)
                        diff_lines = abs(len(new_text.splitlines()) - len(old_text.splitlines()))
                        applied.append(FileChange(
                            path=filepath,
                            action="modified",
                            diff=f"-{old_text[:100]}...\n+{new_text[:100]}...",
                            lines_changed=max(diff_lines, 1),
                        ))
                        logger.info(f"Edited file: {filepath}")
                    else:
                        logger.warning(f"Edit target not found in {filepath}")

            except Exception as e:
                logger.error(f"Error applying change to {filepath}: {e}")

        return applied


# ── API Endpoints ────────────────────────────────────────────────────

def _get_engine(project_path: str):
    """Create a coding engine scoped to a project."""
    from products.fred_api.server import get_team
    tools = ProjectTools(project_path)
    team = get_team()
    return CodingAgentEngine(team, tools)


@router.post("/task", response_model=CodingTaskResponse)
async def execute_coding_task(request: CodingTaskRequest):
    """
    Execute a coding task: read code, make changes, run tests, self-correct.

    This is the main endpoint that turns El Gringo into a coding agent.
    """
    try:
        engine = _get_engine(request.project_path)
        result = await engine.execute_task(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Coding task error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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

        # Read files matching pattern
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
