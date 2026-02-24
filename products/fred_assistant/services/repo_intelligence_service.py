"""
Repo Intelligence Service — deep analysis engine for dev projects.
Scans repos for issues, tech debt, and opportunities. Produces a health
score and prioritized task list with revenue awareness.
"""

import json
import logging
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta

from products.fred_assistant.database import get_conn

logger = logging.getLogger(__name__)

_projects_service_cache = None


def _projects_svc():
    global _projects_service_cache
    if _projects_service_cache is None:
        from products.fred_assistant.services import projects_service
        _projects_service_cache = projects_service
    return _projects_service_cache


# ── AI Review ────────────────────────────────────────────────────────

def _get_review_agent():
    from products.fred_assistant.services.llm_shared import get_gemini
    return get_gemini()


AI_REVIEW_PROMPT = """You are a senior code reviewer. Analyze this real code and produce specific, actionable findings.

Project: {project_name}
Tech stack: {tech_stack}
Static analysis health score: {health_score}/100

Source files:
{code_content}

Return ONLY a JSON array of findings. Each finding must have:
- severity: "high" | "medium" | "low"
- category: "security" | "testing" | "performance" | "architecture" | "quality" | "devops" | "documentation" | "dependencies"
- title: specific, actionable title referencing actual code (NOT generic like "add tests")
- detail: 2-3 sentences explaining the specific issue with file/function references
- revenue_impact: "blocks launch" | "blocks sales" | null

Focus on:
1. Actual bugs or logic errors in the code
2. Security vulnerabilities specific to this codebase
3. Architecture problems (circular deps, god classes, tight coupling)
4. Missing error handling in specific functions
5. Performance issues in specific code paths

Do NOT produce generic findings like "add tests" or "add CI/CD" — only findings specific to the actual code you see.
Return 3-8 findings max. Return ONLY the JSON array."""

PROJECTS_DIR = os.getenv("PROJECTS_DIR", os.path.expanduser("~/Development/Projects"))

# Directories to skip when walking
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "coverage", ".eggs", "*.egg-info",
}

# Source file extensions worth scanning
SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java",
    ".rb", ".php", ".swift", ".kt", ".c", ".cpp", ".h",
}


