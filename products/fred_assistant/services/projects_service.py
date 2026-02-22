"""
Git/Projects Service — scans local dev projects, reads git status.
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

PROJECTS_DIR = os.path.expanduser("~/Development/Projects")

# Files that indicate tech stack
TECH_INDICATORS = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java",
    "build.gradle": "Java",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "tailwind.config.js": "Tailwind",
    "tsconfig.json": "TypeScript",
    ".env": "Environment Config",
}


def _git(repo_path: str, *args, timeout: int = 5) -> str:
    """Run a git command in the given repo and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _is_git_repo(path: str) -> bool:
    return os.path.isdir(os.path.join(path, ".git"))


def detect_tech_stack(path: str) -> list[str]:
    """Detect technologies used in the project."""
    stack = set()
    try:
        entries = os.listdir(path)
    except OSError:
        return []

    for filename, tech in TECH_INDICATORS.items():
        if filename in entries:
            stack.add(tech)

    # Check for common source directories
    if any(d in entries for d in ["src", "lib", "app"]):
        # Look deeper for language hints
        for d in ["src", "lib", "app"]:
            subdir = os.path.join(path, d)
            if os.path.isdir(subdir):
                try:
                    sub_entries = os.listdir(subdir)
                    exts = {os.path.splitext(f)[1] for f in sub_entries}
                    if ".py" in exts:
                        stack.add("Python")
                    if ".jsx" in exts or ".tsx" in exts:
                        stack.add("React")
                    if ".js" in exts or ".ts" in exts:
                        stack.add("JavaScript")
                    if ".rs" in exts:
                        stack.add("Rust")
                    if ".go" in exts:
                        stack.add("Go")
                    if ".swift" in exts:
                        stack.add("Swift")
                except OSError:
                    pass

    return sorted(stack)


def get_project_info(path: str) -> dict:
    """Get info for a single project directory."""
    name = os.path.basename(path)
    info = {
        "name": name,
        "path": path,
        "is_git": _is_git_repo(path),
        "git_branch": None,
        "git_status": "clean",
        "uncommitted_changes": 0,
        "last_commit_msg": None,
        "last_commit_date": None,
        "tech_stack": detect_tech_stack(path),
        "remote_url": None,
    }

    if info["is_git"]:
        # Current branch
        info["git_branch"] = _git(path, "rev-parse", "--abbrev-ref", "HEAD") or None

        # Uncommitted changes count
        status = _git(path, "status", "--porcelain")
        changes = [l for l in status.splitlines() if l.strip()]
        info["uncommitted_changes"] = len(changes)
        info["git_status"] = "dirty" if changes else "clean"

        # Last commit
        log = _git(path, "log", "-1", "--format=%s|||%ai")
        if "|||" in log:
            msg, date_str = log.split("|||", 1)
            info["last_commit_msg"] = msg
            info["last_commit_date"] = date_str[:10]

        # Remote URL
        remote = _git(path, "remote", "get-url", "origin")
        if remote:
            info["remote_url"] = remote

    return info


def list_projects(projects_dir: str = None) -> list[dict]:
    """List all projects in the dev directory."""
    base = projects_dir or PROJECTS_DIR
    if not os.path.isdir(base):
        return []

    projects = []
    try:
        for entry in sorted(os.listdir(base)):
            full = os.path.join(base, entry)
            if os.path.isdir(full) and not entry.startswith("."):
                projects.append(get_project_info(full))
    except OSError as e:
        logger.warning(f"Error scanning projects: {e}")

    return projects


def get_recent_commits(path: str, count: int = 10) -> list[dict]:
    """Get recent commits for a project."""
    if not _is_git_repo(path):
        return []

    log = _git(path, "log", f"-{count}", "--format=%H|||%s|||%an|||%ai")
    commits = []
    for line in log.splitlines():
        parts = line.split("|||")
        if len(parts) == 4:
            commits.append({
                "hash": parts[0][:8],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3][:10],
            })
    return commits


def get_branches(path: str) -> list[dict]:
    """Get all branches for a project."""
    if not _is_git_repo(path):
        return []

    current = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
    raw = _git(path, "branch", "-a", "--format=%(refname:short)")
    branches = []
    for name in raw.splitlines():
        name = name.strip()
        if name:
            branches.append({"name": name, "current": name == current})
    return branches
