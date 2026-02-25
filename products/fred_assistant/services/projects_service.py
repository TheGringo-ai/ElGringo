"""
Git/Projects Service — discovers projects from GitHub org or local directory.
On the VM: pulls repos from GitHub API (GITHUB_TOKEN + GITHUB_ORG).
Locally: scans ~/Development/Projects as before.
Clones repos on-demand for git details (branches, commits).
"""

import os
import shutil
import subprocess
import logging
import tarfile
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


# Known deploy URLs for projects
DEPLOY_URLS = {
    "managers-dashboard": "https://dashboard.chatterfix.com",
    "ManagersDashboard": "https://dashboard.chatterfix.com",
    "FredAI": "https://ai.chatterfix.com",
}

# Text-like extensions for file browser
_TEXT_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".yaml",
    ".yml", ".md", ".txt", ".toml", ".cfg", ".ini", ".env", ".sh", ".bash",
    ".sql", ".xml", ".csv", ".dockerfile", ".service", ".conf", ".gitignore",
    ".lock", ".log",
}

_MAX_READ_SIZE = 512_000


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
        "repo_html_url": "",
        "deploy_url": DEPLOY_URLS.get(name, ""),
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
            info["repo_html_url"] = _remote_to_html_url(remote)

    return info


def _remote_to_html_url(remote: str) -> str:
    """Convert a git remote URL to a GitHub HTML URL."""
    url = remote.strip()
    # git@github.com:user/repo.git → https://github.com/user/repo
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url[len("git@github.com:"):]
    # strip .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    return url


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

    clone_url = repo.get("clone_url", "")
    html_url = repo.get("html_url", "")
    repo_name = repo["name"]

    return {
        "name": repo_name,
        "path": local_path if is_cloned else "",
        "is_git": True,
        "git_branch": repo.get("default_branch", "main"),
        "git_status": "clean",
        "uncommitted_changes": 0,
        "last_commit_msg": None,
        "last_commit_date": (repo.get("pushed_at") or "")[:10] or None,
        "tech_stack": tech_stack,
        "remote_url": clone_url,
        "repo_html_url": html_url or _remote_to_html_url(clone_url),
        "deploy_url": DEPLOY_URLS.get(repo_name, ""),
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


# ── File Browser ─────────────────────────────────────────────────────


def _resolve_project_path(project_name: str) -> str:
    """Resolve project name to its absolute directory path."""
    # Check local projects dir
    local_path = os.path.join(PROJECTS_DIR, project_name)
    if os.path.isdir(local_path):
        return local_path
    # Check clone dir
    clone_path = os.path.join(CLONE_DIR, project_name)
    if os.path.isdir(clone_path):
        return clone_path
    # Try cloning from GitHub
    cloned = _ensure_clone(project_name)
    if cloned:
        return cloned
    raise FileNotFoundError(f"Project not found: {project_name}")


def _safe_path(base_dir: str, rel_path: str) -> str:
    """Prevent path traversal — normpath + startswith check."""
    resolved = os.path.normpath(os.path.join(base_dir, rel_path))
    if not resolved.startswith(os.path.normpath(base_dir)):
        raise PermissionError("Path traversal not allowed")
    return resolved


def list_project_files(project_name: str, rel_path: str = "") -> dict:
    """List files and directories in a project folder."""
    base = _resolve_project_path(project_name)
    abs_path = _safe_path(base, rel_path) if rel_path else base
    if not os.path.isdir(abs_path):
        return {"error": "Not a directory"}

    entries = []
    try:
        for name in sorted(os.listdir(abs_path)):
            if name.startswith("."):
                continue
            full = os.path.join(abs_path, name)
            rel = os.path.relpath(full, base)
            is_dir = os.path.isdir(full)
            entry = {"name": name, "path": rel, "is_dir": is_dir}
            if not is_dir:
                try:
                    entry["size"] = os.path.getsize(full)
                except OSError:
                    entry["size"] = 0
                entry["ext"] = os.path.splitext(name)[1].lower()
            entries.append(entry)
    except OSError as e:
        return {"error": str(e)}

    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return {"path": rel_path or ".", "project_dir": base, "entries": entries}


def read_project_file(project_name: str, rel_path: str) -> dict:
    """Read a file's content from a project."""
    base = _resolve_project_path(project_name)
    abs_path = _safe_path(base, rel_path)
    if not os.path.isfile(abs_path):
        return {"error": "File not found"}

    size = os.path.getsize(abs_path)
    ext = os.path.splitext(abs_path)[1].lower()
    is_text = ext in _TEXT_EXTS or ext == "" or size == 0

    if not is_text:
        return {"path": rel_path, "size": size, "ext": ext, "binary": True, "content": None}
    if size > _MAX_READ_SIZE:
        return {"error": f"File too large ({size} bytes, max {_MAX_READ_SIZE})"}

    try:
        with open(abs_path, "r", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}

    return {"path": rel_path, "size": size, "ext": ext, "binary": False, "content": content}


def write_project_file(project_name: str, rel_path: str, content: str) -> dict:
    """Write/update a file in a project."""
    base = _resolve_project_path(project_name)
    abs_path = _safe_path(base, rel_path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as f:
            f.write(content)
        return {"status": "ok", "path": rel_path, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def create_project_file(project_name: str, rel_path: str, content: str = "") -> dict:
    """Create a new file or directory in a project."""
    base = _resolve_project_path(project_name)
    abs_path = _safe_path(base, rel_path)
    if os.path.exists(abs_path):
        return {"error": "Path already exists"}
    try:
        if rel_path.endswith("/"):
            os.makedirs(abs_path, exist_ok=True)
            return {"status": "ok", "path": rel_path, "is_dir": True}
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as f:
            f.write(content)
        return {"status": "ok", "path": rel_path, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def delete_project_file(project_name: str, rel_path: str) -> dict:
    """Delete a file or directory from a project."""
    base = _resolve_project_path(project_name)
    abs_path = _safe_path(base, rel_path)
    if not os.path.exists(abs_path):
        return {"error": "Path not found"}
    try:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        return {"status": "ok", "path": rel_path}
    except Exception as e:
        return {"error": str(e)}


def rename_project_file(project_name: str, old_path: str, new_path: str) -> dict:
    """Rename/move a file within a project."""
    base = _resolve_project_path(project_name)
    abs_old = _safe_path(base, old_path)
    abs_new = _safe_path(base, new_path)
    if not os.path.exists(abs_old):
        return {"error": "Source not found"}
    if os.path.exists(abs_new):
        return {"error": "Destination already exists"}
    try:
        os.makedirs(os.path.dirname(abs_new), exist_ok=True)
        os.rename(abs_old, abs_new)
        return {"status": "ok", "old_path": old_path, "new_path": new_path}
    except Exception as e:
        return {"error": str(e)}


# ── AI Project Chat ──────────────────────────────────────────────────

PROJECT_CHAT_SYSTEM = """You are Fred, an AI development assistant. You're discussing the "{project_name}" project with the developer.

Project Info:
- Tech Stack: {tech_stack}
- Branch: {branch} ({status}, {changes} uncommitted)
- Last commit: {last_commit}
- Health Score: {health_score}/100
- Deploy URL: {deploy_url}

Top-level files:
{file_listing}

{review_context}

You can help with:
1. Analyzing code patterns and architecture
2. Suggesting improvements and fixes
3. Creating actionable TODO tasks
4. Planning features and implementations
5. Debugging issues

IMPORTANT RESPONSE FORMAT:
- Always write your response in plain, conversational English first.
- Use numbered lists and bullet points for clarity.
- Be concise, actionable, and specific. Reference file paths when relevant.
- When the user asks you to create tasks or a TODO list, explain what needs to be done in plain English FIRST.
- Then put TASK: blocks at the VERY END of your response, one per line. These are machine-readable and will be auto-created on the board — the user will NOT see them.
- TASK format (one per line at the end): TASK: {{"title": "Short action title", "priority": 1-5, "board": "{board_id}", "description": "Brief explanation", "tags": ["project:{project_name}"]}}
- Priority: 1=critical, 2=high, 3=medium, 4=low, 5=nice-to-have
- NEVER put TASK: blocks in the middle of your explanation."""


def _parse_and_create_tasks(full_text: str, project_name: str, board_id: str = "work") -> list[dict]:
    """Parse TASK: JSON blocks from AI response text and create them on boards."""
    import json as _json
    from products.fred_assistant.services.task_service import create_task

    created = []
    for line in full_text.splitlines():
        line = line.strip()
        if not line.startswith("TASK:"):
            continue
        json_str = line[5:].strip()
        try:
            t = _json.loads(json_str)
        except (_json.JSONDecodeError, ValueError):
            continue

        tags = t.get("tags", [])
        if f"project:{project_name}" not in tags:
            tags.append(f"project:{project_name}")
        try:
            task = create_task({
                "board_id": t.get("board", board_id),
                "title": t.get("title", "Untitled task"),
                "description": t.get("description", ""),
                "priority": min(max(int(t.get("priority", 3)), 1), 5),
                "tags": tags,
                "category": "ai_generated",
            })
            created.append({
                "task_id": task.get("id"),
                "title": task.get("title"),
                "priority": task.get("priority"),
                "board_id": task.get("board_id"),
            })
        except Exception as e:
            logger.warning("Failed to create task from chat: %s", e)

    return created


async def stream_project_chat(message: str, project_name: str, context: dict):
    """Stream an AI response about a project. Yields {type, data} dicts.
    After streaming, parses any TASK: blocks and auto-creates them on boards."""
    from products.fred_assistant.services.llm_shared import get_gemini

    # Gather project info
    project = get_project(project_name)
    if not project:
        yield {"type": "token", "data": f"Project '{project_name}' not found."}
        yield {"type": "done", "data": ""}
        return

    # Build file listing
    file_listing = ""
    try:
        files = list_project_files(project_name, "")
        if "entries" in files:
            lines = []
            for e in files["entries"][:30]:
                prefix = "📁" if e.get("is_dir") else "📄"
                lines.append(f"  {prefix} {e['name']}")
            file_listing = "\n".join(lines)
    except Exception:
        file_listing = "(unavailable)"

    # Build review context from passed-in context
    review_context = ""
    if context.get("action_items"):
        items = context["action_items"]
        review_context = "Recent review action items:\n" + "\n".join(
            f"- [{a.get('severity', 'medium')}] {a.get('title', '')}" for a in items[:8]
        )

    board_id = context.get("board_id", "work")

    system = PROJECT_CHAT_SYSTEM.format(
        project_name=project_name,
        tech_stack=", ".join(project.get("tech_stack", [])) or "Unknown",
        branch=project.get("git_branch") or "N/A",
        status=project.get("git_status", "unknown"),
        changes=project.get("uncommitted_changes", 0),
        last_commit=project.get("last_commit_msg") or "N/A",
        health_score=context.get("health_score", "N/A"),
        deploy_url=project.get("deploy_url") or "N/A",
        file_listing=file_listing or "(no files)",
        review_context=review_context,
        board_id=board_id,
    )

    full_prompt = f"User question: {message}"

    from products.fred_assistant.services.llm_shared import get_gemini, llm_response

    # Accumulate full response to parse TASK: blocks after streaming
    full_response = ""
    streamed = False

    # Try streaming via Gemini first
    agent = get_gemini()
    if agent and hasattr(agent, "stream_response"):
        try:
            async for chunk in agent.stream_response(full_prompt, system_override=system):
                if hasattr(chunk, "content") and chunk.content:
                    full_response += chunk.content
                    yield {"type": "token", "data": chunk.content}
                    streamed = True
                elif isinstance(chunk, str):
                    full_response += chunk
                    yield {"type": "token", "data": chunk}
                    streamed = True
        except Exception as e:
            logger.warning("Project chat stream failed: %s — falling back to llm_response", e)

    # If streaming produced nothing, fall back to llm_response (ModelRouter with full fallback chain)
    if not streamed or not full_response.strip():
        full_response = ""
        try:
            content = await llm_response(full_prompt, system, feature="project_chat")
            if content:
                full_response = content
                chunk_size = 20
                for i in range(0, len(content), chunk_size):
                    yield {"type": "token", "data": content[i:i + chunk_size]}
            else:
                yield {"type": "token", "data": "AI service is temporarily unavailable. Please try again in a moment."}
        except Exception as e:
            logger.warning("Project chat fallback also failed: %s", e)
            yield {"type": "token", "data": f"Error: {e}"}

    # Auto-create any TASK: blocks found in the response
    if "TASK:" in full_response:
        created_tasks = _parse_and_create_tasks(full_response, project_name)
        if created_tasks:
            yield {"type": "tasks_created", "data": created_tasks}

    yield {"type": "done", "data": ""}


TASK_GEN_SYSTEM = """You are Fred, an AI project planner. Analyze the project and generate actionable tasks.

Project: {project_name}
Tech Stack: {tech_stack}
Files: {file_listing}

{instructions}

Return ONLY a JSON array of task objects. Each task must have:
- title: concise actionable title (imperative, e.g. "Add unit tests for auth module")
- priority: 1 (critical) to 5 (nice-to-have)
- description: 1-2 sentence explanation
- tags: array of strings (always include "project:{project_name}")

Return 3-8 tasks. Return ONLY the JSON array, no markdown fences."""


async def generate_project_tasks(project_name: str, instructions: str = "", board_id: str = "work") -> list[dict]:
    """AI generates tasks for a project and creates them on boards."""
    import json
    from products.fred_assistant.services.llm_shared import llm_response
    from products.fred_assistant.services.task_service import create_task

    project = get_project(project_name)
    if not project:
        return []

    # Build file listing
    file_listing = ""
    try:
        files = list_project_files(project_name, "")
        if "entries" in files:
            file_listing = ", ".join(e["name"] for e in files["entries"][:30])
    except Exception:
        pass

    system = TASK_GEN_SYSTEM.format(
        project_name=project_name,
        tech_stack=", ".join(project.get("tech_stack", [])) or "Unknown",
        file_listing=file_listing or "(unavailable)",
        instructions=f"User instructions: {instructions}" if instructions else "Generate a comprehensive TODO list for this project.",
    )

    prompt = f"Analyze the {project_name} project and generate tasks."
    response = await llm_response(prompt, system)
    if not response:
        return []

    # Parse JSON from response
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        tasks_data = json.loads(cleaned)
        if not isinstance(tasks_data, list):
            return []
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse task generation JSON")
        return []

    # Create tasks on the board
    created = []
    for t in tasks_data[:8]:
        try:
            tags = t.get("tags", [])
            if f"project:{project_name}" not in tags:
                tags.append(f"project:{project_name}")
            task = create_task({
                "board_id": board_id,
                "title": t.get("title", "Untitled task"),
                "description": t.get("description", ""),
                "priority": min(max(int(t.get("priority", 3)), 1), 5),
                "tags": tags,
                "category": "ai_generated",
            })
            created.append({
                "task_id": task.get("id"),
                "title": task.get("title"),
                "priority": task.get("priority"),
                "board_id": board_id,
            })
        except Exception as e:
            logger.warning("Failed to create task: %s", e)

    return created



# ── Project Notes ─────────────────────────────────────────────────

import json as _json
import uuid
from datetime import datetime

from products.fred_assistant.database import get_conn, log_activity


def _row_to_note(row) -> dict:
    """Convert a sqlite3.Row to a note dict, parsing JSON fields."""
    d = dict(row)
    for field in ("tags", "metadata"):
        try:
            d[field] = _json.loads(d.get(field) or "{}" if field == "metadata" else d.get(field) or "[]")
        except (_json.JSONDecodeError, TypeError):
            d[field] = [] if field == "tags" else {}
    d["pinned"] = bool(d.get("pinned"))
    return d


def list_project_notes(project_name: str) -> list[dict]:
    """List all notes for a project — pinned first, then by updated_at DESC."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM project_notes WHERE project_name = ? ORDER BY pinned DESC, updated_at DESC",
            (project_name,),
        ).fetchall()
    return [_row_to_note(r) for r in rows]


def get_project_note(note_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM project_notes WHERE id = ?", (note_id,)).fetchone()
    return _row_to_note(row) if row else None


def create_project_note(project_name: str, data: dict) -> dict:
    note_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO project_notes (id, project_name, title, content, note_type, tags, pinned, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)""",
            (
                note_id,
                project_name,
                data.get("title", "Untitled"),
                data.get("content", ""),
                data.get("note_type", "manual"),
                _json.dumps(data.get("tags", [])),
                1 if data.get("pinned") else 0,
                now,
                now,
            ),
        )
    log_activity("note_created", "project_note", note_id, {"project": project_name})
    return get_project_note(note_id)


def update_project_note(note_id: str, data: dict) -> dict | None:
    existing = get_project_note(note_id)
    if not existing:
        return None
    now = datetime.utcnow().isoformat(timespec="seconds")
    sets, params = [], []
    if data.get("title") is not None:
        sets.append("title = ?"); params.append(data["title"])
    if data.get("content") is not None:
        sets.append("content = ?"); params.append(data["content"])
    if data.get("tags") is not None:
        sets.append("tags = ?"); params.append(_json.dumps(data["tags"]))
    if data.get("pinned") is not None:
        sets.append("pinned = ?"); params.append(1 if data["pinned"] else 0)
    if not sets:
        return existing
    sets.append("updated_at = ?"); params.append(now)
    params.append(note_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE project_notes SET {', '.join(sets)} WHERE id = ?", params)
    return get_project_note(note_id)


def delete_project_note(note_id: str) -> bool:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM project_notes WHERE id = ?", (note_id,))
    return cursor.rowcount > 0


NOTES_GEN_SYSTEM = """You are Fred, a senior engineering AI. Generate intelligent project notes that analyze the current state of the "{project_name}" project.

Project Info:
- Tech Stack: {tech_stack}
- Branch: {branch} ({status}, {changes} uncommitted changes)
- Last commit: {last_commit}

Recent commits:
{commits_text}

Open tasks:
{open_tasks_text}

Completed tasks:
{done_tasks_text}

Health analysis:
{health_text}

Top-level files:
{file_listing}

Generate a structured project intelligence report with these sections:

## Status Summary
Brief health assessment, branch info, recent activity level.

## What's Been Done
Key accomplishments from recent commits and completed tasks.

## What's Pending
Open tasks, backlog items, work in progress.

## Improvement Suggestions
Based on health findings, missing tests, CI gaps, security items, code quality.

## Next Steps
Top 3 priorities the developer should tackle next.

Be concise, specific, and actionable. Reference actual file paths when relevant. Write like a senior engineer briefing the team."""


async def generate_project_notes(project_name: str) -> dict | None:
    """AI-generate intelligent project notes by gathering context from multiple sources."""
    from products.fred_assistant.services.llm_shared import llm_response

    project = get_project(project_name)
    if not project:
        return None

    # 1. Recent commits
    commits = get_recent_commits(project_name, count=10)
    commits_text = "\n".join(
        f"- {c['hash']} {c['date']}: {c['message']}" for c in commits
    ) if commits else "(no recent commits)"

    # 2. Tasks filtered by project tag
    open_tasks_text = "(none)"
    done_tasks_text = "(none)"
    try:
        from products.fred_assistant.services.task_service import list_tasks
        all_tasks = list_tasks()
        project_tag = f"project:{project_name}"
        open_tasks = [t for t in all_tasks if t.get("status") != "done" and project_tag in (t.get("tags") or [])]
        done_tasks = [t for t in all_tasks if t.get("status") == "done" and project_tag in (t.get("tags") or [])]
        if open_tasks:
            open_tasks_text = "\n".join(f"- [{t.get('priority', 3)}] {t['title']}" for t in open_tasks[:10])
        if done_tasks:
            done_tasks_text = "\n".join(f"- {t['title']}" for t in done_tasks[:10])
    except Exception:
        pass

    # 3. Health analysis
    health_text = "(no analysis available)"
    try:
        from products.fred_assistant.services.repo_intelligence_service import get_latest_analysis
        analysis = get_latest_analysis(project_name)
        if analysis:
            health_text = f"Score: {analysis.get('health_score', 'N/A')}/100"
            actions = analysis.get("action_items") or []
            if isinstance(actions, str):
                try:
                    actions = _json.loads(actions)
                except Exception:
                    actions = []
            if actions:
                health_text += "\nAction items:\n" + "\n".join(
                    f"- [{a.get('severity', 'medium')}] {a.get('title', '')}" for a in actions[:8]
                )
    except Exception:
        pass

    # 4. File listing
    file_listing = "(unavailable)"
    try:
        files = list_project_files(project_name, "")
        if "entries" in files:
            file_listing = "\n".join(
                f"  {'dir' if e.get('is_dir') else 'file'}: {e['name']}" for e in files["entries"][:30]
            )
    except Exception:
        pass

    system = NOTES_GEN_SYSTEM.format(
        project_name=project_name,
        tech_stack=", ".join(project.get("tech_stack", [])) or "Unknown",
        branch=project.get("git_branch") or "N/A",
        status=project.get("git_status", "unknown"),
        changes=project.get("uncommitted_changes", 0),
        last_commit=project.get("last_commit_msg") or "N/A",
        commits_text=commits_text,
        open_tasks_text=open_tasks_text,
        done_tasks_text=done_tasks_text,
        health_text=health_text,
        file_listing=file_listing,
    )

    prompt = f"Generate intelligent project notes for {project_name}."

    try:
        content = await llm_response(prompt, system, feature="project_notes")
    except Exception as e:
        logger.warning("AI note generation failed: %s", e)
        content = ""

    if not content:
        content = (
            f"## Status Summary\n"
            f"Project: {project_name} | Branch: {project.get('git_branch', 'N/A')} | "
            f"Status: {project.get('git_status', 'unknown')}\n\n"
            f"## Recent Activity\n{commits_text}\n\n"
            f"## Open Tasks\n{open_tasks_text}\n\n"
            f"*AI analysis unavailable — showing raw data.*"
        )

    title = f"Project Intelligence — {project_name} ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')})"
    note = create_project_note(project_name, {
        "title": title,
        "content": content,
        "note_type": "ai_generated",
        "tags": ["ai", "intelligence"],
        "pinned": False,
    })
    return note


def export_project(project_name: str) -> dict:
    """Create a tar.gz export of a project. Returns path to archive."""
    base = _resolve_project_path(project_name)
    export_dir = os.path.join(PROJECTS_DIR, "_exports")
    os.makedirs(export_dir, exist_ok=True)
    archive_name = f"{project_name}-export.tar.gz"
    archive_path = os.path.join(export_dir, archive_name)

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(base, arcname=project_name)
        return {
            "status": "ok",
            "archive_path": archive_path,
            "archive_name": archive_name,
            "size": os.path.getsize(archive_path),
        }
    except Exception as e:
        return {"error": str(e)}