# ── Helpers ──────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str, timeout: int = 10) -> str:
    """Run a command and return stdout."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _walk_source_files(path: str, max_files: int = 5000) -> list[str]:
    """Walk project tree and return source file paths (relative)."""
    files = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            ext = os.path.splitext(f)[1]
            if ext in SOURCE_EXTS:
                files.append(os.path.relpath(os.path.join(root, f), path))
                if len(files) >= max_files:
                    return files
    return files


def _empty_findings() -> dict:
    return {
        "missing_tests": {"severity": "high", "count": 0, "details": []},
        "missing_ci": {"severity": "medium", "detected": False, "details": ""},
        "todo_fixme": {"severity": "low", "count": 0, "items": []},
        "large_files": {"severity": "low", "count": 0, "items": []},
        "security_patterns": {"severity": "high", "count": 0, "items": []},
        "dependency_issues": {"severity": "medium", "count": 0, "items": []},
        "code_smells": {"severity": "medium", "count": 0, "items": []},
        "missing_docs": {"severity": "low", "detected": False},
        "dead_code_hints": {"severity": "low", "count": 0, "items": []},
    }


# ── Quick Checks ─────────────────────────────────────────────────

def _check_ci(path: str, entries: set) -> dict:
    """Check for CI/CD configuration."""
    ci_files = [
        ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile",
        "cloudbuild.yaml", ".circleci", ".travis.yml",
    ]
    for cf in ci_files:
        full = os.path.join(path, cf)
        if os.path.exists(full):
            return {"severity": "medium", "detected": True, "details": cf}
    return {"severity": "medium", "detected": False, "details": "No CI/CD configuration found"}


def _check_tests(path: str, entries: set) -> dict:
    """Check for test infrastructure."""
    test_indicators = [
        "tests", "test", "__tests__", "spec",
        "pytest.ini", "jest.config.js", "jest.config.ts",
        ".pytest.ini", "setup.cfg",
    ]
    found = []
    for ind in test_indicators:
        if ind in entries or os.path.exists(os.path.join(path, ind)):
            found.append(ind)
    # Also check for test_*.py or *.test.js patterns
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            if f.startswith("test_") and f.endswith(".py"):
                found.append(f)
                break
            if f.endswith(".test.js") or f.endswith(".test.ts") or f.endswith(".test.tsx"):
                found.append(f)
                break
        if found:
            break
    if found:
        return {"severity": "high", "count": 0, "details": found}
    return {"severity": "high", "count": 1, "details": ["No test infrastructure detected"]}


def _check_docs(path: str, entries: set) -> dict:
    """Check for documentation."""
    has_readme = "README.md" in entries or "readme.md" in entries or "README.rst" in entries
    has_docs = "docs" in entries or "CHANGELOG.md" in entries
    if has_readme:
        return {"severity": "low", "detected": True}
    return {"severity": "low", "detected": False}


def _check_todo_fixme(path: str) -> dict:
    """Scan source files for TODO/FIXME/HACK/XXX markers."""
    items = []
    try:
        result = subprocess.run(
            ["grep", "-rn", "-E", "TODO|FIXME|HACK|XXX",
             "--include=*.py", "--include=*.js", "--include=*.jsx",
             "--include=*.ts", "--include=*.tsx", "--include=*.go",
             "--include=*.rs", "--include=*.java", "--include=*.rb",
             path],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines()[:50]:
            rel = line.replace(path + "/", "", 1)
            items.append(rel[:200])
    except Exception:
        pass
    return {"severity": "low", "count": len(items), "items": items[:30]}


def _check_large_files(path: str) -> dict:
    """Find files larger than 1MB (excluding .git, node_modules, etc.)."""
    items = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            full = os.path.join(root, f)
            try:
                size = os.path.getsize(full)
                if size > 1_000_000:
                    rel = os.path.relpath(full, path)
                    items.append({"file": rel, "size_mb": round(size / 1_000_000, 1)})
            except OSError:
                pass
    return {"severity": "low", "count": len(items), "items": items[:20]}


def _check_git_health(path: str) -> dict:
    """Check git health — uncommitted changes, last commit age, branch count."""
    info = {}
    status = _run(["git", "status", "--porcelain"], path)
    changes = [l for l in status.splitlines() if l.strip()]
    info["uncommitted_changes"] = len(changes)

    log_date = _run(["git", "log", "-1", "--format=%ai"], path)
    if log_date:
        try:
            last_commit = datetime.fromisoformat(log_date.strip())
            info["days_since_last_commit"] = (datetime.now(last_commit.tzinfo) - last_commit).days
        except Exception:
            info["days_since_last_commit"] = -1
    else:
        info["days_since_last_commit"] = -1

    branches = _run(["git", "branch", "--list"], path)
    info["branch_count"] = len([b for b in branches.splitlines() if b.strip()])

    return info


def _check_dependency_freshness(path: str, entries: set) -> dict:
    """Check if dependency files exist and their age."""
    dep_files = ["package-lock.json", "requirements.txt", "poetry.lock", "Cargo.lock", "go.sum"]
    issues = []
    for df in dep_files:
        full = os.path.join(path, df)
        if os.path.isfile(full):
            try:
                mtime = os.path.getmtime(full)
                age_days = (datetime.now().timestamp() - mtime) / 86400
                if age_days > 90:
                    issues.append(f"{df} is {int(age_days)} days old")
            except OSError:
                pass
    # Check if dependency file exists at all
    has_deps = any(os.path.isfile(os.path.join(path, f)) for f in
                   ["package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod"])
    if has_deps:
        has_lock = any(os.path.isfile(os.path.join(path, f)) for f in dep_files)
        if not has_lock:
            issues.append("No lock file found (package-lock.json, poetry.lock, etc.)")
    return {"severity": "medium", "count": len(issues), "items": issues}


# ── Deep Checks ──────────────────────────────────────────────────

def _check_security_patterns(path: str) -> dict:
    """Grep for hardcoded secrets, API keys, passwords."""
    patterns = [
        r'API_KEY\s*=\s*["\'][^"\']{8,}',
        r'api_key\s*=\s*["\'][^"\']{8,}',
        r'password\s*=\s*["\'][^"\']{4,}',
        r'SECRET\s*=\s*["\'][^"\']{8,}',
        r'secret\s*=\s*["\'][^"\']{8,}',
        r'PRIVATE_KEY',
        r'BEGIN RSA PRIVATE KEY',
        r'BEGIN OPENSSH PRIVATE KEY',
    ]
    items = []
    for pattern in patterns:
        try:
            result = subprocess.run(
                ["grep", "-rn", "-E", pattern,
                 "--include=*.py", "--include=*.js", "--include=*.ts",
                 "--include=*.jsx", "--include=*.tsx", "--include=*.env",
                 "--include=*.yaml", "--include=*.yml", "--include=*.json",
                 path],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.strip().splitlines()[:10]:
                rel = line.replace(path + "/", "", 1)
                # Don't include .env.template or .env.example
                if ".env.template" in rel or ".env.example" in rel:
                    continue
                items.append(rel[:200])
        except Exception:
            pass
    # Deduplicate
    items = list(dict.fromkeys(items))
    return {"severity": "high", "count": len(items), "items": items[:20]}


def _check_test_source_ratio(path: str) -> dict:
    """Count test files vs source files."""
    source_count = 0
    test_count = 0
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            ext = os.path.splitext(f)[1]
            if ext not in SOURCE_EXTS:
                continue
            if f.startswith("test_") or f.endswith((".test.js", ".test.ts", ".test.tsx", ".spec.js", ".spec.ts")):
                test_count += 1
            else:
                source_count += 1
    ratio = test_count / max(source_count, 1)
    items = []
    if source_count > 5 and ratio < 0.2:
        items.append(f"Test-to-source ratio: {ratio:.2f} ({test_count} test files / {source_count} source files)")
    return {"severity": "medium", "count": len(items), "items": items}


def _check_complexity(path: str) -> dict:
    """Flag files with > 500 lines or functions with > 50 lines (heuristic)."""
    items = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in filenames:
            ext = os.path.splitext(f)[1]
            if ext not in SOURCE_EXTS:
                continue
            full = os.path.join(root, f)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
                if len(lines) > 500:
                    rel = os.path.relpath(full, path)
                    items.append(f"{rel}: {len(lines)} lines")
            except OSError:
                pass
            if len(items) >= 20:
                break
        if len(items) >= 20:
            break
    return {"severity": "medium", "count": len(items), "items": items[:20]}


def _check_dependency_count(path: str) -> dict:
    """Flag projects with excessive dependencies."""
    items = []
    pkg_json = os.path.join(path, "package.json")
    if os.path.isfile(pkg_json):
        try:
            with open(pkg_json, "r") as f:
                data = json.load(f)
            deps = len(data.get("dependencies", {}))
            dev_deps = len(data.get("devDependencies", {}))
            total = deps + dev_deps
            if total > 50:
                items.append(f"package.json: {deps} deps + {dev_deps} devDeps = {total} total")
        except Exception:
            pass
    req_txt = os.path.join(path, "requirements.txt")
    if os.path.isfile(req_txt):
        try:
            with open(req_txt, "r") as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            if len(lines) > 50:
                items.append(f"requirements.txt: {len(lines)} dependencies")
        except Exception:
            pass
    return {"severity": "medium", "count": len(items), "items": items}


# ── Health Score ─────────────────────────────────────────────────

def _compute_health_score(findings: dict, git_health: dict, depth: str) -> int:
    """Compute health score 0-100 from findings."""
    score = 100

    # No tests detected: -25
    if findings["missing_tests"]["count"] > 0:
        score -= 25

    # No CI/CD: -15
    if not findings["missing_ci"]["detected"]:
        score -= 15

    # No README: -10
    if not findings["missing_docs"]["detected"]:
        score -= 10

    # TODO/FIXME count
    todo_count = findings["todo_fixme"]["count"]
    if todo_count > 30:
        score -= 10
    elif todo_count > 10:
        score -= 5

    # Large files
    if findings["large_files"]["count"] > 5:
        score -= 5

    # Security patterns found: -20
    if findings["security_patterns"]["count"] > 0:
        score -= 20

    # Uncommitted changes > 20: -5
    if git_health.get("uncommitted_changes", 0) > 20:
        score -= 5

    # No recent commits (30 days): -10
    days = git_health.get("days_since_last_commit", 0)
    if days > 30:
        score -= 10

    # Deep-only deductions
    if depth == "full":
        # Low test-to-source ratio: -10
        if findings["code_smells"]["count"] > 0:
            score -= 5
        if findings["dead_code_hints"]["count"] > 0:
            score -= 10

    return max(0, min(100, score))


def _generate_summary(findings: dict, health_score: int, tech_stack: list, git_health: dict) -> str:
    """Generate a human-readable summary."""
    parts = [f"Health Score: {health_score}/100"]
    if tech_stack:
        parts.append(f"Tech: {', '.join(tech_stack)}")

    issues = []
    if findings["missing_tests"]["count"] > 0:
        issues.append("no tests")
    if not findings["missing_ci"]["detected"]:
        issues.append("no CI/CD")
    if not findings["missing_docs"]["detected"]:
        issues.append("no README")
    if findings["security_patterns"]["count"] > 0:
        issues.append(f"{findings['security_patterns']['count']} security concerns")
    if findings["todo_fixme"]["count"] > 0:
        issues.append(f"{findings['todo_fixme']['count']} TODOs/FIXMEs")

    if issues:
        parts.append(f"Issues: {', '.join(issues)}")
    else:
        parts.append("No major issues found")

    return " | ".join(parts)


# ── Core API ─────────────────────────────────────────────────────

def _resolve_repo_path(project_name: str) -> str | None:
    """Resolve a project name to its full path. Checks local, clone dir, then auto-clones."""
    path = os.path.join(PROJECTS_DIR, project_name)
    if os.path.isdir(path):
        return path
    clone_path = os.path.join(_projects_svc().CLONE_DIR, project_name)
    if os.path.isdir(clone_path):
        return clone_path
    cloned = _projects_svc()._ensure_clone(project_name)
    if cloned:
        return cloned
    return None


def analyze_repo(project_name: str, depth: str = "quick") -> dict:
    """Analyze a repository and return health score + findings."""
    path = _resolve_repo_path(project_name)
    if not path:
        return {"error": f"Project '{project_name}' not found"}

    try:
        entries = set(os.listdir(path))
    except OSError:
        entries = set()

    # Tech stack (reuse existing)
    tech_stack = _projects_svc().detect_tech_stack(path)

    # Git health
    is_git = os.path.isdir(os.path.join(path, ".git"))
    git_health = _check_git_health(path) if is_git else {}

    # Quick checks (always run)
    findings = _empty_findings()
    findings["missing_ci"] = _check_ci(path, entries)
    findings["missing_tests"] = _check_tests(path, entries)
    findings["missing_docs"] = _check_docs(path, entries)
    findings["todo_fixme"] = _check_todo_fixme(path)
    findings["large_files"] = _check_large_files(path)
    findings["dependency_issues"] = _check_dependency_freshness(path, entries)

    # Deep checks
    if depth == "full":
        findings["security_patterns"] = _check_security_patterns(path)
        findings["dead_code_hints"] = _check_test_source_ratio(path)
        findings["code_smells"] = _check_complexity(path)
        dep_count = _check_dependency_count(path)
        if dep_count["count"] > 0:
            findings["dependency_issues"]["items"].extend(dep_count["items"])
            findings["dependency_issues"]["count"] += dep_count["count"]

    # Health score
    health_score = _compute_health_score(findings, git_health, depth)

    # Summary
    summary = _generate_summary(findings, health_score, tech_stack, git_health)

    # Save to DB
    analysis_id = str(uuid.uuid4())[:8]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO repo_analyses
               (id, project_name, project_path, depth, health_score, tech_stack, findings, tasks_generated, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (analysis_id, project_name, path, depth, health_score,
             json.dumps(tech_stack), json.dumps(findings), "[]", summary),
        )

    return {
        "id": analysis_id,
        "project_name": project_name,
        "project_path": path,
        "depth": depth,
        "health_score": health_score,
        "tech_stack": tech_stack,
        "findings": findings,
        "tasks_generated": [],
        "summary": summary,
        "git_health": git_health,
        "created_at": datetime.now().isoformat(),
    }


def get_analysis(analysis_id: str) -> dict | None:
    """Fetch a stored analysis by ID."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM repo_analyses WHERE id = ?", (analysis_id,)).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def get_latest_analysis(project_name: str) -> dict | None:
    """Fetch the most recent analysis for a project."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM repo_analyses WHERE project_name = ? ORDER BY created_at DESC LIMIT 1",
            (project_name,),
        ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def list_analyses(project_name: str = None, limit: int = 20) -> list[dict]:
    """List analyses, optionally filtered by project."""
    with get_conn() as conn:
        if project_name:
            rows = conn.execute(
                "SELECT * FROM repo_analyses WHERE project_name = ? ORDER BY created_at DESC LIMIT ?",
                (project_name, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM repo_analyses ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _detect_tech_context(tech_stack: list) -> dict:
    """Detect which tech-specific steps to include."""
    stack_lower = [t.lower() for t in tech_stack]
    return {
        "python": any(t in stack_lower for t in ["python"]),
        "node": any(t in stack_lower for t in ["node.js", "javascript", "react", "vite", "next.js"]),
        "docker": "docker" in stack_lower,
        "react": "react" in stack_lower,
    }


def generate_tasks_from_analysis(analysis_id: str, create_tasks: bool = False) -> list[dict]:
    """Convert analysis findings into detailed, step-by-step task lists."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        return []

    findings = analysis["findings"]
    project = analysis["project_name"]
    tech = _detect_tech_context(analysis.get("tech_stack", []))
    tasks = []

    # ── Missing tests → step-by-step setup ────────────────────────
    if findings.get("missing_tests", {}).get("count", 0) > 0:
        test_steps = []
        if tech["python"]:
            test_steps.extend([
                f"[{project}] Install pytest: pip install pytest pytest-cov",
                f"[{project}] Create tests/ directory and tests/__init__.py",
                f"[{project}] Write first test file (test_main.py) for critical path",
                f"[{project}] Add pytest.ini or pyproject.toml [tool.pytest] config",
                f"[{project}] Run tests and verify: pytest tests/ -v",
            ])
        elif tech["node"]:
            test_steps.extend([
                f"[{project}] Install test framework: npm install -D jest",
                f"[{project}] Add jest config to package.json or jest.config.js",
                f"[{project}] Create __tests__/ directory",
                f"[{project}] Write first test for core module",
                f"[{project}] Add test script to package.json: \"test\": \"jest\"",
            ])
        else:
            test_steps.extend([
                f"[{project}] Choose and install test framework",
                f"[{project}] Create test directory structure",
                f"[{project}] Write tests for core functionality",
            ])
        for step in test_steps:
            tasks.append({
                "title": step,
                "description": f"Part of: Set up test infrastructure for {project}",
                "priority": 1,
                "board": "fredai",
                "category": "testing",
                "revenue_impact": "blocks launch",
            })

    # ── Missing CI/CD → step-by-step pipeline ─────────────────────
    ci = findings.get("missing_ci", {})
    if not ci.get("detected", False):
        ci_steps = [
            f"[{project}] Create .github/workflows/ directory",
            f"[{project}] Add CI workflow (lint + test on push/PR)",
        ]
        if tech["python"]:
            ci_steps.append(f"[{project}] Add Python CI steps: install deps, run pytest, run ruff")
        elif tech["node"]:
            ci_steps.append(f"[{project}] Add Node CI steps: npm ci, npm test, npm run lint")
        if tech["docker"]:
            ci_steps.append(f"[{project}] Add Docker build step to CI")
        ci_steps.append(f"[{project}] Add deploy workflow (staging/production)")

        for step in ci_steps:
            tasks.append({
                "title": step,
                "description": f"Part of: Set up CI/CD pipeline for {project}",
                "priority": 2,
                "board": "fredai",
                "category": "devops",
                "revenue_impact": "blocks launch",
            })

    # ── Missing docs → step-by-step ───────────────────────────────
    if not findings.get("missing_docs", {}).get("detected", False):
        doc_steps = [
            f"[{project}] Create README.md with project description",
            f"[{project}] Add setup/install instructions to README",
            f"[{project}] Document environment variables and configuration",
            f"[{project}] Add usage examples or API reference",
        ]
        for step in doc_steps:
            tasks.append({
                "title": step,
                "description": f"Part of: Add documentation for {project}",
                "priority": 3,
                "board": "fredai",
                "category": "documentation",
                "revenue_impact": "blocks sales",
            })

    # ── Security issues → one task per file ───────────────────────
    sec = findings.get("security_patterns", {})
    if sec.get("count", 0) > 0:
        tasks.append({
            "title": f"[{project}] Move hardcoded secrets to .env file",
            "description": "Create .env (if missing) and move all secrets there. Add .env to .gitignore.",
            "priority": 1,
            "board": "fredai",
            "category": "security",
            "revenue_impact": "blocks launch",
        })
        for item in sec.get("items", [])[:10]:
            # item is "file:line: content"
            file_ref = item.split(":")[0] if ":" in item else item
            tasks.append({
                "title": f"[{project}] Fix secret in {file_ref[:60]}",
                "description": f"Replace hardcoded value with env var.\nFound: {item[:200]}",
                "priority": 1,
                "board": "fredai",
                "category": "security",
                "revenue_impact": "blocks launch",
            })

    # ── TODO/FIXME items → individual tasks (up to 20) ────────────
    todo = findings.get("todo_fixme", {})
    todo_items = todo.get("items", [])
    if todo_items:
        for item in todo_items[:20]:
            parts = item.split(":", 2)
            if len(parts) >= 3:
                file_ref = parts[0].strip()
                line_ref = parts[1].strip()
                text = parts[2].strip()[:120]
                marker = "FIXME" if "FIXME" in item.upper() else "TODO" if "TODO" in item.upper() else "HACK"
            else:
                file_ref = ""
                line_ref = ""
                text = item[:120]
                marker = "TODO"
            tasks.append({
                "title": f"[{project}] {marker}: {text}",
                "description": f"{file_ref}:{line_ref}" if file_ref else text,
                "priority": 2 if marker == "FIXME" else 3,
                "board": "fredai",
                "category": "tech_debt",
                "revenue_impact": None,
            })

    # ── Dependency issues → individual tasks ──────────────────────
    dep = findings.get("dependency_issues", {})
    if dep.get("count", 0) > 0:
        for item in dep.get("items", []):
            tasks.append({
                "title": f"[{project}] {item[:80]}",
                "description": item,
                "priority": 2,
                "board": "fredai",
                "category": "dependencies",
                "revenue_impact": None,
            })

    # ── Complex files → individual refactor tasks ─────────────────
    smells = findings.get("code_smells", {})
    if smells.get("count", 0) > 0:
        for item in smells.get("items", [])[:10]:
            tasks.append({
                "title": f"[{project}] Refactor: {item[:70]}",
                "description": f"File exceeds 500 lines — split into smaller modules.\n{item}",
                "priority": 3,
                "board": "fredai",
                "category": "refactoring",
                "revenue_impact": None,
            })

    # ── Large files → individual tasks ────────────────────────────
    large = findings.get("large_files", {})
    if large.get("count", 0) > 0:
        for item in large.get("items", [])[:5]:
            tasks.append({
                "title": f"[{project}] Reduce {item['file']} ({item['size_mb']}MB)",
                "description": f"File is over 1MB. Consider git LFS, compression, or removal.",
                "priority": 3,
                "board": "fredai",
                "category": "optimization",
                "revenue_impact": None,
            })

    # ── Low test coverage ─────────────────────────────────────────
    dead = findings.get("dead_code_hints", {})
    if dead.get("count", 0) > 0:
        for item in dead.get("items", []):
            tasks.append({
                "title": f"[{project}] Improve test coverage",
                "description": item,
                "priority": 2,
                "board": "fredai",
                "category": "testing",
                "revenue_impact": None,
            })

    # ── Create real tasks on the board (deduplicated) ───────────
    if create_tasks and tasks:
        from products.fred_assistant.services import task_service
        existing = task_service.list_tasks(board_id="fredai")
        existing_titles = {t["title"] for t in existing}
        created_count = 0
        for t in tasks:
            if t["title"] in existing_titles:
                continue  # skip duplicate
            created = task_service.create_task({
                "board_id": t["board"],
                "title": t["title"],
                "description": t["description"],
                "status": "backlog",
                "priority": t["priority"],
                "category": t.get("category", "general"),
                "tags": [project, t.get("category", "review")],
            })
            t["task_id"] = created["id"]
            existing_titles.add(t["title"])
            created_count += 1

    # Store task list in analysis
    with get_conn() as conn:
        conn.execute(
            "UPDATE repo_analyses SET tasks_generated = ? WHERE id = ?",
            (json.dumps(tasks), analysis_id),
        )

    return tasks


