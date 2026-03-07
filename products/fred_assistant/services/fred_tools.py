"""
Fred Tools — Action execution engine for Fred Assistant.
Parses ACTION: markers from AI responses and executes them against local services.
"""

import json
import logging
import os
import re
import subprocess
from datetime import date

from products.fred_assistant.database import get_conn, log_activity
# Lazy service placeholders — set to None so @patch() can find them for tests,
# but _svc() skips None and imports the real module on first use.
task_service = None
memory_service = None
calendar_service = None
coach_service = None
projects_service = None
content_service = None
focus_service = None
crm_service = None
publish_service = None
metrics_service = None
inbox_service = None
playbook_service = None
repo_intelligence_service = None
platform_services = None


def _svc(name: str):
    """Lazy-load a service module by name. Stores in globals() for @patch compatibility."""
    cached = globals().get(name)
    if cached is not None:
        return cached
    import importlib
    mod = importlib.import_module(f"products.fred_assistant.services.{name}")
    globals()[name] = mod
    return mod

logger = logging.getLogger(__name__)

# ── Security ────────────────────────────────────────────────────────

ALLOWED_ROOTS = [
    os.path.expanduser("~/Development"),
    os.path.expanduser("~/Documents"),
    "/tmp",
    "/private/tmp",  # macOS resolves /tmp -> /private/tmp
    "/opt/elgringo/projects",  # VM clone directory
]

BLOCKED_PATHS = [
    os.path.expanduser("~/.ssh"),
    os.path.expanduser("~/.gnupg"),
    os.path.expanduser("~/.aws"),
    os.path.expanduser("~/.config"),
    "/etc",
    "/private/etc",  # macOS resolves /etc -> /private/etc
    "/System",
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/var",
    "/private/var",  # macOS resolves /var -> /private/var
]

MAX_FILE_SIZE = 500 * 1024  # 500KB
MAX_ROUNDS = 5


def validate_path(path: str) -> str:
    """Validate and resolve a file path. Returns resolved path or raises ValueError."""
    resolved = os.path.realpath(os.path.expanduser(path))

    for blocked in BLOCKED_PATHS:
        if resolved.startswith(blocked):
            raise ValueError(f"Access denied: {path} is in a restricted directory")

    for root in ALLOWED_ROOTS:
        if resolved.startswith(root):
            return resolved

    raise ValueError(
        f"Access denied: {path} is outside allowed directories "
        f"({', '.join(ALLOWED_ROOTS)})"
    )


# ── Action Parsing ──────────────────────────────────────────────────

# Matches ACTION: name(...) — handles nested parens inside quoted strings
ACTION_RE = re.compile(
    r'ACTION:\s*(\w+)\(((?:[^()]*|"[^"]*")*)\)'
)
PARAM_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|([\d.]+)|(true|false)|(\[.*?\]))')


def parse_params(param_str: str) -> dict:
    """Parse key=value parameters from an ACTION: call."""
    params = {}
    for match in PARAM_RE.finditer(param_str):
        key = match.group(1)
        if match.group(2) is not None:  # string
            params[key] = match.group(2)
        elif match.group(3) is not None:  # number
            val = match.group(3)
            params[key] = int(val) if "." not in val else float(val)
        elif match.group(4) is not None:  # boolean
            params[key] = match.group(4) == "true"
        elif match.group(5) is not None:  # array
            try:
                params[key] = json.loads(match.group(5))
            except json.JSONDecodeError:
                params[key] = match.group(5)
    return params


def parse_actions(text: str) -> list[dict]:
    """Extract all ACTION: calls from AI response text."""
    actions = []
    for match in ACTION_RE.finditer(text):
        name = match.group(1)
        params = parse_params(match.group(2))
        actions.append({"name": name, "params": params})
    return actions


def strip_action_lines(text: str) -> str:
    """Remove ACTION: lines from text before showing to user."""
    lines = text.split("\n")
    cleaned = [line for line in lines if not line.strip().startswith("ACTION:")]
    return "\n".join(cleaned).strip()


# ── Tool Executors ──────────────────────────────────────────────────

# ─── Task Management ───────────────────────────────────────────────

def _exec_create_task(params: dict) -> dict:
    board_id = params.get("board", "work")
    data = {
        "board_id": board_id,
        "title": params.get("title", "Untitled task"),
        "priority": params.get("priority", 3),
        "description": params.get("description", ""),
    }
    if params.get("due_date"):
        data["due_date"] = params["due_date"]
    task = _svc("task_service").create_task(data)
    return {"success": True, "task": task, "message": f"Created task: {task['title']} on {board_id} board"}


def _exec_update_task(params: dict) -> dict:
    task_id = params.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id is required"}
    updates = {}
    for key in ["status", "priority", "title", "description", "due_date", "board_id"]:
        if key in params:
            updates[key] = params[key]
    # Allow 'board' as alias for 'board_id'
    if "board" in params and "board_id" not in updates:
        updates["board_id"] = params["board"]
    if not updates:
        return {"success": False, "error": "No fields to update"}
    task = _svc("task_service").update_task(task_id, updates)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    return {"success": True, "task": task, "message": f"Updated task: {task['title']}"}


def _exec_complete_task(params: dict) -> dict:
    task_id = params.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id is required"}
    task = _svc("task_service").update_task(task_id, {"status": "done"})
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    return {"success": True, "task": task, "message": f"Completed: {task['title']}"}


def _exec_delete_task(params: dict) -> dict:
    task_id = params.get("task_id")
    if not task_id:
        return {"success": False, "error": "task_id is required"}
    task = _svc("task_service").get_task(task_id)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}
    title = task["title"]
    _svc("task_service").delete_task(task_id)
    return {"success": True, "message": f"Deleted task: {title}"}


def _exec_list_tasks(params: dict) -> dict:
    board = params.get("board")
    status = params.get("status")
    tasks = _svc("task_service").list_tasks(board_id=board, status=status)
    summary = []
    for t in tasks[:20]:
        line = f"[{t['id']}] {t['title']} (P{t['priority']}, {t['status']}, board:{t['board_id']})"
        if t.get("due_date"):
            line += f" due:{t['due_date']}"
        summary.append(line)
    return {
        "success": True,
        "count": len(tasks),
        "tasks": summary,
        "message": f"Found {len(tasks)} tasks" + (f" on {board}" if board else ""),
    }


def _exec_search_tasks(params: dict) -> dict:
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "query is required"}
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM tasks
               WHERE (title LIKE ? OR description LIKE ?) AND status != 'done'
               ORDER BY priority ASC LIMIT 20""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    tasks = [dict(r) for r in rows]
    summary = []
    for t in tasks:
        line = f"[{t['id']}] {t['title']} (P{t['priority']}, {t['status']}, board:{t['board_id']})"
        if t.get("due_date"):
            line += f" due:{t['due_date']}"
        summary.append(line)
    return {
        "success": True,
        "count": len(tasks),
        "tasks": summary,
        "message": f"Found {len(tasks)} tasks matching '{query}'",
    }


def _exec_create_todo_list(params: dict) -> dict:
    title = params.get("title", "Todo List")
    items = params.get("items", [])
    board = params.get("board", "work")
    if not items:
        return {"success": False, "error": "items list is required"}
    created = []
    for i, item in enumerate(items):
        item_title = item if isinstance(item, str) else str(item)
        task = _svc("task_service").create_task({
            "board_id": board,
            "title": item_title,
            "priority": 3,
            "description": f"Part of: {title}",
        })
        created.append(task)
    return {
        "success": True,
        "count": len(created),
        "tasks": [t["title"] for t in created],
        "message": f"Created {len(created)} tasks for '{title}' on {board} board",
    }


# ─── Memory ────────────────────────────────────────────────────────

def _exec_remember(params: dict) -> dict:
    category = params.get("category", "general")
    key = params.get("key")
    value = params.get("value")
    if not key or not value:
        return {"success": False, "error": "key and value are required"}
    mem = _svc("memory_service").remember(category, key, value)
    return {"success": True, "memory": mem, "message": f"Remembered: {key} = {value}"}


def _exec_search_memory(params: dict) -> dict:
    query = params.get("query", "")
    if not query:
        return {"success": False, "error": "query is required"}
    results = _svc("memory_service").search_memories(query)
    summary = [f"[{m['category']}] {m['key']}: {m['value']}" for m in results[:10]]
    return {"success": True, "count": len(results), "results": summary}


