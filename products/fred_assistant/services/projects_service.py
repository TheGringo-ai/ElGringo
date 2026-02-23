"""
Git/Projects Service — discovers projects from GitHub org or local directory.
On the VM: pulls repos from GitHub API (GITHUB_TOKEN + GITHUB_ORG).
Locally: scans ~/Development/Projects as before.
Clones repos on-demand for git details (branches, commits).
"""

import os
import subprocess
import logging
import time

import httpx

logger = logging.getLogger(__name__)

PROJECTS_DIR = os.getenv("PROJECTS_DIR", os.path.expanduser("~/Development/Projects"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ORG = os.getenv("GITHUB_ORG", "")
CLONE_DIR = os.getenv("CLONE_DIR", "/opt/fredai/projects")

# Cache GitHub results for 5 minutes
_gh_cache: list[dict] = []
_gh_cache_time: float = 0
GH_CACHE_TTL = 300

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

# Language mapping from GitHub API
GH_LANGUAGE_MAP = {
    "Python": "Python",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "Rust": "Rust",
    "Go": "Go",
    "Java": "Java",
    "Ruby": "Ruby",
    "PHP": "PHP",
    "Swift": "Swift",
    "Kotlin": "Kotlin",
    "C++": "C++",
    "C#": "C#",
    "Shell": "Shell",
    "HTML": "HTML",
    "CSS": "CSS",
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
        info["git_branch"] = _git(path, "rev-parse", "--abbrev-ref", "HEAD") or None

        status = _git(path, "status", "--porcelain")
        changes = [l for l in status.splitlines() if l.strip()]
        info["uncommitted_changes"] = len(changes)
        info["git_status"] = "dirty" if changes else "clean"

        log = _git(path, "log", "-1", "--format=%s|||%ai")
        if "|||" in log:
            msg, date_str = log.split("|||", 1)
            info["last_commit_msg"] = msg
            info["last_commit_date"] = date_str[:10]

        remote = _git(path, "remote", "get-url", "origin")
        if remote:
            info["remote_url"] = remote

    return info


# ── GitHub API ───────────────────────────────────────────────────────

def _gh_api(path: str) -> dict | list | None:
    """Call GitHub API with token auth."""
    if not GITHUB_TOKEN:
        return None
    try:
        resp = httpx.get(
            f"https://api.github.com{path}",
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning("GitHub API error: %s", e)
    return None


def _fetch_github_repos() -> list[dict]:
    """Fetch repos from GitHub org/user."""
    global _gh_cache, _gh_cache_time
    now = time.time()
    if _gh_cache and now - _gh_cache_time < GH_CACHE_TTL:
        return _gh_cache

    repos = []

    # Try org repos first
    if GITHUB_ORG:
        data = _gh_api(f"/orgs/{GITHUB_ORG}/repos?per_page=100&sort=updated")
        if data:
            repos = data

    # Fallback to user repos
    if not repos:
        data = _gh_api("/user/repos?per_page=100&sort=updated&affiliation=owner")
        if data:
            repos = data

    if not repos:
        return []

    _gh_cache = repos
    _gh_cache_time = now
    return repos


def _gh_repo_to_project(repo: dict) -> dict:
    """Convert a GitHub API repo object to our project format."""
    tech_stack = []
    if repo.get("language"):
        lang = GH_LANGUAGE_MAP.get(repo["language"], repo["language"])
        tech_stack.append(lang)

    # Check local clone for more detail
    local_path = os.path.join(CLONE_DIR, repo["name"])
    is_cloned = os.path.isdir(local_path) and _is_git_repo(local_path)

    if is_cloned:
        tech_stack = detect_tech_stack(local_path) or tech_stack

    return {
        "name": repo["name"],
        "path": local_path if is_cloned else "",
        "is_git": True,
        "git_branch": repo.get("default_branch", "main"),
        "git_status": "clean",
        "uncommitted_changes": 0,
        "last_commit_msg": None,
        "last_commit_date": (repo.get("pushed_at") or "")[:10] or None,
        "tech_stack": tech_stack,
        "remote_url": repo.get("clone_url", ""),
        "description": repo.get("description", ""),
        "private": repo.get("private", False),
        "stars": repo.get("stargazers_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "source": "github",
    }


def _ensure_clone(project_name: str) -> str | None:
    """Clone a repo if not already cloned. Returns the local path or None."""
    local_path = os.path.join(CLONE_DIR, project_name)
    if os.path.isdir(local_path) and _is_git_repo(local_path):
        # Pull latest
        _git(local_path, "pull", "--ff-only")
        return local_path

    # Find the repo URL
    repos = _fetch_github_repos()
    repo = next((r for r in repos if r["name"] == project_name), None)
    if not repo:
        return None

    clone_url = repo.get("clone_url", "")
    if not clone_url:
        return None

    # Clone
    try:
        os.makedirs(CLONE_DIR, exist_ok=True)
        # Use token in URL for private repos
        if GITHUB_TOKEN and "github.com" in clone_url:
            clone_url = clone_url.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")
        subprocess.run(
            ["git", "clone", "--depth", "50", clone_url, local_path],
            capture_output=True, text=True, timeout=60,
        )
        if _is_git_repo(local_path):
            return local_path
    except Exception as e:
        logger.warning("Clone failed for %s: %s", project_name, e)

    return None


# ── Public API ───────────────────────────────────────────────────────

def list_projects(projects_dir: str = None) -> list[dict]:
    """List all projects — merge local clones + GitHub API."""
    base = projects_dir or PROJECTS_DIR
    projects_by_name: dict[str, dict] = {}

    # Scan local/clone directories for rich git info
    for scan_dir in [base, CLONE_DIR]:
        if not os.path.isdir(scan_dir):
            continue
        try:
            for entry in sorted(os.listdir(scan_dir)):
                full = os.path.join(scan_dir, entry)
                if os.path.isdir(full) and not entry.startswith(".") and entry not in projects_by_name:
                    projects_by_name[entry] = get_project_info(full)
        except OSError as e:
            logger.warning("Error scanning %s: %s", scan_dir, e)

    # Merge GitHub API repos (adds repos not yet cloned)
    if GITHUB_TOKEN:
        repos = _fetch_github_repos()
        for repo in repos:
            if repo.get("fork"):
                continue
            name = repo["name"]
            if name not in projects_by_name:
                projects_by_name[name] = _gh_repo_to_project(repo)

    return sorted(projects_by_name.values(), key=lambda p: p["name"].lower())


def get_project(project_name: str) -> dict | None:
    """Get a single project by name — local or GitHub."""
    # Check local first
    local_path = os.path.join(PROJECTS_DIR, project_name)
    if os.path.isdir(local_path):
        return get_project_info(local_path)

    # Check clones
    clone_path = os.path.join(CLONE_DIR, project_name)
    if os.path.isdir(clone_path) and _is_git_repo(clone_path):
        return get_project_info(clone_path)

    # Try GitHub
    if GITHUB_TOKEN:
        repos = _fetch_github_repos()
        repo = next((r for r in repos if r["name"] == project_name), None)
        if repo:
            return _gh_repo_to_project(repo)

    return None


def get_recent_commits(path_or_name: str, count: int = 10) -> list[dict]:
    """Get recent commits — clone on demand if needed."""
    path = path_or_name

    # If it's a name (not a path), resolve it
    if not os.path.isdir(path):
        # Try local projects dir
        local = os.path.join(PROJECTS_DIR, path_or_name)
        if os.path.isdir(local):
            path = local
        else:
            # Clone from GitHub
            cloned = _ensure_clone(path_or_name)
            if cloned:
                path = cloned
            else:
                return []

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


def get_branches(path_or_name: str) -> list[dict]:
    """Get all branches — clone on demand if needed."""
    path = path_or_name

    if not os.path.isdir(path):
        local = os.path.join(PROJECTS_DIR, path_or_name)
        if os.path.isdir(local):
            path = local
        else:
            cloned = _ensure_clone(path_or_name)
            if cloned:
                path = cloned
            else:
                return []

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