async def generate_roadmap(project_name: str) -> dict:
    """AI-generated roadmap from the latest analysis."""
    analysis = get_latest_analysis(project_name)
    if not analysis:
        # Run a quick analysis first
        analysis = analyze_repo(project_name, depth="quick")
        if "error" in analysis:
            return analysis

    findings = analysis["findings"]
    tech_stack = analysis["tech_stack"]
    health_score = analysis["health_score"]

    # Build context for AI
    issues = []
    if findings.get("missing_tests", {}).get("count", 0) > 0:
        issues.append("No test infrastructure")
    ci = findings.get("missing_ci", {})
    if not ci.get("detected", False):
        issues.append("No CI/CD")
    if not findings.get("missing_docs", {}).get("detected", False):
        issues.append("No documentation")
    sec = findings.get("security_patterns", {})
    if sec.get("count", 0) > 0:
        issues.append(f"{sec['count']} security concerns")
    todo = findings.get("todo_fixme", {})
    if todo.get("count", 0) > 0:
        issues.append(f"{todo['count']} TODO/FIXME items")

    roadmap = {
        "project": project_name,
        "health_score": health_score,
        "tech_stack": tech_stack,
        "sprint_1_week": [],
        "roadmap_30_day": [],
        "revenue_suggestions": [],
    }

    # Generate sprint priorities based on findings
    if findings.get("security_patterns", {}).get("count", 0) > 0:
        roadmap["sprint_1_week"].append("Fix security concerns (hardcoded secrets/keys)")
    if findings.get("missing_tests", {}).get("count", 0) > 0:
        roadmap["sprint_1_week"].append("Set up test framework and write critical path tests")
    if not findings.get("missing_ci", {}).get("detected", False):
        roadmap["sprint_1_week"].append("Add CI/CD pipeline (GitHub Actions recommended)")
    if not findings.get("missing_docs", {}).get("detected", False):
        roadmap["sprint_1_week"].append("Create README.md with setup instructions")

    # 30-day roadmap
    roadmap["roadmap_30_day"] = [
        "Achieve 70%+ test coverage on critical paths",
        "Implement automated deployment pipeline",
        "Address all TODO/FIXME items",
        "Performance optimization pass",
    ]
    if findings.get("code_smells", {}).get("count", 0) > 0:
        roadmap["roadmap_30_day"].append("Refactor high-complexity files")

    # Revenue suggestions
    if health_score >= 70:
        roadmap["revenue_suggestions"].append("Ready for beta users — start onboarding")
    elif health_score >= 40:
        roadmap["revenue_suggestions"].append("Fix critical issues first, then soft launch")
    else:
        roadmap["revenue_suggestions"].append("Significant work needed before launch")

    roadmap["revenue_suggestions"].append("Add monitoring/analytics for usage insights")

    return roadmap