def _exec_forget(params: dict) -> dict:
    memory_id = params.get("memory_id")
    key = params.get("key")
    category = params.get("category")
    if not memory_id and not key:
        return {"success": False, "error": "memory_id or key is required"}
    # If key provided, find the memory first
    if not memory_id and key:
        results = _svc("memory_service").search_memories(key)
        if category:
            results = [m for m in results if m["category"] == category]
        if not results:
            return {"success": False, "error": f"No memory found for key '{key}'"}
        memory_id = results[0]["id"]
    mem = _svc("memory_service").get_memory(memory_id)
    if not mem:
        return {"success": False, "error": f"Memory {memory_id} not found"}
    label = f"{mem['key']}: {mem['value']}"
    _svc("memory_service").forget(memory_id)
    return {"success": True, "message": f"Forgot: {label}"}


# ─── Calendar ──────────────────────────────────────────────────────

def _exec_create_event(params: dict) -> dict:
    data = {
        "title": params.get("title", "Untitled event"),
        "start_date": params.get("start_date", date.today().isoformat()),
        "start_time": params.get("start_time"),
        "end_time": params.get("end_time"),
        "event_type": params.get("event_type", "event"),
        "description": params.get("description", ""),
    }
    event = _svc("calendar_service").create_event(data)
    return {"success": True, "event": event, "message": f"Created event: {event['title']} on {data['start_date']}"}


def _exec_list_events(params: dict) -> dict:
    days = params.get("days", 7)
    events = _svc("calendar_service").get_upcoming(days=days)
    summary = []
    for e in events[:15]:
        line = f"[{e['id']}] {e['title']} ({e['event_type']}) on {e['start_date']}"
        if e.get("start_time"):
            line += f" at {e['start_time']}"
        summary.append(line)
    return {"success": True, "count": len(events), "events": summary}


def _exec_update_event(params: dict) -> dict:
    event_id = params.get("event_id")
    if not event_id:
        return {"success": False, "error": "event_id is required"}
    updates = {}
    for key in ["title", "description", "event_type", "start_date", "start_time", "end_time", "location"]:
        if key in params:
            updates[key] = params[key]
    if not updates:
        return {"success": False, "error": "No fields to update"}
    event = _svc("calendar_service").update_event(event_id, updates)
    if not event:
        return {"success": False, "error": f"Event {event_id} not found"}
    return {"success": True, "event": event, "message": f"Updated event: {event['title']}"}


def _exec_delete_event(params: dict) -> dict:
    event_id = params.get("event_id")
    if not event_id:
        return {"success": False, "error": "event_id is required"}
    event = _svc("calendar_service").get_event(event_id)
    if not event:
        return {"success": False, "error": f"Event {event_id} not found"}
    title = event["title"]
    _svc("calendar_service").delete_event(event_id)
    return {"success": True, "message": f"Deleted event: {title}"}


# ─── Goals & Accountability ───────────────────────────────────────

def _exec_create_goal(params: dict) -> dict:
    data = {
        "title": params.get("title", "Untitled goal"),
        "category": params.get("category", "business"),
        "target_date": params.get("target_date"),
        "description": params.get("description", ""),
    }
    goal = _svc("coach_service").create_goal(data)
    return {"success": True, "goal": goal, "message": f"Created goal: {goal['title']}"}


def _exec_update_goal(params: dict) -> dict:
    goal_id = params.get("goal_id")
    if not goal_id:
        return {"success": False, "error": "goal_id is required"}
    updates = {}
    for key in ["progress", "status", "title", "description"]:
        if key in params:
            updates[key] = params[key]
    goal = _svc("coach_service").update_goal(goal_id, updates)
    if not goal:
        return {"success": False, "error": f"Goal {goal_id} not found"}
    return {"success": True, "goal": goal, "message": f"Updated goal: {goal['title']} ({goal['progress']}%)"}


def _exec_delete_goal(params: dict) -> dict:
    goal_id = params.get("goal_id")
    if not goal_id:
        return {"success": False, "error": "goal_id is required"}
    goal = _svc("coach_service").get_goal(goal_id)
    if not goal:
        return {"success": False, "error": f"Goal {goal_id} not found"}
    title = goal["title"]
    _svc("coach_service").delete_goal(goal_id)
    return {"success": True, "message": f"Deleted goal: {title}"}


def _exec_accountability_check(params: dict) -> dict:
    goals = _svc("coach_service").list_goals(status="active")
    stats = _svc("task_service").get_dashboard_stats()
    today = date.today().isoformat()

    # Query overdue directly in SQL instead of loading all tasks
    with get_conn() as conn:
        overdue_rows = conn.execute(
            "SELECT id, title, due_date, board_id FROM tasks WHERE due_date < ? AND status != 'done' ORDER BY due_date LIMIT 20",
            (today,),
        ).fetchall()
    overdue = [dict(r) for r in overdue_rows]

    report = {
        "active_goals": len(goals),
        "goals": [
            {"title": g["title"], "progress": g["progress"], "category": g["category"]}
            for g in goals[:10]
        ],
        "task_stats": stats,
        "overdue_count": len(overdue),
        "overdue_tasks": [
            {"title": t["title"], "due_date": t["due_date"], "board": t["board_id"]}
            for t in overdue[:10]
        ],
    }
    return {"success": True, "report": report, "message": "Accountability check complete"}


def _exec_find_revenue(params: dict) -> dict:
    projects = _svc("projects_service").list_projects()
    scored = []
    for p in projects:
        score = 0
        strategies = []
        stack = [s.lower() for s in p.get("tech_stack", [])]
        name_lower = p["name"].lower()

        # Full-stack (web + API)
        has_frontend = any(t in stack for t in ["react", "next.js", "vite", "javascript"])
        has_backend = any(t in stack for t in ["python", "node.js", "go", "rust"])
        if has_frontend and has_backend:
            score += 30
            strategies.append("SaaS product (has full frontend + backend)")

        # AI/ML project
        if any(kw in name_lower for kw in ["ai", "ml", "smart", "intelligence", "gpt"]):
            score += 20
            strategies.append("AI-powered service or API product")

        # Active development
        if p.get("git_status") == "dirty":
            score += 15

        # Product-like naming
        if any(kw in name_lower for kw in ["dashboard", "platform", "saas", "app", "studio", "hub"]):
            score += 15
            strategies.append("White-label or multi-tenant platform")

        # Modern frontend
        if any(t in stack for t in ["react", "next.js"]):
            score += 10

        # Deploy-ready
        if any(t in stack for t in ["docker", "environment config"]):
            score += 10
            strategies.append("Consulting/implementation services")

        # Version controlled with remote
        if p.get("remote_url"):
            score += 5
            strategies.append("Open-source with paid tier")

        if score >= 30:
            scored.append({
                "name": p["name"],
                "score": score,
                "tech_stack": p.get("tech_stack", []),
                "strategies": strategies,
                "git_status": p.get("git_status", "unknown"),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "success": True,
        "projects": scored[:10],
        "total_scanned": len(projects),
        "opportunities": len(scored),
        "message": f"Found {len(scored)} revenue opportunities across {len(projects)} projects",
    }


async def _exec_generate_review(params: dict) -> dict:
    review = await _svc("coach_service").generate_weekly_review()
    wins = review.get("wins", [])
    challenges = review.get("challenges", [])
    priorities = review.get("next_week_priorities", [])
    return {
        "success": True,
        "review": review,
        "message": (
            f"Weekly review generated — "
            f"{len(wins)} wins, {len(challenges)} challenges, {len(priorities)} priorities"
        ),
    }


# ─── Projects & Git ───────────────────────────────────────────────

def _exec_review_project(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "project name is required"}
    path = _resolve_project_path(name)
    if not path:
        return {"success": False, "error": f"Project '{name}' not found"}

    info = _svc("projects_service").get_project_info(path)
    commits = _svc("projects_service").get_recent_commits(path, count=5)
    branches = _svc("projects_service").get_branches(path)

    return {
        "success": True,
        "project": info,
        "recent_commits": commits,
        "branches": [b["name"] for b in branches],
        "message": f"Project review: {name} ({', '.join(info.get('tech_stack', []))})",
    }


def _exec_list_projects(params: dict) -> dict:
    projects = _svc("projects_service").list_projects()
    summary = []
    for p in projects[:20]:
        line = f"{p['name']} ({', '.join(p.get('tech_stack', [])[:3])})"
        if p.get("git_status") == "dirty":
            line += " [uncommitted changes]"
        if p.get("description"):
            line += f" — {p['description']}"
        summary.append(line)
    msg = f"Found {len(projects)} projects:\n" + "\n".join(f"- {s}" for s in summary) if summary else "No projects found"
    return {"success": True, "count": len(projects), "projects": summary, "message": msg}


def _exec_git_status(params: dict) -> dict:
    name = params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}
    path = _resolve_project_path(name)
    if not path:
        return {"success": False, "error": f"Project '{name}' not found"}

    info = _svc("projects_service").get_project_info(path)
    return {
        "success": True,
        "branch": info.get("git_branch"),
        "status": info.get("git_status"),
        "uncommitted_changes": info.get("uncommitted_changes", 0),
        "last_commit": info.get("last_commit_msg"),
        "message": f"{name}: branch={info.get('git_branch')}, status={info.get('git_status')}, "
                   f"{info.get('uncommitted_changes', 0)} uncommitted changes",
    }