async def review_repo(project_name: str) -> dict:
    """Run a full code review — static analysis + AI review of actual code."""
    analysis = analyze_repo(project_name, depth="full")
    if "error" in analysis:
        return analysis

    findings = analysis["findings"]
    health_score = analysis["health_score"]
    tech_stack = analysis["tech_stack"]
    path = analysis["project_path"]

    # Build TODO items from the todo_fixme scan
    todo_items = []
    for item in findings.get("todo_fixme", {}).get("items", []):
        parts = item.split(":", 2)
        if len(parts) >= 3:
            todo_items.append({
                "file": parts[0].strip(),
                "line": parts[1].strip(),
                "text": parts[2].strip()[:150],
                "type": "TODO" if "TODO" in item.upper() else
                        "FIXME" if "FIXME" in item.upper() else
                        "HACK" if "HACK" in item.upper() else "XXX",
            })
        else:
            todo_items.append({"file": "", "line": "", "text": item[:150], "type": "TODO"})

    # ── AI-powered code review (reads actual files) ──────────────────
    action_items = await _ai_review_code(path, project_name, tech_stack, health_score)

    # ── Fallback: append static findings if AI returned nothing ──────
    if not action_items:
        action_items = _static_action_items(findings)

    # Sort action items: high first, then medium, then low
    severity_order = {"high": 0, "medium": 1, "low": 2}
    action_items.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 9))

    return {
        "analysis_id": analysis["id"],
        "project_name": project_name,
        "health_score": health_score,
        "tech_stack": tech_stack,
        "summary": analysis["summary"],
        "todo_items": todo_items,
        "todo_count": len(todo_items),
        "action_items": action_items,
        "action_count": len(action_items),
        "findings": findings,
        "created_at": analysis["created_at"],
    }