def _exec_git_log(params: dict) -> dict:
    name = params.get("project")
    count = params.get("count", 10)
    if not name:
        return {"success": False, "error": "project name is required"}
    path = _resolve_project_path(name)
    if not path:
        return {"success": False, "error": f"Project '{name}' not found"}

    commits = _svc("projects_service").get_recent_commits(path, count=count)
    summary = [f"[{c['hash']}] {c['message']} ({c['date']})" for c in commits]
    return {"success": True, "commits": summary, "count": len(commits)}


def _exec_git_diff(params: dict) -> dict:
    name = params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}
    path = _resolve_project_path(name)
    if not path:
        return {"success": False, "error": f"Project '{name}' not found"}

    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=path, capture_output=True, text=True, timeout=5,
        )
        diff_stat = result.stdout.strip()
        result_full = subprocess.run(
            ["git", "diff"],
            cwd=path, capture_output=True, text=True, timeout=5,
        )
        diff_text = result_full.stdout[:3000]  # Limit output
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {
        "success": True,
        "stat": diff_stat,
        "diff": diff_text,
        "message": f"Git diff for {name}:\n{diff_stat}" if diff_stat else f"No uncommitted changes in {name}",
    }


# ─── Files ─────────────────────────────────────────────────────────

def _exec_read_file(params: dict) -> dict:
    path = params.get("path")
    if not path:
        return {"success": False, "error": "path is required"}
    try:
        resolved = validate_path(path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if not os.path.isfile(resolved):
        return {"success": False, "error": f"File not found: {path}"}

    size = os.path.getsize(resolved)
    if size > MAX_FILE_SIZE:
        return {"success": False, "error": f"File too large: {size} bytes (max {MAX_FILE_SIZE})"}

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.count("\n") + 1
        return {
            "success": True,
            "path": resolved,
            "size": size,
            "lines": lines,
            "content": content[:5000],  # Limit content sent back
            "truncated": len(content) > 5000,
            "message": f"Read {resolved} ({lines} lines, {size} bytes)",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to read file: {e}"}


def _exec_write_file(params: dict) -> dict:
    path = params.get("path")
    content = params.get("content")
    if not path or content is None:
        return {"success": False, "error": "path and content are required"}
    try:
        resolved = validate_path(path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "success": True,
            "path": resolved,
            "size": len(content),
            "message": f"Wrote {len(content)} bytes to {resolved}",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to write file: {e}"}


def _exec_list_files(params: dict) -> dict:
    path = params.get("path", PROJECTS_DIR)
    pattern = params.get("pattern")
    try:
        resolved = validate_path(path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if not os.path.isdir(resolved):
        return {"success": False, "error": f"Not a directory: {path}"}

    try:
        entries = sorted(os.listdir(resolved))
        if pattern:
            import fnmatch
            entries = [e for e in entries if fnmatch.fnmatch(e, pattern)]
        files = []
        for e in entries[:50]:
            full = os.path.join(resolved, e)
            is_dir = os.path.isdir(full)
            files.append(f"{'[dir] ' if is_dir else ''}{e}")
        return {
            "success": True,
            "path": resolved,
            "count": len(entries),
            "files": files,
            "message": f"Listed {len(entries)} items in {resolved}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _exec_search_files(params: dict) -> dict:
    path = params.get("path", PROJECTS_DIR)
    query = params.get("query")
    pattern = params.get("pattern", "*.py")
    if not query:
        return {"success": False, "error": "query is required"}
    try:
        resolved = validate_path(path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        result = subprocess.run(
            ["grep", "-rn", "-F", "--include", pattern, query, resolved],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")[:20]
        return {
            "success": True,
            "matches": [ln for ln in lines if ln],
            "count": len([ln for ln in lines if ln]),
            "message": f"Found matches for '{query}' in {resolved}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Content ───────────────────────────────────────────────────────

async def _exec_generate_content(params: dict) -> dict:
    topic = params.get("topic")
    if not topic:
        return {"success": False, "error": "topic is required"}

    platform = params.get("platform", "linkedin")
    tone = params.get("tone", "professional")

    result = await _svc("content_service").generate_content(
        topic=topic, platform=platform, tone=tone,
    )
    return {
        "success": True,
        "content": result,
        "message": f"Generated {platform} content about: {topic}",
    }


def _exec_schedule_content(params: dict) -> dict:
    content_id = params.get("content_id")
    scheduled_date = params.get("scheduled_date")
    if not content_id:
        return {"success": False, "error": "content_id is required"}
    if not scheduled_date:
        return {"success": False, "error": "scheduled_date is required"}
    updates = {"scheduled_date": scheduled_date, "status": "scheduled"}
    if params.get("scheduled_time"):
        updates["scheduled_time"] = params["scheduled_time"]
    result = _svc("content_service").update_content(content_id, updates)
    if not result:
        return {"success": False, "error": f"Content {content_id} not found"}
    return {"success": True, "content": result, "message": f"Scheduled '{result['title']}' for {scheduled_date}"}


# ─── Focus Mode ───────────────────────────────────────────────────

def _exec_start_focus(params: dict) -> dict:
    task_id = params.get("task_id")
    minutes = params.get("minutes", 25)
    session = _svc("focus_service").start_focus(task_id=task_id, planned_minutes=minutes)
    return {"success": True, "session": session, "message": f"Focus session started ({minutes} min){' on: ' + session.get('task_title') if session.get('task_title') else ''}"}


def _exec_end_focus(params: dict) -> dict:
    notes = params.get("notes", "")
    session = _svc("focus_service").end_focus(notes=notes)
    if not session:
        return {"success": False, "error": "No active focus session"}
    return {"success": True, "session": session, "message": "Focus session ended"}


def _exec_focus_stats(params: dict) -> dict:
    days = params.get("days", 7)
    stats = _svc("focus_service").get_focus_stats(days)
    return {
        "success": True,
        "stats": stats,
        "message": f"Focus stats ({days}d): {stats['total_minutes']}min across {stats['total_sessions']} sessions",
    }


# ─── Briefing & Shutdown ─────────────────────────────────────────

async def _exec_daily_briefing(params: dict) -> dict:
    from products.fred_assistant.services import assistant
    briefing = await assistant.generate_briefing()
    return {"success": True, "briefing": briefing, "message": "Daily briefing generated"}


async def _exec_daily_shutdown(params: dict) -> dict:
    from products.fred_assistant.services import assistant
    shutdown = await assistant.generate_shutdown()
    return {"success": True, "shutdown": shutdown, "message": "Daily shutdown review generated"}


# ─── CRM ──────────────────────────────────────────────────────────

def _exec_add_lead(params: dict) -> dict:
    data = {
        "name": params.get("name", ""),
        "company": params.get("company", ""),
        "email": params.get("email", ""),
        "source": params.get("source", ""),
        "deal_value": params.get("deal_value", 0),
    }
    if not data["name"]:
        return {"success": False, "error": "name is required"}
    lead = _svc("crm_service").create_lead(data)
    return {"success": True, "lead": lead, "message": f"Created lead: {lead['name']} ({lead['company'] or 'no company'})"}


def _exec_update_lead(params: dict) -> dict:
    lead_id = params.get("lead_id")
    if not lead_id:
        return {"success": False, "error": "lead_id is required"}
    updates = {}
    for key in ["stage", "deal_value", "notes", "name", "company", "email"]:
        if key in params:
            if key == "stage":
                updates["pipeline_stage"] = params[key]
            else:
                updates[key] = params[key]
    lead = _svc("crm_service").update_lead(lead_id, updates)
    if not lead:
        return {"success": False, "error": f"Lead {lead_id} not found"}
    return {"success": True, "lead": lead, "message": f"Updated lead: {lead['name']} ({lead['pipeline_stage']})"}


def _exec_log_outreach(params: dict) -> dict:
    lead_id = params.get("lead_id")
    if not lead_id:
        return {"success": False, "error": "lead_id is required"}
    entry = _svc("crm_service").log_outreach(
        lead_id=lead_id,
        outreach_type=params.get("type", "email"),
        content=params.get("content", ""),
        result=params.get("result", ""),
    )
    return {"success": True, "entry": entry, "message": f"Logged {entry['outreach_type']} outreach for lead {lead_id}"}


def _exec_schedule_followup(params: dict) -> dict:
    lead_id = params.get("lead_id")
    followup_date = params.get("date")
    if not lead_id or not followup_date:
        return {"success": False, "error": "lead_id and date are required"}
    lead = _svc("crm_service").schedule_followup(lead_id, followup_date, params.get("notes", ""))
    if not lead:
        return {"success": False, "error": f"Lead {lead_id} not found"}
    return {"success": True, "lead": lead, "message": f"Followup scheduled for {followup_date} with {lead['name']}"}


def _exec_list_leads(params: dict) -> dict:
    stage = params.get("stage")
    leads = _svc("crm_service").list_leads(stage=stage)
    summary = [f"[{lead['id']}] {lead['name']} ({lead['company'] or 'no co.'}) — {lead['pipeline_stage']}, ${lead['deal_value']:,.0f}" for lead in leads[:20]]
    return {"success": True, "count": len(leads), "leads": summary, "message": f"Found {len(leads)} leads" + (f" in {stage}" if stage else "")}


def _exec_pipeline_summary(params: dict) -> dict:
    summary = _svc("crm_service").get_pipeline_summary()
    stages = summary.get("stages", {})
    lines = [f"{s}: {d['count']} leads (${d['total_value']:,.0f})" for s, d in stages.items() if d["count"] > 0]
    return {
        "success": True,
        "summary": summary,
        "message": f"Pipeline: {summary['total_leads']} leads, ${summary['total_pipeline_value']:,.0f} total\n" + "\n".join(lines),
    }


# ─── Publish ──────────────────────────────────────────────────────

def _exec_approve_content(params: dict) -> dict:
    content_id = params.get("content_id")
    if not content_id:
        return {"success": False, "error": "content_id is required"}
    result = _svc("publish_service").approve_content(content_id)
    if not result:
        return {"success": False, "error": f"Content {content_id} not found"}
    return {"success": True, "content": result, "message": f"Approved: {result.get('title', content_id)}"}


def _exec_publish_content(params: dict) -> dict:
    content_id = params.get("content_id")
    if not content_id:
        return {"success": False, "error": "content_id is required"}
    platform = params.get("platform")
    dry_run = params.get("dry_run", True)
    result = _svc("publish_service").publish_content(content_id, platform, dry_run)
    if not result:
        return {"success": False, "error": f"Content {content_id} not found"}
    return {"success": True, "result": result, "message": result.get("message", "Published")}


# ─── Metrics / CEO Lens ──────────────────────────────────────────

def _exec_ceo_lens(params: dict) -> dict:
    metrics = _svc("metrics_service").get_current_metrics()
    lines = [
        f"MRR: ${metrics['mrr']:,.0f}",
        f"Leads contacted: {metrics['leads_contacted']}",
        f"Calls booked: {metrics['calls_booked']}",
        f"Trials: {metrics['trials_started']}",
        f"Deals closed: {metrics['deals_closed']}",
        f"Sprint completion: {metrics['sprint_completion_pct']}%",
        f"Content published: {metrics['content_published']}",
        f"Overdue tasks: {metrics['overdue_tasks']}",
        f"Focus today: {metrics['focus_minutes_today']}min",
    ]
    return {"success": True, "metrics": metrics, "message": "CEO Lens:\n" + "\n".join(lines)}


def _exec_log_metric(params: dict) -> dict:
    name = params.get("name")
    value = params.get("value")
    if not name or value is None:
        return {"success": False, "error": "name and value are required"}
    result = _svc("metrics_service").log_metric(name, float(value))
    return {"success": True, "snapshot": result, "message": f"Logged {name} = {value}"}


# ─── Inbox ────────────────────────────────────────────────────────

def _exec_inbox(params: dict) -> dict:
    items = _svc("inbox_service").get_inbox()
    summary = [f"[{i['type']}] {i['title']} — {i['description']}" for i in items[:15]]
    return {"success": True, "count": len(items), "items": summary, "message": f"Inbox: {len(items)} items needing attention"}


def _exec_inbox_summary(params: dict) -> dict:
    counts = _svc("inbox_service").get_inbox_count()
    lines = [f"{t}: {c}" for t, c in counts.get("by_type", {}).items()]
    return {"success": True, "counts": counts, "message": f"Inbox summary: {counts['total']} total\n" + "\n".join(lines)}


# ─── Playbooks ────────────────────────────────────────────────────

async def _exec_run_playbook(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "playbook name is required"}
    pb = _svc("playbook_service").get_playbook_by_name(name)
    if not pb:
        return {"success": False, "error": f"Playbook '{name}' not found"}
    result = await _svc("playbook_service").run_playbook(pb["id"])
    return {
        "success": True,
        "result": result,
        "message": f"Ran playbook '{name}': {result['status']} ({len(result.get('steps', []))} steps)",
    }


def _exec_list_playbooks(params: dict) -> dict:
    category = params.get("category")
    playbooks = _svc("playbook_service").list_playbooks(category)
    summary = [f"[{p['id']}] {p['name']} ({p['category']}) — {len(p.get('steps', []))} steps" for p in playbooks]
    return {"success": True, "count": len(playbooks), "playbooks": summary, "message": f"Found {len(playbooks)} playbooks"}


def _exec_create_playbook(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "name is required"}
    data = {
        "name": name,
        "description": params.get("description", ""),
        "steps": params.get("steps", []),
        "category": params.get("category", "general"),
    }
    pb = _svc("playbook_service").create_playbook(data)
    return {"success": True, "playbook": pb, "message": f"Created playbook: {pb['name']}"}


async def _exec_run_autopilot(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "autopilot name is required"}
    pb = _svc("playbook_service").get_playbook_by_name(name)
    if not pb:
        return {"success": False, "error": f"Autopilot '{name}' not found"}
    if pb.get("category") != "autopilot":
        return {"success": False, "error": f"'{name}' is not an autopilot playbook (category: {pb.get('category')})"}
    result = await _svc("playbook_service").run_playbook(pb["id"])
    return {
        "success": True,
        "result": result,
        "message": f"Ran autopilot '{name}': {result['status']}",
    }


def _exec_list_autopilots(params: dict) -> dict:
    playbooks = _svc("playbook_service").list_playbooks("autopilot")
    summary = [f"{p['name']} — {p['description']}" for p in playbooks]
    return {"success": True, "count": len(playbooks), "autopilots": summary}


# ─── Repo Intelligence ───────────────────────────────────────────

def _exec_analyze_repo(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "project name is required"}
    depth = params.get("depth", "quick")
    if depth not in ("quick", "full"):
        depth = "quick"
    result = _svc("repo_intelligence_service").analyze_repo(name, depth=depth)
    if "error" in result:
        return {"success": False, "error": result["error"]}
    findings = result["findings"]
    issue_summary = []
    if findings.get("missing_tests", {}).get("count", 0) > 0:
        issue_summary.append("no tests")
    if not findings.get("missing_ci", {}).get("detected", False):
        issue_summary.append("no CI/CD")
    if findings.get("security_patterns", {}).get("count", 0) > 0:
        issue_summary.append(f"{findings['security_patterns']['count']} security concerns")
    return {
        "success": True,
        "analysis_id": result["id"],
        "health_score": result["health_score"],
        "summary": result["summary"],
        "issues": issue_summary,
        "message": f"Analyzed {name} ({depth}): health score {result['health_score']}/100. {result['summary']}",
    }


def _exec_create_repo_tasks(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "project name is required"}
    create = params.get("create", False)
    latest = _svc("repo_intelligence_service").get_latest_analysis(name)
    if not latest:
        return {"success": False, "error": f"No analysis found for '{name}'. Run analyze_repo first."}
    tasks = _svc("repo_intelligence_service").generate_tasks_from_analysis(latest["id"], create_tasks=create)
    task_lines = [f"P{t['priority']}: {t['title']}" + (f" [{t['revenue_impact']}]" if t.get('revenue_impact') else "") for t in tasks]
    return {
        "success": True,
        "count": len(tasks),
        "tasks": task_lines,
        "created": create,
        "message": f"Generated {len(tasks)} tasks from {name} analysis" + (" (created on boards)" if create else " (preview only)"),
    }


async def _exec_repo_roadmap(params: dict) -> dict:
    name = params.get("name")
    if not name:
        return {"success": False, "error": "project name is required"}
    roadmap = await _svc("repo_intelligence_service").generate_roadmap(name)
    if "error" in roadmap:
        return {"success": False, "error": roadmap["error"]}
    sprint = roadmap.get("sprint_1_week", [])
    month = roadmap.get("roadmap_30_day", [])
    revenue = roadmap.get("revenue_suggestions", [])
    lines = [f"Health: {roadmap['health_score']}/100"]
    if sprint:
        lines.append("This week: " + "; ".join(sprint))
    if month:
        lines.append("30-day: " + "; ".join(month[:3]))
    if revenue:
        lines.append("Revenue: " + "; ".join(revenue[:2]))
    return {
        "success": True,
        "roadmap": roadmap,
        "message": f"Roadmap for {name}:\n" + "\n".join(lines),
    }


def _exec_repo_health(params: dict) -> dict:
    name = params.get("name")
    if name:
        latest = _svc("repo_intelligence_service").get_latest_analysis(name)
        if not latest:
            result = _svc("repo_intelligence_service").analyze_repo(name, depth="quick")
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {
                "success": True,
                "project": name,
                "health_score": result["health_score"],
                "summary": result["summary"],
                "message": f"{name}: {result['health_score']}/100 — {result['summary']}",
            }
        return {
            "success": True,
            "project": name,
            "health_score": latest["health_score"],
            "summary": latest["summary"],
            "message": f"{name}: {latest['health_score']}/100 — {latest['summary']}",
        }
    # All projects
    projects = _svc("projects_service").list_projects()
    results = []
    for p in projects:
        if not p.get("is_git"):
            continue
        latest = _svc("repo_intelligence_service").get_latest_analysis(p["name"])
        if latest:
            results.append({"name": p["name"], "health_score": latest["health_score"]})
        else:
            r = _svc("repo_intelligence_service").analyze_repo(p["name"], depth="quick")
            if "error" not in r:
                results.append({"name": p["name"], "health_score": r["health_score"]})
    results.sort(key=lambda x: x["health_score"])
    lines = [f"{r['name']}: {r['health_score']}/100" for r in results]
    return {
        "success": True,
        "projects": results,
        "count": len(results),
        "message": f"Health scores for {len(results)} repos:\n" + "\n".join(lines),
    }


# ─── Platform Services ────────────────────────────────────────────

PROJECTS_DIR = os.getenv("PROJECTS_DIR", os.path.expanduser("~/Development/Projects"))

_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".go": "go", ".rs": "rust",
    ".java": "java", ".rb": "ruby", ".c": "c", ".cpp": "cpp",
    ".sh": "bash", ".sql": "sql", ".html": "html", ".css": "css",
}


def _detect_language(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    return _LANG_MAP.get(ext, "text")


def _read_project_files(project_path: str, extensions: tuple = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"), max_files: int = 8, max_chars: int = 80000) -> list[dict]:
    """Gather key source files from a project for sending to specialist services."""
    files = []
    total_chars = 0
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
    for root, dirs, filenames in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in sorted(filenames):
            if len(files) >= max_files:
                return files
            if not any(fn.endswith(ext) for ext in extensions):
                continue
            full = os.path.join(root, fn)
            try:
                size = os.path.getsize(full)
                if size > MAX_FILE_SIZE or size == 0:
                    continue
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if total_chars + len(content) > max_chars:
                    continue
                total_chars += len(content)
                rel = os.path.relpath(full, project_path)
                files.append({"path": rel, "content": content, "language": _detect_language(fn)})
            except Exception:
                continue
    return files


def _resolve_project_path(name: str) -> str | None:
    """Resolve a project name to its full path. Auto-clones from GitHub if needed."""
    # Check local dev directory
    path = os.path.join(PROJECTS_DIR, name)
    if os.path.isdir(path):
        return path
    # Check clone directory
    clone_path = os.path.join(_svc("projects_service").CLONE_DIR, name)
    if os.path.isdir(clone_path):
        return clone_path
    # Try auto-clone from GitHub
    cloned = _svc("projects_service")._ensure_clone(name)
    if cloned:
        return cloned
    return None


async def _resolve_code_for_service(params: dict, max_files: int = 3, extra_data: dict = None) -> tuple[dict | None, str | None]:
    """Shared helper: resolve file/project to code + language for platform services.
    Returns (data_dict, project_name) or (error_dict, None)."""
    path = params.get("path")
    project = params.get("project") or params.get("name")
    if not path and not project:
        return {"success": False, "error": "path (file) or project (name) is required"}, None

    if path:
        try:
            resolved = validate_path(path)
        except ValueError as e:
            return {"success": False, "error": str(e)}, None
        if not os.path.isfile(resolved):
            return {"success": False, "error": f"File not found: {path}"}, None
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                code = f.read(MAX_FILE_SIZE)
        except Exception as e:
            return {"success": False, "error": str(e)}, None
        data = {"code": code, "language": _detect_language(resolved), "filename": os.path.basename(resolved)}
    else:
        proj_path = _resolve_project_path(project)
        if not proj_path:
            return {"success": False, "error": f"Project not found: {project}"}, None
        files = _read_project_files(proj_path, max_files=max_files)
        if not files:
            return {"success": False, "error": f"No source files found in {project}"}, None
        combined = "\n\n".join(f"# {f['path']}\n{f['content']}" for f in files)
        data = {"code": combined, "language": files[0]["language"], "filename": project}

    if extra_data:
        data.update(extra_data)
    return data, project or os.path.basename(path)


async def _exec_audit_security(params: dict) -> dict:
    data, name = await _resolve_code_for_service(params)
    if name is None:
        return data
    result = await _svc("platform_services").call_service("code_audit", "POST", "/audit/security", data)
    if "error" in result:
        return {"success": False, "error": result["error"]}
    _svc("platform_services").store_service_result("code_audit", "security", name, result)
    return {
        "success": True, "findings": result.get("findings", ""),
        "agents_used": result.get("agents_used", []),
        "message": f"Security audit complete. Agents: {', '.join(result.get('agents_used', []))}",
    }


async def _exec_audit_code(params: dict) -> dict:
    data, name = await _resolve_code_for_service(params)
    if name is None:
        return data
    result = await _svc("platform_services").call_service("code_audit", "POST", "/audit/review", data)
    if "error" in result:
        return {"success": False, "error": result["error"]}
    _svc("platform_services").store_service_result("code_audit", "review", name, result)
    return {
        "success": True, "findings": result.get("findings", ""),
        "agents_used": result.get("agents_used", []),
        "message": f"Code review complete. Agents: {', '.join(result.get('agents_used', []))}",
    }


async def _exec_generate_tests(params: dict) -> dict:
    extra = {}
    if params.get("focus"):
        extra["focus"] = params["focus"]
    data, name = await _resolve_code_for_service(params, extra_data=extra)
    if name is None:
        return data
    result = await _svc("platform_services").call_service("test_gen", "POST", "/tests/generate", data)
    if "error" in result:
        return {"success": False, "error": result["error"]}
    _svc("platform_services").store_service_result("test_gen", "generate", name, result)
    return {
        "success": True, "tests": result.get("result", ""),
        "framework": result.get("framework", ""),
        "message": f"Tests generated ({result.get('framework', 'unknown')} framework)",
    }


async def _exec_analyze_tests(params: dict) -> dict:
    extra = {}
    if params.get("tests_path"):
        try:
            t_resolved = validate_path(params["tests_path"])
            with open(t_resolved, "r", encoding="utf-8", errors="replace") as f:
                extra["tests"] = f.read(MAX_FILE_SIZE)
        except Exception:
            pass
    data, name = await _resolve_code_for_service(params, extra_data=extra)
    if name is None:
        return data
    result = await _svc("platform_services").call_service("test_gen", "POST", "/tests/analyze", data)
    if "error" in result:
        return {"success": False, "error": result["error"]}
    _svc("platform_services").store_service_result("test_gen", "analyze", name, result)
    return {"success": True, "analysis": result.get("result", ""), "message": "Test coverage analysis complete"}


async def _exec_doc_gen(params: dict, endpoint: str, doc_type: str, result_key: str, extensions: tuple = None) -> dict:
    """Shared helper for doc generation functions (readme, api, architecture)."""
    project = params.get("project") or params.get("name")
    if not project:
        return {"success": False, "error": "project name is required"}
    proj_path = _resolve_project_path(project)
    if not proj_path:
        return {"success": False, "error": f"Project not found: {project}"}
    kw = {"extensions": extensions} if extensions else {}
    files = _read_project_files(proj_path, max_files=8, **kw)
    if not files:
        return {"success": False, "error": f"No source files found in {project}"}
    file_entries = [{"path": f["path"], "content": f["content"]} for f in files]
    result = await _svc("platform_services").call_service("doc_gen", "POST", endpoint, {
        "project_name": project, "files": file_entries,
    })
    if "error" in result:
        return {"success": False, "error": result["error"]}
    _svc("platform_services").store_service_result("doc_gen", doc_type, project, result)
    content = result.get("content", "")
    return {
        "success": True, result_key: content[:3000], "full_length": len(content),
        "message": f"{doc_type.replace('_', ' ').title()} generated for {project} ({len(content)} chars)",
    }


async def _exec_generate_readme(params: dict) -> dict:
    return await _exec_doc_gen(params, "/docs/readme", "readme", "readme")


async def _exec_generate_api_docs(params: dict) -> dict:
    return await _exec_doc_gen(params, "/docs/api", "api", "docs", extensions=(".py", ".js", ".ts"))


async def _exec_generate_architecture(params: dict) -> dict:
    return await _exec_doc_gen(params, "/docs/architecture", "architecture", "architecture")


def _exec_platform_status(params: dict) -> dict:
    status = _svc("platform_services").check_all_services()
    online = sum(1 for s in status.values() if s["healthy"])
    total = len(status)
    lines = []
    for name, s in status.items():
        icon = "online" if s["healthy"] else "OFFLINE"
        lines.append(f"  {s['label']} (:{s['port']}): {icon}")
    return {
        "success": True,
        "services": status,
        "online": online,
        "total": total,
        "message": f"Platform: {online}/{total} services online\n" + "\n".join(lines),
    }


async def _exec_full_project_review(params: dict) -> dict:
    name = params.get("name") or params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}

    results = {"steps": []}

    # Step 1: Repo intelligence analysis
    analysis = _svc("repo_intelligence_service").analyze_repo(name, depth="full")
    if "error" in analysis:
        return {"success": False, "error": analysis["error"]}
    results["health_score"] = analysis["health_score"]
    results["steps"].append(f"Repo analysis: {analysis['health_score']}/100")

    # Step 2: Code audit on key files
    proj_path = _resolve_project_path(name)
    if proj_path:
        files = _read_project_files(proj_path, max_files=3)
        if files:
            combined = "\n\n".join(f"# {f['path']}\n{f['content']}" for f in files)
            audit = await _svc("platform_services").call_service("code_audit", "POST", "/audit/full", {
                "code": combined, "language": files[0]["language"], "filename": name,
            })
            if "error" not in audit:
                results["audit"] = audit.get("findings", "")
                results["steps"].append("Code audit: complete")
                _svc("platform_services").store_service_result("code_audit", "full", name, audit)
            else:
                results["steps"].append(f"Code audit: {audit['error']}")

            # Step 3: Test coverage analysis
            test_analysis = await _svc("platform_services").call_service("test_gen", "POST", "/tests/analyze", {
                "code": combined, "language": files[0]["language"],
            })
            if "error" not in test_analysis:
                results["test_analysis"] = test_analysis.get("result", "")
                results["steps"].append("Test analysis: complete")
                _svc("platform_services").store_service_result("test_gen", "analyze", name, test_analysis)
            else:
                results["steps"].append(f"Test analysis: {test_analysis['error']}")

    # Step 4: Generate tasks from findings
    tasks = _svc("repo_intelligence_service").generate_tasks_from_analysis(analysis["id"], create_tasks=True)
    results["tasks_created"] = len(tasks)
    results["steps"].append(f"Tasks created: {len(tasks)}")

    return {
        "success": True,
        **results,
        "message": f"Full review of {name}: {analysis['health_score']}/100, {len(tasks)} tasks created\n" + "\n".join(results["steps"]),
    }


async def _exec_ship_ready_check(params: dict) -> dict:
    name = params.get("name") or params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}

    proj_path = _resolve_project_path(name)
    if not proj_path:
        return {"success": False, "error": f"Project not found: {name}"}

    checklist = []
    files = _read_project_files(proj_path, max_files=5)
    if not files:
        return {"success": False, "error": f"No source files found in {name}"}

    combined = "\n\n".join(f"# {f['path']}\n{f['content']}" for f in files)
    file_entries = [{"path": f["path"], "content": f["content"]} for f in files]

    # Security audit
    audit = await _svc("platform_services").call_service("code_audit", "POST", "/audit/security", {
        "code": combined, "language": files[0]["language"], "filename": name,
    })
    if "error" not in audit:
        checklist.append({"check": "Security Audit", "status": "done", "details": audit.get("findings", "")[:500]})
        _svc("platform_services").store_service_result("code_audit", "security", name, audit)
    else:
        checklist.append({"check": "Security Audit", "status": "skipped", "details": audit["error"]})

    # Test generation
    test_result = await _svc("platform_services").call_service("test_gen", "POST", "/tests/generate", {
        "code": combined, "language": files[0]["language"], "filename": name,
    })
    if "error" not in test_result:
        checklist.append({"check": "Test Generation", "status": "done", "details": f"Tests generated ({test_result.get('framework', '')})"})
        _svc("platform_services").store_service_result("test_gen", "generate", name, test_result)
    else:
        checklist.append({"check": "Test Generation", "status": "skipped", "details": test_result["error"]})

    # README check
    readme_path = os.path.join(proj_path, "README.md")
    if os.path.isfile(readme_path):
        checklist.append({"check": "README", "status": "done", "details": "README.md exists"})
    else:
        doc_result = await _svc("platform_services").call_service("doc_gen", "POST", "/docs/readme", {
            "project_name": name, "files": file_entries,
        })
        if "error" not in doc_result:
            checklist.append({"check": "README", "status": "generated", "details": "README.md generated (not saved)"})
            _svc("platform_services").store_service_result("doc_gen", "readme", name, doc_result)
        else:
            checklist.append({"check": "README", "status": "missing", "details": doc_result["error"]})

    done = sum(1 for c in checklist if c["status"] in ("done", "generated"))
    lines = [f"  {'[x]' if c['status'] in ('done', 'generated') else '[ ]'} {c['check']}: {c['status']}" for c in checklist]
    return {
        "success": True,
        "checklist": checklist,
        "passed": done,
        "total": len(checklist),
        "message": f"Ship-ready check for {name}: {done}/{len(checklist)} passed\n" + "\n".join(lines),
    }


async def _exec_bootstrap_project(params: dict) -> dict:
    name = params.get("name") or params.get("project")
    if not name:
        return {"success": False, "error": "project name is required"}

    proj_path = _resolve_project_path(name)
    if not proj_path:
        return {"success": False, "error": f"Project not found: {name}"}

    files = _read_project_files(proj_path, max_files=8)
    if not files:
        return {"success": False, "error": f"No source files found in {name}"}

    file_entries = [{"path": f["path"], "content": f["content"]} for f in files]
    outputs = []

    # Generate README
    readme_result = await _svc("platform_services").call_service("doc_gen", "POST", "/docs/readme", {
        "project_name": name, "files": file_entries,
    })
    if "error" not in readme_result:
        outputs.append(f"README.md generated ({len(readme_result.get('content', ''))} chars)")
        _svc("platform_services").store_service_result("doc_gen", "readme", name, readme_result)
    else:
        outputs.append(f"README: {readme_result['error']}")

    # Generate architecture docs
    arch_result = await _svc("platform_services").call_service("doc_gen", "POST", "/docs/architecture", {
        "project_name": name, "files": file_entries,
    })
    if "error" not in arch_result:
        outputs.append(f"Architecture docs generated ({len(arch_result.get('content', ''))} chars)")
        _svc("platform_services").store_service_result("doc_gen", "architecture", name, arch_result)
    else:
        outputs.append(f"Architecture: {arch_result['error']}")

    # Generate test scaffold
    combined = "\n\n".join(f"# {f['path']}\n{f['content']}" for f in files[:3])
    test_result = await _svc("platform_services").call_service("test_gen", "POST", "/tests/generate", {
        "code": combined, "language": files[0]["language"], "filename": name,
    })
    if "error" not in test_result:
        outputs.append(f"Test scaffold generated ({test_result.get('framework', '')})")
        _svc("platform_services").store_service_result("test_gen", "generate", name, test_result)
    else:
        outputs.append(f"Tests: {test_result['error']}")

    # Create setup tasks
    setup_tasks = [
        {"title": f"Set up CI/CD for {name}", "description": "Add GitHub Actions workflow for tests and linting", "priority": 2},
        {"title": f"Add test coverage to {name}", "description": "Run the generated tests, fill coverage gaps", "priority": 2},
        {"title": f"Write contributing guide for {name}", "description": "Add CONTRIBUTING.md with dev setup and PR guidelines", "priority": 3},
    ]
    for t in setup_tasks:
        _svc("task_service").create_task({**t, "board_id": "work"})
    outputs.append(f"{len(setup_tasks)} setup tasks created on work board")

    return {
        "success": True,
        "outputs": outputs,
        "message": f"Bootstrap for {name}:\n" + "\n".join(f"  - {o}" for o in outputs),
    }


# ── Action Registry ─────────────────────────────────────────────────

TOOLS = {
    # Task Management
    "create_task": {"fn": _exec_create_task, "async": False,
                    "desc": "Create a task on a board",
                    "params": "title (required), board (default: work), priority (1-5, default: 3), due_date, description"},
    "update_task": {"fn": _exec_update_task, "async": False,
                    "desc": "Update task fields (including move between boards)",
                    "params": "task_id (required), status, priority, title, description, due_date, board (move to another board)"},
    "complete_task": {"fn": _exec_complete_task, "async": False,
                      "desc": "Mark a task as done",
                      "params": "task_id (required)"},
    "delete_task": {"fn": _exec_delete_task, "async": False,
                    "desc": "Permanently delete a task",
                    "params": "task_id (required)"},
    "list_tasks": {"fn": _exec_list_tasks, "async": False,
                   "desc": "List tasks with optional filters",
                   "params": "board, status (todo/in_progress/review/done)"},
    "search_tasks": {"fn": _exec_search_tasks, "async": False,
                     "desc": "Search tasks by keyword in title or description",
                     "params": "query (required)"},
    "create_todo_list": {"fn": _exec_create_todo_list, "async": False,
                         "desc": "Batch-create multiple tasks from a list",
                         "params": "title (list name), items (required, array of strings), board (default: work)"},
    # Memory
    "remember": {"fn": _exec_remember, "async": False,
                 "desc": "Store a persistent fact",
                 "params": "category, key (required), value (required)"},
    "search_memory": {"fn": _exec_search_memory, "async": False,
                      "desc": "Search stored memories",
                      "params": "query (required)"},
    "forget": {"fn": _exec_forget, "async": False,
               "desc": "Delete a stored memory",
               "params": "memory_id or key (required), category (optional, narrows search by key)"},
    # Calendar
    "create_event": {"fn": _exec_create_event, "async": False,
                     "desc": "Create a calendar event",
                     "params": "title (required), start_date, start_time, end_time, event_type (event/deadline/meeting), description"},
    "list_events": {"fn": _exec_list_events, "async": False,
                    "desc": "List upcoming calendar events",
                    "params": "days (default: 7)"},
    "update_event": {"fn": _exec_update_event, "async": False,
                     "desc": "Update a calendar event",
                     "params": "event_id (required), title, description, event_type, start_date, start_time, end_time, location"},
    "delete_event": {"fn": _exec_delete_event, "async": False,
                     "desc": "Delete a calendar event",
                     "params": "event_id (required)"},
    # Goals & Accountability
    "create_goal": {"fn": _exec_create_goal, "async": False,
                    "desc": "Set a new goal",
                    "params": "title (required), category (business/personal/health), target_date, description"},
    "update_goal": {"fn": _exec_update_goal, "async": False,
                    "desc": "Update goal progress or status",
                    "params": "goal_id (required), progress (0-100), status (active/paused/completed), title"},
    "delete_goal": {"fn": _exec_delete_goal, "async": False,
                    "desc": "Delete a goal",
                    "params": "goal_id (required)"},
    "accountability_check": {"fn": _exec_accountability_check, "async": False,
                             "desc": "Full accountability report — goals, overdue tasks, stats",
                             "params": "none"},
    "find_revenue": {"fn": _exec_find_revenue, "async": False,
                     "desc": "Scan projects for monetization opportunities",
                     "params": "none"},
    "generate_review": {"fn": _exec_generate_review, "async": True,
                        "desc": "Generate an AI-powered weekly review (wins, challenges, lessons, priorities)",
                        "params": "none"},
    # Projects & Git
    "review_project": {"fn": _exec_review_project, "async": False,
                       "desc": "Full project scan — git info, tech stack, commits, branches",
                       "params": "name (required, project directory name)"},
    "list_projects": {"fn": _exec_list_projects, "async": False,
                      "desc": "List all dev projects with tech stacks",
                      "params": "none"},
    "git_status": {"fn": _exec_git_status, "async": False,
                   "desc": "Show current branch and uncommitted changes",
                   "params": "project (required, directory name)"},
    "git_log": {"fn": _exec_git_log, "async": False,
                "desc": "Show recent commits",
                "params": "project (required), count (default: 10)"},
    "git_diff": {"fn": _exec_git_diff, "async": False,
                 "desc": "Show uncommitted changes diff",
                 "params": "project (required)"},
    # Files
    "read_file": {"fn": _exec_read_file, "async": False,
                  "desc": "Read a file (path-validated, max 500KB)",
                  "params": "path (required)"},
    "write_file": {"fn": _exec_write_file, "async": False,
                   "desc": "Write content to a file (path-validated, short content only)",
                   "params": "path (required), content (required)"},
    "list_files": {"fn": _exec_list_files, "async": False,
                   "desc": "List directory contents",
                   "params": "path (default: projects directory), pattern (glob filter)"},
    "search_files": {"fn": _exec_search_files, "async": False,
                     "desc": "Search file contents with literal text match",
                     "params": "path, query (required), pattern (default: *.py)"},
    # Content
    "generate_content": {"fn": _exec_generate_content, "async": True,
                         "desc": "Generate AI content for social media",
                         "params": "topic (required), platform (linkedin/twitter/github), tone (professional/casual/technical)"},
    "schedule_content": {"fn": _exec_schedule_content, "async": False,
                         "desc": "Schedule existing content for a date",
                         "params": "content_id (required), scheduled_date (required, YYYY-MM-DD), scheduled_time"},
    # Focus Mode
    "start_focus": {"fn": _exec_start_focus, "async": False,
                    "desc": "Start a focus/pomodoro session",
                    "params": "task_id (optional), minutes (default: 25)"},
    "end_focus": {"fn": _exec_end_focus, "async": False,
                  "desc": "End the current focus session",
                  "params": "notes (optional)"},
    "focus_stats": {"fn": _exec_focus_stats, "async": False,
                    "desc": "Show focus session statistics",
                    "params": "days (default: 7)"},
    # Briefing & Shutdown
    "daily_briefing": {"fn": _exec_daily_briefing, "async": True,
                       "desc": "Generate morning daily briefing with priorities",
                       "params": "none"},
    "daily_shutdown": {"fn": _exec_daily_shutdown, "async": True,
                       "desc": "Generate end-of-day shutdown review",
                       "params": "none"},
    # CRM
    "add_lead": {"fn": _exec_add_lead, "async": False,
                 "desc": "Add a new lead to the CRM",
                 "params": "name (required), company, email, source, deal_value"},
    "update_lead": {"fn": _exec_update_lead, "async": False,
                    "desc": "Update a lead's info or stage",
                    "params": "lead_id (required), stage, deal_value, notes, name, company, email"},
    "log_outreach": {"fn": _exec_log_outreach, "async": False,
                     "desc": "Log an outreach activity for a lead",
                     "params": "lead_id (required), type (email/call/linkedin/meeting), content, result"},
    "schedule_followup": {"fn": _exec_schedule_followup, "async": False,
                          "desc": "Schedule a followup with a lead",
                          "params": "lead_id (required), date (required, YYYY-MM-DD), notes"},
    "list_leads": {"fn": _exec_list_leads, "async": False,
                   "desc": "List leads with optional stage filter",
                   "params": "stage (cold/contacted/call_booked/trial/paid/churned)"},
    "pipeline_summary": {"fn": _exec_pipeline_summary, "async": False,
                         "desc": "Show pipeline summary with counts and values per stage",
                         "params": "none"},
    # Publish
    "approve_content": {"fn": _exec_approve_content, "async": False,
                        "desc": "Approve content for publishing",
                        "params": "content_id (required)"},
    "publish_content": {"fn": _exec_publish_content, "async": False,
                        "desc": "Publish content to a platform (dry_run by default)",
                        "params": "content_id (required), platform, dry_run (default: true)"},
    # Metrics / CEO Lens
    "ceo_lens": {"fn": _exec_ceo_lens, "async": False,
                 "desc": "Show CEO-level metrics dashboard (MRR, pipeline, sprint, focus)",
                 "params": "none"},
    "log_metric": {"fn": _exec_log_metric, "async": False,
                   "desc": "Log a custom metric (e.g., MRR, revenue)",
                   "params": "name (required), value (required, number)"},
    # Inbox
    "inbox": {"fn": _exec_inbox, "async": False,
              "desc": "Show all items needing attention (overdue, followups, approvals, stale goals)",
              "params": "none"},
    "inbox_summary": {"fn": _exec_inbox_summary, "async": False,
                      "desc": "Quick count of inbox items by type",
                      "params": "none"},
    # Playbooks
    "run_playbook": {"fn": _exec_run_playbook, "async": True,
                     "desc": "Run a multi-step playbook by name",
                     "params": "name (required)"},
    "list_playbooks": {"fn": _exec_list_playbooks, "async": False,
                       "desc": "List available playbooks",
                       "params": "category (general/autopilot/project/routine)"},
    "create_playbook": {"fn": _exec_create_playbook, "async": False,
                        "desc": "Create a new playbook with steps",
                        "params": "name (required), description, steps (array of action objects), category"},
    # Autopilot
    "run_autopilot": {"fn": _exec_run_autopilot, "async": True,
                      "desc": "Run an autopilot playbook (generates proposed actions)",
                      "params": "name (required)"},
    "list_autopilots": {"fn": _exec_list_autopilots, "async": False,
                        "desc": "List autopilot-category playbooks",
                        "params": "none"},
    # Repo Intelligence
    "analyze_repo": {"fn": _exec_analyze_repo, "async": False,
                     "desc": "Deep-scan a repo for issues, tech debt, and opportunities",
                     "params": "name (required, project directory), depth (quick/full, default: quick)"},
    "create_repo_tasks": {"fn": _exec_create_repo_tasks, "async": False,
                          "desc": "Generate sprint-ready tasks from repo analysis findings",
                          "params": "name (required), create (bool, default: false — preview only)"},
    "repo_roadmap": {"fn": _exec_repo_roadmap, "async": True,
                     "desc": "AI-generated development roadmap from repo analysis",
                     "params": "name (required)"},
    "repo_health": {"fn": _exec_repo_health, "async": False,
                    "desc": "Quick health score for a repo (or all repos)",
                    "params": "name (optional, omit for all repos)"},
    # Platform Services
    "audit_security": {"fn": _exec_audit_security, "async": True,
                       "desc": "Run a security audit on a file or project (uses Code Audit service)",
                       "params": "path (file) or project (name) — one required"},
    "audit_code": {"fn": _exec_audit_code, "async": True,
                   "desc": "Run a code quality review on a file or project (uses Code Audit service)",
                   "params": "path (file) or project (name) — one required"},
    "generate_tests": {"fn": _exec_generate_tests, "async": True,
                       "desc": "Generate unit tests for a file or project (uses Test Generator service)",
                       "params": "path (file) or project (name) — one required, focus (optional area)"},
    "analyze_tests": {"fn": _exec_analyze_tests, "async": True,
                      "desc": "Analyze test coverage and suggest missing tests",
                      "params": "path (source file) or project (name) — one required, tests_path (existing test file)"},
    "generate_readme": {"fn": _exec_generate_readme, "async": True,
                        "desc": "Generate README.md for a project (uses Doc Generator service)",
                        "params": "project (required, project name)"},
    "generate_api_docs": {"fn": _exec_generate_api_docs, "async": True,
                          "desc": "Generate API documentation for a project (uses Doc Generator service)",
                          "params": "project (required, project name)"},
    "generate_architecture": {"fn": _exec_generate_architecture, "async": True,
                              "desc": "Generate architecture docs with Mermaid diagrams (uses Doc Generator service)",
                              "params": "project (required, project name)"},
    "platform_status": {"fn": _exec_platform_status, "async": False,
                        "desc": "Check health of all platform services (Code Audit, Test Gen, Doc Gen, PR Bot, Fred API)",
                        "params": "none"},
    # Workflows
    "full_project_review": {"fn": _exec_full_project_review, "async": True,
                            "desc": "Full integrated review: repo analysis + code audit + test analysis + task creation",
                            "params": "name (required, project name)"},
    "ship_ready_check": {"fn": _exec_ship_ready_check, "async": True,
                         "desc": "Ship-readiness checklist: security audit + test gen + doc check",
                         "params": "name (required, project name)"},
    "bootstrap_project": {"fn": _exec_bootstrap_project, "async": True,
                          "desc": "Bootstrap a project: generate README + architecture docs + test scaffold + setup tasks",
                          "params": "name (required, project name)"},
}


def get_tool_definitions() -> str:
    """Build a tool definition block for the system prompt."""
    lines = ["## Available Actions", ""]
    lines.append("You can take actions by including ACTION: lines in your response.")
    lines.append('Format: ACTION: tool_name(param="value", num=123, flag=true, list=["a","b"])')
    lines.append("You may include multiple ACTION: lines. Each must be on its own line.")
    lines.append("After actions execute, you'll see results and can respond based on them.")
    lines.append("")

    categories = {
        "Task Management": ["create_task", "update_task", "complete_task", "delete_task",
                            "list_tasks", "search_tasks", "create_todo_list"],
        "Memory": ["remember", "search_memory", "forget"],
        "Calendar": ["create_event", "list_events", "update_event", "delete_event"],
        "Goals & Accountability": ["create_goal", "update_goal", "delete_goal",
                                   "accountability_check", "find_revenue", "generate_review"],
        "Projects & Git": ["review_project", "list_projects", "git_status", "git_log", "git_diff"],
        "Files": ["read_file", "write_file", "list_files", "search_files"],
        "Content": ["generate_content", "schedule_content", "approve_content", "publish_content"],
        "Focus Mode": ["start_focus", "end_focus", "focus_stats"],
        "Briefing & Shutdown": ["daily_briefing", "daily_shutdown"],
        "CRM": ["add_lead", "update_lead", "log_outreach", "schedule_followup",
                "list_leads", "pipeline_summary"],
        "CEO Lens": ["ceo_lens", "log_metric"],
        "Inbox": ["inbox", "inbox_summary"],
        "Playbooks & Autopilot": ["run_playbook", "list_playbooks", "create_playbook",
                                   "run_autopilot", "list_autopilots"],
        "Repo Intelligence": ["analyze_repo", "create_repo_tasks", "repo_roadmap", "repo_health"],
        "Platform Services": ["audit_security", "audit_code", "generate_tests", "analyze_tests",
                              "generate_readme", "generate_api_docs", "generate_architecture",
                              "platform_status"],
        "Workflows": ["full_project_review", "ship_ready_check", "bootstrap_project"],
    }

    for cat, tool_names in categories.items():
        lines.append(f"### {cat}")
        for name in tool_names:
            tool = TOOLS[name]
            lines.append(f"- **{name}** — {tool['desc']}")
            lines.append(f"  Params: {tool['params']}")
        lines.append("")

    return "\n".join(lines)


async def execute_action(action: dict) -> dict:
    """Execute a single parsed action and return the result."""
    name = action["name"]
    params = action["params"]

    if name not in TOOLS:
        return {"success": False, "error": f"Unknown action: {name}"}

    tool = TOOLS[name]
    try:
        if tool["async"]:
            result = await tool["fn"](params)
        else:
            result = tool["fn"](params)

        # Log to activity_log
        log_activity(
            f"action:{name}",
            "fred_tool",
            None,
            {"params": params, "success": result.get("success", False)},
        )
        return result
    except Exception as e:
        logger.error(f"Action {name} failed: {e}", exc_info=True)
        return {"success": False, "error": f"Action failed: {str(e)}"}


async def execute_actions(actions: list[dict]) -> list[dict]:
    """Execute a list of actions sequentially and return results."""
    results = []
    for action in actions:
        result = await execute_action(action)
        results.append({"action": action["name"], "params": action["params"], **result})
    return results