async def _ai_review_code(path: str, project_name: str, tech_stack: list, health_score: int) -> list[dict]:
    """Read actual code files and use AI to find real issues."""
    agent = _get_review_agent()
    if not agent:
        return []

    # Lazy import to avoid circular dependency (fred_tools imports this module)
    from products.fred_assistant.services.fred_tools import _read_project_files

    # Read real source files
    files = _read_project_files(path, max_files=8)
    if not files:
        return []

    code_content = "\n\n".join(
        f"### {f['path']} ({f['language']})\n```\n{f['content'][:2000]}\n```"
        for f in files
    )

    prompt = AI_REVIEW_PROMPT.format(
        project_name=project_name,
        tech_stack=", ".join(tech_stack) or "unknown",
        health_score=health_score,
        code_content=code_content[:8000],
    )

    try:
        resp = await agent.generate_response(prompt)
        if resp.error or not resp.content:
            logger.warning("AI review failed: %s", resp.error)
            return []

        # Parse JSON from response
        cleaned = resp.content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        items = json.loads(cleaned)
        if isinstance(items, list):
            return items[:8]
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("AI review JSON parse failed: %s", e)
    except Exception as e:
        logger.warning("AI review error: %s", e)

    return []


def _static_action_items(findings: dict) -> list[dict]:
    """Fallback: build action items from static analysis when AI is unavailable."""
    action_items = []

    if findings.get("missing_tests", {}).get("count", 0) > 0:
        action_items.append({
            "severity": "high", "category": "testing",
            "title": "Add test infrastructure",
            "detail": "No tests detected. Add pytest/jest and write initial test suite.",
            "revenue_impact": "blocks launch",
        })

    ci = findings.get("missing_ci", {})
    if not ci.get("detected", False):
        action_items.append({
            "severity": "medium", "category": "devops",
            "title": "Set up CI/CD pipeline",
            "detail": "No CI/CD configuration. Add GitHub Actions or similar.",
            "revenue_impact": "blocks launch",
        })

    if not findings.get("missing_docs", {}).get("detected", False):
        action_items.append({
            "severity": "low", "category": "documentation",
            "title": "Add README documentation",
            "detail": "No README.md found.",
            "revenue_impact": "blocks sales",
        })

    sec = findings.get("security_patterns", {})
    if sec.get("count", 0) > 0:
        action_items.append({
            "severity": "high", "category": "security",
            "title": f"Fix {sec['count']} security concerns",
            "detail": "Potential hardcoded secrets:\n" + "\n".join(sec.get("items", [])[:3]),
            "revenue_impact": "blocks launch",
        })

    dep = findings.get("dependency_issues", {})
    if dep.get("count", 0) > 0:
        action_items.append({
            "severity": "medium", "category": "dependencies",
            "title": "Address dependency issues",
            "detail": "\n".join(dep.get("items", [])[:3]),
            "revenue_impact": None,
        })

    smells = findings.get("code_smells", {})
    if smells.get("count", 0) > 0:
        action_items.append({
            "severity": "medium", "category": "refactoring",
            "title": f"Refactor {smells['count']} complex files",
            "detail": "Files over 500 lines:\n" + "\n".join(smells.get("items", [])[:3]),
            "revenue_impact": None,
        })

    large = findings.get("large_files", {})
    if large.get("count", 0) > 0:
        items_str = ", ".join(f"{i['file']} ({i['size_mb']}MB)" for i in large.get("items", [])[:3])
        action_items.append({
            "severity": "low", "category": "optimization",
            "title": f"Address {large['count']} large files",
            "detail": items_str,
            "revenue_impact": None,
        })

    dead = findings.get("dead_code_hints", {})
    if dead.get("count", 0) > 0:
        action_items.append({
            "severity": "medium", "category": "testing",
            "title": "Improve test coverage",
            "detail": "\n".join(dead.get("items", [])[:3]),
            "revenue_impact": None,
        })

    return action_items


def _row_to_dict(row) -> dict:
    """Convert a DB row to a dict with JSON parsing."""
    d = dict(row)
    for field in ("tech_stack", "findings", "tasks_generated"):
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d
